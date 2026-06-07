from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.viz.pointcloud import write_pointcloud_gt_svg


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
