from __future__ import annotations

from pathlib import Path

from pcdad.analysis.failure_modes import (
    BoundarySampleRecord,
    Cap3TemplateMismatchRecord,
    FailureModeClosureRecord,
    WeakLocalizationRecord,
    build_boundary_record,
    build_failure_mode_closure_records,
    build_weak_localization_records,
    classify_cap3_template_mismatch,
    render_failure_mode_closure_markdown,
    write_failure_mode_closure_csv,
)
from pcdad.analysis.pasdf_calibration import PasdfCalibrationSummary, PasdfTopKCalibrationRecord
from pcdad.analysis.targeted_p6 import Cap3ResidualRegionRecord


def _calibration_record(
    *,
    class_name: str,
    sample_id: str,
    label: int,
    topk_score: float,
    gt_background_gap: float | None = None,
    gt_enrichment: float | None = None,
) -> PasdfTopKCalibrationRecord:
    return PasdfTopKCalibrationRecord(
        class_name=class_name,
        sample_id=sample_id,
        label=label,
        point_count=4,
        gt_point_count=1 if label == 1 else 0,
        gt_point_ratio=0.25 if label == 1 else 0.0,
        top_ratio=0.01,
        stored_object_score=topk_score,
        topk_score=topk_score,
        score_mean=topk_score / 2,
        score_p95=topk_score,
        gt_score_mean=None if label == 0 else topk_score,
        background_score_mean=topk_score / 2,
        gt_background_gap=gt_background_gap,
        topk_gt_hit_rate=None if label == 0 else 0.25,
        gt_coverage=None if label == 0 else 0.5,
        gt_enrichment=gt_enrichment,
    )


def _summary(
    *,
    class_name: str,
    strict: bool,
    soft: bool,
    weak_count: int,
    mean_anomaly: float = 0.8,
    max_positive: float = 0.5,
) -> PasdfCalibrationSummary:
    return PasdfCalibrationSummary(
        class_name=class_name,
        top_ratio=0.01,
        sample_count=3,
        anomaly_count=2,
        positive_count=1,
        mean_anomaly_topk=mean_anomaly,
        mean_positive_topk=0.2,
        min_anomaly_topk=0.4,
        max_positive_topk=max_positive,
        strict_object_pass=strict,
        soft_object_pass=soft,
        mean_gt_background_gap=0.1,
        mean_topk_gt_hit_rate=0.2,
        mean_gt_coverage=0.5,
        mean_gt_enrichment=4.0,
        weak_localization_count=weak_count,
    )


def test_boundary_record_reports_margin_from_lowest_anomaly_to_highest_positive() -> None:
    records = (
        _calibration_record(class_name="tap1", sample_id="tap1_broken2", label=1, topk_score=0.4),
        _calibration_record(class_name="tap1", sample_id="tap1_hole0", label=1, topk_score=0.2),
        _calibration_record(
            class_name="tap1",
            sample_id="tap1_positive0",
            label=0,
            topk_score=0.3,
        ),
    )

    boundary = build_boundary_record(records, class_name="tap1", top_ratio=0.01)

    assert boundary == BoundarySampleRecord(
        class_name="tap1",
        top_ratio=0.01,
        highest_positive_sample="tap1_positive0",
        highest_positive_score=0.3,
        lowest_anomaly_sample="tap1_hole0",
        lowest_anomaly_score=0.2,
        boundary_margin=-0.1,
    )


def test_weak_localization_records_capture_low_enrichment_and_negative_gap() -> None:
    records = (
        _calibration_record(
            class_name="helmet1",
            sample_id="helmet1_concavity1",
            label=1,
            topk_score=0.4,
            gt_background_gap=0.1,
            gt_enrichment=0.8,
        ),
        _calibration_record(
            class_name="helmet1",
            sample_id="helmet1_concavity2",
            label=1,
            topk_score=0.3,
            gt_background_gap=-0.01,
            gt_enrichment=2.0,
        ),
        _calibration_record(
            class_name="helmet1",
            sample_id="helmet1_positive0",
            label=0,
            topk_score=0.5,
        ),
    )

    weak = build_weak_localization_records(records, class_name="helmet1", top_ratio=0.01)

    assert weak == (
        WeakLocalizationRecord(
            class_name="helmet1",
            sample_id="helmet1_concavity1",
            top_ratio=0.01,
            gt_background_gap=0.1,
            gt_enrichment=0.8,
            reason="gt_enrichment<=1",
        ),
        WeakLocalizationRecord(
            class_name="helmet1",
            sample_id="helmet1_concavity2",
            top_ratio=0.01,
            gt_background_gap=-0.01,
            gt_enrichment=2.0,
            reason="gt_background_gap<=0",
        ),
    )


