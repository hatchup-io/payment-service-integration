"""Smoke test confirming the package imports and exposes its version."""

from hatchup_psip import __version__


def test_version_is_set() -> None:
    assert __version__
    assert isinstance(__version__, str)
