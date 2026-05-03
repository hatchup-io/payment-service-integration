"""Models for the ``/transactions`` list and detail endpoints."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

TransactionStatus = Literal["succeeded", "failed", "pending"]


class Transaction(BaseModel):
    """A single transaction as returned by ``/api/v1/transactions``.

    Both list and detail endpoints validate against this model.
    ``stripe_checkout_session_id`` is only present in detail responses;
    list responses populate it as ``None``.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: UUID
    order_id: str
    amount: Decimal  # server returns as string via DRF CharField; pydantic accepts both
    currency: str
    status: TransactionStatus
    is_test: bool
    verified_at: datetime | None = None
    created_at: datetime
    stripe_checkout_session_id: str | None = None


class TransactionListFilters(BaseModel):
    """Query params for ``GET /api/v1/transactions``.

    Use :meth:`to_query_params` when calling the transport — it drops
    ``None`` values, formats dates as ``YYYY-MM-DD``, and serializes
    booleans as the ``"true"``/``"false"`` strings the server accepts.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    date_from: date | None = None
    date_to: date | None = None
    status: TransactionStatus | None = None
    sandbox: bool | None = None
    verified: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    def to_query_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.date_from is not None:
            params["date_from"] = self.date_from.isoformat()
        if self.date_to is not None:
            params["date_to"] = self.date_to.isoformat()
        if self.status is not None:
            params["status"] = self.status
        if self.sandbox is not None:
            params["sandbox"] = "true" if self.sandbox else "false"
        if self.verified is not None:
            params["verified"] = "true" if self.verified else "false"
        params["page"] = str(self.page)
        params["page_size"] = str(self.page_size)
        return params


class TransactionPage(BaseModel):
    """Paginated ``data`` envelope for ``GET /api/v1/transactions``.

    .. note::
       Server-side ``count`` is the *length of the current page*, not the
       total count. Use :meth:`hatchup_psip.resources.transactions.TransactionsResource.iter_all`
       to iterate every page until exhaustion (the SDK detects exhaustion
       via ``len(results) < page_size``, not via ``count``).
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    results: list[Transaction]
    page: int
    page_size: int
    count: int

    @property
    def has_more(self) -> bool:
        """True if the current page is full and another page may exist."""
        return len(self.results) >= self.page_size


__all__ = [
    "Transaction",
    "TransactionListFilters",
    "TransactionPage",
    "TransactionStatus",
]
