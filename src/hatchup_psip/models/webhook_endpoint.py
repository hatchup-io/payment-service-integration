"""Models for the ``/webhook-endpoints`` endpoints (chunk 4.2).

Webhook subscriptions are project-side resources — each row tells
payment-system "fan these event types out to this URL." The
``signing_secret`` is shown ONCE at creation + rotation; afterwards it's
returned blank.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl


class WebhookEndpointCreateRequest(BaseModel):
    """Body for ``POST /api/v1/webhook-endpoints``."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    url: HttpUrl
    subscribed_events: list[str] = Field(..., min_length=1)
    description: str | None = Field(default=None, max_length=255)


class WebhookEndpointUpdateRequest(BaseModel):
    """Body for ``POST /api/v1/webhook-endpoints/<id>``. Partial."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    url: HttpUrl | None = None
    subscribed_events: list[str] | None = None
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class WebhookEndpoint(BaseModel):
    """Server's view of one webhook subscription.

    ``signing_secret`` is non-empty ONLY in the responses to ``create``
    and ``rotate_secret``. Subsequent reads return an empty string.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    object: str = "webhook_endpoint"
    url: str
    description: str = ""
    subscribed_events: list[str] = Field(default_factory=list)
    is_active: bool = True
    signing_secret: str = ""
    created_at: datetime
    updated_at: datetime


class WebhookEndpointPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: list[WebhookEndpoint] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    count: int = 0


__all__ = [
    "WebhookEndpoint",
    "WebhookEndpointCreateRequest",
    "WebhookEndpointPage",
    "WebhookEndpointUpdateRequest",
]
