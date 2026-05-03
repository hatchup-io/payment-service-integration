"""Tests for webhook.py models."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from hatchup_psip.models.webhook import PaymentCompletedEvent

PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}


def test_parses_server_payload() -> None:
    event = PaymentCompletedEvent.model_validate(PAYLOAD)
    assert event.order_id == "ord_1"
    assert event.amount == Decimal("9.99")
    assert event.transaction_id == UUID("11111111-1111-1111-1111-111111111111")


def test_received_at_is_stamped_at_parse_time() -> None:
    before = datetime.now(UTC)
    event = PaymentCompletedEvent.model_validate(PAYLOAD)
    after = datetime.now(UTC)
    assert before - timedelta(seconds=1) <= event.received_at <= after + timedelta(seconds=1)


def test_received_at_can_be_overridden_for_replay() -> None:
    fixed = datetime(2026, 1, 1, tzinfo=UTC)
    event = PaymentCompletedEvent.model_validate(PAYLOAD | {"received_at": fixed})
    assert event.received_at == fixed


def test_status_must_be_completed() -> None:
    with pytest.raises(ValidationError):
        PaymentCompletedEvent.model_validate(PAYLOAD | {"status": "failed"})


def test_invalid_uuid_rejected() -> None:
    with pytest.raises(ValidationError):
        PaymentCompletedEvent.model_validate(PAYLOAD | {"transaction_id": "not-a-uuid"})


def test_extra_fields_ignored() -> None:
    event = PaymentCompletedEvent.model_validate(PAYLOAD | {"event_type": "completed"})
    assert not hasattr(event, "event_type")


def test_is_frozen() -> None:
    event = PaymentCompletedEvent.model_validate(PAYLOAD)
    with pytest.raises(ValidationError):
        event.order_id = "ord_2"  # type: ignore[misc]
