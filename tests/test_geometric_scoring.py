from __future__ import annotations

import numpy as np

from pcdad.geometry.residuals import GeometryResidualResult
from pcdad.scoring.aggregate import percentile_score, smooth_point_scores, topk_mean
from pcdad.scoring.geometric import GeometryScoreConfig, score_geometry_residuals


def test_topk_mean_uses_highest_ratio_with_at_least_one_point() -> None:
    scores = np.array([0.0, 1.0, 2.0, 100.0], dtype=np.float32)

    assert topk_mean(scores, ratio=0.25) == 100.0
    assert topk_mean(scores, ratio=0.5) == 51.0


def test_percentile_score_handles_constant_scores() -> None:
    scores = np.array([3.0, 3.0, 3.0], dtype=np.float32)

    assert percentile_score(scores, percentile=95.0) == 3.0


def test_smooth_point_scores_averages_neighbor_scores() -> None:
    points = np.array(
        [[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [5.0, 0.0, 0.0]],
        dtype=np.float32,
    )
    scores = np.array([0.0, 10.0, 2.0], dtype=np.float32)

    smoothed = smooth_point_scores(points, scores, k=1)

    np.testing.assert_allclose(smoothed, np.array([5.0, 5.0, 6.0]), atol=1e-6)


def test_score_geometry_residuals_combines_enabled_components_and_topk_object_score() -> None:
    residuals = GeometryResidualResult(
        nn_distance=np.array([0.0, 0.1, 1.0, 0.0], dtype=np.float32),
        normal_angle=np.array([0.0, 0.0, 0.5, 0.0], dtype=np.float32),
        curvature_delta=np.array([0.0, 0.1, 0.7, 0.0], dtype=np.float32),
        template_indices=np.array([0, 1, 2, 3], dtype=np.int64),
    )

    result = score_geometry_residuals(
        residuals,
        GeometryScoreConfig(
            distance_weight=1.0,
            normal_weight=0.5,
            curvature_weight=0.5,
            topk_ratio=0.25,
            smooth_k=0,
        ),
    )

    assert result.point_scores.shape == (4,)
    assert int(np.argmax(result.point_scores)) == 2
    assert result.object_score == float(result.point_scores[2])
    assert set(result.components) == {"distance", "normal", "curvature"}
