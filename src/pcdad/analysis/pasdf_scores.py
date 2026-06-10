"""PASDF per-sample score export summaries."""

from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PasdfSampleScore:
    """Summary statistics for one PASDF-scored test sample."""

    class_name: str
    sample_id: str
    sample_path: str
    label: int
    point_count: int
    object_score: float
    topk_score: float
    score_mean: float
    score_p95: float
    score_max: float
    gt_point_count: int
    gt_point_ratio: float
    gt_score_mean: float | None
    background_score_mean: float | None
    point_score_path: str | None = None


SAMPLE_SCORE_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "sample_path",
    "label",
    "point_count",
    "object_score",
    "topk_score",
    "score_mean",
    "score_p95",
    "score_max",
    "gt_point_count",
    "gt_point_ratio",
    "gt_score_mean",
    "background_score_mean",
    "point_score_path",
)


def summarize_point_scores(
    *,
    class_name: str,
    sample_id: str,
    sample_path: str,
    point_scores: NDArray[np.floating[Any]],
    mask: NDArray[np.floating[Any]],
    label: int,
    top_k: int,
    point_score_path: str | None = None,
) -> PasdfSampleScore:
    """Compute stable sample-level summary values from PASDF point scores."""

    scores = np.asarray(point_scores, dtype=np.float64).reshape(-1)
    labels = np.asarray(mask).reshape(-1)
    if scores.size == 0:
        raise ValueError("At least one point score is required")
    if labels.size != scores.size:
        raise ValueError("point_scores and mask must have the same length")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if not np.all(np.isfinite(scores)):
        raise ValueError("point_scores must contain only finite values")

    clipped_top_k = min(top_k, scores.size)
    topk_score = float(np.mean(np.partition(scores, -clipped_top_k)[-clipped_top_k:]))
    gt_mask = labels.astype(bool)
    bg_mask = ~gt_mask

    gt_score_mean = float(np.mean(scores[gt_mask])) if np.any(gt_mask) else None
    background_score_mean = float(np.mean(scores[bg_mask])) if np.any(bg_mask) else None
    gt_point_count = int(np.count_nonzero(gt_mask))

    return PasdfSampleScore(
        class_name=class_name,
        sample_id=sample_id,
        sample_path=sample_path,
        label=int(label),
        point_count=int(scores.size),
        object_score=_round_score(topk_score),
        topk_score=_round_score(topk_score),
        score_mean=_round_score(float(np.mean(scores))),
        score_p95=_round_score(float(np.percentile(scores, 95))),
        score_max=_round_score(float(np.max(scores))),
        gt_point_count=gt_point_count,
        gt_point_ratio=_round_score(gt_point_count / float(scores.size)),
        gt_score_mean=_round_optional(gt_score_mean),
        background_score_mean=_round_optional(background_score_mean),
        point_score_path=point_score_path,
    )


def write_sample_scores_csv(records: Sequence[PasdfSampleScore], path: str | Path) -> Path:
    """Write PASDF sample score records with a stable column order."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SAMPLE_SCORE_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(_csv_row(record))
    return output


def render_score_export_markdown(
    records: Sequence[PasdfSampleScore],
    *,
    title: str = "P5 PASDF 样本级分数导出摘要",
) -> str:
    """Render a Chinese Markdown summary for P5 score export stage records."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("At least one PASDF sample score is required")

    anomaly_count = sum(1 for record in record_tuple if record.label == 1)
    positive_count = len(record_tuple) - anomaly_count
    class_names = tuple(sorted({record.class_name for record in record_tuple}))
    lines = [
        f"# {title}",
        "",
        "## 记录范围",
        "",
        f"- 样本数：{len(record_tuple)}",
        f"- 类别数：{len(class_names)}",
        f"- 异常样本数：{anomaly_count}",
        f"- Positive 样本数：{positive_count}",
        f"- 类别：{', '.join(f'`{name}`' for name in class_names)}",
        "",
        "## 类别摘要",
        "",
    ]
    lines.extend(_format_class_summary_table(record_tuple))
    lines.extend(["", "## 优先复查样本", ""])
    priority_rows = _select_priority_samples(record_tuple)
    lines.extend(_format_priority_table(priority_rows))
    lines.append("")
    return "\n".join(lines)


def _round_score(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round_score(value)


def _csv_row(record: PasdfSampleScore) -> dict[str, object]:
    row = asdict(record)
    return {field: ("" if row[field] is None else row[field]) for field in SAMPLE_SCORE_FIELDS}


def _format_class_summary_table(records: Sequence[PasdfSampleScore]) -> list[str]:
    lines = [
        "| 类别 | 样本数 | 异常数 | Positive 数 | Object 均值 | 异常 Object 均值 | "
        "Positive Object 均值 | GT 内均值 | 背景均值 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for class_name in sorted({record.class_name for record in records}):
        class_records = tuple(record for record in records if record.class_name == class_name)
        anomaly_records = tuple(record for record in class_records if record.label == 1)
        positive_records = tuple(record for record in class_records if record.label == 0)
        gt_means = tuple(
            record.gt_score_mean for record in class_records if record.gt_score_mean is not None
        )
        bg_means = tuple(
            record.background_score_mean
            for record in class_records
            if record.background_score_mean is not None
        )
        lines.append(
            f"| {class_name} | {len(class_records)} | {len(anomaly_records)} | "
            f"{len(positive_records)} | {_fmt_mean(_mean_object(class_records))} | "
            f"{_fmt_mean(_mean_object(anomaly_records))} | "
            f"{_fmt_mean(_mean_object(positive_records))} | {_fmt_mean(_mean(gt_means))} | "
            f"{_fmt_mean(_mean(bg_means))} |"
        )
    return lines


def _format_priority_table(records: Sequence[tuple[PasdfSampleScore, str]]) -> list[str]:
    lines = [
        "| 类别 | 样本 | Label | Object Score | GT 内均值 | 背景均值 | 原因 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for record, reason in records:
        lines.append(
            f"| {record.class_name} | `{record.sample_id}` | {record.label} | "
            f"{record.object_score:.6f} | {_fmt_optional(record.gt_score_mean)} | "
            f"{_fmt_optional(record.background_score_mean)} | {reason} |"
        )
    return lines


def _select_priority_samples(
    records: Sequence[PasdfSampleScore],
    *,
    limit: int = 10,
) -> tuple[tuple[PasdfSampleScore, str], ...]:
    candidates: list[tuple[float, PasdfSampleScore, str]] = []
    for record in records:
        if (
            record.label == 1
            and record.gt_score_mean is not None
            and record.background_score_mean is not None
            and record.gt_score_mean < record.background_score_mean
        ):
            gap = record.background_score_mean - record.gt_score_mean
            candidates.append((gap, record, "GT 内均值低于背景均值"))
        elif record.label == 0:
            candidates.append((record.object_score, record, "Positive object score 偏高"))

    selected = sorted(
        candidates,
        key=lambda item: (-item[0], item[1].class_name, item[1].sample_id),
    )[:limit]
    return tuple((record, reason) for _, record, reason in selected)


def _mean_object(records: Sequence[PasdfSampleScore]) -> float | None:
    return _mean(tuple(record.object_score for record in records))


def _mean(values: Sequence[float | None]) -> float | None:
    finite_values = tuple(float(value) for value in values if value is not None)
    if not finite_values:
        return None
    return math.fsum(finite_values) / len(finite_values)


def _fmt_mean(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"
