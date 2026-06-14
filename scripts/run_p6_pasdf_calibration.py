"""Run P6 PASDF top-k calibration diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from pcdad.analysis.pasdf_calibration import (
    build_pasdf_topk_calibration_records,
    render_pasdf_calibration_markdown,
    summarize_pasdf_calibration,
    write_pasdf_calibration_records_csv,
    write_pasdf_calibration_summary_csv,
)

DEFAULT_SCORE_ROOT = Path("experiments/P5_pasdf_scores/representative")
DEFAULT_CLASSES = ("cap3", "tap1", "helmet1")
DEFAULT_TOP_RATIOS = (0.01, 0.02, 0.05, 0.10)
DEFAULT_RECORDS_CSV = Path("experiments/P6_pasdf_calibration/topk_calibration_records.csv")
DEFAULT_SUMMARY_CSV = Path("docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.csv")
DEFAULT_SUMMARY_MD = Path("docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--classes", nargs="+", default=list(DEFAULT_CLASSES))
    parser.add_argument("--top-ratios", nargs="+", type=float, default=list(DEFAULT_TOP_RATIOS))
    parser.add_argument("--records-csv", type=Path, default=DEFAULT_RECORDS_CSV)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    score_paths = _collect_score_paths(args.score_root, tuple(args.classes))
    records = build_pasdf_topk_calibration_records(
        score_paths=score_paths,
        top_ratios=tuple(args.top_ratios),
    )
    summaries = summarize_pasdf_calibration(records)
    write_pasdf_calibration_records_csv(records, args.records_csv)
    write_pasdf_calibration_summary_csv(summaries, args.summary_csv)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(
        render_pasdf_calibration_markdown(records=records, summaries=summaries),
        encoding="utf-8",
    )
    print(f"Wrote PASDF calibration records CSV to {args.records_csv}")
    print(f"Wrote PASDF calibration summary CSV to {args.summary_csv}")
    print(f"Wrote PASDF calibration markdown to {args.summary_md}")
    print(f"Processed {len(records)} records from {len(score_paths)} score files")


def _collect_score_paths(score_root: Path, classes: tuple[str, ...]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for class_name in classes:
        class_dir = score_root / class_name / "points"
        class_paths = sorted(class_dir.glob("*.npz"))
        if not class_paths:
            raise FileNotFoundError(f"No PASDF point-score NPZ files found under {class_dir}")
        paths.extend(class_paths)
    return tuple(paths)


if __name__ == "__main__":
    main()
