"""Tests for PSIPWebhookView."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from django.test import Client
from django.test import RequestFactory
from pydantic import SecretStr

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy
from hatchup_psip.django.client import get_default_dispatcher
from hatchup_psip.django.views import PSIPWebhookView
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.webhooks.dispatcher import WebhookDispatcher

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
TX_DETAIL_URL = f"https://test.example.com/api/v1/transactions/{EVENT_PAYLOAD['transaction_id']}"
WEBHOOK_PATH = "/psip/webhook/"


# --------------------------------------------------------------------------- #
# Default singleton wiring (settings.PSIP-backed)
# --------------------------------------------------------------------------- #


@pytest.fixture
def http_client() -> Client:
    return Client()


def test_post_valid_event_returns_200(http_client: Client) -> None:
    with respx.mock:
        respx.get(TX_DETAIL_URL).mock(
            return_value=httpx.Response(200, json={"data": SERVER_TX, "status": "ok", "message": ""}),
        )
        response = http_client.post(
            WEBHOOK_PATH,
            data=json.dumps(EVENT_PAYLOAD),
            content_type="application/json",
        )
    assert response.status_code == 200


def test_post_invalid_payload_returns_400(http_client: Client) -> None:
    response = http_client.post(WEBHOOK_PATH, data=b"<html>not json</html>", content_type="application/json")
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body


def test_post_missing_field_returns_400(http_client: Client) -> None:
    bad = {**EVENT_PAYLOAD}
    del bad["transaction_id"]
    response = http_client.post(WEBHOOK_PATH, data=json.dumps(bad), content_type="application/json")
    assert response.status_code == 400


def test_post_with_404_from_server_returns_403(http_client: Client) -> None:
    """Forgery: server doesn't know the transaction the webhook claims."""
    with respx.mock:
        respx.get(TX_DETAIL_URL).mock(
            return_value=httpx.Response(
                404,
                json={"data": None, "status": "failure", "message": "not found"},
            ),
        )
        response = http_client.post(
            WEBHOOK_PATH,
            data=json.dumps(EVENT_PAYLOAD),
            content_type="application/json",
        )
    assert response.status_code == 403


def test_post_with_amount_mismatch_returns_403(http_client: Client) -> None:
    with respx.mock:
        respx.get(TX_DETAIL_URL).mock(
            return_value=httpx.Response(
                200,
                json={"data": SERVER_TX | {"amount": "100.00"}, "status": "ok", "message": ""},
            ),
        )
        response = http_client.post(
            WEBHOOK_PATH,
            data=json.dumps(EVENT_PAYLOAD),
            content_type="application/json",
        )
    assert response.status_code == 403


def test_get_returns_method_not_allowed(http_client: Client) -> None:
    response = http_client.get(WEBHOOK_PATH)
    assert response.status_code == 405


def test_csrf_exempt(http_client: Client) -> None:
    """Without csrf_exempt, the test client's enforce_csrf_checks=True path would 403.

    Note: Django's test Client defaults to enforce_csrf_checks=False, so we
    use a client with checks enabled to prove the decorator is in effect.
    """
    enforced = Client(enforce_csrf_checks=True)
    response = enforced.post(WEBHOOK_PATH, data=b"not json", content_type="application/json")
    # Without csrf_exempt this would be 403; we got 400 from the parser, so CSRF was bypassed.
    assert response.status_code == 400


def test_handler_runs_when_dispatcher_has_one(http_client: Client) -> None:
    received: list[PaymentCompletedEvent] = []
    dispatcher = get_default_dispatcher()

    @dispatcher.on("payment.completed")
    def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    with respx.mock:
        respx.get(TX_DETAIL_URL).mock(
            return_value=httpx.Response(200, json={"data": SERVER_TX, "status": "ok", "message": ""}),
        )
        response = http_client.post(
            WEBHOOK_PATH,
            data=json.dumps(EVENT_PAYLOAD),
            content_type="application/json",
        )

    assert response.status_code == 200
    assert len(received) == 1
    assert received[0].order_id == "ord_1"


# --------------------------------------------------------------------------- #
# Explicit injection via as_view(client=..., dispatcher=...) — multi-tenant path
# --------------------------------------------------------------------------- #


def _explicit_setup() -> tuple[PaymentServiceClient, WebhookDispatcher]:
    cfg = PSIPConfig(
        api_key=SecretStr("hp_explicit_test_key"),
        base_url="https://other.example.com/api/v1/",
        retry=RetryPolicy(max_retries=0, backoff_factor=0),
    )
    client = PaymentServiceClient(cfg)
    dispatcher = WebhookDispatcher(verifier=client.webhooks.verify_event)
    return client, dispatcher


def test_explicit_client_and_dispatcher_via_request_factory() -> None:
    """Direct view invocation — proves as_view(client=..., dispatcher=...) wires through."""
    client, dispatcher = _explicit_setup()
    received: list[PaymentCompletedEvent] = []

    @dispatcher.on("payment.completed")
    def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    factory = RequestFactory()
    view = PSIPWebhookView.as_view(client=client, dispatcher=dispatcher)
    other_tx_url = f"https://other.example.com/api/v1/transactions/{EVENT_PAYLOAD['transaction_id']}"

    try:
        with respx.mock:
            respx.get(other_tx_url).mock(
                return_value=httpx.Response(200, json={"data": SERVER_TX, "status": "ok", "message": ""}),
            )
            request = factory.post(
                "/ignored/",
                data=json.dumps(EVENT_PAYLOAD),
                content_type="application/json",
            )
            response = view(request)
    finally:
        client.close()

    assert response.status_code == 200
    assert len(received) == 1


def test_verify_false_skips_server_roundtrip() -> None:
    """A view configured with verify=False should not hit the server."""
    client, dispatcher = _explicit_setup()
    factory = RequestFactory()
    view = PSIPWebhookView.as_view(client=client, dispatcher=dispatcher, verify=False)

    try:
        with respx.mock:
            # No respx route registered — if the view called transactions.get, this
            # would raise a "no matching route" error.
            request = factory.post(
                "/ignored/",
                data=json.dumps(EVENT_PAYLOAD),
                content_type="application/json",
            )
            response = view(request)
    finally:
        client.close()

    assert response.status_code == 200
