from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import yaml


def _load_evaluate_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "evaluate.py"
    spec = importlib.util.spec_from_file_location("evaluate_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evaluate_dry_run_writes_pasdf_config_and_prints_command(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    config = tmp_path / "E1_pasdf_baseline.yaml"
    dataset_dir = tmp_path / "data" / "Anomaly-ShapeNet-v2" / "dataset" / "16384"
    pasdf_root = tmp_path / "third_party" / "PASDF"
    output_dir = tmp_path / "experiments" / "E1_pasdf_baseline" / "smoke_ashtray0"
    config.write_text(
        "\n".join(
            [
                "dataset:",
                f"  pasdf_dir: {dataset_dir}",
                "model:",
                "  repo_path: third_party/PASDF",
                "experiment:",
                "  id: E1",
                "  name: pasdf_baseline",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate.py",
            "--config",
            str(config),
            "--pasdf-root",
            str(pasdf_root),
            "--classes",
            "ashtray0",
            "--output-dir",
            str(output_dir),
            "--dry-run",
        ],
    )

    _load_evaluate_module().main()

    generated = output_dir / "pasdf_test_ShapeNetAD.yaml"
    assert generated.is_file()
    payload = yaml.safe_load(generated.read_text(encoding="utf-8"))
    assert payload["dataset"]["dataset_dir"] == str(dataset_dir.resolve())
    assert payload["dataset"]["cls_name"] == ["ashtray0"]
    assert payload["infer"]["output_dir"] == str(output_dir.resolve())
    stdout = capsys.readouterr().out
    assert "Dry run: PASDF config written to" in stdout
    assert "python Test/AD_test.py --config" in stdout


def test_evaluate_config_can_supply_default_classes_and_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = tmp_path / "experiment.yaml"
    dataset_dir = tmp_path / "dataset" / "16384"
    output_dir = tmp_path / "runs" / "full_40cls"
    config.write_text(
        "\n".join(
            [
                "dataset:",
                f"  pasdf_dir: {dataset_dir}",
                "model:",
                f"  repo_path: {tmp_path / 'third_party' / 'PASDF'}",
                "experiment:",
                "  pasdf:",
                "    classes: [ashtray0, bag0]",
                "    voxel_size: 0.025",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate.py",
            "--config",
            str(config),
            "--output-dir",
            str(output_dir),
            "--dry-run",
        ],
    )

    _load_evaluate_module().main()

    payload = yaml.safe_load(
        (output_dir / "pasdf_test_ShapeNetAD.yaml").read_text(encoding="utf-8")
    )
    assert payload["dataset"]["cls_name"] == ["ashtray0", "bag0"]
    assert payload["infer"]["voxel_size"] == 0.025
