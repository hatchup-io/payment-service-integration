"""Models for inbound webhooks (payment-system → consumer).

The payment-system POSTs to the consumer's ``success_webhook`` URL with
the payload defined here. Note the lack of a signature header — see
``docs/webhooks.md`` and the verify-by-default dispatcher in
:mod:`hatchup_psip.webhooks` for the SDK's forgery-mitigation strategy.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PaymentCompletedEvent(BaseModel):
    """A ``payment.completed`` webhook payload from the payment-system.

    Field shape mirrors ``apps/payments/webhooks.py`` line 113-120 in the
    server. ``received_at`` is stamped by the SDK at parse time and is
    not present in the wire format.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    order_id: str
    status: Literal["completed"]
    amount: Decimal  # server sends as string; pydantic parses
    currency: str
    transaction_id: UUID
    received_at: datetime = Field(default_factory=_utc_now)


__all__ = ["PaymentCompletedEvent"]
