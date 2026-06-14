from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_p6_failure_mode_closure.py"
    spec = importlib.util.spec_from_file_location("run_p6_failure_mode_closure_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_score_npz(
    root: Path,
    class_name: str,
    sample_id: str,
    *,
    label: int,
    scores: np.ndarray,
    mask: np.ndarray,
) -> None:
    path = root / class_name / "points" / f"{sample_id}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    points = np.column_stack(
        [
            np.arange(scores.shape[0], dtype=np.float32),
            np.zeros(scores.shape[0], dtype=np.float32),
            np.zeros(scores.shape[0], dtype=np.float32),
        ]
    )
    np.savez_compressed(
        path,
        points=points.astype(np.float32),
        point_scores=scores.astype(np.float64),
        mask=mask.astype(np.int64),
        label=np.array(label, dtype=np.int64),
        object_score=np.array(float(np.max(scores)), dtype=np.float64),
    )


def _write_template_obj(root: Path, class_name: str) -> None:
    path = root / class_name / f"{class_name}_template0.obj"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "v 0.0 0.0 0.0",
                "v -1.0 0.0 0.0",
                "v -2.0 0.0 0.0",
                "v -3.0 0.0 0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_run_p6_failure_mode_closure_cli_writes_summary(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    score_root = tmp_path / "scores"
    template_root = tmp_path / "templates"

    _write_score_npz(
        score_root,
        "cap3",
        "cap3_positive9",
        label=0,
        scores=np.array([0.1, 0.2, 0.9, 0.8], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
    )
    _write_score_npz(
        score_root,
        "cap3",
        "cap3_hole0",
        label=1,
        scores=np.array([0.2, 0.1, 0.05, 0.04], dtype=np.float64),
        mask=np.array([1, 0, 0, 0], dtype=np.int64),
    )
    _write_score_npz(
        score_root,
        "tap1",
        "tap1_broken2",
        label=1,
        scores=np.array([0.1, 0.9, 0.8, 0.2], dtype=np.float64),
        mask=np.array([0, 1, 0, 0], dtype=np.int64),
    )
    _write_score_npz(
        score_root,
        "tap1",
        "tap1_positive0",
        label=0,
        scores=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
    )
    _write_score_npz(
        score_root,
        "helmet1",
        "helmet1_concavity1",
        label=1,
        scores=np.array([0.1, 0.9, 0.8, 0.2], dtype=np.float64),
        mask=np.array([1, 0, 0, 0], dtype=np.int64),
    )
    _write_score_npz(
        score_root,
        "helmet1",
        "helmet1_positive0",
        label=0,
        scores=np.array([0.2, 0.3, 0.4, 0.5], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
    )
    _write_template_obj(template_root, "cap3")

    records_csv = tmp_path / "records.csv"
    summary_csv = tmp_path / "summary.csv"
    summary_md = tmp_path / "summary.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_p6_failure_mode_closure.py",
            "--score-root",
            str(score_root),
            "--template-root",
            str(template_root),
            "--classes",
            "cap3",
            "tap1",
            "helmet1",
            "--top-ratio",
            "0.5",
            "--cap3-samples",
            "cap3_positive9",
            "cap3_hole0",
            "--records-csv",
            str(records_csv),
            "--summary-csv",
            str(summary_csv),
            "--summary-md",
            str(summary_md),
        ],
    )

    module.main()

    assert records_csv.exists()
    assert summary_csv.exists()
    assert summary_md.exists()
    assert "cap3" in summary_csv.read_text(encoding="utf-8")
    assert "P6 Failure Mode Closure" in summary_md.read_text(encoding="utf-8")
    assert "cap3_positive9" in summary_md.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert f"Wrote failure mode closure markdown to {summary_md}" in stdout
