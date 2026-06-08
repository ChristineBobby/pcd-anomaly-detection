"""PASDF registration warning diagnostics and voxel sweep planning."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from pcdad.analysis.pasdf_failures import (
    EVALUATING_RE,
    TOO_FEW_CORRESPONDENCES_RE,
    ClassFailureRecord,
    PasdfFailureSummary,
    _strip_ansi,
)

PCD_PATH_RE = re.compile(r"(/[^\s\r\n]+\.pcd)")
DEFAULT_SWEEP_VOXEL_SIZES = (0.02, 0.03, 0.04, 0.05)
DEFAULT_EXPERIMENT_CONFIG = Path("configs/experiment/E1_pasdf_baseline.yaml")
DEFAULT_OUTPUT_ROOT = Path("experiments/P4_registration_sweep")


@dataclass(frozen=True)
class RegistrationWarningEvent:
    """One Open3D registration warning with class and sample context."""

    class_name: str | None
    sample_path: Path | None
    sample_name: str | None
    line_number: int
    correspondence_count: int
    message: str


@dataclass(frozen=True)
class RegistrationPriorityRow:
    """Per-class registration diagnostic row used to choose P4 sweep targets."""

    class_name: str
    pixel_auc: float
    object_auc: float
    warning_count: int
    warning_sample_count: int
    official_voxel_size: float | None
    sweep_voxel_sizes: tuple[float, ...]


@dataclass(frozen=True)
class WarningSampleRow:
    """Warning counts grouped by sample path."""

    class_name: str | None
    sample_name: str | None
    sample_path: Path | None
    warning_count: int
    min_correspondences: int
    max_correspondences: int


@dataclass(frozen=True)
class RegistrationDiagnosticInputs:
    """Inputs needed to build PASDF registration diagnostics."""

    failure_summary: PasdfFailureSummary
    run_log: Path
    voxel_sizes_path: Path | None = None
    sweep_voxel_sizes: tuple[float, ...] = DEFAULT_SWEEP_VOXEL_SIZES
    experiment_config: Path = DEFAULT_EXPERIMENT_CONFIG
    output_root: Path = DEFAULT_OUTPUT_ROOT
    max_classes: int | None = None


@dataclass(frozen=True)
class RegistrationDiagnostics:
    """Structured P4 registration diagnostic and voxel sweep plan."""

    priority_rows: tuple[RegistrationPriorityRow, ...]
    warning_sample_rows: tuple[WarningSampleRow, ...]
    sweep_commands: tuple[str, ...]
    warning_events: tuple[RegistrationWarningEvent, ...]
    run_log: Path
    voxel_sizes_path: Path | None


def parse_registration_warning_events(path: str | Path) -> tuple[RegistrationWarningEvent, ...]:
    """Parse PASDF run.log and attach each warning to the nearest preceding sample path."""

    log_path = Path(path)
    current_class: str | None = None
    current_sample_path: Path | None = None
    events: list[RegistrationWarningEvent] = []

    for line_number, raw_line in enumerate(log_path.read_text(errors="replace").splitlines(), 1):
        line = _strip_ansi(raw_line)
        class_match = EVALUATING_RE.search(line)
        if class_match:
            current_class = class_match.group(1)

        sample_match = PCD_PATH_RE.search(line)
        if sample_match:
            current_sample_path = Path(sample_match.group(1))

        warning_match = TOO_FEW_CORRESPONDENCES_RE.search(line)
        if warning_match is None:
            continue

        events.append(
            RegistrationWarningEvent(
                class_name=current_class,
                sample_path=current_sample_path,
                sample_name=current_sample_path.name if current_sample_path is not None else None,
                line_number=line_number,
                correspondence_count=int(warning_match.group(1)),
                message=line.strip(),
            )
        )
    return tuple(events)


def load_shapenetad_voxel_sizes(path: str | Path | None) -> dict[str, float]:
    """Load official PASDF ShapeNetAD per-class voxel sizes if available."""

    if path is None:
        return {}
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"voxel_sizes.yaml must be a mapping: {path}")
    shapenetad = payload.get("ShapeNetAD", {})
    if not isinstance(shapenetad, dict):
        raise ValueError(f"ShapeNetAD voxel sizes must be a mapping: {path}")
    return {str(key): float(value) for key, value in shapenetad.items()}


def build_registration_diagnostics(
    inputs: RegistrationDiagnosticInputs,
) -> RegistrationDiagnostics:
    """Build class and sample-level registration diagnostics from P4 failure data."""

    events = parse_registration_warning_events(inputs.run_log)
    voxel_sizes = load_shapenetad_voxel_sizes(inputs.voxel_sizes_path)
    rows_by_class = {row.class_name: row for row in inputs.failure_summary.rows}
    priority_classes = inputs.failure_summary.priority_classes
    if inputs.max_classes is not None:
        priority_classes = priority_classes[: inputs.max_classes]

    class_warning_counts = _count_events_by_class(events)
    class_warning_sample_counts = _count_warning_samples_by_class(events)
    priority_rows = tuple(
        _build_priority_row(
            rows_by_class[class_name],
            warning_count=class_warning_counts.get(class_name, 0),
            warning_sample_count=class_warning_sample_counts.get(class_name, 0),
            official_voxel_size=voxel_sizes.get(class_name),
            sweep_voxel_sizes=inputs.sweep_voxel_sizes,
        )
        for class_name in priority_classes
        if class_name in rows_by_class
    )
    commands = tuple(
        _format_sweep_command(
            class_name=row.class_name,
            voxel_size=voxel_size,
            experiment_config=inputs.experiment_config,
            output_root=inputs.output_root,
        )
        for row in priority_rows
        for voxel_size in row.sweep_voxel_sizes
    )

    return RegistrationDiagnostics(
        priority_rows=priority_rows,
        warning_sample_rows=_build_warning_sample_rows(events),
        sweep_commands=commands,
        warning_events=events,
        run_log=inputs.run_log,
        voxel_sizes_path=inputs.voxel_sizes_path,
    )


def render_registration_diagnostics_markdown(
    diagnostics: RegistrationDiagnostics,
    *,
    title: str = "P4 PASDF Registration Diagnostics",
) -> str:
    """Render a Markdown report for P4 registration diagnostics."""

    lines = [
        f"# {title}",
        "",
        "## Scope",
        "",
        f"- Run log: `{diagnostics.run_log}`",
        (
            f"- Voxel sizes: `{diagnostics.voxel_sizes_path}`"
            if diagnostics.voxel_sizes_path is not None
            else "- Voxel sizes: _not provided_"
        ),
        f"- Open3D warning events: {len(diagnostics.warning_events)}",
        "",
        "## Priority Classes",
        "",
    ]
    lines.extend(_format_priority_table(diagnostics.priority_rows))
    lines.extend(["", "## Warning Samples", ""])
    lines.extend(_format_warning_sample_table(diagnostics.warning_sample_rows))
    lines.extend(["", "## Voxel Sweep Commands", ""])
    lines.extend(f"```bash\n{command}\n```" for command in diagnostics.sweep_commands)
    lines.append("")
    return "\n".join(lines)


def _build_priority_row(
    record: ClassFailureRecord,
    *,
    warning_count: int,
    warning_sample_count: int,
    official_voxel_size: float | None,
    sweep_voxel_sizes: tuple[float, ...],
) -> RegistrationPriorityRow:
    return RegistrationPriorityRow(
        class_name=record.class_name,
        pixel_auc=record.pixel_auc,
        object_auc=record.object_auc,
        warning_count=warning_count,
        warning_sample_count=warning_sample_count,
        official_voxel_size=official_voxel_size,
        sweep_voxel_sizes=sweep_voxel_sizes,
    )


def _count_events_by_class(events: Iterable[RegistrationWarningEvent]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        if event.class_name is not None:
            counts[event.class_name] += 1
    return dict(counts)


def _count_warning_samples_by_class(events: Iterable[RegistrationWarningEvent]) -> dict[str, int]:
    samples_by_class: dict[str, set[Path | None]] = defaultdict(set)
    for event in events:
        if event.class_name is not None:
            samples_by_class[event.class_name].add(event.sample_path)
    return {class_name: len(samples) for class_name, samples in samples_by_class.items()}


def _build_warning_sample_rows(
    events: Iterable[RegistrationWarningEvent],
) -> tuple[WarningSampleRow, ...]:
    groups: dict[tuple[str | None, Path | None], list[RegistrationWarningEvent]] = defaultdict(list)
    for event in events:
        groups[(event.class_name, event.sample_path)].append(event)

    rows = tuple(
        WarningSampleRow(
            class_name=class_name,
            sample_name=sample_path.name if sample_path is not None else None,
            sample_path=sample_path,
            warning_count=len(group_events),
            min_correspondences=min(event.correspondence_count for event in group_events),
            max_correspondences=max(event.correspondence_count for event in group_events),
        )
        for (class_name, sample_path), group_events in groups.items()
    )
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                -(row.warning_count),
                row.class_name or "",
                row.sample_name or "",
            ),
        )
    )


def _format_sweep_command(
    *,
    class_name: str,
    voxel_size: float,
    experiment_config: Path,
    output_root: Path,
) -> str:
    voxel_label = f"{voxel_size:.3f}".replace(".", "p")
    output_dir = output_root / class_name / f"vs_{voxel_label}"
    return (
        "PYTHONPATH=src python scripts/evaluate.py "
        f"--config {experiment_config} "
        f"--classes {class_name} "
        f"--voxel-size {voxel_size:.2f} "
        f"--output-dir {output_dir}"
    )


def _format_priority_table(rows: Iterable[RegistrationPriorityRow]) -> list[str]:
    lines = [
        "| Class | Pixel AUROC | Object AUROC | Warnings | Warning Samples | "
        "Official Voxel | Sweep Voxels |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        official = (
            f"{row.official_voxel_size:.3f}" if row.official_voxel_size is not None else "_missing_"
        )
        sweep = ", ".join(f"{value:.3f}" for value in row.sweep_voxel_sizes)
        lines.append(
            f"| {row.class_name} | {row.pixel_auc:.6f} | {row.object_auc:.6f} | "
            f"{row.warning_count} | {row.warning_sample_count} | {official} | {sweep} |"
        )
    return lines


def _format_warning_sample_table(rows: Iterable[WarningSampleRow]) -> list[str]:
    lines = [
        "| Class | Sample | Warnings | Correspondence Range | Path |",
        "|---|---|---:|---|---|",
    ]
    for row in rows:
        class_name = row.class_name or "_unknown_"
        sample_name = row.sample_name or "_unknown_"
        sample_path = f"`{row.sample_path}`" if row.sample_path is not None else "_unknown_"
        lines.append(
            f"| {class_name} | {sample_name} | {row.warning_count} | "
            f"{row.min_correspondences}-{row.max_correspondences} | {sample_path} |"
        )
    return lines


def _safe_yaml_load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
