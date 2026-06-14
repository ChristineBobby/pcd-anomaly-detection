"""Score aggregation helpers for point-cloud anomaly diagnostics."""

from __future__ import annotations

from typing import Any

import numpy as np

from pcdad.geometry.neighbors import knn_indices


def topk_mean(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    ratio: float = 0.05,
) -> float:
    """Return the mean of the largest score ratio, with at least one point."""

    values = _as_scores(scores)
    if ratio <= 0.0 or ratio > 1.0:
        raise ValueError("ratio must be in (0, 1]")
    k = max(1, int(np.ceil(values.shape[0] * ratio)))
    top_values = np.sort(values)[-k:]
    return float(np.mean(top_values))


def percentile_score(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    percentile: float = 95.0,
) -> float:
    """Return a percentile score as a Python float."""

    values = _as_scores(scores)
    if percentile < 0.0 or percentile > 100.0:
        raise ValueError("percentile must be in [0, 100]")
    return float(np.percentile(values, percentile))


def smooth_point_scores(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    k: int = 16,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Average each point score with its k nearest neighbor scores."""

    values = _as_scores(scores)
    points_array = np.asarray(points, dtype=np.float64)
    if points_array.ndim != 2 or points_array.shape[1] != 3:
        raise ValueError(f"Expected points with shape (N, 3), got {points_array.shape}")
    if points_array.shape[0] != values.shape[0]:
        raise ValueError(
            f"Score count {values.shape[0]} does not match point count {points_array.shape[0]}"
        )
    if k <= 0 or points_array.shape[0] <= 1:
        copied = np.empty_like(values, dtype=np.float64)
        copied[:] = values
        return copied
    effective_k = min(k, points_array.shape[0] - 1)
    indices = knn_indices(points_array, k=effective_k)
    smoothed = np.empty_like(values, dtype=np.float64)
    for row_index, neighbor_indices in enumerate(indices):
        local_scores = np.concatenate([[values[row_index]], values[neighbor_indices]])
        smoothed[row_index] = float(np.mean(local_scores))
    return smoothed


def _as_scores(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    values: np.ndarray[Any, np.dtype[np.float64]] = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError(f"Expected one-dimensional scores, got {values.shape}")
    if values.shape[0] == 0:
        raise ValueError("scores must contain at least one value")
    if not np.all(np.isfinite(values)):
        raise ValueError("scores contains non-finite values")
    return values
