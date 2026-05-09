"""Models for the ``/customers`` endpoints (chunk 4.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl


class CustomerCreateRequest(BaseModel):
    """Body for ``POST /api/v1/customers``. Idempotency-Key header required server-side."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    email: str | None = None
    name: str | None = None
    phone: str | None = None
    description: str | None = Field(default=None, max_length=500)
    sandbox: bool = True
    metadata: dict[str, str] | None = None


class CustomerUpdateRequest(BaseModel):
    """Body for ``POST /api/v1/customers/<stripe_customer_id>``. Partial."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    email: str | None = None
    name: str | None = None
    phone: str | None = None
    description: str | None = Field(default=None, max_length=500)
    metadata: dict[str, str] | None = None


class Customer(BaseModel):
    """Server's view of one customer (chunk 1.1 server-side)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "customer"
    email: str = ""
    name: str = ""
    phone: str = ""
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_test: bool = True
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PaymentMethodCard(BaseModel):
    """Card-flavored details inside a saved PaymentMethod row."""

    model_config = ConfigDict(extra="ignore")

    brand: str = ""
    last4: str = ""
    exp_month: int | None = None
    exp_year: int | None = None


class PaymentMethod(BaseModel):
    """One saved payment method (typically a card) on a customer."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: str
    card: PaymentMethodCard | None = None
    customer: str | None = None


class PaymentMethodList(BaseModel):
    """Envelope ``data`` shape for the saved-cards listing."""

    model_config = ConfigDict(extra="ignore")

    object: str = "list"
    results: list[PaymentMethod] = Field(default_factory=list)


class CustomerListPage(BaseModel):
    """Paginated customer list."""

    model_config = ConfigDict(extra="ignore")

    results: list[Customer] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


class CustomerPortalSessionRequest(BaseModel):
    """Body for ``POST /api/v1/customers/<id>/portal-sessions``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    return_url: HttpUrl


class CustomerPortalSession(BaseModel):
    """Stripe Billing Portal session URL."""

    model_config = ConfigDict(extra="ignore")

    id: str
    url: str


__all__ = [
    "Customer",
    "CustomerCreateRequest",
    "CustomerListPage",
    "CustomerPortalSession",
    "CustomerPortalSessionRequest",
    "CustomerUpdateRequest",
    "PaymentMethod",
    "PaymentMethodCard",
    "PaymentMethodList",
]
