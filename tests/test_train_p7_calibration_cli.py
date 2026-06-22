from __future__ import annotations

from pathlib import Path

from scripts.train_p7_calibration import build_arg_parser, main, planned_outputs


def test_train_p7_calibration_cli_dry_run_outputs_expected_paths(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    args = build_arg_parser().parse_args(
        [
            "--input-csv",
            "experiments/P7_A_multitemplate/four_class_train_pcd/per_sample_scores.csv",
            "--output-dir",
            str(output_dir),
            "--classes",
            "cap3",
            "tap1",
            "--dry-run",
        ]
    )

    outputs = planned_outputs(args)

    assert outputs["calibration_records_csv"] == output_dir / "calibration_records.csv"
    assert outputs["metrics_csv"] == output_dir / "metrics.csv"
    assert outputs["boundary_margin_csv"] == output_dir / "boundary_margin.csv"
    assert outputs["failure_toplist_csv"] == output_dir / "failure_toplist.csv"
    assert outputs["readme"] == output_dir / "README.md"


def test_train_p7_calibration_cli_writes_outputs(tmp_path: Path) -> None:
    input_csv = tmp_path / "per_sample_scores.csv"
    output_dir = tmp_path / "out"
    input_csv.write_text(
        "\n".join(
            [
                "class_name,sample_id,label,point_count,gt_point_count,pasdf_object_score,"
                "nn_topk_mean,residual_overlap,assignment_entropy,registration_confidence,"
                "top1_top2_margin",
                "cap3,cap3_positive9,0,100,0,0.9,0.3,0.6,0.8,0.2,0.01",
                "cap3,cap3_hole0,1,100,5,0.7,0.2,0.1,0.4,0.8,0.05",
                "tap1,tap1_positive0,0,100,0,0.1,0.2,0.0,0.2,0.9,0.2",
                "tap1,tap1_broken2,1,100,5,0.8,0.3,0.1,0.3,0.9,0.2",
                "helmet1,helmet1_positive0,0,100,0,0.2,0.2,0.0,0.2,0.9,0.2",
                "helmet1,helmet1_concavity1,1,100,5,0.85,0.3,0.1,0.3,0.9,0.2",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--input-csv",
            str(input_csv),
            "--output-dir",
            str(output_dir),
            "--classes",
            "cap3",
            "tap1",
            "helmet1",
            "--methods",
            "pasdf_raw",
            "confidence_gate",
            "logistic_l2",
            "--split-modes",
            "none",
            "leave_one_class_out",
        ]
    )

    assert exit_code == 0
    records_text = (output_dir / "calibration_records.csv").read_text(encoding="utf-8")
    metrics_text = (output_dir / "metrics.csv").read_text(encoding="utf-8")
    boundary_text = (output_dir / "boundary_margin.csv").read_text(encoding="utf-8")
    toplist_text = (output_dir / "failure_toplist.csv").read_text(encoding="utf-8")
    readme_text = (output_dir / "README.md").read_text(encoding="utf-8")

    assert "logistic_l2" in records_text
    assert "boundary_margin" in metrics_text
    assert "max_positive_sample_id" in boundary_text
    assert "cap3_positive9" in toplist_text
    assert "P7-B Positive-aware Calibration" in readme_text
