"""Summarize PASDF voxel-size sweep runs for P4 analysis."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pcdad.analysis.pasdf_sweep import (
    SweepCollectionSpec,
    SweepResultRow,
    SweepSummary,
    collect_pasdf_sweep_results,
    render_sweep_summary_markdown,
)

DEFAULT_ROOT = Path("experiments/P4_registration_sweep")
DEFAULT_OUTPUT = Path("docs/document/stage_record/2026-06-08_p4_voxel_sweep_summary.md")
DEFAULT_CSV = Path("docs/document/stage_record/2026-06-08_p4_voxel_sweep_summary.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"PASDF sweep output root. Default: {DEFAULT_ROOT}",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        required=True,
        help="Classes to collect from the sweep root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown summary output path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV summary output path. Default: {DEFAULT_CSV}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = collect_pasdf_sweep_results(
        SweepCollectionSpec(root=args.root, classes=tuple(args.classes))
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_sweep_summary_markdown(summary), encoding="utf-8")

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_sweep_csv(summary, csv_path)

    print(f"Wrote PASDF sweep summary to {output}")
    print(f"Wrote PASDF sweep CSV to {csv_path}")
    print(
        "PASDF sweep summary: " f"runs={len(summary.rows)} " f"classes={len(summary.best_by_class)}"
    )
    print(
        "best_voxels="
        + ",".join(
            f"{class_name}:{row.voxel_size:.3f}"
            for class_name, row in summary.best_by_class.items()
        )
    )


def _write_sweep_csv(summary: SweepSummary, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "class",
                "voxel_size",
                "pixel_auc",
                "object_auc",
                "warning_count",
                "warning_sample_count",
                "is_best_object_auc",
                "run_dir",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in summary.rows:
            writer.writerow(_row_to_csv(row, summary.best_by_class))


def _row_to_csv(row: SweepResultRow, best_by_class: dict[str, SweepResultRow]) -> dict[str, object]:
    best = best_by_class.get(row.class_name)
    return {
        "class": row.class_name,
        "voxel_size": row.voxel_size,
        "pixel_auc": row.pixel_auc,
        "object_auc": row.object_auc,
        "warning_count": row.warning_count,
        "warning_sample_count": row.warning_sample_count,
        "is_best_object_auc": best == row,
        "run_dir": row.run_dir,
    }


if __name__ == "__main__":
    main()
