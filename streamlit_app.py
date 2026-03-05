from dataclasses import asdict

import cv2
import numpy as np
import streamlit as st
from site2cad_pipeline import (
    ReconstructionSettings,
    build_convex_hull_mesh,
    decode_uploaded_images,
    mesh_to_dxf_bytes,
    mesh_to_obj_bytes,
    points_to_ply_bytes,
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
    settings = ReconstructionSettings(
        feature_method=feature_method,
        match_ratio=float(match_ratio),
        min_matches=int(min_matches),
        ransac_threshold=float(ransac_threshold),
        baseline_meters=float(baseline_meters),
        max_points_per_pair=int(max_points_per_pair),
        focal_scale=float(focal_scale),
    )

    with st.spinner("Decoding photos and running reconstruction..."):
        images, image_names = decode_uploaded_images(uploaded_files)
        result = reconstruct_sparse_point_cloud(images, settings)
        faces = build_convex_hull_mesh(result.points)

    st.session_state["result_points"] = result.points
    st.session_state["result_colors"] = result.colors
    st.session_state["result_faces"] = faces
    st.session_state["result_pair_stats"] = [asdict(row) for row in result.pair_stats]
    st.session_state["result_warnings"] = result.warnings
    st.session_state["result_image_names"] = image_names

if "result_points" in st.session_state:
    points = st.session_state["result_points"]
    colors = st.session_state["result_colors"]
    faces = st.session_state["result_faces"]
    pair_stats = st.session_state["result_pair_stats"]
    warnings = st.session_state["result_warnings"]
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

        dcol1, dcol2, dcol3 = st.columns(3)
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
    else:
        st.info("No points were generated. Try photos with more overlap and texture.")

st.markdown(
    """
    ---
    **Note:** This MVP creates a sparse photogrammetry reconstruction with approximate scale.
    For production CAD accuracy, integrate camera calibration, control points, and dense reconstruction.
    """
)
