"""Models for the ``/payment`` and ``/repayment`` endpoints.

Field names mirror payment-system's ``apps/payments/schema.py`` 1:1 — the
contract test in ``tests/contract/`` will fail if the server adds or
removes a field without a matching SDK update.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl
from pydantic import field_validator

PaymentType = Literal["one_time", "subscription"]


class PaymentCreateRequest(BaseModel):
    """Body for ``POST /api/v1/payment``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    price: Decimal = Field(..., gt=0, max_digits=20, decimal_places=2)
    currency: str = Field(default="usd", min_length=2, max_length=10)
    order_id: str = Field(..., min_length=1)
    payment_type: PaymentType = "one_time"
    success_webhook: HttpUrl
    failure_webhook: HttpUrl
    sandbox: bool = True
    metadata: dict[str, str] | None = Field(
        default=None,
        description=(
            "Optional flat key→string map forwarded to the Stripe Checkout "
            "Session's metadata. Server enforces Stripe's constraints "
            "(≤50 keys, ≤40-char keys, ≤500-char values) and silently strips "
            "the reserved ``payment_request_id`` key on merge. Server feature "
            "since payment-system commit 9d32b43."
        ),
    )

    @field_validator("currency", mode="before")
    @classmethod
    def _lowercase_currency(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v


class PaymentCreateResponse(BaseModel):
    """Body of the ``data`` envelope for ``POST /api/v1/payment`` and ``/repayment``."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    payment_url: str
    session_id: str
    order_id: str


class CheckoutSessionVerifyResponse(BaseModel):
    """Body of the ``data`` envelope for
    ``POST /api/v1/checkout-sessions/<session_id>/verify``.

    ``payment_status`` mirrors Stripe's Checkout Session vocabulary:
    ``paid``, ``unpaid``, ``no_payment_required``. ``transaction_id`` is
    populated only when the session was applied to a local Transaction
    (i.e. ``payment_status == 'paid'``); otherwise it's ``None``.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    session_id: str
    order_id: str
    payment_status: str
    amount: Decimal
    currency: str
    transaction_id: str | None = None


class RepaymentRequest(BaseModel):
    """Body for ``POST /api/v1/repayment``.

    Re-creates a checkout session for an order whose previous attempt
    failed/expired. ``order_id`` is the only required field; the server
    re-uses webhook URLs from the original PaymentRequest if not provided.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    order_id: str = Field(..., min_length=1)
    success_webhook: HttpUrl | None = None
    failure_webhook: HttpUrl | None = None
    sandbox: bool | None = None
    metadata: dict[str, str] | None = Field(
        default=None,
        description="See :attr:`PaymentCreateRequest.metadata`.",
    )


__all__ = [
    "CheckoutSessionVerifyResponse",
    "PaymentCreateRequest",
    "PaymentCreateResponse",
    "PaymentType",
    "RepaymentRequest",
]
