"""Async smoke tests for the v1.0 resource pairs (chunk 4.1 + 4.2).

The async resources share their request-building / parsing helpers
with the sync counterparts (covered exhaustively in the matching
``test_*`` files). These tests prove the ``await`` path works and the
right URL/body shape lands on the wire.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import respx
from pydantic import SecretStr

from hatchup_psip.client import AsyncPaymentServiceClient
from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy
from hatchup_psip.models.customer import Customer
from hatchup_psip.models.invoice import Invoice
from hatchup_psip.models.payment_intent import PaymentIntent
from hatchup_psip.models.subscription import Subscription
from hatchup_psip.models.webhook_endpoint import WebhookEndpoint

BASE = "https://test.example.com/api/v1/"


def _env(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


_CUSTOMER = {
    "id": "cus_test",
    "object": "customer",
    "email": "x@example.com",
    "name": "",
    "phone": "",
    "description": "",
    "metadata": {},
    "is_test": True,
    "deleted_at": None,
    "created_at": "2026-05-09T12:00:00Z",
    "updated_at": "2026-05-09T12:00:00Z",
}
_PI = {
    "id": "pi_test",
    "object": "payment_intent",
    "amount": "1.00",
    "currency": "usd",
    "status": "succeeded",
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
_SUB = {
    "id": "sub_test",
    "object": "subscription",
    "customer": "cus_test",
    "status": "active",
    "items": [],
    "current_period_start": None,
    "current_period_end": None,
    "trial_start": None,
    "trial_end": None,
    "cancel_at_period_end": False,
    "canceled_at": None,
    "cancellation_reason": None,
    "default_payment_method": None,
    "latest_invoice": None,
    "metadata": {},
    "is_test": True,
    "created_at": "2026-05-09T12:00:00Z",
}
_INVOICE = {
    "id": "in_test",
    "object": "invoice",
    "customer": "cus_test",
    "subscription": None,
    "status": "paid",
    "amount_due": "1.00",
    "amount_paid": "1.00",
    "amount_remaining": "0",
    "currency": "usd",
    "period_start": None,
    "period_end": None,
    "hosted_invoice_url": None,
    "invoice_pdf": None,
    "metadata": {},
    "is_test": True,
    "paid_at": None,
    "voided_at": None,
    "created_at": "2026-05-09T12:00:00Z",
}
_ENDPOINT = {
    "id": "11111111-1111-1111-1111-111111111111",
    "object": "webhook_endpoint",
    "url": "https://app.example/h",
    "description": "",
    "subscribed_events": ["x.y"],
    "is_active": True,
    "signing_secret": "",
    "created_at": "2026-05-09T12:00:00Z",
    "updated_at": "2026-05-09T12:00:00Z",
}


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncPaymentServiceClient]:
    cfg = PSIPConfig(
        api_key=SecretStr("hp_test_key"),
        base_url=BASE,
        retry=RetryPolicy(max_retries=0, backoff_factor=0),
    )
    async with AsyncPaymentServiceClient(cfg) as client:
        yield client


async def test_async_customer_create(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        respx.post(BASE + "customers").mock(
            return_value=httpx.Response(200, json=_env(_CUSTOMER)),
        )
        customer = await async_client.customers.create(email="x@example.com")
    assert isinstance(customer, Customer)


async def test_async_payment_intent_retrieve(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        respx.get(BASE + "payment-intents/pi_test").mock(
            return_value=httpx.Response(200, json=_env(_PI)),
        )
        pi = await async_client.payment_intents.retrieve("pi_test")
    assert isinstance(pi, PaymentIntent)
    assert pi.status == "succeeded"


async def test_async_subscription_cancel_at_period_end(
    async_client: AsyncPaymentServiceClient,
) -> None:
    with respx.mock:
        respx.post(BASE + "subscriptions/sub_test/cancel").mock(
            return_value=httpx.Response(
                200,
                json=_env({**_SUB, "cancel_at_period_end": True}),
            ),
        )
        sub = await async_client.subscriptions.cancel(
            "sub_test",
            at_period_end=True,
        )
    assert isinstance(sub, Subscription)
    assert sub.cancel_at_period_end is True


async def test_async_invoice_pay(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        respx.post(BASE + "invoices/in_test/pay").mock(
            return_value=httpx.Response(200, json=_env(_INVOICE)),
        )
        inv = await async_client.invoices.pay("in_test")
    assert isinstance(inv, Invoice)


async def test_async_webhook_endpoint_rotate_secret(
    async_client: AsyncPaymentServiceClient,
) -> None:
    with respx.mock:
        respx.post(BASE + "webhook-endpoints/11111111-1111-1111-1111-111111111111/rotate-secret").mock(
            return_value=httpx.Response(
                200,
                json=_env({**_ENDPOINT, "signing_secret": "whsec_new"}),
            ),
        )
        endpoint = await async_client.webhook_endpoints.rotate_secret(
            "11111111-1111-1111-1111-111111111111",
        )
    assert isinstance(endpoint, WebhookEndpoint)
    assert endpoint.signing_secret == "whsec_new"
