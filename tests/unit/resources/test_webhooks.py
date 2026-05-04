"""Tests for WebhooksResource (the client.webhooks composition)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.models.webhook import PaymentCompletedEvent

DETAIL_BASE = "https://test.example.com/api/v1/transactions/"

EVENT_PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}

SERVER_TX = {
    "id": "11111111-1111-1111-1111-111111111111",
    "order_id": "ord_1",
    "amount": "9.99",
    "currency": "usd",
    "status": "succeeded",
    "is_test": True,
    "verified_at": "2026-05-01T12:30:00Z",
    "created_at": "2026-05-01T12:00:00Z",
    "stripe_checkout_session_id": "cs_xxx",
}


def test_parse_returns_event(psip_client: PaymentServiceClient) -> None:
    event = psip_client.webhooks.parse(json.dumps(EVENT_PAYLOAD).encode())
    assert isinstance(event, PaymentCompletedEvent)
    assert event.order_id == "ord_1"


def test_parse_invalid_body_raises_webhook_validation_error(psip_client: PaymentServiceClient) -> None:
    with pytest.raises(PSIPWebhookValidationError):
        psip_client.webhooks.parse(b"not json")


def test_verify_event_round_trips_server(psip_client: PaymentServiceClient) -> None:
    event = PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)
    with respx.mock:
        respx.get(DETAIL_BASE + str(event.transaction_id)).mock(
            return_value=httpx.Response(
                200,
                json={"data": SERVER_TX, "status": "ok", "message": ""},
            ),
        )
        tx = psip_client.webhooks.verify_event(event)
    assert tx.order_id == event.order_id
    assert tx.status == "succeeded"


def test_verify_event_raises_forgery_on_mismatch(psip_client: PaymentServiceClient) -> None:
    event = PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)
    with respx.mock:
        respx.get(DETAIL_BASE + str(event.transaction_id)).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": SERVER_TX | {"amount": "100.00"},
                    "status": "ok",
                    "message": "",
                },
            ),
        )
        with pytest.raises(PSIPWebhookForgeryError, match="amount"):
            psip_client.webhooks.verify_event(event)


def test_verify_event_raises_forgery_on_404(psip_client: PaymentServiceClient) -> None:
    event = PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)
    with respx.mock:
        respx.get(DETAIL_BASE + str(event.transaction_id)).mock(
            return_value=httpx.Response(
                404,
                json={"data": None, "status": "failure", "message": "not found"},
            ),
        )
        with pytest.raises(PSIPWebhookForgeryError, match="unknown transaction"):
            psip_client.webhooks.verify_event(event)
