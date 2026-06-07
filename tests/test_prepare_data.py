from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_prepare_data_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "prepare_data.py"
    spec = importlib.util.spec_from_file_location("prepare_data_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_ascii_pcd(path: Path, point_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"{idx}.0 {idx + 1}.0 {idx + 2}.0" for idx in range(point_count))
    path.write_text(
        "\n".join(
            [
                "VERSION 0.7",
                "FIELDS x y z",
                "SIZE 4 4 4",
                "TYPE F F F",
                "COUNT 1 1 1",
                f"WIDTH {point_count}",
                "HEIGHT 1",
                f"POINTS {point_count}",
                "DATA ascii",
                rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_prepare_data_stat_writes_markdown_report(tmp_path: Path, monkeypatch) -> None:
    dataset_root = tmp_path / "Anomaly-ShapeNet-v2"
    class_root = dataset_root / "dataset" / "pcd" / "widget0"
    _write_ascii_pcd(class_root / "train" / "widget0_template0.pcd", 3)
    _write_ascii_pcd(class_root / "test" / "widget0_positive0.pcd", 2)

    config = tmp_path / "data.yaml"
    config.write_text(
        "\n".join(
            [
                "dataset:",
                f"  root: {dataset_root}",
                "  collections: [pcd]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "stats.md"

    monkeypatch.setattr(
        "sys.argv",
        ["prepare_data.py", "--stat", "--config", str(config), "--output", str(output)],
    )

    _load_prepare_data_module().main()

    report = output.read_text(encoding="utf-8")
    assert "# Anomaly-ShapeNet Data Statistics" in report
    assert f"- Root: `{dataset_root}`" in report
    assert "- Samples: 2" in report
    assert "- Min points: 2" in report
    assert "- Max points: 3" in report
