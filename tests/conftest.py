"""Shared fixtures for the SDK test suite."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy

BASE_URL = "https://test.example.com/api/v1/"


@pytest.fixture
def psip_config() -> PSIPConfig:
    """A PSIPConfig with retries disabled — most tests assert on a single response."""
    return PSIPConfig(
        api_key=SecretStr("hp_test_key_12345"),
        base_url=BASE_URL,
        retry=RetryPolicy(max_retries=0, backoff_factor=0),
    )


@pytest.fixture
def psip_client(psip_config: PSIPConfig) -> Iterator[PaymentServiceClient]:
    with PaymentServiceClient(psip_config) as client:
        yield client
