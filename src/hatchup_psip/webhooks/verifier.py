"""Server-roundtrip forgery guard for inbound webhooks.

The payment-system does **not** sign outbound webhooks today (no HMAC,
no shared secret — see ``apps/payments/webhooks.py:37-46``). Anyone who
learns or guesses the consumer's ``success_webhook_url`` can forge a
``{order_id, status:"completed", amount, ...}`` POST. The dispatcher's
default ``verify=True`` mode runs :func:`verify_event` before invoking
any user handler so a forgery is caught before it can mark an order
paid in the consumer's database.

When payment-system gains HMAC signing, this module stays — it's also
useful as a defence-in-depth check (signature OR roundtrip). The
roundtrip becomes optional then.
"""

from __future__ import annotations

from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.resources.transactions import TransactionsResource

# Webhook event.status -> server Transaction.status it must match
_EXPECTED_SERVER_STATUS = {"completed": "succeeded"}


def _check_match(event: PaymentCompletedEvent, tx: Transaction) -> Transaction:
    """Compare server's record against the webhook payload. Return tx on success, else raise."""
    mismatches: list[str] = []
    if tx.order_id != event.order_id:
        mismatches.append(
            f"order_id: server={tx.order_id!r} vs webhook={event.order_id!r}",
        )
    if tx.amount != event.amount:
        mismatches.append(
            f"amount: server={tx.amount} vs webhook={event.amount}",
        )
    if tx.currency.lower() != event.currency.lower():
        mismatches.append(
            f"currency: server={tx.currency!r} vs webhook={event.currency!r}",
        )
    expected_server_status = _EXPECTED_SERVER_STATUS.get(event.status)
    if expected_server_status is not None and tx.status != expected_server_status:
        mismatches.append(
            f"status: webhook={event.status!r} expects server={expected_server_status!r}, got server={tx.status!r}",
        )

    if mismatches:
        raise PSIPWebhookForgeryError(
            f"webhook payload does not match server transaction "
            f"(transaction_id={event.transaction_id}): {'; '.join(mismatches)}",
        )
    return tx


def verify_event(
    event: PaymentCompletedEvent,
    transactions: TransactionsResource,
) -> Transaction:
    """Round-trip the server to confirm a webhook isn't forged.

    Raises :class:`PSIPWebhookForgeryError` if:

    - the server has no record of ``event.transaction_id`` (404), or
    - the server's transaction differs from the webhook in any of:
      ``order_id``, ``amount``, ``currency``, or ``status`` (where
      ``"completed"`` on the wire must correspond to ``"succeeded"``
      server-side).

    Returns the server's :class:`Transaction` on success — callers can
    pass it to user handlers as an authoritative replacement for the
    untrusted webhook payload.
    """
    try:
        tx = transactions.get(event.transaction_id)
    except PSIPNotFoundError as exc:
        raise PSIPWebhookForgeryError(
            f"webhook references unknown transaction_id={event.transaction_id}",
        ) from exc
    return _check_match(event, tx)


async def async_verify_event(
    event: PaymentCompletedEvent,
    transactions: AsyncTransactionsResource,
) -> Transaction:
    """Async equivalent of :func:`verify_event` — same contract, awaits ``transactions.get``."""
    try:
        tx = await transactions.get(event.transaction_id)
    except PSIPNotFoundError as exc:
        raise PSIPWebhookForgeryError(
            f"webhook references unknown transaction_id={event.transaction_id}",
        ) from exc
    return _check_match(event, tx)


__all__ = ["async_verify_event", "verify_event"]
