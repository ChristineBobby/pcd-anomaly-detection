"""Plan PASDF registration diagnostics and voxel-size sweeps for P4."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pcdad.analysis.pasdf_failures import analyze_pasdf_failures
from pcdad.analysis.pasdf_registration import (
    DEFAULT_EXPERIMENT_CONFIG,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SWEEP_VOXEL_SIZES,
    RegistrationDiagnosticInputs,
    RegistrationDiagnostics,
    build_registration_diagnostics,
    render_registration_diagnostics_markdown,
)

DEFAULT_RESULTS = Path("experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv")
DEFAULT_LOG = Path("experiments/E1_pasdf_baseline/full_40cls/run.log")
DEFAULT_VOXEL_SIZES = Path("third_party/PASDF/config_files/voxel_sizes.yaml")
DEFAULT_OUTPUT = Path("docs/document/stage_record/2026-06-08_p4_registration_diagnostics.md")
DEFAULT_PRIORITY_CSV = Path("docs/document/stage_record/2026-06-08_p4_registration_priority.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS,
        help=f"PASDF evaluation_results.csv path. Default: {DEFAULT_RESULTS}",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG,
        help=f"PASDF run.log path. Default: {DEFAULT_LOG}",
    )
    parser.add_argument(
        "--voxel-sizes",
        type=Path,
        default=DEFAULT_VOXEL_SIZES,
        help=f"PASDF voxel_sizes.yaml path. Default: {DEFAULT_VOXEL_SIZES}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown diagnostics output path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--priority-csv",
        type=Path,
        default=DEFAULT_PRIORITY_CSV,
        help=f"Priority class CSV output path. Default: {DEFAULT_PRIORITY_CSV}",
    )
    parser.add_argument(
        "--sweep-voxel-sizes",
        type=float,
        nargs="+",
        default=list(DEFAULT_SWEEP_VOXEL_SIZES),
        help="Voxel sizes to include in generated sweep commands.",
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
        help=f"Experiment config used by sweep commands. Default: {DEFAULT_EXPERIMENT_CONFIG}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Sweep output root used by commands. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--max-classes",
        type=int,
        default=None,
        help="Limit priority classes included in the sweep plan.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    failure_summary = analyze_pasdf_failures(args.results, log_path=args.log)
    diagnostics = build_registration_diagnostics(
        RegistrationDiagnosticInputs(
            failure_summary=failure_summary,
            run_log=args.log,
            voxel_sizes_path=args.voxel_sizes,
            sweep_voxel_sizes=tuple(args.sweep_voxel_sizes),
            experiment_config=args.experiment_config,
            output_root=args.output_root,
            max_classes=args.max_classes,
        )
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_registration_diagnostics_markdown(diagnostics), encoding="utf-8")

    priority_csv = Path(args.priority_csv)
    priority_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_priority_csv(diagnostics, priority_csv)

    print(f"Wrote PASDF registration diagnostics to {output}")
    print(f"Wrote PASDF registration priority CSV to {priority_csv}")
    print(
        "PASDF registration diagnostics: "
        f"classes={len(diagnostics.priority_rows)} "
        f"warning_events={len(diagnostics.warning_events)} "
        f"warning_samples={len(diagnostics.warning_sample_rows)} "
        f"sweep_commands={len(diagnostics.sweep_commands)}"
    )
    print("priority_classes=" + ",".join(row.class_name for row in diagnostics.priority_rows))


def _write_priority_csv(diagnostics: RegistrationDiagnostics, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "class",
                "pixel_auc",
                "object_auc",
                "warning_count",
                "warning_sample_count",
                "official_voxel_size",
                "sweep_voxel_sizes",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in diagnostics.priority_rows:
            writer.writerow(
                {
                    "class": row.class_name,
                    "pixel_auc": row.pixel_auc,
                    "object_auc": row.object_auc,
                    "warning_count": row.warning_count,
                    "warning_sample_count": row.warning_sample_count,
                    "official_voxel_size": row.official_voxel_size,
                    "sweep_voxel_sizes": " ".join(
                        f"{value:.3f}" for value in row.sweep_voxel_sizes
                    ),
                }
            )


if __name__ == "__main__":
    main()
