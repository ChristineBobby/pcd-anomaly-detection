"""Run the default P4 geometry smoke analysis."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import yaml

from pcdad.analysis.sample_geometry import (
    ClassGeometrySummary,
    GeometryAnalysisSpec,
    analyze_class_geometry_samples,
    render_geometry_smoke_markdown,
    sample_geometry_rows_to_dicts,
    write_geometry_smoke_svgs,
)
from pcdad.scoring.geometric import GeometryScoreConfig

DEFAULT_DATASET_ROOT = Path("data/Anomaly-ShapeNet-v2/dataset/16384")
DEFAULT_CLASSES = ("cap3", "cap4", "tap1")
DEFAULT_STAGE_RECORD_DIR = Path("docs/document/stage_record")
DEFAULT_BASENAME = "2026-06-08_p4_geometry_smoke_summary"
CONFIG_DATE_PREFIX = "2026-06-09"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional experiment YAML containing experiment.geometry_smoke settings.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        help=f"Fixed-size ShapeNetAD dataset root. Default: {DEFAULT_DATASET_ROOT}",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=None,
        help=f"Classes to analyze. Default: {' '.join(DEFAULT_CLASSES)}",
    )
    parser.add_argument("--max-samples", type=int, default=None, help="Max samples per class.")
    parser.add_argument("--k-normal", type=int, default=None, help="PCA normal k.")
    parser.add_argument(
        "--k-curvature",
        type=int,
        nargs="+",
        default=None,
        help="PCA curvature k values.",
    )
    parser.add_argument("--topk-ratio", type=float, default=None, help="Object top-k ratio.")
    parser.add_argument(
        "--distance-only",
        action="store_true",
        help="Disable normal and curvature components for a fast distance-only smoke.",
    )
    parser.add_argument(
        "--stage-record-dir",
        type=Path,
        default=DEFAULT_STAGE_RECORD_DIR,
        help=f"Stage record output directory. Default: {DEFAULT_STAGE_RECORD_DIR}",
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
        help="Maximum points per SVG when --svg-dir is provided.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = _load_config_with_defaults(args.config) if args.config is not None else {}
    options = _resolve_options(args, config)
    summaries = tuple(
        analyze_class_geometry_samples(
            GeometryAnalysisSpec(
                dataset_root=options.dataset_root,
                class_name=class_name,
                max_samples=options.max_samples,
                k_normal=options.k_normal,
                k_curvature=options.k_curvature,
                topk_ratio=options.topk_ratio,
                use_normals=options.use_normals,
                use_curvature=options.use_curvature,
                score_config=options.score_config,
            )
        )
        for class_name in options.classes
    )
    stage_record_dir = Path(args.stage_record_dir)
    basename = options.output_basename
    markdown_path = stage_record_dir / f"{basename}.md"
    csv_path = stage_record_dir / f"{basename}.csv"
    _write_outputs(summaries, markdown_path, csv_path)
    svg_count = 0
    if args.svg_dir is not None:
        svg_outputs = write_geometry_smoke_svgs(
            summaries,
            args.svg_dir,
            max_points=args.svg_max_points,
        )
        svg_count = len(svg_outputs)
    sample_count = sum(summary.sample_count for summary in summaries)
    print(f"Wrote geometry smoke summary to {markdown_path}")
    print(f"Wrote geometry smoke CSV to {csv_path}")
    if args.svg_dir is not None:
        print(f"Wrote geometry smoke SVGs to {args.svg_dir}: {svg_count}")
    print(
        "Geometry smoke summary: "
        f"experiment={options.experiment_label} "
        f"classes={len(summaries)} samples={sample_count}"
    )


class GeometrySmokeOptions:
    def __init__(
        self,
        *,
        dataset_root: Path,
        classes: tuple[str, ...],
        max_samples: int,
        k_normal: int,
        k_curvature: tuple[int, ...],
        topk_ratio: float,
        use_normals: bool,
        use_curvature: bool,
        score_config: GeometryScoreConfig,
        experiment_label: str,
        output_basename: str,
    ) -> None:
        self.dataset_root = dataset_root
        self.classes = classes
        self.max_samples = max_samples
        self.k_normal = k_normal
        self.k_curvature = k_curvature
        self.topk_ratio = topk_ratio
        self.use_normals = use_normals
        self.use_curvature = use_curvature
        self.score_config = score_config
        self.experiment_label = experiment_label
        self.output_basename = output_basename


def _resolve_options(args: argparse.Namespace, config: dict[str, Any]) -> GeometrySmokeOptions:
    experiment = _section(config, "experiment")
    smoke = experiment.get("geometry_smoke", {})
    smoke = smoke if isinstance(smoke, dict) else {}
    components = smoke.get("components", {})
    components = components if isinstance(components, dict) else {}
    score = smoke.get("score", {})
    score = score if isinstance(score, dict) else {}
    dataset = _section(config, "dataset")

    experiment_id = str(experiment.get("id", "P4"))
    experiment_name = str(experiment.get("name", "geometry_smoke"))
    experiment_label = f"{experiment_id}_{experiment_name}"
    output_basename = (
        DEFAULT_BASENAME
        if args.config is None
        else f"{CONFIG_DATE_PREFIX}_{_slugify(experiment_label)}_geometry_smoke_summary"
    )

    dataset_root = args.dataset_root
    if dataset_root is None:
        dataset_root = _dataset_root_from_config(dataset)

    classes = args.classes
    if classes is None:
        classes = smoke.get("classes", list(DEFAULT_CLASSES))

    distance_only = bool(args.distance_only)
    use_normals = bool(components.get("normal", True))
    use_curvature = bool(components.get("curvature", True))
    if distance_only:
        use_normals = False
        use_curvature = False

    return GeometrySmokeOptions(
        dataset_root=Path(dataset_root),
        classes=tuple(str(class_name) for class_name in classes),
        max_samples=int(
            args.max_samples if args.max_samples is not None else smoke.get("max_samples", 4)
        ),
        k_normal=int(args.k_normal if args.k_normal is not None else smoke.get("k_normal", 32)),
        k_curvature=tuple(
            int(value)
            for value in (
                args.k_curvature
                if args.k_curvature is not None
                else smoke.get("k_curvature", [16, 32, 64])
            )
        ),
        topk_ratio=float(
            args.topk_ratio if args.topk_ratio is not None else smoke.get("topk_ratio", 0.05)
        ),
        use_normals=use_normals,
        use_curvature=use_curvature,
        score_config=GeometryScoreConfig(
            distance_weight=float(score.get("distance_weight", 1.0)),
            normal_weight=float(score.get("normal_weight", 0.5)),
            curvature_weight=float(score.get("curvature_weight", 0.5)),
            topk_ratio=float(
                args.topk_ratio if args.topk_ratio is not None else smoke.get("topk_ratio", 0.05)
            ),
            smooth_k=int(score.get("smooth_k", 0)),
        ),
        experiment_label=experiment_label,
        output_basename=output_basename,
    )


def _dataset_root_from_config(dataset: dict[str, Any]) -> Path:
    pasdf_dir = dataset.get("pasdf_dir")
    if pasdf_dir is not None:
        return Path(str(pasdf_dir))
    root = Path(str(dataset.get("root", DEFAULT_DATASET_ROOT.parent.parent)))
    target_num_points = str(dataset.get("target_num_points", 16384))
    return root / "dataset" / target_num_points


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise SystemExit(f"Config must be a YAML mapping: {path}")
    return payload


def _load_config_with_defaults(path: Path) -> dict[str, Any]:
    config = _load_yaml(path)
    defaults = config.get("defaults", [])
    if defaults is None:
        defaults = []
    if not isinstance(defaults, list):
        raise SystemExit(f"Config defaults must be a list: {path}")

    merged: dict[str, Any] = {}
    for item in defaults:
        if not isinstance(item, str):
            raise SystemExit(f"Only string defaults are supported in {path}: {item!r}")
        default_path = (path.parent / item).resolve()
        merged = _deep_merge(merged, _load_config_with_defaults(default_path))
    local = dict(config)
    local.pop("defaults", None)
    return _deep_merge(merged, local)


def _section(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key, {})
    return value if isinstance(value, dict) else {}


def _slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def _write_outputs(
    summaries: tuple[ClassGeometrySummary, ...],
    markdown_path: Path,
    csv_path: Path,
) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_geometry_smoke_markdown(summaries), encoding="utf-8")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
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
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in sample_geometry_rows_to_dicts(summaries):
            writer.writerow(row)


if __name__ == "__main__":
    main()
