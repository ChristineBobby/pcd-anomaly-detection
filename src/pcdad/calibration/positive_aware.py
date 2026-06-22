"""Positive-aware calibration for object-level anomaly scores."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import average_precision_score, roc_auc_score  # type: ignore[import-untyped]


@dataclass(frozen=True)
class CalibrationRecord:
    """One sample score record used by P7-B calibration."""

    dataset_name: str
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    pasdf_score: float
    template_score: float
    registration_confidence: float
    assignment_entropy: float
    residual_overlap: float
    top1_top2_margin: float
    calibrated_score: float
    method: str
    split_tag: str
    note: str = ""


@dataclass(frozen=True)
class BoundaryMargin:
    """Positive-aware object boundary summary."""

    class_name: str
    score_field: str
    sample_count: int
    positive_count: int
    anomaly_count: int
    max_positive_score: float | None
    max_positive_sample_id: str | None
    min_anomaly_score: float | None
    min_anomaly_sample_id: str | None
    margin: float | None
    strict_pass: bool


@dataclass(frozen=True)
class CalibrationSummary:
    """Class-level score summary for one score field."""

    method: str
    split_tag: str
    class_name: str
    score_field: str
    sample_count: int
    positive_count: int
    anomaly_count: int
    object_auroc: float | None
    object_aupr: float | None
    max_positive_score: float | None
    min_anomaly_score: float | None
    boundary_margin: float | None
    strict_pass: bool
    false_positive_top1_sample_id: str | None
    false_positive_top1_score: float | None


FEATURE_ALIASES: dict[str, str] = {
    "pasdf_object_score": "pasdf_score",
    "nn_topk_mean": "template_score",
}

CALIBRATION_RECORD_FIELDS: tuple[str, ...] = (
    "dataset_name",
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "pasdf_score",
    "template_score",
    "registration_confidence",
    "assignment_entropy",
    "residual_overlap",
    "top1_top2_margin",
    "calibrated_score",
    "method",
    "split_tag",
    "note",
)

BOUNDARY_MARGIN_FIELDS: tuple[str, ...] = (
    "class_name",
    "score_field",
    "sample_count",
    "positive_count",
    "anomaly_count",
    "max_positive_score",
    "max_positive_sample_id",
    "min_anomaly_score",
    "min_anomaly_sample_id",
    "margin",
    "strict_pass",
)

CALIBRATION_SUMMARY_FIELDS: tuple[str, ...] = (
    "method",
    "split_tag",
    "class_name",
    "score_field",
    "sample_count",
    "positive_count",
    "anomaly_count",
    "object_auroc",
    "object_aupr",
    "max_positive_score",
    "min_anomaly_score",
    "boundary_margin",
    "strict_pass",
    "false_positive_top1_sample_id",
    "false_positive_top1_score",
)


def load_calibration_records(
    path: str | Path, *, dataset_name: str
) -> tuple[CalibrationRecord, ...]:
    """Load P7-A per-sample CSV records into calibration records."""

    csv_path = Path(path)
    rows: list[CalibrationRecord] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                CalibrationRecord(
                    dataset_name=dataset_name,
                    class_name=_require_str(row, "class_name"),
                    sample_id=_require_str(row, "sample_id"),
                    label=_require_int(row, "label"),
                    point_count=_require_int(row, "point_count"),
                    gt_point_count=_require_int(row, "gt_point_count"),
                    pasdf_score=_require_float(row, "pasdf_object_score"),
                    template_score=_require_float(row, "nn_topk_mean"),
                    registration_confidence=_require_float(row, "registration_confidence"),
                    assignment_entropy=_require_float(row, "assignment_entropy"),
                    residual_overlap=_require_float(row, "residual_overlap"),
                    top1_top2_margin=_require_float(row, "top1_top2_margin"),
                    calibrated_score=_require_float(row, "pasdf_object_score"),
                    method="pasdf_raw",
                    split_tag="input",
                    note="",
                )
            )
    if not rows:
        raise ValueError(f"no calibration records found in {csv_path}")
    return tuple(rows)


def boundary_margin(
    records: Sequence[CalibrationRecord],
    score_field: str,
    *,
    class_name: str | None = None,
) -> BoundaryMargin:
    """Return min anomaly score minus max positive score for one record group."""

    group = _filter_records(records, class_name=class_name)
    if not group:
        raise ValueError("records must contain at least one item")
    positives = tuple(record for record in group if record.label == 0)
    anomalies = tuple(record for record in group if record.label == 1)
    max_positive = _max_record(positives, score_field)
    min_anomaly = _min_record(anomalies, score_field)
    max_positive_score = None if max_positive is None else _score(max_positive, score_field)
    min_anomaly_score = None if min_anomaly is None else _score(min_anomaly, score_field)
    margin = (
        None
        if max_positive_score is None or min_anomaly_score is None
        else min_anomaly_score - max_positive_score
    )
    resolved_class = class_name or (group[0].class_name if _single_class(group) else "overall")
    return BoundaryMargin(
        class_name=resolved_class,
        score_field=score_field,
        sample_count=len(group),
        positive_count=len(positives),
        anomaly_count=len(anomalies),
        max_positive_score=_round_optional(max_positive_score),
        max_positive_sample_id=None if max_positive is None else max_positive.sample_id,
        min_anomaly_score=_round_optional(min_anomaly_score),
        min_anomaly_sample_id=None if min_anomaly is None else min_anomaly.sample_id,
        margin=_round_optional(margin),
        strict_pass=bool(margin is not None and margin > 0.0),
    )


def build_feature_matrix(
    records: Sequence[CalibrationRecord],
    feature_names: Sequence[str],
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.int64]]]:
    """Build a feature matrix and label vector from selected record fields."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("records must contain at least one item")
    if not feature_names:
        raise ValueError("feature_names must contain at least one item")
    matrix = np.asarray(
        [
            [_feature_value(record, feature_name) for feature_name in feature_names]
            for record in record_tuple
        ],
        dtype=np.float64,
    )
    labels = np.asarray([record.label for record in record_tuple], dtype=np.int64)
    if not np.all(np.isfinite(matrix)):
        raise ValueError("feature matrix contains non-finite values")
    return matrix, labels


