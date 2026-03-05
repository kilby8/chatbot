from dataclasses import asdict

import cv2
import numpy as np
import streamlit as st
from site2cad_pipeline import (
    PostProcessSettings,
    ReconstructionSettings,
    build_convex_hull_mesh,
    decode_uploaded_images,
    mesh_to_dxf_bytes,
    mesh_to_obj_bytes,
    points_to_floorplan_dxf_bytes,
    points_to_ply_bytes,
    postprocess_point_cloud,
    reconstruct_sparse_point_cloud,
)

st.set_page_config(page_title="Site2CAD", page_icon=":triangular_ruler:", layout="wide")


def _render_projection(points: np.ndarray, x_idx: int, y_idx: int, title: str) -> None:
    if len(points) == 0:
        return

    selected = points[:, [x_idx, y_idx]]
    minimums = selected.min(axis=0)
    spans = np.maximum(selected.max(axis=0) - minimums, 1e-6)
    normalized = (selected - minimums) / spans

    canvas_size = 800
    canvas = np.zeros((canvas_size, canvas_size, 3), dtype=np.uint8)
    for point in normalized:
        px = int(point[0] * (canvas_size - 1))
        py = int((1.0 - point[1]) * (canvas_size - 1))
        cv2.circle(canvas, (px, py), radius=1, color=(0, 255, 255), thickness=-1)

    st.image(canvas, caption=title, channels="BGR", use_container_width=True)


st.title(":triangular_ruler: Site2CAD")
st.caption("Upload site photos, reconstruct a sparse 3D model, and export CAD-friendly files.")

with st.expander("Capture guide", expanded=True):
    st.markdown(
        """
        - Capture **6-30 photos** with strong overlap (60-80%) while walking around the site.
        - Keep lighting consistent and avoid motion blur.
        - Include textured surfaces; blank walls reconstruct poorly.
        - Keep camera height and movement consistent for better geometry.
        """
    )

with st.sidebar:
    st.header("Reconstruction Settings")
    feature_method = st.selectbox("Feature detector", options=["SIFT", "ORB"], index=0)
    match_ratio = st.slider("Feature match ratio test", 0.50, 0.95, 0.75, 0.01)
    min_matches = st.number_input("Minimum matches per pair", min_value=20, max_value=500, value=40, step=5)
    ransac_threshold = st.slider("RANSAC threshold (pixels)", 0.3, 5.0, 1.0, 0.1)
    baseline_meters = st.slider("Approx camera step between photos (m)", 0.1, 5.0, 1.0, 0.1)
    focal_scale = st.slider("Focal scale estimate", 0.4, 1.6, 0.9, 0.05)
    max_points_per_pair = st.number_input(
        "Max triangulated points per image pair",
        min_value=100,
        max_value=10000,
        value=1500,
        step=100,
    )
    st.divider()
    st.header("Post-processing / CAD")
    align_to_ground = st.checkbox("Align model to ground axis (PCA)", value=True)
    remove_outliers = st.checkbox("Remove outlier points", value=True)
    outlier_std_limit = st.slider("Outlier z-score limit", 1.5, 5.0, 2.8, 0.1)
    trim_percentile = st.slider("Trim extreme percentile per axis", 0.0, 5.0, 1.0, 0.1)
    target_dimension_m = st.number_input(
        "Known dimension to scale model (meters, 0=off)",
        min_value=0.0,
        max_value=10000.0,
        value=0.0,
        step=0.1,
    )
    target_axis = st.selectbox("Scale axis", options=["longest", "x", "y", "z"], index=0)
    run_reconstruction = st.button("Run Site2CAD", type="primary", use_container_width=True)

uploaded_files = st.file_uploader(
    "Upload site photos",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Upload sequential photos around the area you want to model.",
)

if run_reconstruction and not uploaded_files:
    st.error("Upload at least 2 photos before running reconstruction.")

