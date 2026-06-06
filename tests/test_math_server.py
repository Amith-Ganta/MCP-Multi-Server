"""Unit tests for the math MCP server tools."""

import math

import math_server as m
import pytest


def test_add_and_subtract():
    assert m.add(2, 3) == 5
    assert m.subtract(10, 4) == 6


def test_multiply_and_divide():
    assert m.multiply(6, 7) == 42
    assert m.divide(9, 3) == 3


def test_divide_by_zero_raises():
    with pytest.raises(ValueError):
        m.divide(1, 0)


def test_factorial_and_gcd_and_lcm():
    assert m.factorial(6) == 720
    assert m.gcd(48, 18) == 6
    assert m.lcm(4, 6) == 12


def test_factorial_negative_raises():
    with pytest.raises(ValueError):
        m.factorial(-1)


def test_powers_and_roots():
    assert m.power(2, 10) == 1024
    assert m.square_root(16) == 4
    assert m.nth_root(27, 3) == pytest.approx(3.0)


def test_square_root_negative_raises():
    with pytest.raises(ValueError):
        m.square_root(-1)


def test_logarithm_and_exp():
    assert m.logarithm(math.e) == pytest.approx(1.0)
    assert m.exp(0) == pytest.approx(1.0)


def test_trigonometry_in_degrees():
    assert m.sin(90) == pytest.approx(1.0)
    assert m.cos(0) == pytest.approx(1.0)


def test_aggregates():
    assert m.mean([2, 4, 6]) == pytest.approx(4.0)
    assert m.percentage(25, 200) == pytest.approx(12.5)


def test_percentage_zero_whole_raises():
    with pytest.raises(ValueError):
        m.percentage(1, 0)
