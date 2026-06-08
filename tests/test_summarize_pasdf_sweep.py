from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "summarize_pasdf_sweep.py"
    spec = importlib.util.spec_from_file_location("summarize_pasdf_sweep_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_run(run_dir: Path, class_name: str, pixel_auc: float, object_auc: float) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "evaluation_results.csv").write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                f"{class_name},{pixel_auc},{object_auc}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (run_dir / "run.log").write_text(
        "\n".join(
            [
                f"Evaluating [{class_name}]: 100%|done",
                f"/workspace/data/{class_name}/test/{class_name}_positive0.pcd",
                "[Open3D WARNING] Too few correspondences (96) after mutual filter",
                f"---{class_name}-- AUROC Pixel: {pixel_auc}, AUROC Object: {object_auc}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_summarize_pasdf_sweep_cli_writes_markdown_and_csv(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "sweep"
    _write_run(root / "cap3" / "vs_0p020", "cap3", 0.84, 0.61)
    _write_run(root / "cap3" / "vs_0p030", "cap3", 0.85, 0.55)
    output = tmp_path / "summary.md"
    csv_path = tmp_path / "summary.csv"

    monkeypatch.setattr(
        "sys.argv",
        [
            "summarize_pasdf_sweep.py",
            "--root",
            str(root),
            "--classes",
            "cap3",
            "--output",
            str(output),
            "--csv",
            str(csv_path),
        ],
    )

    _load_script_module().main()

    assert output.read_text(encoding="utf-8").startswith("# P4 PASDF Voxel Sweep 结果摘要")
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "class,voxel_size,pixel_auc,object_auc,warning_count,warning_sample_count" in csv_text
    assert "cap3,0.02,0.84,0.61,1,1" in csv_text
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF sweep summary to {output}" in stdout
    assert f"Wrote PASDF sweep CSV to {csv_path}" in stdout
    assert "best_voxels=cap3:0.020" in stdout
