from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import cv2
import ezdxf
import numpy as np
from scipy.spatial import ConvexHull


@dataclass
class ReconstructionSettings:
    feature_method: str = "SIFT"
    match_ratio: float = 0.75
    min_matches: int = 40
    ransac_threshold: float = 1.0
    baseline_meters: float = 1.0
    max_points_per_pair: int = 1500
    focal_scale: float = 0.9


@dataclass
class PairStat:
    pair: str
    good_matches: int
    inliers: int
    triangulated_points: int
    status: str


@dataclass
class ReconstructionResult:
    points: np.ndarray
    colors: np.ndarray
    pair_stats: list[PairStat] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PostProcessSettings:
    align_to_ground: bool = True
    remove_outliers: bool = True
    outlier_std_limit: float = 2.8
    trim_percentile: float = 1.0
    target_dimension_m: float = 0.0
    target_axis: str = "longest"


@dataclass
class PostProcessReport:
    points_input: int
    points_after_outlier: int
    points_after_trim: int
    scale_factor: float
    bbox_before_xyz: tuple[float, float, float]
    bbox_after_xyz: tuple[float, float, float]


@dataclass
class PostProcessResult:
    points: np.ndarray
    colors: np.ndarray
    report: PostProcessReport
    warnings: list[str] = field(default_factory=list)


def decode_uploaded_images(uploaded_files: Iterable) -> tuple[list[np.ndarray], list[str]]:
    images: list[np.ndarray] = []
    names: list[str] = []
    for uploaded_file in uploaded_files:
        image_bytes = np.frombuffer(uploaded_file.read(), dtype=np.uint8)
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        if image is not None:
            images.append(image)
            names.append(uploaded_file.name)
    return images, names


