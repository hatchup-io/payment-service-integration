"""Fixtures for live-server integration tests.

All fixtures here pull configuration from ``PSIP_INTEGRATION_*`` env vars.
Tests are skipped at fixture-resolution time when env vars are unset, so
running ``pytest -m live`` without configuration produces clean
"skipped" output rather than a sea of failures.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.config import PSIPConfig

ENV_BASE_URL = "PSIP_INTEGRATION_BASE_URL"
ENV_API_KEY = "PSIP_INTEGRATION_API_KEY"
ENV_SUCCESS = "PSIP_INTEGRATION_SUCCESS_URL"
ENV_FAILURE = "PSIP_INTEGRATION_FAILURE_URL"


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set — see tests/integration/README.md")
    return value


@pytest.fixture(scope="session")
def live_config() -> PSIPConfig:
    return PSIPConfig(
        api_key=SecretStr(_require(ENV_API_KEY)),
        base_url=_require(ENV_BASE_URL),
        timeout=30.0,
    )


@pytest.fixture
def live_client(live_config: PSIPConfig) -> Iterator[PaymentServiceClient]:
    with PaymentServiceClient(live_config) as client:
        yield client


@pytest.fixture
def webhooks() -> tuple[str, str]:
    return _require(ENV_SUCCESS), _require(ENV_FAILURE)
