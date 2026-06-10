"""Export PASDF per-sample and optional per-point scores for P5 analysis."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import yaml  # type: ignore[import-untyped]

from pcdad.analysis.pasdf_scores import (
    PasdfSampleScore,
    render_score_export_markdown,
    summarize_point_scores,
    write_sample_scores_csv,
)

DEFAULT_CONFIG = Path("experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml")
DEFAULT_PASDF_ROOT = Path("third_party/PASDF")
DEFAULT_OUTPUT_DIR = Path("experiments/P5_pasdf_scores")
DEFAULT_SUMMARY_MD = Path("docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md")
DEFAULT_SUMMARY_CSV = Path(
    "docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"PASDF ShapeNetAD evaluation YAML. Default: {DEFAULT_CONFIG}",
    )
    parser.add_argument(
        "--pasdf-root",
        type=Path,
        default=DEFAULT_PASDF_ROOT,
        help=f"Official PASDF repository root. Default: {DEFAULT_PASDF_ROOT}",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=None,
        help="Optional class subset. Default: classes from PASDF config.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Experiment output directory. Default: {DEFAULT_OUTPUT_DIR}",
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
        "--save-point-scores",
        action="store_true",
        help="Save per-point points/mask/score arrays as npz under output-dir.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = _read_yaml(args.config)
    classes = tuple(args.classes) if args.classes is not None else tuple(cfg["dataset"]["cls_name"])
    if not classes:
        raise ValueError("At least one class is required")

    runtime = _load_pasdf_runtime(args.pasdf_root)
    records = export_pasdf_scores(
        runtime=runtime,
        cfg=cfg,
        classes=classes,
        output_dir=args.output_dir,
        save_point_scores=args.save_point_scores,
    )

    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    write_sample_scores_csv(records, args.summary_csv)
    args.summary_md.write_text(render_score_export_markdown(records), encoding="utf-8")
    print(f"Wrote PASDF score markdown to {args.summary_md}")
    print(f"Wrote PASDF score CSV to {args.summary_csv}")
    print(f"Exported PASDF sample scores: classes={len(classes)} samples={len(records)}")


def export_pasdf_scores(
    *,
    runtime: ModuleType | type,
    cfg: dict[str, Any],
    classes: Sequence[str],
    output_dir: Path,
    save_point_scores: bool,
) -> tuple[PasdfSampleScore, ...]:
    """Run PASDF scoring for selected classes and return sample-level records."""

    records: list[PasdfSampleScore] = []
    top_k = int(cfg["infer"]["top_k"])
    for cls_name in classes:
        class_records: list[PasdfSampleScore] = []
        scorer = _build_scorer(runtime, cfg, cls_name)
        for batch in _iter_pasdf_batches(runtime, cfg, cls_name):
            sample_path = _batch_sample_path(batch)
            sample_id = Path(sample_path).stem
            points = np.asarray(_first_batch_item(batch["points"]), dtype=np.float32)
            mask = _to_numpy_1d(batch["mask"])
            label = int(_to_scalar(batch["label"]))
            template_points = np.asarray(
                _first_batch_item(batch["template_points"]),
                dtype=np.float32,
            )

            registered_points = _register_points(runtime, cfg, points, template_points)
            point_scores, object_score = _score_registered_points(
                runtime,
                scorer,
                registered_points,
            )
            score_array = np.asarray(point_scores, dtype=np.float64).reshape(-1)
            point_score_path = None
            if save_point_scores:
                point_score_path = _save_point_score_npz(
                    output_dir=output_dir,
                    class_name=cls_name,
                    sample_id=sample_id,
                    points=np.asarray(registered_points, dtype=np.float32),
                    mask=mask,
                    point_scores=score_array,
                    label=label,
                    object_score=float(_object_score_scalar(object_score)),
                    sample_path=sample_path,
                )

            record = summarize_point_scores(
                class_name=cls_name,
                sample_id=sample_id,
                sample_path=sample_path,
                point_scores=score_array,
                mask=mask,
                label=label,
                top_k=top_k,
                point_score_path=point_score_path,
            )
            records.append(record)
            class_records.append(record)
        write_sample_scores_csv(class_records, output_dir / cls_name / "sample_scores.csv")
    return tuple(records)


def _load_pasdf_runtime(pasdf_root: str | Path) -> ModuleType:
    root = Path(pasdf_root).resolve()
    test_dir = root / "Test"
    for path in (str(root), str(test_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)

    runtime = ModuleType("pasdf_runtime")
    try:
        import torch  # type: ignore[import-not-found]
        from dataset import Dataset_ShapeNetAD_test  # type: ignore[import-not-found]
        from infer import SDFScorer  # type: ignore[import-not-found]
        from utils import register_point_clouds  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PASDF runtime imports failed. Run this script inside the Docker/conda pasdf "
            "environment with torch/open3d/PASDF dependencies available."
        ) from exc

    runtime.Dataset_ShapeNetAD_test = Dataset_ShapeNetAD_test
    runtime.SDFScorer = SDFScorer
    runtime.register_point_clouds = register_point_clouds
    runtime.torch = torch
    runtime.pasdf_root = root
    return runtime


def _iter_pasdf_batches(
    runtime: ModuleType | type,
    cfg: dict[str, Any],
    cls_name: str,
) -> Iterator[dict[str, Any]]:
    dataset_cfg = cfg["dataset"]
    if dataset_cfg["name"] != "ShapeNetAD":
        raise ValueError("P5 PASDF score export currently supports ShapeNetAD only")

    dataset = runtime.Dataset_ShapeNetAD_test(
        dataset_dir=dataset_cfg["dataset_dir"],
        cls_name=cls_name,
        num_points=dataset_cfg.get("num_points", 0),
        normalize=dataset_cfg.get("normalize", False),
        scale_factor=dataset_cfg.get("scale_factor", 1.0),
        template_path=dataset_cfg.get("template_path", None),
    )
    sample_list = tuple(getattr(dataset, "test_sample_list", ()))
    for index in range(len(dataset)):
        batch = dataset[index]
        if "sample_path" not in batch and index < len(sample_list):
            batch = dict(batch)
            batch["sample_path"] = sample_list[index]
        yield batch


def _register_points(
    runtime: ModuleType | type,
    cfg: dict[str, Any],
    points: np.ndarray,
    template_points: np.ndarray,
) -> np.ndarray:
    registered, _, _ = runtime.register_point_clouds(
        points,
        template_points,
        voxel_size=cfg["infer"].get("voxel_size", 0.03),
        cd_threshold=cfg["infer"].get("cd_threshold", 1.6),
    )
    if hasattr(registered, "points"):
        return np.asarray(registered.points, dtype=np.float32)
    return np.asarray(registered, dtype=np.float32)


def _score_registered_points(
    runtime: ModuleType | type,
    scorer: Any,
    points: np.ndarray,
) -> tuple[Sequence[float], Sequence[float]]:
    point_tensor = runtime.torch.from_numpy(np.asarray(points, dtype=np.float32))
    point_tensor = point_tensor.unsqueeze(0)
    return scorer.infer(point_tensor)


def _build_scorer(runtime: ModuleType | type, cfg: dict[str, Any], cls_name: str) -> Any:
    cwd = Path.cwd()
    pasdf_root = Path(getattr(runtime, "pasdf_root", cwd))
    try:
        os.chdir(pasdf_root)
        return runtime.SDFScorer(cfg, cls_name, device=cfg.get("device", "cuda"))
    finally:
        os.chdir(cwd)


def _save_point_score_npz(
    *,
    output_dir: Path,
    class_name: str,
    sample_id: str,
    points: np.ndarray,
    mask: np.ndarray,
    point_scores: np.ndarray,
    label: int,
    object_score: float,
    sample_path: str,
) -> str:
    point_dir = output_dir / class_name / "points"
    point_dir.mkdir(parents=True, exist_ok=True)
    output = point_dir / f"{sample_id}.npz"
    np.savez_compressed(
        output,
        points=points,
        mask=mask,
        point_scores=point_scores,
        label=np.array(label, dtype=np.int64),
        object_score=np.array(object_score, dtype=np.float64),
        sample_path=np.array(sample_path),
    )
    return str(output)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"YAML config must be a mapping: {path}")
    return payload


def _batch_sample_path(batch: dict[str, Any]) -> str:
    sample_path = batch.get("sample_path")
    if sample_path is None:
        raise ValueError("PASDF batch does not include sample_path and dataset has no sample list")
    if isinstance(sample_path, list | tuple):
        return str(sample_path[0])
    return str(sample_path)


def _first_batch_item(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        if value.ndim >= 3 and value.shape[0] == 1:
            return value[0]
        return value
    if isinstance(value, list | tuple):
        return value[0]
    if hasattr(value, "detach"):
        array = value.detach().cpu().numpy()
        if array.ndim >= 3 and array.shape[0] == 1:
            return array[0]
        return array
    return value


def _to_numpy_1d(value: Any) -> np.ndarray:
    item = _first_batch_item(value)
    if hasattr(item, "detach"):
        item = item.detach().cpu().numpy()
    elif hasattr(item, "numpy"):
        item = item.numpy()
    return np.asarray(item).reshape(-1)


def _to_scalar(value: Any) -> int | float:
    item = _first_batch_item(value)
    if hasattr(item, "item"):
        return item.item()
    return np.asarray(item).reshape(-1)[0].item()


def _object_score_scalar(value: Sequence[float] | float) -> float:
    if isinstance(value, list | tuple):
        return float(value[0])
    return float(value)


if __name__ == "__main__":
    main()
