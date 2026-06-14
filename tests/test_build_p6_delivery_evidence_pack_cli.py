from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_p6_delivery_evidence_pack.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_p6_delivery_evidence_pack_script", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_p6_delivery_evidence_pack_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_csv = tmp_path / "delivery.csv"
    output_md = tmp_path / "delivery.md"
    report_draft = tmp_path / "report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_p6_delivery_evidence_pack.py",
            "--repo-root",
            str(repo_root),
            "--commit-hash",
            "abc1234",
            "--output-csv",
            str(output_csv),
            "--output-md",
            str(output_md),
            "--report-draft",
            str(report_draft),
        ],
    )

    module.main()

    assert output_csv.exists()
    assert output_md.exists()
    assert report_draft.exists()
    assert "p3_pasdf_baseline_40cls" in output_csv.read_text(encoding="utf-8")
    assert "P6 交付证据包" in output_md.read_text(encoding="utf-8")
    assert "最终报告草稿" in report_draft.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert f"Wrote delivery evidence CSV to {output_csv}" in stdout
    assert "Processed 9 evidence records" in stdout