def confidence_gated_score(*, pasdf_score: float, registration_confidence: float) -> float:
    """Scale PASDF score by registration confidence."""

    _require_unit_interval_value("registration_confidence", registration_confidence)
    if pasdf_score < 0.0:
        raise ValueError("pasdf_score must be non-negative")
    return _round(pasdf_score * registration_confidence)


def calibrate_scores(
    records: Sequence[CalibrationRecord],
    *,
    method: str,
    feature_names: Sequence[str],
    split_mode: str,
) -> tuple[CalibrationRecord, ...]:
    """Calibrate records with a simple method and split mode."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("records must contain at least one item")
    if method == "pasdf_raw":
        return tuple(
            _with_score(record, record.pasdf_score, method, split_mode) for record in record_tuple
        )
    if method == "template_residual":
        return tuple(
            _with_score(record, record.template_score, method, split_mode)
            for record in record_tuple
        )
    if method == "confidence_gate":
        return tuple(
            _with_score(
                record,
                confidence_gated_score(
                    pasdf_score=record.pasdf_score,
                    registration_confidence=record.registration_confidence,
                ),
                method,
                split_mode,
            )
            for record in record_tuple
        )
    if split_mode == "diagnostic_oracle":
        return _fit_predict(record_tuple, record_tuple, method, feature_names, split_tag=split_mode)
    if split_mode == "leave_one_class_out":
        calibrated: list[CalibrationRecord] = []
        for heldout_class in sorted({record.class_name for record in record_tuple}):
            train = tuple(record for record in record_tuple if record.class_name != heldout_class)
            test = tuple(record for record in record_tuple if record.class_name == heldout_class)
            calibrated.extend(
                _fit_predict(
                    train,
                    test,
                    method,
                    feature_names,
                    split_tag=f"leave_one_class_out:{heldout_class}",
                )
            )
        return tuple(calibrated)
    raise ValueError(f"unsupported split_mode: {split_mode}")


def summarize_calibration(
    records: Sequence[CalibrationRecord],
    score_fields: Sequence[str],
) -> tuple[CalibrationSummary, ...]:
    """Summarize score fields by class."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("records must contain at least one item")
    if not score_fields:
        raise ValueError("score_fields must contain at least one item")
    summaries: list[CalibrationSummary] = []
    keys = sorted({(record.method, record.split_tag, record.class_name) for record in record_tuple})
    for method, split_tag, class_name in keys:
        class_records = tuple(
            record
            for record in record_tuple
            if record.method == method
            and record.split_tag == split_tag
            and record.class_name == class_name
        )
        for score_field in score_fields:
            margin = boundary_margin(class_records, score_field, class_name=class_name)
            labels = np.asarray([record.label for record in class_records], dtype=np.int64)
            scores = np.asarray(
                [_score(record, score_field) for record in class_records], dtype=np.float64
            )
            top_positive = _max_record(
                tuple(record for record in class_records if record.label == 0),
                score_field,
            )
            summaries.append(
                CalibrationSummary(
                    method=method,
                    split_tag=split_tag,
                    class_name=class_name,
                    score_field=score_field,
                    sample_count=len(class_records),
                    positive_count=margin.positive_count,
                    anomaly_count=margin.anomaly_count,
                    object_auroc=_round_optional(_safe_auroc(labels, scores)),
                    object_aupr=_round_optional(_safe_aupr(labels, scores)),
                    max_positive_score=margin.max_positive_score,
                    min_anomaly_score=margin.min_anomaly_score,
                    boundary_margin=margin.margin,
                    strict_pass=margin.strict_pass,
                    false_positive_top1_sample_id=(
                        None if top_positive is None else top_positive.sample_id
                    ),
                    false_positive_top1_score=(
                        None if top_positive is None else _round(_score(top_positive, score_field))
                    ),
                )
            )
    return tuple(summaries)


