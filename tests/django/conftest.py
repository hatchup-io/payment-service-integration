"""Fixtures shared by the Django-integration test suite."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator

import pytest

from hatchup_psip.django.client import get_default_client
from hatchup_psip.django.client import get_default_dispatcher


@pytest.fixture(autouse=True)
def _reset_default_singletons() -> Iterator[None]:
    """Clear the cached default client + dispatcher between tests.

    Tests register handlers on the default dispatcher and assert
    ``httpx.Client`` state on the default client; persisting state
    across tests would cause flaky cross-talk.
    """
    get_default_client.cache_clear()
    get_default_dispatcher.cache_clear()
    yield
    # Best-effort close — the dispatcher cache holds no resources.
    with contextlib.suppress(Exception):
        get_default_client().close()
    get_default_client.cache_clear()
    get_default_dispatcher.cache_clear()
