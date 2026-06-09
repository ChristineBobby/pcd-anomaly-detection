from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.analysis.sample_geometry import (
    GeometryAnalysisSpec,
    analyze_class_geometry_samples,
    render_geometry_smoke_markdown,
)
from pcdad.data.preprocess import write_ascii_xyz_pcd, write_pasdf_gt_txt
from pcdad.scoring.geometric import GeometryScoreConfig


def _make_geometry_dataset(root: Path) -> Path:
    dataset_root = root / "Anomaly-ShapeNet-v2" / "dataset" / "16384"
    class_root = dataset_root / "widget0"
    template = np.array(
        [
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, -1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [-1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    write_ascii_xyz_pcd(class_root / "train" / "widget0_template0.pcd", template)
    write_ascii_xyz_pcd(class_root / "test" / "widget0_positive0.pcd", template)

    anomaly = template.copy()
    anomaly[4] = np.array([0.0, 0.0, 0.9], dtype=np.float32)
    labels = np.zeros((template.shape[0],), dtype=np.int64)
    labels[4] = 1
    write_ascii_xyz_pcd(class_root / "test" / "widget0_bulge0.pcd", anomaly)
    write_pasdf_gt_txt(class_root / "GT" / "widget0_bulge0.txt", anomaly, labels)
    return dataset_root


def _make_dataset_with_many_anomalies(root: Path) -> Path:
    dataset_root = _make_geometry_dataset(root)
    class_root = dataset_root / "widget0"
    template = np.array(
        [
            [-1.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [1.0, -1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [-1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    for index in range(3):
        anomaly = template.copy()
        anomaly[4] = np.array([0.0, 0.0, 0.4 + index * 0.1], dtype=np.float32)
        labels = np.zeros((template.shape[0],), dtype=np.int64)
        labels[4] = 1
        write_ascii_xyz_pcd(class_root / "test" / f"widget0_crack{index}.pcd", anomaly)
        write_pasdf_gt_txt(class_root / "GT" / f"widget0_crack{index}.txt", anomaly, labels)
    return dataset_root


def test_analyze_class_geometry_samples_scores_anomaly_above_positive(tmp_path: Path) -> None:
    dataset_root = _make_geometry_dataset(tmp_path)

    summary = analyze_class_geometry_samples(
        GeometryAnalysisSpec(
            dataset_root=dataset_root,
            class_name="widget0",
            max_samples=2,
            k_normal=4,
            k_curvature=(4, 6),
            topk_ratio=0.2,
            use_normals=False,
            use_curvature=False,
        )
    )

    assert summary.class_name == "widget0"
    assert summary.template_sample_id == "widget0_template0"
    assert len(summary.rows) == 2
    by_id = {row.sample_id: row for row in summary.rows}
    assert by_id["widget0_bulge0"].is_anomaly is True
    assert by_id["widget0_bulge0"].gt_anomaly_points == 1
    assert by_id["widget0_bulge0"].object_score > by_id["widget0_positive0"].object_score
    assert by_id["widget0_bulge0"].gt_point_score_mean > by_id["widget0_bulge0"].bg_point_score_mean


def test_analyze_class_geometry_samples_keeps_positive_control_when_anomalies_exceed_limit(
    tmp_path: Path,
) -> None:
    dataset_root = _make_dataset_with_many_anomalies(tmp_path)

    summary = analyze_class_geometry_samples(
        GeometryAnalysisSpec(
            dataset_root=dataset_root,
            class_name="widget0",
            max_samples=3,
            k_normal=4,
            k_curvature=(4, 6),
            topk_ratio=0.2,
            use_normals=False,
            use_curvature=False,
        )
    )

    assert len(summary.rows) == 3
    assert any(not row.is_anomaly for row in summary.rows)
    assert any(row.is_anomaly for row in summary.rows)


def test_render_geometry_smoke_markdown_contains_chinese_summary(tmp_path: Path) -> None:
    dataset_root = _make_geometry_dataset(tmp_path)
    summary = analyze_class_geometry_samples(
        GeometryAnalysisSpec(
            dataset_root=dataset_root,
            class_name="widget0",
            max_samples=1,
            k_normal=4,
            k_curvature=(4, 6),
            topk_ratio=0.2,
            use_normals=False,
            use_curvature=False,
        )
    )

    markdown = render_geometry_smoke_markdown((summary,))

    assert markdown.startswith("# P4 几何 Smoke 摘要")
    assert "## 类别摘要" in markdown
    assert "| widget0 | widget0_template0 |" in markdown
    assert "## 样本明细" in markdown


def test_analyze_class_geometry_samples_uses_score_config_weights(tmp_path: Path) -> None:
    dataset_root = _make_geometry_dataset(tmp_path)

    distance_only = analyze_class_geometry_samples(
        GeometryAnalysisSpec(
            dataset_root=dataset_root,
            class_name="widget0",
            max_samples=1,
            k_normal=4,
            k_curvature=(4, 6),
            topk_ratio=0.2,
            use_normals=True,
            use_curvature=True,
            score_config=GeometryScoreConfig(
                distance_weight=1.0,
                normal_weight=0.0,
                curvature_weight=0.0,
                topk_ratio=0.2,
                smooth_k=0,
            ),
        )
    )
    full_weight = analyze_class_geometry_samples(
        GeometryAnalysisSpec(
            dataset_root=dataset_root,
            class_name="widget0",
            max_samples=1,
            k_normal=4,
            k_curvature=(4, 6),
            topk_ratio=0.2,
            use_normals=True,
            use_curvature=True,
            score_config=GeometryScoreConfig(
                distance_weight=1.0,
                normal_weight=1.0,
                curvature_weight=1.0,
                topk_ratio=0.2,
                smooth_k=0,
            ),
        )
    )

    assert full_weight.rows[0].object_score != distance_only.rows[0].object_score
