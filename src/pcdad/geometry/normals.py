"""PCA normal estimation for point-cloud diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pcdad.geometry.neighbors import knn_indices


@dataclass(frozen=True)
class NormalEstimationResult:
    """PCA normals, local covariance eigenvalues, and curvature."""

    normals: np.ndarray[Any, np.dtype[np.float64]]
    eigenvalues: np.ndarray[Any, np.dtype[np.float64]]
    curvature: np.ndarray[Any, np.dtype[np.float64]]


def estimate_pca_normals(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    k: int = 32,
) -> NormalEstimationResult:
    """Estimate unoriented normals from each point's k-neighborhood."""

    points_array = _as_points(points)
    if k <= 0:
        raise ValueError("k must be positive")
    if points_array.shape[0] < k + 1:
        raise ValueError("points must contain at least k + 1 rows")

    neighbor_indices = knn_indices(points_array, k=k)
    normals = np.empty_like(points_array, dtype=np.float64)
    eigenvalues = np.empty((points_array.shape[0], 3), dtype=np.float64)
    curvature = np.empty((points_array.shape[0],), dtype=np.float64)

    for row_index, indices in enumerate(neighbor_indices):
        local = points_array[indices]
        covariance = _local_covariance(local)
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(values)
        sorted_values = np.maximum(values[order], 0.0)
        normal = vectors[:, order[0]]
        normal_norm = float(np.linalg.norm(normal))
        if normal_norm <= 1e-12:
            normal = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        else:
            normal = normal / normal_norm
        normals[row_index] = normal
        eigenvalues[row_index] = sorted_values
        eigen_sum = float(np.sum(sorted_values))
        curvature[row_index] = 0.0 if eigen_sum <= 1e-12 else sorted_values[0] / eigen_sum

    return NormalEstimationResult(normals=normals, eigenvalues=eigenvalues, curvature=curvature)


def normal_angle_residual(
    source_normals: np.ndarray[Any, np.dtype[np.floating[Any]]],
    target_normals: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Return sign-invariant normal residual in ``[0, 1]``."""

    source = _as_points(source_normals, name="source_normals")
    target = _as_points(target_normals, name="target_normals")
    if source.shape != target.shape:
        raise ValueError(f"Normal shapes must match, got {source.shape} and {target.shape}")
    source_unit = _normalize_rows(source)
    target_unit = _normalize_rows(target)
    cosine = np.sum(source_unit * target_unit, axis=1)
    return np.asarray(1.0 - np.abs(np.clip(cosine, -1.0, 1.0)), dtype=np.float64)


def _as_points(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    name: str = "points",
) -> np.ndarray[Any, np.dtype[np.float64]]:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"Expected {name} with shape (N, 3), got {array.shape}")
    if array.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one point")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array


def _local_covariance(
    points: np.ndarray[Any, np.dtype[np.float64]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    centered = points - points.mean(axis=0, keepdims=True)
    return np.asarray((centered.T @ centered) / max(points.shape[0], 1), dtype=np.float64)


def _normalize_rows(
    points: np.ndarray[Any, np.dtype[np.float64]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    lengths = np.linalg.norm(points, axis=1, keepdims=True)
    if np.any(lengths <= 1e-12):
        raise ValueError("Normals must have non-zero length")
    return np.asarray(points / lengths, dtype=np.float64)
