"""Default URL conf — wire with ``include("hatchup_psip.django.urls")``.

Mounts :class:`PSIPWebhookView` at the empty path so a parent
``include("hatchup_psip.django.urls")`` controls the full prefix::

    # myproject/urls.py
    urlpatterns = [
        path("psip/webhook/", include("hatchup_psip.django.urls")),
    ]

This default-wired view falls back to the settings-backed singletons
in :mod:`hatchup_psip.django.client`. Multi-tenant deployments should
build their own URL conf with
``PSIPWebhookView.as_view(client=..., dispatcher=...)``.
"""

from __future__ import annotations

from django.urls import path
from hatchup_psip.django.views import PSIPWebhookView

app_name = "psip"
urlpatterns = [
    path("", PSIPWebhookView.as_view(), name="webhook"),
]
