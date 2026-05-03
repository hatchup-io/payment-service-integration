"""Runtime configuration for the Hatchup Payment Service SDK."""

from __future__ import annotations

import os
from typing import Any
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import SecretStr
from pydantic import field_validator
from pydantic import model_validator

from hatchup_psip._version import __version__

DEFAULT_BASE_URL = "https://payments.hatchup.io/api/v1/"
ENV_PREFIX_DEFAULT = "PSIP_"


class RetryPolicy(BaseModel):
    """Retry configuration for transient server errors.

    Only retries on the listed status codes. 4xx is never retried — it's
    deterministic. Network errors are retried using the same policy.
    """

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=2, ge=0, le=10)
    backoff_factor: float = Field(default=0.5, ge=0.0)
    retry_on_status: tuple[int, ...] = (502, 503, 504)


class PSIPConfig(BaseModel):
    """Connection settings for a :class:`PaymentServiceClient` instance.

    Construction precedence (documented for callers):

    1. Explicit kwargs to ``PSIPConfig(...)`` always win.
    2. :meth:`from_env` reads ``PSIP_*`` environment variables.
    3. ``hatchup_psip.django.settings.psip_config_from_django_settings()``
       reads ``settings.PSIP`` — only available when Django is importable.

    There is intentionally **no** module-level singleton: multi-tenant
    consumers (e.g. launchpad-backend, where each Company has its own API
    key) need a config per tenant.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    api_key: SecretStr
    base_url: str = DEFAULT_BASE_URL
    timeout: float = Field(default=10.0, gt=0)
    default_sandbox: bool = True
    user_agent: str = Field(
        default_factory=lambda: f"hatchup-psip/{__version__} (api=v1)",
    )
    retry: RetryPolicy = RetryPolicy()

    @field_validator("api_key")
    @classmethod
    def _check_api_key_prefix(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        if not raw.startswith("hp_"):
            raise ValueError("api_key must start with 'hp_' (payment-system convention)")
        if len(raw) < 8:
            raise ValueError("api_key looks too short to be valid")
        return v

    @field_validator("base_url")
    @classmethod
    def _normalize_base_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v if v.endswith("/") else v + "/"

    @model_validator(mode="after")
    def _check_user_agent(self) -> Self:
        if not self.user_agent.strip():
            raise ValueError("user_agent must not be empty")
        return self

    @classmethod
    def from_env(cls, prefix: str = ENV_PREFIX_DEFAULT, **overrides: Any) -> Self:
        """Build a config from ``{prefix}*`` environment variables.

        Reads ``{prefix}API_KEY``, ``{prefix}BASE_URL``, ``{prefix}TIMEOUT``,
        ``{prefix}DEFAULT_SANDBOX``. Explicit kwargs in ``overrides`` take
        precedence over env values (matches step (1) above).
        """
        env: dict[str, Any] = {}
        if (v := os.environ.get(f"{prefix}API_KEY")) is not None:
            env["api_key"] = v
        if (v := os.environ.get(f"{prefix}BASE_URL")) is not None:
            env["base_url"] = v
        if (v := os.environ.get(f"{prefix}TIMEOUT")) is not None:
            env["timeout"] = float(v)
        if (v := os.environ.get(f"{prefix}DEFAULT_SANDBOX")) is not None:
            env["default_sandbox"] = v.strip().lower() in ("1", "true", "yes", "on")
        return cls(**{**env, **overrides})


__all__ = ["DEFAULT_BASE_URL", "ENV_PREFIX_DEFAULT", "PSIPConfig", "RetryPolicy"]
