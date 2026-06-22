"""Run P7-B positive-aware calibration experiments."""

from __future__ import annotations

import argparse
import csv
import subprocess
from collections.abc import Sequence
from pathlib import Path

from pcdad.calibration.positive_aware import (
    BoundaryMargin,
    CalibrationRecord,
    CalibrationSummary,
    boundary_margin,
    calibrate_scores,
    load_calibration_records,
    summarize_calibration,
    write_boundary_margins_csv,
    write_calibration_records_csv,
    write_calibration_summaries_csv,
)

DEFAULT_METHODS: tuple[str, ...] = (
    "pasdf_raw",
    "template_residual",
    "confidence_gate",
    "isotonic_pasdf",
    "isotonic_gated",
    "logistic_l2",
)

DEFAULT_SPLIT_MODES: tuple[str, ...] = (
    "none",
    "diagnostic_oracle",
    "leave_one_class_out",
)

DEFAULT_FEATURES: tuple[str, ...] = (
    "pasdf_score",
    "template_score",
    "top1_top2_margin",
    "assignment_entropy",
    "residual_overlap",
    "registration_confidence",
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build P7-B CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--classes", nargs="+", required=True)
    parser.add_argument("--dataset-name", default="anomaly_shapenet_16384")
    parser.add_argument("--methods", nargs="+", default=list(DEFAULT_METHODS))
    parser.add_argument("--split-modes", nargs="+", default=list(DEFAULT_SPLIT_MODES))
    parser.add_argument("--features", nargs="+", default=list(DEFAULT_FEATURES))
    parser.add_argument("--dry-run", action="store_true")
    return parser


def planned_outputs(args: argparse.Namespace) -> dict[str, Path]:
    """Return planned output paths."""

    output_dir = Path(args.output_dir)
    return {
        "calibration_records_csv": output_dir / "calibration_records.csv",
        "metrics_csv": output_dir / "metrics.csv",
        "boundary_margin_csv": output_dir / "boundary_margin.csv",
        "failure_toplist_csv": output_dir / "failure_toplist.csv",
        "readme": output_dir / "README.md",
        "config": output_dir / "config.yaml",
        "git_hash": output_dir / "git_hash.txt",
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = build_arg_parser().parse_args(argv)
    outputs = planned_outputs(args)
    if args.dry_run:
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return 0

    input_records = load_calibration_records(args.input_csv, dataset_name=args.dataset_name)
    selected_records = tuple(
        record for record in input_records if record.class_name in args.classes
    )
    if not selected_records:
        raise ValueError("no records remain after class filtering")
    calibrated_records = run_calibration_matrix(
        selected_records,
        methods=tuple(args.methods),
        split_modes=tuple(args.split_modes),
        feature_names=tuple(args.features),
    )
    summaries = summarize_calibration(calibrated_records, score_fields=("calibrated_score",))
    margins = build_boundary_margins(calibrated_records)
    write_calibration_records_csv(calibrated_records, outputs["calibration_records_csv"])
    write_calibration_summaries_csv(summaries, outputs["metrics_csv"])
    write_boundary_margins_csv(margins, outputs["boundary_margin_csv"])
    write_failure_toplist_csv(calibrated_records, outputs["failure_toplist_csv"])
    write_config(args, outputs["config"])
    write_git_hash(outputs["git_hash"])
    write_readme(args, outputs["readme"], summaries)
    return 0


def run_calibration_matrix(
    records: Sequence[CalibrationRecord],
    *,
    methods: tuple[str, ...],
    split_modes: tuple[str, ...],
    feature_names: tuple[str, ...],
) -> tuple[CalibrationRecord, ...]:
    """Run requested methods and split modes."""

    outputs: list[CalibrationRecord] = []
    for method in methods:
        applicable_splits = _applicable_split_modes(method, split_modes)
        for split_mode in applicable_splits:
            method_features = _features_for_method(method, feature_names)
            outputs.extend(
                calibrate_scores(
                    records,
                    method=method,
                    feature_names=method_features,
                    split_mode=split_mode,
                )
            )
    return tuple(outputs)


def build_boundary_margins(records: Sequence[CalibrationRecord]) -> tuple[BoundaryMargin, ...]:
    """Build boundary margins by method/split/class."""

    margins: list[BoundaryMargin] = []
    keys = sorted({(record.method, record.split_tag, record.class_name) for record in records})
    for method, split_tag, class_name in keys:
        group = tuple(
            record
            for record in records
            if record.method == method
            and record.split_tag == split_tag
            and record.class_name == class_name
        )
        margin = boundary_margin(group, "calibrated_score", class_name=class_name)
        margins.append(
            BoundaryMargin(
                class_name=f"{method}|{split_tag}|{margin.class_name}",
                score_field=margin.score_field,
                sample_count=margin.sample_count,
                positive_count=margin.positive_count,
                anomaly_count=margin.anomaly_count,
                max_positive_score=margin.max_positive_score,
                max_positive_sample_id=margin.max_positive_sample_id,
                min_anomaly_score=margin.min_anomaly_score,
                min_anomaly_sample_id=margin.min_anomaly_sample_id,
                margin=margin.margin,
                strict_pass=margin.strict_pass,
            )
        )
    return tuple(margins)


def write_failure_toplist_csv(records: Sequence[CalibrationRecord], path: Path) -> Path:
    """Write positive samples with highest calibrated scores."""

    rows = sorted(
        (record for record in records if record.label == 0),
        key=lambda record: (
            record.method,
            record.split_tag,
            record.class_name,
            -record.calibrated_score,
            record.sample_id,
        ),
    )
    fields = (
        "dataset_name",
        "method",
        "split_tag",
        "class_name",
        "sample_id",
        "label",
        "pasdf_score",
        "template_score",
        "registration_confidence",
        "assignment_entropy",
        "residual_overlap",
        "top1_top2_margin",
        "calibrated_score",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in rows:
            writer.writerow({field: getattr(record, field) for field in fields})
    return path


def write_config(args: argparse.Namespace, path: Path) -> Path:
    """Write config snapshot."""

    lines = [
        f"input_csv: {args.input_csv}",
        f"output_dir: {args.output_dir}",
        f"dataset_name: {args.dataset_name}",
        "classes:",
        *[f"  - {class_name}" for class_name in args.classes],
        "methods:",
        *[f"  - {method}" for method in args.methods],
        "split_modes:",
        *[f"  - {split_mode}" for split_mode in args.split_modes],
        "features:",
        *[f"  - {feature}" for feature in args.features],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_git_hash(path: Path) -> Path:
    """Write current git hash."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        value = "unknown"
    path.write_text(value + "\n", encoding="utf-8")
    return path


def write_readme(
    args: argparse.Namespace,
    path: Path,
    summaries: Sequence[CalibrationSummary],
) -> Path:
    """Write concise experiment README."""

    best_lines = []
    for summary in sorted(
        summaries,
        key=lambda item: (
            item.class_name,
            -999.0 if item.boundary_margin is None else -item.boundary_margin,
        ),
    )[:20]:
        best_lines.append(
            f"| {summary.method} | {summary.split_tag} | {summary.class_name} | "
            f"{summary.score_field} | "
            f"{_fmt(summary.object_auroc)} | {_fmt(summary.boundary_margin)} | "
            f"{summary.false_positive_top1_sample_id or ''} |"
        )
    lines = [
        "# P7-B Positive-aware Calibration",
        "",
        "## Command",
        "",
        "```bash",
        "PYTHONPATH=src python scripts/train_p7_calibration.py "
        f"--input-csv {args.input_csv} "
        f"--output-dir {args.output_dir} "
        f"--classes {' '.join(args.classes)}",
        "```",
        "",
        "## Summary Preview",
        "",
        "| method | split | class | score field | AUROC | boundary margin | false-positive top1 |",
        "|---|---|---|---|---:|---:|---|",
        *best_lines,
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _applicable_split_modes(method: str, split_modes: tuple[str, ...]) -> tuple[str, ...]:
    if method in {"pasdf_raw", "template_residual", "confidence_gate"}:
        return ("none",) if "none" in split_modes else ()
    return tuple(split_mode for split_mode in split_modes if split_mode != "none")


def _features_for_method(method: str, feature_names: tuple[str, ...]) -> tuple[str, ...]:
    if method == "isotonic_pasdf":
        return ("pasdf_score",)
    if method == "isotonic_gated":
        return ("gated_pasdf_score",)
    return feature_names


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
