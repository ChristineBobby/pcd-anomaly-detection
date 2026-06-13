"""P6 targeted registration diagnostics and score fusion utilities."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.analysis.pasdf_case_study import (
    compute_distance_geometry_scores,
    load_pasdf_point_score,
    load_pasdf_template_points,
)
from pcdad.geometry.neighbors import nearest_neighbors
from pcdad.geometry.residuals import point_to_template_residuals
from pcdad.scoring.aggregate import topk_mean
from pcdad.viz.pointcloud import write_pointcloud_score_comparison_svg


@dataclass(frozen=True)
class RegistrationDiagnosticRecord:
    """Registration/template distance summary for one sample."""

    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    nn_distance_mean: float
    nn_distance_p95: float
    nn_distance_p99: float
    nn_distance_top5_mean: float
    pasdf_object_score: float


@dataclass(frozen=True)
class HybridScoreRecord:
    """PASDF/geometry/hybrid score summary for one sample."""

    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    pasdf_object_score: float
    geometry_object_score: float
    hybrid_object_score: float
    pasdf_gt_mean: float | None
    pasdf_background_mean: float | None
    geometry_gt_mean: float | None
    geometry_background_mean: float | None
    hybrid_gt_mean: float | None
    hybrid_background_mean: float | None
    svg_path: str | None


@dataclass(frozen=True)
class AlphaSweepRecord:
    """One sample's hybrid score under one alpha value."""

    alpha: float
    class_name: str
    sample_id: str
    label: int
    hybrid_object_score: float
    pasdf_object_score: float
    geometry_object_score: float
    pasdf_separation: float | None
    hybrid_separation: float | None
    separation_gain: float | None


@dataclass(frozen=True)
class AlphaSweepSummary:
    """Positive-aware alpha sweep aggregate for one alpha value."""

    alpha: float
    anomaly_count: int
    positive_count: int
    min_anomaly_hybrid_object: float | None
    mean_anomaly_hybrid_object: float | None
    max_positive_hybrid_object: float | None
    mean_anomaly_separation_gain: float | None
    strict_pass: bool
    soft_pass: bool


@dataclass(frozen=True)
class TopKRegionMetrics:
    """GT and GT-neighborhood metrics for one top-k score region."""

    score_name: str
    top_ratio: float
    top_count: int
    gt_hit_count: int
    gt_hit_rate: float | None
    gt_coverage: float | None
    gt_neighbor_hit_count: int
    gt_neighbor_hit_rate: float | None
    gt_neighbor_coverage: float | None
    gt_enrichment: float | None
    gt_neighbor_enrichment: float | None


@dataclass(frozen=True)
class Tap1RegionExplanationRecord:
    """PASDF-vs-geometry top-k GT locality diagnostics for one tap1 anomaly."""

    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    neighbor_radius: float
    pasdf_topk_gt_hit_rate: float | None
    geometry_topk_gt_hit_rate: float | None
    pasdf_gt_coverage: float | None
    geometry_gt_coverage: float | None
    pasdf_neighbor_hit_rate: float | None
    geometry_neighbor_hit_rate: float | None
    pasdf_neighbor_enrichment: float | None
    geometry_neighbor_enrichment: float | None


@dataclass(frozen=True)
class Cap3ResidualRegionRecord:
    """PASDF/residual top-k overlap and concentration diagnostics for cap3."""

    class_name: str
    sample_id: str
    label: int
    point_count: int
    pasdf_object_score: float
    residual_topk_mean: float
    residual_topk_p95: float
    pasdf_residual_topk_overlap: float
    residual_topk_bbox_ratio: float
    residual_topk_mean_pair_distance_ratio: float


REGISTRATION_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "nn_distance_mean",
    "nn_distance_p95",
    "nn_distance_p99",
    "nn_distance_top5_mean",
    "pasdf_object_score",
)

HYBRID_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "pasdf_object_score",
    "geometry_object_score",
    "hybrid_object_score",
    "pasdf_gt_mean",
    "pasdf_background_mean",
    "geometry_gt_mean",
    "geometry_background_mean",
    "hybrid_gt_mean",
    "hybrid_background_mean",
    "svg_path",
)

ALPHA_SWEEP_FIELDS: tuple[str, ...] = (
    "alpha",
    "class_name",
    "sample_id",
    "label",
    "hybrid_object_score",
    "pasdf_object_score",
    "geometry_object_score",
    "pasdf_separation",
    "hybrid_separation",
    "separation_gain",
)

ALPHA_SWEEP_SUMMARY_FIELDS: tuple[str, ...] = (
    "alpha",
    "anomaly_count",
    "positive_count",
    "min_anomaly_hybrid_object",
    "mean_anomaly_hybrid_object",
    "max_positive_hybrid_object",
    "mean_anomaly_separation_gain",
    "strict_pass",
    "soft_pass",
)

TAP1_REGION_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "neighbor_radius",
    "pasdf_topk_gt_hit_rate",
    "geometry_topk_gt_hit_rate",
    "pasdf_gt_coverage",
    "geometry_gt_coverage",
    "pasdf_neighbor_hit_rate",
    "geometry_neighbor_hit_rate",
    "pasdf_neighbor_enrichment",
    "geometry_neighbor_enrichment",
)

CAP3_RESIDUAL_REGION_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "pasdf_object_score",
    "residual_topk_mean",
    "residual_topk_p95",
    "pasdf_residual_topk_overlap",
    "residual_topk_bbox_ratio",
    "residual_topk_mean_pair_distance_ratio",
)

