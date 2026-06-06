"""Math MCP server.

A local Model Context Protocol (MCP) server exposing 18 mathematical
operations over FastMCP — arithmetic, powers/roots, combinatorics, logarithms,
trigonometry, and simple aggregates.

The ``MultiServerMCPClient`` configured in ``mcp_config.py`` (used by both
``cli.py`` and ``app.py``) launches this file over STDIO, so it runs with the
STDIO transport by default (see ``__main__``).

Run standalone for a quick check::

    uv run fastmcp run servers/math_server.py
"""

import math

from fastmcp import FastMCP

mcp = FastMCP("MathServer")


# ---------------------------------------------------------------------------
# Basic arithmetic
# ---------------------------------------------------------------------------
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return their sum."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a and return the difference."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b. Raises an error on division by zero."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


@mcp.tool()
def modulo(a: float, b: float) -> float:
    """Return the remainder of a divided by b (a mod b)."""
    if b == 0:
        raise ValueError("Modulo by zero is not allowed.")
    return a % b


# ---------------------------------------------------------------------------
# Powers and roots
# ---------------------------------------------------------------------------
@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent (base ** exponent)."""
    return base ** exponent


@mcp.tool()
def square_root(x: float) -> float:
    """Return the square root of a non-negative number."""
    if x < 0:
        raise ValueError("Cannot take the square root of a negative number.")
    return math.sqrt(x)


@mcp.tool()
def nth_root(x: float, n: float) -> float:
    """Return the nth root of x (x ** (1/n))."""
    if n == 0:
        raise ValueError("The root degree n cannot be zero.")
    if x < 0 and int(n) % 2 == 0:
        raise ValueError("Even root of a negative number is not real.")
    return math.copysign(abs(x) ** (1.0 / n), x)


# ---------------------------------------------------------------------------
# Combinatorics & number theory
# ---------------------------------------------------------------------------
@mcp.tool()
def factorial(n: int) -> int:
    """Return the factorial of a non-negative integer n (n!)."""
    if n < 0:
        raise ValueError("Factorial is only defined for non-negative integers.")
    return math.factorial(n)


@mcp.tool()
def gcd(a: int, b: int) -> int:
    """Return the greatest common divisor of two integers."""
    return math.gcd(a, b)


@mcp.tool()
def lcm(a: int, b: int) -> int:
    """Return the least common multiple of two integers."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // math.gcd(a, b)


# ---------------------------------------------------------------------------
# Logarithms & exponentials
# ---------------------------------------------------------------------------
@mcp.tool()
def logarithm(x: float, base: float = math.e) -> float:
    """Return the logarithm of x to the given base (natural log by default)."""
    if x <= 0:
        raise ValueError("Logarithm is only defined for positive numbers.")
    if base <= 0 or base == 1:
        raise ValueError("Logarithm base must be positive and not equal to 1.")
    return math.log(x, base)


@mcp.tool()
def exp(x: float) -> float:
    """Return e raised to the power of x."""
    return math.exp(x)


# ---------------------------------------------------------------------------
# Trigonometry (inputs in degrees for intuitive use)
# ---------------------------------------------------------------------------
@mcp.tool()
def sin(degrees: float) -> float:
    """Return the sine of an angle given in degrees."""
    return math.sin(math.radians(degrees))


@mcp.tool()
def cos(degrees: float) -> float:
    """Return the cosine of an angle given in degrees."""
    return math.cos(math.radians(degrees))


@mcp.tool()
def tan(degrees: float) -> float:
    """Return the tangent of an angle given in degrees."""
    return math.tan(math.radians(degrees))


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------
@mcp.tool()
def mean(numbers: list[float]) -> float:
    """Return the arithmetic mean (average) of a list of numbers."""
    if not numbers:
        raise ValueError("Cannot compute the mean of an empty list.")
    return sum(numbers) / len(numbers)


@mcp.tool()
def percentage(part: float, whole: float) -> float:
    """Return what percentage 'part' is of 'whole'."""
    if whole == 0:
        raise ValueError("Whole cannot be zero when computing a percentage.")
    return (part / whole) * 100.0


if __name__ == "__main__":
    # STDIO transport: this is what mcp_config.py's MultiServerMCPClient expects.
    mcp.run()
