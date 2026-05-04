"""Tests for parse_payment_completed."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

import pytest

from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.webhooks.parser import parse_payment_completed

PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}


def test_parses_dict_payload() -> None:
    event = parse_payment_completed(PAYLOAD)
    assert event.order_id == "ord_1"
    assert event.amount == Decimal("9.99")
    assert event.transaction_id == UUID("11111111-1111-1111-1111-111111111111")


def test_parses_str_payload() -> None:
    event = parse_payment_completed(json.dumps(PAYLOAD))
    assert event.order_id == "ord_1"


def test_parses_bytes_payload() -> None:
    event = parse_payment_completed(json.dumps(PAYLOAD).encode())
    assert event.order_id == "ord_1"


def test_invalid_json_raises() -> None:
    with pytest.raises(PSIPWebhookValidationError, match="not valid JSON"):
        parse_payment_completed(b"<html>not json</html>")


def test_non_object_json_raises() -> None:
    with pytest.raises(PSIPWebhookValidationError, match="JSON object"):
        parse_payment_completed(b"[1, 2, 3]")


def test_missing_field_raises() -> None:
    bad = {**PAYLOAD}
    del bad["transaction_id"]
    with pytest.raises(PSIPWebhookValidationError, match="PaymentCompletedEvent"):
        parse_payment_completed(bad)


def test_invalid_uuid_raises() -> None:
    with pytest.raises(PSIPWebhookValidationError):
        parse_payment_completed(PAYLOAD | {"transaction_id": "not-a-uuid"})


def test_unknown_status_raises() -> None:
    with pytest.raises(PSIPWebhookValidationError):
        parse_payment_completed(PAYLOAD | {"status": "failed"})
