"""Lightweight point-cloud smoke visualizations."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.data.preprocess import deterministic_sample_indices


def _project_xy(
    points: np.ndarray[Any, np.dtype[np.float32]], size: int, margin: int
) -> np.ndarray[Any, np.dtype[np.float64]]:
    xy = points[:, :2].astype(np.float64)
    if xy.shape[0] == 0:
        return np.empty((0, 2), dtype=np.float64)
    min_xy = xy.min(axis=0)
    max_xy = xy.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-9)
    normalized = (xy - min_xy) / span
    scale = size - 2 * margin
    projected = normalized * scale + margin
    projected[:, 1] = size - projected[:, 1]
    return np.asarray(projected, dtype=np.float64)


def _sample_for_svg(
    points: np.ndarray[Any, np.dtype[np.float32]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    normals: np.ndarray[Any, np.dtype[np.float32]] | None,
    *,
    max_points: int,
    seed: int,
) -> tuple[
    np.ndarray[Any, np.dtype[np.float32]],
    np.ndarray[Any, np.dtype[np.int64]],
    np.ndarray[Any, np.dtype[np.float32]] | None,
]:
    if labels.shape[0] != points.shape[0]:
        raise ValueError(
            f"Label count {labels.shape[0]} does not match point count {points.shape[0]}"
        )
    if normals is not None and normals.shape != points.shape:
        raise ValueError(
            f"Normals shape {normals.shape} does not match points shape {points.shape}"
        )
    if max_points > 0 and points.shape[0] > max_points:
        indices = deterministic_sample_indices(
            points.shape[0],
            max_points,
            seed=seed,
            key="svg",
        )
        points = points[indices]
        labels = labels[indices]
        normals = normals[indices] if normals is not None else None
    return points, labels, normals


def write_pointcloud_gt_svg(
    path: str | Path,
    points: np.ndarray[Any, np.dtype[np.float32]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    *,
    normals: np.ndarray[Any, np.dtype[np.float32]] | None = None,
    title: str = "Point cloud GT smoke",
    max_points: int = 4096,
    max_normals: int = 128,
    seed: int = 42,
    size: int = 900,
) -> None:
    """Write a deterministic SVG overlay of point labels and optional normals."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    points_array = np.asarray(points, dtype=np.float32)
    labels_array = np.asarray(labels, dtype=np.int64)
    normals_array = None if normals is None else np.asarray(normals, dtype=np.float32)
    view_points, view_labels, view_normals = _sample_for_svg(
        points_array,
        labels_array,
        normals_array,
        max_points=max_points,
        seed=seed,
    )
    projected = _project_xy(view_points, size=size, margin=48)
    anomaly_count = int(view_labels.sum())
    title_text = html.escape(title)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">',
        "<style>",
        ".bg { fill: #f7f7f4; }",
        ".axis { stroke: #d4d4ce; stroke-width: 1; }",
        ".point { opacity: 0.72; }",
        ".normal { stroke: #1f2937; stroke-width: 1.1; opacity: 0.65; }",
        ".normal-point { fill: #1f2937; opacity: 0.8; }",
        ".normal-label { fill: #374151; font: 12px sans-serif; }",
        ".normal-sample { fill: #2563eb; }",
        ".point.normal { fill: #2563eb; }",
        ".point.anomaly { fill: #dc2626; }",
        ".title { fill: #111827; font: 18px sans-serif; font-weight: 700; }",
        ".meta { fill: #374151; font: 13px sans-serif; }",
        "</style>",
        '<rect class="bg" x="0" y="0" width="100%" height="100%"/>',
        f'<text class="title" x="32" y="34">{title_text}</text>',
        f'<text class="meta" x="32" y="56">points={view_points.shape[0]} '
        f"anomaly_points={anomaly_count}</text>",
        f'<line class="axis" x1="48" y1="{size - 48}" x2="{size - 48}" y2="{size - 48}"/>',
        f'<line class="axis" x1="48" y1="48" x2="48" y2="{size - 48}"/>',
    ]

    for row_index, label in enumerate(view_labels):
        x = float(projected[row_index, 0])
        y = float(projected[row_index, 1])
        cls = "anomaly" if int(label) > 0 else "normal"
        radius = 2.4 if cls == "anomaly" else 1.6
        lines.append(f'<circle class="point {cls}" cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}"/>')

    if view_normals is not None and view_normals.shape[0] > 0 and max_normals > 0:
        normal_indices = deterministic_sample_indices(
            view_normals.shape[0],
            min(max_normals, view_normals.shape[0]),
            seed=seed,
            key="svg-normals",
        )
        normal_vectors = view_normals[normal_indices, :2].astype(np.float64)
        normal_lengths = np.linalg.norm(normal_vectors, axis=1)
        nonzero = normal_lengths > 1e-9
        for idx, vector, length in zip(
            normal_indices[nonzero],
            normal_vectors[nonzero],
            normal_lengths[nonzero],
            strict=True,
        ):
            x = float(projected[int(idx), 0])
            y = float(projected[int(idx), 1])
            direction = vector / length
            end_x = x + direction[0] * 16.0
            end_y = y - direction[1] * 16.0
            lines.append(
                f'<line class="normal" x1="{x:.2f}" y1="{y:.2f}" '
                f'x2="{end_x:.2f}" y2="{end_y:.2f}"/>'
            )
            lines.append(f'<circle class="normal-point" cx="{x:.2f}" cy="{y:.2f}" r="1.4"/>')
        lines.append(
            '<text class="normal-label" x="32" y="80">'
            "normal lines: sampled PCA/Open3D smoke check</text>"
        )

    lines.append("</svg>")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pointcloud_score_svg(
    path: str | Path,
    points: np.ndarray[Any, np.dtype[np.float32]],
    scores: np.ndarray[Any, np.dtype[np.float64]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    *,
    title: str,
    max_points: int = 4096,
    seed: int = 42,
    size: int = 900,
) -> None:
    """Write a deterministic SVG heatmap from point anomaly scores and GT labels."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    points_array = np.asarray(points, dtype=np.float32)
    scores_array = np.asarray(scores, dtype=np.float64).reshape(-1)
    labels_array = np.asarray(labels, dtype=np.int64).reshape(-1)
    if scores_array.shape[0] != points_array.shape[0]:
        message = (
            f"Score count {scores_array.shape[0]} does not match "
            f"point count {points_array.shape[0]}"
        )
        raise ValueError(message)
    if labels_array.shape[0] != points_array.shape[0]:
        message = (
            f"Label count {labels_array.shape[0]} does not match "
            f"point count {points_array.shape[0]}"
        )
        raise ValueError(message)
    if points_array.shape[0] == 0:
        raise ValueError("At least one point is required")
    if not np.all(np.isfinite(scores_array)):
        raise ValueError("Scores must contain only finite values")

    view_points = points_array
    view_scores = scores_array
    view_labels = labels_array
    if max_points > 0 and points_array.shape[0] > max_points:
        indices = deterministic_sample_indices(
            points_array.shape[0],
            max_points,
            seed=seed,
            key="score-svg",
        )
        view_points = points_array[indices]
        view_scores = scores_array[indices]
        view_labels = labels_array[indices]

    projected = _project_xy(view_points, size=size, margin=48)
    title_text = html.escape(title)
    score_min = float(np.min(view_scores))
    score_mean = float(np.mean(view_scores))
    score_p95 = float(np.percentile(view_scores, 95))
    score_max = float(np.max(view_scores))
    anomaly_count = int(np.count_nonzero(view_labels))

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">',
        "<style>",
        ".bg { fill: #f7f7f4; }",
        ".axis { stroke: #d4d4ce; stroke-width: 1; }",
        ".point { opacity: 0.78; }",
        ".score-point { stroke-width: 0.35; stroke: #243142; }",
        ".score-point.gt { stroke-width: 1.35; stroke: #111827; }",
        ".title { fill: #111827; font: 18px sans-serif; font-weight: 700; }",
        ".meta { fill: #374151; font: 13px sans-serif; }",
        "</style>",
        '<rect class="bg" x="0" y="0" width="100%" height="100%"/>',
        f'<text class="title" x="32" y="34">{title_text}</text>',
        f'<text class="meta" x="32" y="56">points={view_points.shape[0]} '
        f"gt_points={anomaly_count} score_min={score_min:.6f} "
        f"score_mean={score_mean:.6f} score_p95={score_p95:.6f} "
        f"score_max={score_max:.6f}</text>",
        f'<line class="axis" x1="48" y1="{size - 48}" x2="{size - 48}" y2="{size - 48}"/>',
        f'<line class="axis" x1="48" y1="48" x2="48" y2="{size - 48}"/>',
    ]

    score_colors = _score_colors(view_scores)
    for row_index, label in enumerate(view_labels):
        x = float(projected[row_index, 0])
        y = float(projected[row_index, 1])
        gt_class = "gt" if int(label) > 0 else "normal"
        radius = 2.6 if gt_class == "gt" else 1.8
        lines.append(
            f'<circle class="point score-point {gt_class}" cx="{x:.2f}" cy="{y:.2f}" '
            f'r="{radius:.2f}" fill="{score_colors[row_index]}"/>'
        )

    lines.append("</svg>")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _score_colors(scores: np.ndarray[Any, np.dtype[np.float64]]) -> list[str]:
    score_min = float(np.min(scores))
    score_max = float(np.max(scores))
    span = max(score_max - score_min, 1e-12)
    normalized = (scores - score_min) / span
    colors: list[str] = []
    for value in normalized:
        red = int(round(37 + float(value) * 203))
        green = int(round(99 - float(value) * 51))
        blue = int(round(235 - float(value) * 187))
        colors.append(f"#{red:02x}{green:02x}{blue:02x}")
    return colors


def write_pointcloud_template_overlay_svg(
    path: str | Path,
    sample_points: np.ndarray[Any, np.dtype[np.float32]],
    template_points: np.ndarray[Any, np.dtype[np.float32]],
    *,
    title: str,
    max_points: int = 4096,
    seed: int = 42,
    size: int = 900,
) -> None:
    """Write a deterministic sample/template registration overlay SVG."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample_array = _as_point_array(sample_points, name="sample_points")
    template_array = _as_point_array(template_points, name="template_points")
    sample_view = _sample_points(sample_array, max_points=max_points, seed=seed, key="sample")
    template_view = _sample_points(
        template_array,
        max_points=max_points,
        seed=seed,
        key="template",
    )
    combined = np.vstack([sample_view, template_view])
    projected = _project_xy(combined, size=size, margin=48)
    sample_projected = projected[: sample_view.shape[0]]
    template_projected = projected[sample_view.shape[0] :]

    title_text = html.escape(title)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">',
        "<style>",
        ".bg { fill: #f7f7f4; }",
        ".axis { stroke: #d4d4ce; stroke-width: 1; }",
        ".point { opacity: 0.72; }",
        ".sample { fill: #dc2626; stroke: #7f1d1d; stroke-width: 0.4; }",
        ".template { fill: #2563eb; stroke: #1e3a8a; stroke-width: 0.4; }",
        ".title { fill: #111827; font: 18px sans-serif; font-weight: 700; }",
        ".meta { fill: #374151; font: 13px sans-serif; }",
        "</style>",
        '<rect class="bg" x="0" y="0" width="100%" height="100%"/>',
        f'<text class="title" x="32" y="34">{title_text}</text>',
        f'<text class="meta" x="32" y="56">sample_points={sample_view.shape[0]} '
        f"template_points={template_view.shape[0]}</text>",
        '<text class="meta" x="32" y="78">sample=red template=blue</text>',
        f'<line class="axis" x1="48" y1="{size - 48}" x2="{size - 48}" y2="{size - 48}"/>',
        f'<line class="axis" x1="48" y1="48" x2="48" y2="{size - 48}"/>',
    ]
    for x, y in template_projected:
        lines.append(
            f'<circle class="point template" cx="{float(x):.2f}" cy="{float(y):.2f}" r="1.8"/>'
        )
    for x, y in sample_projected:
        lines.append(
            f'<circle class="point sample" cx="{float(x):.2f}" cy="{float(y):.2f}" r="1.8"/>'
        )
    lines.append("</svg>")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pointcloud_score_comparison_svg(
    path: str | Path,
    points: np.ndarray[Any, np.dtype[np.float32]],
    left_scores: np.ndarray[Any, np.dtype[np.float64]],
    right_scores: np.ndarray[Any, np.dtype[np.float64]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    *,
    title: str,
    left_label: str,
    right_label: str,
    max_points: int = 4096,
    seed: int = 42,
    size: int = 900,
) -> None:
    """Write side-by-side score heatmaps for the same point cloud."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    points_array = _as_point_array(points, name="points")
    left_array = np.asarray(left_scores, dtype=np.float64).reshape(-1)
    right_array = np.asarray(right_scores, dtype=np.float64).reshape(-1)
    labels_array = np.asarray(labels, dtype=np.int64).reshape(-1)
    _validate_score_lengths(points_array, left_array, labels_array, score_name="left_scores")
    _validate_score_lengths(points_array, right_array, labels_array, score_name="right_scores")
    if max_points > 0 and points_array.shape[0] > max_points:
        indices = deterministic_sample_indices(
            points_array.shape[0],
            max_points,
            seed=seed,
            key="score-comparison",
        )
        points_array = points_array[indices]
        left_array = left_array[indices]
        right_array = right_array[indices]
        labels_array = labels_array[indices]

    left_projected = _project_panel_xy(points_array, size=size, margin=48, panel="left")
    right_projected = _project_panel_xy(points_array, size=size, margin=48, panel="right")
    left_colors = _score_colors(left_array)
    right_colors = _score_colors(right_array)
    title_text = html.escape(title)
    left_text = html.escape(left_label)
    right_text = html.escape(right_label)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">',
        "<style>",
        ".bg { fill: #f7f7f4; }",
        ".divider { stroke: #d4d4ce; stroke-width: 1; }",
        ".point { opacity: 0.78; }",
        ".score-point { stroke-width: 0.35; stroke: #243142; }",
        ".score-point.gt { stroke-width: 1.35; stroke: #111827; }",
        ".title { fill: #111827; font: 18px sans-serif; font-weight: 700; }",
        ".meta { fill: #374151; font: 13px sans-serif; }",
        ".panel-title { fill: #111827; font: 15px sans-serif; font-weight: 700; }",
        "</style>",
        '<rect class="bg" x="0" y="0" width="100%" height="100%"/>',
        f'<text class="title" x="32" y="34">{title_text}</text>',
        f'<text class="meta" x="32" y="56">points={points_array.shape[0]} '
        f"gt_points={int(np.count_nonzero(labels_array))} "
        f"left_score_mean={float(np.mean(left_array)):.6f} "
        f"right_score_mean={float(np.mean(right_array)):.6f}</text>",
        f'<text class="panel-title" x="32" y="84">{left_text}</text>',
        f'<text class="panel-title" x="{size // 2 + 24}" y="84">{right_text}</text>',
        f'<line class="divider" x1="{size // 2}" y1="96" x2="{size // 2}" y2="{size - 48}"/>',
    ]
    _append_score_points(lines, left_projected, labels_array, left_colors)
    _append_score_points(lines, right_projected, labels_array, right_colors)
    lines.append("</svg>")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _as_point_array(
    points: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    name: str,
) -> np.ndarray[Any, np.dtype[np.float32]]:
    array = np.asarray(points, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3): {array.shape}")
    if array.shape[0] == 0:
        raise ValueError(f"{name} must contain at least one point")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _sample_points(
    points: np.ndarray[Any, np.dtype[np.float32]],
    *,
    max_points: int,
    seed: int,
    key: str,
) -> np.ndarray[Any, np.dtype[np.float32]]:
    if max_points > 0 and points.shape[0] > max_points:
        indices = deterministic_sample_indices(points.shape[0], max_points, seed=seed, key=key)
        return np.asarray(points[indices], dtype=np.float32)
    return points


def _validate_score_lengths(
    points: np.ndarray[Any, np.dtype[np.float32]],
    scores: np.ndarray[Any, np.dtype[np.float64]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    *,
    score_name: str,
) -> None:
    if scores.shape[0] != points.shape[0]:
        raise ValueError(f"{score_name} length must match points")
    if labels.shape[0] != points.shape[0]:
        raise ValueError("labels length must match points")
    if not np.all(np.isfinite(scores)):
        raise ValueError(f"{score_name} must contain only finite values")


def _project_panel_xy(
    points: np.ndarray[Any, np.dtype[np.float32]],
    *,
    size: int,
    margin: int,
    panel: str,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    projected = _project_xy(points, size=size, margin=margin)
    panel_width = (size - 3 * margin) / 2.0
    projected[:, 0] = margin + (projected[:, 0] - margin) / (size - 2 * margin) * panel_width
    if panel == "right":
        projected[:, 0] += panel_width + margin
    return projected


def _append_score_points(
    lines: list[str],
    projected: np.ndarray[Any, np.dtype[np.float64]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    colors: list[str],
) -> None:
    for row_index, label in enumerate(labels):
        x = float(projected[row_index, 0])
        y = float(projected[row_index, 1])
        gt_class = "gt" if int(label) > 0 else "normal"
        radius = 2.4 if gt_class == "gt" else 1.7
        lines.append(
            f'<circle class="point score-point {gt_class}" cx="{x:.2f}" cy="{y:.2f}" '
            f'r="{radius:.2f}" fill="{colors[row_index]}"/>'
        )
