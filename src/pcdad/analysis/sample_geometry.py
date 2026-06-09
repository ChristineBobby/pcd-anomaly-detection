"""Sample-level geometry diagnostics for P4 smoke experiments."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.data.dataset import (
    SampleRecord,
    discover_samples,
    parse_anomaly_type,
    read_gt_labels,
    read_pcd_points,
)
from pcdad.geometry.residuals import point_to_template_residuals
from pcdad.scoring.geometric import GeometryScoreConfig, score_geometry_residuals
from pcdad.viz.pointcloud import write_pointcloud_gt_svg


@dataclass(frozen=True)
class GeometryAnalysisSpec:
    """Configuration for a single-class geometry smoke analysis."""

    dataset_root: Path
    class_name: str
    max_samples: int = 4
    k_normal: int = 32
    k_curvature: tuple[int, ...] = (16, 32, 64)
    topk_ratio: float = 0.05
    use_normals: bool = True
    use_curvature: bool = True


@dataclass(frozen=True)
class SampleGeometryRecord:
    """Geometry score summary for one test sample."""

    class_name: str
    sample_id: str
    anomaly_type: str
    is_anomaly: bool
    gt_anomaly_points: int
    point_count: int
    object_score: float
    max_point_score: float
    mean_nn_distance: float
    max_nn_distance: float
    gt_point_score_mean: float | None
    bg_point_score_mean: float | None
    pcd_path: Path
    gt_path: Path | None


@dataclass(frozen=True)
class ClassGeometrySummary:
    """Geometry smoke summary for one class."""

    class_name: str
    template_sample_id: str
    template_path: Path
    rows: tuple[SampleGeometryRecord, ...]

    @property
    def sample_count(self) -> int:
        return len(self.rows)

    @property
    def mean_anomaly_object_score(self) -> float:
        return _mean(row.object_score for row in self.rows if row.is_anomaly)

    @property
    def mean_positive_object_score(self) -> float:
        return _mean(row.object_score for row in self.rows if not row.is_anomaly)


def analyze_class_geometry_samples(spec: GeometryAnalysisSpec) -> ClassGeometrySummary:
    """Run lightweight geometry diagnostics for one class."""

    samples = _discover_geometry_samples(spec.dataset_root, spec.class_name)
    class_samples = [sample for sample in samples if sample.class_name == spec.class_name]
    if not class_samples:
        raise ValueError(f"No samples found for class {spec.class_name}: {spec.dataset_root}")

    template = _select_template(class_samples)
    template_points = read_pcd_points(template.pcd_path)
    test_samples = _select_test_samples(class_samples, max_samples=spec.max_samples)
    rows = tuple(_analyze_sample(sample, template_points, spec) for sample in test_samples)
    return ClassGeometrySummary(
        class_name=spec.class_name,
        template_sample_id=template.sample_id,
        template_path=template.pcd_path,
        rows=rows,
    )


def render_geometry_smoke_markdown(
    summaries: Iterable[ClassGeometrySummary],
    *,
    title: str = "P4 几何 Smoke 摘要",
) -> str:
    """Render a Chinese Markdown summary for geometry smoke records."""

    summary_tuple = tuple(summaries)
    lines = [
        f"# {title}",
        "",
        "## 类别摘要",
        "",
        "| 类别 | Template | 样本数 | Anomaly Object Score 均值 | Positive Object Score 均值 |",
        "|---|---|---:|---:|---:|",
    ]
    for summary in summary_tuple:
        lines.append(
            f"| {summary.class_name} | {summary.template_sample_id} | {summary.sample_count} | "
            f"{_format_float(summary.mean_anomaly_object_score)} | "
            f"{_format_float(summary.mean_positive_object_score)} |"
        )

    lines.extend(
        [
            "",
            "## 样本明细",
            "",
            "| 类别 | 样本 | 类型 | 是否异常 | GT 异常点 | Object Score | Max Point Score | "
            "Mean NN Distance | Max NN Distance | GT Score Mean | BG Score Mean |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in summary_tuple:
        for row in summary.rows:
            lines.append(
                f"| {row.class_name} | {row.sample_id} | {row.anomaly_type} | "
                f"{row.is_anomaly} | {row.gt_anomaly_points} | "
                f"{row.object_score:.6f} | {row.max_point_score:.6f} | "
                f"{row.mean_nn_distance:.6f} | {row.max_nn_distance:.6f} | "
                f"{_format_float(row.gt_point_score_mean)} | "
                f"{_format_float(row.bg_point_score_mean)} |"
            )
    lines.append("")
    return "\n".join(lines)


def sample_geometry_rows_to_dicts(
    summaries: Iterable[ClassGeometrySummary],
) -> list[dict[str, object]]:
    """Flatten summaries into CSV-friendly dictionaries."""

    rows: list[dict[str, object]] = []
    for summary in summaries:
        for row in summary.rows:
            rows.append(
                {
                    "class": row.class_name,
                    "template_sample_id": summary.template_sample_id,
                    "sample_id": row.sample_id,
                    "anomaly_type": row.anomaly_type,
                    "is_anomaly": row.is_anomaly,
                    "gt_anomaly_points": row.gt_anomaly_points,
                    "point_count": row.point_count,
                    "object_score": row.object_score,
                    "max_point_score": row.max_point_score,
                    "mean_nn_distance": row.mean_nn_distance,
                    "max_nn_distance": row.max_nn_distance,
                    "gt_point_score_mean": row.gt_point_score_mean,
                    "bg_point_score_mean": row.bg_point_score_mean,
                }
            )
    return rows


def write_geometry_smoke_svgs(
    summaries: Iterable[ClassGeometrySummary],
    output_dir: str | Path,
    *,
    max_points: int = 4096,
    seed: int = 42,
) -> tuple[Path, ...]:
    """Write deterministic GT SVG overlays for analyzed samples."""

    svg_dir = Path(output_dir)
    svg_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for summary in summaries:
        for row in summary.rows:
            points = read_pcd_points(row.pcd_path)
            labels = _labels_for_record(row, points.shape[0])
            output = svg_dir / f"{row.class_name}_{row.sample_id}.svg"
            write_pointcloud_gt_svg(
                output,
                points,
                labels,
                title=f"{row.class_name}/{row.sample_id}",
                max_points=max_points,
                seed=seed,
            )
            outputs.append(output)
    return tuple(outputs)


def _discover_geometry_samples(root: Path, class_name: str) -> list[SampleRecord]:
    fixed_class_dir = root / class_name
    if fixed_class_dir.is_dir():
        return _discover_fixed_class_samples(root, class_name)
    return discover_samples(root, collections=("16384",))


def _discover_fixed_class_samples(root: Path, class_name: str) -> list[SampleRecord]:
    class_dir = root / class_name
    samples: list[SampleRecord] = []
    for split in ("train", "test"):
        split_dir = class_dir / split
        if not split_dir.is_dir():
            continue
        for pcd_path in sorted(split_dir.glob("*.pcd")):
            sample_id = pcd_path.stem
            anomaly_type = parse_anomaly_type(sample_id, class_name)
            is_anomaly = split == "test" and anomaly_type not in {"positive", "template"}
            gt_path = class_dir / "GT" / f"{sample_id}.txt"
            samples.append(
                SampleRecord(
                    collection=root.name,
                    class_name=class_name,
                    split=split,
                    sample_id=sample_id,
                    pcd_path=pcd_path,
                    gt_path=gt_path if gt_path.is_file() else None,
                    anomaly_type=anomaly_type,
                    is_anomaly=is_anomaly,
                )
            )
    return samples


def _select_template(samples: list[SampleRecord]) -> SampleRecord:
    templates = sorted(
        (sample for sample in samples if sample.split == "train"),
        key=lambda sample: sample.sample_id,
    )
    if not templates:
        raise ValueError("At least one train template sample is required")
    return templates[0]


def _select_test_samples(
    samples: list[SampleRecord], *, max_samples: int
) -> tuple[SampleRecord, ...]:
    if max_samples <= 0:
        raise ValueError("max_samples must be positive")
    test_samples = [sample for sample in samples if sample.split == "test"]
    anomaly_samples = sorted(
        (sample for sample in test_samples if sample.is_anomaly), key=_sample_key
    )
    positive_samples = sorted(
        (sample for sample in test_samples if not sample.is_anomaly),
        key=_sample_key,
    )
    if max_samples == 1 or not positive_samples:
        return tuple(anomaly_samples[:max_samples] or positive_samples[:max_samples])
    anomaly_limit = max_samples - 1 if anomaly_samples else 0
    selected = [*anomaly_samples[:anomaly_limit], positive_samples[0]]
    if len(selected) < max_samples:
        selected.extend(anomaly_samples[anomaly_limit:max_samples])
    return tuple(selected[:max_samples])


def _sample_key(sample: SampleRecord) -> str:
    return sample.sample_id


def _analyze_sample(
    sample: SampleRecord,
    template_points: np.ndarray[Any, np.dtype[np.float32]],
    spec: GeometryAnalysisSpec,
) -> SampleGeometryRecord:
    points = read_pcd_points(sample.pcd_path)
    residuals = point_to_template_residuals(
        points,
        template_points,
        k_normal=spec.k_normal,
        k_curvature=spec.k_curvature,
        use_normals=spec.use_normals,
        use_curvature=spec.use_curvature,
    )
    score_result = score_geometry_residuals(
        residuals,
        GeometryScoreConfig(topk_ratio=spec.topk_ratio, smooth_k=0),
    )
    labels = _labels_for_sample(sample, points.shape[0])
    gt_scores = score_result.point_scores[labels > 0]
    bg_scores = score_result.point_scores[labels == 0]
    return SampleGeometryRecord(
        class_name=sample.class_name,
        sample_id=sample.sample_id,
        anomaly_type=sample.anomaly_type,
        is_anomaly=sample.is_anomaly,
        gt_anomaly_points=int(labels.sum()),
        point_count=int(points.shape[0]),
        object_score=score_result.object_score,
        max_point_score=float(np.max(score_result.point_scores)),
        mean_nn_distance=float(np.mean(residuals.nn_distance)),
        max_nn_distance=float(np.max(residuals.nn_distance)),
        gt_point_score_mean=_optional_mean(gt_scores),
        bg_point_score_mean=_optional_mean(bg_scores),
        pcd_path=sample.pcd_path,
        gt_path=sample.gt_path,
    )


def _labels_for_sample(
    sample: SampleRecord, point_count: int
) -> np.ndarray[Any, np.dtype[np.int64]]:
    if sample.gt_path is None:
        return np.zeros((point_count,), dtype=np.int64)
    labels = read_gt_labels(sample.gt_path)
    if labels.shape[0] != point_count:
        raise ValueError(
            f"Label count {labels.shape[0]} does not match point count {point_count} "
            f"for {sample.sample_id}"
        )
    return labels


def _labels_for_record(
    row: SampleGeometryRecord,
    point_count: int,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    if row.gt_path is None:
        return np.zeros((point_count,), dtype=np.int64)
    labels = read_gt_labels(row.gt_path)
    if labels.shape[0] != point_count:
        raise ValueError(
            f"Label count {labels.shape[0]} does not match point count {point_count} "
            f"for {row.sample_id}"
        )
    return labels


def _mean(values: Iterable[float]) -> float:
    values_tuple = tuple(values)
    if not values_tuple:
        return math.nan
    return float(math.fsum(values_tuple) / len(values_tuple))


def _optional_mean(values: np.ndarray[Any, np.dtype[np.float64]]) -> float | None:
    if values.shape[0] == 0:
        return None
    return float(np.mean(values))


def _format_float(value: float | None) -> str:
    if value is None:
        return "NA"
    if math.isnan(value):
        return "NA"
    return f"{value:.6f}"
