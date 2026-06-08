"""PASDF baseline failure analysis utilities."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pcdad.models.pasdf_adapter import PasdfEvaluationResult, parse_evaluation_results

EVALUATING_RE = re.compile(r"Evaluating \[([^\]]+)\]")
TOO_FEW_CORRESPONDENCES_RE = re.compile(r"Too few correspondences \((\d+)\)")


@dataclass(frozen=True)
class FailureThresholds:
    """AUROC thresholds used to flag classes for P4 analysis."""

    pixel_auc: float = 0.85
    object_auc: float = 0.8


DEFAULT_FAILURE_THRESHOLDS = FailureThresholds()


@dataclass(frozen=True)
class WarningExample:
    """One Open3D warning with the evaluation class context inferred from the log."""

    class_name: str | None
    line_number: int
    correspondence_count: int | None
    message: str


@dataclass(frozen=True)
class Open3DWarningSummary:
    """Open3D warning counts grouped by PASDF class context."""

    total_count: int
    by_class: dict[str, int]
    unattributed_count: int
    examples: dict[str, tuple[WarningExample, ...]]
    unattributed_examples: tuple[WarningExample, ...]


@dataclass(frozen=True)
class ClassFailureRecord:
    """Per-class PASDF metric row with attached warning count."""

    class_name: str
    pixel_auc: float
    object_auc: float
    open3d_warning_count: int = 0


@dataclass(frozen=True)
class PasdfFailureSummary:
    """Structured P4 failure summary for PASDF official-weight evaluation."""

    class_count: int
    mean_pixel_auc: float
    mean_object_auc: float
    thresholds: FailureThresholds
    rows: tuple[ClassFailureRecord, ...]
    pixel_failures: tuple[ClassFailureRecord, ...]
    object_failures: tuple[ClassFailureRecord, ...]
    min_pixel: ClassFailureRecord
    min_object: ClassFailureRecord
    open3d_warnings: Open3DWarningSummary
    results_path: Path
    log_path: Path | None

    @property
    def priority_classes(self) -> tuple[str, ...]:
        """Return class names needing P4 attention in deterministic priority order."""

        names: list[str] = []
        for record in (*self.object_failures, *self.pixel_failures):
            if record.class_name not in names:
                names.append(record.class_name)
        return tuple(names)


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def parse_open3d_warnings_by_class(
    path: str | Path,
    *,
    max_examples: int = 3,
) -> Open3DWarningSummary:
    """Parse PASDF run.log and group Open3D correspondence warnings by current class."""

    log_path = Path(path)
    current_class: str | None = None
    counts: dict[str, int] = defaultdict(int)
    examples: dict[str, list[WarningExample]] = defaultdict(list)
    unattributed_examples: list[WarningExample] = []
    unattributed_count = 0
    total_count = 0

    for line_number, raw_line in enumerate(log_path.read_text(errors="replace").splitlines(), 1):
        line = _strip_ansi(raw_line)
        class_match = EVALUATING_RE.search(line)
        if class_match:
            current_class = class_match.group(1)

        warning_match = TOO_FEW_CORRESPONDENCES_RE.search(line)
        if warning_match is None:
            continue

        total_count += 1
        correspondence_count = int(warning_match.group(1))
        warning = WarningExample(
            class_name=current_class,
            line_number=line_number,
            correspondence_count=correspondence_count,
            message=line.strip(),
        )
        if current_class is None:
            unattributed_count += 1
            if len(unattributed_examples) < max_examples:
                unattributed_examples.append(warning)
            continue

        counts[current_class] += 1
        if len(examples[current_class]) < max_examples:
            examples[current_class].append(warning)

    return Open3DWarningSummary(
        total_count=total_count,
        by_class=dict(sorted(counts.items())),
        unattributed_count=unattributed_count,
        examples={key: tuple(value) for key, value in sorted(examples.items())},
        unattributed_examples=tuple(unattributed_examples),
    )


def _empty_warning_summary() -> Open3DWarningSummary:
    return Open3DWarningSummary(
        total_count=0,
        by_class={},
        unattributed_count=0,
        examples={},
        unattributed_examples=(),
    )


def _to_failure_rows(
    results: Iterable[PasdfEvaluationResult],
    warning_summary: Open3DWarningSummary,
) -> tuple[ClassFailureRecord, ...]:
    return tuple(
        ClassFailureRecord(
            class_name=result.class_name,
            pixel_auc=result.pixel_auc,
            object_auc=result.object_auc,
            open3d_warning_count=warning_summary.by_class.get(result.class_name, 0),
        )
        for result in results
    )


def _sort_metric_failures(
    rows: Iterable[ClassFailureRecord],
    *,
    metric: str,
    threshold: float,
) -> tuple[ClassFailureRecord, ...]:
    return tuple(
        sorted(
            (row for row in rows if getattr(row, metric) < threshold),
            key=lambda row: (getattr(row, metric), row.class_name),
        )
    )


def analyze_pasdf_failures(
    results_path: str | Path,
    *,
    log_path: str | Path | None = None,
    thresholds: FailureThresholds = DEFAULT_FAILURE_THRESHOLDS,
) -> PasdfFailureSummary:
    """Analyze PASDF evaluation CSV and optional run.log into P4 failure priorities."""

    result_file = Path(results_path)
    results = parse_evaluation_results(result_file)
    if not results:
        raise ValueError("At least one PASDF evaluation result is required")

    warning_summary = (
        parse_open3d_warnings_by_class(log_path)
        if log_path is not None
        else _empty_warning_summary()
    )
    rows = _to_failure_rows(results, warning_summary)
    class_count = len(rows)
    mean_pixel_auc = math.fsum(row.pixel_auc for row in rows) / class_count
    mean_object_auc = math.fsum(row.object_auc for row in rows) / class_count

    return PasdfFailureSummary(
        class_count=class_count,
        mean_pixel_auc=round(mean_pixel_auc, 12),
        mean_object_auc=round(mean_object_auc, 12),
        thresholds=thresholds,
        rows=rows,
        pixel_failures=_sort_metric_failures(
            rows,
            metric="pixel_auc",
            threshold=thresholds.pixel_auc,
        ),
        object_failures=_sort_metric_failures(
            rows,
            metric="object_auc",
            threshold=thresholds.object_auc,
        ),
        min_pixel=min(rows, key=lambda row: (row.pixel_auc, row.class_name)),
        min_object=min(rows, key=lambda row: (row.object_auc, row.class_name)),
        open3d_warnings=warning_summary,
        results_path=result_file,
        log_path=Path(log_path) if log_path is not None else None,
    )


def _format_record_table(records: Iterable[ClassFailureRecord]) -> list[str]:
    lines = [
        "| 类别 | Pixel AUROC | Object AUROC | Open3D Warnings |",
        "|---|---:|---:|---:|",
    ]
    for record in records:
        lines.append(
            f"| {record.class_name} | {record.pixel_auc:.6f} | "
            f"{record.object_auc:.6f} | {record.open3d_warning_count} |"
        )
    return lines


def _merge_failure_rows(summary: PasdfFailureSummary) -> tuple[ClassFailureRecord, ...]:
    rows: list[ClassFailureRecord] = []
    seen: set[str] = set()
    for record in (*summary.object_failures, *summary.pixel_failures):
        if record.class_name in seen:
            continue
        rows.append(record)
        seen.add(record.class_name)
    return tuple(rows)


def render_failure_report_markdown(
    summary: PasdfFailureSummary,
    *,
    title: str = "P4 PASDF 失败分析摘要",
) -> str:
    """Render a lightweight Markdown report suitable for stage records."""

    lines = [
        f"# {title}",
        "",
        "## 记录范围",
        "",
        f"- 结果 CSV：`{summary.results_path}`",
        (
            f"- 运行日志：`{summary.log_path}`"
            if summary.log_path is not None
            else "- 运行日志：_未提供_"
        ),
        f"- 类别数：{summary.class_count}",
        "",
        "## 指标摘要",
        "",
        f"- mean_pixel_auc: `{summary.mean_pixel_auc:.12f}`",
        f"- mean_object_auc: `{summary.mean_object_auc:.12f}`",
        f"- min_pixel: `{summary.min_pixel.class_name}` = `{summary.min_pixel.pixel_auc:.12f}`",
        f"- min_object: `{summary.min_object.class_name}` = `{summary.min_object.object_auc:.12f}`",
        "",
        "## 阈值失败类别",
        "",
        f"- pixel_auc < {summary.thresholds.pixel_auc}: "
        + _format_class_list(record.class_name for record in summary.pixel_failures),
        f"- object_auc < {summary.thresholds.object_auc}: "
        + _format_class_list(record.class_name for record in summary.object_failures),
        "",
        "## Open3D Warning 摘要",
        "",
        f"- total_too_few_correspondences: {summary.open3d_warnings.total_count}",
        f"- unattributed_warnings: {summary.open3d_warnings.unattributed_count}",
        "",
        "## P4 优先分析类别",
        "",
        _format_class_list(summary.priority_classes),
        "",
        "## 失败类别明细",
        "",
    ]
    failure_rows = _merge_failure_rows(summary)
    lines.extend(_format_record_table(failure_rows or summary.rows))
    lines.append("")
    return "\n".join(lines)


def _format_class_list(class_names: Iterable[str]) -> str:
    names = tuple(class_names)
    if not names:
        return "_none_"
    return ", ".join(f"`{name}`" for name in names)
