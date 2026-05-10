"""Tests for WebhookEndpointsResource (chunk 4.2)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.models.webhook_endpoint import WebhookEndpoint
from hatchup_psip.models.webhook_endpoint import WebhookEndpointPage

BASE = "https://test.example.com/api/v1"
WE_URL = f"{BASE}/webhook-endpoints"
ENDPOINT_ID = "11111111-1111-1111-1111-111111111111"
WE_DETAIL = f"{WE_URL}/{ENDPOINT_ID}"


def _envelope(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


def _endpoint_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": ENDPOINT_ID,
        "object": "webhook_endpoint",
        "url": "https://app.example.com/hooks/psip",
        "description": "main",
        "subscribed_events": ["payment_intent.succeeded"],
        "is_active": True,
        "signing_secret": "",
        "created_at": "2026-05-09T12:00:00Z",
        "updated_at": "2026-05-09T12:00:00Z",
    }
    base.update(overrides)
    return base


def test_create_returns_signing_secret(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(WE_URL).mock(
            return_value=httpx.Response(
                200,
                json=_envelope(_endpoint_payload(signing_secret="whsec_abc123")),
            ),
        )
        endpoint = psip_client.webhook_endpoints.create(
            url="https://app.example.com/hooks/psip",
            subscribed_events=["payment_intent.succeeded"],
            description="main",
        )
    assert isinstance(endpoint, WebhookEndpoint)
    assert endpoint.signing_secret == "whsec_abc123"

    sent = json.loads(route.calls.last.request.content)
    assert sent["url"].startswith("https://app.example.com/hooks/psip")
    assert sent["subscribed_events"] == ["payment_intent.succeeded"]


def test_create_rejects_empty_subscribed_events(psip_client: PaymentServiceClient) -> None:
    with pytest.raises(ValidationError):
        psip_client.webhook_endpoints.create(
            url="https://app.example.com/hook",
            subscribed_events=[],
        )


def test_retrieve_returns_blank_secret(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.get(WE_DETAIL).mock(
            return_value=httpx.Response(200, json=_envelope(_endpoint_payload())),
        )
        endpoint = psip_client.webhook_endpoints.retrieve(ENDPOINT_ID)
    assert endpoint.signing_secret == ""


def test_update_partial(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(WE_DETAIL).mock(
            return_value=httpx.Response(200, json=_envelope(_endpoint_payload(is_active=False))),
        )
        psip_client.webhook_endpoints.update(ENDPOINT_ID, is_active=False)
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"is_active": False}


def test_rotate_secret_returns_new_value(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.post(f"{WE_DETAIL}/rotate-secret").mock(
            return_value=httpx.Response(
                200,
                json=_envelope(_endpoint_payload(signing_secret="whsec_new")),
            ),
        )
        endpoint = psip_client.webhook_endpoints.rotate_secret(ENDPOINT_ID)
    assert endpoint.signing_secret == "whsec_new"


def test_list_filters_active(psip_client: PaymentServiceClient) -> None:
    page = {"results": [_endpoint_payload()], "page": 1, "page_size": 20, "count": 1}
    with respx.mock:
        route = respx.get(WE_URL).mock(return_value=httpx.Response(200, json=_envelope(page)))
        result = psip_client.webhook_endpoints.list(active=True)
    assert isinstance(result, WebhookEndpointPage)
    params = dict(route.calls.last.request.url.params)
    assert params["active"] == "true"


def test_delete_returns_envelope_data(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.delete(WE_DETAIL).mock(
            return_value=httpx.Response(
                200,
                json=_envelope({"id": ENDPOINT_ID, "deleted": True}),
            ),
        )
        data = psip_client.webhook_endpoints.delete(ENDPOINT_ID)
    assert data == {"id": ENDPOINT_ID, "deleted": True}
