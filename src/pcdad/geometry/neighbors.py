"""Nearest-neighbor utilities for small point-cloud diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class NeighborResult:
    """Nearest-neighbor distances and reference indices."""

    distances: np.ndarray[Any, np.dtype[np.float64]]
    indices: np.ndarray[Any, np.dtype[np.int64]]


def nearest_neighbors(
    query: np.ndarray[Any, np.dtype[np.floating[Any]]],
    reference: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    k: int = 1,
) -> NeighborResult:
    """Return sorted k-nearest neighbors from ``reference`` for each query point."""

    query_points = _as_points(query, name="query")
    reference_points = _as_points(reference, name="reference")
    _validate_k(k, reference_points.shape[0], name="reference point count")
    distances, indices = _query_knn(query_points, reference_points, k=k)
    return NeighborResult(distances=distances, indices=indices)


def knn_indices(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    k: int,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    """Return k nearest neighbor indices for each point, excluding the point itself."""

    points_array = _as_points(points, name="points")
    if k <= 0:
        raise ValueError("k must be positive")
    if points_array.shape[0] < k + 1:
        raise ValueError("points must contain at least k + 1 rows")
    result = nearest_neighbors(points_array, points_array, k=k + 1)
    return np.asarray(result.indices[:, 1:], dtype=np.int64)


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


def _validate_k(k: int, reference_count: int, *, name: str) -> None:
    if k <= 0:
        raise ValueError("k must be positive")
    if k > reference_count:
        raise ValueError(f"k cannot exceed {name}: k={k}, {name}={reference_count}")


def _query_knn(
    query: np.ndarray[Any, np.dtype[np.float64]],
    reference: np.ndarray[Any, np.dtype[np.float64]],
    *,
    k: int,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.int64]]]:
    try:
        from scipy.spatial import cKDTree  # type: ignore[import-untyped]

        tree = cKDTree(reference)
        distances, indices = tree.query(query, k=k)
        distances = np.asarray(distances, dtype=np.float64)
        indices = np.asarray(indices, dtype=np.int64)
        if k == 1:
            distances = distances.reshape(-1, 1)
            indices = indices.reshape(-1, 1)
        return distances, indices
    except ImportError:
        return _query_knn_numpy(query, reference, k=k)


def _query_knn_numpy(
    query: np.ndarray[Any, np.dtype[np.float64]],
    reference: np.ndarray[Any, np.dtype[np.float64]],
    *,
    k: int,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.int64]]]:
    distances = np.empty((query.shape[0], k), dtype=np.float64)
    indices = np.empty((query.shape[0], k), dtype=np.int64)
    for row_index, point in enumerate(query):
        squared = np.sum((reference - point) ** 2, axis=1)
        candidate_indices = np.argsort(squared, kind="mergesort")[:k]
        distances[row_index] = np.sqrt(squared[candidate_indices])
        indices[row_index] = candidate_indices
    return distances, indices
