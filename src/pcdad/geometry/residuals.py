"""Geometry residuals between a sample point cloud and a template."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pcdad.geometry.curvature import estimate_multiscale_curvature
from pcdad.geometry.neighbors import nearest_neighbors
from pcdad.geometry.normals import estimate_pca_normals, normal_angle_residual


@dataclass(frozen=True)
class GeometryResidualResult:
    """Per-point residual components against a template cloud."""

    nn_distance: np.ndarray[Any, np.dtype[np.float64]]
    normal_angle: np.ndarray[Any, np.dtype[np.float64]] | None
    curvature_delta: np.ndarray[Any, np.dtype[np.float64]] | None
    template_indices: np.ndarray[Any, np.dtype[np.int64]]


def point_to_template_residuals(
    sample_points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    template_points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    k_normal: int = 32,
    k_curvature: tuple[int, ...] = (16, 32, 64),
    use_normals: bool = True,
    use_curvature: bool = True,
) -> GeometryResidualResult:
    """Compare sample points to their nearest template points."""

    sample = _as_points(sample_points, name="sample_points")
    template = _as_points(template_points, name="template_points")
    neighbors = nearest_neighbors(sample, template, k=1)
    template_indices = np.asarray(neighbors.indices[:, 0], dtype=np.int64)
    distances = np.asarray(neighbors.distances[:, 0], dtype=np.float64)

    normal_angle: np.ndarray[Any, np.dtype[np.float64]] | None = None
    if use_normals:
        sample_normals = estimate_pca_normals(sample, k=k_normal).normals
        template_normals = estimate_pca_normals(template, k=k_normal).normals
        normal_angle = normal_angle_residual(sample_normals, template_normals[template_indices])

    curvature_delta: np.ndarray[Any, np.dtype[np.float64]] | None = None
    if use_curvature:
        sample_curvature = estimate_multiscale_curvature(
            sample, k_values=k_curvature
        ).mean_curvature
        template_curvature = estimate_multiscale_curvature(
            template, k_values=k_curvature
        ).mean_curvature
        curvature_delta = np.abs(sample_curvature - template_curvature[template_indices])

    return GeometryResidualResult(
        nn_distance=distances,
        normal_angle=normal_angle,
        curvature_delta=curvature_delta,
        template_indices=template_indices,
    )


def _as_points(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    name: str,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"Expected {name} with shape (N, 3), got {array.shape}")
    if array.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one point")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array
