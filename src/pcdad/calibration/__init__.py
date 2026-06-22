"""Positive-aware calibration utilities."""

from pcdad.calibration.positive_aware import (
    BoundaryMargin,
    CalibrationRecord,
    CalibrationSummary,
    boundary_margin,
    build_feature_matrix,
    calibrate_scores,
    confidence_gated_score,
    load_calibration_records,
    summarize_calibration,
    write_boundary_margins_csv,
    write_calibration_records_csv,
    write_calibration_summaries_csv,
)

__all__ = [
    "BoundaryMargin",
    "CalibrationRecord",
    "CalibrationSummary",
    "build_feature_matrix",
    "boundary_margin",
    "calibrate_scores",
    "confidence_gated_score",
    "load_calibration_records",
    "summarize_calibration",
    "write_boundary_margins_csv",
    "write_calibration_records_csv",
    "write_calibration_summaries_csv",
]
