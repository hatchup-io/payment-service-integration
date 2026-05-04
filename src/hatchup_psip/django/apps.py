"""Django AppConfig — optional, for boot-time settings validation.

``INSTALLED_APPS = [..., "hatchup_psip.django"]`` is **not required**.
The :class:`PSIPWebhookView` works without it. Registering the app only
buys you fail-fast validation of ``settings.PSIP`` at process boot.
"""

from __future__ import annotations

from django.apps import AppConfig
from django.conf import settings

from hatchup_psip.django.settings import psip_config_from_django_settings


class PSIPAppConfig(AppConfig):
    name = "hatchup_psip.django"
    label = "hatchup_psip"
    verbose_name = "Hatchup Payment Service Integration"

    def ready(self) -> None:
        # Only validate if the consumer opted into settings-based config.
        # Multi-tenant deployments may have no global settings.PSIP at all.
        if not hasattr(settings, "PSIP"):
            return
        psip_config_from_django_settings()
