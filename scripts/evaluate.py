"""Evaluate an experiment config."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path
from typing import Any

import yaml

from pcdad.models.pasdf_adapter import (
    PasdfEvalOptions,
    PasdfPaths,
    build_pasdf_command,
    build_shapenetad_eval_config,
    normalize_shapenetad_classes,
    parse_evaluation_results,
    summarize_results,
    write_eval_config,
)

DEFAULT_DATASET_DIR = Path("data/Anomaly-ShapeNet-v2/dataset/16384")
DEFAULT_PASDF_ROOT = Path("third_party/PASDF")
DEFAULT_OUTPUT_DIR = Path("experiments/E1_pasdf_baseline")
DEFAULT_GENERATED_CONFIG = "pasdf_test_ShapeNetAD.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to an experiment YAML config.")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=None,
        help=f"PASDF fixed-size ShapeNetAD dataset. Default: {DEFAULT_DATASET_DIR}",
    )
    parser.add_argument(
        "--pasdf-root",
        type=Path,
        default=None,
        help=f"PASDF repository root. Default: {DEFAULT_PASDF_ROOT}",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=None,
        help="Optional ShapeNetAD class filter. Default: config value or official 40 classes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Experiment output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--generated-config-name",
        default=DEFAULT_GENERATED_CONFIG,
        help=f"Generated PASDF YAML filename. Default: {DEFAULT_GENERATED_CONFIG}",
    )
    parser.add_argument("--seed", type=int, default=None, help="Override PASDF seed.")
    parser.add_argument("--device", default=None, help="Override PASDF device field.")
    parser.add_argument("--batch-size", type=int, default=None, help="Override PASDF batch size.")
    parser.add_argument("--num-workers", type=int, default=None, help="Override PASDF num_workers.")
    parser.add_argument("--voxel-size", type=float, default=None, help="Override PASDF voxel size.")
    parser.add_argument("--top-k", type=int, default=None, help="Override PASDF top_k.")
    parser.add_argument(
        "--cd-threshold", type=float, default=None, help="Override PASDF CD threshold."
    )
    parser.add_argument(
        "--python",
        default="python",
        help="Python executable used to run PASDF official evaluation.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate config and print command only."
    )
    return parser.parse_args()


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


def _pasdf_section(config: dict[str, Any]) -> dict[str, Any]:
    experiment = _section(config, "experiment")
    value = experiment.get("pasdf", {})
    return value if isinstance(value, dict) else {}


def _resolve_dataset_dir(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    if args.dataset_dir is not None:
        return args.dataset_dir
    dataset = _section(config, "dataset")
    pasdf_dir = dataset.get("pasdf_dir")
    if pasdf_dir is not None:
        return Path(str(pasdf_dir))
    root = dataset.get("root")
    target_num_points = dataset.get("target_num_points", 16384)
    if root is not None:
        return Path(str(root)) / "dataset" / str(target_num_points)
    return DEFAULT_DATASET_DIR


def _resolve_pasdf_root(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    if args.pasdf_root is not None:
        return args.pasdf_root
    model = _section(config, "model")
    repo_path = model.get("repo_path")
    return Path(str(repo_path)) if repo_path is not None else DEFAULT_PASDF_ROOT


def _resolve_output_dir(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    if args.output_dir is not None:
        return args.output_dir
    project = _section(config, "project")
    experiment = _section(config, "experiment")
    output_root = Path(str(project.get("output_root", "experiments")))
    exp_id = str(experiment.get("id", "E1"))
    exp_name = str(experiment.get("name", "pasdf_baseline"))
    return output_root / f"{exp_id}_{exp_name}"


def _resolve_classes(args: argparse.Namespace, config: dict[str, Any]) -> tuple[str, ...]:
    if args.classes is not None:
        return normalize_shapenetad_classes(args.classes)
    value = _pasdf_section(config).get("classes")
    if value is None:
        return normalize_shapenetad_classes(None)
    if isinstance(value, str):
        return normalize_shapenetad_classes([value])
    if isinstance(value, list):
        return normalize_shapenetad_classes(str(item) for item in value)
    raise SystemExit("experiment.pasdf.classes must be a string or list of strings")


def _option_value(
    args: argparse.Namespace,
    config: dict[str, Any],
    arg_name: str,
    config_name: str,
    default: Any,
) -> Any:
    cli_value = getattr(args, arg_name)
    if cli_value is not None:
        return cli_value
    return _pasdf_section(config).get(config_name, default)


def _build_options(args: argparse.Namespace, config: dict[str, Any]) -> PasdfEvalOptions:
    return PasdfEvalOptions(
        classes=_resolve_classes(args, config),
        seed=int(_option_value(args, config, "seed", "seed", 42)),
        device=str(_option_value(args, config, "device", "device", "cuda")),
        batch_size=int(_option_value(args, config, "batch_size", "batch_size", 1)),
        num_workers=int(_option_value(args, config, "num_workers", "num_workers", 0)),
        voxel_size=float(_option_value(args, config, "voxel_size", "voxel_size", 0.03)),
        top_k=int(_option_value(args, config, "top_k", "top_k", 1)),
        cd_threshold=float(_option_value(args, config, "cd_threshold", "cd_threshold", 1.6)),
    )


def main() -> None:
    args = parse_args()
    experiment_config = _load_config_with_defaults(Path(args.config))
    output_dir = _resolve_output_dir(args, experiment_config)
    paths = PasdfPaths(
        pasdf_root=_resolve_pasdf_root(args, experiment_config),
        dataset_dir=_resolve_dataset_dir(args, experiment_config),
        output_dir=output_dir,
    )
    options = _build_options(args, experiment_config)
    pasdf_config = build_shapenetad_eval_config(paths, options)
    generated_config = write_eval_config(pasdf_config, output_dir / args.generated_config_name)
    command = build_pasdf_command(paths.pasdf_root, generated_config, python=args.python)

    print(f"PASDF config written to {generated_config}")
    print(f"PASDF cwd: {paths.pasdf_root}")
    print(f"PASDF command: {shlex.join(command)}")
    if args.dry_run:
        print(f"Dry run: PASDF config written to {generated_config}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run.log"
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            command,
            cwd=paths.pasdf_root,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    results_path = output_dir / "evaluation_results.csv"
    results = parse_evaluation_results(results_path)
    summary = summarize_results(results)
    print(f"PASDF log written to {log_path}")
    print(f"PASDF results written to {results_path}")
    print(
        "PASDF summary: "
        f"classes={int(summary['class_count'])} "
        f"mean_pixel_auc={summary['mean_pixel_auc']:.6f} "
        f"mean_object_auc={summary['mean_object_auc']:.6f}"
    )


if __name__ == "__main__":
    main()