def _build_intrinsics(image_shape: tuple[int, int, int], focal_scale: float) -> np.ndarray:
    height, width = image_shape[:2]
    focal = max(width, height) * focal_scale
    return np.array(
        [[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def _create_detector(feature_method: str):
    method = feature_method.upper()
    if method == "SIFT" and hasattr(cv2, "SIFT_create"):
        return cv2.SIFT_create(nfeatures=6000), cv2.NORM_L2, "SIFT"
    return cv2.ORB_create(nfeatures=6000), cv2.NORM_HAMMING, "ORB"


def _match_keypoints(
    image_a: np.ndarray,
    image_b: np.ndarray,
    feature_method: str,
    match_ratio: float,
) -> tuple[np.ndarray, np.ndarray, str]:
    detector, norm_type, used_method = _create_detector(feature_method)

    gray_a = cv2.cvtColor(image_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(image_b, cv2.COLOR_BGR2GRAY)
    keypoints_a, descriptors_a = detector.detectAndCompute(gray_a, None)
    keypoints_b, descriptors_b = detector.detectAndCompute(gray_b, None)

    if descriptors_a is None or descriptors_b is None:
        return np.empty((0, 2)), np.empty((0, 2)), used_method

    matcher = cv2.BFMatcher(norm_type, crossCheck=False)
    matches = matcher.knnMatch(descriptors_a, descriptors_b, k=2)
    good_matches = [m for pair in matches if len(pair) == 2 for m, n in [pair] if m.distance < match_ratio * n.distance]

    pts_a = np.float64([keypoints_a[m.queryIdx].pt for m in good_matches])
    pts_b = np.float64([keypoints_b[m.trainIdx].pt for m in good_matches])
    return pts_a, pts_b, used_method


def reconstruct_sparse_point_cloud(
    images: list[np.ndarray],
    settings: ReconstructionSettings,
) -> ReconstructionResult:
    warnings: list[str] = []
    pair_stats: list[PairStat] = []

    if len(images) < 2:
        return ReconstructionResult(
            points=np.empty((0, 3)),
            colors=np.empty((0, 3), dtype=np.uint8),
            warnings=["Upload at least 2 photos to run reconstruction."],
        )

    intrinsics = _build_intrinsics(images[0].shape, settings.focal_scale)
    camera_rotation = np.eye(3, dtype=np.float64)
    camera_translation = np.zeros((3, 1), dtype=np.float64)

    all_points: list[np.ndarray] = []
    all_colors: list[np.ndarray] = []
    used_fallback_method = False

    for idx in range(len(images) - 1):
        points_a, points_b, used_method = _match_keypoints(
            images[idx],
            images[idx + 1],
            settings.feature_method,
            settings.match_ratio,
        )
        if settings.feature_method.upper() == "SIFT" and used_method == "ORB":
            used_fallback_method = True

        if len(points_a) < settings.min_matches:
            pair_stats.append(
                PairStat(
                    pair=f"{idx}-{idx + 1}",
                    good_matches=len(points_a),
                    inliers=0,
                    triangulated_points=0,
                    status="Skipped: not enough matches",
                )
            )
            continue

        essential_matrix, inlier_mask = cv2.findEssentialMat(
            points_a,
            points_b,
            intrinsics,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=settings.ransac_threshold,
        )
        if essential_matrix is None or inlier_mask is None:
            pair_stats.append(
                PairStat(
                    pair=f"{idx}-{idx + 1}",
                    good_matches=len(points_a),
                    inliers=0,
                    triangulated_points=0,
                    status="Skipped: essential matrix failed",
                )
            )
            continue

        inlier_mask = inlier_mask.ravel().astype(bool)
        inlier_points_a = points_a[inlier_mask]
        inlier_points_b = points_b[inlier_mask]

        if len(inlier_points_a) < settings.min_matches:
            pair_stats.append(
                PairStat(
                    pair=f"{idx}-{idx + 1}",
                    good_matches=len(points_a),
                    inliers=len(inlier_points_a),
                    triangulated_points=0,
                    status="Skipped: not enough inliers",
                )
            )
            continue

        _, relative_rotation, relative_translation, pose_mask = cv2.recoverPose(
            essential_matrix,
            inlier_points_a,
            inlier_points_b,
            intrinsics,
        )
        pose_inliers = int(pose_mask.sum()) if pose_mask is not None else len(inlier_points_a)

        relative_translation = relative_translation * settings.baseline_meters
        next_rotation = relative_rotation @ camera_rotation
        next_translation = relative_rotation @ camera_translation + relative_translation

        projection_a = intrinsics @ np.hstack((camera_rotation, camera_translation))
        projection_b = intrinsics @ np.hstack((next_rotation, next_translation))
        homogeneous_points = cv2.triangulatePoints(
            projection_a,
            projection_b,
            inlier_points_a.T,
            inlier_points_b.T,
        )
        triangulated = (homogeneous_points[:3] / homogeneous_points[3]).T
        finite = np.isfinite(triangulated).all(axis=1)
        triangulated = triangulated[finite]
        kept_points_a = inlier_points_a[finite]

        if len(triangulated) == 0:
            pair_stats.append(
                PairStat(
                    pair=f"{idx}-{idx + 1}",
                    good_matches=len(points_a),
                    inliers=pose_inliers,
                    triangulated_points=0,
                    status="Skipped: triangulation failed",
                )
            )
            continue

        depth_a = (camera_rotation @ triangulated.T + camera_translation).T[:, 2]
        depth_b = (next_rotation @ triangulated.T + next_translation).T[:, 2]
        positive_depth = (depth_a > 0.0) & (depth_b > 0.0)
        triangulated = triangulated[positive_depth]
        kept_points_a = kept_points_a[positive_depth]

        if len(triangulated) > settings.max_points_per_pair:
            sample_idx = np.random.choice(
                len(triangulated),
                settings.max_points_per_pair,
                replace=False,
            )
            triangulated = triangulated[sample_idx]
            kept_points_a = kept_points_a[sample_idx]

        height, width = images[idx].shape[:2]
        pixel_x = np.clip(np.round(kept_points_a[:, 0]).astype(int), 0, width - 1)
        pixel_y = np.clip(np.round(kept_points_a[:, 1]).astype(int), 0, height - 1)
        colors_bgr = images[idx][pixel_y, pixel_x]
        colors_rgb = colors_bgr[:, ::-1]

        all_points.append(triangulated.astype(np.float32))
        all_colors.append(colors_rgb.astype(np.uint8))
        pair_stats.append(
            PairStat(
                pair=f"{idx}-{idx + 1}",
                good_matches=len(points_a),
                inliers=pose_inliers,
                triangulated_points=len(triangulated),
                status="OK",
            )
        )

        camera_rotation = next_rotation
        camera_translation = next_translation

    if used_fallback_method:
        warnings.append("SIFT was not available; ORB was used as a fallback feature detector.")

    if all_points:
        merged_points = np.vstack(all_points)
        merged_colors = np.vstack(all_colors)
    else:
        merged_points = np.empty((0, 3), dtype=np.float32)
        merged_colors = np.empty((0, 3), dtype=np.uint8)
        warnings.append("No valid 3D points were reconstructed. Try more overlapping photos.")

    return ReconstructionResult(
        points=merged_points,
        colors=merged_colors,
        pair_stats=pair_stats,
        warnings=warnings,
    )


def build_convex_hull_mesh(points: np.ndarray) -> np.ndarray:
    if len(points) < 4:
        return np.empty((0, 3), dtype=np.int32)
    try:
        hull = ConvexHull(points)
        return hull.simplices.astype(np.int32)
    except Exception:
        return np.empty((0, 3), dtype=np.int32)


def points_to_ply_bytes(points: np.ndarray, colors: np.ndarray) -> bytes:
    header = [
        "ply",
        "format ascii 1.0",
        f"element vertex {len(points)}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header",
    ]
    body = [
        f"{p[0]} {p[1]} {p[2]} {int(c[0])} {int(c[1])} {int(c[2])}"
        for p, c in zip(points, colors, strict=False)
    ]
    return ("\n".join(header + body) + "\n").encode("utf-8")


def mesh_to_obj_bytes(points: np.ndarray, faces: np.ndarray) -> bytes:
    lines = [f"v {p[0]} {p[1]} {p[2]}" for p in points]
    lines.extend(f"f {a + 1} {b + 1} {c + 1}" for a, b, c in faces)
    return ("\n".join(lines) + "\n").encode("utf-8")


def mesh_to_dxf_bytes(points: np.ndarray, faces: np.ndarray) -> bytes:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    if len(faces) > 0:
        for a, b, c in faces:
            pa = tuple(points[a])
            pb = tuple(points[b])
            pc = tuple(points[c])
            msp.add_3dface([pa, pb, pc, pc])
    else:
        for point in points:
            msp.add_point(tuple(point))

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "site_model.dxf"
        doc.saveas(path)
        return path.read_bytes()


def points_to_floorplan_dxf_bytes(points: np.ndarray, ground_percentile: float = 35.0) -> bytes:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    if len(points) == 0:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "site_floorplan.dxf"
            doc.saveas(path)
            return path.read_bytes()

    z_threshold = np.percentile(points[:, 2], ground_percentile)
    near_ground = points[points[:, 2] <= z_threshold]
    source = near_ground if len(near_ground) >= 3 else points
    xy = source[:, :2]

    if len(xy) >= 3:
        try:
            hull = ConvexHull(xy)
            vertices = xy[hull.vertices]
            polyline_points = [(float(p[0]), float(p[1])) for p in vertices]
            msp.add_lwpolyline(polyline_points, close=True)
        except Exception:
            for p in xy:
                msp.add_point((float(p[0]), float(p[1]), 0.0))
    else:
        for p in xy:
            msp.add_point((float(p[0]), float(p[1]), 0.0))

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "site_floorplan.dxf"
        doc.saveas(path)
        return path.read_bytes()


def _bbox_extents(points: np.ndarray) -> tuple[float, float, float]:
    if len(points) == 0:
        return 0.0, 0.0, 0.0
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    extents = maxs - mins
    return float(extents[0]), float(extents[1]), float(extents[2])


def _axis_dimension(extents: tuple[float, float, float], axis: str) -> float:
    lookup = {"x": extents[0], "y": extents[1], "z": extents[2], "longest": max(extents)}
    return float(lookup.get(axis, max(extents)))


def _align_to_ground(points: np.ndarray) -> np.ndarray:
    if len(points) < 3:
        return points
    centered = points - points.mean(axis=0, keepdims=True)
    covariance = np.cov(centered, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    basis = eigenvectors[:, order]
    if np.linalg.det(basis) < 0:
        basis[:, 2] *= -1.0
    return centered @ basis


def postprocess_point_cloud(
    points: np.ndarray,
    colors: np.ndarray,
    settings: PostProcessSettings,
) -> PostProcessResult:
    warnings: list[str] = []
    if len(points) == 0:
        report = PostProcessReport(
            points_input=0,
            points_after_outlier=0,
            points_after_trim=0,
            scale_factor=1.0,
            bbox_before_xyz=(0.0, 0.0, 0.0),
            bbox_after_xyz=(0.0, 0.0, 0.0),
        )
        return PostProcessResult(points=points, colors=colors, report=report, warnings=warnings)

    processed_points = points.astype(np.float32).copy()
    processed_colors = colors.copy()
    bbox_before = _bbox_extents(processed_points)
    points_after_outlier = len(processed_points)
    points_after_trim = len(processed_points)

    if settings.align_to_ground:
        processed_points = _align_to_ground(processed_points).astype(np.float32)

    if settings.remove_outliers and len(processed_points) > 10:
        mean = processed_points.mean(axis=0)
        std = processed_points.std(axis=0)
        std[std < 1e-8] = 1.0
        zscores = np.abs((processed_points - mean) / std)
        mask = np.all(zscores <= settings.outlier_std_limit, axis=1)
        processed_points = processed_points[mask]
        processed_colors = processed_colors[mask]
        points_after_outlier = len(processed_points)

    if settings.trim_percentile > 0 and len(processed_points) > 10:
        p = float(settings.trim_percentile)
        lower = np.percentile(processed_points, p, axis=0)
        upper = np.percentile(processed_points, 100 - p, axis=0)
        mask = np.all((processed_points >= lower) & (processed_points <= upper), axis=1)
        processed_points = processed_points[mask]
        processed_colors = processed_colors[mask]
        points_after_trim = len(processed_points)

    scale_factor = 1.0
    if settings.target_dimension_m > 0 and len(processed_points) > 0:
        current_extents = _bbox_extents(processed_points)
        current_dimension = _axis_dimension(current_extents, settings.target_axis.lower())
        if current_dimension > 1e-8:
            scale_factor = settings.target_dimension_m / current_dimension
            processed_points *= scale_factor
        else:
            warnings.append("Could not apply scale target because current model dimension is near zero.")

    bbox_after = _bbox_extents(processed_points)
    report = PostProcessReport(
        points_input=len(points),
        points_after_outlier=points_after_outlier,
        points_after_trim=points_after_trim,
        scale_factor=float(scale_factor),
        bbox_before_xyz=bbox_before,
        bbox_after_xyz=bbox_after,
    )
    return PostProcessResult(
        points=processed_points,
        colors=processed_colors,
        report=report,
        warnings=warnings,
    )
