"""Build a :class:`PSIPConfig` from a Django ``settings.PSIP`` mapping.

Recognised keys (all uppercase, Django convention)::

    settings.PSIP = {
        "API_KEY": "hp_...",                  # required
        "BASE_URL": "https://payments...",    # optional
        "TIMEOUT": 5.0,                       # optional
        "DEFAULT_SANDBOX": True,              # optional
        "USER_AGENT": "...",                  # optional
    }

Unknown keys are ignored — silently — so consumers can prototype with a
larger settings dict without breaking validation.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pydantic import SecretStr
from pydantic import ValidationError

from hatchup_psip.config import PSIPConfig


def psip_config_from_django_settings() -> PSIPConfig:
    """Read ``settings.PSIP`` and return a validated :class:`PSIPConfig`.

    Raises :class:`django.core.exceptions.ImproperlyConfigured` if
    ``settings.PSIP`` is missing, malformed, or fails pydantic validation.
    """
    raw: Any = getattr(settings, "PSIP", None)
    if not raw:
        raise ImproperlyConfigured(
            "settings.PSIP is not configured. Set settings.PSIP = "
            "{'API_KEY': 'hp_...'} (BASE_URL/TIMEOUT/DEFAULT_SANDBOX optional).",
        )
    if not isinstance(raw, dict):
        raise ImproperlyConfigured(
            f"settings.PSIP must be a mapping, got {type(raw).__name__}.",
        )

    kwargs: dict[str, Any] = {}
    if "API_KEY" in raw:
        kwargs["api_key"] = SecretStr(raw["API_KEY"])
    if "BASE_URL" in raw:
        kwargs["base_url"] = raw["BASE_URL"]
    if "TIMEOUT" in raw:
        kwargs["timeout"] = raw["TIMEOUT"]
    if "DEFAULT_SANDBOX" in raw:
        kwargs["default_sandbox"] = raw["DEFAULT_SANDBOX"]
    if "USER_AGENT" in raw:
        kwargs["user_agent"] = raw["USER_AGENT"]

    try:
        return PSIPConfig(**kwargs)
    except ValidationError as exc:
        raise ImproperlyConfigured(
            f"settings.PSIP failed validation: {exc}",
        ) from exc


__all__ = ["psip_config_from_django_settings"]
