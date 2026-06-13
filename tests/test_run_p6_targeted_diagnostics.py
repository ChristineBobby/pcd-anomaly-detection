from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_p6_targeted_diagnostics.py"
    spec = importlib.util.spec_from_file_location("run_p6_targeted_diagnostics_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_score_npz(root: Path, class_name: str, sample_id: str, *, label: int) -> None:
    path = root / class_name / "points" / f"{sample_id}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        points=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.float32,
        ),
        point_scores=np.array([0.1, 0.3, 0.8], dtype=np.float64),
        mask=np.array([0, 1, 1], dtype=np.int64) if label == 1 else np.zeros(3),
        label=np.array(label, dtype=np.int64),
        object_score=np.array(0.8, dtype=np.float64),
    )


def _write_template_obj(root: Path, class_name: str) -> None:
    path = root / class_name / f"{class_name}_template0.obj"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(["v 0.0 0.0 0.0", "v 1.0 0.0 0.0", "v 0.0 1.0 0.0"]) + "\n",
        encoding="utf-8",
    )


def test_run_p6_targeted_diagnostics_cli_writes_summary_tables_and_svgs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    score_root = tmp_path / "scores"
    template_root = tmp_path / "templates"
    _write_score_npz(score_root, "cap3", "cap3_positive9", label=0)
    _write_score_npz(score_root, "tap1", "tap1_broken2", label=1)
    _write_score_npz(score_root, "tap1", "tap1_positive0", label=0)
    _write_template_obj(template_root, "cap3")
    _write_template_obj(template_root, "tap1")
    output_dir = tmp_path / "p6"
    summary_md = tmp_path / "summary.md"
    summary_csv = tmp_path / "summary.csv"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_p6_targeted_diagnostics.py",
            "--score-root",
            str(score_root),
            "--template-root",
            str(template_root),
            "--cap3-samples",
            "cap3_positive9",
            "--tap1-samples",
            "tap1_broken2",
            "--tap1-positive-samples",
            "tap1_positive0",
            "--output-dir",
            str(output_dir),
            "--summary-md",
            str(summary_md),
            "--summary-csv",
            str(summary_csv),
            "--max-points",
            "3",
        ],
    )

    module.main()

    assert summary_md.exists()
    assert summary_csv.exists()
    assert "P6 Targeted Diagnostics" in summary_md.read_text(encoding="utf-8")
    assert "tap1_broken2" in summary_csv.read_text(encoding="utf-8")
    assert (output_dir / "tap1_hybrid_scores" / "tap1" / "tap1_broken2_hybrid.svg").exists()
    assert (output_dir / "tap1_hybrid_scores" / "tap1" / "tap1_positive0_hybrid.svg").exists()
    stdout = capsys.readouterr().out
    assert f"Wrote P6 targeted markdown to {summary_md}" in stdout
