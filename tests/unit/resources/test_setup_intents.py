"""Tests for SetupIntents + PaymentMethod.detach (chunk 4.1)."""

from __future__ import annotations

import json

import httpx
import respx

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.models.setup_intent import DetachedPaymentMethod
from hatchup_psip.models.setup_intent import SetupIntent

BASE = "https://test.example.com/api/v1"
SI_URL = f"{BASE}/setup-intents"
SI_DETAIL = f"{BASE}/setup-intents/seti_test"


def _envelope(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


def _si_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "seti_test",
        "object": "setup_intent",
        "status": "requires_payment_method",
        "client_secret": "seti_test_secret",
        "customer": None,
        "payment_method": None,
        "usage": "off_session",
        "metadata": {},
        "is_test": True,
        "last_error_message": None,
        "cancellation_reason": None,
        "created_at": "2026-05-09T12:00:00Z",
    }
    base.update(overrides)
    return base


def test_create_setup_intent_default_usage(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(SI_URL).mock(
            return_value=httpx.Response(200, json=_envelope(_si_payload())),
        )
        si = psip_client.setup_intents.create(customer="cus_test")

    assert isinstance(si, SetupIntent)
    sent = json.loads(route.calls.last.request.content)
    assert sent["customer"] == "cus_test"
    assert sent["usage"] == "off_session"
    assert sent["confirm"] is False


def test_confirm_setup_intent_passes_payment_method(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(f"{SI_DETAIL}/confirm").mock(
            return_value=httpx.Response(200, json=_envelope(_si_payload(status="succeeded"))),
        )
        psip_client.setup_intents.confirm("seti_test", payment_method="pm_card_visa")

    sent = json.loads(route.calls.last.request.content)
    assert sent == {"payment_method": "pm_card_visa"}


def test_cancel_setup_intent(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.post(f"{SI_DETAIL}/cancel").mock(
            return_value=httpx.Response(200, json=_envelope(_si_payload(status="canceled"))),
        )
        si = psip_client.setup_intents.cancel("seti_test")
    assert si.status == "canceled"


def test_payment_method_detach(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.post(f"{BASE}/payment-methods/pm_card_visa/detach").mock(
            return_value=httpx.Response(
                200,
                json=_envelope({"id": "pm_card_visa", "detached": True}),
            ),
        )
        result = psip_client.payment_methods.detach("pm_card_visa")
    assert isinstance(result, DetachedPaymentMethod)
    assert result.detached is True
