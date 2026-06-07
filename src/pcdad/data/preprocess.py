"""Deterministic preprocessing utilities for PASDF-compatible data."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.data.dataset import (
    DEFAULT_COLLECTIONS,
    SampleRecord,
    discover_samples,
    read_pcd_points,
)


class NormalizationMode(str, Enum):
    NONE = "none"
    UNIT_SPHERE = "unit_sphere"


@dataclass(frozen=True)
class NormalizationParams:
    mode: str
    center: tuple[float, float, float]
    scale: float


@dataclass(frozen=True)
class PreparedSample:
    collection: str
    class_name: str
    split: str
    sample_id: str
    anomaly_type: str
    is_anomaly: bool
    source_pcd_path: str
    source_gt_path: str | None
    output_pcd_path: str
    output_gt_path: str | None
    original_point_count: int
    output_point_count: int
    target_num_points: int
    seed: int
    sample_key: str
    sample_index_sha256: str
    unique_sampled_indices: int
    normalization: NormalizationParams


@dataclass(frozen=True)
class PrepareManifest:
    root: str
    output_root: str
    collections: tuple[str, ...]
    target_num_points: int
    seed: int
    normalize: str
    sample_count: int
    samples: tuple[PreparedSample, ...]


def _rng_seed(seed: int, key: str) -> int:
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="little", signed=False)


def _index_digest(indices: np.ndarray[Any, np.dtype[np.int64]]) -> str:
    return hashlib.sha256(np.ascontiguousarray(indices).tobytes()).hexdigest()


def deterministic_sample_indices(
    point_count: int,
    target_num_points: int,
    *,
    seed: int,
    key: str,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    """Return stable sample indices for a sample-specific key."""

    if point_count <= 0:
        raise ValueError("point_count must be positive")
    if target_num_points <= 0:
        raise ValueError("target_num_points must be positive")
    if point_count == target_num_points:
        return np.arange(point_count, dtype=np.int64)

    rng = np.random.default_rng(_rng_seed(seed, key))
    replace = point_count < target_num_points
    indices = rng.choice(point_count, size=target_num_points, replace=replace)
    return np.asarray(indices, dtype=np.int64)


def sample_points_and_labels(
    points: np.ndarray[Any, np.dtype[np.float32]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
    *,
    target_num_points: int,
    seed: int,
    key: str,
) -> tuple[
    np.ndarray[Any, np.dtype[np.float32]],
    np.ndarray[Any, np.dtype[np.int64]],
    np.ndarray[Any, np.dtype[np.int64]],
]:
    """Sample points and labels with the same deterministic index vector."""

    if labels.shape[0] != points.shape[0]:
        raise ValueError(
            f"Label count {labels.shape[0]} does not match point count {points.shape[0]}"
        )
    indices = deterministic_sample_indices(
        points.shape[0],
        target_num_points,
        seed=seed,
        key=key,
    )
    return points[indices], labels[indices], indices


def labels_for_points(
    points: np.ndarray[Any, np.dtype[np.float32]],
    gt_values: np.ndarray[Any, np.dtype[np.float32]],
    *,
    max_distance: float = 1e-4,
) -> np.ndarray[Any, np.dtype[np.int64]]:
    """Map GT coordinate-label rows onto PCD point order using nearest coordinates."""

    if gt_values.ndim == 1:
        gt_values = gt_values.reshape(1, -1)
    if gt_values.shape[1] < 4:
        raise ValueError(f"GT values must contain at least 4 columns, got {gt_values.shape}")
    gt_points = np.asarray(gt_values[:, :3], dtype=np.float32)
    gt_labels = (gt_values[:, 3] > 0).astype(np.int64, copy=False)
    if gt_points.shape[0] == points.shape[0] and np.allclose(gt_points, points, atol=1e-6):
        return gt_labels

    try:
        from scipy.spatial import cKDTree  # type: ignore[import-untyped]

        tree = cKDTree(gt_points.astype(np.float64, copy=False))
        distances, indices = tree.query(points.astype(np.float64, copy=False), k=1)
        if float(np.max(distances)) > max_distance:
            raise ValueError(
                "GT coordinates do not match PCD points: "
                f"max nearest-neighbor distance {float(np.max(distances)):.6g} "
                f"exceeds {max_distance:.6g}"
            )
        return np.asarray(gt_labels[indices], dtype=np.int64)
    except ImportError:
        labels = np.empty((points.shape[0],), dtype=np.int64)
        gt_points64 = gt_points.astype(np.float64, copy=False)
        for start in range(0, points.shape[0], 4096):
            chunk = points[start : start + 4096].astype(np.float64, copy=False)
            distances = ((chunk[:, None, :] - gt_points64[None, :, :]) ** 2).sum(axis=2)
            nearest_distances = np.sqrt(np.min(distances, axis=1))
            if float(np.max(nearest_distances)) > max_distance:
                raise ValueError(
                    "GT coordinates do not match PCD points: "
                    f"max nearest-neighbor distance {float(np.max(nearest_distances)):.6g} "
                    f"exceeds {max_distance:.6g}"
                ) from None
            labels[start : start + chunk.shape[0]] = gt_labels[np.argmin(distances, axis=1)]
        return labels


def read_gt_labels_for_points(
    path: str | Path,
    points: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.int64]]:
    gt_path = Path(path)
    gt_values = np.loadtxt(gt_path, delimiter=",", dtype=np.float32)
    return labels_for_points(points, gt_values)


def unit_sphere_normalize(
    points: np.ndarray[Any, np.dtype[np.float32]],
) -> tuple[np.ndarray[Any, np.dtype[np.float32]], NormalizationParams]:
    """Center points by their mean and scale them into the unit sphere."""

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Expected points with shape (N, 3), got {points.shape}")
    center = points.astype(np.float64).mean(axis=0)
    centered = points.astype(np.float64) - center
    radii = np.linalg.norm(centered, axis=1)
    scale = float(radii.max()) if radii.size else 1.0
    if scale <= 0:
        scale = 1.0
    normalized = (centered / scale).astype(np.float32)
    params = NormalizationParams(
        mode=NormalizationMode.UNIT_SPHERE.value,
        center=(float(center[0]), float(center[1]), float(center[2])),
        scale=scale,
    )
    return normalized, params


def _normalize(
    points: np.ndarray[Any, np.dtype[np.float32]], mode: NormalizationMode
) -> tuple[np.ndarray[Any, np.dtype[np.float32]], NormalizationParams]:
    if mode == NormalizationMode.NONE:
        return (
            np.asarray(points, dtype=np.float32),
            NormalizationParams(
                mode=NormalizationMode.NONE.value,
                center=(0.0, 0.0, 0.0),
                scale=1.0,
            ),
        )
    if mode == NormalizationMode.UNIT_SPHERE:
        return unit_sphere_normalize(points)
    raise ValueError(f"Unsupported normalization mode: {mode}")


def write_ascii_xyz_pcd(
    path: str | Path,
    points: np.ndarray[Any, np.dtype[np.float32]],
) -> None:
    """Write an ASCII PCD containing XYZ float fields only."""

    pcd_path = Path(path)
    pcd_path.parent.mkdir(parents=True, exist_ok=True)
    points_array = np.asarray(points, dtype=np.float32)
    header = "\n".join(
        [
            "# .PCD v0.7 - Point Cloud Data file format",
            "VERSION 0.7",
            "FIELDS x y z",
            "SIZE 4 4 4",
            "TYPE F F F",
            "COUNT 1 1 1",
            f"WIDTH {points_array.shape[0]}",
            "HEIGHT 1",
            "VIEWPOINT 0 0 0 1 0 0 0",
            f"POINTS {points_array.shape[0]}",
            "DATA ascii",
        ]
    )
    with pcd_path.open("w", encoding="utf-8") as handle:
        handle.write(header)
        handle.write("\n")
        np.savetxt(handle, points_array, fmt="%.8f %.8f %.8f")


def write_pasdf_gt_txt(
    path: str | Path,
    points: np.ndarray[Any, np.dtype[np.float32]],
    labels: np.ndarray[Any, np.dtype[np.int64]],
) -> None:
    """Write PASDF ShapeNetAD GT txt with space-delimited XYZ and label columns."""

    if labels.shape[0] != points.shape[0]:
        raise ValueError(
            f"Label count {labels.shape[0]} does not match point count {points.shape[0]}"
        )
    gt_path = Path(path)
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    payload = np.column_stack(
        [np.asarray(points, dtype=np.float32), np.asarray(labels, dtype=np.int64)]
    )
    np.savetxt(gt_path, payload, fmt=["%.8f", "%.8f", "%.8f", "%d"], delimiter=" ")


def _sample_key(sample: SampleRecord) -> str:
    return f"{sample.collection}/{sample.class_name}/{sample.split}/{sample.sample_id}"


def _prepare_one_sample(
    sample: SampleRecord,
    *,
    output_root: Path,
    target_num_points: int,
    seed: int,
    normalize: NormalizationMode,
) -> PreparedSample:
    points = read_pcd_points(sample.pcd_path)
    if sample.gt_path is not None:
        labels = read_gt_labels_for_points(sample.gt_path, points)
    else:
        labels = np.zeros((points.shape[0],), dtype=np.int64)
    normalized_points, normalization = _normalize(points, normalize)
    key = _sample_key(sample)
    sampled_points, sampled_labels, indices = sample_points_and_labels(
        normalized_points,
        labels,
        target_num_points=target_num_points,
        seed=seed,
        key=key,
    )

    output_pcd_path = output_root / sample.class_name / sample.split / f"{sample.sample_id}.pcd"
    write_ascii_xyz_pcd(output_pcd_path, sampled_points)
    output_gt_path: Path | None = None
    if sample.gt_path is not None:
        output_gt_path = output_root / sample.class_name / "GT" / f"{sample.sample_id}.txt"
        write_pasdf_gt_txt(output_gt_path, sampled_points, sampled_labels)

    return PreparedSample(
        collection=sample.collection,
        class_name=sample.class_name,
        split=sample.split,
        sample_id=sample.sample_id,
        anomaly_type=sample.anomaly_type,
        is_anomaly=sample.is_anomaly,
        source_pcd_path=str(sample.pcd_path),
        source_gt_path=str(sample.gt_path) if sample.gt_path is not None else None,
        output_pcd_path=str(output_pcd_path),
        output_gt_path=str(output_gt_path) if output_gt_path is not None else None,
        original_point_count=int(points.shape[0]),
        output_point_count=int(sampled_points.shape[0]),
        target_num_points=target_num_points,
        seed=seed,
        sample_key=key,
        sample_index_sha256=_index_digest(indices),
        unique_sampled_indices=int(np.unique(indices).size),
        normalization=normalization,
    )


def _manifest_to_json(manifest: PrepareManifest) -> dict[str, Any]:
    return asdict(manifest)


def prepare_pasdf_dataset(
    root: str | Path,
    *,
    output_root: str | Path | None = None,
    target_num_points: int = 16384,
    seed: int = 42,
    collections: Iterable[str] = DEFAULT_COLLECTIONS,
    class_names: Iterable[str] | None = None,
    normalize: NormalizationMode | str = NormalizationMode.UNIT_SPHERE,
) -> PrepareManifest:
    """Create a PASDF-compatible fixed-size ShapeNetAD dataset directory."""

    root_path = Path(root)
    output_path = Path(output_root) if output_root is not None else root_path / "dataset" / "16384"
    collection_tuple = tuple(collections)
    class_filter = set(class_names) if class_names is not None else None
    normalization = NormalizationMode(normalize)
    samples = discover_samples(root_path, collection_tuple)
    if class_filter is not None:
        samples = [sample for sample in samples if sample.class_name in class_filter]
    if not samples:
        raise ValueError("No samples matched the requested root, collections, and classes")

    prepared = tuple(
        _prepare_one_sample(
            sample,
            output_root=output_path,
            target_num_points=target_num_points,
            seed=seed,
            normalize=normalization,
        )
        for sample in samples
    )
    manifest = PrepareManifest(
        root=str(root_path),
        output_root=str(output_path),
        collections=collection_tuple,
        target_num_points=target_num_points,
        seed=seed,
        normalize=normalization.value,
        sample_count=len(prepared),
        samples=prepared,
    )
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "preprocess_manifest.json").write_text(
        json.dumps(_manifest_to_json(manifest), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest
