"""Tests for PaymentIntentsResource (chunk 4.1)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.models.payment_intent import PaymentIntent
from hatchup_psip.models.payment_intent import PaymentIntentPage

BASE = "https://test.example.com/api/v1"
PI_URL = f"{BASE}/payment-intents"
PI_DETAIL = f"{BASE}/payment-intents/pi_test"


def _envelope(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


def _pi_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "pi_test",
        "object": "payment_intent",
        "amount": "25.99",
        "currency": "usd",
        "status": "requires_payment_method",
        "client_secret": "pi_test_secret",
        "customer": None,
        "payment_method": None,
        "payment_method_details": {},
        "metadata": {},
        "is_test": True,
        "last_error_message": None,
        "cancellation_reason": None,
        "created_at": "2026-05-09T12:00:00Z",
    }
    base.update(overrides)
    return base


class TestCreate:
    def test_happy_path_forwards_amount_in_decimal(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(PI_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_pi_payload())),
            )
            pi = psip_client.payment_intents.create(amount="25.99", currency="USD")
        assert isinstance(pi, PaymentIntent)
        assert pi.client_secret == "pi_test_secret"

        sent = json.loads(route.calls.last.request.content)
        # Currency is lowercased by the request validator.
        assert sent["currency"] == "usd"
        assert sent["amount"] == "25.99"
        assert sent["capture_method"] == "automatic"

    def test_negative_amount_raises_validation_error(self, psip_client: PaymentServiceClient) -> None:
        with pytest.raises(ValidationError):
            psip_client.payment_intents.create(amount="-1.00")


class TestLifecycle:
    def test_retrieve(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.get(PI_DETAIL).mock(
                return_value=httpx.Response(200, json=_envelope(_pi_payload(status="succeeded"))),
            )
            pi = psip_client.payment_intents.retrieve("pi_test")
        assert pi.status == "succeeded"

    def test_confirm_passes_payment_method(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(f"{PI_DETAIL}/confirm").mock(
                return_value=httpx.Response(200, json=_envelope(_pi_payload(status="processing"))),
            )
            psip_client.payment_intents.confirm("pi_test", payment_method="pm_card_visa")

        sent = json.loads(route.calls.last.request.content)
        assert sent == {"payment_method": "pm_card_visa"}

    def test_capture_with_partial_amount(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(f"{PI_DETAIL}/capture").mock(
                return_value=httpx.Response(200, json=_envelope(_pi_payload(status="succeeded"))),
            )
            psip_client.payment_intents.capture("pi_test", amount_to_capture="10.00")

        sent = json.loads(route.calls.last.request.content)
        assert sent == {"amount_to_capture": "10.00"}

    def test_capture_without_amount_sends_empty_body(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(f"{PI_DETAIL}/capture").mock(
                return_value=httpx.Response(200, json=_envelope(_pi_payload(status="succeeded"))),
            )
            psip_client.payment_intents.capture("pi_test")

        sent = json.loads(route.calls.last.request.content)
        assert sent == {}

    def test_cancel_with_reason(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(f"{PI_DETAIL}/cancel").mock(
                return_value=httpx.Response(200, json=_envelope(_pi_payload(status="canceled"))),
            )
            psip_client.payment_intents.cancel("pi_test", cancellation_reason="requested_by_customer")

        sent = json.loads(route.calls.last.request.content)
        assert sent == {"cancellation_reason": "requested_by_customer"}


class TestList:
    def test_list_filters_by_customer(self, psip_client: PaymentServiceClient) -> None:
        page = {"results": [_pi_payload()], "page": 1, "page_size": 20, "count": 1}
        with respx.mock:
            route = respx.get(PI_URL).mock(return_value=httpx.Response(200, json=_envelope(page)))
            result = psip_client.payment_intents.list(customer="cus_x", status="succeeded")

        assert isinstance(result, PaymentIntentPage)
        params = dict(route.calls.last.request.url.params)
        assert params == {"page": "1", "page_size": "20", "customer": "cus_x", "status": "succeeded"}