REGION_EXPLANATION_FIELDS: tuple[str, ...] = (
    "record_type",
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "neighbor_radius",
    "pasdf_topk_gt_hit_rate",
    "geometry_topk_gt_hit_rate",
    "pasdf_gt_coverage",
    "geometry_gt_coverage",
    "pasdf_neighbor_hit_rate",
    "geometry_neighbor_hit_rate",
    "pasdf_neighbor_enrichment",
    "geometry_neighbor_enrichment",
    "pasdf_object_score",
    "residual_topk_mean",
    "residual_topk_p95",
    "pasdf_residual_topk_overlap",
    "residual_topk_bbox_ratio",
    "residual_topk_mean_pair_distance_ratio",
)


def compute_registration_diagnostic_record(
    *,
    score_path: str | Path,
    template_root: str | Path,
) -> RegistrationDiagnosticRecord:
    """Compute sample/template nearest-neighbor distance diagnostics."""

    path = Path(score_path)
    payload = load_pasdf_point_score(path)
    class_name = _class_name_from_score_path(path)
    sample_id = path.stem
    points = payload["points"].astype(np.float32)
    mask = payload["mask"].astype(np.int64).reshape(-1)
    template_points = load_pasdf_template_points(template_root, class_name)
    residuals = point_to_template_residuals(
        points,
        template_points,
        use_normals=False,
        use_curvature=False,
    )
    distances = np.asarray(residuals.nn_distance, dtype=np.float64)
    return RegistrationDiagnosticRecord(
        class_name=class_name,
        sample_id=sample_id,
        label=_payload_label(payload),
        point_count=int(points.shape[0]),
        gt_point_count=int(np.count_nonzero(mask)),
        nn_distance_mean=_round(float(np.mean(distances))),
        nn_distance_p95=_round(float(np.percentile(distances, 95))),
        nn_distance_p99=_round(float(np.percentile(distances, 99))),
        nn_distance_top5_mean=_round(topk_mean(distances, ratio=0.05)),
        pasdf_object_score=_round(_payload_object_score(payload)),
    )


def compute_hybrid_score_record(
    *,
    score_path: str | Path,
    template_root: str | Path,
    alpha: float,
    svg_path: str | Path | None = None,
    max_points: int = 4096,
    seed: int = 42,
) -> HybridScoreRecord:
    """Compute PASDF + geometry hybrid scores for one sample."""

    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    path = Path(score_path)
    payload = load_pasdf_point_score(path)
    class_name = _class_name_from_score_path(path)
    sample_id = path.stem
    points = payload["points"].astype(np.float32)
    pasdf_scores = payload["point_scores"].astype(np.float64).reshape(-1)
    mask = payload["mask"].astype(np.int64).reshape(-1)
    template_points = load_pasdf_template_points(template_root, class_name)
    geometry_result = compute_distance_geometry_scores(points, template_points)
    geometry_scores = np.asarray(geometry_result.point_scores, dtype=np.float64).reshape(-1)

    pasdf_norm = robust_minmax(pasdf_scores)
    geometry_norm = robust_minmax(geometry_scores)
    hybrid_scores = pasdf_norm + alpha * geometry_norm
    output_svg = None if svg_path is None else Path(svg_path)
    if output_svg is not None:
        write_pointcloud_score_comparison_svg(
            output_svg,
            points,
            pasdf_norm,
            hybrid_scores,
            mask,
            title=f"{class_name}/{sample_id} PASDF vs hybrid",
            left_label="PASDF score",
            right_label="Hybrid score",
            max_points=max_points,
            seed=seed,
        )

    pasdf_gt_mean, pasdf_background_mean = _gt_background_means(pasdf_scores, mask)
    geometry_gt_mean, geometry_background_mean = _gt_background_means(geometry_scores, mask)
    hybrid_gt_mean, hybrid_background_mean = _gt_background_means(hybrid_scores, mask)
    return HybridScoreRecord(
        class_name=class_name,
        sample_id=sample_id,
        label=_payload_label(payload),
        point_count=int(points.shape[0]),
        gt_point_count=int(np.count_nonzero(mask)),
        pasdf_object_score=_round(_payload_object_score(payload)),
        geometry_object_score=_round(float(geometry_result.object_score)),
        hybrid_object_score=_round(topk_mean(hybrid_scores, ratio=0.05)),
        pasdf_gt_mean=_round_optional(pasdf_gt_mean),
        pasdf_background_mean=_round_optional(pasdf_background_mean),
        geometry_gt_mean=_round_optional(geometry_gt_mean),
        geometry_background_mean=_round_optional(geometry_background_mean),
        hybrid_gt_mean=_round_optional(hybrid_gt_mean),
        hybrid_background_mean=_round_optional(hybrid_background_mean),
        svg_path=None if output_svg is None else str(output_svg),
    )


def build_alpha_sweep_record_from_scores(
    *,
    alpha: float,
    class_name: str,
    sample_id: str,
    label: int,
    pasdf_object_score: float,
    geometry_object_score: float,
    pasdf_scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    geometry_scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    mask: np.ndarray[Any, np.dtype[np.integer[Any]]],
) -> AlphaSweepRecord:
    """Build one alpha sweep record from point-level scores."""

    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    pasdf_values = np.asarray(pasdf_scores, dtype=np.float64).reshape(-1)
    geometry_values = np.asarray(geometry_scores, dtype=np.float64).reshape(-1)
    if pasdf_values.shape[0] != geometry_values.shape[0]:
        raise ValueError("pasdf_scores and geometry_scores must have the same length")
    pasdf_norm = robust_minmax(pasdf_values)
    geometry_norm = robust_minmax(geometry_values)
    hybrid_scores = pasdf_norm + alpha * geometry_norm
    pasdf_gt_mean, pasdf_background_mean = _gt_background_means(pasdf_values, mask)
    hybrid_gt_mean, hybrid_background_mean = _gt_background_means(hybrid_scores, mask)
    pasdf_separation = _separation(pasdf_gt_mean, pasdf_background_mean)
    hybrid_separation = _separation(hybrid_gt_mean, hybrid_background_mean)
    separation_gain = (
        None
        if pasdf_separation is None or hybrid_separation is None
        else hybrid_separation - pasdf_separation
    )
    return AlphaSweepRecord(
        alpha=_round(alpha),
        class_name=class_name,
        sample_id=sample_id,
        label=label,
        hybrid_object_score=_round(topk_mean(hybrid_scores, ratio=0.05)),
        pasdf_object_score=_round(pasdf_object_score),
        geometry_object_score=_round(geometry_object_score),
        pasdf_separation=_round_optional(pasdf_separation),
        hybrid_separation=_round_optional(hybrid_separation),
        separation_gain=_round_optional(separation_gain),
    )


