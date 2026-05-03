"""Models for the ``/verify`` endpoint."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class VerifyRequest(BaseModel):
    """Body for ``POST /api/v1/verify``.

    Asserts that the payment for ``order_id`` reached the server with a
    matching ``price`` and ``currency``. Used both as the primary
    consumer-side verification call and as the dispatcher's webhook
    forgery guard (see :mod:`hatchup_psip.webhooks`).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    order_id: str = Field(..., min_length=1)
    price: Decimal = Field(..., gt=0, max_digits=20, decimal_places=2)
    currency: str = Field(default="usd", min_length=2, max_length=10)

    @field_validator("currency", mode="before")
    @classmethod
    def _lowercase_currency(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v


class VerifyResponse(BaseModel):
    """Body of the ``data`` envelope for ``POST /api/v1/verify``."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    order_id: str
    verified: bool


__all__ = ["VerifyRequest", "VerifyResponse"]