def test_classify_cap3_template_mismatch_uses_overlap_strength() -> None:
    strong = Cap3ResidualRegionRecord(
        class_name="cap3",
        sample_id="cap3_positive9",
        label=0,
        point_count=4,
        pasdf_object_score=0.9,
        residual_topk_mean=0.4,
        residual_topk_p95=0.5,
        pasdf_residual_topk_overlap=0.95,
        residual_topk_bbox_ratio=0.4,
        residual_topk_mean_pair_distance_ratio=0.1,
    )
    partial = Cap3ResidualRegionRecord(
        class_name="cap3",
        sample_id="cap3_broken3",
        label=1,
        point_count=4,
        pasdf_object_score=0.2,
        residual_topk_mean=0.1,
        residual_topk_p95=0.2,
        pasdf_residual_topk_overlap=0.6,
        residual_topk_bbox_ratio=0.9,
        residual_topk_mean_pair_distance_ratio=0.4,
    )

    assert (
        classify_cap3_template_mismatch(strong).closure_label == "strong_positive_template_mismatch"
    )
    assert (
        classify_cap3_template_mismatch(partial).closure_label == "anomaly_residual_overlap_control"
    )


def test_failure_mode_closure_records_are_class_specific() -> None:
    summaries = (
        _summary(class_name="cap3", strict=False, soft=False, weak_count=5),
        _summary(class_name="tap1", strict=False, soft=True, weak_count=2),
        _summary(class_name="helmet1", strict=False, soft=False, weak_count=3),
    )

    closures = build_failure_mode_closure_records(summaries)

    assert closures == (
        FailureModeClosureRecord(
            class_name="cap3",
            primary_failure_mode="registration/template false positive",
            object_boundary_status="failed",
            localization_status="5 weak-localization anomaly samples",
            evidence="top-k calibration failed; cap3 positive residual overlap should be checked",
            next_action="continue registration/template robustness; do not tune PASDF top-k only",
        ),
        FailureModeClosureRecord(
            class_name="helmet1",
            primary_failure_mode="point-level localization weakness",
            object_boundary_status="failed",
            localization_status="3 weak-localization anomaly samples",
            evidence="mean anomaly can be high but positive boundary still overlaps",
            next_action="audit weak-localization anomalies and high positive boundary samples",
        ),
        FailureModeClosureRecord(
            class_name="tap1",
            primary_failure_mode="soft object boundary with low-amplitude local PASDF signal",
            object_boundary_status="soft_pass",
            localization_status="2 weak-localization anomaly samples",
            evidence=(
                "PASDF-only calibration soft-passes; additive geometry fusion remains rejected"
            ),
            next_action=(
                "audit positive boundary and low-score anomalies; keep geometry as diagnostic only"
            ),
        ),
    )


def test_failure_mode_closure_csv_and_markdown_are_stable(tmp_path: Path) -> None:
    closures = (
        FailureModeClosureRecord(
            class_name="cap3",
            primary_failure_mode="registration/template false positive",
            object_boundary_status="failed",
            localization_status="5 weak-localization anomaly samples",
            evidence="top-k calibration failed",
            next_action="continue registration/template robustness",
        ),
    )
    boundaries = (
        BoundarySampleRecord(
            class_name="cap3",
            top_ratio=0.01,
            highest_positive_sample="cap3_positive9",
            highest_positive_score=0.9,
            lowest_anomaly_sample="cap3_hole0",
            lowest_anomaly_score=0.1,
            boundary_margin=-0.8,
        ),
    )
    weak_records = (
        WeakLocalizationRecord(
            class_name="cap3",
            sample_id="cap3_broken3",
            top_ratio=0.01,
            gt_background_gap=-0.01,
            gt_enrichment=0.0,
            reason="gt_enrichment<=1;gt_background_gap<=0",
        ),
    )
    cap3_records = (
        Cap3TemplateMismatchRecord(
            sample_id="cap3_positive9",
            label=0,
            pasdf_object_score=0.9,
            residual_topk_mean=0.4,
            pasdf_residual_topk_overlap=0.95,
            residual_topk_bbox_ratio=0.4,
            residual_topk_mean_pair_distance_ratio=0.1,
            closure_label="strong_positive_template_mismatch",
        ),
    )

    csv_path = write_failure_mode_closure_csv(closures, tmp_path / "closure.csv")
    markdown = render_failure_mode_closure_markdown(
        closures=closures,
        boundaries=boundaries,
        weak_records=weak_records,
        cap3_records=cap3_records,
    )

    assert (
        csv_path.read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith("class_name,primary_failure_mode")
    )
    assert "cap3,registration/template false positive" in csv_path.read_text(encoding="utf-8")
    assert "# P6 Failure Mode Closure" in markdown
    assert "## 类别闭环结论" in markdown
    assert "`cap3_positive9`" in markdown
    assert "strong_positive_template_mismatch" in markdown
