"""Tests for the SDK exception hierarchy."""

from __future__ import annotations

import pytest

from hatchup_psip.exceptions import PSIPAPIError
from hatchup_psip.exceptions import PSIPAuthError
from hatchup_psip.exceptions import PSIPError
from hatchup_psip.exceptions import PSIPNetworkError
from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.exceptions import PSIPServerError
from hatchup_psip.exceptions import PSIPValidationError
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.exceptions import PSIPWebhookValidationError


@pytest.mark.parametrize(
    "exc_cls",
    [
        PSIPNetworkError,
        PSIPProtocolError,
        PSIPAPIError,
        PSIPAuthError,
        PSIPValidationError,
        PSIPNotFoundError,
        PSIPServerError,
        PSIPWebhookValidationError,
        PSIPWebhookForgeryError,
    ],
)
def test_all_subclasses_inherit_from_psip_error(exc_cls: type[PSIPError]) -> None:
    assert issubclass(exc_cls, PSIPError)


@pytest.mark.parametrize("exc_cls", [PSIPWebhookValidationError, PSIPWebhookForgeryError])
def test_webhook_errors_inherit_from_psip_protocol_error(exc_cls: type[PSIPProtocolError]) -> None:
    assert issubclass(exc_cls, PSIPProtocolError)


@pytest.mark.parametrize(
    "exc_cls",
    [PSIPAuthError, PSIPValidationError, PSIPNotFoundError, PSIPServerError],
)
def test_specific_api_errors_inherit_from_psip_api_error(exc_cls: type[PSIPAPIError]) -> None:
    assert issubclass(exc_cls, PSIPAPIError)


def test_psip_api_error_carries_payload() -> None:
    err = PSIPAPIError(
        status_code=400,
        message="amount must be positive",
        raw={"data": None, "status": "failure", "message": "amount must be positive"},
        request_id="req_abc",
    )
    assert err.status_code == 400
    assert err.message == "amount must be positive"
    assert err.raw == {"data": None, "status": "failure", "message": "amount must be positive"}
    assert err.request_id == "req_abc"
    assert "[400]" in str(err)
    assert "amount must be positive" in str(err)


def test_psip_api_error_defaults_raw_and_request_id() -> None:
    err = PSIPAPIError(status_code=500, message="boom")
    assert err.raw == {}
    assert err.request_id is None


def test_network_error_message_passthrough() -> None:
    err = PSIPNetworkError("connection refused")
    assert "connection refused" in str(err)


def test_protocol_error_is_distinct_from_api_error() -> None:
    err = PSIPProtocolError("envelope missing 'data' field")
    assert isinstance(err, PSIPError)
    assert not isinstance(err, PSIPAPIError)