def write_calibration_records_csv(
    records: Sequence[CalibrationRecord],
    path: str | Path,
) -> Path:
    """Write per-sample calibration records."""

    return _write_dataclass_csv(records, CALIBRATION_RECORD_FIELDS, path)


def write_boundary_margins_csv(
    margins: Sequence[BoundaryMargin],
    path: str | Path,
) -> Path:
    """Write boundary margin summaries."""

    return _write_dataclass_csv(margins, BOUNDARY_MARGIN_FIELDS, path)


def write_calibration_summaries_csv(
    summaries: Sequence[CalibrationSummary],
    path: str | Path,
) -> Path:
    """Write calibration metric summaries."""

    return _write_dataclass_csv(summaries, CALIBRATION_SUMMARY_FIELDS, path)


def _fit_predict(
    train_records: Sequence[CalibrationRecord],
    test_records: Sequence[CalibrationRecord],
    method: str,
    feature_names: Sequence[str],
    *,
    split_tag: str,
) -> tuple[CalibrationRecord, ...]:
    if not train_records or not test_records:
        raise ValueError("train and test records must be non-empty")
    train_features, train_labels = build_feature_matrix(train_records, feature_names)
    test_features, _ = build_feature_matrix(test_records, feature_names)
    if len(set(int(label) for label in train_labels)) < 2:
        raise ValueError("training records must contain both labels")
    if method == "logistic_l2":
        model = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=0)
        model.fit(train_features, train_labels)
        scores = model.predict_proba(test_features)[:, 1]
    elif method in {"isotonic_pasdf", "isotonic_gated"}:
        if len(feature_names) != 1:
            raise ValueError(f"{method} requires exactly one feature")
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(train_features[:, 0], train_labels)
        scores = model.predict(test_features[:, 0])
    else:
        raise ValueError(f"unsupported calibration method: {method}")
    return tuple(
        _with_score(record, float(score), method, split_tag)
        for record, score in zip(test_records, scores, strict=True)
    )


def _with_score(
    record: CalibrationRecord,
    score: float,
    method: str,
    split_tag: str,
) -> CalibrationRecord:
    return replace(
        record,
        calibrated_score=_round(float(score)),
        method=method,
        split_tag=split_tag,
    )


def _filter_records(
    records: Sequence[CalibrationRecord],
    *,
    class_name: str | None,
) -> tuple[CalibrationRecord, ...]:
    return tuple(
        record for record in records if class_name is None or record.class_name == class_name
    )


def _single_class(records: Sequence[CalibrationRecord]) -> bool:
    return len({record.class_name for record in records}) == 1


def _max_record(records: Sequence[CalibrationRecord], score_field: str) -> CalibrationRecord | None:
    if not records:
        return None
    return max(records, key=lambda record: (_score(record, score_field), record.sample_id))


def _min_record(records: Sequence[CalibrationRecord], score_field: str) -> CalibrationRecord | None:
    if not records:
        return None
    return min(records, key=lambda record: (_score(record, score_field), record.sample_id))


def _score(record: CalibrationRecord, score_field: str) -> float:
    value = getattr(record, _field_name(score_field))
    return float(value)


def _feature_value(record: CalibrationRecord, feature_name: str) -> float:
    if feature_name == "gated_pasdf_score":
        return confidence_gated_score(
            pasdf_score=record.pasdf_score,
            registration_confidence=record.registration_confidence,
        )
    if feature_name == "low_confidence_score":
        return record.pasdf_score * (1.0 - record.registration_confidence)
    name = _field_name(feature_name)
    value = getattr(record, name)
    return float(value)


def _field_name(name: str) -> str:
    return FEATURE_ALIASES.get(name, name)


def _require_str(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"missing required field: {key}")
    return value


def _require_int(row: dict[str, str], key: str) -> int:
    return int(_require_str(row, key))


def _require_float(row: dict[str, str], key: str) -> float:
    return float(_require_str(row, key))


def _require_unit_interval_value(name: str, value: float) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def _safe_auroc(
    labels: np.ndarray[Any, np.dtype[np.int64]],
    scores: np.ndarray[Any, np.dtype[np.float64]],
) -> float | None:
    if len(set(int(label) for label in labels)) < 2:
        return None
    return float(roc_auc_score(labels, scores))


def _safe_aupr(
    labels: np.ndarray[Any, np.dtype[np.int64]],
    scores: np.ndarray[Any, np.dtype[np.float64]],
) -> float | None:
    if len(set(int(label) for label in labels)) < 2:
        return None
    return float(average_precision_score(labels, scores))


def _round(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round(value)


def _write_dataclass_csv(
    records: Sequence[Any],
    fieldnames: Sequence[str],
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            writer.writerow({field: row.get(field) for field in fieldnames})
    return output_path
