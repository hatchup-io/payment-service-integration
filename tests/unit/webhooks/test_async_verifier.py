"""Tests for async_verify_event — async-specific paths only.

The match-comparison logic is shared with the sync verifier and covered
exhaustively in ``test_verifier.py``. These tests confirm the async
path awaits ``transactions.get`` and surfaces the same exception types.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.webhooks.verifier import async_verify_event

EVENT_PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}
SERVER_TX_PAYLOAD = {
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


def _event() -> PaymentCompletedEvent:
    return PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)


def _server_tx(**overrides: object) -> Transaction:
    return Transaction.model_validate(SERVER_TX_PAYLOAD | overrides)


def _mock_async_transactions(
    returns: Transaction | None = None,
    raises: Exception | None = None,
) -> AsyncMock:
    txs = AsyncMock(spec=AsyncTransactionsResource)
    if raises is not None:
        txs.get.side_effect = raises
    else:
        txs.get.return_value = returns
    return txs


async def test_passes_when_server_matches() -> None:
    transactions = _mock_async_transactions(returns=_server_tx())
    tx = await async_verify_event(_event(), transactions)
    assert tx.order_id == "ord_1"
    transactions.get.assert_awaited_once()


async def test_raises_forgery_on_404() -> None:
    transactions = _mock_async_transactions(
        raises=PSIPNotFoundError(status_code=404, message="not found"),
    )
    with pytest.raises(PSIPWebhookForgeryError, match="unknown transaction"):
        await async_verify_event(_event(), transactions)


async def test_raises_forgery_on_amount_mismatch() -> None:
    transactions = _mock_async_transactions(returns=_server_tx(amount="100.00"))
    with pytest.raises(PSIPWebhookForgeryError, match="amount"):
        await async_verify_event(_event(), transactions)
