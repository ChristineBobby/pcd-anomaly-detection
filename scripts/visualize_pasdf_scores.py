"""Visualize targeted PASDF point-score NPZ files for P5 case studies."""

from __future__ import annotations

import argparse
from pathlib import Path

from pcdad.analysis.pasdf_case_study import (
    PasdfCaseStudySpec,
    render_case_study_markdown,
    run_pasdf_case_study,
    write_case_study_csv,
)

DEFAULT_SCORE_ROOT = Path("experiments/P5_pasdf_scores/representative")
DEFAULT_TEMPLATE_ROOT = Path("third_party/PASDF/data/ShapeNetAD")
DEFAULT_OUTPUT_DIR = Path("experiments/P5_case_study")
DEFAULT_SUMMARY_MD = Path("docs/document/stage_record/2026-06-13_p5_targeted_case_study.md")
DEFAULT_SUMMARY_CSV = Path("docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv")
DEFAULT_SAMPLES = (
    "cap3_positive9",
    "cap3_positive7",
    "cap3_positive10",
    "cap3_hole0",
    "cap3_hole1",
    "cap3_broken2",
    "cap3_broken3",
    "helmet1_concavity2",
    "helmet1_concavity4",
    "helmet1_concavity3",
    "tap1_broken2",
    "tap1_broken3",
    "tap1_hole0",
)
DEFAULT_TEMPLATE_OVERLAY_SAMPLES = (
    "cap3_positive9",
    "cap3_positive7",
    "cap3_positive10",
)
DEFAULT_GEOMETRY_COMPARISON_SAMPLES = (
    "tap1_broken2",
    "tap1_broken3",
    "tap1_hole0",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--score-root",
        type=Path,
        default=DEFAULT_SCORE_ROOT,
        help=f"P5 PASDF score root. Default: {DEFAULT_SCORE_ROOT}",
    )
    parser.add_argument(
        "--samples",
        nargs="+",
        default=list(DEFAULT_SAMPLES),
        help="Sample ids to visualize.",
    )
    parser.add_argument(
        "--template-root",
        type=Path,
        default=DEFAULT_TEMPLATE_ROOT,
        help=f"PASDF ShapeNetAD template root. Default: {DEFAULT_TEMPLATE_ROOT}",
    )
    parser.add_argument(
        "--template-overlay-samples",
        nargs="*",
        default=list(DEFAULT_TEMPLATE_OVERLAY_SAMPLES),
        help="Sample ids that should also get sample/template overlay SVGs.",
    )
    parser.add_argument(
        "--geometry-comparison-samples",
        nargs="*",
        default=list(DEFAULT_GEOMETRY_COMPARISON_SAMPLES),
        help="Sample ids that should also get PASDF-vs-geometry comparison SVGs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"SVG output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=DEFAULT_SUMMARY_MD,
        help=f"Markdown summary path. Default: {DEFAULT_SUMMARY_MD}",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=DEFAULT_SUMMARY_CSV,
        help=f"CSV summary path. Default: {DEFAULT_SUMMARY_CSV}",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=4096,
        help="Maximum points per SVG. Default: 4096",
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic SVG sample seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = run_pasdf_case_study(
        PasdfCaseStudySpec(
            score_root=args.score_root,
            sample_ids=tuple(args.samples),
            output_dir=args.output_dir,
            template_root=args.template_root,
            overlay_sample_ids=tuple(args.template_overlay_samples),
            comparison_sample_ids=tuple(args.geometry_comparison_samples),
            max_points=args.max_points,
            seed=args.seed,
        )
    )
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(render_case_study_markdown(records), encoding="utf-8")
    write_case_study_csv(records, args.summary_csv)
    print(f"Wrote PASDF case-study markdown to {args.summary_md}")
    print(f"Wrote PASDF case-study CSV to {args.summary_csv}")
    print(f"Wrote PASDF case-study SVGs to {args.output_dir}: {len(records)}")


if __name__ == "__main__":
    main()
