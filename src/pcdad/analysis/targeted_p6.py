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


def _round(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round(value)


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _fmt_path(value: str | None) -> str:
    return "NA" if value is None else f"`{value}`"
