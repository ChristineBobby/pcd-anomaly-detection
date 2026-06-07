from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pcdad.data.dataset import read_pcd_points
from pcdad.data.preprocess import (
    NormalizationMode,
    deterministic_sample_indices,
    labels_for_points,
    prepare_pasdf_dataset,
    sample_points_and_labels,
    unit_sphere_normalize,
    write_ascii_xyz_pcd,
    write_pasdf_gt_txt,
)


def _write_ascii_pcd(path: Path, points: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"{x} {y} {z}" for x, y, z in points)
    path.write_text(
        "\n".join(
            [
                "VERSION 0.7",
                "FIELDS x y z",
                "SIZE 4 4 4",
                "TYPE F F F",
                "COUNT 1 1 1",
                f"WIDTH {points.shape[0]}",
                "HEIGHT 1",
                f"POINTS {points.shape[0]}",
                "DATA ascii",
                rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_gt(path: Path, points: np.ndarray, labels: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            f"{point[0]},{point[1]},{point[2]},{label}.0\n"
            for point, label in zip(points, labels, strict=True)
        ),
        encoding="utf-8",
    )


def _make_tiny_dataset(root: Path) -> Path:
    dataset_root = root / "Anomaly-ShapeNet-v2"
    class_root = dataset_root / "dataset" / "pcd" / "widget0"
    _write_ascii_pcd(
        class_root / "train" / "widget0_template0.pcd",
        np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        ),
    )
    test_points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    _write_ascii_pcd(class_root / "test" / "widget0_bulge0.pcd", test_points)
    _write_gt(class_root / "GT" / "widget0_bulge0.txt", test_points, [0, 1, 0, 1])
    return dataset_root


def test_deterministic_sampling_is_stable_per_sample_key() -> None:
    first = deterministic_sample_indices(10, 4, seed=7, key="a")
    second = deterministic_sample_indices(10, 4, seed=7, key="a")
    other = deterministic_sample_indices(10, 4, seed=7, key="b")

    np.testing.assert_array_equal(first, second)
    assert first.shape == (4,)
    assert len(set(first.tolist())) == 4
    assert not np.array_equal(first, other)


def test_sample_points_and_labels_uses_same_indices() -> None:
    points = np.arange(30, dtype=np.float32).reshape(10, 3)
    labels = np.arange(10, dtype=np.int64)

    sampled_points, sampled_labels, indices = sample_points_and_labels(
        points,
        labels,
        target_num_points=5,
        seed=11,
        key="sample",
    )

    np.testing.assert_array_equal(sampled_points, points[indices])
    np.testing.assert_array_equal(sampled_labels, labels[indices])


def test_labels_for_points_reorders_gt_rows_by_coordinates() -> None:
    points = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    gt_values = np.array(
        [
            [0.0, 1.0, 0.0, 1.0],
            [9.0, 9.0, 9.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )

    labels = labels_for_points(points, gt_values)

    np.testing.assert_array_equal(labels, np.array([0, 1, 1], dtype=np.int64))


def test_labels_for_points_rejects_unmatched_gt_coordinates() -> None:
    points = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
    gt_values = np.array([[9.0, 9.0, 9.0, 1.0]], dtype=np.float32)

    with pytest.raises(ValueError, match="GT coordinates do not match"):
        labels_for_points(points, gt_values)


def test_unit_sphere_normalize_records_reversible_parameters() -> None:
    points = np.array(
        [[2.0, 0.0, 0.0], [4.0, 0.0, 0.0], [3.0, 3.0, 0.0]],
        dtype=np.float32,
    )

    normalized, params = unit_sphere_normalize(points)

    np.testing.assert_allclose(normalized.mean(axis=0), np.zeros(3), atol=1e-6)
    assert np.max(np.linalg.norm(normalized, axis=1)) == 1.0
    restored = normalized * params.scale + params.center
    np.testing.assert_allclose(restored, points, atol=1e-6)


def test_write_pasdf_pcd_and_gt_are_readable(tmp_path: Path) -> None:
    points = np.array([[0.0, 0.0, 0.0], [1.25, 2.5, 3.75]], dtype=np.float32)
    labels = np.array([0, 1], dtype=np.int64)
    pcd_path = tmp_path / "sample.pcd"
    gt_path = tmp_path / "sample.txt"

    write_ascii_xyz_pcd(pcd_path, points)
    write_pasdf_gt_txt(gt_path, points, labels)

    np.testing.assert_allclose(read_pcd_points(pcd_path), points)
    gt = np.loadtxt(gt_path, delimiter=" ")
    np.testing.assert_allclose(gt[:, :3], points)
    np.testing.assert_array_equal(gt[:, 3].astype(np.int64), labels)


def test_prepare_pasdf_dataset_writes_16384_layout_and_manifest(tmp_path: Path) -> None:
    dataset_root = _make_tiny_dataset(tmp_path)
    output_root = dataset_root / "dataset" / "16384"

    manifest = prepare_pasdf_dataset(
        dataset_root,
        output_root=output_root,
        target_num_points=3,
        seed=19,
        collections=("pcd",),
        class_names=("widget0",),
        normalize=NormalizationMode.NONE,
    )

    assert manifest.sample_count == 2
    prepared_pcd = output_root / "widget0" / "test" / "widget0_bulge0.pcd"
    prepared_gt = output_root / "widget0" / "GT" / "widget0_bulge0.txt"
    assert prepared_pcd.is_file()
    assert prepared_gt.is_file()
    assert (output_root / "preprocess_manifest.json").is_file()

    prepared_points = read_pcd_points(prepared_pcd)
    prepared_gt_values = np.loadtxt(prepared_gt, delimiter=" ")
    assert prepared_points.shape == (3, 3)
    np.testing.assert_allclose(prepared_gt_values[:, :3], prepared_points)
    assert set(prepared_gt_values[:, 3].astype(np.int64).tolist()) <= {0, 1}
