from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.analysis.targeted_p6 import (
    HybridScoreRecord,
    RegistrationDiagnosticRecord,
    compute_hybrid_score_record,
    compute_registration_diagnostic_record,
    render_p6_targeted_summary,
    write_hybrid_scores_csv,
    write_registration_diagnostics_csv,
)


def _write_score_npz(
    root: Path,
    class_name: str,
    sample_id: str,
    *,
    label: int = 1,
) -> Path:
    path = root / class_name / "points" / f"{sample_id}.npz"
    path.parent.mkdir(parents=True)
    np.savez_compressed(
        path,
        points=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [2.0, 2.0, 0.0],
            ],
            dtype=np.float32,
        ),
        point_scores=np.array([0.1, 0.2, 0.3, 0.9], dtype=np.float64),
        mask=np.array([0, 0, 1, 1], dtype=np.int64) if label == 1 else np.zeros(4),
        label=np.array(label, dtype=np.int64),
        object_score=np.array(0.9, dtype=np.float64),
    )
    return path


def _write_template_obj(root: Path, class_name: str) -> Path:
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
    return path


def test_compute_registration_diagnostic_record_reports_distance_summary(
    tmp_path: Path,
) -> None:
    score_path = _write_score_npz(tmp_path / "scores", "cap3", "cap3_positive9", label=0)
    _write_template_obj(tmp_path / "templates", "cap3")

    record = compute_registration_diagnostic_record(
        score_path=score_path,
        template_root=tmp_path / "templates",
    )

    assert isinstance(record, RegistrationDiagnosticRecord)
    assert record.class_name == "cap3"
    assert record.sample_id == "cap3_positive9"
    assert record.label == 0
    assert record.point_count == 4
    assert record.gt_point_count == 0
    assert record.pasdf_object_score == 0.9
    assert record.nn_distance_mean >= 0.0
    assert record.nn_distance_p95 >= record.nn_distance_mean
    assert record.nn_distance_p99 >= record.nn_distance_p95
    assert record.nn_distance_top5_mean >= record.nn_distance_mean


def test_compute_hybrid_score_record_fuses_pasdf_and_geometry_scores(
    tmp_path: Path,
) -> None:
    score_path = _write_score_npz(tmp_path / "scores", "tap1", "tap1_broken2", label=1)
    _write_template_obj(tmp_path / "templates", "tap1")
    svg_path = tmp_path / "out" / "tap1_broken2_hybrid.svg"

    record = compute_hybrid_score_record(
        score_path=score_path,
        template_root=tmp_path / "templates",
        alpha=1.0,
        svg_path=svg_path,
        max_points=4,
        seed=7,
    )

    assert isinstance(record, HybridScoreRecord)
    assert record.class_name == "tap1"
    assert record.sample_id == "tap1_broken2"
    assert record.label == 1
    assert record.pasdf_object_score == 0.9
    assert record.geometry_object_score >= 0.0
    assert record.hybrid_object_score >= record.pasdf_object_score
    assert record.hybrid_gt_mean is not None
    assert record.hybrid_background_mean is not None
    assert record.hybrid_gt_mean > record.hybrid_background_mean
    assert record.svg_path == str(svg_path)
    assert svg_path.exists()
    assert "Hybrid score" in svg_path.read_text(encoding="utf-8")


def test_p6_csv_and_markdown_are_stable(tmp_path: Path) -> None:
    registration_records = (
        RegistrationDiagnosticRecord(
            class_name="cap3",
            sample_id="cap3_positive9",
            label=0,
            point_count=4,
            gt_point_count=0,
            nn_distance_mean=0.1,
            nn_distance_p95=0.2,
            nn_distance_p99=0.3,
            nn_distance_top5_mean=0.4,
            pasdf_object_score=0.9,
        ),
    )
    hybrid_records = (
        HybridScoreRecord(
            class_name="tap1",
            sample_id="tap1_broken2",
            label=1,
            point_count=4,
            gt_point_count=2,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            hybrid_object_score=0.3,
            pasdf_gt_mean=0.4,
            pasdf_background_mean=0.2,
            geometry_gt_mean=0.5,
            geometry_background_mean=0.3,
            hybrid_gt_mean=0.7,
            hybrid_background_mean=0.4,
            svg_path="experiments/P6/tap1_broken2.svg",
        ),
    )

    registration_csv = write_registration_diagnostics_csv(
        registration_records,
        tmp_path / "registration.csv",
    )
    hybrid_csv = write_hybrid_scores_csv(hybrid_records, tmp_path / "hybrid.csv")
    markdown = render_p6_targeted_summary(registration_records, hybrid_records)

    assert (
        registration_csv.read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith("class_name,sample_id,label")
    )
    assert "cap3,cap3_positive9,0,4,0,0.1,0.2,0.3,0.4,0.9" in registration_csv.read_text(
        encoding="utf-8"
    )
    assert "tap1,tap1_broken2,1,4,2,0.1,0.2,0.3" in hybrid_csv.read_text(encoding="utf-8")
    assert "P6 Targeted Diagnostics" in markdown
    assert "cap3 registration/template mismatch" in markdown
    assert "tap1 PASDF + geometry fusion" in markdown
