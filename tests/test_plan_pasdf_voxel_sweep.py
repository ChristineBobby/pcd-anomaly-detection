from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "plan_pasdf_voxel_sweep.py"
    spec = importlib.util.spec_from_file_location("plan_pasdf_voxel_sweep_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_pasdf_voxel_sweep_cli_writes_markdown_and_csv(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    results = tmp_path / "evaluation_results.csv"
    results.write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                "cap3,0.846928,0.550877",
                "cap4,0.863803,0.628070",
                "",
            ]
        ),
        encoding="utf-8",
    )
    log = tmp_path / "run.log"
    log.write_text(
        "\n".join(
            [
                "Evaluating [cap3]: 100%|done",
                "/workspace/data/16384/cap3/test/cap3_concavity2.pcd",
                "[Open3D WARNING] Too few correspondences (96) after mutual filter",
                "---cap3-- AUROC Pixel: 0.846928, AUROC Object: 0.550877",
                "",
            ]
        ),
        encoding="utf-8",
    )
    voxel = tmp_path / "voxel_sizes.yaml"
    voxel.write_text("ShapeNetAD:\n  cap3: 0.03\n  cap4: 0.02\n", encoding="utf-8")
    markdown = tmp_path / "registration.md"
    csv_path = tmp_path / "registration.csv"

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_pasdf_voxel_sweep.py",
            "--results",
            str(results),
            "--log",
            str(log),
            "--voxel-sizes",
            str(voxel),
            "--output",
            str(markdown),
            "--priority-csv",
            str(csv_path),
            "--max-classes",
            "1",
        ],
    )

    _load_script_module().main()

    report = markdown.read_text(encoding="utf-8")
    priority_csv = csv_path.read_text(encoding="utf-8")
    assert report.startswith("# P4 PASDF Registration Diagnostics")
    assert "| cap3 | 0.846928 | 0.550877 | 1 | 1 | 0.030 |" in report
    assert "class,pixel_auc,object_auc,warning_count,warning_sample_count" in priority_csv
    assert "cap3,0.846928,0.550877,1,1,0.03" in priority_csv
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF registration diagnostics to {markdown}" in stdout
    assert f"Wrote PASDF registration priority CSV to {csv_path}" in stdout
    assert "priority_classes=cap3" in stdout
