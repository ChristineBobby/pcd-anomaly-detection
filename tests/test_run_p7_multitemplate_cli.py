from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.run_p7_multitemplate import build_arg_parser, load_template_prototypes, planned_outputs
from scripts.run_p7_multitemplate import main as run_main


def test_run_p7_multitemplate_cli_dry_run_writes_expected_paths(tmp_path: Path) -> None:
    output_dir = tmp_path / "p7"
    args = build_arg_parser().parse_args(
        [
            "--score-root",
            "experiments/P5_pasdf_scores/representative",
            "--template-root",
            "third_party/PASDF/data/ShapeNetAD",
            "--classes",
            "cap3",
            "tap1",
            "--output-dir",
            str(output_dir),
            "--dry-run",
        ]
    )

    outputs = planned_outputs(args)

    assert outputs["template_assignments_csv"] == output_dir / "template_assignments.csv"
    assert outputs["per_sample_scores_csv"] == output_dir / "per_sample_scores.csv"
    assert outputs["readme"] == output_dir / "README.md"


def test_run_p7_multitemplate_cli_writes_assignment_csv(tmp_path: Path) -> None:
    score_root = tmp_path / "scores"
    template_root = tmp_path / "templates"
    output_dir = tmp_path / "out"
    sample_dir = score_root / "cap3" / "points"
    sample_dir.mkdir(parents=True)
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    np.savez(
        sample_dir / "cap3_positive9.npz",
        points=points,
        point_scores=np.array([0.0, 0.1, 0.2, 0.9], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
        label=np.array(0, dtype=np.int64),
        object_score=np.array(0.5, dtype=np.float64),
    )
    class_template_dir = template_root / "cap3"
    class_template_dir.mkdir(parents=True)
    (class_template_dir / "cap3_template0.obj").write_text(
        "\n".join(
            [
                "v 0 0 0",
                "v 1 0 0",
                "v 2 0 0",
                "v 10 0 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = run_main(
        [
            "--score-root",
            str(score_root),
            "--template-root",
            str(template_root),
            "--classes",
            "cap3",
            "--output-dir",
            str(output_dir),
            "--top-ratio",
            "0.25",
        ]
    )

    assert exit_code == 0
    assignment_csv = output_dir / "template_assignments.csv"
    text = assignment_csv.read_text(encoding="utf-8")
    assert "cap3_positive9" in text
    assert "cap3_template0" in text
    assert "template_mismatch_risk" in text
    assert (output_dir / "README.md").exists()


def test_run_p7_multitemplate_cli_loads_train_pcd_template_bank(tmp_path: Path) -> None:
    score_root = tmp_path / "scores"
    template_root = tmp_path / "dataset" / "16384"
    output_dir = tmp_path / "out"
    sample_dir = score_root / "cap3" / "points"
    sample_dir.mkdir(parents=True)
    points = np.array(
        [
            [10.0, 0.0, 0.0],
            [10.1, 0.0, 0.0],
            [10.2, 0.0, 0.0],
            [10.3, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    np.savez(
        sample_dir / "cap3_positive9.npz",
        points=points,
        point_scores=np.array([0.0, 0.1, 0.2, 0.9], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
        label=np.array(0, dtype=np.int64),
        object_score=np.array(0.5, dtype=np.float64),
    )
    train_dir = template_root / "cap3" / "train"
    train_dir.mkdir(parents=True)
    _write_ascii_pcd(
        train_dir / "cap3_template0.pcd",
        np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0]], dtype=np.float32),
    )
    _write_ascii_pcd(train_dir / "cap3_template1.pcd", points)

    exit_code = run_main(
        [
            "--score-root",
            str(score_root),
            "--template-root",
            str(template_root),
            "--template-mode",
            "train_pcd",
            "--classes",
            "cap3",
            "--output-dir",
            str(output_dir),
            "--top-ratio",
            "0.25",
        ]
    )

    assert exit_code == 0
    assignment_text = (output_dir / "template_assignments.csv").read_text(encoding="utf-8")
    per_sample_text = (output_dir / "per_sample_scores.csv").read_text(encoding="utf-8")
    lines = assignment_text.strip().splitlines()
    assert len(lines) == 3
    assert "cap3_template1,1," in assignment_text
    assert "cap3_template0,2," in assignment_text
    assert "top2_nn_topk_mean" in per_sample_text
    assert "top1_top2_margin" in per_sample_text
    assert "top1_top2_relative_margin" in per_sample_text
    assert "template_mode: train_pcd" in (output_dir / "config.yaml").read_text(encoding="utf-8")


def test_load_template_prototypes_supports_train_pcd_mode(tmp_path: Path) -> None:
    train_dir = tmp_path / "cap3" / "train"
    train_dir.mkdir(parents=True)
    _write_ascii_pcd(train_dir / "cap3_template0.pcd", np.zeros((3, 3), dtype=np.float32))
    _write_ascii_pcd(train_dir / "cap3_template1.pcd", np.ones((4, 3), dtype=np.float32))

    templates = load_template_prototypes(tmp_path, "cap3", template_mode="train_pcd")

    assert [template.template_id for template in templates] == ["cap3_template0", "cap3_template1"]
    assert templates[0].points.shape == (3, 3)
    assert templates[1].points.shape == (4, 3)


def _write_ascii_pcd(path: Path, points: np.ndarray) -> None:
    rows = ["{:.6f} {:.6f} {:.6f}".format(*point) for point in points]
    path.write_text(
        "\n".join(
            [
                "# .PCD v0.7 - Point Cloud Data file format",
                "VERSION 0.7",
                "FIELDS x y z",
                "SIZE 4 4 4",
                "TYPE F F F",
                "COUNT 1 1 1",
                f"WIDTH {len(points)}",
                "HEIGHT 1",
                "VIEWPOINT 0 0 0 1 0 0 0",
                f"POINTS {len(points)}",
                "DATA ascii",
                *rows,
                "",
            ]
        ),
        encoding="ascii",
    )
