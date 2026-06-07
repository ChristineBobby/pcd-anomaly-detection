"""Anomaly-ShapeNet dataset discovery, IO, and statistics."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_COLLECTIONS = ("pcd",)
ALL_PCD_COLLECTIONS = ("pcd", "new_pcd")
NORMAL_TYPES = {"positive", "template"}
ANOMALY_TYPE_ALIASES = {"crak": "crack"}
DatasetItem = tuple[
    np.ndarray[Any, np.dtype[np.float32]],
    np.ndarray[Any, np.dtype[np.float32]],
    np.ndarray[Any, np.dtype[np.int64]],
    dict[str, Any],
]


@dataclass(frozen=True)
class PcdMetadata:
    """PCD header metadata needed for fast stats and binary parsing."""

    path: Path
    point_count: int
    fields: tuple[str, ...]
    sizes: tuple[int, ...]
    types: tuple[str, ...]
    counts: tuple[int, ...]
    width: int | None
    height: int | None
    data: str
    header_bytes: int
    header_lines: int


@dataclass(frozen=True)
class GTLabelStats:
    """Summary of a point-level label file."""

    total_points: int
    anomaly_points: int

    @property
    def anomaly_ratio(self) -> float:
        if self.total_points == 0:
            return 0.0
        return self.anomaly_points / self.total_points


@dataclass(frozen=True)
class SampleRecord:
    """A single Anomaly-ShapeNet point-cloud sample."""

    collection: str
    class_name: str
    split: str
    sample_id: str
    pcd_path: Path
    gt_path: Path | None
    anomaly_type: str
    is_anomaly: bool


@dataclass(frozen=True)
class PointCountSummary:
    """Distribution summary for sample point counts."""

    count: int
    min: int
    mean: float
    max: int


@dataclass(frozen=True)
class ClassStatistics:
    """Per-class statistics for report generation."""

    sample_count: int
    train_count: int
    test_count: int
    anomaly_count: int
    normal_count: int
    point_counts: PointCountSummary


@dataclass(frozen=True)
class DatasetStatistics:
    """Dataset-level statistics used by P2 reports."""

    root: Path
    collections: tuple[str, ...]
    sample_count: int
    class_count: int
    split_counts: dict[str, int]
    collection_counts: dict[str, int]
    anomaly_type_counts: dict[str, int]
    point_counts: PointCountSummary
    gt_file_count: int
    aggregate_labeled_points: int
    aggregate_anomaly_points: int
    class_stats: dict[str, ClassStatistics]

    @property
    def aggregate_anomaly_ratio(self) -> float:
        if self.aggregate_labeled_points == 0:
            return 0.0
        return self.aggregate_anomaly_points / self.aggregate_labeled_points


def _resolve_dataset_dir(root: Path) -> Path:
    dataset_dir = root / "dataset"
    if dataset_dir.is_dir():
        return dataset_dir
    return root


def _parse_int_values(header: dict[str, tuple[str, ...]], key: str) -> tuple[int, ...]:
    return tuple(int(value) for value in header.get(key, ()))


def read_pcd_metadata(path: str | Path) -> PcdMetadata:
    """Read PCD header metadata without loading point payload."""

    pcd_path = Path(path)
    header: dict[str, tuple[str, ...]] = {}
    header_lines = 0

    with pcd_path.open("rb") as handle:
        while True:
            line = handle.readline()
            if not line:
                raise ValueError(f"PCD file has no DATA line: {pcd_path}")
            header_lines += 1
            decoded = line.decode("ascii", errors="strict").strip()
            if not decoded or decoded.startswith("#"):
                continue
            key, *values = decoded.split()
            key = key.upper()
            header[key] = tuple(values)
            if key == "DATA":
                header_bytes = handle.tell()
                break

    fields = header.get("FIELDS")
    if not fields:
        raise ValueError(f"PCD file has no FIELDS line: {pcd_path}")

    sizes = _parse_int_values(header, "SIZE")
    types = header.get("TYPE", ())
    counts = _parse_int_values(header, "COUNT")
    if not counts:
        counts = tuple(1 for _ in fields)

    if not (len(fields) == len(sizes) == len(types) == len(counts)):
        raise ValueError(f"PCD header field metadata length mismatch: {pcd_path}")

    width_values = _parse_int_values(header, "WIDTH")
    height_values = _parse_int_values(header, "HEIGHT")
    point_values = _parse_int_values(header, "POINTS")
    width = width_values[0] if width_values else None
    height = height_values[0] if height_values else None
    if point_values:
        point_count = point_values[0]
    elif width is not None and height is not None:
        point_count = width * height
    else:
        raise ValueError(f"PCD file has no POINTS or WIDTH/HEIGHT metadata: {pcd_path}")

    data_values = header.get("DATA")
    if not data_values:
        raise ValueError(f"PCD file has no DATA value: {pcd_path}")

    return PcdMetadata(
        path=pcd_path,
        point_count=point_count,
        fields=tuple(fields),
        sizes=sizes,
        types=tuple(value.upper() for value in types),
        counts=counts,
        width=width,
        height=height,
        data=data_values[0].lower(),
        header_bytes=header_bytes,
        header_lines=header_lines,
    )


def _dtype_for_pcd_field(field_type: str, size: int) -> np.dtype[Any]:
    if field_type == "F" and size == 4:
        return np.dtype("<f4")
    if field_type == "F" and size == 8:
        return np.dtype("<f8")
    if field_type == "I" and size in {1, 2, 4, 8}:
        return np.dtype(f"<i{size}")
    if field_type == "U" and size in {1, 2, 4, 8}:
        return np.dtype(f"<u{size}")
    raise ValueError(f"Unsupported PCD field type/size combination: {field_type}{size}")


def _structured_dtype(metadata: PcdMetadata) -> np.dtype[Any]:
    fields: list[Any] = []
    for name, size, field_type, count in zip(
        metadata.fields, metadata.sizes, metadata.types, metadata.counts, strict=True
    ):
        dtype = _dtype_for_pcd_field(field_type, size)
        if count == 1:
            fields.append((name, dtype))
        else:
            fields.append((name, dtype, (count,)))
    return np.dtype(fields)


def _load_ascii_points(path: Path, metadata: PcdMetadata) -> np.ndarray[Any, np.dtype[np.float32]]:
    with path.open("rb") as handle:
        handle.seek(metadata.header_bytes)
        payload = handle.read().decode("ascii", errors="strict").strip()
    if not payload:
        return np.empty((0, 3), dtype=np.float32)

    values = np.loadtxt(payload.splitlines(), dtype=np.float32)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    indices = [metadata.fields.index(axis) for axis in ("x", "y", "z")]
    return np.asarray(values[:, indices], dtype=np.float32)


def _load_binary_points(path: Path, metadata: PcdMetadata) -> np.ndarray[Any, np.dtype[np.float32]]:
    dtype = _structured_dtype(metadata)
    with path.open("rb") as handle:
        handle.seek(metadata.header_bytes)
        payload = handle.read()
    array = np.frombuffer(payload, dtype=dtype, count=metadata.point_count)
    field_names = array.dtype.names or ()
    missing = [axis for axis in ("x", "y", "z") if axis not in field_names]
    if missing:
        raise ValueError(f"PCD file is missing coordinate fields {missing}: {path}")
    return np.column_stack([array["x"], array["y"], array["z"]]).astype(np.float32, copy=False)


def read_pcd_points(path: str | Path) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Load XYZ points from an ASCII or uncompressed binary PCD file."""

    pcd_path = Path(path)
    metadata = read_pcd_metadata(pcd_path)
    if metadata.data == "ascii":
        return _load_ascii_points(pcd_path, metadata)
    if metadata.data == "binary":
        return _load_binary_points(pcd_path, metadata)
    raise ValueError(f"Unsupported PCD DATA mode {metadata.data!r}: {pcd_path}")


