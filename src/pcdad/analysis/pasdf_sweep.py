"""PASDF voxel-size sweep result collection and reporting."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pcdad.analysis.pasdf_registration import parse_registration_warning_events
from pcdad.models.pasdf_adapter import parse_evaluation_results

VOXEL_DIR_RE = re.compile(r"^vs_(\d+)p(\d+)$")


@dataclass(frozen=True)
class SweepCollectionSpec:
    """Filesystem layout for a PASDF voxel-size sweep."""

    root: Path
    classes: tuple[str, ...]


@dataclass(frozen=True)
class SweepResultRow:
    """One PASDF class/voxel-size sweep run."""

    class_name: str
    voxel_size: float
    pixel_auc: float
    object_auc: float
    warning_count: int
    warning_sample_count: int
    run_dir: Path


@dataclass(frozen=True)
class SweepSummary:
    """PASDF sweep rows plus best run selected per class."""

    rows: tuple[SweepResultRow, ...]
    best_by_class: dict[str, SweepResultRow]
    root: Path


def collect_pasdf_sweep_results(spec: SweepCollectionSpec) -> SweepSummary:
    """Collect PASDF sweep metrics and registration warnings from run directories."""

    rows: list[SweepResultRow] = []
    for class_name in spec.classes:
        class_dir = spec.root / class_name
        if not class_dir.exists():
            continue
        for run_dir in sorted(path for path in class_dir.iterdir() if path.is_dir()):
            voxel_size = _parse_voxel_dir_name(run_dir.name)
            if voxel_size is None:
                continue
            row = _load_sweep_row(class_name, voxel_size, run_dir)
            if row is not None:
                rows.append(row)

    sorted_rows = tuple(sorted(rows, key=lambda row: (row.class_name, row.voxel_size)))
    return SweepSummary(
        rows=sorted_rows,
        best_by_class=_select_best_by_class(sorted_rows),
        root=spec.root,
    )


def render_sweep_summary_markdown(
    summary: SweepSummary,
    *,
    title: str = "P4 PASDF Voxel Sweep Summary",
) -> str:
    """Render a Markdown summary for PASDF voxel sweep results."""

    lines = [
        f"# {title}",
        "",
        "## Scope",
        "",
        f"- Sweep root: `{summary.root}`",
        f"- Runs parsed: {len(summary.rows)}",
        "",
        "## Best By Class",
        "",
    ]
    lines.extend(_format_sweep_table(summary.best_by_class.values()))
    lines.extend(["", "## All Runs", ""])
    lines.extend(_format_sweep_table(summary.rows))
    lines.append("")
    return "\n".join(lines)


def _parse_voxel_dir_name(name: str) -> float | None:
    match = VOXEL_DIR_RE.match(name)
    if match is None:
        return None
    return float(f"{match.group(1)}.{match.group(2)}")


def _load_sweep_row(
    expected_class: str,
    voxel_size: float,
    run_dir: Path,
) -> SweepResultRow | None:
    results_path = run_dir / "evaluation_results.csv"
    log_path = run_dir / "run.log"
    if not results_path.exists() or not log_path.exists():
        return None

    results = parse_evaluation_results(results_path)
    result = next((row for row in results if row.class_name == expected_class), None)
    if result is None:
        return None

    warning_events = parse_registration_warning_events(log_path)
    sample_paths = {
        event.sample_path
        for event in warning_events
        if event.class_name == expected_class and event.sample_path is not None
    }
    warning_count = sum(1 for event in warning_events if event.class_name == expected_class)
    return SweepResultRow(
        class_name=expected_class,
        voxel_size=voxel_size,
        pixel_auc=result.pixel_auc,
        object_auc=result.object_auc,
        warning_count=warning_count,
        warning_sample_count=len(sample_paths),
        run_dir=run_dir,
    )


def _select_best_by_class(rows: Iterable[SweepResultRow]) -> dict[str, SweepResultRow]:
    best: dict[str, SweepResultRow] = {}
    for row in rows:
        current = best.get(row.class_name)
        if current is None or _best_sort_key(row) > _best_sort_key(current):
            best[row.class_name] = row
    return dict(sorted(best.items()))


def _best_sort_key(row: SweepResultRow) -> tuple[float, float, int, float]:
    return (
        row.object_auc,
        row.pixel_auc,
        -row.warning_count,
        -row.voxel_size,
    )


def _format_sweep_table(rows: Iterable[SweepResultRow]) -> list[str]:
    lines = [
        "| Class | Voxel Size | Pixel AUROC | Object AUROC | Warnings | Warning Samples |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.class_name} | {row.voxel_size:.3f} | {row.pixel_auc:.6f} | "
            f"{row.object_auc:.6f} | {row.warning_count} | {row.warning_sample_count} |"
        )
    return lines
