"""Smoke tests for the async resource pairs.

The async resources share request-building and response-parsing helpers
with their sync counterparts (those are covered exhaustively in
``test_payments.py``, ``test_verify.py``, ``test_transactions.py``,
``test_webhooks.py``). These tests focus on the async-specific paths:
that ``await`` works, ``async for`` paginates, and the verify roundtrip
awaits ``transactions.get``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from hatchup_psip.client import AsyncPaymentServiceClient
from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.models.payment import PaymentCreateResponse
from hatchup_psip.models.webhook import PaymentCompletedEvent

BASE = "https://test.example.com/api/v1/"
PAYMENT_URL = BASE + "payment"
REPAYMENT_URL = BASE + "repayment"
VERIFY_URL = BASE + "verify"
TRANSACTIONS_URL = BASE + "transactions"
TX_DETAIL_BASE = BASE + "transactions/"

PAY_OK = {
    "data": {
        "payment_url": "https://checkout.stripe.com/c/pay/cs_xxx",
        "session_id": "cs_xxx",
        "order_id": "ord_1",
    },
    "status": "ok",
    "message": "",
}
TX = {
    "id": "11111111-1111-1111-1111-111111111111",
    "order_id": "ord_1",
    "amount": "9.99",
    "currency": "usd",
    "status": "succeeded",
    "is_test": True,
    "verified_at": None,
    "created_at": "2026-05-01T12:00:00Z",
    "stripe_checkout_session_id": "cs_xxx",
}
EVENT_PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}


def _page(*, results: int = 1, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return {
        "data": {
            "results": [TX] * results,
            "page": page,
            "page_size": page_size,
            "count": results,
        },
        "status": "ok",
        "message": "",
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


# --------------------------------------------------------------------------- #
# Payments
# --------------------------------------------------------------------------- #


async def test_payments_create_awaits(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(PAYMENT_URL).mock(return_value=httpx.Response(200, json=PAY_OK))
        response = await async_client.payments.create(
            price="9.99",
            order_id="ord_1",
            success_webhook="https://app.example/cb/ok",
            failure_webhook="https://app.example/cb/fail",
        )
    assert isinstance(response, PaymentCreateResponse)
    sent = json.loads(route.calls.last.request.content)
    assert sent["order_id"] == "ord_1"


async def test_payments_recreate_awaits(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        respx.post(REPAYMENT_URL).mock(return_value=httpx.Response(200, json=PAY_OK))
        response = await async_client.payments.recreate("ord_1")
    assert response.session_id == "cs_xxx"


# --------------------------------------------------------------------------- #
# Verify
# --------------------------------------------------------------------------- #


async def test_verify_awaits(async_client: AsyncPaymentServiceClient) -> None:
    payload = {"data": {"order_id": "ord_1", "verified": True}, "status": "ok", "message": ""}
    with respx.mock:
        respx.post(VERIFY_URL).mock(return_value=httpx.Response(200, json=payload))
        result = await async_client.verify("ord_1", "9.99")
    assert result.verified is True


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #


async def test_transactions_list_awaits(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        respx.get(TRANSACTIONS_URL).mock(return_value=httpx.Response(200, json=_page()))
        page = await async_client.transactions.list()
    assert len(page.results) == 1


async def test_transactions_get_awaits(async_client: AsyncPaymentServiceClient) -> None:
    with respx.mock:
        respx.get(TX_DETAIL_BASE + "ord_1").mock(
            return_value=httpx.Response(200, json={"data": TX, "status": "ok", "message": ""}),
        )
        tx = await async_client.transactions.get("ord_1")
    assert tx.order_id == "ord_1"


async def test_transactions_iter_all_paginates(async_client: AsyncPaymentServiceClient) -> None:
    """async for over multiple pages — partial second page ends iteration."""
    responses = [
        httpx.Response(200, json=_page(results=2, page=1, page_size=2)),
        httpx.Response(200, json=_page(results=1, page=2, page_size=2)),
    ]
    with respx.mock:
        respx.get(TRANSACTIONS_URL).mock(side_effect=responses)
        collected = [tx async for tx in async_client.transactions.iter_all(page_size=2)]
    assert len(collected) == 3


# --------------------------------------------------------------------------- #
# Webhooks
# --------------------------------------------------------------------------- #


async def test_webhooks_parse_is_sync(async_client: AsyncPaymentServiceClient) -> None:
    """parse() is intentionally synchronous — pure JSON, no IO."""
    event = async_client.webhooks.parse(EVENT_PAYLOAD)
    assert isinstance(event, PaymentCompletedEvent)


async def test_webhooks_verify_event_awaits(async_client: AsyncPaymentServiceClient) -> None:
    event = PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)
    with respx.mock:
        respx.get(TX_DETAIL_BASE + str(event.transaction_id)).mock(
            return_value=httpx.Response(200, json={"data": TX, "status": "ok", "message": ""}),
        )
        tx = await async_client.webhooks.verify_event(event)
    assert tx.order_id == "ord_1"


async def test_webhooks_verify_event_raises_forgery(
    async_client: AsyncPaymentServiceClient,
) -> None:
    event = PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)
    with respx.mock:
        respx.get(TX_DETAIL_BASE + str(event.transaction_id)).mock(
            return_value=httpx.Response(
                404,
                json={"data": None, "status": "failure", "message": "not found"},
            ),
        )
        with pytest.raises(PSIPWebhookForgeryError):
            await async_client.webhooks.verify_event(event)
