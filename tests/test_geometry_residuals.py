from __future__ import annotations

import numpy as np
import pytest

from pcdad.geometry.residuals import point_to_template_residuals


def _template_points() -> np.ndarray:
    return np.array(
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


def test_point_to_template_residuals_marks_displaced_point_with_larger_distance() -> None:
    template = _template_points()
    sample = template.copy()
    sample[4] = np.array([0.0, 0.0, 0.7], dtype=np.float32)

    residuals = point_to_template_residuals(
        sample,
        template,
        k_normal=4,
        k_curvature=(4, 6),
        use_normals=True,
        use_curvature=True,
    )

    assert residuals.nn_distance.shape == (sample.shape[0],)
    assert residuals.template_indices.shape == (sample.shape[0],)
    assert residuals.normal_angle is not None
    assert residuals.curvature_delta is not None
    assert int(np.argmax(residuals.nn_distance)) == 4
    assert float(residuals.nn_distance[4]) > 0.6
    assert float(np.median(residuals.nn_distance)) < 1e-6


def test_point_to_template_residuals_can_disable_optional_components() -> None:
    template = _template_points()

    residuals = point_to_template_residuals(
        template,
        template,
        use_normals=False,
        use_curvature=False,
    )

    np.testing.assert_allclose(residuals.nn_distance, 0.0, atol=1e-6)
    assert residuals.normal_angle is None
    assert residuals.curvature_delta is None


def test_point_to_template_residuals_rejects_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="shape \\(N, 3\\)"):
        point_to_template_residuals(np.array([1.0, 2.0, 3.0]), _template_points())