def read_gt_labels(path: str | Path) -> np.ndarray[Any, np.dtype[np.int64]]:
    """Read point-level labels from Anomaly-ShapeNet GT txt files."""

    gt_path = Path(path)
    values = np.loadtxt(gt_path, delimiter=",", dtype=np.float32)
    if values.size == 0:
        return np.empty((0,), dtype=np.int64)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.shape[1] < 4:
        raise ValueError(f"GT file must contain at least 4 columns: {gt_path}")
    return (values[:, 3] > 0).astype(np.int64, copy=False)


def read_gt_label_stats(path: str | Path) -> GTLabelStats:
    labels = read_gt_labels(path)
    return GTLabelStats(total_points=int(labels.size), anomaly_points=int(labels.sum()))


def parse_anomaly_type(sample_id: str, class_name: str) -> str:
    prefixes = [f"{class_name}_"]
    base_class_name = class_name.rstrip("0123456789")
    if base_class_name and base_class_name != class_name:
        prefixes.append(f"{base_class_name}_")
    suffix = sample_id
    for prefix in prefixes:
        if sample_id.startswith(prefix):
            suffix = sample_id[len(prefix) :]
            break
    anomaly_type = suffix.rstrip("0123456789")
    return ANOMALY_TYPE_ALIASES.get(anomaly_type, anomaly_type)


def discover_samples(
    root: str | Path,
    collections: Iterable[str] = DEFAULT_COLLECTIONS,
) -> list[SampleRecord]:
    """Discover Anomaly-ShapeNet PCD samples under one or more collections."""

    root_path = Path(root)
    dataset_dir = _resolve_dataset_dir(root_path)
    samples: list[SampleRecord] = []

    for collection in collections:
        collection_dir = dataset_dir / collection
        if not collection_dir.is_dir():
            continue
        for class_dir in sorted(path for path in collection_dir.iterdir() if path.is_dir()):
            for split in ("train", "test"):
                split_dir = class_dir / split
                if not split_dir.is_dir():
                    continue
                for pcd_path in sorted(split_dir.glob("*.pcd")):
                    sample_id = pcd_path.stem
                    anomaly_type = parse_anomaly_type(sample_id, class_dir.name)
                    is_anomaly = split == "test" and anomaly_type not in NORMAL_TYPES
                    gt_path = class_dir / "GT" / f"{sample_id}.txt"
                    samples.append(
                        SampleRecord(
                            collection=collection,
                            class_name=class_dir.name,
                            split=split,
                            sample_id=sample_id,
                            pcd_path=pcd_path,
                            gt_path=gt_path if gt_path.is_file() else None,
                            anomaly_type=anomaly_type,
                            is_anomaly=is_anomaly,
                        )
                    )
    return samples


