"""Process-wide singletons for the default Django wiring.

These factories are used by :class:`PSIPWebhookView` when the consumer
does not pass an explicit ``client``/``dispatcher`` via ``as_view(...)``.
They are intentionally lazy and cached: built on first access, reused
for the lifetime of the process.

**Multi-tenant consumers** (each tenant has its own API key — e.g.
launchpad-backend keyed by Company) should bypass these helpers and
construct one :class:`PaymentServiceClient` per tenant, passing it
into ``PSIPWebhookView.as_view(client=..., dispatcher=...)`` from a
custom URL conf.
"""

from __future__ import annotations

from functools import cache

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.django.settings import psip_config_from_django_settings
from hatchup_psip.webhooks.dispatcher import WebhookDispatcher


@cache
def get_default_client() -> PaymentServiceClient:
    """Process-wide :class:`PaymentServiceClient` built from ``settings.PSIP``.

    The returned client is cached for the process lifetime. Tests must
    call ``get_default_client.cache_clear()`` between cases to avoid
    leaking ``httpx.Client`` state.
    """
    return PaymentServiceClient(psip_config_from_django_settings())


@cache
def get_default_dispatcher() -> WebhookDispatcher:
    """Process-wide :class:`WebhookDispatcher` wired to verify via the default client."""
    return WebhookDispatcher(verifier=get_default_client().webhooks.verify_event)


__all__ = ["get_default_client", "get_default_dispatcher"]
