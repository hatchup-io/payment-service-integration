"""Models for the ``/subscriptions`` endpoints (chunk 4.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

SubscriptionStatus = Literal[
    "incomplete",
    "incomplete_expired",
    "trialing",
    "active",
    "past_due",
    "canceled",
    "unpaid",
    "paused",
]

ProrationBehavior = Literal["create_prorations", "none", "always_invoice"]

CancellationReason = Literal[
    "customer_service",
    "low_quality",
    "missing_features",
    "switched_service",
    "too_complex",
    "too_expensive",
    "unused",
    "other",
]


# --------------------------------------------------------------------------- #
# Item shapes (create + update)
# --------------------------------------------------------------------------- #


class SubscriptionItemInput(BaseModel):
    """One line of a subscription create or update.

    On create: only ``price`` (and optional ``quantity``) are meaningful.
    On update: pass ``id`` to mutate a line, ``id`` + ``deleted=True`` to
    remove one, or ``price`` (no ``id``) to add a new line.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str | None = None
    price: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    deleted: bool = False

    @model_validator(mode="after")
    def _check_either_id_or_price(self) -> SubscriptionItemInput:
        if not self.id and not self.price:
            raise ValueError("each item must carry an `id` (update/delete) or a `price` (new line)")
        return self


class SubscriptionItemSnapshot(BaseModel):
    """Item shape as the server returns it on a Subscription."""

    model_config = ConfigDict(extra="ignore")

    stripe_subscription_item_id: str
    price_id: str
    quantity: int = 1


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #


class SubscriptionCreateRequest(BaseModel):
    """Body for ``POST /api/v1/subscriptions``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    customer: str = Field(..., min_length=1)
    items: list[SubscriptionItemInput] = Field(..., min_length=1)
    trial_period_days: int | None = Field(default=None, ge=0)
    default_payment_method: str | None = None
    metadata: dict[str, str] | None = None
    sandbox: bool = True


class SubscriptionUpdateRequest(BaseModel):
    """Body for ``POST /api/v1/subscriptions/<id>``. Partial.

    Omit ``proration_behavior`` to fall back to the project's
    ``default_proration_behavior`` (decision #6 in STRIPE_GATEWAY_PLAN.md).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    items: list[SubscriptionItemInput] | None = None
    default_payment_method: str | None = None
    cancel_at_period_end: bool | None = None
    proration_behavior: ProrationBehavior | None = None
    metadata: dict[str, str] | None = None


class SubscriptionCancelRequest(BaseModel):
    """Body for ``POST /api/v1/subscriptions/<id>/cancel``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    at_period_end: bool = False
    cancellation_reason: CancellationReason | None = None
    invoice_now: bool = False
    prorate: bool | None = None


# --------------------------------------------------------------------------- #
# Response shape
# --------------------------------------------------------------------------- #


class Subscription(BaseModel):
    """Server's view of one subscription (chunk 2.2 server-side)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "subscription"
    customer: str
    status: SubscriptionStatus
    items: list[SubscriptionItemSnapshot] = Field(default_factory=list)
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    trial_start: datetime | None = None
    trial_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    cancellation_reason: str | None = None
    default_payment_method: str | None = None
    latest_invoice: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_test: bool = True
    created_at: datetime


class SubscriptionPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[Subscription] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


__all__ = [
    "CancellationReason",
    "ProrationBehavior",
    "Subscription",
    "SubscriptionCancelRequest",
    "SubscriptionCreateRequest",
    "SubscriptionItemInput",
    "SubscriptionItemSnapshot",
    "SubscriptionPage",
    "SubscriptionStatus",
    "SubscriptionUpdateRequest",
]
