"""Forgery guards for inbound webhooks — two flavors.

1. **HMAC signature** (chunk 1.5+): payment-system signs new-style
   ``WebhookEndpoint`` deliveries with HMAC-SHA256 over
   ``f"{timestamp}.{body}"`` using the per-endpoint ``signing_secret``.
   Use :func:`verify_signature` *before* parsing.

2. **Server roundtrip** (legacy): per-row deliveries
   (``PaymentRequest.success_webhook_url`` etc.) carry no signature.
   :func:`verify_event` confirms the payload by re-fetching the
   server's record. Used by the dispatcher's ``verify=True`` mode.

Either is sufficient. Defence-in-depth is encouraged on the
HMAC path: verify the signature *and* roundtrip.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import time

from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.resources.transactions import TransactionsResource

_SIGNATURE_HEADER = "X-Hatchup-Signature"
_DEFAULT_TOLERANCE_SECONDS = 300  # 5 minutes — matches Stripe's default tolerance.


def _parse_signature_header(header_value: str) -> tuple[int, str]:
    """Decode ``t=<unix>,v1=<hex>`` into ``(timestamp_int, hex_digest)``.

    Tolerates extra unknown ``vN=...`` schemes for forward compatibility.
    """
    timestamp: int | None = None
    digest: str | None = None
    for part in header_value.split(","):
        if "=" not in part:
            continue
        name, _, value = part.strip().partition("=")
        if name == "t":
            with contextlib.suppress(ValueError):
                timestamp = int(value)
        elif name == "v1":
            digest = value
    if timestamp is None or digest is None:
        raise PSIPWebhookValidationError(
            f"{_SIGNATURE_HEADER} header missing t= or v1= scheme",
        )
    return (timestamp, digest)


def verify_signature(
    *,
    body: bytes | str,
    signing_secret: str,
    header_value: str,
    tolerance_seconds: int = _DEFAULT_TOLERANCE_SECONDS,
    now_func: callable[[], float] | None = None,  # type: ignore[type-arg]
) -> None:
    """Verify an ``X-Hatchup-Signature`` header against ``body``.

    Raises :class:`PSIPWebhookForgeryError` on signature mismatch or
    timestamp drift outside ``tolerance_seconds``. Returns ``None`` on
    success.

    ``body`` must be the **raw** request body (the same bytes Stripe
    signed) — not a re-serialised dict. ``signing_secret`` is the value
    returned at create / rotate-secret time.
    """
    if not signing_secret:
        raise PSIPWebhookValidationError("signing_secret is required to verify a webhook")
    if not header_value:
        raise PSIPWebhookForgeryError(f"missing {_SIGNATURE_HEADER} header")

    timestamp, expected_hex = _parse_signature_header(header_value)

    now_unix = (now_func or time.time)()
    if abs(now_unix - timestamp) > tolerance_seconds:
        raise PSIPWebhookForgeryError(
            f"webhook timestamp {timestamp} outside tolerance {tolerance_seconds}s of now {int(now_unix)}",
        )

    body_str = body.decode("utf-8") if isinstance(body, bytes) else body
    msg = f"{timestamp}.{body_str}".encode()
    actual_hex = hmac.new(signing_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(actual_hex, expected_hex):
        raise PSIPWebhookForgeryError("HMAC-SHA256 signature mismatch")


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


__all__ = ["async_verify_event", "verify_event", "verify_signature"]
