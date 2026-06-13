"""Run P6 targeted registration diagnostics and PASDF/geometry fusion."""

from __future__ import annotations

import argparse
from pathlib import Path

from pcdad.analysis.targeted_p6 import (
    build_cap3_residual_region_records,
    build_hybrid_records,
    build_registration_records,
    build_tap1_region_explanation_records,
    render_alpha_sweep_markdown,
    render_p6_targeted_summary,
    render_region_explanation_markdown,
    run_alpha_sweep,
    summarize_alpha_sweep,
    write_alpha_sweep_records_csv,
    write_alpha_sweep_summary_csv,
    write_cap3_residual_region_csv,
    write_hybrid_scores_csv,
    write_region_explanation_csv,
    write_registration_diagnostics_csv,
    write_tap1_region_explanation_csv,
)

DEFAULT_SCORE_ROOT = Path("experiments/P5_pasdf_scores/representative")
DEFAULT_TEMPLATE_ROOT = Path("third_party/PASDF/data/ShapeNetAD")
DEFAULT_OUTPUT_DIR = Path("experiments/P6_targeted_diagnostics")
DEFAULT_SUMMARY_MD = Path(
    "docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md"
)
DEFAULT_SUMMARY_CSV = Path(
    "docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.csv"
)
DEFAULT_ALPHA_SWEEP_CSV = Path("experiments/P6_alpha_sweep/tap1_alpha_sweep_records.csv")
DEFAULT_ALPHA_SWEEP_SUMMARY_CSV = Path(
    "docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv"
)
DEFAULT_REGION_OUTPUT_DIR = Path("experiments/P6_region_explanation")
DEFAULT_REGION_SUMMARY_MD = Path(
    "docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md"
)
DEFAULT_REGION_SUMMARY_CSV = Path(
    "docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv"
)
DEFAULT_CAP3_SAMPLES = (
    "cap3_positive9",
    "cap3_positive7",
    "cap3_positive10",
    "cap3_hole0",
    "cap3_hole1",
    "cap3_broken2",
    "cap3_broken3",
)
DEFAULT_TAP1_SAMPLES = (
    "tap1_broken2",
    "tap1_broken3",
    "tap1_hole0",
)
DEFAULT_TAP1_POSITIVE_SAMPLES = ("tap1_positive0",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--template-root", type=Path, default=DEFAULT_TEMPLATE_ROOT)
    parser.add_argument("--cap3-samples", nargs="+", default=list(DEFAULT_CAP3_SAMPLES))
    parser.add_argument("--tap1-samples", nargs="+", default=list(DEFAULT_TAP1_SAMPLES))
    parser.add_argument(
        "--tap1-positive-samples",
        nargs="*",
        default=list(DEFAULT_TAP1_POSITIVE_SAMPLES),
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument(
        "--alpha-grid",
        nargs="*",
        type=float,
        default=[],
        help="Optional alpha values for positive-aware sweep.",
    )
    parser.add_argument("--alpha-sweep-csv", type=Path, default=DEFAULT_ALPHA_SWEEP_CSV)
    parser.add_argument(
        "--alpha-sweep-summary-csv",
        type=Path,
        default=DEFAULT_ALPHA_SWEEP_SUMMARY_CSV,
    )
    parser.add_argument(
        "--run-region-explanation",
        action="store_true",
        help="Run cap3 residual region and tap1 top-k locality diagnostics.",
    )
    parser.add_argument("--region-output-dir", type=Path, default=DEFAULT_REGION_OUTPUT_DIR)
    parser.add_argument("--region-summary-md", type=Path, default=DEFAULT_REGION_SUMMARY_MD)
    parser.add_argument("--region-summary-csv", type=Path, default=DEFAULT_REGION_SUMMARY_CSV)
    parser.add_argument("--top-ratio", type=float, default=0.05)
    parser.add_argument("--neighbor-radius-ratio", type=float, default=0.02)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--max-points", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registration_records = build_registration_records(
        score_root=args.score_root,
        template_root=args.template_root,
        sample_ids=tuple(args.cap3_samples),
    )
    hybrid_records = build_hybrid_records(
        score_root=args.score_root,
        template_root=args.template_root,
        sample_ids=tuple(args.tap1_samples) + tuple(args.tap1_positive_samples),
        output_dir=args.output_dir,
        alpha=args.alpha,
        max_points=args.max_points,
        seed=args.seed,
    )

    registration_csv = args.output_dir / "cap3_registration_diagnostics.csv"
    hybrid_csv = args.output_dir / "tap1_hybrid_scores.csv"
    write_registration_diagnostics_csv(registration_records, registration_csv)
    write_hybrid_scores_csv(hybrid_records, hybrid_csv)
    write_hybrid_scores_csv(hybrid_records, args.summary_csv)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_p6_targeted_summary(registration_records, hybrid_records)
    if args.alpha_grid:
        alpha_records = run_alpha_sweep(
            score_root=args.score_root,
            template_root=args.template_root,
            anomaly_sample_ids=tuple(args.tap1_samples),
            positive_sample_ids=tuple(args.tap1_positive_samples),
            alpha_grid=tuple(args.alpha_grid),
        )
        alpha_summaries = summarize_alpha_sweep(alpha_records)
        write_alpha_sweep_records_csv(alpha_records, args.alpha_sweep_csv)
        write_alpha_sweep_summary_csv(alpha_summaries, args.alpha_sweep_summary_csv)
        markdown = (
            markdown.rstrip()
            + "\n\n"
            + render_alpha_sweep_markdown(alpha_summaries).rstrip()
            + "\n"
        )
        print(f"Wrote alpha sweep records CSV to {args.alpha_sweep_csv}")
        print(f"Wrote alpha sweep summary CSV to {args.alpha_sweep_summary_csv}")
    args.summary_md.write_text(markdown, encoding="utf-8")

    if args.run_region_explanation:
        cap3_region_records = build_cap3_residual_region_records(
            score_root=args.score_root,
            template_root=args.template_root,
            sample_ids=tuple(args.cap3_samples),
            top_ratio=args.top_ratio,
        )
        tap1_region_records = build_tap1_region_explanation_records(
            score_root=args.score_root,
            template_root=args.template_root,
            sample_ids=tuple(args.tap1_samples),
            top_ratio=args.top_ratio,
            neighbor_radius_ratio=args.neighbor_radius_ratio,
        )
        cap3_region_csv = args.region_output_dir / "cap3_residual_regions.csv"
        tap1_region_csv = args.region_output_dir / "tap1_region_explanation.csv"
        write_cap3_residual_region_csv(cap3_region_records, cap3_region_csv)
        write_tap1_region_explanation_csv(tap1_region_records, tap1_region_csv)
        write_region_explanation_csv(
            tap1_records=tap1_region_records,
            cap3_records=cap3_region_records,
            path=args.region_summary_csv,
        )
        args.region_summary_md.parent.mkdir(parents=True, exist_ok=True)
        args.region_summary_md.write_text(
            render_region_explanation_markdown(
                tap1_records=tap1_region_records,
                cap3_records=cap3_region_records,
            ),
            encoding="utf-8",
        )
        print(f"Wrote region explanation markdown to {args.region_summary_md}")
        print(f"Wrote region explanation summary CSV to {args.region_summary_csv}")
        print(f"Wrote cap3 residual region CSV to {cap3_region_csv}")
        print(f"Wrote tap1 region explanation CSV to {tap1_region_csv}")

    print(f"Wrote P6 targeted markdown to {args.summary_md}")
    print(f"Wrote P6 targeted summary CSV to {args.summary_csv}")
    print(f"Wrote registration diagnostics CSV to {registration_csv}")
    print(f"Wrote hybrid scores CSV to {hybrid_csv}")
    print(f"Wrote hybrid SVGs to {args.output_dir / 'tap1_hybrid_scores'}: {len(hybrid_records)}")


if __name__ == "__main__":
    main()
