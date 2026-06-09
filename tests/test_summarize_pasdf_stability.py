from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "summarize_pasdf_stability.py"
    spec = importlib.util.spec_from_file_location("summarize_pasdf_stability_script", script_path)
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
                f"---{class_name}-- AUROC Pixel: {pixel_auc}, AUROC Object: {object_auc}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_summarize_pasdf_stability_cli_writes_markdown_and_csv(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "stability"
    _write_run(root / "helmet2" / "run_001", "helmet2", 0.80, 0.64)
    _write_run(root / "helmet2" / "run_002", "helmet2", 0.82, 0.70)
    output = tmp_path / "stability.md"
    csv_path = tmp_path / "stability.csv"

    monkeypatch.setattr(
        "sys.argv",
        [
            "summarize_pasdf_stability.py",
            "--root",
            str(root),
            "--classes",
            "helmet2",
            "--output",
            str(output),
            "--csv",
            str(csv_path),
        ],
    )

    _load_script_module().main()

    assert output.read_text(encoding="utf-8").startswith("# P4 PASDF 稳定性复核摘要")
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "class,run_id,pixel_auc,object_auc,warning_count" in csv_text
    assert "helmet2,run_001,0.8,0.64,0" in csv_text
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF stability summary to {output}" in stdout
    assert "classes=1 runs=2" in stdout
