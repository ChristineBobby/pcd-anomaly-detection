"""Multiscale PCA curvature utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pcdad.geometry.normals import estimate_pca_normals


@dataclass(frozen=True)
class CurvatureResult:
    """Per-scale and aggregate curvature estimates."""

    per_scale: dict[int, np.ndarray[Any, np.dtype[np.float64]]]
    mean_curvature: np.ndarray[Any, np.dtype[np.float64]]
    max_curvature: np.ndarray[Any, np.dtype[np.float64]]


def estimate_multiscale_curvature(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    k_values: tuple[int, ...] = (16, 32, 64),
) -> CurvatureResult:
    """Estimate PCA curvature for multiple neighborhood sizes."""

    if not k_values:
        raise ValueError("k_values must contain at least one k")
    unique_k_values = tuple(dict.fromkeys(k_values))
    per_scale: dict[int, np.ndarray[Any, np.dtype[np.float64]]] = {}
    for k in unique_k_values:
        if k <= 0:
            raise ValueError("k_values must be positive")
        per_scale[k] = estimate_pca_normals(points, k=k).curvature

    stacked = np.stack([per_scale[k] for k in unique_k_values], axis=0)
    return CurvatureResult(
        per_scale=per_scale,
        mean_curvature=np.mean(stacked, axis=0),
        max_curvature=np.max(stacked, axis=0),
    )
