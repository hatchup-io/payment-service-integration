"""Models for the ``/payment-intents`` endpoints (chunk 4.1)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl
from pydantic import field_validator

PaymentIntentStatus = Literal[
    "requires_payment_method",
    "requires_confirmation",
    "requires_action",
    "processing",
    "requires_capture",
    "succeeded",
    "canceled",
]

CaptureMethod = Literal["automatic", "manual"]

CancellationReason = Literal[
    "duplicate",
    "fraudulent",
    "requested_by_customer",
    "abandoned",
]


class PaymentIntentCreateRequest(BaseModel):
    """Body for ``POST /api/v1/payment-intents``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    amount: Decimal = Field(..., gt=0, max_digits=20, decimal_places=2)
    currency: str = Field(default="usd", min_length=2, max_length=10)
    customer: str | None = None
    payment_method: str | None = None
    confirm: bool = False
    capture_method: CaptureMethod = "automatic"
    description: str | None = None
    success_webhook: HttpUrl | None = None
    failure_webhook: HttpUrl | None = None
    sandbox: bool = True
    metadata: dict[str, str] | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def _lowercase_currency(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v


class PaymentIntentConfirmRequest(BaseModel):
    """Body for ``POST /api/v1/payment-intents/<id>/confirm``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    payment_method: str | None = None


class PaymentIntentCaptureRequest(BaseModel):
    """Body for ``POST /api/v1/payment-intents/<id>/capture``."""

    model_config = ConfigDict(frozen=True)

    amount_to_capture: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=2)


class PaymentIntentCancelRequest(BaseModel):
    """Body for ``POST /api/v1/payment-intents/<id>/cancel``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    cancellation_reason: CancellationReason | None = None


class PaymentMethodDetails(BaseModel):
    """Card details surfaced on a PaymentIntent (when card-shaped)."""

    model_config = ConfigDict(extra="ignore")

    type: str = ""
    brand: str = ""
    last4: str = ""
    exp_month: int | None = None
    exp_year: int | None = None


class PaymentIntent(BaseModel):
    """Server's view of one PaymentIntent."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "payment_intent"
    amount: Decimal
    currency: str
    status: PaymentIntentStatus
    client_secret: str = ""
    customer: str | None = None
    payment_method: str | None = None
    payment_method_details: PaymentMethodDetails | dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_test: bool = True
    last_error_message: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime


class PaymentIntentListFilters(BaseModel):
    """Query params for ``GET /api/v1/payment-intents``."""

    model_config = ConfigDict(frozen=True)

    customer: str | None = None
    status: PaymentIntentStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaymentIntentPage(BaseModel):
    """Paginated payment-intent list."""

    model_config = ConfigDict(extra="ignore")

    results: list[PaymentIntent] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


__all__ = [
    "CancellationReason",
    "CaptureMethod",
    "PaymentIntent",
    "PaymentIntentCancelRequest",
    "PaymentIntentCaptureRequest",
    "PaymentIntentConfirmRequest",
    "PaymentIntentCreateRequest",
    "PaymentIntentListFilters",
    "PaymentIntentPage",
    "PaymentIntentStatus",
    "PaymentMethodDetails",
]
