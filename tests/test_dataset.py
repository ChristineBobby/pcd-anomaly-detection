from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.data.dataset import (
    AnomalyShapeNetDataset,
    collect_dataset_statistics,
    discover_samples,
    read_gt_label_stats,
    read_pcd_metadata,
)


def _write_ascii_pcd(path: Path, points: list[tuple[float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"{x} {y} {z}" for x, y, z in points)
    path.write_text(
        "\n".join(
            [
                "# .PCD v0.7 - Point Cloud Data file format",
                "VERSION 0.7",
                "FIELDS x y z",
                "SIZE 4 4 4",
                "TYPE F F F",
                "COUNT 1 1 1",
                f"WIDTH {len(points)}",
                "HEIGHT 1",
                f"POINTS {len(points)}",
                "DATA ascii",
                rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_gt(path: Path, labels: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{idx}.0,{idx + 1}.0,{idx + 2}.0,{label}.0\n" for idx, label in enumerate(labels)),
        encoding="utf-8",
    )


def _make_tiny_anomaly_shapenet(root: Path) -> Path:
    dataset_root = root / "Anomaly-ShapeNet-v2"
    class_root = dataset_root / "dataset" / "pcd" / "widget0"
    _write_ascii_pcd(
        class_root / "train" / "widget0_template0.pcd",
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
    )
    _write_ascii_pcd(
        class_root / "test" / "widget0_positive0.pcd",
        [(0.0, 0.0, 1.0), (1.0, 1.0, 0.0)],
    )
    _write_ascii_pcd(
        class_root / "test" / "widget0_bulge0.pcd",
        [(2.0, 0.0, 0.0), (2.0, 1.0, 0.0)],
    )
    _write_gt(class_root / "GT" / "widget0_bulge0.txt", [0, 1])
    return dataset_root


def test_read_pcd_metadata_uses_header_point_count(tmp_path: Path) -> None:
    dataset_root = _make_tiny_anomaly_shapenet(tmp_path)
    metadata = read_pcd_metadata(
        dataset_root / "dataset" / "pcd" / "widget0" / "train" / "widget0_template0.pcd"
    )

    assert metadata.point_count == 3
    assert metadata.fields == ("x", "y", "z")
    assert metadata.data == "ascii"


def test_read_gt_label_stats_counts_positive_labels(tmp_path: Path) -> None:
    dataset_root = _make_tiny_anomaly_shapenet(tmp_path)

    label_stats = read_gt_label_stats(
        dataset_root / "dataset" / "pcd" / "widget0" / "GT" / "widget0_bulge0.txt"
    )

    assert label_stats.total_points == 2
    assert label_stats.anomaly_points == 1
    assert label_stats.anomaly_ratio == 0.5


def test_read_gt_label_stats_accepts_whitespace_delimited_gt(tmp_path: Path) -> None:
    gt_path = tmp_path / "sample.txt"
    gt_path.write_text(
        "\n".join(
            [
                "0.0 0.0 0.0 0",
                "1.0 0.0 0.0 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    label_stats = read_gt_label_stats(gt_path)

    assert label_stats.total_points == 2
    assert label_stats.anomaly_points == 1


def test_discover_samples_marks_train_positive_and_anomaly_samples(tmp_path: Path) -> None:
    dataset_root = _make_tiny_anomaly_shapenet(tmp_path)

    samples = discover_samples(dataset_root, collections=("pcd",))
    by_id = {sample.sample_id: sample for sample in samples}

    assert sorted(by_id) == ["widget0_bulge0", "widget0_positive0", "widget0_template0"]
    assert by_id["widget0_template0"].split == "train"
    assert by_id["widget0_template0"].is_anomaly is False
    assert by_id["widget0_positive0"].split == "test"
    assert by_id["widget0_positive0"].is_anomaly is False
    assert by_id["widget0_bulge0"].split == "test"
    assert by_id["widget0_bulge0"].is_anomaly is True
    assert by_id["widget0_bulge0"].anomaly_type == "bulge"
    assert by_id["widget0_bulge0"].gt_path is not None


def test_discover_samples_parses_digit_prefixed_class_names(tmp_path: Path) -> None:
    dataset_root = tmp_path / "Anomaly-ShapeNet-v2"
    class_root = dataset_root / "dataset" / "pcd" / "desk0"
    _write_ascii_pcd(class_root / "test" / "desk0_bulge0.pcd", [(0.0, 0.0, 0.0)])
    _write_gt(class_root / "GT" / "desk0_bulge0.txt", [1])

    [sample] = discover_samples(dataset_root, collections=("pcd",))

    assert sample.sample_id == "desk0_bulge0"
    assert sample.anomaly_type == "bulge"


def test_discover_samples_parses_base_class_prefix_when_instance_digit_is_missing(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "Anomaly-ShapeNet-v2"
    class_root = dataset_root / "dataset" / "pcd" / "desk0"
    _write_ascii_pcd(class_root / "test" / "desk_bulge0.pcd", [(0.0, 0.0, 0.0)])
    _write_gt(class_root / "GT" / "desk_bulge0.txt", [1])

    [sample] = discover_samples(dataset_root, collections=("pcd",))

    assert sample.sample_id == "desk_bulge0"
    assert sample.anomaly_type == "bulge"


def test_dataset_returns_points_normals_labels_and_meta(tmp_path: Path) -> None:
    dataset_root = _make_tiny_anomaly_shapenet(tmp_path)
    dataset = AnomalyShapeNetDataset(dataset_root, split="test", collections=("pcd",))

    assert len(dataset) == 2
    sample = next(
        dataset[idx]
        for idx in range(len(dataset))
        if dataset[idx][3]["sample_id"] == "widget0_bulge0"
    )
    points, normals, labels, meta = sample

    np.testing.assert_allclose(
        points, np.array([[2.0, 0.0, 0.0], [2.0, 1.0, 0.0]], dtype=np.float32)
    )
    assert normals.shape == points.shape
    assert normals.dtype == np.float32
    np.testing.assert_array_equal(labels, np.array([0, 1], dtype=np.int64))
    assert meta["collection"] == "pcd"
    assert meta["class_name"] == "widget0"
    assert meta["anomaly_type"] == "bulge"
    assert meta["is_anomaly"] is True


def test_collect_dataset_statistics_summarizes_counts_and_anomaly_ratio(tmp_path: Path) -> None:
    dataset_root = _make_tiny_anomaly_shapenet(tmp_path)

    stats = collect_dataset_statistics(dataset_root, collections=("pcd",))

    assert stats.sample_count == 3
    assert stats.class_count == 1
    assert stats.split_counts == {"test": 2, "train": 1}
    assert stats.anomaly_type_counts == {"bulge": 1, "positive": 1, "template": 1}
    assert stats.point_counts.count == 3
    assert stats.point_counts.min == 2
    assert stats.point_counts.max == 3
    assert stats.gt_file_count == 1
    assert stats.aggregate_labeled_points == 2
    assert stats.aggregate_anomaly_points == 1
    assert stats.aggregate_anomaly_ratio == 0.5
