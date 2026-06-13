from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "visualize_pasdf_scores.py"
    spec = importlib.util.spec_from_file_location("visualize_pasdf_scores_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_score_npz(root: Path, class_name: str, sample_id: str) -> None:
    path = root / class_name / "points" / f"{sample_id}.npz"
    path.parent.mkdir(parents=True)
    np.savez_compressed(
        path,
        points=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32),
        point_scores=np.array([0.2, 0.8], dtype=np.float64),
        mask=np.array([0, 1], dtype=np.int64),
        label=np.array(1, dtype=np.int64),
        object_score=np.array(0.8, dtype=np.float64),
    )


def _write_template_obj(root: Path, class_name: str) -> None:
    path = root / class_name / f"{class_name}_template0.obj"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "v 0.0 0.0 0.0",
                "v 1.0 0.0 0.0",
                "v 0.0 1.0 0.0",
                "v 1.0 1.0 0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_visualize_pasdf_scores_cli_writes_markdown_csv_and_svg(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    score_root = tmp_path / "scores"
    template_root = tmp_path / "templates"
    _write_score_npz(score_root, "cap3", "cap3_positive9")
    _write_template_obj(template_root, "cap3")
    output_dir = tmp_path / "case_study"
    summary_md = tmp_path / "summary.md"
    summary_csv = tmp_path / "summary.csv"
    monkeypatch.setattr(
        "sys.argv",
        [
            "visualize_pasdf_scores.py",
            "--score-root",
            str(score_root),
            "--samples",
            "cap3_positive9",
            "--template-root",
            str(template_root),
            "--template-overlay-samples",
            "cap3_positive9",
            "--geometry-comparison-samples",
            "cap3_positive9",
            "--output-dir",
            str(output_dir),
            "--summary-md",
            str(summary_md),
            "--summary-csv",
            str(summary_csv),
            "--max-points",
            "2",
        ],
    )

    module.main()

    assert summary_md.read_text(encoding="utf-8").startswith("# P5 PASDF Targeted Case Study")
    assert "cap3,cap3_positive9,1,2,1,0.8" in summary_csv.read_text(encoding="utf-8")
    assert (output_dir / "pasdf_scores" / "cap3" / "cap3_positive9_pasdf_score.svg").exists()
    assert (
        output_dir / "template_overlay" / "cap3" / "cap3_positive9_template_overlay.svg"
    ).exists()
    assert (
        output_dir / "pasdf_vs_geometry" / "cap3" / "cap3_positive9_pasdf_vs_geometry.svg"
    ).exists()
    stdout = capsys.readouterr().out
    assert f"Wrote PASDF case-study markdown to {summary_md}" in stdout
    assert f"Wrote PASDF case-study CSV to {summary_csv}" in stdout
