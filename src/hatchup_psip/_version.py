"""Single source of truth for the SDK version.

Derived at import time from the installed distribution metadata so future
releases only need to bump ``pyproject.toml`` — no second place to update.
The ``PackageNotFoundError`` fallback covers source-checkout usage where
the package hasn't been installed (e.g. ``python -c`` from the repo root
without ``uv sync`` first); test/CI environments always install the
package so they take the metadata branch.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("hatchup-payment-service-integration")
except PackageNotFoundError:  # pragma: no cover - source-checkout fallback
    __version__ = "0.0.0+unknown"
