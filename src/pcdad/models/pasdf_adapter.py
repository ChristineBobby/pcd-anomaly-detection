"""Adapter utilities for running official PASDF ShapeNetAD evaluation."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

SHAPENETAD_CLASSES: tuple[str, ...] = (
    "ashtray0",
    "bag0",
    "bottle0",
    "bottle1",
    "bottle3",
    "bowl0",
    "bowl1",
    "bowl2",
    "bowl3",
    "bowl4",
    "bowl5",
    "bucket0",
    "bucket1",
    "cap0",
    "cap3",
    "cap4",
    "cap5",
    "cup0",
    "cup1",
    "eraser0",
    "headset0",
    "headset1",
    "helmet0",
    "helmet1",
    "helmet2",
    "helmet3",
    "jar0",
    "microphone0",
    "shelf0",
    "tap0",
    "tap1",
    "vase0",
    "vase1",
    "vase2",
    "vase3",
    "vase4",
    "vase5",
    "vase7",
    "vase8",
    "vase9",
)


@dataclass(frozen=True)
class PasdfPaths:
    """Filesystem paths used to generate a PASDF evaluation config."""

    pasdf_root: Path
    dataset_dir: Path
    output_dir: Path
    template_path: str = "data/ShapeNetAD"
    checkpoint_path: str = "results/ShapeNetAD/runs_sdf/"
    settings_path: str = "results/ShapeNetAD/runs_sdf/settings.yaml"


@dataclass(frozen=True)
class PasdfEvalOptions:
    """Evaluation options mirrored from PASDF's official ShapeNetAD YAML."""

    classes: tuple[str, ...]
    seed: int = 42
    device: str = "cuda"
    batch_size: int = 1
    num_workers: int = 0
    voxel_size: float = 0.03
    top_k: int = 1
    shuffle: bool = False
    cd_threshold: float = 1.6
    normalize: bool = False
    scale_factor: float = 1.0


@dataclass(frozen=True)
class PasdfEvaluationResult:
    """One row from PASDF's official evaluation_results.csv."""

    class_name: str
    pixel_auc: float
    object_auc: float


def normalize_shapenetad_classes(classes: Iterable[str] | None) -> tuple[str, ...]:
    """Return validated ShapeNetAD class names in the requested order."""

    if classes is None:
        return SHAPENETAD_CLASSES
    normalized = tuple(classes)
    if not normalized:
        raise ValueError("At least one ShapeNetAD class is required")

    known = set(SHAPENETAD_CLASSES)
    unknown = tuple(class_name for class_name in normalized if class_name not in known)
    if unknown:
        raise ValueError(f"Unknown ShapeNetAD classes: {', '.join(unknown)}")
    return normalized


def build_shapenetad_eval_config(paths: PasdfPaths, options: PasdfEvalOptions) -> dict[str, Any]:
    """Build a PASDF-compatible ShapeNetAD evaluation YAML payload."""

    classes = normalize_shapenetad_classes(options.classes)
    return {
        "seed": options.seed,
        "device": options.device,
        "dataset": {
            "name": "ShapeNetAD",
            "dataset_dir": str(paths.dataset_dir.resolve()),
            "cls_name": list(classes),
            "normalize": options.normalize,
            "scale_factor": options.scale_factor,
            "template_path": paths.template_path,
        },
        "infer": {
            "batch_size": options.batch_size,
            "num_workers": options.num_workers,
            "voxel_size": options.voxel_size,
            "top_k": options.top_k,
            "shuffle": options.shuffle,
            "cd_threshold": options.cd_threshold,
            "checkpoint_path": paths.checkpoint_path,
            "output_dir": str(paths.output_dir.resolve()),
            "settings_path": paths.settings_path,
        },
    }


def write_eval_config(config: Mapping[str, Any], path: str | Path) -> Path:
    """Write an evaluation YAML config and return its path."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(dict(config), sort_keys=False), encoding="utf-8")
    return output


def build_pasdf_command(
    pasdf_root: str | Path,
    config_path: str | Path,
    *,
    python: str = "python",
) -> list[str]:
    """Return the command that runs PASDF's official evaluation entrypoint."""

    _ = Path(pasdf_root)
    return [python, "Test/AD_test.py", "--config", str(Path(config_path).resolve())]


def parse_evaluation_results(path: str | Path) -> tuple[PasdfEvaluationResult, ...]:
    """Read PASDF evaluation_results.csv and validate required columns."""

    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"class", "pixel_auc", "object_auc"}
        fieldnames = set(reader.fieldnames or ())
        missing = required - fieldnames
        if missing:
            raise ValueError(
                "PASDF evaluation results missing required columns: "
                f"{', '.join(sorted(missing))}"
            )
        return tuple(
            PasdfEvaluationResult(
                class_name=row["class"],
                pixel_auc=float(row["pixel_auc"]),
                object_auc=float(row["object_auc"]),
            )
            for row in reader
        )


def summarize_results(results: Iterable[PasdfEvaluationResult]) -> dict[str, float]:
    """Return class count and mean AUROC values."""

    result_tuple = tuple(results)
    if not result_tuple:
        raise ValueError("At least one PASDF evaluation result is required")
    count = float(len(result_tuple))
    return {
        "class_count": count,
        "mean_pixel_auc": round(
            math.fsum(result.pixel_auc for result in result_tuple) / count,
            12,
        ),
        "mean_object_auc": round(
            math.fsum(result.object_auc for result in result_tuple) / count,
            12,
        ),
    }
