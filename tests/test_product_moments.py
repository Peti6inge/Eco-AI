from __future__ import annotations

from math import isclose

from app.estimate import product_moments


def test_product_moments_plan_example():
    mean, sigma = product_moments(10.0, 2.0, 1.0, 0.2)
    assert isclose(mean, 10.0)
    assert isclose(sigma, (10**2 * 0.2**2 + 1**2 * 2**2 + 0.2**2 * 2**2) ** 0.5)
    # Plan V1 : ≈ 2,83 (√8,16 ≈ 2,856).
    assert isclose(sigma, 2.83, rel_tol=0, abs_tol=0.03)


def test_independent_zero_sigma():
    mean, sigma = product_moments(4.0, 0.0, 3.0, 0.0)
    assert mean == 12.0
    assert sigma == 0.0
