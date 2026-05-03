"""Tests for the generic ApiEnvelope model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hatchup_psip.models.envelope import ApiEnvelope
from hatchup_psip.models.payment import PaymentCreateResponse


def test_parses_ok_envelope_with_typed_data() -> None:
    payload = {
        "data": {"payment_url": "https://x.test/cb", "session_id": "cs_1", "order_id": "ord_1"},
        "status": "ok",
        "message": "",
    }
    env = ApiEnvelope[PaymentCreateResponse].model_validate(payload)
    assert env.is_ok
    assert env.data.session_id == "cs_1"


def test_parses_failure_envelope() -> None:
    env = ApiEnvelope[dict].model_validate({"data": {}, "status": "failure", "message": "boom"})
    assert not env.is_ok
    assert env.message == "boom"


def test_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        ApiEnvelope[dict].model_validate({"data": {}, "status": "weird", "message": ""})


def test_message_defaults_to_empty_string() -> None:
    env = ApiEnvelope[dict].model_validate({"data": {}, "status": "ok"})
    assert env.message == ""


def test_extra_fields_are_ignored() -> None:
    """Server adding new envelope fields must not break older SDKs."""
    env = ApiEnvelope[dict].model_validate(
        {"data": {}, "status": "ok", "message": "", "trace_id": "abc"},
    )
    assert not hasattr(env, "trace_id")
