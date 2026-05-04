"""Tests for the webhook forgery guard (verify_event)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.webhooks.verifier import verify_event

EVENT_PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}

# Server's authoritative transaction for the same order
SERVER_TX_PAYLOAD = {
    "id": "11111111-1111-1111-1111-111111111111",
    "order_id": "ord_1",
    "amount": "9.99",
    "currency": "usd",
    "status": "succeeded",  # webhook "completed" maps to server "succeeded"
    "is_test": True,
    "verified_at": None,
    "created_at": "2026-05-01T12:00:00Z",
    "stripe_checkout_session_id": "cs_xxx",
}


def _event() -> PaymentCompletedEvent:
    return PaymentCompletedEvent.model_validate(EVENT_PAYLOAD)


def _server_tx(**overrides: object) -> Transaction:
    return Transaction.model_validate(SERVER_TX_PAYLOAD | overrides)


def _mock_transactions(returns: Transaction | None = None, raises: Exception | None = None) -> MagicMock:
    txs = MagicMock(spec=TransactionsResource)
    if raises is not None:
        txs.get.side_effect = raises
    else:
        txs.get.return_value = returns
    return txs


def test_passes_when_server_record_matches() -> None:
    transactions = _mock_transactions(returns=_server_tx())
    tx = verify_event(_event(), transactions)
    assert tx.order_id == "ord_1"
    transactions.get.assert_called_once()


def test_currency_compared_case_insensitively() -> None:
    transactions = _mock_transactions(returns=_server_tx(currency="USD"))
    tx = verify_event(_event(), transactions)
    assert tx.currency == "USD"


def test_raises_forgery_when_server_returns_404() -> None:
    not_found = PSIPNotFoundError(status_code=404, message="Transaction not found")
    transactions = _mock_transactions(raises=not_found)
    with pytest.raises(PSIPWebhookForgeryError, match="unknown transaction"):
        verify_event(_event(), transactions)


def test_raises_on_order_id_mismatch() -> None:
    transactions = _mock_transactions(returns=_server_tx(order_id="ord_OTHER"))
    with pytest.raises(PSIPWebhookForgeryError, match="order_id"):
        verify_event(_event(), transactions)


def test_raises_on_amount_mismatch() -> None:
    transactions = _mock_transactions(returns=_server_tx(amount="100.00"))
    with pytest.raises(PSIPWebhookForgeryError, match="amount"):
        verify_event(_event(), transactions)


def test_raises_on_currency_mismatch() -> None:
    transactions = _mock_transactions(returns=_server_tx(currency="eur"))
    with pytest.raises(PSIPWebhookForgeryError, match="currency"):
        verify_event(_event(), transactions)


@pytest.mark.parametrize("server_status", ["pending", "failed"])
def test_raises_when_server_status_does_not_match_completed_webhook(server_status: str) -> None:
    transactions = _mock_transactions(returns=_server_tx(status=server_status))
    with pytest.raises(PSIPWebhookForgeryError, match="status"):
        verify_event(_event(), transactions)


def test_aggregates_multiple_mismatches_in_one_message() -> None:
    transactions = _mock_transactions(returns=_server_tx(order_id="ord_OTHER", amount="100.00"))
    with pytest.raises(PSIPWebhookForgeryError) as exc_info:
        verify_event(_event(), transactions)
    msg = str(exc_info.value)
    assert "order_id" in msg
    assert "amount" in msg
