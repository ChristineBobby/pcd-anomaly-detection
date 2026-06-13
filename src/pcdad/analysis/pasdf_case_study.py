"""Targeted PASDF point-score case study utilities."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.geometry.residuals import point_to_template_residuals
from pcdad.scoring.geometric import (
    GeometryScoreConfig,
    GeometryScoreResult,
    score_geometry_residuals,
)
from pcdad.viz.pointcloud import (
    write_pointcloud_score_comparison_svg,
    write_pointcloud_score_svg,
    write_pointcloud_template_overlay_svg,
)


@dataclass(frozen=True)
class PasdfCaseStudySpec:
    """Filesystem and sample selection for P5 PASDF case studies."""

    score_root: Path
    sample_ids: tuple[str, ...]
    output_dir: Path
    template_root: Path = Path("third_party/PASDF/data/ShapeNetAD")
    overlay_sample_ids: tuple[str, ...] = ()
    comparison_sample_ids: tuple[str, ...] = ()
    max_points: int = 4096
    seed: int = 42


@dataclass(frozen=True)
class PasdfCaseStudyRecord:
    """One targeted PASDF point-score visualization record."""

    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    object_score: float
    score_mean: float
    score_p95: float
    score_max: float
    gt_score_mean: float | None
    background_score_mean: float | None
    svg_path: str
    point_score_path: str
    template_overlay_path: str | None
    geometry_comparison_path: str | None
    geometry_object_score: float | None
    geometry_gt_score_mean: float | None
    geometry_background_score_mean: float | None


CASE_STUDY_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "object_score",
    "score_mean",
    "score_p95",
    "score_max",
    "gt_score_mean",
    "background_score_mean",
    "svg_path",
    "point_score_path",
    "template_overlay_path",
    "geometry_comparison_path",
    "geometry_object_score",
    "geometry_gt_score_mean",
    "geometry_background_score_mean",
)


def run_pasdf_case_study(spec: PasdfCaseStudySpec) -> tuple[PasdfCaseStudyRecord, ...]:
    """Write targeted PASDF case-study SVGs and return per-sample records."""

    records: list[PasdfCaseStudyRecord] = []
    overlay_samples = set(spec.overlay_sample_ids)
    comparison_samples = set(spec.comparison_sample_ids)
    template_cache: dict[str, np.ndarray[Any, np.dtype[np.float32]]] = {}
    for sample_id in spec.sample_ids:
        score_path = _find_sample_npz(spec.score_root, sample_id)
        payload = load_pasdf_point_score(score_path)
        class_name = score_path.parent.parent.name
        points = payload["points"].astype(np.float32)
        scores = payload["point_scores"].astype(np.float64)
        labels = payload["mask"].astype(np.int64)
        svg_path = spec.output_dir / "pasdf_scores" / class_name / f"{sample_id}_pasdf_score.svg"
        write_pointcloud_score_svg(
            svg_path,
            points,
            scores,
            labels,
            title=f"{class_name}/{sample_id}",
            max_points=spec.max_points,
            seed=spec.seed,
        )

        template_overlay_path: Path | None = None
        geometry_comparison_path: Path | None = None
        geometry_result: GeometryScoreResult | None = None
        if sample_id in overlay_samples or sample_id in comparison_samples:
            template_points = template_cache.setdefault(
                class_name,
                load_pasdf_template_points(spec.template_root, class_name),
            )
            if sample_id in overlay_samples:
                template_overlay_path = (
                    spec.output_dir
                    / "template_overlay"
                    / class_name
                    / f"{sample_id}_template_overlay.svg"
                )
                write_pointcloud_template_overlay_svg(
                    template_overlay_path,
                    points,
                    template_points,
                    title=f"{class_name}/{sample_id} template overlay",
                    max_points=spec.max_points,
                    seed=spec.seed,
                )
            if sample_id in comparison_samples:
                geometry_result = compute_distance_geometry_scores(points, template_points)
                geometry_comparison_path = (
                    spec.output_dir
                    / "pasdf_vs_geometry"
                    / class_name
                    / f"{sample_id}_pasdf_vs_geometry.svg"
                )
                write_pointcloud_score_comparison_svg(
                    geometry_comparison_path,
                    points,
                    scores,
                    geometry_result.point_scores,
                    labels,
                    title=f"{class_name}/{sample_id} PASDF vs geometry",
                    left_label="PASDF score",
                    right_label="Geometry distance score",
                    max_points=spec.max_points,
                    seed=spec.seed,
                )

        records.append(
            _record_from_payload(
                class_name,
                sample_id,
                score_path,
                svg_path,
                payload,
                template_overlay_path=template_overlay_path,
                geometry_comparison_path=geometry_comparison_path,
                geometry_result=geometry_result,
            )
        )
    return tuple(records)


def load_pasdf_point_score(path: str | Path) -> dict[str, np.ndarray[Any, np.dtype[Any]]]:
    """Load and validate one P5 PASDF point-score NPZ."""

    score_path = Path(path)
    with np.load(score_path, allow_pickle=False) as payload:
        required = {"points", "point_scores", "mask", "label", "object_score"}
        missing = required - set(payload.files)
        if missing:
            raise ValueError(f"PASDF point-score NPZ missing fields: {', '.join(sorted(missing))}")
        loaded = {key: np.asarray(payload[key]) for key in payload.files}

    points = np.asarray(loaded["points"], dtype=np.float32)
    scores = np.asarray(loaded["point_scores"], dtype=np.float64).reshape(-1)
    mask = np.asarray(loaded["mask"], dtype=np.int64).reshape(-1)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points must have shape (N, 3): {points.shape}")
    if scores.shape[0] != points.shape[0]:
        raise ValueError("point_scores length must match points")
    if mask.shape[0] != points.shape[0]:
        raise ValueError("mask length must match points")
    return {
        "points": points,
        "point_scores": scores,
        "mask": mask,
        "label": np.asarray(loaded["label"]),
        "object_score": np.asarray(loaded["object_score"]),
    }


def load_pasdf_template_points(
    template_root: str | Path,
    class_name: str,
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Load PASDF ShapeNetAD template OBJ vertices in PASDF canonical orientation."""

    path = Path(template_root) / class_name / f"{class_name}_template0.obj"
    if not path.exists():
        raise FileNotFoundError(f"PASDF template OBJ not found: {path}")
    vertices: list[tuple[float, float, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.startswith("v "):
                continue
            parts = raw_line.split()
            if len(parts) < 4:
                raise ValueError(f"Malformed OBJ vertex line in {path}: {raw_line.rstrip()}")
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
    if not vertices:
        raise ValueError(f"PASDF template OBJ contains no vertices: {path}")
    return _pasdf_shapenet_rotate(np.asarray(vertices, dtype=np.float32))


def compute_distance_geometry_scores(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    template_points: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> GeometryScoreResult:
    """Compute distance-only geometry scores against a PASDF template."""

    residuals = point_to_template_residuals(
        points,
        template_points,
        use_normals=False,
        use_curvature=False,
    )
    return score_geometry_residuals(
        residuals,
        GeometryScoreConfig(distance_weight=1.0, normal_weight=0.0, curvature_weight=0.0),
    )


def write_case_study_csv(records: Sequence[PasdfCaseStudyRecord], path: str | Path) -> Path:
    """Write P5 targeted case-study records to CSV."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_STUDY_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(_csv_row(record))
    return output


def render_case_study_markdown(
    records: Sequence[PasdfCaseStudyRecord],
    *,
    title: str = "P5 PASDF Targeted Case Study",
) -> str:
    """Render a Chinese Markdown summary for targeted PASDF score visualizations."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("At least one PASDF case-study record is required")
    lines = [
        f"# {title}",
        "",
        "## 记录范围",
        "",
        f"- 样本数：{len(record_tuple)}",
        f"- 类别数：{len({record.class_name for record in record_tuple})}",
        "",
        "## 样本明细",
        "",
        "| 类别 | 样本 | Label | PASDF Object | GT 点数 | GT 内均值 | 背景均值 | "
        "PASDF SVG | Overlay | PASDF-vs-geometry | Geometry Object |",
        "|---|---|---:|---:|---:|---:|---:|---|---|---|---:|",
    ]
    for record in record_tuple:
        lines.append(
            f"| {record.class_name} | `{record.sample_id}` | {record.label} | "
            f"{record.object_score:.6f} | {record.gt_point_count} | "
            f"{_fmt_optional(record.gt_score_mean)} | "
            f"{_fmt_optional(record.background_score_mean)} | `{record.svg_path}` | "
            f"{_fmt_path(record.template_overlay_path)} | "
            f"{_fmt_path(record.geometry_comparison_path)} | "
            f"{_fmt_optional(record.geometry_object_score)} |"
        )
    lines.extend(["", "## 初步解读", ""])
    lines.extend(_interpret_records(record_tuple))
    lines.append("")
    return "\n".join(lines)


def _find_sample_npz(score_root: Path, sample_id: str) -> Path:
    matches = sorted(score_root.glob(f"*/points/{sample_id}.npz"))
    if not matches:
        raise FileNotFoundError(f"Could not find PASDF point-score NPZ for sample: {sample_id}")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise ValueError(f"Multiple PASDF point-score NPZ files matched {sample_id}: {joined}")
    return matches[0]


def _record_from_payload(
    class_name: str,
    sample_id: str,
    score_path: Path,
    svg_path: Path,
    payload: dict[str, np.ndarray[Any, np.dtype[Any]]],
    *,
    template_overlay_path: Path | None = None,
    geometry_comparison_path: Path | None = None,
    geometry_result: GeometryScoreResult | None = None,
) -> PasdfCaseStudyRecord:
    scores = np.asarray(payload["point_scores"], dtype=np.float64).reshape(-1)
    mask = np.asarray(payload["mask"], dtype=np.int64).reshape(-1)
    gt_mask = mask.astype(bool)
    bg_mask = ~gt_mask
    gt_score_mean = float(np.mean(scores[gt_mask])) if np.any(gt_mask) else None
    background_score_mean = float(np.mean(scores[bg_mask])) if np.any(bg_mask) else None
    geometry_scores = None if geometry_result is None else geometry_result.point_scores
    geometry_gt_score_mean = (
        float(np.mean(geometry_scores[gt_mask]))
        if geometry_scores is not None and np.any(gt_mask)
        else None
    )
    geometry_background_score_mean = (
        float(np.mean(geometry_scores[bg_mask]))
        if geometry_scores is not None and np.any(bg_mask)
        else None
    )
    return PasdfCaseStudyRecord(
        class_name=class_name,
        sample_id=sample_id,
        label=int(np.asarray(payload["label"]).reshape(-1)[0]),
        point_count=int(scores.shape[0]),
        gt_point_count=int(np.count_nonzero(gt_mask)),
        object_score=_round(float(np.asarray(payload["object_score"]).reshape(-1)[0])),
        score_mean=_round(float(np.mean(scores))),
        score_p95=_round(float(np.percentile(scores, 95))),
        score_max=_round(float(np.max(scores))),
        gt_score_mean=_round_optional(gt_score_mean),
        background_score_mean=_round_optional(background_score_mean),
        svg_path=str(svg_path),
        point_score_path=str(score_path),
        template_overlay_path=None if template_overlay_path is None else str(template_overlay_path),
        geometry_comparison_path=(
            None if geometry_comparison_path is None else str(geometry_comparison_path)
        ),
        geometry_object_score=(
            None if geometry_result is None else _round(float(geometry_result.object_score))
        ),
        geometry_gt_score_mean=_round_optional(geometry_gt_score_mean),
        geometry_background_score_mean=_round_optional(geometry_background_score_mean),
    )


def _csv_row(record: PasdfCaseStudyRecord) -> dict[str, object]:
    row = asdict(record)
    return {field: ("" if row[field] is None else row[field]) for field in CASE_STUDY_FIELDS}


def _interpret_records(records: Sequence[PasdfCaseStudyRecord]) -> list[str]:
    lines: list[str] = []
    for record in records:
        if record.label == 0:
            lines.append(
                f"- `{record.sample_id}` 是 positive 样本，Object Score 为 "
                f"`{record.object_score:.6f}`；若 SVG 中高分区域集中，应优先检查配准或模板差异。"
            )
        elif (
            record.gt_score_mean is not None
            and record.background_score_mean is not None
            and record.gt_score_mean <= record.background_score_mean
        ):
            lines.append(
                f"- `{record.sample_id}` 的 GT 内均值 `{record.gt_score_mean:.6f}` "
                f"不高于背景 `{record.background_score_mean:.6f}`，属于点级定位失败优先样本。"
            )
        else:
            lines.append(
                f"- `{record.sample_id}` 的 GT 内均值为 "
                f"`{_fmt_optional(record.gt_score_mean)}`，背景均值为 "
                f"`{_fmt_optional(record.background_score_mean)}`。"
            )
        if record.template_overlay_path is not None:
            lines.append(
                f"  template overlay：`{record.template_overlay_path}`，用于人工确认 "
                "sample/template registration 是否存在系统偏差。"
            )
        if record.geometry_comparison_path is not None:
            lines.append(
                f"  PASDF-vs-geometry：`{record.geometry_comparison_path}`；"
                f"Geometry Object Score=`{_fmt_optional(record.geometry_object_score)}`，"
                f"GT 内 geometry 均值=`{_fmt_optional(record.geometry_gt_score_mean)}`，"
                f"背景 geometry 均值=`{_fmt_optional(record.geometry_background_score_mean)}`。"
            )
    return lines


def _pasdf_shapenet_rotate(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Apply PASDF's ShapeNetAD Euler rotation [pi/2, 0, -pi/2] without pybullet."""

    rot_m = np.asarray(
        [
            [0.0, 0.0, -1.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    rotated = np.einsum("ij,kj->ki", rot_m, np.asarray(points, dtype=np.float32))
    return np.asarray(rotated, dtype=np.float32)


def _round(value: float) -> float:
    return round(float(value), 6)


def _round_optional(value: float | None) -> float | None:
    return None if value is None else _round(value)


def _fmt_optional(value: float | None) -> str:
    return "NA" if value is None else f"{value:.6f}"


def _fmt_path(value: str | None) -> str:
    return "NA" if value is None else f"`{value}`"
