"""Models for the ``/invoices`` endpoints (chunk 4.2)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

InvoiceStatus = Literal["draft", "open", "paid", "uncollectible", "void"]


class Invoice(BaseModel):
    """Server's view of one invoice."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "invoice"
    number: str | None = None
    customer: str | None = None
    subscription: str | None = None
    status: InvoiceStatus
    amount_due: Decimal
    amount_paid: Decimal
    amount_remaining: Decimal
    currency: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    hosted_invoice_url: str | None = None
    invoice_pdf: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_test: bool = True
    paid_at: datetime | None = None
    voided_at: datetime | None = None
    created_at: datetime


class UpcomingInvoice(BaseModel):
    """Preview returned by ``GET /api/v1/invoices/upcoming``.

    Not a real ``Invoice`` row — Stripe doesn't persist these. Period
    bounds and amounts mirror the full Invoice shape but the
    ``preview=True`` flag tells consumers it's transient.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    object: str = "invoice"
    preview: bool = True
    customer: str
    subscription: str | None = None
    amount_due: Decimal
    amount_paid: Decimal
    amount_remaining: Decimal
    currency: str
    period_start: datetime | None = None
    period_end: datetime | None = None


class InvoiceListFilters(BaseModel):
    """Query for ``GET /api/v1/invoices``."""

    model_config = ConfigDict(frozen=True)

    customer: str | None = None
    subscription: str | None = None
    status: InvoiceStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class InvoicePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[Invoice] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


__all__ = [
    "Invoice",
    "InvoiceListFilters",
    "InvoicePage",
    "InvoiceStatus",
    "UpcomingInvoice",
]
