"""Tests for SubscriptionsResource (chunk 4.2)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.models.subscription import Subscription
from hatchup_psip.models.subscription import SubscriptionPage

BASE = "https://test.example.com/api/v1"
SUB_URL = f"{BASE}/subscriptions"
SUB_DETAIL = f"{BASE}/subscriptions/sub_test"


def _envelope(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


def _sub_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "sub_test",
        "object": "subscription",
        "customer": "cus_test",
        "status": "active",
        "items": [
            {"stripe_subscription_item_id": "si_x", "price_id": "price_x", "quantity": 1},
        ],
        "current_period_start": "2026-05-01T00:00:00Z",
        "current_period_end": "2026-06-01T00:00:00Z",
        "trial_start": None,
        "trial_end": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "cancellation_reason": None,
        "default_payment_method": None,
        "latest_invoice": None,
        "metadata": {},
        "is_test": True,
        "created_at": "2026-05-01T00:00:00Z",
    }
    base.update(overrides)
    return base


class TestCreate:
    def test_create_with_trial(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(SUB_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_sub_payload(status="trialing"))),
            )
            sub = psip_client.subscriptions.create(
                customer="cus_test",
                items=[{"price": "price_x", "quantity": 1}],
                trial_period_days=14,
            )
        assert isinstance(sub, Subscription)
        assert sub.status == "trialing"

        sent = json.loads(route.calls.last.request.content)
        assert sent["customer"] == "cus_test"
        assert sent["items"] == [{"price": "price_x", "quantity": 1, "deleted": False}]
        assert sent["trial_period_days"] == 14

    def test_create_rejects_empty_items(self, psip_client: PaymentServiceClient) -> None:
        with pytest.raises(ValidationError):
            psip_client.subscriptions.create(customer="cus_test", items=[])

    def test_item_without_id_or_price_rejected(self, psip_client: PaymentServiceClient) -> None:
        with pytest.raises(ValidationError):
            psip_client.subscriptions.create(
                customer="cus_test",
                items=[{"quantity": 1}],  # missing both id and price
            )


class TestUpdate:
    def test_update_with_explicit_proration(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(SUB_DETAIL).mock(
                return_value=httpx.Response(200, json=_envelope(_sub_payload())),
            )
            psip_client.subscriptions.update(
                "sub_test",
                items=[{"id": "si_x", "quantity": 5}],
                proration_behavior="none",
            )

        sent = json.loads(route.calls.last.request.content)
        assert sent["proration_behavior"] == "none"
        assert sent["items"][0]["id"] == "si_x"

    def test_update_omits_proration_falls_back_server_side(
        self,
        psip_client: PaymentServiceClient,
    ) -> None:
        # SDK should NOT inject a default proration_behavior — the server
        # reads ``user.default_proration_behavior`` when the field is
        # omitted (decision #6).
        with respx.mock:
            route = respx.post(SUB_DETAIL).mock(
                return_value=httpx.Response(200, json=_envelope(_sub_payload())),
            )
            psip_client.subscriptions.update("sub_test", cancel_at_period_end=True)

        sent = json.loads(route.calls.last.request.content)
        assert "proration_behavior" not in sent
        assert sent == {"cancel_at_period_end": True}


class TestCancelResume:
    def test_cancel_at_period_end(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(f"{SUB_DETAIL}/cancel").mock(
                return_value=httpx.Response(
                    200,
                    json=_envelope(_sub_payload(cancel_at_period_end=True)),
                ),
            )
            psip_client.subscriptions.cancel(
                "sub_test",
                at_period_end=True,
                cancellation_reason="too_expensive",
            )
        sent = json.loads(route.calls.last.request.content)
        assert sent["at_period_end"] is True
        assert sent["cancellation_reason"] == "too_expensive"

    def test_resume_no_body(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(f"{SUB_DETAIL}/resume").mock(
                return_value=httpx.Response(200, json=_envelope(_sub_payload())),
            )
            psip_client.subscriptions.resume("sub_test")
        # Resource sends no body on resume.
        assert route.calls.last.request.content in (b"", b"null")


class TestList:
    def test_list_filters_by_customer_and_status(self, psip_client: PaymentServiceClient) -> None:
        page = {"results": [_sub_payload()], "page": 1, "page_size": 20, "count": 1}
        with respx.mock:
            route = respx.get(SUB_URL).mock(return_value=httpx.Response(200, json=_envelope(page)))
            result = psip_client.subscriptions.list(customer="cus_test", status="active")
        assert isinstance(result, SubscriptionPage)
        params = dict(route.calls.last.request.url.params)
        assert params == {"page": "1", "page_size": "20", "customer": "cus_test", "status": "active"}
