from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pcdad.analysis.pasdf_calibration import (
    PasdfCalibrationSummary,
    PasdfTopKCalibrationRecord,
    build_pasdf_topk_calibration_records,
    compute_pasdf_topk_calibration_record,
    render_pasdf_calibration_markdown,
    summarize_pasdf_calibration,
    write_pasdf_calibration_records_csv,
    write_pasdf_calibration_summary_csv,
)


def _write_score_npz(
    root: Path,
    class_name: str,
    sample_id: str,
    *,
    label: int,
    scores: np.ndarray,
    mask: np.ndarray,
    object_score: float = 0.5,
) -> Path:
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
        object_score=np.array(object_score, dtype=np.float64),
    )
    return path


def test_compute_pasdf_topk_calibration_record_scores_gt_locality(tmp_path: Path) -> None:
    score_path = _write_score_npz(
        tmp_path,
        "tap1",
        "tap1_broken2",
        label=1,
        scores=np.array([0.1, 0.9, 0.8, 0.2], dtype=np.float64),
        mask=np.array([0, 1, 0, 1], dtype=np.int64),
        object_score=0.85,
    )

    record = compute_pasdf_topk_calibration_record(score_path=score_path, top_ratio=0.5)

    assert record == PasdfTopKCalibrationRecord(
        class_name="tap1",
        sample_id="tap1_broken2",
        label=1,
        point_count=4,
        gt_point_count=2,
        gt_point_ratio=0.5,
        top_ratio=0.5,
        stored_object_score=0.85,
        topk_score=0.85,
        score_mean=0.5,
        score_p95=0.885,
        gt_score_mean=0.55,
        background_score_mean=0.45,
        gt_background_gap=0.1,
        topk_gt_hit_rate=0.5,
        gt_coverage=0.5,
        gt_enrichment=1.0,
    )


def test_compute_pasdf_topk_calibration_record_handles_positive_without_gt(
    tmp_path: Path,
) -> None:
    score_path = _write_score_npz(
        tmp_path,
        "cap3",
        "cap3_positive9",
        label=0,
        scores=np.array([0.1, 0.9, 0.8, 0.2], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
        object_score=0.85,
    )

    record = compute_pasdf_topk_calibration_record(score_path=score_path, top_ratio=0.25)

    assert record.topk_score == 0.9
    assert record.gt_point_count == 0
    assert record.gt_score_mean is None
    assert record.gt_background_gap is None
    assert record.topk_gt_hit_rate is None
    assert record.gt_coverage is None
    assert record.gt_enrichment is None


def test_build_records_rejects_invalid_top_ratio(tmp_path: Path) -> None:
    score_path = _write_score_npz(
        tmp_path,
        "helmet1",
        "helmet1_concavity2",
        label=1,
        scores=np.array([0.1, 0.2], dtype=np.float64),
        mask=np.array([1, 0], dtype=np.int64),
    )

    with pytest.raises(ValueError, match="top_ratio"):
        build_pasdf_topk_calibration_records(score_paths=[score_path], top_ratios=[0.0])


def test_summarize_pasdf_calibration_reports_object_and_localization_status(
    tmp_path: Path,
) -> None:
    paths = [
        _write_score_npz(
            tmp_path,
            "helmet1",
            "helmet1_concavity2",
            label=1,
            scores=np.array([0.9, 0.8, 0.2, 0.1], dtype=np.float64),
            mask=np.array([1, 0, 0, 0], dtype=np.int64),
        ),
        _write_score_npz(
            tmp_path,
            "helmet1",
            "helmet1_concavity4",
            label=1,
            scores=np.array([0.1, 0.9, 0.8, 0.2], dtype=np.float64),
            mask=np.array([1, 0, 0, 0], dtype=np.int64),
        ),
        _write_score_npz(
            tmp_path,
            "helmet1",
            "helmet1_positive0",
            label=0,
            scores=np.array([0.4, 0.3, 0.2, 0.1], dtype=np.float64),
            mask=np.zeros(4, dtype=np.int64),
        ),
    ]
    records = build_pasdf_topk_calibration_records(score_paths=paths, top_ratios=[0.5])

    summaries = summarize_pasdf_calibration(records)

    assert summaries == (
        PasdfCalibrationSummary(
            class_name="helmet1",
            top_ratio=0.5,
            sample_count=3,
            anomaly_count=2,
            positive_count=1,
            mean_anomaly_topk=0.85,
            mean_positive_topk=0.35,
            min_anomaly_topk=0.85,
            max_positive_topk=0.35,
            strict_object_pass=True,
            soft_object_pass=True,
            mean_gt_background_gap=0.0,
            mean_topk_gt_hit_rate=0.25,
            mean_gt_coverage=0.5,
            mean_gt_enrichment=1.0,
            weak_localization_count=1,
        ),
    )


def test_pasdf_calibration_csv_and_markdown_are_stable(tmp_path: Path) -> None:
    records = (
        PasdfTopKCalibrationRecord(
            class_name="tap1",
            sample_id="tap1_broken2",
            label=1,
            point_count=4,
            gt_point_count=1,
            gt_point_ratio=0.25,
            top_ratio=0.5,
            stored_object_score=0.8,
            topk_score=0.85,
            score_mean=0.5,
            score_p95=0.9,
            gt_score_mean=0.9,
            background_score_mean=0.366667,
            gt_background_gap=0.533333,
            topk_gt_hit_rate=0.25,
            gt_coverage=1.0,
            gt_enrichment=1.0,
        ),
        PasdfTopKCalibrationRecord(
            class_name="tap1",
            sample_id="tap1_positive0",
            label=0,
            point_count=4,
            gt_point_count=0,
            gt_point_ratio=0.0,
            top_ratio=0.5,
            stored_object_score=0.2,
            topk_score=0.25,
            score_mean=0.15,
            score_p95=0.3,
            gt_score_mean=None,
            background_score_mean=0.15,
            gt_background_gap=None,
            topk_gt_hit_rate=None,
            gt_coverage=None,
            gt_enrichment=None,
        ),
    )
    summaries = summarize_pasdf_calibration(records)

    records_csv = write_pasdf_calibration_records_csv(records, tmp_path / "records.csv")
    summary_csv = write_pasdf_calibration_summary_csv(summaries, tmp_path / "summary.csv")
    markdown = render_pasdf_calibration_markdown(records=records, summaries=summaries)

    assert (
        records_csv.read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith("class_name,sample_id,label,point_count")
    )
    assert "tap1,tap1_broken2,1,4,1,0.25,0.5" in records_csv.read_text(encoding="utf-8")
    assert "class_name,top_ratio,sample_count" in summary_csv.read_text(encoding="utf-8")
    assert "# P6 PASDF Top-k Calibration" in markdown
    assert "object score 越高表示越异常" in markdown
    assert "`tap1_broken2`" in markdown
    assert "weak localization" in markdown