if run_reconstruction and uploaded_files:
    reconstruction_settings = ReconstructionSettings(
        feature_method=feature_method,
        match_ratio=float(match_ratio),
        min_matches=int(min_matches),
        ransac_threshold=float(ransac_threshold),
        baseline_meters=float(baseline_meters),
        max_points_per_pair=int(max_points_per_pair),
        focal_scale=float(focal_scale),
    )
    postprocess_settings = PostProcessSettings(
        align_to_ground=bool(align_to_ground),
        remove_outliers=bool(remove_outliers),
        outlier_std_limit=float(outlier_std_limit),
        trim_percentile=float(trim_percentile),
        target_dimension_m=float(target_dimension_m),
        target_axis=target_axis,
    )

    with st.spinner("Decoding photos and running reconstruction..."):
        images, image_names = decode_uploaded_images(uploaded_files)
        raw_result = reconstruct_sparse_point_cloud(images, reconstruction_settings)
        post_result = postprocess_point_cloud(raw_result.points, raw_result.colors, postprocess_settings)
        faces = build_convex_hull_mesh(post_result.points)

    all_warnings = [*raw_result.warnings, *post_result.warnings]
    st.session_state["result_points"] = post_result.points
    st.session_state["result_colors"] = post_result.colors
    st.session_state["result_faces"] = faces
    st.session_state["result_pair_stats"] = [asdict(row) for row in raw_result.pair_stats]
    st.session_state["result_warnings"] = all_warnings
    st.session_state["result_postprocess_report"] = asdict(post_result.report)
    st.session_state["result_image_names"] = image_names

if "result_points" in st.session_state:
    points = st.session_state["result_points"]
    colors = st.session_state["result_colors"]
    faces = st.session_state["result_faces"]
    pair_stats = st.session_state["result_pair_stats"]
    warnings = st.session_state["result_warnings"]
    report = st.session_state.get(
        "result_postprocess_report",
        {
            "points_input": len(points),
            "points_after_outlier": len(points),
            "points_after_trim": len(points),
            "scale_factor": 1.0,
            "bbox_before_xyz": (0.0, 0.0, 0.0),
            "bbox_after_xyz": (0.0, 0.0, 0.0),
        },
    )
    image_names = st.session_state["result_image_names"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Uploaded photos", len(image_names))
    col2.metric("Reconstructed points", len(points))
    col3.metric("Generated mesh faces", len(faces))

    if warnings:
        for warning in warnings:
            st.warning(warning)

    if pair_stats:
        st.subheader("Pair-by-pair reconstruction report")
        st.dataframe(pair_stats, use_container_width=True)

    st.subheader("Post-processing report")
    rep_col1, rep_col2, rep_col3 = st.columns(3)
    rep_col1.metric("Input points", int(report["points_input"]))
    rep_col2.metric("After outlier filter", int(report["points_after_outlier"]))
    rep_col3.metric("After trim filter", int(report["points_after_trim"]))
    st.write(
        f"Scale factor applied: **{report['scale_factor']:.4f}x**  \n"
        f"BBox before (X, Y, Z): **{tuple(round(v, 3) for v in report['bbox_before_xyz'])}**  \n"
        f"BBox after (X, Y, Z): **{tuple(round(v, 3) for v in report['bbox_after_xyz'])}**"
    )

    st.subheader("Point cloud projections")
    if len(points) > 0:
        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            _render_projection(points, 0, 1, "XY projection")
        with pcol2:
            _render_projection(points, 0, 2, "XZ projection")
        with pcol3:
            _render_projection(points, 1, 2, "YZ projection")

        st.subheader("Export files")
        ply_bytes = points_to_ply_bytes(points, colors)
        obj_bytes = mesh_to_obj_bytes(points, faces)
        dxf_bytes = mesh_to_dxf_bytes(points, faces)
        floorplan_dxf_bytes = points_to_floorplan_dxf_bytes(points)

        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        with dcol1:
            st.download_button(
                "Download PLY (point cloud)",
                data=ply_bytes,
                file_name="site_model.ply",
                mime="application/octet-stream",
                use_container_width=True,
            )
        with dcol2:
            st.download_button(
                "Download OBJ (mesh)",
                data=obj_bytes,
                file_name="site_model.obj",
                mime="application/octet-stream",
                use_container_width=True,
            )
        with dcol3:
            st.download_button(
                "Download DXF (CAD)",
                data=dxf_bytes,
                file_name="site_model.dxf",
                mime="application/dxf",
                use_container_width=True,
            )
        with dcol4:
            st.download_button(
                "Download DXF floorplan",
                data=floorplan_dxf_bytes,
                file_name="site_floorplan.dxf",
                mime="application/dxf",
                use_container_width=True,
            )
    else:
        st.info("No points were generated. Try photos with more overlap and texture.")

st.markdown(
    """
    ---
    **Note:** This MVP creates a sparse photogrammetry reconstruction with approximate scale.
    For production CAD accuracy, integrate camera calibration, control points, and dense reconstruction.
    """
)
