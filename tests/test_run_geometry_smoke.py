from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np

from pcdad.data.preprocess import write_ascii_xyz_pcd, write_pasdf_gt_txt


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_geometry_smoke.py"
    spec = importlib.util.spec_from_file_location("run_geometry_smoke_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_dataset(root: Path) -> Path:
    dataset_root = root / "Anomaly-ShapeNet-v2" / "dataset" / "16384"
    class_root = dataset_root / "widget0"
    points = np.array(
        [
            [-1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
        ],
        dtype=np.float32,
    )
    write_ascii_xyz_pcd(class_root / "train" / "widget0_template0.pcd", points)
    sample = points.copy()
    sample[1] = np.array([0.0, 0.0, 0.5], dtype=np.float32)
    labels = np.zeros((points.shape[0],), dtype=np.int64)
    labels[1] = 1
    write_ascii_xyz_pcd(class_root / "test" / "widget0_bulge0.pcd", sample)
    write_pasdf_gt_txt(class_root / "GT" / "widget0_bulge0.txt", sample, labels)
    return dataset_root


def test_run_geometry_smoke_cli_uses_default_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    dataset_root = _make_dataset(tmp_path)
    output_root = tmp_path / "stage"

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_geometry_smoke.py",
            "--dataset-root",
            str(dataset_root),
            "--classes",
            "widget0",
            "--max-samples",
            "1",
            "--k-normal",
            "2",
            "--k-curvature",
            "2",
            "--distance-only",
            "--stage-record-dir",
            str(output_root),
        ],
    )

    _load_script_module().main()

    assert (output_root / "2026-06-08_p4_geometry_smoke_summary.md").is_file()
    assert (output_root / "2026-06-08_p4_geometry_smoke_summary.csv").is_file()
    stdout = capsys.readouterr().out
    assert "Geometry smoke summary: experiment=P4_geometry_smoke classes=1 samples=1" in stdout


def test_run_geometry_smoke_cli_can_read_experiment_config(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    dataset_root = _make_dataset(tmp_path)
    output_root = tmp_path / "stage"
    config = tmp_path / "A2_widget.yaml"
    config.write_text(
        "\n".join(
            [
                "experiment:",
                "  id: A2",
                "  name: widget_normal",
                "  geometry_smoke:",
                "    classes: [widget0]",
                "    max_samples: 1",
                "    k_normal: 2",
                "    k_curvature: [2]",
                "    topk_ratio: 0.25",
                "    components:",
                "      distance: true",
                "      normal: false",
                "      curvature: false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_geometry_smoke.py",
            "--config",
            str(config),
            "--dataset-root",
            str(dataset_root),
            "--stage-record-dir",
            str(output_root),
        ],
    )

    _load_script_module().main()

    assert (output_root / "2026-06-09_a2_widget_normal_geometry_smoke_summary.md").is_file()
    assert (output_root / "2026-06-09_a2_widget_normal_geometry_smoke_summary.csv").is_file()
    stdout = capsys.readouterr().out
    assert "experiment=A2_widget_normal" in stdout
