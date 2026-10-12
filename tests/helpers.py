"""Small assertion helpers shared by tests."""


def must[T](value: T | None) -> T:
    """Assert that a lookup found something, narrowing ``T | None`` to ``T``."""
    assert value is not None, "expected a value, got None"
    return value
