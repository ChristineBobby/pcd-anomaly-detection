"""Analyze PASDF evaluation results for P4 failure analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from pcdad.analysis.pasdf_failures import (
    FailureThresholds,
    analyze_pasdf_failures,
    render_failure_report_markdown,
)

DEFAULT_RESULTS = Path("experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv")
DEFAULT_LOG = Path("experiments/E1_pasdf_baseline/full_40cls/run.log")
DEFAULT_OUTPUT = Path("docs/document/stage_record/2026-06-08_p4_failure_summary.md")


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
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Markdown summary output path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--pixel-threshold",
        type=float,
        default=0.85,
        help="Flag classes with pixel AUROC below this value.",
    )
    parser.add_argument(
        "--object-threshold",
        type=float,
        default=0.8,
        help="Flag classes with object AUROC below this value.",
    )
    parser.add_argument(
        "--title",
        default="P4 PASDF Failure Analysis Summary",
        help="Markdown report title.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = analyze_pasdf_failures(
        args.results,
        log_path=args.log,
        thresholds=FailureThresholds(
            pixel_auc=args.pixel_threshold,
            object_auc=args.object_threshold,
        ),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_failure_report_markdown(summary, title=args.title),
        encoding="utf-8",
    )
    print(f"Wrote PASDF failure summary to {output}")
    print(
        "PASDF failure summary: "
        f"classes={summary.class_count} "
        f"mean_pixel_auc={summary.mean_pixel_auc:.6f} "
        f"mean_object_auc={summary.mean_object_auc:.6f} "
        f"open3d_warnings={summary.open3d_warnings.total_count}"
    )
    print(f"priority_classes={','.join(summary.priority_classes)}")


if __name__ == "__main__":
    main()
