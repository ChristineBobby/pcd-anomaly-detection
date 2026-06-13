from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.viz.pointcloud import (
    write_pointcloud_gt_svg,
    write_pointcloud_score_comparison_svg,
    write_pointcloud_score_svg,
    write_pointcloud_template_overlay_svg,
)


def test_write_pointcloud_gt_svg_contains_points_labels_and_normals(tmp_path: Path) -> None:
    points = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float32,
    )
    labels = np.array([0, 1, 0, 1], dtype=np.int64)
    normals = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    output = tmp_path / "smoke.svg"

    write_pointcloud_gt_svg(
        output,
        points,
        labels,
        normals=normals,
        title="widget0_bulge0",
        max_points=4,
        max_normals=2,
        seed=3,
    )

    text = output.read_text(encoding="utf-8")
    assert text.startswith("<svg")
    assert "widget0_bulge0" in text
    assert 'class="point anomaly"' in text
    assert 'class="normal"' in text


def test_write_pointcloud_score_svg_contains_heatmap_and_gt_overlay(tmp_path: Path) -> None:
    points = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    scores = np.array([0.1, 0.7, 0.3, 0.9], dtype=np.float64)
    labels = np.array([0, 1, 0, 1], dtype=np.int64)
    output = tmp_path / "score.svg"

    write_pointcloud_score_svg(
        output,
        points,
        scores,
        labels,
        title="cap3_positive9",
        max_points=4,
        seed=3,
    )

    text = output.read_text(encoding="utf-8")
    assert text.startswith("<svg")
    assert "cap3_positive9" in text
    assert 'class="point score-point gt"' in text
    assert "score_mean=0.500000" in text
    assert "score_p95=0.870000" in text


def test_write_pointcloud_score_svg_rejects_shape_mismatch(tmp_path: Path) -> None:
    points = np.zeros((2, 3), dtype=np.float32)
    scores = np.array([0.1], dtype=np.float64)
    labels = np.array([0, 1], dtype=np.int64)

    try:
        write_pointcloud_score_svg(tmp_path / "bad.svg", points, scores, labels, title="bad")
    except ValueError as exc:
        assert "Score count" in str(exc)
    else:
        raise AssertionError("Expected ValueError for score/point length mismatch")


def test_write_pointcloud_template_overlay_svg_contains_sample_and_template_points(
    tmp_path: Path,
) -> None:
    sample_points = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        dtype=np.float32,
    )
    template_points = np.array(
        [[0.0, 1.0, 0.0], [1.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    output = tmp_path / "overlay.svg"

    write_pointcloud_template_overlay_svg(
        output,
        sample_points,
        template_points,
        title="cap3_positive9 overlay",
        max_points=4,
    )

    text = output.read_text(encoding="utf-8")
    assert "cap3_positive9 overlay" in text
    assert "sample_points=2" in text
    assert "template_points=2" in text
    assert 'class="point sample"' in text
    assert 'class="point template"' in text


def test_write_pointcloud_score_comparison_svg_contains_two_score_panels(
    tmp_path: Path,
) -> None:
    points = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    left_scores = np.array([0.1, 0.7, 0.2], dtype=np.float64)
    right_scores = np.array([0.5, 0.2, 0.9], dtype=np.float64)
    labels = np.array([0, 1, 1], dtype=np.int64)
    output = tmp_path / "comparison.svg"

    write_pointcloud_score_comparison_svg(
        output,
        points,
        left_scores,
        right_scores,
        labels,
        title="tap1_broken2 pasdf vs geometry",
        left_label="PASDF",
        right_label="Geometry",
        max_points=3,
    )

    text = output.read_text(encoding="utf-8")
    assert "tap1_broken2 pasdf vs geometry" in text
    assert "PASDF" in text
    assert "Geometry" in text
    assert "left_score_mean=0.333333" in text
    assert "right_score_mean=0.533333" in text
    assert 'class="point score-point gt"' in text
