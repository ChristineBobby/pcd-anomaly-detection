from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_p6_pasdf_calibration.py"
    spec = importlib.util.spec_from_file_location("run_p6_pasdf_calibration_script", script_path)
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


def test_run_p6_pasdf_calibration_cli_writes_stage_records(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    score_root = tmp_path / "scores"
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
    records_csv = tmp_path / "records.csv"
    summary_csv = tmp_path / "summary.csv"
    summary_md = tmp_path / "summary.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_p6_pasdf_calibration.py",
            "--score-root",
            str(score_root),
            "--classes",
            "tap1",
            "--top-ratios",
            "0.5",
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
    assert "tap1,tap1_broken2,1" in records_csv.read_text(encoding="utf-8")
    assert "tap1,0.5,2,1,1" in summary_csv.read_text(encoding="utf-8")
    assert "P6 PASDF Top-k Calibration" in summary_md.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF calibration markdown to {summary_md}" in stdout
