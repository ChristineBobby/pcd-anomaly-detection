"""PASDF repeated-run stability summaries."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pcdad.analysis.pasdf_registration import parse_registration_warning_events
from pcdad.models.pasdf_adapter import parse_evaluation_results


@dataclass(frozen=True)
class StabilityCollectionSpec:
    """Filesystem layout for repeated PASDF stability runs."""

    root: Path
    classes: tuple[str, ...]


@dataclass(frozen=True)
class PasdfRunRecord:
    """One PASDF repeated-run record."""

    class_name: str
    run_id: str
    pixel_auc: float
    object_auc: float
    warning_count: int
    warning_sample_count: int
    run_dir: Path


@dataclass(frozen=True)
class ClassStabilitySummary:
    """Per-class mean, spread, and warning summary."""

    class_name: str
    run_count: int
    mean_pixel_auc: float
    std_pixel_auc: float
    mean_object_auc: float
    std_object_auc: float
    min_object_auc: float
    max_object_auc: float
    total_warning_count: int


@dataclass(frozen=True)
class PasdfStabilitySummary:
    """Repeated PASDF run summary."""

    rows: tuple[PasdfRunRecord, ...]
    by_class: dict[str, ClassStabilitySummary]
    root: Path


def collect_pasdf_stability_runs(spec: StabilityCollectionSpec) -> PasdfStabilitySummary:
    """Collect repeated PASDF runs from ``root/class_name/run_id`` directories."""

    rows: list[PasdfRunRecord] = []
    for class_name in spec.classes:
        class_dir = spec.root / class_name
        if not class_dir.exists():
            continue
        for run_dir in sorted(path for path in class_dir.iterdir() if path.is_dir()):
            row = _load_run_record(class_name, run_dir)
            if row is not None:
                rows.append(row)

    sorted_rows = tuple(sorted(rows, key=lambda row: (row.class_name, row.run_id)))
    return PasdfStabilitySummary(
        rows=sorted_rows,
        by_class=_summarize_by_class(sorted_rows),
        root=spec.root,
    )


def render_stability_markdown(
    summary: PasdfStabilitySummary,
    *,
    title: str = "P4 PASDF 稳定性复核摘要",
) -> str:
    """Render a Chinese Markdown summary for repeated PASDF runs."""

    lines = [
        f"# {title}",
        "",
        "## 记录范围",
        "",
        f"- 稳定性实验根目录：`{summary.root}`",
        f"- 已解析 run 数：{len(summary.rows)}",
        "",
        "## 类别稳定性摘要",
        "",
    ]
    lines.extend(_format_class_table(summary.by_class.values()))
    lines.extend(["", "## 全部 Run", ""])
    lines.extend(_format_run_table(summary.rows))
    lines.append("")
    return "\n".join(lines)


def _load_run_record(class_name: str, run_dir: Path) -> PasdfRunRecord | None:
    results_path = run_dir / "evaluation_results.csv"
    log_path = run_dir / "run.log"
    if not results_path.exists() or not log_path.exists():
        return None

    results = parse_evaluation_results(results_path)
    result = next((row for row in results if row.class_name == class_name), None)
    if result is None:
        return None

    warning_events = parse_registration_warning_events(log_path)
    matching_events = tuple(event for event in warning_events if event.class_name == class_name)
    warning_samples = {
        event.sample_path for event in matching_events if event.sample_path is not None
    }
    return PasdfRunRecord(
        class_name=class_name,
        run_id=run_dir.name,
        pixel_auc=result.pixel_auc,
        object_auc=result.object_auc,
        warning_count=len(matching_events),
        warning_sample_count=len(warning_samples),
        run_dir=run_dir,
    )


def _summarize_by_class(rows: Iterable[PasdfRunRecord]) -> dict[str, ClassStabilitySummary]:
    grouped: dict[str, list[PasdfRunRecord]] = defaultdict(list)
    for row in rows:
        grouped[row.class_name].append(row)
    return {
        class_name: _summarize_class(class_name, class_rows)
        for class_name, class_rows in sorted(grouped.items())
    }


def _summarize_class(
    class_name: str,
    rows: list[PasdfRunRecord],
) -> ClassStabilitySummary:
    pixel_values = tuple(row.pixel_auc for row in rows)
    object_values = tuple(row.object_auc for row in rows)
    return ClassStabilitySummary(
        class_name=class_name,
        run_count=len(rows),
        mean_pixel_auc=round(_mean(pixel_values), 12),
        std_pixel_auc=round(_population_std(pixel_values), 12),
        mean_object_auc=round(_mean(object_values), 12),
        std_object_auc=round(_population_std(object_values), 12),
        min_object_auc=min(object_values),
        max_object_auc=max(object_values),
        total_warning_count=sum(row.warning_count for row in rows),
    )


def _mean(values: tuple[float, ...]) -> float:
    if not values:
        raise ValueError("At least one value is required")
    return math.fsum(values) / len(values)


def _population_std(values: tuple[float, ...]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = _mean(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _format_class_table(rows: Iterable[ClassStabilitySummary]) -> list[str]:
    lines = [
        "| 类别 | Run 数 | Mean Pixel AUROC | Mean Object AUROC | "
        "Std Object AUROC | Min Object AUROC | Max Object AUROC | Warning 总数 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.class_name} | {row.run_count} | {row.mean_pixel_auc:.6f} | "
            f"{row.mean_object_auc:.6f} | {row.std_object_auc:.6f} | "
            f"{row.min_object_auc:.6f} | {row.max_object_auc:.6f} | "
            f"{row.total_warning_count} |"
        )
    return lines


def _format_run_table(rows: Iterable[PasdfRunRecord]) -> list[str]:
    lines = [
        "| 类别 | Run ID | Pixel AUROC | Object AUROC | Warning 数 | Warning 样本数 | Run 目录 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.class_name} | {row.run_id} | {row.pixel_auc:.6f} | "
            f"{row.object_auc:.6f} | {row.warning_count} | "
            f"{row.warning_sample_count} | `{row.run_dir}` |"
        )
    return lines
