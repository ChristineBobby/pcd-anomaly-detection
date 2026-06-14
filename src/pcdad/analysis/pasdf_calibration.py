"""PASDF top-k calibration diagnostics."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.analysis.pasdf_case_study import load_pasdf_point_score
from pcdad.scoring.aggregate import topk_mean


@dataclass(frozen=True)
class PasdfTopKCalibrationRecord:
    """PASDF score diagnostics for one sample under one top-k ratio."""

    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    gt_point_ratio: float
    top_ratio: float
    stored_object_score: float
    topk_score: float
    score_mean: float
    score_p95: float
    gt_score_mean: float | None
    background_score_mean: float | None
    gt_background_gap: float | None
    topk_gt_hit_rate: float | None
    gt_coverage: float | None
    gt_enrichment: float | None


@dataclass(frozen=True)
class PasdfCalibrationSummary:
    """Class-level PASDF calibration summary under one top-k ratio."""

    class_name: str
    top_ratio: float
    sample_count: int
    anomaly_count: int
    positive_count: int
    mean_anomaly_topk: float | None
    mean_positive_topk: float | None
    min_anomaly_topk: float | None
    max_positive_topk: float | None
    strict_object_pass: bool
    soft_object_pass: bool
    mean_gt_background_gap: float | None
    mean_topk_gt_hit_rate: float | None
    mean_gt_coverage: float | None
    mean_gt_enrichment: float | None
    weak_localization_count: int


CALIBRATION_RECORD_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "gt_point_ratio",
    "top_ratio",
    "stored_object_score",
    "topk_score",
    "score_mean",
    "score_p95",
    "gt_score_mean",
    "background_score_mean",
    "gt_background_gap",
    "topk_gt_hit_rate",
    "gt_coverage",
    "gt_enrichment",
)

CALIBRATION_SUMMARY_FIELDS: tuple[str, ...] = (
    "class_name",
    "top_ratio",
    "sample_count",
    "anomaly_count",
    "positive_count",
    "mean_anomaly_topk",
    "mean_positive_topk",
    "min_anomaly_topk",
    "max_positive_topk",
    "strict_object_pass",
    "soft_object_pass",
    "mean_gt_background_gap",
    "mean_topk_gt_hit_rate",
    "mean_gt_coverage",
    "mean_gt_enrichment",
    "weak_localization_count",
)


def compute_pasdf_topk_calibration_record(
    *,
    score_path: str | Path,
    top_ratio: float,
) -> PasdfTopKCalibrationRecord:
    """Compute PASDF top-k calibration diagnostics for one NPZ score file."""

    _validate_top_ratio(top_ratio)
    path = Path(score_path)
    payload = load_pasdf_point_score(path)
    scores = np.asarray(payload["point_scores"], dtype=np.float64).reshape(-1)
    mask = np.asarray(payload["mask"], dtype=np.int64).reshape(-1)
    gt_mask = mask.astype(bool)
    bg_mask = ~gt_mask
    top_indices = _topk_indices(scores, top_ratio=top_ratio)
    top_count = int(top_indices.shape[0])
    gt_point_count = int(np.count_nonzero(gt_mask))
    gt_hit_count = int(np.count_nonzero(gt_mask[top_indices]))

    gt_score_mean = float(np.mean(scores[gt_mask])) if np.any(gt_mask) else None
    background_score_mean = float(np.mean(scores[bg_mask])) if np.any(bg_mask) else None
    gt_background_gap = (
        None
        if gt_score_mean is None or background_score_mean is None
        else gt_score_mean - background_score_mean
    )
    gt_point_ratio = gt_point_count / float(scores.shape[0])
    topk_gt_hit_rate = None if gt_point_count == 0 else gt_hit_count / float(top_count)
    gt_coverage = None if gt_point_count == 0 else gt_hit_count / float(gt_point_count)
    gt_enrichment = (
        None
        if topk_gt_hit_rate is None or gt_point_ratio <= 0.0
        else topk_gt_hit_rate / gt_point_ratio
    )

    return PasdfTopKCalibrationRecord(
        class_name=_class_name_from_score_path(path),
        sample_id=path.stem,
        label=int(np.asarray(payload["label"]).reshape(-1)[0]),
        point_count=int(scores.shape[0]),
        gt_point_count=gt_point_count,
        gt_point_ratio=_round(gt_point_ratio),
        top_ratio=_round(top_ratio),
        stored_object_score=_round(float(np.asarray(payload["object_score"]).reshape(-1)[0])),
        topk_score=_round(topk_mean(scores, ratio=top_ratio)),
        score_mean=_round(float(np.mean(scores))),
        score_p95=_round(float(np.percentile(scores, 95))),
        gt_score_mean=_round_optional(gt_score_mean),
        background_score_mean=_round_optional(background_score_mean),
        gt_background_gap=_round_optional(gt_background_gap),
        topk_gt_hit_rate=_round_optional(topk_gt_hit_rate),
        gt_coverage=_round_optional(gt_coverage),
        gt_enrichment=_round_optional(gt_enrichment),
    )


def build_pasdf_topk_calibration_records(
    *,
    score_paths: Sequence[str | Path],
    top_ratios: Sequence[float],
) -> tuple[PasdfTopKCalibrationRecord, ...]:
    """Build calibration records for all score files and top-k ratios."""

    if not score_paths:
        raise ValueError("At least one score_path is required")
    if not top_ratios:
        raise ValueError("At least one top_ratio is required")
    for top_ratio in top_ratios:
        _validate_top_ratio(top_ratio)

    records: list[PasdfTopKCalibrationRecord] = []
    for score_path in sorted(Path(path) for path in score_paths):
        for top_ratio in top_ratios:
            records.append(
                compute_pasdf_topk_calibration_record(
                    score_path=score_path,
                    top_ratio=top_ratio,
                )
            )
    return tuple(records)


def summarize_pasdf_calibration(
    records: Sequence[PasdfTopKCalibrationRecord],
) -> tuple[PasdfCalibrationSummary, ...]:
    """Summarize PASDF calibration records by class and top-k ratio."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("At least one calibration record is required")

    summaries: list[PasdfCalibrationSummary] = []
    keys = sorted({(record.class_name, record.top_ratio) for record in record_tuple})
    for class_name, top_ratio in keys:
        group = tuple(
            record
            for record in record_tuple
            if record.class_name == class_name and record.top_ratio == top_ratio
        )
        anomaly_records = tuple(record for record in group if record.label == 1)
        positive_records = tuple(record for record in group if record.label == 0)
        anomaly_topk = tuple(record.topk_score for record in anomaly_records)
        positive_topk = tuple(record.topk_score for record in positive_records)
        min_anomaly = min(anomaly_topk) if anomaly_topk else None
        max_positive = max(positive_topk) if positive_topk else None
        mean_anomaly = _mean(anomaly_topk)
        mean_positive = _mean(positive_topk)
        strict_pass = (
            min_anomaly is not None and max_positive is not None and min_anomaly > max_positive
        )
        soft_pass = (
            mean_anomaly is not None and max_positive is not None and mean_anomaly > max_positive
        )
        summaries.append(
            PasdfCalibrationSummary(
                class_name=class_name,
                top_ratio=top_ratio,
                sample_count=len(group),
                anomaly_count=len(anomaly_records),
                positive_count=len(positive_records),
                mean_anomaly_topk=_round_optional(mean_anomaly),
                mean_positive_topk=_round_optional(mean_positive),
                min_anomaly_topk=_round_optional(min_anomaly),
                max_positive_topk=_round_optional(max_positive),
                strict_object_pass=strict_pass,
                soft_object_pass=soft_pass,
                mean_gt_background_gap=_round_optional(
                    _mean_optional(record.gt_background_gap for record in anomaly_records)
                ),
                mean_topk_gt_hit_rate=_round_optional(
                    _mean_optional(record.topk_gt_hit_rate for record in anomaly_records)
                ),
                mean_gt_coverage=_round_optional(
                    _mean_optional(record.gt_coverage for record in anomaly_records)
                ),
                mean_gt_enrichment=_round_optional(
                    _mean_optional(record.gt_enrichment for record in anomaly_records)
                ),
                weak_localization_count=sum(
                    1 for record in anomaly_records if _is_weak_localization(record)
                ),
            )
        )
    return tuple(summaries)


