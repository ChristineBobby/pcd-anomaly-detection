"""Analyze sample-level geometry residuals for P4 smoke checks."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pcdad.analysis.sample_geometry import (
    ClassGeometrySummary,
    GeometryAnalysisSpec,
    analyze_class_geometry_samples,
    render_geometry_smoke_markdown,
    sample_geometry_rows_to_dicts,
    write_geometry_smoke_svgs,
)

DEFAULT_DATASET_ROOT = Path("data/Anomaly-ShapeNet-v2/dataset/16384")
DEFAULT_OUTPUT = Path("docs/document/stage_record/2026-06-08_p4_geometry_smoke_summary.md")
DEFAULT_CSV = Path("docs/document/stage_record/2026-06-08_p4_geometry_smoke_summary.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
        help=f"Fixed-size ShapeNetAD dataset root. Default: {DEFAULT_DATASET_ROOT}",
    )
    parser.add_argument("--classes", nargs="+", required=True, help="Classes to analyze.")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=4,
        help="Maximum test samples per class. Default: 4",
    )
    parser.add_argument("--k-normal", type=int, default=32, help="PCA normal k. Default: 32")
    parser.add_argument(
        "--k-curvature",
        type=int,
        nargs="+",
        default=[16, 32, 64],
        help="PCA curvature k values. Default: 16 32 64",
    )
    parser.add_argument(
        "--topk-ratio",
        type=float,
        default=0.05,
        help="Object score top-k ratio. Default: 0.05",
    )
    parser.add_argument(
        "--distance-only",
        action="store_true",
        help="Disable normal and curvature components for a fast distance-only smoke.",
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
    parser.add_argument(
        "--svg-dir",
        type=Path,
        default=None,
        help="Optional directory for deterministic GT SVG overlays.",
    )
    parser.add_argument(
        "--svg-max-points",
        type=int,
        default=4096,
        help="Maximum points per SVG when --svg-dir is provided. Default: 4096",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summaries = tuple(
        analyze_class_geometry_samples(
            GeometryAnalysisSpec(
                dataset_root=args.dataset_root,
                class_name=class_name,
                max_samples=args.max_samples,
                k_normal=args.k_normal,
                k_curvature=tuple(args.k_curvature),
                topk_ratio=args.topk_ratio,
                use_normals=not args.distance_only,
                use_curvature=not args.distance_only,
            )
        )
        for class_name in args.classes
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_geometry_smoke_markdown(summaries), encoding="utf-8")

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _write_geometry_csv(summaries, csv_path)
    svg_count = 0
    if args.svg_dir is not None:
        svg_outputs = write_geometry_smoke_svgs(
            summaries,
            args.svg_dir,
            max_points=args.svg_max_points,
        )
        svg_count = len(svg_outputs)

    sample_count = sum(summary.sample_count for summary in summaries)
    print(f"Wrote geometry smoke summary to {output}")
    print(f"Wrote geometry smoke CSV to {csv_path}")
    if args.svg_dir is not None:
        print(f"Wrote geometry smoke SVGs to {args.svg_dir}: {svg_count}")
    print(f"Geometry smoke summary: classes={len(summaries)} samples={sample_count}")


def _write_geometry_csv(summaries: tuple[ClassGeometrySummary, ...], path: Path) -> None:
    fieldnames = [
        "class",
        "template_sample_id",
        "sample_id",
        "anomaly_type",
        "is_anomaly",
        "gt_anomaly_points",
        "point_count",
        "object_score",
        "max_point_score",
        "mean_nn_distance",
        "max_nn_distance",
        "gt_point_score_mean",
        "bg_point_score_mean",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in sample_geometry_rows_to_dicts(summaries):
            writer.writerow(row)


if __name__ == "__main__":
    main()
