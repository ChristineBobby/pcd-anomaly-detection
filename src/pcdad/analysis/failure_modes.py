"""P6 failure-mode closure summaries."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from pcdad.analysis.pasdf_calibration import PasdfCalibrationSummary, PasdfTopKCalibrationRecord
from pcdad.analysis.targeted_p6 import Cap3ResidualRegionRecord


@dataclass(frozen=True)
class FailureModeClosureRecord:
    """Class-level failure-mode closure for report handoff."""

    class_name: str
    primary_failure_mode: str
    object_boundary_status: str
    localization_status: str
    evidence: str
    next_action: str


@dataclass(frozen=True)
class BoundarySampleRecord:
    """Object-boundary samples for one class and top-k ratio."""

    class_name: str
    top_ratio: float
    highest_positive_sample: str | None
    highest_positive_score: float | None
    lowest_anomaly_sample: str | None
    lowest_anomaly_score: float | None
    boundary_margin: float | None


@dataclass(frozen=True)
class WeakLocalizationRecord:
    """One anomaly sample with weak top-k localization evidence."""

    class_name: str
    sample_id: str
    top_ratio: float
    gt_background_gap: float | None
    gt_enrichment: float | None
    reason: str


@dataclass(frozen=True)
class Cap3TemplateMismatchRecord:
    """Cap3 PASDF/template residual overlap closure evidence."""

    sample_id: str
    label: int
    pasdf_object_score: float
    residual_topk_mean: float
    pasdf_residual_topk_overlap: float
    residual_topk_bbox_ratio: float
    residual_topk_mean_pair_distance_ratio: float
    closure_label: str


FAILURE_MODE_CLOSURE_FIELDS: tuple[str, ...] = (
    "class_name",
    "primary_failure_mode",
    "object_boundary_status",
    "localization_status",
    "evidence",
    "next_action",
)

BOUNDARY_FIELDS: tuple[str, ...] = (
    "record_type",
    "class_name",
    "top_ratio",
    "highest_positive_sample",
    "highest_positive_score",
    "lowest_anomaly_sample",
    "lowest_anomaly_score",
    "boundary_margin",
)

WEAK_LOCALIZATION_FIELDS: tuple[str, ...] = (
    "record_type",
    "class_name",
    "sample_id",
    "top_ratio",
    "gt_background_gap",
    "gt_enrichment",
    "reason",
)

CAP3_TEMPLATE_FIELDS: tuple[str, ...] = (
    "record_type",
    "sample_id",
    "label",
    "pasdf_object_score",
    "residual_topk_mean",
    "pasdf_residual_topk_overlap",
    "residual_topk_bbox_ratio",
    "residual_topk_mean_pair_distance_ratio",
    "closure_label",
)

COMBINED_FIELDS: tuple[str, ...] = (
    "record_type",
    "class_name",
    "sample_id",
    "top_ratio",
    "primary_failure_mode",
    "object_boundary_status",
    "localization_status",
    "evidence",
    "next_action",
    "highest_positive_sample",
    "highest_positive_score",
    "lowest_anomaly_sample",
    "lowest_anomaly_score",
    "boundary_margin",
    "gt_background_gap",
    "gt_enrichment",
    "reason",
    "label",
    "pasdf_object_score",
    "residual_topk_mean",
    "pasdf_residual_topk_overlap",
    "residual_topk_bbox_ratio",
    "residual_topk_mean_pair_distance_ratio",
    "closure_label",
)


def build_boundary_record(
    records: Sequence[PasdfTopKCalibrationRecord],
    *,
    class_name: str,
    top_ratio: float,
) -> BoundarySampleRecord:
    """Find highest-positive and lowest-anomaly boundary samples."""

    group = tuple(
        record
        for record in records
        if record.class_name == class_name and record.top_ratio == top_ratio
    )
    positives = tuple(record for record in group if record.label == 0)
    anomalies = tuple(record for record in group if record.label == 1)
    highest_positive = max(positives, key=lambda record: record.topk_score, default=None)
    lowest_anomaly = min(anomalies, key=lambda record: record.topk_score, default=None)
    margin = (
        None
        if highest_positive is None or lowest_anomaly is None
        else lowest_anomaly.topk_score - highest_positive.topk_score
    )
    return BoundarySampleRecord(
        class_name=class_name,
        top_ratio=top_ratio,
        highest_positive_sample=None if highest_positive is None else highest_positive.sample_id,
        highest_positive_score=None if highest_positive is None else highest_positive.topk_score,
        lowest_anomaly_sample=None if lowest_anomaly is None else lowest_anomaly.sample_id,
        lowest_anomaly_score=None if lowest_anomaly is None else lowest_anomaly.topk_score,
        boundary_margin=_round_optional(margin),
    )


def build_weak_localization_records(
    records: Sequence[PasdfTopKCalibrationRecord],
    *,
    class_name: str,
    top_ratio: float,
) -> tuple[WeakLocalizationRecord, ...]:
    """Return anomaly samples with weak localization evidence."""

    weak_records: list[WeakLocalizationRecord] = []
    for record in records:
        if record.class_name != class_name or record.top_ratio != top_ratio or record.label != 1:
            continue
        reasons = _weak_reasons(record)
        if not reasons:
            continue
        weak_records.append(
            WeakLocalizationRecord(
                class_name=class_name,
                sample_id=record.sample_id,
                top_ratio=top_ratio,
                gt_background_gap=record.gt_background_gap,
                gt_enrichment=record.gt_enrichment,
                reason=";".join(reasons),
            )
        )
    return tuple(
        sorted(
            weak_records,
            key=lambda record: (
                record.class_name,
                record.sample_id,
                record.top_ratio,
            ),
        )
    )


def classify_cap3_template_mismatch(
    record: Cap3ResidualRegionRecord,
) -> Cap3TemplateMismatchRecord:
    """Classify one cap3 residual-overlap record."""

    if record.label == 0 and record.pasdf_residual_topk_overlap >= 0.8:
        closure_label = "strong_positive_template_mismatch"
    elif record.label == 0 and record.pasdf_residual_topk_overlap >= 0.5:
        closure_label = "partial_positive_template_mismatch"
    elif record.label == 1 and record.pasdf_residual_topk_overlap >= 0.5:
        closure_label = "anomaly_residual_overlap_control"
    else:
        closure_label = "weak_residual_overlap"
    return Cap3TemplateMismatchRecord(
        sample_id=record.sample_id,
        label=record.label,
        pasdf_object_score=record.pasdf_object_score,
        residual_topk_mean=record.residual_topk_mean,
        pasdf_residual_topk_overlap=record.pasdf_residual_topk_overlap,
        residual_topk_bbox_ratio=record.residual_topk_bbox_ratio,
        residual_topk_mean_pair_distance_ratio=record.residual_topk_mean_pair_distance_ratio,
        closure_label=closure_label,
    )


def build_failure_mode_closure_records(
    summaries: Sequence[PasdfCalibrationSummary],
) -> tuple[FailureModeClosureRecord, ...]:
    """Build class-level closure records from PASDF calibration summaries."""

    records: list[FailureModeClosureRecord] = []
    for class_name in sorted({summary.class_name for summary in summaries}):
        summary = _select_summary_for_class(summaries, class_name)
        object_status = _object_boundary_status(summary)
        localization_status = f"{summary.weak_localization_count} weak-localization anomaly samples"
        records.append(
            FailureModeClosureRecord(
                class_name=class_name,
                primary_failure_mode=_primary_failure_mode(class_name, object_status),
                object_boundary_status=object_status,
                localization_status=localization_status,
                evidence=_evidence_text(class_name, object_status),
                next_action=_next_action_text(class_name),
            )
        )
    return tuple(records)


def write_failure_mode_closure_csv(
    records: Sequence[FailureModeClosureRecord],
    path: str | Path,
) -> Path:
    """Write class-level failure-mode closure CSV."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FAILURE_MODE_CLOSURE_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return output