def write_pasdf_calibration_records_csv(
    records: Sequence[PasdfTopKCalibrationRecord],
    path: str | Path,
) -> Path:
    """Write per-sample PASDF calibration records."""

    return _write_dataclass_csv(records, CALIBRATION_RECORD_FIELDS, path)


def write_pasdf_calibration_summary_csv(
    records: Sequence[PasdfCalibrationSummary],
    path: str | Path,
) -> Path:
    """Write class-level PASDF calibration summaries."""

    return _write_dataclass_csv(records, CALIBRATION_SUMMARY_FIELDS, path)


def render_pasdf_calibration_markdown(
    *,
    records: Sequence[PasdfTopKCalibrationRecord],
    summaries: Sequence[PasdfCalibrationSummary],
    title: str = "P6 PASDF Top-k Calibration",
) -> str:
    """Render a Chinese Markdown stage record for PASDF top-k calibration."""

    record_tuple = tuple(records)
    summary_tuple = tuple(summaries)
    if not record_tuple:
        raise ValueError("At least one calibration record is required")
    if not summary_tuple:
        raise ValueError("At least one calibration summary is required")

    lines = [
        f"# {title}",
        "",
        "## 结论摘要",
        "",
        "- object score 越高表示越异常。",
        "- 本轮只检查 PASDF 自身的 top-k 聚合、score 幅度和 GT 局部命中，"
        "不继续 additive geometry fusion。",
    ]
    lines.extend(_interpret_summaries(summary_tuple))
    lines.extend(
        [
            "",
            "## 类别与 top-k ratio 汇总",
            "",
            "| 类别 | top-k ratio | 样本数 | anomaly | positive | mean anomaly topk | "
            "max positive topk | strict | soft | mean GT-bg | mean topk GT hit | "
            "mean GT cover | mean GT enrich | weak localization |",
            "|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in summary_tuple:
        lines.append(
            f"| {summary.class_name} | {summary.top_ratio:.6f} | {summary.sample_count} | "
            f"{summary.anomaly_count} | {summary.positive_count} | "
            f"{_fmt_optional(summary.mean_anomaly_topk)} | "
            f"{_fmt_optional(summary.max_positive_topk)} | {summary.strict_object_pass} | "
            f"{summary.soft_object_pass} | {_fmt_optional(summary.mean_gt_background_gap)} | "
            f"{_fmt_optional(summary.mean_topk_gt_hit_rate)} | "
            f"{_fmt_optional(summary.mean_gt_coverage)} | "
            f"{_fmt_optional(summary.mean_gt_enrichment)} | "
            f"{summary.weak_localization_count} |"
        )

    lines.extend(["", "## 优先复查样本", ""])
    lines.extend(_format_priority_records(record_tuple))
    lines.extend(["", "## 阶段解读", ""])
    lines.extend(_format_stage_interpretation(summary_tuple))
    lines.extend(["", "## 下一步建议", ""])
    lines.extend(_format_next_actions(summary_tuple))
    lines.append("")
    return "\n".join(lines)


def _format_priority_records(records: Sequence[PasdfTopKCalibrationRecord]) -> list[str]:
    priority = _select_priority_records(records)
    lines = [
        "| 类别 | 样本 | label | top-k ratio | topk score | GT-bg | GT enrich | 原因 |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for record, reason in priority:
        lines.append(
            f"| {record.class_name} | `{record.sample_id}` | {record.label} | "
            f"{record.top_ratio:.6f} | {record.topk_score:.6f} | "
            f"{_fmt_optional(record.gt_background_gap)} | "
            f"{_fmt_optional(record.gt_enrichment)} | {reason} |"
        )
    return lines


def _select_priority_records(
    records: Sequence[PasdfTopKCalibrationRecord],
    *,
    limit: int = 12,
) -> tuple[tuple[PasdfTopKCalibrationRecord, str], ...]:
    candidates: list[tuple[float, PasdfTopKCalibrationRecord, str]] = []
    seen: set[tuple[str, str, float]] = set()
    for record in records:
        key = (record.class_name, record.sample_id, record.top_ratio)
        if key in seen:
            continue
        seen.add(key)
        if record.label == 0:
            candidates.append((record.topk_score, record, "positive top-k score 偏高"))
        elif _is_weak_localization(record):
            severity = 0.0
            if record.gt_background_gap is not None:
                severity += max(0.0, -record.gt_background_gap)
            if record.gt_enrichment is not None:
                severity += max(0.0, 1.0 - record.gt_enrichment)
            candidates.append((severity, record, "weak localization"))
    selected = sorted(
        candidates,
        key=lambda item: (-item[0], item[1].class_name, item[1].sample_id, item[1].top_ratio),
    )[:limit]
    return tuple((record, reason) for _, record, reason in selected)


def _interpret_summaries(summaries: Sequence[PasdfCalibrationSummary]) -> list[str]:
    lines: list[str] = []
    for class_name in sorted({summary.class_name for summary in summaries}):
        class_summaries = tuple(
            summary for summary in summaries if summary.class_name == class_name
        )
        strict = tuple(summary for summary in class_summaries if summary.strict_object_pass)
        soft = tuple(summary for summary in class_summaries if summary.soft_object_pass)
        if strict:
            ratios = ", ".join(f"{summary.top_ratio:.2%}" for summary in strict)
            lines.append(f"- `{class_name}` 存在 strict object pass ratio：{ratios}。")
        elif soft:
            ratios = ", ".join(f"{summary.top_ratio:.2%}" for summary in soft)
            lines.append(
                f"- `{class_name}` 只有 soft object pass ratio：{ratios}，"
                "需要复查 positive 边界。"
            )
        else:
            lines.append(f"- `{class_name}` 没有通过 object 排序约束，" "优先排查校准或模板问题。")

        weakest = max(class_summaries, key=lambda summary: summary.weak_localization_count)
        if weakest.weak_localization_count > 0:
            lines.append(
                f"- `{class_name}` 在 top-k ratio `{weakest.top_ratio:.2%}` 下有 "
                f"`{weakest.weak_localization_count}` 个 anomaly 呈现 weak localization。"
            )
    return lines


def _format_stage_interpretation(summaries: Sequence[PasdfCalibrationSummary]) -> list[str]:
    lines: list[str] = []
    for class_name in sorted({summary.class_name for summary in summaries}):
        class_summaries = tuple(
            summary for summary in summaries if summary.class_name == class_name
        )
        best_ratio = max(
            class_summaries,
            key=lambda summary: (
                float(summary.soft_object_pass),
                summary.mean_anomaly_topk or float("-inf"),
                -(summary.max_positive_topk or float("inf")),
            ),
        )
        lines.append(
            f"- `{class_name}`：最佳候选 top-k ratio 为 `{best_ratio.top_ratio:.2%}`。"
            f"mean anomaly topk 为 `{_fmt_optional(best_ratio.mean_anomaly_topk)}`，"
            f"max positive topk 为 `{_fmt_optional(best_ratio.max_positive_topk)}`，"
            f"strict={best_ratio.strict_object_pass}，soft={best_ratio.soft_object_pass}。"
        )
    return lines


def _format_next_actions(summaries: Sequence[PasdfCalibrationSummary]) -> list[str]:
    class_names = sorted({summary.class_name for summary in summaries})
    lines: list[str] = []
    if "cap3" in class_names:
        lines.append(
            "- `cap3`：top-k ratio 调整没有解决 object 排序问题，继续优先做 "
            "registration/template robustness，而不是调 PASDF 聚合超参。"
        )
    if "tap1" in class_names:
        lines.append(
            "- `tap1`：PASDF-only 聚合有稳定 soft pass，但没有 strict pass；后续应检查 "
            "positive 边界样本和低分 anomaly，暂不恢复 additive geometry fusion。"
        )
    if "helmet1" in class_names:
        lines.append(
            "- `helmet1`：mean anomaly 高于 mean positive，但最高 positive 仍压住排序边界；"
            "下一步应做点级定位失败解释和 positive 边界复查。"
        )
    if not lines:
        lines.append("- 继续按类别查看 strict/soft pass 与 weak localization 样本。")
    return lines


def _write_dataclass_csv(
    records: Sequence[PasdfTopKCalibrationRecord] | Sequence[PasdfCalibrationSummary],
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


def _topk_indices(
    scores: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    top_ratio: float,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    _validate_top_ratio(top_ratio)
    if values.shape[0] == 0:
        raise ValueError("scores must contain at least one value")
    if not np.all(np.isfinite(values)):
        raise ValueError("scores must contain only finite values")
    count = max(1, int(math.ceil(values.shape[0] * top_ratio)))
    return np.asarray(np.argsort(values, kind="mergesort")[-count:], dtype=np.int64)


def _validate_top_ratio(top_ratio: float) -> None:
    if top_ratio <= 0.0 or top_ratio > 1.0:
        raise ValueError("top_ratio must be in (0, 1]")


def _class_name_from_score_path(path: Path) -> str:
    return path.parent.parent.name


def _is_weak_localization(record: PasdfTopKCalibrationRecord) -> bool:
    return (record.gt_enrichment is not None and record.gt_enrichment <= 1.0) or (
        record.gt_background_gap is not None and record.gt_background_gap <= 0.0
    )


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return math.fsum(float(value) for value in values) / len(values)


def _mean_optional(values: Iterable[float | None]) -> float | None:
    finite_values = tuple(float(value) for value in values if value is not None)
    if not finite_values:
        return None
    return math.fsum(finite_values) / len(finite_values)


def _round(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round(value)


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _none_to_empty(row: dict[str, object]) -> dict[str, object]:
    return {key: ("" if value is None else value) for key, value in row.items()}
