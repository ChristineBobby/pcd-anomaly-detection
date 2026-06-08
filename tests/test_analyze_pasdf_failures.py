from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "analyze_pasdf_failures.py"
    spec = importlib.util.spec_from_file_location("analyze_pasdf_failures_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_pasdf_failures_cli_writes_markdown_report(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    results = tmp_path / "evaluation_results.csv"
    results.write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                "ashtray0,0.92,1.0",
                "cap3,0.846,0.551",
                "helmet1,0.623,0.957",
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
                "[Open3D WARNING] Too few correspondences (85) after mutual filter",
                "---cap3-- AUROC Pixel: 0.846, AUROC Object: 0.551",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "summary.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze_pasdf_failures.py",
            "--results",
            str(results),
            "--log",
            str(log),
            "--output",
            str(output),
            "--title",
            "P4 Test Summary",
        ],
    )

    _load_script_module().main()

    report = output.read_text(encoding="utf-8")
    assert report.startswith("# P4 Test Summary")
    assert "| cap3 | 0.846000 | 0.551000 | 1 |" in report
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF failure summary to {output}" in stdout
    assert "priority_classes=cap3,helmet1" in stdout
