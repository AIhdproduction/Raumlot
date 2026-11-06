from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np
import pytest


@pytest.mark.native
def test_version_matches_cargo_package_version() -> None:
    import raumlot_native

    cargo_toml = tomllib.loads(
        (Path(__file__).parents[2] / "native" / "Cargo.toml").read_text(encoding="utf-8")
    )

    assert raumlot_native.version() == cargo_toml["package"]["version"]


@pytest.mark.native
def test_sum_of_squares() -> None:
    import raumlot_native

    assert raumlot_native.sum_of_squares([1.0, 2.0, 3.0]) == 14.0
    assert raumlot_native.sum_of_squares([]) == 0.0


@pytest.mark.native
def test_plane_distances_match_numpy_reference() -> None:
    import raumlot_native

    points = [(0.0, 0.0, 0.0), (1.5, -2.0, 1.0), (0.0, 4.0, 3.25)]
    normal = (0.0, 0.0, 1.0)
    offset = 1.0

    expected = np.dot(np.asarray(points), np.asarray(normal)) - offset
    actual = np.asarray(raumlot_native.plane_distances(points, normal, offset))

    np.testing.assert_allclose(actual, expected, atol=1e-12, rtol=0.0)


@pytest.mark.native
def test_plane_distances_rejects_wrong_length_point() -> None:
    import raumlot_native

    with pytest.raises((TypeError, ValueError)):
        raumlot_native.plane_distances([(0.0, 0.0)], (0.0, 0.0, 1.0), 1.0)
