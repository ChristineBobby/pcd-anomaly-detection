from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pcdad.analysis.targeted_p6 import (
    Cap3ResidualRegionRecord,
    Tap1RegionExplanationRecord,
    TopKRegionMetrics,
    compute_cap3_residual_region_record,
    compute_tap1_region_explanation_record,
    compute_topk_region_metrics,
    render_region_explanation_markdown,
    topk_indices,
    write_region_explanation_csv,
)


def _write_score_npz(
    root: Path,
    class_name: str,
    sample_id: str,
    *,
    label: int,
    points: np.ndarray,
    scores: np.ndarray,
    mask: np.ndarray,
) -> Path:
    path = root / class_name / "points" / f"{sample_id}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        points=points.astype(np.float32),
        point_scores=scores.astype(np.float64),
        mask=mask.astype(np.int64),
        label=np.array(label, dtype=np.int64),
        object_score=np.array(0.8, dtype=np.float64),
    )
    return path


def _write_template_obj(root: Path, class_name: str, vertices: np.ndarray) -> Path:
    path = root / class_name / f"{class_name}_template0.obj"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_vertices = np.column_stack(
        [
            -vertices[:, 1],
            vertices[:, 2],
            -vertices[:, 0],
        ]
    )
    lines = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in raw_vertices]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_topk_indices_are_stable_and_validate_inputs() -> None:
    indices = topk_indices(np.array([0.2, 0.8, 0.8, 0.1]), ratio=0.5)

    assert indices.tolist() == [1, 2]
    with pytest.raises(ValueError, match="ratio"):
        topk_indices(np.array([0.1, 0.2]), ratio=0.0)
    with pytest.raises(ValueError, match="finite"):
        topk_indices(np.array([0.1, np.nan]), ratio=0.5)


def test_compute_topk_region_metrics_counts_gt_and_neighbor_hits() -> None:
    points = np.array(
        [
            [0.00, 0.00, 0.00],
            [0.03, 0.00, 0.00],
            [0.20, 0.00, 0.00],
            [1.00, 0.00, 0.00],
        ],
        dtype=np.float32,
    )
    scores = np.array([0.1, 0.9, 0.8, 0.2], dtype=np.float64)
    mask = np.array([1, 0, 0, 0], dtype=np.int64)

    metrics = compute_topk_region_metrics(
        points=points,
        scores=scores,
        mask=mask,
        score_name="geometry",
        top_ratio=0.5,
        neighbor_radius_ratio=0.05,
    )

    assert metrics == TopKRegionMetrics(
        score_name="geometry",
        top_ratio=0.5,
        top_count=2,
        gt_hit_count=0,
        gt_hit_rate=0.0,
        gt_coverage=0.0,
        gt_neighbor_hit_count=1,
        gt_neighbor_hit_rate=0.5,
        gt_neighbor_coverage=0.5,
        gt_enrichment=0.0,
        gt_neighbor_enrichment=1.0,
    )


def test_compute_tap1_region_explanation_record_compares_pasdf_and_geometry(
    tmp_path: Path,
) -> None:
    points = np.array(
        [
            [0.00, 0.00, 0.00],
            [0.03, 0.00, 0.00],
            [0.20, 0.00, 0.00],
            [1.00, 0.00, 0.00],
        ],
        dtype=np.float32,
    )
    score_path = _write_score_npz(
        tmp_path / "scores",
        "tap1",
        "tap1_broken2",
        label=1,
        points=points,
        scores=np.array([0.95, 0.3, 0.2, 0.1], dtype=np.float64),
        mask=np.array([1, 0, 0, 0], dtype=np.int64),
    )
    _write_template_obj(
        tmp_path / "templates",
        "tap1",
        np.array(
            [
                [0.00, 0.00, 0.00],
                [0.20, 0.00, 0.00],
                [1.00, 0.00, 0.00],
            ],
            dtype=np.float32,
        ),
    )

    record = compute_tap1_region_explanation_record(
        score_path=score_path,
        template_root=tmp_path / "templates",
        top_ratio=0.5,
        neighbor_radius_ratio=0.05,
    )

    assert isinstance(record, Tap1RegionExplanationRecord)
    assert record.sample_id == "tap1_broken2"
    assert record.gt_point_count == 1
    assert record.pasdf_topk_gt_hit_rate == 0.5
    assert record.geometry_topk_gt_hit_rate == 0.0
    assert record.geometry_neighbor_hit_rate == 0.5
    assert record.neighbor_radius > 0.0