def run_alpha_sweep(
    *,
    score_root: str | Path,
    template_root: str | Path,
    anomaly_sample_ids: Sequence[str],
    positive_sample_ids: Sequence[str],
    alpha_grid: Sequence[float],
) -> tuple[AlphaSweepRecord, ...]:
    """Run alpha sweep for anomaly and positive sample ids."""

    sample_ids = tuple(anomaly_sample_ids) + tuple(positive_sample_ids)
    records: list[AlphaSweepRecord] = []
    for sample_id in sample_ids:
        score_path = _find_sample_npz(score_root, sample_id)
        payload = load_pasdf_point_score(score_path)
        class_name = _class_name_from_score_path(score_path)
        points = payload["points"].astype(np.float32)
        pasdf_scores = payload["point_scores"].astype(np.float64).reshape(-1)
        mask = payload["mask"].astype(np.int64).reshape(-1)
        template_points = load_pasdf_template_points(template_root, class_name)
        geometry_result = compute_distance_geometry_scores(points, template_points)
        geometry_scores = np.asarray(geometry_result.point_scores, dtype=np.float64).reshape(-1)
        for alpha in alpha_grid:
            records.append(
                build_alpha_sweep_record_from_scores(
                    alpha=alpha,
                    class_name=class_name,
                    sample_id=score_path.stem,
                    label=_payload_label(payload),
                    pasdf_object_score=_payload_object_score(payload),
                    geometry_object_score=float(geometry_result.object_score),
                    pasdf_scores=pasdf_scores,
                    geometry_scores=geometry_scores,
                    mask=mask,
                )
            )
    return tuple(records)


def summarize_alpha_sweep(records: Sequence[AlphaSweepRecord]) -> tuple[AlphaSweepSummary, ...]:
    """Summarize alpha sweep records with positive-aware pass flags."""

    summaries: list[AlphaSweepSummary] = []
    for alpha in sorted({record.alpha for record in records}):
        alpha_records = tuple(record for record in records if record.alpha == alpha)
        anomaly_records = tuple(record for record in alpha_records if record.label == 1)
        positive_records = tuple(record for record in alpha_records if record.label == 0)
        anomaly_objects = tuple(record.hybrid_object_score for record in anomaly_records)
        positive_objects = tuple(record.hybrid_object_score for record in positive_records)
        gains = tuple(
            record.separation_gain
            for record in anomaly_records
            if record.separation_gain is not None
        )
        min_anomaly = min(anomaly_objects) if anomaly_objects else None
        mean_anomaly = _mean(anomaly_objects)
        max_positive = max(positive_objects) if positive_objects else None
        mean_gain = _mean(gains)
        strict_pass = (
            min_anomaly is not None
            and max_positive is not None
            and mean_gain is not None
            and min_anomaly > max_positive
            and mean_gain > 0.0
        )
        soft_pass = (
            mean_anomaly is not None
            and max_positive is not None
            and mean_gain is not None
            and mean_anomaly > max_positive
            and mean_gain > 0.0
        )
        summaries.append(
            AlphaSweepSummary(
                alpha=_round(alpha),
                anomaly_count=len(anomaly_records),
                positive_count=len(positive_records),
                min_anomaly_hybrid_object=_round_optional(min_anomaly),
                mean_anomaly_hybrid_object=_round_optional(mean_anomaly),
                max_positive_hybrid_object=_round_optional(max_positive),
                mean_anomaly_separation_gain=_round_optional(mean_gain),
                strict_pass=strict_pass,
                soft_pass=soft_pass,
            )
        )
    return tuple(summaries)


