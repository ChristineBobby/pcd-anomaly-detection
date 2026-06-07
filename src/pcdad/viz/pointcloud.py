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
