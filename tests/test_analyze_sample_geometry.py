from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np

from pcdad.data.preprocess import write_ascii_xyz_pcd, write_pasdf_gt_txt


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "analyze_sample_geometry.py"
    spec = importlib.util.spec_from_file_location("analyze_sample_geometry_script", script_path)
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


def test_analyze_sample_geometry_cli_writes_markdown_and_csv(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    dataset_root = _make_dataset(tmp_path)
    output = tmp_path / "geometry.md"
    csv_path = tmp_path / "geometry.csv"
    svg_dir = tmp_path / "svg"

    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze_sample_geometry.py",
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
            "--output",
            str(output),
            "--csv",
            str(csv_path),
            "--svg-dir",
            str(svg_dir),
            "--svg-max-points",
            "5",
        ],
    )

    _load_script_module().main()

    assert output.read_text(encoding="utf-8").startswith("# P4 几何 Smoke 摘要")
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "class,template_sample_id,sample_id,anomaly_type" in csv_text
    assert "widget0,widget0_template0,widget0_bulge0,bulge" in csv_text
    assert (svg_dir / "widget0_widget0_bulge0.svg").is_file()
    stdout = capsys.readouterr().out
    assert f"Wrote geometry smoke summary to {output}" in stdout
    assert "classes=1 samples=1" in stdout
