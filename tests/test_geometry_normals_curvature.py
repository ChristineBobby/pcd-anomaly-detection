from __future__ import annotations

import numpy as np
import pytest

from pcdad.geometry.curvature import estimate_multiscale_curvature
from pcdad.geometry.normals import estimate_pca_normals, normal_angle_residual


def _plane_grid(size: int = 7) -> np.ndarray:
    values = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    xx, yy = np.meshgrid(values, values)
    zz = np.zeros_like(xx)
    return np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]).astype(np.float32)


def _paraboloid_grid(size: int = 7) -> np.ndarray:
    values = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    xx, yy = np.meshgrid(values, values)
    zz = 0.35 * (xx**2 + yy**2)
    return np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]).astype(np.float32)


def test_estimate_pca_normals_returns_unit_normals_and_low_plane_curvature() -> None:
    points = _plane_grid()

    result = estimate_pca_normals(points, k=8)

    assert result.normals.shape == points.shape
    np.testing.assert_allclose(np.linalg.norm(result.normals, axis=1), 1.0, atol=1e-5)
    assert result.eigenvalues.shape == (points.shape[0], 3)
    assert float(np.median(result.curvature)) < 1e-6
    assert float(np.median(np.abs(result.normals[:, 2]))) > 0.99


def test_normal_angle_residual_is_invariant_to_normal_sign() -> None:
    source = np.array(
        [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    target = np.array(
        [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0]],
        dtype=np.float32,
    )

    residual = normal_angle_residual(source, target)

    np.testing.assert_allclose(residual, np.array([0.0, 1.0, 0.0]), atol=1e-6)


def test_multiscale_curvature_separates_paraboloid_from_plane() -> None:
    plane = _plane_grid(size=9)
    paraboloid = _paraboloid_grid(size=9)

    plane_curvature = estimate_multiscale_curvature(plane, k_values=(8, 16))
    paraboloid_curvature = estimate_multiscale_curvature(paraboloid, k_values=(8, 16))

    assert set(plane_curvature.per_scale) == {8, 16}
    assert plane_curvature.mean_curvature.shape == (plane.shape[0],)
    assert paraboloid_curvature.mean_curvature.shape == (paraboloid.shape[0],)
    assert float(np.median(paraboloid_curvature.mean_curvature)) > float(
        np.median(plane_curvature.mean_curvature)
    )


def test_estimate_pca_normals_rejects_too_few_neighbors() -> None:
    points = _plane_grid(size=2)
    with pytest.raises(ValueError, match="at least k \\+ 1"):
        estimate_pca_normals(points, k=8)
