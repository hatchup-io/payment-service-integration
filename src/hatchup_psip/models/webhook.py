"""Models for inbound webhooks (payment-system → consumer).

The payment-system POSTs to the consumer's URL with the payloads defined
here. Two delivery flavors coexist:

- **Per-row legacy** (PaymentRequest / PaymentIntent ``success_webhook_url``):
  unsigned. Verified via server roundtrip
  (:mod:`hatchup_psip.webhooks.verifier`).
- **Project-level WebhookEndpoint** (chunk 1.5+): HMAC-SHA256 signed in
  the ``X-Hatchup-Signature: t=<unix>,v1=<hex>`` header (covers
  ``f"{ts}.{body}"``). Use
  :func:`hatchup_psip.webhooks.verifier.verify_signature` before parsing.

All event payloads carry an ``event`` discriminator string matching the
public taxonomy (``payment.completed``, ``payment_intent.succeeded``,
``subscription.updated``, etc.).
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class PaymentCompletedEvent(BaseModel):
    """``payment.completed`` — Checkout flow."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    order_id: str
    status: Literal["completed"]
    amount: Decimal
    currency: str
    transaction_id: UUID
    received_at: datetime = Field(default_factory=_utc_now)


class PaymentIntentSucceededEvent(BaseModel):
    """``payment_intent.succeeded``."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    event: Literal["payment_intent.succeeded"]
    id: str
    status: str
    amount: Decimal
    currency: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=_utc_now)


class PaymentIntentFailedEvent(BaseModel):
    """``payment_intent.payment_failed``."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    event: Literal["payment_intent.payment_failed"]
    id: str
    status: str
    amount: Decimal
    currency: str
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=_utc_now)


class CustomerEvent(BaseModel):
    """``customer.created`` / ``customer.updated`` — only the fields we forward."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    event: Literal["customer.created", "customer.updated"]
    id: str
    email: str = ""
    name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=_utc_now)


class SubscriptionEvent(BaseModel):
    """``subscription.{created,updated,deleted,trial_will_end}``.

    The Stripe ``customer.`` prefix is stripped server-side (chunk 2.4)
    so wire names match the SDK's public taxonomy.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    event: Literal[
        "subscription.created",
        "subscription.updated",
        "subscription.deleted",
        "subscription.trial_will_end",
    ]
    id: str
    status: str = ""
    customer: str | None = None
    current_period_end: int | None = None
    cancel_at_period_end: bool = False
    trial_end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=_utc_now)


class InvoiceEvent(BaseModel):
    """``invoice.paid`` / ``invoice.payment_failed`` / ``invoice.upcoming``.

    ``invoice.upcoming`` is a preview event — there's no server row for
    it; subscribers use it for renewal-reminder hooks.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    event: Literal["invoice.paid", "invoice.payment_failed", "invoice.upcoming"]
    id: str
    status: str = ""
    customer: str | None = None
    subscription: str | None = None
    amount_due: Decimal | None = None
    amount_paid: Decimal | None = None
    currency: str = "usd"
    hosted_invoice_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=_utc_now)


__all__ = [
    "CustomerEvent",
    "InvoiceEvent",
    "PaymentCompletedEvent",
    "PaymentIntentFailedEvent",
    "PaymentIntentSucceededEvent",
    "SubscriptionEvent",
]
