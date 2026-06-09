from __future__ import annotations

import numpy as np
import pytest

from pcdad.geometry.neighbors import knn_indices, nearest_neighbors


def test_nearest_neighbors_returns_sorted_distances_and_indices() -> None:
    query = np.array([[0.1, 0.0, 0.0], [2.2, 0.0, 0.0]], dtype=np.float32)
    reference = np.array(
        [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]],
        dtype=np.float32,
    )

    result = nearest_neighbors(query, reference, k=2)

    assert result.indices.shape == (2, 2)
    assert result.distances.shape == (2, 2)
    np.testing.assert_array_equal(result.indices[0], np.array([0, 1]))
    np.testing.assert_allclose(result.distances[0], np.array([0.1, 1.9]), atol=1e-6)
    np.testing.assert_array_equal(result.indices[1], np.array([1, 2]))
    np.testing.assert_allclose(result.distances[1], np.array([0.2, 0.8]), atol=1e-6)


def test_knn_indices_excludes_self_and_returns_k_neighbors() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [5.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )

    indices = knn_indices(points, k=2)

    assert indices.shape == (4, 2)
    assert 0 not in indices[0]
    np.testing.assert_array_equal(indices[3], np.array([1, 0]))


def test_nearest_neighbors_rejects_invalid_shapes_and_k() -> None:
    reference = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
    with pytest.raises(ValueError, match="shape \\(N, 3\\)"):
        nearest_neighbors(np.array([0.0, 0.0, 0.0], dtype=np.float32), reference)
    with pytest.raises(ValueError, match="positive"):
        nearest_neighbors(reference, reference, k=0)
    with pytest.raises(ValueError, match="reference point count"):
        nearest_neighbors(reference, reference, k=2)


def test_knn_indices_requires_enough_points() -> None:
    with pytest.raises(ValueError, match="at least k \\+ 1"):
        knn_indices(np.array([[0.0, 0.0, 0.0]], dtype=np.float32), k=1)
