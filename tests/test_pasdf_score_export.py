from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pcdad.analysis.pasdf_scores import (
    PasdfSampleScore,
    render_score_export_markdown,
    summarize_point_scores,
    write_sample_scores_csv,
)


def test_summarize_point_scores_computes_topk_and_gt_background_means() -> None:
    record = summarize_point_scores(
        class_name="tap1",
        sample_id="tap1_broken2",
        sample_path="/data/tap1/test/broken/tap1_broken2.pcd",
        point_scores=np.array([0.1, 0.8, 0.4, 0.9], dtype=np.float32),
        mask=np.array([0, 1, 0, 1], dtype=np.float32),
        label=1,
        top_k=2,
        point_score_path="points/tap1_broken2.npz",
    )

    assert record == PasdfSampleScore(
        class_name="tap1",
        sample_id="tap1_broken2",
        sample_path="/data/tap1/test/broken/tap1_broken2.pcd",
        label=1,
        point_count=4,
        object_score=0.85,
        topk_score=0.85,
        score_mean=0.55,
        score_p95=0.885,
        score_max=0.9,
        gt_point_count=2,
        gt_point_ratio=0.5,
        gt_score_mean=0.85,
        background_score_mean=0.25,
        point_score_path="points/tap1_broken2.npz",
    )


def test_summarize_point_scores_handles_positive_sample_without_gt_points() -> None:
    record = summarize_point_scores(
        class_name="ashtray0",
        sample_id="ashtray0_positive0",
        sample_path="/data/ashtray0/test/positive/ashtray0_positive0.pcd",
        point_scores=np.array([0.2, 0.4, 0.6], dtype=np.float32),
        mask=np.array([0, 0, 0], dtype=np.float32),
        label=0,
        top_k=10,
    )

    assert record.point_count == 3
    assert record.object_score == 0.4
    assert record.gt_point_count == 0
    assert record.gt_point_ratio == 0.0
    assert record.gt_score_mean is None
    assert record.background_score_mean == 0.4
    assert record.point_score_path is None


def test_summarize_point_scores_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="At least one point score"):
        summarize_point_scores(
            class_name="cap3",
            sample_id="empty",
            sample_path="empty.pcd",
            point_scores=np.array([], dtype=np.float32),
            mask=np.array([], dtype=np.float32),
            label=1,
            top_k=1,
        )

    with pytest.raises(ValueError, match="same length"):
        summarize_point_scores(
            class_name="cap3",
            sample_id="bad_mask",
            sample_path="bad_mask.pcd",
            point_scores=np.array([0.1, 0.2], dtype=np.float32),
            mask=np.array([0], dtype=np.float32),
            label=1,
            top_k=1,
        )

    with pytest.raises(ValueError, match="top_k must be >= 1"):
        summarize_point_scores(
            class_name="cap3",
            sample_id="bad_topk",
            sample_path="bad_topk.pcd",
            point_scores=np.array([0.1], dtype=np.float32),
            mask=np.array([0], dtype=np.float32),
            label=0,
            top_k=0,
        )


def test_write_sample_scores_csv_uses_stable_fields_and_empty_nullable_values(
    tmp_path: Path,
) -> None:
    records = [
        summarize_point_scores(
            class_name="tap1",
            sample_id="tap1_broken2",
            sample_path="/data/tap1/test/broken/tap1_broken2.pcd",
            point_scores=np.array([0.1, 0.8, 0.4, 0.9], dtype=np.float32),
            mask=np.array([0, 1, 0, 1], dtype=np.float32),
            label=1,
            top_k=2,
            point_score_path="points/tap1_broken2.npz",
        ),
        summarize_point_scores(
            class_name="tap1",
            sample_id="tap1_positive0",
            sample_path="/data/tap1/test/positive/tap1_positive0.pcd",
            point_scores=np.array([0.2, 0.4], dtype=np.float32),
            mask=np.array([0, 0], dtype=np.float32),
            label=0,
            top_k=1,
        ),
    ]
    output = tmp_path / "sample_scores.csv"

    write_sample_scores_csv(records, output)

    csv_text = output.read_text(encoding="utf-8")
    assert csv_text.splitlines()[0] == (
        "class_name,sample_id,sample_path,label,point_count,object_score,topk_score,"
        "score_mean,score_p95,score_max,gt_point_count,gt_point_ratio,gt_score_mean,"
        "background_score_mean,point_score_path"
    )
    assert "tap1,tap1_broken2,/data/tap1/test/broken/tap1_broken2.pcd,1,4,0.85" in csv_text
    assert "tap1,tap1_positive0,/data/tap1/test/positive/tap1_positive0.pcd,0,2,0.4" in csv_text
    assert ",0,0.0,,0.3," in csv_text


def test_render_score_export_markdown_summarizes_classes_and_priority_samples() -> None:
    records = [
        summarize_point_scores(
            class_name="helmet1",
            sample_id="helmet1_bulge0",
            sample_path="/data/helmet1/test/bulge/helmet1_bulge0.pcd",
            point_scores=np.array([0.8, 0.1, 0.2, 0.1], dtype=np.float32),
            mask=np.array([0, 1, 1, 0], dtype=np.float32),
            label=1,
            top_k=1,
        ),
        summarize_point_scores(
            class_name="helmet1",
            sample_id="helmet1_positive0",
            sample_path="/data/helmet1/test/positive/helmet1_positive0.pcd",
            point_scores=np.array([0.7, 0.6, 0.2, 0.1], dtype=np.float32),
            mask=np.array([0, 0, 0, 0], dtype=np.float32),
            label=0,
            top_k=1,
        ),
        summarize_point_scores(
            class_name="tap1",
            sample_id="tap1_broken2",
            sample_path="/data/tap1/test/broken/tap1_broken2.pcd",
            point_scores=np.array([0.1, 0.8, 0.4, 0.9], dtype=np.float32),
            mask=np.array([0, 1, 0, 1], dtype=np.float32),
            label=1,
            top_k=2,
        ),
    ]

    markdown = render_score_export_markdown(records, title="P5 PASDF Score Export")

    assert markdown.startswith("# P5 PASDF Score Export")
    assert "- 样本数：3" in markdown
    assert (
        "| helmet1 | 2 | 1 | 1 | 0.750000 | 0.800000 | 0.700000 | 0.150000 | " "0.425000 |"
    ) in markdown
    assert "`helmet1_bulge0`" in markdown
    assert "GT 内均值低于背景均值" in markdown


def test_render_score_export_markdown_rejects_empty_records() -> None:
    with pytest.raises(ValueError, match="At least one PASDF sample score"):
        render_score_export_markdown([], title="empty")
