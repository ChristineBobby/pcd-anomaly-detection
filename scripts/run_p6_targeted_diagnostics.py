"""Run P6 targeted registration diagnostics and PASDF/geometry fusion."""

from __future__ import annotations

import argparse
from pathlib import Path

from pcdad.analysis.targeted_p6 import (
    build_hybrid_records,
    build_registration_records,
    render_p6_targeted_summary,
    write_hybrid_scores_csv,
    write_registration_diagnostics_csv,
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
    args.summary_md.write_text(
        render_p6_targeted_summary(registration_records, hybrid_records),
        encoding="utf-8",
    )

    print(f"Wrote P6 targeted markdown to {args.summary_md}")
    print(f"Wrote P6 targeted summary CSV to {args.summary_csv}")
    print(f"Wrote registration diagnostics CSV to {registration_csv}")
    print(f"Wrote hybrid scores CSV to {hybrid_csv}")
    print(f"Wrote hybrid SVGs to {args.output_dir / 'tap1_hybrid_scores'}: {len(hybrid_records)}")


if __name__ == "__main__":
    main()
