"""Template-bank assignment for registration-aware PASDF diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.geometry.residuals import point_to_template_residuals
from pcdad.prototypes.registration_confidence import registration_confidence_from_features


@dataclass(frozen=True)
class TemplatePrototype:
    """One normal prototype point cloud."""

    class_name: str
    template_id: str
    points: np.ndarray[Any, np.dtype[np.floating[Any]]]
    source_path: Path | None = None


@dataclass(frozen=True)
class TemplateAssignment:
    """One sample-to-template assignment summary."""

    class_name: str
    sample_id: str
    template_id: str
    rank: int
    nn_mean: float
    nn_p95: float
    nn_topk_mean: float
    residual_overlap: float | None
    bbox_ratio: float
    pair_ratio: float
    assignment_entropy: float
    registration_confidence: float
    risk_reason: str


def build_template_assignments(
    *,
    class_name: str,
    sample_id: str,
    sample_points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    templates: tuple[TemplatePrototype, ...],
    pasdf_scores: np.ndarray[Any, np.dtype[np.floating[Any]]] | None,
    top_ratio: float,
) -> tuple[TemplateAssignment, ...]:
    """Rank templates by nearest-neighbor top-k residual and attach confidence features."""

    points = _as_points(sample_points, name="sample_points")
    if not templates:
        raise ValueError("templates must contain at least one prototype")
    _validate_top_ratio(top_ratio)
    scores = (
        None if pasdf_scores is None else _as_scores(pasdf_scores, expected_count=points.shape[0])
    )

    summaries: list[tuple[TemplatePrototype, np.ndarray[Any, np.dtype[np.float64]], float]] = []
    for template in templates:
        if template.class_name != class_name:
            raise ValueError(
                f"template {template.template_id} belongs to {template.class_name}, "
                f"expected {class_name}"
            )
        residuals = point_to_template_residuals(
            points,
            template.points,
            use_normals=False,
            use_curvature=False,
        )
        distances = np.asarray(residuals.nn_distance, dtype=np.float64)
        summaries.append((template, distances, _topk_mean(distances, top_ratio)))

    topk_values = np.asarray([item[2] for item in summaries], dtype=np.float64)
    entropy = assignment_entropy(topk_values)
    ranked = sorted(summaries, key=lambda item: (item[2], item[0].template_id))
    assignments: list[TemplateAssignment] = []
    for rank, (template, distances, nn_topk_mean) in enumerate(ranked, 1):
        overlap = None if scores is None else _topk_overlap(scores, distances, top_ratio)
        top_indices = _topk_indices(distances, top_ratio)
        top_points = points[top_indices]
        bbox_ratio = _safe_ratio(_bbox_diagonal(top_points), _bbox_diagonal(points))
        pair_ratio = _safe_ratio(_mean_pair_distance(top_points), _bbox_diagonal(points))
        confidence = registration_confidence_from_features(
            nn_topk_mean=nn_topk_mean,
            assignment_entropy=entropy,
            residual_overlap=overlap,
            bbox_ratio=bbox_ratio,
            pair_ratio=pair_ratio,
        )
        assignments.append(
            TemplateAssignment(
                class_name=class_name,
                sample_id=sample_id,
                template_id=template.template_id,
                rank=rank,
                nn_mean=_round(float(np.mean(distances))),
                nn_p95=_round(float(np.percentile(distances, 95))),
                nn_topk_mean=_round(nn_topk_mean),
                residual_overlap=None if overlap is None else _round(overlap),
                bbox_ratio=_round(bbox_ratio),
                pair_ratio=_round(pair_ratio),
                assignment_entropy=_round(entropy),
                registration_confidence=confidence.confidence,
                risk_reason=confidence.risk_reason,
            )
        )
    return tuple(assignments)


def assignment_entropy(topk_residuals: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    """Return normalized entropy of template assignment probabilities."""

    values = np.asarray(topk_residuals, dtype=np.float64).reshape(-1)
    if values.shape[0] == 0:
        raise ValueError("topk_residuals must contain at least one value")
    if not np.all(np.isfinite(values)):
        raise ValueError("topk_residuals contains non-finite values")
    if values.shape[0] == 1:
        return 0.0
    shifted = values - float(np.min(values))
    scale = float(np.std(shifted))
    if scale <= 1e-12:
        probabilities = np.full(values.shape[0], 1.0 / values.shape[0], dtype=np.float64)
    else:
        logits = -shifted / scale
        logits = logits - float(np.max(logits))
        exp_values = np.exp(logits)
        probabilities = exp_values / float(np.sum(exp_values))
    entropy = -float(np.sum(probabilities * np.log(probabilities + 1e-12)))
    return _round(entropy / float(np.log(values.shape[0])))


def _as_points(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    name: str,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3), got {array.shape}")
    if array.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one point")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array


def _as_scores(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    expected_count: int,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    if values.shape[0] != expected_count:
        raise ValueError("pasdf_scores length must match sample point count")
    if not np.all(np.isfinite(values)):
        raise ValueError("pasdf_scores contains non-finite values")
    return values


def _validate_top_ratio(top_ratio: float) -> None:
    if top_ratio <= 0.0 or top_ratio > 1.0:
        raise ValueError("top_ratio must be in (0, 1]")


def _topk_indices(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    top_ratio: float,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    _validate_top_ratio(top_ratio)
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    count = max(1, int(np.ceil(values.shape[0] * top_ratio)))
    return np.asarray(np.argsort(values, kind="mergesort")[-count:], dtype=np.int64)


def _topk_mean(scores: np.ndarray[Any, np.dtype[np.floating[Any]]], top_ratio: float) -> float:
    indices = _topk_indices(scores, top_ratio)
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    return float(np.mean(values[indices]))


def _topk_overlap(
    left_scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    right_scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    top_ratio: float,
) -> float:
    left = set(int(index) for index in _topk_indices(left_scores, top_ratio))
    right = set(int(index) for index in _topk_indices(right_scores, top_ratio))
    if not left:
        return 0.0
    return len(left & right) / len(left)


def _bbox_diagonal(points: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    array = _as_points(points, name="points")
    return float(np.linalg.norm(np.max(array, axis=0) - np.min(array, axis=0)))


def _mean_pair_distance(points: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    array = _as_points(points, name="points")
    if array.shape[0] <= 1:
        return 0.0
    distances: list[float] = []
    for index in range(array.shape[0] - 1):
        deltas = array[index + 1 :] - array[index]
        distances.extend(float(value) for value in np.linalg.norm(deltas, axis=1))
    return float(np.mean(distances)) if distances else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 1e-12:
        return 0.0
    return float(numerator / denominator)


def _round(value: float) -> float:
    return round(float(value), 6)
