"""Run P6 failure-mode closure diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path

from pcdad.analysis.failure_modes import (
    build_boundary_record,
    build_failure_mode_closure_records,
    build_weak_localization_records,
    classify_cap3_template_mismatch,
    render_failure_mode_closure_markdown,
    write_combined_failure_mode_records_csv,
    write_failure_mode_closure_csv,
)
from pcdad.analysis.pasdf_calibration import (
    build_pasdf_topk_calibration_records,
    summarize_pasdf_calibration,
)
from pcdad.analysis.targeted_p6 import compute_cap3_residual_region_record

DEFAULT_SCORE_ROOT = Path("experiments/P5_pasdf_scores/representative")
DEFAULT_TEMPLATE_ROOT = Path("third_party/PASDF/data/ShapeNetAD")
DEFAULT_CLASSES = ("cap3", "tap1", "helmet1")
DEFAULT_TOP_RATIO = 0.01
DEFAULT_CAP3_SAMPLES = (
    "cap3_positive9",
    "cap3_positive7",
    "cap3_positive10",
    "cap3_hole0",
    "cap3_hole1",
    "cap3_broken2",
    "cap3_broken3",
)
DEFAULT_RECORDS_CSV = Path("experiments/P6_failure_mode_closure/failure_mode_closure_records.csv")
DEFAULT_SUMMARY_CSV = Path("docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv")
DEFAULT_SUMMARY_MD = Path("docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, default=DEFAULT_SCORE_ROOT)
    parser.add_argument("--template-root", type=Path, default=DEFAULT_TEMPLATE_ROOT)
    parser.add_argument("--classes", nargs="+", default=list(DEFAULT_CLASSES))
    parser.add_argument("--top-ratio", type=float, default=DEFAULT_TOP_RATIO)
    parser.add_argument("--cap3-samples", nargs="+", default=list(DEFAULT_CAP3_SAMPLES))
    parser.add_argument("--records-csv", type=Path, default=DEFAULT_RECORDS_CSV)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    classes = tuple(args.classes)
    score_paths = _collect_score_paths(args.score_root, classes)
    calibration_records = build_pasdf_topk_calibration_records(
        score_paths=score_paths,
        top_ratios=(args.top_ratio,),
    )
    calibration_summaries = summarize_pasdf_calibration(calibration_records)
    closures = build_failure_mode_closure_records(calibration_summaries)
    boundaries = tuple(
        build_boundary_record(
            calibration_records,
            class_name=class_name,
            top_ratio=args.top_ratio,
        )
        for class_name in classes
    )
    weak_records = tuple(
        weak_record
        for class_name in classes
        for weak_record in build_weak_localization_records(
            calibration_records,
            class_name=class_name,
            top_ratio=args.top_ratio,
        )
    )
    cap3_records = tuple(
        classify_cap3_template_mismatch(
            compute_cap3_residual_region_record(
                score_path=_find_sample_npz(args.score_root, sample_id),
                template_root=args.template_root,
                top_ratio=args.top_ratio,
            )
        )
        for sample_id in args.cap3_samples
    )

    write_combined_failure_mode_records_csv(
        closures=closures,
        boundaries=boundaries,
        weak_records=weak_records,
        cap3_records=cap3_records,
        path=args.records_csv,
    )
    write_failure_mode_closure_csv(closures, args.summary_csv)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(
        render_failure_mode_closure_markdown(
            closures=closures,
            boundaries=boundaries,
            weak_records=weak_records,
            cap3_records=cap3_records,
        ),
        encoding="utf-8",
    )
    print(f"Wrote failure mode closure records CSV to {args.records_csv}")
    print(f"Wrote failure mode closure summary CSV to {args.summary_csv}")
    print(f"Wrote failure mode closure markdown to {args.summary_md}")
    print(f"Processed {len(calibration_records)} calibration records")


def _collect_score_paths(score_root: Path, classes: tuple[str, ...]) -> tuple[Path, ...]:
    paths: list[Path] = []
    for class_name in classes:
        class_dir = score_root / class_name / "points"
        class_paths = sorted(class_dir.glob("*.npz"))
        if not class_paths:
            raise FileNotFoundError(f"No PASDF point-score NPZ files found under {class_dir}")
        paths.extend(class_paths)
    return tuple(paths)


def _find_sample_npz(score_root: Path, sample_id: str) -> Path:
    matches = sorted(score_root.glob(f"*/points/{sample_id}.npz"))
    if not matches:
        raise FileNotFoundError(f"Could not find PASDF point-score NPZ for sample: {sample_id}")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise ValueError(f"Multiple PASDF point-score NPZ files matched {sample_id}: {joined}")
    return matches[0]


if __name__ == "__main__":
    main()
