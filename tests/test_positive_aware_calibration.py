from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pcdad.calibration.positive_aware import (
    CalibrationRecord,
    boundary_margin,
    build_feature_matrix,
    calibrate_scores,
    confidence_gated_score,
    load_calibration_records,
    summarize_calibration,
)


def test_boundary_margin_strict_pass_and_failure() -> None:
    strict_records = (
        _record("cap3", "positive0", 0, pasdf_score=0.2),
        _record("cap3", "anomaly0", 1, pasdf_score=0.8),
    )
    failed_records = (
        _record("cap3", "positive0", 0, pasdf_score=0.9),
        _record("cap3", "anomaly0", 1, pasdf_score=0.7),
    )

    strict = boundary_margin(strict_records, "pasdf_score")
    failed = boundary_margin(failed_records, "pasdf_score")

    assert strict.margin == pytest.approx(0.6)
    assert strict.strict_pass is True
    assert strict.max_positive_sample_id == "positive0"
    assert failed.margin == pytest.approx(-0.2)
    assert failed.strict_pass is False


def test_build_feature_matrix_uses_requested_features_only() -> None:
    records = (
        _record("cap3", "positive0", 0, pasdf_score=0.2, template_score=0.3),
        _record("cap3", "anomaly0", 1, pasdf_score=0.8, template_score=0.4),
    )

    features, labels = build_feature_matrix(
        records,
        ("pasdf_score", "template_score", "registration_confidence"),
    )

    assert features.shape == (2, 3)
    assert np.allclose(features[0], [0.2, 0.3, 0.5])
    assert labels.tolist() == [0, 1]


def test_build_feature_matrix_supports_gated_pasdf_feature() -> None:
    records = (_record("cap3", "positive0", 0, pasdf_score=0.8, registration_confidence=0.25),)

    features, labels = build_feature_matrix(records, ("gated_pasdf_score",))

    assert features.shape == (1, 1)
    assert features[0, 0] == pytest.approx(0.2)
    assert labels.tolist() == [0]


def test_confidence_gate_reduces_low_confidence_high_score() -> None:
    high_conf = confidence_gated_score(pasdf_score=0.8, registration_confidence=0.9)
    low_conf = confidence_gated_score(pasdf_score=0.8, registration_confidence=0.2)

    assert high_conf == pytest.approx(0.72)
    assert low_conf == pytest.approx(0.16)
    assert low_conf < high_conf


def test_calibrate_scores_leave_one_class_out_does_not_train_on_heldout_class() -> None:
    records = (
        _record("cap3", "cap_pos", 0, pasdf_score=0.9, registration_confidence=0.2),
        _record("cap3", "cap_anom", 1, pasdf_score=0.7, registration_confidence=0.8),
        _record("tap1", "tap_pos", 0, pasdf_score=0.1, registration_confidence=0.9),
        _record("tap1", "tap_anom", 1, pasdf_score=0.8, registration_confidence=0.9),
        _record("helmet1", "helmet_pos", 0, pasdf_score=0.2, registration_confidence=0.9),
        _record("helmet1", "helmet_anom", 1, pasdf_score=0.85, registration_confidence=0.9),
    )

    calibrated = calibrate_scores(
        records,
        method="logistic_l2",
        feature_names=("pasdf_score", "registration_confidence"),
        split_mode="leave_one_class_out",
    )

    cap_rows = [record for record in calibrated if record.class_name == "cap3"]
    assert {record.split_tag for record in cap_rows} == {"leave_one_class_out:cap3"}
    assert all(record.method == "logistic_l2" for record in calibrated)
    assert all(0.0 <= record.calibrated_score <= 1.0 for record in calibrated)


def test_summarize_calibration_reports_false_positive_top1() -> None:
    records = (
        _record("cap3", "positive_low", 0, pasdf_score=0.1, calibrated_score=0.1),
        _record("cap3", "positive_high", 0, pasdf_score=0.9, calibrated_score=0.7),
        _record("cap3", "anomaly", 1, pasdf_score=0.8, calibrated_score=0.8),
    )

    summaries = summarize_calibration(records, score_fields=("pasdf_score", "calibrated_score"))

    calibrated = next(item for item in summaries if item.score_field == "calibrated_score")
    assert calibrated.class_name == "cap3"
    assert calibrated.false_positive_top1_sample_id == "positive_high"
    assert calibrated.boundary_margin == pytest.approx(0.1)
    assert calibrated.strict_pass is True


def test_summarize_calibration_keeps_methods_and_splits_separate() -> None:
    raw = (
        _record("cap3", "positive", 0, pasdf_score=0.9, calibrated_score=0.9),
        _record("cap3", "anomaly", 1, pasdf_score=0.8, calibrated_score=0.8),
    )
    gated = tuple(
        record.__class__(
            **{
                **record.__dict__,
                "calibrated_score": record.calibrated_score * 0.1,
                "method": "confidence_gate",
                "split_tag": "none",
            }
        )
        for record in raw
    )

    summaries = summarize_calibration(
        (*raw, *gated),
        score_fields=("calibrated_score",),
    )

    keys = {(item.method, item.split_tag, item.sample_count) for item in summaries}
    assert keys == {("input", "none", 2), ("confidence_gate", "none", 2)}


def test_load_calibration_records_reads_p7a_per_sample_csv(tmp_path: Path) -> None:
    path = tmp_path / "per_sample_scores.csv"
    path.write_text(
        "\n".join(
            [
                "class_name,sample_id,label,point_count,gt_point_count,pasdf_object_score,"
                "nn_topk_mean,residual_overlap,assignment_entropy,registration_confidence,"
                "top1_top2_margin",
                "cap3,cap3_positive9,0,16384,0,0.109517,0.275955,0.634146,"
                "0.778389,0.27047,0.004327",
                "",
            ]
        ),
        encoding="utf-8",
    )

    records = load_calibration_records(path, dataset_name="anomaly_shapenet_16384")

    assert len(records) == 1
    assert records[0].dataset_name == "anomaly_shapenet_16384"
    assert records[0].sample_id == "cap3_positive9"
    assert records[0].pasdf_score == pytest.approx(0.109517)
    assert records[0].template_score == pytest.approx(0.275955)


def _record(
    class_name: str,
    sample_id: str,
    label: int,
    *,
    pasdf_score: float,
    template_score: float = 0.1,
    registration_confidence: float = 0.5,
    assignment_entropy: float = 0.2,
    residual_overlap: float = 0.1,
    top1_top2_margin: float = 0.05,
    calibrated_score: float | None = None,
) -> CalibrationRecord:
    return CalibrationRecord(
        dataset_name="unit",
        class_name=class_name,
        sample_id=sample_id,
        label=label,
        point_count=100,
        gt_point_count=5 if label else 0,
        pasdf_score=pasdf_score,
        template_score=template_score,
        registration_confidence=registration_confidence,
        assignment_entropy=assignment_entropy,
        residual_overlap=residual_overlap,
        top1_top2_margin=top1_top2_margin,
        calibrated_score=pasdf_score if calibrated_score is None else calibrated_score,
        method="input",
        split_tag="none",
        note="",
    )
