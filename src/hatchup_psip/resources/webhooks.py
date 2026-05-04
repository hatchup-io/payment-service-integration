"""Webhooks resource — parsing + forgery guard.

Unlike the other resource classes, :class:`WebhooksResource` does not
own a :class:`Transport` directly. It composes a
:class:`TransactionsResource` for the forgery-guard server roundtrip,
and delegates parsing to :mod:`hatchup_psip.webhooks.parser`.
"""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.webhooks.parser import parse_payment_completed
from hatchup_psip.webhooks.verifier import verify_event as _verify_event


class WebhooksResource:
    """High-level entry-point for inbound-webhook handling.

    Two methods exposed:

    - :meth:`parse` — JSON-decode + schema-validate the request body
      into a :class:`PaymentCompletedEvent`. No HTTP call.
    - :meth:`verify_event` — round-trip the server through
      ``transactions.get`` to confirm the event is genuine. Used by
      :class:`hatchup_psip.webhooks.WebhookDispatcher` when
      ``verify=True``.
    """

    def __init__(self, *, transactions: TransactionsResource) -> None:
        self._transactions = transactions

    def parse(self, body: bytes | str | dict[str, Any]) -> PaymentCompletedEvent:
        """Decode + validate a raw webhook body. See :func:`parse_payment_completed`."""
        return parse_payment_completed(body)

    def verify_event(self, event: PaymentCompletedEvent) -> Transaction:
        """Confirm ``event`` matches the server's record. See :func:`verify_event`."""
        return _verify_event(event, self._transactions)


__all__ = ["WebhooksResource"]