def test_compute_cap3_residual_region_record_reports_overlap_and_concentration(
    tmp_path: Path,
) -> None:
    points = np.array(
        [
            [0.00, 0.00, 0.00],
            [1.00, 0.00, 0.00],
            [2.00, 0.00, 0.00],
            [3.00, 0.00, 0.00],
        ],
        dtype=np.float32,
    )
    score_path = _write_score_npz(
        tmp_path / "scores",
        "cap3",
        "cap3_positive9",
        label=0,
        points=points,
        scores=np.array([0.1, 0.2, 0.9, 0.8], dtype=np.float64),
        mask=np.zeros(4, dtype=np.int64),
    )
    _write_template_obj(
        tmp_path / "templates",
        "cap3",
        np.array(
            [
                [0.00, 0.00, 0.00],
                [1.00, 0.00, 0.00],
                [1.95, 0.00, 0.00],
                [2.90, 0.00, 0.00],
            ],
            dtype=np.float32,
        ),
    )

    record = compute_cap3_residual_region_record(
        score_path=score_path,
        template_root=tmp_path / "templates",
        top_ratio=0.5,
    )

    assert isinstance(record, Cap3ResidualRegionRecord)
    assert record.sample_id == "cap3_positive9"
    assert record.pasdf_residual_topk_overlap == 1.0
    assert record.residual_topk_mean > 0.0
    assert 0.0 <= record.residual_topk_bbox_ratio <= 1.0
    assert 0.0 <= record.residual_topk_mean_pair_distance_ratio <= 1.0


def test_region_explanation_csv_and_markdown_are_stable(tmp_path: Path) -> None:
    tap1_records = (
        Tap1RegionExplanationRecord(
            class_name="tap1",
            sample_id="tap1_broken2",
            label=1,
            point_count=4,
            gt_point_count=1,
            neighbor_radius=0.03,
            pasdf_topk_gt_hit_rate=0.5,
            geometry_topk_gt_hit_rate=0.0,
            pasdf_gt_coverage=1.0,
            geometry_gt_coverage=0.0,
            pasdf_neighbor_hit_rate=0.5,
            geometry_neighbor_hit_rate=0.5,
            pasdf_neighbor_enrichment=1.0,
            geometry_neighbor_enrichment=1.0,
        ),
    )
    cap3_records = (
        Cap3ResidualRegionRecord(
            class_name="cap3",
            sample_id="cap3_positive9",
            label=0,
            point_count=4,
            pasdf_object_score=0.8,
            residual_topk_mean=0.2,
            residual_topk_p95=0.3,
            pasdf_residual_topk_overlap=1.0,
            residual_topk_bbox_ratio=0.4,
            residual_topk_mean_pair_distance_ratio=0.3,
        ),
    )

    csv_path = write_region_explanation_csv(
        tap1_records=tap1_records,
        cap3_records=cap3_records,
        path=tmp_path / "region.csv",
    )
    markdown = render_region_explanation_markdown(
        tap1_records=tap1_records,
        cap3_records=cap3_records,
    )

    csv_text = csv_path.read_text(encoding="utf-8")
    assert "record_type,class_name,sample_id,label" in csv_text
    assert "tap1_region,tap1,tap1_broken2,1" in csv_text
    assert "cap3_residual,cap3,cap3_positive9,0" in csv_text
    assert "P6 Region Explanation" in markdown
    assert "tap1 region-level explanation" in markdown
    assert "cap3 residual region diagnostics" in markdown
    assert "当前结果不支持把 geometry 作为主局部解释信号" in markdown