def write_combined_failure_mode_records_csv(
    *,
    closures: Sequence[FailureModeClosureRecord],
    boundaries: Sequence[BoundarySampleRecord],
    weak_records: Sequence[WeakLocalizationRecord],
    cap3_records: Sequence[Cap3TemplateMismatchRecord],
    path: str | Path,
) -> Path:
    """Write closure, boundary, weak-localization, and cap3 evidence in one CSV."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMBINED_FIELDS)
        writer.writeheader()
        for closure in closures:
            row = _empty_row("closure")
            row.update(_none_to_empty(asdict(closure)))
            writer.writerow(row)
        for boundary in boundaries:
            row = _empty_row("boundary")
            row.update(_none_to_empty(asdict(boundary)))
            writer.writerow(row)
        for weak_record in weak_records:
            row = _empty_row("weak_localization")
            row.update(_none_to_empty(asdict(weak_record)))
            writer.writerow(row)
        for cap3_record in cap3_records:
            row = _empty_row("cap3_template")
            row.update(_none_to_empty(asdict(cap3_record)))
            writer.writerow(row)
    return output


def render_failure_mode_closure_markdown(
    *,
    closures: Sequence[FailureModeClosureRecord],
    boundaries: Sequence[BoundarySampleRecord],
    weak_records: Sequence[WeakLocalizationRecord],
    cap3_records: Sequence[Cap3TemplateMismatchRecord],
    title: str = "P6 Failure Mode Closure",
) -> str:
    """Render Chinese failure-mode closure report."""

    lines = [
        f"# {title}",
        "",
        "## 结论摘要",
        "",
        "- 本轮不恢复 additive geometry fusion，也不扩 40 类 hybrid。",
        "- `cap3` 按 registration/template false positive 收口。",
        "- `tap1` 按 PASDF soft object boundary 与低幅度局部信号收口。",
        "- `helmet1` 按点级定位弱和 positive boundary 混淆收口。",
        "",
        "## 类别闭环结论",
        "",
        "| 类别 | Failure mode | Object boundary | Localization | Evidence | Next action |",
        "|---|---|---|---|---|---|",
    ]
    for closure in closures:
        lines.append(
            f"| {closure.class_name} | {closure.primary_failure_mode} | "
            f"{closure.object_boundary_status} | {closure.localization_status} | "
            f"{closure.evidence} | {closure.next_action} |"
        )

    lines.extend(
        [
            "",
            "## Object Boundary 样本",
            "",
            "| 类别 | top-k ratio | highest positive | positive score | "
            "lowest anomaly | anomaly score | margin |",
            "|---|---:|---|---:|---|---:|---:|",
        ]
    )
    for boundary in boundaries:
        lines.append(
            f"| {boundary.class_name} | {boundary.top_ratio:.6f} | "
            f"{_fmt_sample(boundary.highest_positive_sample)} | "
            f"{_fmt_optional(boundary.highest_positive_score)} | "
            f"{_fmt_sample(boundary.lowest_anomaly_sample)} | "
            f"{_fmt_optional(boundary.lowest_anomaly_score)} | "
            f"{_fmt_optional(boundary.boundary_margin)} |"
        )

    lines.extend(
        [
            "",
            "## Weak Localization 样本",
            "",
            "| 类别 | 样本 | top-k ratio | GT-bg | GT enrich | 原因 |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for weak_record in weak_records:
        lines.append(
            f"| {weak_record.class_name} | `{weak_record.sample_id}` | "
            f"{weak_record.top_ratio:.6f} | {_fmt_optional(weak_record.gt_background_gap)} | "
            f"{_fmt_optional(weak_record.gt_enrichment)} | {weak_record.reason} |"
        )

    lines.extend(
        [
            "",
            "## cap3 Template Mismatch 证据",
            "",
            "说明：只有 label=0 的 positive 样本会被解释为 false-positive template mismatch；"
            "label=1 的 anomaly 行用于对照 residual/PASDF overlap，不作为 false-positive 证据。",
            "",
            "| 样本 | label | PASDF object | residual topk mean | overlap | "
            "bbox ratio | pair ratio | closure |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for cap3_record in cap3_records:
        lines.append(
            f"| `{cap3_record.sample_id}` | {cap3_record.label} | "
            f"{cap3_record.pasdf_object_score:.6f} | "
            f"{cap3_record.residual_topk_mean:.6f} | "
            f"{cap3_record.pasdf_residual_topk_overlap:.6f} | "
            f"{cap3_record.residual_topk_bbox_ratio:.6f} | "
            f"{cap3_record.residual_topk_mean_pair_distance_ratio:.6f} | "
            f"{cap3_record.closure_label} |"
        )

    lines.extend(["", "## 下一步", ""])
    lines.extend(_next_stage_lines(closures))
    lines.append("")
    return "\n".join(lines)


def _select_summary_for_class(
    summaries: Sequence[PasdfCalibrationSummary],
    class_name: str,
) -> PasdfCalibrationSummary:
    class_summaries = tuple(summary for summary in summaries if summary.class_name == class_name)
    if not class_summaries:
        raise ValueError(f"No summary for class {class_name}")
    return max(
        class_summaries,
        key=lambda summary: (
            float(summary.strict_object_pass),
            float(summary.soft_object_pass),
            summary.mean_anomaly_topk or float("-inf"),
            -(summary.max_positive_topk or float("inf")),
        ),
    )


def _object_boundary_status(summary: PasdfCalibrationSummary) -> str:
    if summary.strict_object_pass:
        return "strict_pass"
    if summary.soft_object_pass:
        return "soft_pass"
    return "failed"


def _primary_failure_mode(class_name: str, object_status: str) -> str:
    if class_name == "cap3":
        return "registration/template false positive"
    if class_name == "tap1":
        return "soft object boundary with low-amplitude local PASDF signal"
    if class_name == "helmet1":
        return "point-level localization weakness"
    if object_status == "strict_pass":
        return "no closure failure under selected top-k ratio"
    return "unclassified PASDF boundary/localization weakness"


def _evidence_text(class_name: str, object_status: str) -> str:
    if class_name == "cap3":
        return "top-k calibration failed; cap3 positive residual overlap should be checked"
    if class_name == "tap1":
        return "PASDF-only calibration soft-passes; additive geometry fusion remains rejected"
    if class_name == "helmet1":
        return "mean anomaly can be high but positive boundary still overlaps"
    return f"object boundary status is {object_status}"


def _next_action_text(class_name: str) -> str:
    if class_name == "cap3":
        return "continue registration/template robustness; do not tune PASDF top-k only"
    if class_name == "tap1":
        return "audit positive boundary and low-score anomalies; keep geometry as diagnostic only"
    if class_name == "helmet1":
        return "audit weak-localization anomalies and high positive boundary samples"
    return "review class-specific weak localization and boundary samples"


def _weak_reasons(record: PasdfTopKCalibrationRecord) -> tuple[str, ...]:
    reasons: list[str] = []
    if record.gt_enrichment is not None and record.gt_enrichment <= 1.0:
        reasons.append("gt_enrichment<=1")
    if record.gt_background_gap is not None and record.gt_background_gap <= 0.0:
        reasons.append("gt_background_gap<=0")
    return tuple(reasons)


def _next_stage_lines(closures: Sequence[FailureModeClosureRecord]) -> list[str]:
    class_names = {closure.class_name for closure in closures}
    lines: list[str] = []
    if "cap3" in class_names:
        lines.append(
            "- `cap3`：进入 registration/template robustness 方案设计，优先考虑 "
            "template selection 或局部对齐诊断。"
        )
    if "tap1" in class_names:
        lines.append("- `tap1`：保留 PASDF calibration 结论，不恢复 naive geometry fusion。")
    if "helmet1" in class_names:
        lines.append("- `helmet1`：补充 heatmap/GT overlay 人工复查，服务最终报告。")
    if not lines:
        lines.append("- 继续按 closure 表中的 next_action 执行。")
    return lines


def _empty_row(record_type: str) -> dict[str, object]:
    row: dict[str, object] = {field: "" for field in COMBINED_FIELDS}
    row["record_type"] = record_type
    return row


def _none_to_empty(row: dict[str, object]) -> dict[str, object]:
    return {key: ("" if value is None else value) for key, value in row.items()}


def _round_optional(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _fmt_sample(value: str | None) -> str:
    return "NA" if value is None else f"`{value}`"
