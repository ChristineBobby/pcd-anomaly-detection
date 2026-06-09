"""Summarize repeated PASDF runs for stability checks."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pcdad.analysis.pasdf_stability import (
    PasdfRunRecord,
    PasdfStabilitySummary,
    StabilityCollectionSpec,
    collect_pasdf_stability_runs,
    render_stability_markdown,
)

DEFAULT_ROOT = Path("experiments/P4_stability")
DEFAULT_OUTPUT = Path("docs/document/stage_record/2026-06-08_p4_stability_summary.md")
DEFAULT_CSV = Path("docs/document/stage_record/2026-06-08_p4_stability_summary.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"PASDF stability output root. Default: {DEFAULT_ROOT}",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        required=True,
        help="Classes to collect from the stability root.",
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
    summary = collect_pasdf_stability_runs(
        StabilityCollectionSpec(root=args.root, classes=tuple(args.classes))
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_stability_markdown(summary), encoding="utf-8")

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_stability_csv(summary, csv_path)

    print(f"Wrote PASDF stability summary to {output}")
    print(f"Wrote PASDF stability CSV to {csv_path}")
    print(
        "PASDF stability summary: " f"classes={len(summary.by_class)} " f"runs={len(summary.rows)}"
    )


def _write_stability_csv(summary: PasdfStabilitySummary, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "class",
                "run_id",
                "pixel_auc",
                "object_auc",
                "warning_count",
                "warning_sample_count",
                "run_dir",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in summary.rows:
            writer.writerow(_row_to_csv(row))


def _row_to_csv(row: PasdfRunRecord) -> dict[str, object]:
    return {
        "class": row.class_name,
        "run_id": row.run_id,
        "pixel_auc": row.pixel_auc,
        "object_auc": row.object_auc,
        "warning_count": row.warning_count,
        "warning_sample_count": row.warning_sample_count,
        "run_dir": row.run_dir,
    }


if __name__ == "__main__":
    main()