def _point_count_summary(values: Iterable[int]) -> PointCountSummary:
    point_counts = list(values)
    if not point_counts:
        return PointCountSummary(count=0, min=0, mean=0.0, max=0)
    return PointCountSummary(
        count=len(point_counts),
        min=min(point_counts),
        mean=float(sum(point_counts) / len(point_counts)),
        max=max(point_counts),
    )


def _class_statistics(
    samples: list[SampleRecord], point_counts: dict[Path, int]
) -> ClassStatistics:
    sample_point_counts = [point_counts[sample.pcd_path] for sample in samples]
    return ClassStatistics(
        sample_count=len(samples),
        train_count=sum(sample.split == "train" for sample in samples),
        test_count=sum(sample.split == "test" for sample in samples),
        anomaly_count=sum(sample.is_anomaly for sample in samples),
        normal_count=sum(not sample.is_anomaly for sample in samples),
        point_counts=_point_count_summary(sample_point_counts),
    )


def collect_dataset_statistics(
    root: str | Path,
    collections: Iterable[str] = DEFAULT_COLLECTIONS,
) -> DatasetStatistics:
    """Collect sample counts, point-count distribution, and GT anomaly ratios."""

    root_path = Path(root)
    collection_tuple = tuple(collections)
    samples = discover_samples(root_path, collection_tuple)
    split_counts = Counter(sample.split for sample in samples)
    collection_counts = Counter(sample.collection for sample in samples)
    anomaly_type_counts = Counter(sample.anomaly_type for sample in samples)

    sample_point_counts: dict[Path, int] = {}
    for sample in samples:
        sample_point_counts[sample.pcd_path] = read_pcd_metadata(sample.pcd_path).point_count

    aggregate_labeled_points = 0
    aggregate_anomaly_points = 0
    gt_file_count = 0
    for sample in samples:
        if sample.gt_path is None:
            continue
        gt_file_count += 1
        label_stats = read_gt_label_stats(sample.gt_path)
        aggregate_labeled_points += label_stats.total_points
        aggregate_anomaly_points += label_stats.anomaly_points

    samples_by_class: dict[str, list[SampleRecord]] = defaultdict(list)
    for sample in samples:
        samples_by_class[sample.class_name].append(sample)

    return DatasetStatistics(
        root=root_path,
        collections=collection_tuple,
        sample_count=len(samples),
        class_count=len(samples_by_class),
        split_counts=dict(sorted(split_counts.items())),
        collection_counts=dict(sorted(collection_counts.items())),
        anomaly_type_counts=dict(sorted(anomaly_type_counts.items())),
        point_counts=_point_count_summary(sample_point_counts.values()),
        gt_file_count=gt_file_count,
        aggregate_labeled_points=aggregate_labeled_points,
        aggregate_anomaly_points=aggregate_anomaly_points,
        class_stats={
            class_name: _class_statistics(class_samples, sample_point_counts)
            for class_name, class_samples in sorted(samples_by_class.items())
        },
    )


def _normal_placeholder(
    points: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    return np.zeros_like(points, dtype=np.float32)


class AnomalyShapeNetDataset:
    """Numpy-backed Anomaly-ShapeNet dataset.

    The class intentionally returns zero normals when the source PCD contains only XYZ. Normal
    estimation belongs in preprocessing; this loader keeps raw data access deterministic.
    """

    def __init__(
        self,
        root: str | Path,
        split: str | None = None,
        collections: Iterable[str] = DEFAULT_COLLECTIONS,
    ) -> None:
        self.root = Path(root)
        self.split = split
        self.collections = tuple(collections)
        samples = discover_samples(self.root, self.collections)
        if split is not None:
            samples = [sample for sample in samples if sample.split == split]
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> DatasetItem:
        sample = self.samples[index]
        points = read_pcd_points(sample.pcd_path)
        normals = _normal_placeholder(points)
        if sample.gt_path is not None:
            labels = read_gt_labels(sample.gt_path)
        else:
            labels = np.zeros((points.shape[0],), dtype=np.int64)
        if labels.shape[0] != points.shape[0]:
            raise ValueError(
                f"Label count {labels.shape[0]} does not match point count {points.shape[0]} "
                f"for {sample.sample_id}"
            )
        meta: dict[str, Any] = {
            "collection": sample.collection,
            "class_name": sample.class_name,
            "split": sample.split,
            "sample_id": sample.sample_id,
            "anomaly_type": sample.anomaly_type,
            "is_anomaly": sample.is_anomaly,
            "pcd_path": str(sample.pcd_path),
            "gt_path": str(sample.gt_path) if sample.gt_path is not None else None,
        }
        return points, normals, labels, meta
