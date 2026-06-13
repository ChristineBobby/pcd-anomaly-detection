from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.analysis.targeted_p6 import (
    AlphaSweepRecord,
    AlphaSweepSummary,
    summarize_alpha_sweep,
    write_alpha_sweep_records_csv,
    write_alpha_sweep_summary_csv,
)


def test_summarize_alpha_sweep_marks_strict_and_soft_passes() -> None:
    records = (
        AlphaSweepRecord(
            alpha=0.1,
            class_name="tap1",
            sample_id="tap1_broken2",
            label=1,
            hybrid_object_score=0.5,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            pasdf_separation=0.01,
            hybrid_separation=0.03,
            separation_gain=0.02,
        ),
        AlphaSweepRecord(
            alpha=0.1,
            class_name="tap1",
            sample_id="tap1_broken3",
            label=1,
            hybrid_object_score=0.6,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            pasdf_separation=0.01,
            hybrid_separation=0.04,
            separation_gain=0.03,
        ),
        AlphaSweepRecord(
            alpha=0.1,
            class_name="tap1",
            sample_id="tap1_positive0",
            label=0,
            hybrid_object_score=0.4,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            pasdf_separation=None,
            hybrid_separation=None,
            separation_gain=None,
        ),
        AlphaSweepRecord(
            alpha=1.0,
            class_name="tap1",
            sample_id="tap1_broken2",
            label=1,
            hybrid_object_score=0.9,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            pasdf_separation=0.01,
            hybrid_separation=0.05,
            separation_gain=0.04,
        ),
        AlphaSweepRecord(
            alpha=1.0,
            class_name="tap1",
            sample_id="tap1_positive0",
            label=0,
            hybrid_object_score=1.2,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            pasdf_separation=None,
            hybrid_separation=None,
            separation_gain=None,
        ),
    )

    summaries = summarize_alpha_sweep(records)

    assert summaries[0] == AlphaSweepSummary(
        alpha=0.1,
        anomaly_count=2,
        positive_count=1,
        min_anomaly_hybrid_object=0.5,
        mean_anomaly_hybrid_object=0.55,
        max_positive_hybrid_object=0.4,
        mean_anomaly_separation_gain=0.025,
        strict_pass=True,
        soft_pass=True,
    )
    assert summaries[1].alpha == 1.0
    assert summaries[1].strict_pass is False
    assert summaries[1].soft_pass is False


def test_write_alpha_sweep_csvs_are_stable(tmp_path: Path) -> None:
    records = (
        AlphaSweepRecord(
            alpha=0.25,
            class_name="tap1",
            sample_id="tap1_broken2",
            label=1,
            hybrid_object_score=0.5,
            pasdf_object_score=0.1,
            geometry_object_score=0.2,
            pasdf_separation=0.01,
            hybrid_separation=0.03,
            separation_gain=0.02,
        ),
    )
    summaries = summarize_alpha_sweep(records)

    records_csv = write_alpha_sweep_records_csv(records, tmp_path / "records.csv")
    summary_csv = write_alpha_sweep_summary_csv(summaries, tmp_path / "summary.csv")

    assert records_csv.read_text(encoding="utf-8").splitlines()[0] == (
        "alpha,class_name,sample_id,label,hybrid_object_score,pasdf_object_score,"
        "geometry_object_score,pasdf_separation,hybrid_separation,separation_gain"
    )
    assert "0.25,tap1,tap1_broken2,1,0.5,0.1,0.2,0.01,0.03,0.02" in records_csv.read_text(
        encoding="utf-8"
    )
    assert "0.25,1,0,0.5,0.5,,0.02,False,False" in summary_csv.read_text(encoding="utf-8")


def test_alpha_sweep_record_can_be_built_from_score_arrays() -> None:
    from pcdad.analysis.targeted_p6 import build_alpha_sweep_record_from_scores

    pasdf_scores = np.array([0.0, 0.1, 0.8, 1.0], dtype=np.float64)
    geometry_scores = np.array([0.0, 0.2, 0.9, 1.0], dtype=np.float64)
    mask = np.array([0, 0, 1, 1], dtype=np.int64)

    record = build_alpha_sweep_record_from_scores(
        alpha=0.5,
        class_name="tap1",
        sample_id="tap1_broken2",
        label=1,
        pasdf_object_score=0.2,
        geometry_object_score=0.3,
        pasdf_scores=pasdf_scores,
        geometry_scores=geometry_scores,
        mask=mask,
    )

    assert record.alpha == 0.5
    assert record.label == 1
    assert record.hybrid_object_score > record.pasdf_object_score
    assert record.separation_gain is not None
    assert record.separation_gain > 0.0
