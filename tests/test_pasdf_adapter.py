from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pcdad.models.pasdf_adapter import (
    SHAPENETAD_CLASSES,
    PasdfEvalOptions,
    PasdfEvaluationResult,
    PasdfPaths,
    build_pasdf_command,
    build_shapenetad_eval_config,
    normalize_shapenetad_classes,
    parse_evaluation_results,
    summarize_results,
    write_eval_config,
)


def test_normalize_shapenetad_classes_defaults_to_official_40_class_order() -> None:
    classes = normalize_shapenetad_classes(None)

    assert classes == SHAPENETAD_CLASSES
    assert len(classes) == 40
    assert classes[:3] == ("ashtray0", "bag0", "bottle0")
    assert classes[-3:] == ("vase7", "vase8", "vase9")


def test_normalize_shapenetad_classes_rejects_empty_and_unknown_values() -> None:
    with pytest.raises(ValueError, match="At least one ShapeNetAD class is required"):
        normalize_shapenetad_classes([])

    with pytest.raises(ValueError, match="Unknown ShapeNetAD classes: missing0"):
        normalize_shapenetad_classes(["ashtray0", "missing0"])


def test_build_shapenetad_eval_config_matches_official_pasdf_schema(tmp_path: Path) -> None:
    paths = PasdfPaths(
        pasdf_root=tmp_path / "third_party" / "PASDF",
        dataset_dir=tmp_path / "data" / "Anomaly-ShapeNet-v2" / "dataset" / "16384",
        output_dir=tmp_path / "experiments" / "E1_pasdf_baseline" / "smoke_ashtray0",
    )
    options = PasdfEvalOptions(classes=("ashtray0",), voxel_size=0.025, cd_threshold=1.5)

    config = build_shapenetad_eval_config(paths, options)

    assert config["seed"] == 42
    assert config["device"] == "cuda"
    assert config["dataset"] == {
        "name": "ShapeNetAD",
        "dataset_dir": str(paths.dataset_dir.resolve()),
        "cls_name": ["ashtray0"],
        "normalize": False,
        "scale_factor": 1.0,
        "template_path": "data/ShapeNetAD",
    }
    assert config["infer"] == {
        "batch_size": 1,
        "num_workers": 0,
        "voxel_size": 0.025,
        "top_k": 1,
        "shuffle": False,
        "cd_threshold": 1.5,
        "checkpoint_path": "results/ShapeNetAD/runs_sdf/",
        "output_dir": str(paths.output_dir.resolve()),
        "settings_path": "results/ShapeNetAD/runs_sdf/settings.yaml",
    }


def test_write_eval_config_creates_stable_yaml(tmp_path: Path) -> None:
    output = tmp_path / "runs" / "pasdf_test_ShapeNetAD.yaml"
    config = {
        "seed": 42,
        "device": "cuda",
        "dataset": {"name": "ShapeNetAD", "cls_name": ["ashtray0"]},
        "infer": {"batch_size": 1},
    }

    written = write_eval_config(config, output)

    assert written == output
    assert yaml.safe_load(output.read_text(encoding="utf-8")) == config
    assert output.read_text(encoding="utf-8").splitlines()[0] == "seed: 42"


def test_build_pasdf_command_runs_official_entrypoint_from_pasdf_root(tmp_path: Path) -> None:
    pasdf_root = tmp_path / "third_party" / "PASDF"
    config_path = tmp_path / "experiments" / "run" / "pasdf_test_ShapeNetAD.yaml"

    command = build_pasdf_command(pasdf_root, config_path, python="python3")

    assert command == [
        "python3",
        "Test/AD_test.py",
        "--config",
        str(config_path.resolve()),
    ]


def test_parse_evaluation_results_reads_official_csv_and_summarizes(tmp_path: Path) -> None:
    csv_path = tmp_path / "evaluation_results.csv"
    csv_path.write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                "ashtray0,0.8125,0.9",
                "bag0,0.75,0.8",
                "",
            ]
        ),
        encoding="utf-8",
    )

    results = parse_evaluation_results(csv_path)

    assert results == (
        PasdfEvaluationResult(class_name="ashtray0", pixel_auc=0.8125, object_auc=0.9),
        PasdfEvaluationResult(class_name="bag0", pixel_auc=0.75, object_auc=0.8),
    )
    assert summarize_results(results) == {
        "class_count": 2.0,
        "mean_pixel_auc": 0.78125,
        "mean_object_auc": 0.85,
    }


def test_parse_evaluation_results_rejects_missing_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("class,pixel_auc\nashtray0,0.8\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        parse_evaluation_results(csv_path)
