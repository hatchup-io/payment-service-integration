"""Models for the ``/setup-intents`` endpoints (chunk 4.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

SetupIntentStatus = Literal[
    "requires_payment_method",
    "requires_confirmation",
    "requires_action",
    "processing",
    "succeeded",
    "canceled",
]

SetupIntentUsage = Literal["off_session", "on_session"]


class SetupIntentCreateRequest(BaseModel):
    """Body for ``POST /api/v1/setup-intents``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    customer: str | None = None
    payment_method: str | None = None
    usage: SetupIntentUsage = "off_session"
    description: str | None = None
    confirm: bool = False
    sandbox: bool = True
    metadata: dict[str, str] | None = None


class SetupIntentConfirmRequest(BaseModel):
    """Body for ``POST /api/v1/setup-intents/<id>/confirm``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    payment_method: str | None = None


class SetupIntent(BaseModel):
    """Server's view of one SetupIntent."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "setup_intent"
    status: SetupIntentStatus
    client_secret: str = ""
    customer: str | None = None
    payment_method: str | None = None
    usage: SetupIntentUsage = "off_session"
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_test: bool = True
    last_error_message: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime


class SetupIntentPage(BaseModel):
    """Paginated setup-intent list."""

    model_config = ConfigDict(extra="ignore")

    results: list[SetupIntent] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


class DetachedPaymentMethod(BaseModel):
    """Response from ``POST /api/v1/payment-methods/<id>/detach``."""

    model_config = ConfigDict(extra="ignore")

    id: str
    detached: bool = True


__all__ = [
    "DetachedPaymentMethod",
    "SetupIntent",
    "SetupIntentConfirmRequest",
    "SetupIntentCreateRequest",
    "SetupIntentPage",
    "SetupIntentStatus",
    "SetupIntentUsage",
]
