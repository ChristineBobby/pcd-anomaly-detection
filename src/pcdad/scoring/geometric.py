"""Geometric residual scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pcdad.geometry.residuals import GeometryResidualResult
from pcdad.scoring.aggregate import topk_mean


@dataclass(frozen=True)
class GeometryScoreConfig:
    """Weights and object aggregation settings for geometry scores."""

    distance_weight: float = 1.0
    normal_weight: float = 0.5
    curvature_weight: float = 0.5
    topk_ratio: float = 0.05
    smooth_k: int = 16


@dataclass(frozen=True)
class GeometryScoreResult:
    """Point-level and object-level geometric anomaly scores."""

    point_scores: np.ndarray[Any, np.dtype[np.float64]]
    object_score: float
    components: dict[str, np.ndarray[Any, np.dtype[np.float64]]]


def score_geometry_residuals(
    residuals: GeometryResidualResult,
    config: GeometryScoreConfig | None = None,
) -> GeometryScoreResult:
    """Normalize and fuse residual components into anomaly scores."""

    cfg = config or GeometryScoreConfig()
    weighted_components: dict[str, np.ndarray[Any, np.dtype[np.float64]]] = {}
    weighted_components["distance"] = _weighted_normalized(
        residuals.nn_distance,
        cfg.distance_weight,
    )
    if residuals.normal_angle is not None and cfg.normal_weight > 0:
        weighted_components["normal"] = _weighted_normalized(
            residuals.normal_angle,
            cfg.normal_weight,
        )
    if residuals.curvature_delta is not None and cfg.curvature_weight > 0:
        weighted_components["curvature"] = _weighted_normalized(
            residuals.curvature_delta,
            cfg.curvature_weight,
        )

    point_scores = np.sum(np.stack(tuple(weighted_components.values()), axis=0), axis=0)
    object_score = topk_mean(point_scores, ratio=cfg.topk_ratio)
    return GeometryScoreResult(
        point_scores=point_scores,
        object_score=object_score,
        components=weighted_components,
    )


def _weighted_normalized(
    values: np.ndarray[Any, np.dtype[np.floating[Any]]],
    weight: float,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    if weight < 0:
        raise ValueError("Geometry score weights must be non-negative")
    normalized = _robust_minmax(values)
    return np.asarray(normalized * weight, dtype=np.float64)


def _robust_minmax(
    values: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"Expected one-dimensional residuals, got {array.shape}")
    if array.shape[0] == 0:
        raise ValueError("residuals must contain at least one value")
    if not np.all(np.isfinite(array)):
        raise ValueError("residuals contains non-finite values")
    lo = float(np.percentile(array, 1.0))
    hi = float(np.percentile(array, 99.0))
    if hi <= lo:
        return np.zeros_like(array, dtype=np.float64)
    return np.clip((array - lo) / (hi - lo), 0.0, 1.0)
