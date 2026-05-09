"""Models for the ``/products`` and ``/prices`` endpoints (chunk 4.2)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

RecurringInterval = Literal["", "day", "week", "month", "year"]


# --------------------------------------------------------------------------- #
# Product
# --------------------------------------------------------------------------- #


class ProductCreateRequest(BaseModel):
    """Body for ``POST /api/v1/products``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict[str, str] | None = None
    sandbox: bool = True


class ProductUpdateRequest(BaseModel):
    """Body for ``POST /api/v1/products/<stripe_product_id>``. Partial."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict[str, str] | None = None
    is_active: bool | None = None


class Product(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "product"
    name: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_test: bool = True
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[Product] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


# --------------------------------------------------------------------------- #
# Price
# --------------------------------------------------------------------------- #


class PriceCreateRequest(BaseModel):
    """Body for ``POST /api/v1/prices``.

    A non-empty ``recurring_interval`` makes this a subscription-eligible price.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    product: str = Field(..., min_length=1)
    unit_amount: Decimal = Field(..., gt=0, max_digits=20, decimal_places=2)
    currency: str = Field(default="usd", min_length=2, max_length=10)
    recurring_interval: RecurringInterval = ""
    recurring_interval_count: int = Field(default=1, ge=1)
    nickname: str | None = Field(default=None, max_length=255)
    metadata: dict[str, str] | None = None
    sandbox: bool = True

    @field_validator("currency", mode="before")
    @classmethod
    def _lowercase_currency(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v


class RecurringPrice(BaseModel):
    """Sub-object on a recurring :class:`Price`."""

    model_config = ConfigDict(extra="ignore")

    interval: str
    interval_count: int = 1


class Price(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "price"
    product: str
    unit_amount: Decimal
    currency: str
    recurring: RecurringPrice | None = None
    nickname: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_test: bool = True
    created_at: datetime
    updated_at: datetime


class PricePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[Price] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


__all__ = [
    "Price",
    "PriceCreateRequest",
    "PricePage",
    "Product",
    "ProductCreateRequest",
    "ProductPage",
    "ProductUpdateRequest",
    "RecurringInterval",
    "RecurringPrice",
]