def topk_indices(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    ratio: float,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    """Return stable indices for the largest score ratio."""

    values = _as_score_array(scores)
    if ratio <= 0.0 or ratio > 1.0:
        raise ValueError("ratio must be in (0, 1]")
    count = max(1, int(np.ceil(values.shape[0] * ratio)))
    return np.asarray(np.argsort(values, kind="mergesort")[-count:], dtype=np.int64)


def compute_topk_region_metrics(
    *,
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    mask: np.ndarray[Any, np.dtype[np.integer[Any]]],
    score_name: str,
    top_ratio: float,
    neighbor_radius_ratio: float,
) -> TopKRegionMetrics:
    """Compute GT and GT-neighborhood locality metrics for one score vector."""

    points_array = _as_points(points)
    scores_array = _as_score_array(scores)
    mask_array = _as_mask(mask, expected_count=points_array.shape[0])
    if scores_array.shape[0] != points_array.shape[0]:
        raise ValueError("scores length must match points")
    if neighbor_radius_ratio < 0.0:
        raise ValueError("neighbor_radius_ratio must be non-negative")

    top_indices = topk_indices(scores_array, ratio=top_ratio)
    gt_mask = mask_array.astype(bool)
    gt_point_count = int(np.count_nonzero(gt_mask))
    gt_hit_count = int(np.count_nonzero(gt_mask[top_indices]))
    top_count = int(top_indices.shape[0])
    gt_hit_rate = None if top_count == 0 else gt_hit_count / top_count
    gt_coverage = None if gt_point_count == 0 else gt_hit_count / gt_point_count

    neighbor_mask = _gt_neighbor_mask(
        points_array,
        gt_mask,
        radius=_neighbor_radius(points_array, neighbor_radius_ratio),
    )
    neighbor_count = int(np.count_nonzero(neighbor_mask))
    gt_neighbor_hit_count = int(np.count_nonzero(neighbor_mask[top_indices]))
    gt_neighbor_hit_rate = None if top_count == 0 else gt_neighbor_hit_count / top_count
    gt_neighbor_coverage = None if neighbor_count == 0 else gt_neighbor_hit_count / neighbor_count

    gt_fraction = gt_point_count / points_array.shape[0]
    neighbor_fraction = neighbor_count / points_array.shape[0]
    gt_enrichment = None if gt_hit_rate is None or gt_fraction <= 0.0 else gt_hit_rate / gt_fraction
    gt_neighbor_enrichment = (
        None
        if gt_neighbor_hit_rate is None or neighbor_fraction <= 0.0
        else gt_neighbor_hit_rate / neighbor_fraction
    )

    return TopKRegionMetrics(
        score_name=score_name,
        top_ratio=_round(top_ratio),
        top_count=top_count,
        gt_hit_count=gt_hit_count,
        gt_hit_rate=_round_optional(gt_hit_rate),
        gt_coverage=_round_optional(gt_coverage),
        gt_neighbor_hit_count=gt_neighbor_hit_count,
        gt_neighbor_hit_rate=_round_optional(gt_neighbor_hit_rate),
        gt_neighbor_coverage=_round_optional(gt_neighbor_coverage),
        gt_enrichment=_round_optional(gt_enrichment),
        gt_neighbor_enrichment=_round_optional(gt_neighbor_enrichment),
    )


def compute_tap1_region_explanation_record(
    *,
    score_path: str | Path,
    template_root: str | Path,
    top_ratio: float,
    neighbor_radius_ratio: float,
) -> Tap1RegionExplanationRecord:
    """Compare PASDF and geometry top-k locality for one tap1 anomaly sample."""

    path = Path(score_path)
    payload = load_pasdf_point_score(path)
    class_name = _class_name_from_score_path(path)
    points = payload["points"].astype(np.float32)
    pasdf_scores = payload["point_scores"].astype(np.float64).reshape(-1)
    mask = payload["mask"].astype(np.int64).reshape(-1)
    template_points = load_pasdf_template_points(template_root, class_name)
    geometry_result = compute_distance_geometry_scores(points, template_points)
    geometry_scores = np.asarray(geometry_result.point_scores, dtype=np.float64).reshape(-1)
    pasdf_metrics = compute_topk_region_metrics(
        points=points,
        scores=pasdf_scores,
        mask=mask,
        score_name="pasdf",
        top_ratio=top_ratio,
        neighbor_radius_ratio=neighbor_radius_ratio,
    )
    geometry_metrics = compute_topk_region_metrics(
        points=points,
        scores=geometry_scores,
        mask=mask,
        score_name="geometry",
        top_ratio=top_ratio,
        neighbor_radius_ratio=neighbor_radius_ratio,
    )
    return Tap1RegionExplanationRecord(
        class_name=class_name,
        sample_id=path.stem,
        label=_payload_label(payload),
        point_count=int(points.shape[0]),
        gt_point_count=int(np.count_nonzero(mask)),
        neighbor_radius=_round(_neighbor_radius(points, neighbor_radius_ratio)),
        pasdf_topk_gt_hit_rate=pasdf_metrics.gt_hit_rate,
        geometry_topk_gt_hit_rate=geometry_metrics.gt_hit_rate,
        pasdf_gt_coverage=pasdf_metrics.gt_coverage,
        geometry_gt_coverage=geometry_metrics.gt_coverage,
        pasdf_neighbor_hit_rate=pasdf_metrics.gt_neighbor_hit_rate,
        geometry_neighbor_hit_rate=geometry_metrics.gt_neighbor_hit_rate,
        pasdf_neighbor_enrichment=pasdf_metrics.gt_neighbor_enrichment,
        geometry_neighbor_enrichment=geometry_metrics.gt_neighbor_enrichment,
    )


def compute_cap3_residual_region_record(
    *,
    score_path: str | Path,
    template_root: str | Path,
    top_ratio: float,
) -> Cap3ResidualRegionRecord:
    """Compute PASDF/residual top-k overlap and residual concentration for cap3."""

    path = Path(score_path)
    payload = load_pasdf_point_score(path)
    class_name = _class_name_from_score_path(path)
    points = payload["points"].astype(np.float32)
    pasdf_scores = payload["point_scores"].astype(np.float64).reshape(-1)
    template_points = load_pasdf_template_points(template_root, class_name)
    residuals = point_to_template_residuals(
        points,
        template_points,
        use_normals=False,
        use_curvature=False,
    )
    residual_scores = np.asarray(residuals.nn_distance, dtype=np.float64).reshape(-1)
    pasdf_top = set(int(index) for index in topk_indices(pasdf_scores, ratio=top_ratio))
    residual_top_indices = topk_indices(residual_scores, ratio=top_ratio)
    residual_top = set(int(index) for index in residual_top_indices)
    overlap = 0.0 if not residual_top else len(pasdf_top & residual_top) / len(residual_top)
    top_residual_values = residual_scores[residual_top_indices]
    top_points = points[residual_top_indices]
    sample_bbox_diag = _bbox_diagonal(points)
    return Cap3ResidualRegionRecord(
        class_name=class_name,
        sample_id=path.stem,
        label=_payload_label(payload),
        point_count=int(points.shape[0]),
        pasdf_object_score=_round(_payload_object_score(payload)),
        residual_topk_mean=_round(float(np.mean(top_residual_values))),
        residual_topk_p95=_round(float(np.percentile(top_residual_values, 95))),
        pasdf_residual_topk_overlap=_round(overlap),
        residual_topk_bbox_ratio=_round(_safe_ratio(_bbox_diagonal(top_points), sample_bbox_diag)),
        residual_topk_mean_pair_distance_ratio=_round(
            _safe_ratio(_mean_pair_distance(top_points), sample_bbox_diag)
        ),
    )


def build_tap1_region_explanation_records(
    *,
    score_root: str | Path,
    template_root: str | Path,
    sample_ids: Sequence[str],
    top_ratio: float,
    neighbor_radius_ratio: float,
) -> tuple[Tap1RegionExplanationRecord, ...]:
    """Build tap1 region explanation records from sample ids."""

    return tuple(
        compute_tap1_region_explanation_record(
            score_path=_find_sample_npz(score_root, sample_id),
            template_root=template_root,
            top_ratio=top_ratio,
            neighbor_radius_ratio=neighbor_radius_ratio,
        )
        for sample_id in sample_ids
    )


def build_cap3_residual_region_records(
    *,
    score_root: str | Path,
    template_root: str | Path,
    sample_ids: Sequence[str],
    top_ratio: float,
) -> tuple[Cap3ResidualRegionRecord, ...]:
    """Build cap3 residual region records from sample ids."""

    return tuple(
        compute_cap3_residual_region_record(
            score_path=_find_sample_npz(score_root, sample_id),
            template_root=template_root,
            top_ratio=top_ratio,
        )
        for sample_id in sample_ids
    )


def robust_minmax(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Normalize scores by 1st/99th percentile clipping."""

    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    if values.shape[0] == 0:
        raise ValueError("scores must contain at least one value")
    if not np.all(np.isfinite(values)):
        raise ValueError("scores must contain only finite values")
    lo = float(np.percentile(values, 1.0))
    hi = float(np.percentile(values, 99.0))
    if hi <= lo:
        return np.zeros_like(values, dtype=np.float64)
    return np.clip((values - lo) / (hi - lo), 0.0, 1.0)


def write_registration_diagnostics_csv(
    records: Sequence[RegistrationDiagnosticRecord],
    path: str | Path,
) -> Path:
    """Write registration diagnostics CSV."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRATION_FIELDS)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            writer.writerow(
                {field: ("" if row[field] is None else row[field]) for field in REGISTRATION_FIELDS}
            )
    return output


def write_hybrid_scores_csv(records: Sequence[HybridScoreRecord], path: str | Path) -> Path:
    """Write hybrid score CSV."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HYBRID_FIELDS)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            writer.writerow(
                {field: ("" if row[field] is None else row[field]) for field in HYBRID_FIELDS}
            )
    return output


def write_alpha_sweep_records_csv(
    records: Sequence[AlphaSweepRecord],
    path: str | Path,
) -> Path:
    """Write per-sample alpha sweep records."""

    return _write_alpha_csv(records, ALPHA_SWEEP_FIELDS, path)


def write_alpha_sweep_summary_csv(
    records: Sequence[AlphaSweepSummary],
    path: str | Path,
) -> Path:
    """Write alpha sweep summary records."""

    return _write_alpha_csv(records, ALPHA_SWEEP_SUMMARY_FIELDS, path)


def write_tap1_region_explanation_csv(
    records: Sequence[Tap1RegionExplanationRecord],
    path: str | Path,
) -> Path:
    """Write tap1 region explanation CSV."""

    return _write_dataclass_csv(records, TAP1_REGION_FIELDS, path)


def write_cap3_residual_region_csv(
    records: Sequence[Cap3ResidualRegionRecord],
    path: str | Path,
) -> Path:
    """Write cap3 residual region CSV."""

    return _write_dataclass_csv(records, CAP3_RESIDUAL_REGION_FIELDS, path)


def write_region_explanation_csv(
    *,
    tap1_records: Sequence[Tap1RegionExplanationRecord],
    cap3_records: Sequence[Cap3ResidualRegionRecord],
    path: str | Path,
) -> Path:
    """Write combined region explanation stage-record CSV."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGION_EXPLANATION_FIELDS)
        writer.writeheader()
        for tap1_record in tap1_records:
            row = _empty_region_row(record_type="tap1_region")
            row.update(_none_to_empty(asdict(tap1_record)))
            writer.writerow(row)
        for cap3_record in cap3_records:
            row = _empty_region_row(record_type="cap3_residual")
            row.update(_none_to_empty(asdict(cap3_record)))
            writer.writerow(row)
    return output


def render_alpha_sweep_markdown(
    summaries: Sequence[AlphaSweepSummary],
    *,
    title: str = "P6 Alpha Sweep Positive-Aware Summary",
) -> str:
    """Render alpha sweep summary Markdown."""

    lines = [
        f"# {title}",
        "",
        "## 判定口径",
        "",
        "- object score 越高表示越异常。",
        "- strict pass: `min anomaly hybrid object > max positive hybrid object` 且 "
        "`mean anomaly separation gain > 0`。",
        "- soft pass: `mean anomaly hybrid object > max positive hybrid object` 且 "
        "`mean anomaly separation gain > 0`。",
        "",
        "## Alpha Sweep",
        "",
        "| alpha | anomaly数 | positive数 | min anomaly obj | mean anomaly obj | "
        "max positive obj | mean sep gain | strict | soft |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for record in summaries:
        lines.append(
            f"| {record.alpha:.6f} | {record.anomaly_count} | {record.positive_count} | "
            f"{_fmt_optional(record.min_anomaly_hybrid_object)} | "
            f"{_fmt_optional(record.mean_anomaly_hybrid_object)} | "
            f"{_fmt_optional(record.max_positive_hybrid_object)} | "
            f"{_fmt_optional(record.mean_anomaly_separation_gain)} | "
            f"{record.strict_pass} | {record.soft_pass} |"
        )
    lines.extend(["", "## 结论", ""])
    strict_candidates = tuple(record for record in summaries if record.strict_pass)
    soft_candidates = tuple(record for record in summaries if record.soft_pass)
    if strict_candidates:
        best = max(
            strict_candidates,
            key=lambda record: record.mean_anomaly_separation_gain or float("-inf"),
        )
        lines.append(
            f"- 存在 strict pass alpha，当前最佳为 `{best.alpha:.6f}`，可进入更大代表类别验证。"
        )
    elif soft_candidates:
        best = max(
            soft_candidates,
            key=lambda record: record.mean_anomaly_separation_gain or float("-inf"),
        )
        lines.append(
            f"- 没有 strict pass，但存在 soft pass alpha `{best.alpha:.6f}`；"
            "后续需要人工复查 positive false-positive 风险。"
        )
    else:
        lines.append(
            "- 没有 alpha 同时满足 anomaly 分离提升和 positive-aware object 排序约束；"
            "当前 additive fusion 不建议扩大实验。"
        )
    lines.append("")
    return "\n".join(lines)


def render_region_explanation_markdown(
    *,
    tap1_records: Sequence[Tap1RegionExplanationRecord],
    cap3_records: Sequence[Cap3ResidualRegionRecord],
    title: str = "P6 Region Explanation",
) -> str:
    """Render Chinese region explanation diagnostics summary."""

    tap1_tuple = tuple(tap1_records)
    cap3_tuple = tuple(cap3_records)
    lines = [
        f"# {title}",
        "",
        "## 结论摘要",
        "",
        "- 本轮不再扩大 additive fusion，而是检查局部高分区域是否贴近 GT 或模板残差。",
        "- tap1 region-level explanation 用 top-k GT/GT-neighborhood 指标判断 "
        "geometry 是否更像局部解释信号。",
        "- cap3 residual region diagnostics 用 PASDF/residual top-k overlap 判断 "
        "false positive 是否来自模板错位。",
        "",
        "## tap1 region-level explanation",
        "",
        "| sample | label | GT点数 | radius | PASDF GT hit | Geometry GT hit | "
        "PASDF GT cover | Geometry GT cover | PASDF neighbor | Geometry neighbor | "
        "PASDF neigh enrich | Geometry neigh enrich |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for tap1_record in tap1_tuple:
        lines.append(
            f"| `{tap1_record.sample_id}` | {tap1_record.label} | "
            f"{tap1_record.gt_point_count} | "
            f"{tap1_record.neighbor_radius:.6f} | "
            f"{_fmt_optional(tap1_record.pasdf_topk_gt_hit_rate)} | "
            f"{_fmt_optional(tap1_record.geometry_topk_gt_hit_rate)} | "
            f"{_fmt_optional(tap1_record.pasdf_gt_coverage)} | "
            f"{_fmt_optional(tap1_record.geometry_gt_coverage)} | "
            f"{_fmt_optional(tap1_record.pasdf_neighbor_hit_rate)} | "
            f"{_fmt_optional(tap1_record.geometry_neighbor_hit_rate)} | "
            f"{_fmt_optional(tap1_record.pasdf_neighbor_enrichment)} | "
            f"{_fmt_optional(tap1_record.geometry_neighbor_enrichment)} |"
        )

    lines.extend(
        [
            "",
            "## cap3 residual region diagnostics",
            "",
            "| sample | label | PASDF object | residual topk mean | residual topk p95 | "
            "PASDF/residual overlap | residual bbox ratio | residual pair ratio |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for cap3_record in cap3_tuple:
        lines.append(
            f"| `{cap3_record.sample_id}` | {cap3_record.label} | "
            f"{cap3_record.pasdf_object_score:.6f} | "
            f"{cap3_record.residual_topk_mean:.6f} | "
            f"{cap3_record.residual_topk_p95:.6f} | "
            f"{cap3_record.pasdf_residual_topk_overlap:.6f} | "
            f"{cap3_record.residual_topk_bbox_ratio:.6f} | "
            f"{cap3_record.residual_topk_mean_pair_distance_ratio:.6f} |"
        )

    lines.extend(["", "## 下一步判断", ""])
    lines.extend(_interpret_region_explanation(tap1_tuple, cap3_tuple))
    lines.append("")
    return "\n".join(lines)


def render_p6_targeted_summary(
    registration_records: Sequence[RegistrationDiagnosticRecord],
    hybrid_records: Sequence[HybridScoreRecord],
    *,
    title: str = "P6 Targeted Diagnostics",
) -> str:
    """Render Chinese P6 targeted diagnostics summary."""

    registration_tuple = tuple(registration_records)
    hybrid_tuple = tuple(hybrid_records)
    lines = [
        f"# {title}",
        "",
        "## 结论摘要",
        "",
        "- object score 越高表示越异常。",
        "- cap3 registration/template mismatch 先看 sample/template distance residual。",
        "- tap1 PASDF + geometry fusion 先看 hybrid 是否提升 GT/background 分离，"
        "同时检查 positive object score 是否被抬高。",
        "",
        "## cap3 registration/template mismatch",
        "",
        "| sample | label | PASDF object | NN mean | NN p95 | NN p99 | NN top5 mean |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for registration_record in registration_tuple:
        lines.append(
            f"| `{registration_record.sample_id}` | {registration_record.label} | "
            f"{registration_record.pasdf_object_score:.6f} | "
            f"{registration_record.nn_distance_mean:.6f} | "
            f"{registration_record.nn_distance_p95:.6f} | "
            f"{registration_record.nn_distance_p99:.6f} | "
            f"{registration_record.nn_distance_top5_mean:.6f} |"
        )

    lines.extend(
        [
            "",
            "## tap1 PASDF + geometry fusion",
            "",
            "| sample | label | PASDF obj | Geometry obj | Hybrid obj | PASDF GT-bg | "
            "Geometry GT-bg | Hybrid GT-bg | SVG |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for hybrid_record in hybrid_tuple:
        lines.append(
            f"| `{hybrid_record.sample_id}` | {hybrid_record.label} | "
            f"{hybrid_record.pasdf_object_score:.6f} | "
            f"{hybrid_record.geometry_object_score:.6f} | "
            f"{hybrid_record.hybrid_object_score:.6f} | "
            f"{_fmt_optional(_pasdf_separation(hybrid_record))} | "
            f"{_fmt_optional(_geometry_separation(hybrid_record))} | "
            f"{_fmt_optional(_hybrid_separation(hybrid_record))} | "
            f"{_fmt_path(hybrid_record.svg_path)} |"
        )

    lines.extend(["", "## 下一步判断", ""])
    lines.extend(_interpret_p6_records(registration_tuple, hybrid_tuple))
    lines.append("")
    return "\n".join(lines)


def _interpret_p6_records(
    registration_records: Sequence[RegistrationDiagnosticRecord],
    hybrid_records: Sequence[HybridScoreRecord],
) -> list[str]:
    lines: list[str] = []
    positive_cap3 = tuple(record for record in registration_records if record.label == 0)
    if positive_cap3:
        top_positive = max(positive_cap3, key=lambda record: record.nn_distance_top5_mean)
        lines.append(
            f"- cap3 positive 中 `{top_positive.sample_id}` 的 NN top5 mean 最高，"
            "应优先和人工 overlay 结论对照，确认 false positive 是否来自局部模板错位。"
        )
    anomaly_hybrid = tuple(record for record in hybrid_records if record.label == 1)
    positive_hybrid = tuple(record for record in hybrid_records if record.label == 0)
    improved = tuple(record for record in anomaly_hybrid if _hybrid_improves_pasdf(record))
    lines.append(
        f"- tap1 anomaly 中 `{len(improved)}/{len(anomaly_hybrid)}` 个样本的 "
        "hybrid GT/background 分离高于 PASDF。"
    )
    if positive_hybrid:
        positive_mean = float(np.mean([record.hybrid_object_score for record in positive_hybrid]))
        lines.append(
            f"- tap1 positive 对照的 hybrid object score 均值为 `{positive_mean:.6f}`；"
            "后续扩大实验时必须继续监控 false positive 风险。"
        )
    return lines


def _find_sample_npz(score_root: str | Path, sample_id: str) -> Path:
    matches = sorted(Path(score_root).glob(f"*/points/{sample_id}.npz"))
    if not matches:
        raise FileNotFoundError(f"Could not find PASDF point-score NPZ for sample: {sample_id}")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise ValueError(f"Multiple PASDF point-score NPZ files matched {sample_id}: {joined}")
    return matches[0]


def build_registration_records(
    *,
    score_root: str | Path,
    template_root: str | Path,
    sample_ids: Sequence[str],
) -> tuple[RegistrationDiagnosticRecord, ...]:
    """Build registration diagnostic records from sample ids."""

    return tuple(
        compute_registration_diagnostic_record(
            score_path=_find_sample_npz(score_root, sample_id),
            template_root=template_root,
        )
        for sample_id in sample_ids
    )


def build_hybrid_records(
    *,
    score_root: str | Path,
    template_root: str | Path,
    sample_ids: Sequence[str],
    output_dir: str | Path,
    alpha: float,
    max_points: int,
    seed: int,
) -> tuple[HybridScoreRecord, ...]:
    """Build hybrid records from sample ids and write PASDF-vs-hybrid SVGs."""

    records: list[HybridScoreRecord] = []
    for sample_id in sample_ids:
        score_path = _find_sample_npz(score_root, sample_id)
        class_name = _class_name_from_score_path(score_path)
        svg_path = Path(output_dir) / "tap1_hybrid_scores" / class_name / f"{sample_id}_hybrid.svg"
        records.append(
            compute_hybrid_score_record(
                score_path=score_path,
                template_root=template_root,
                alpha=alpha,
                svg_path=svg_path,
                max_points=max_points,
                seed=seed,
            )
        )
    return tuple(records)


def _write_alpha_csv(
    records: Sequence[AlphaSweepRecord] | Sequence[AlphaSweepSummary],
    fields: tuple[str, ...],
    path: str | Path,
) -> Path:
    return _write_dataclass_csv(records, fields, path)


def _write_dataclass_csv(
    records: (
        Sequence[AlphaSweepRecord]
        | Sequence[AlphaSweepSummary]
        | Sequence[Tap1RegionExplanationRecord]
        | Sequence[Cap3ResidualRegionRecord]
    ),
    fields: tuple[str, ...],
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = _none_to_empty(asdict(record))
            writer.writerow({field: row[field] for field in fields})
    return output


def _empty_region_row(*, record_type: str) -> dict[str, object]:
    row: dict[str, object] = {field: "" for field in REGION_EXPLANATION_FIELDS}
    row["record_type"] = record_type
    return row


def _none_to_empty(row: dict[str, object]) -> dict[str, object]:
    return {key: ("" if value is None else value) for key, value in row.items()}


def _class_name_from_score_path(path: Path) -> str:
    return path.parent.parent.name


def _payload_label(payload: dict[str, np.ndarray[Any, np.dtype[Any]]]) -> int:
    return int(np.asarray(payload["label"]).reshape(-1)[0])


def _payload_object_score(payload: dict[str, np.ndarray[Any, np.dtype[Any]]]) -> float:
    return float(np.asarray(payload["object_score"]).reshape(-1)[0])


def _gt_background_means(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    mask: np.ndarray[Any, np.dtype[np.integer[Any]]],
) -> tuple[float | None, float | None]:
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    labels = np.asarray(mask, dtype=np.int64).reshape(-1)
    gt_mask = labels.astype(bool)
    bg_mask = ~gt_mask
    gt_mean = float(np.mean(values[gt_mask])) if np.any(gt_mask) else None
    background_mean = float(np.mean(values[bg_mask])) if np.any(bg_mask) else None
    return gt_mean, background_mean


def _separation(gt_mean: float | None, background_mean: float | None) -> float | None:
    if gt_mean is None or background_mean is None:
        return None
    return gt_mean - background_mean


def _pasdf_separation(record: HybridScoreRecord) -> float | None:
    return _separation(record.pasdf_gt_mean, record.pasdf_background_mean)


def _geometry_separation(record: HybridScoreRecord) -> float | None:
    return _separation(record.geometry_gt_mean, record.geometry_background_mean)


def _hybrid_separation(record: HybridScoreRecord) -> float | None:
    return _separation(record.hybrid_gt_mean, record.hybrid_background_mean)


def _hybrid_improves_pasdf(record: HybridScoreRecord) -> bool:
    pasdf_separation = _pasdf_separation(record)
    hybrid_separation = _hybrid_separation(record)
    if pasdf_separation is None or hybrid_separation is None:
        return False
    return hybrid_separation > pasdf_separation


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _interpret_region_explanation(
    tap1_records: Sequence[Tap1RegionExplanationRecord],
    cap3_records: Sequence[Cap3ResidualRegionRecord],
) -> list[str]:
    lines: list[str] = []
    if tap1_records:
        better_neighbor = tuple(
            record
            for record in tap1_records
            if _optional_greater(
                record.geometry_neighbor_enrichment,
                record.pasdf_neighbor_enrichment,
            )
        )
        if better_neighbor:
            lines.append(
                f"- tap1 中 `{len(better_neighbor)}/{len(tap1_records)}` 个样本的 geometry "
                "GT-neighborhood enrichment 高于 PASDF；这些样本可作为后续非加性 "
                "region gating 候选。"
            )
        else:
            lines.append(
                f"- tap1 中 `0/{len(tap1_records)}` 个样本的 geometry GT-neighborhood "
                "enrichment 高于 PASDF；当前结果不支持把 geometry 作为主局部解释信号。"
            )
    if cap3_records:
        high_overlap = tuple(
            record for record in cap3_records if record.pasdf_residual_topk_overlap >= 0.5
        )
        lines.append(
            f"- cap3 中 `{len(high_overlap)}/{len(cap3_records)}` 个样本的 PASDF/residual "
            "top-k overlap 不低于 0.5；positive 样本若 overlap 高，应继续优先排查模板错位。"
        )
    return lines


def _optional_greater(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return False
    return left > right


def _as_score_array(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    if values.shape[0] == 0:
        raise ValueError("scores must contain at least one value")
    if not np.all(np.isfinite(values)):
        raise ValueError("scores must contain only finite values")
    return values


def _as_points(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float64]]:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"points must have shape (N, 3), got {array.shape}")
    if array.shape[0] == 0:
        raise ValueError("points must contain at least one point")
    if not np.all(np.isfinite(array)):
        raise ValueError("points must contain only finite values")
    return array


def _as_mask(
    mask: np.ndarray[Any, np.dtype[np.integer[Any]]],
    *,
    expected_count: int,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    labels = np.asarray(mask, dtype=np.int64).reshape(-1)
    if labels.shape[0] != expected_count:
        raise ValueError("mask length must match points")
    return labels


def _neighbor_radius(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    ratio: float,
) -> float:
    return _bbox_diagonal(points) * ratio


def _gt_neighbor_mask(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    gt_mask: np.ndarray[Any, np.dtype[np.bool_]],
    *,
    radius: float,
) -> np.ndarray[Any, np.dtype[np.bool_]]:
    if not np.any(gt_mask):
        return np.zeros(points.shape[0], dtype=np.bool_)
    gt_points = points[gt_mask]
    distances = nearest_neighbors(points, gt_points, k=1).distances[:, 0]
    return np.asarray(distances <= radius, dtype=np.bool_)


def _bbox_diagonal(points: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    points_array = _as_points(points)
    min_xyz = np.min(points_array, axis=0)
    max_xyz = np.max(points_array, axis=0)
    return float(np.linalg.norm(max_xyz - min_xyz))


def _mean_pair_distance(points: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    points_array = _as_points(points)
    if points_array.shape[0] < 2:
        return 0.0
    distances: list[float] = []
    for row_index in range(points_array.shape[0] - 1):
        deltas = points_array[row_index + 1 :] - points_array[row_index]
        distances.extend(float(value) for value in np.linalg.norm(deltas, axis=1))
    return float(np.mean(np.asarray(distances, dtype=np.float64)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 1e-12:
        return 0.0
    return numerator / denominator


def _round(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round(value)


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _fmt_path(value: str | None) -> str:
    return "NA" if value is None else f"`{value}`"
