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
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            writer.writerow({field: ("" if row[field] is None else row[field]) for field in fields})
    return output


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


def _round(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round(value)


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _fmt_path(value: str | None) -> str:
    return "NA" if value is None else f"`{value}`"
