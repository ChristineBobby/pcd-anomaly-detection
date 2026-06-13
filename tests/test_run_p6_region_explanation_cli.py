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
            [[0.0, 0.0, 0.0], [0.03, 0.0, 0.0], [0.2, 0.0, 0.0], [1.0, 0.0, 0.0]],
            dtype=np.float32,
        ),
        point_scores=np.array([0.9, 0.4, 0.2, 0.1], dtype=np.float64),
        mask=np.array([1, 0, 0, 0], dtype=np.int64) if label == 1 else np.zeros(4),
        label=np.array(label, dtype=np.int64),
        object_score=np.array(0.8, dtype=np.float64),
    )


def _write_template_obj(root: Path, class_name: str) -> None:
    path = root / class_name / f"{class_name}_template0.obj"
    path.parent.mkdir(parents=True, exist_ok=True)
    vertices = np.array(
        [[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.9, 0.0, 0.0], [1.1, 0.0, 0.0]],
        dtype=np.float32,
    )
    raw_vertices = np.column_stack(
        [
            -vertices[:, 1],
            vertices[:, 2],
            -vertices[:, 0],
        ]
    )
    lines = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in raw_vertices]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_run_p6_targeted_diagnostics_cli_writes_region_explanation_outputs(
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
    region_output_dir = tmp_path / "region"
    region_summary_md = tmp_path / "region_summary.md"
    region_summary_csv = tmp_path / "region_summary.csv"
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
            str(tmp_path / "summary.md"),
            "--summary-csv",
            str(tmp_path / "summary.csv"),
            "--run-region-explanation",
            "--region-output-dir",
            str(region_output_dir),
            "--region-summary-md",
            str(region_summary_md),
            "--region-summary-csv",
            str(region_summary_csv),
            "--top-ratio",
            "0.5",
            "--neighbor-radius-ratio",
            "0.05",
            "--max-points",
            "4",
        ],
    )

    module.main()

    assert region_summary_md.exists()
    assert region_summary_csv.exists()
    assert (region_output_dir / "cap3_residual_regions.csv").exists()
    assert (region_output_dir / "tap1_region_explanation.csv").exists()
    assert "P6 Region Explanation" in region_summary_md.read_text(encoding="utf-8")
    assert "tap1_region,tap1,tap1_broken2,1" in region_summary_csv.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert f"Wrote region explanation markdown to {region_summary_md}" in stdout
