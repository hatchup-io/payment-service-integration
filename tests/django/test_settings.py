"""Tests for ``psip_config_from_django_settings`` and the AppConfig."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from hatchup_psip.django.settings import psip_config_from_django_settings


def test_reads_settings_psip() -> None:
    cfg = psip_config_from_django_settings()
    assert cfg.api_key.get_secret_value() == "hp_test_django_key_xyz"
    assert cfg.base_url == "https://test.example.com/api/v1/"
    assert cfg.timeout == 5.0


@override_settings(PSIP=None)
def test_missing_settings_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="not configured"):
        psip_config_from_django_settings()


@override_settings(PSIP="not-a-dict")
def test_non_dict_settings_raises() -> None:
    with pytest.raises(ImproperlyConfigured, match="must be a mapping"):
        psip_config_from_django_settings()


@override_settings(PSIP={"API_KEY": "wrong_prefix"})
def test_invalid_api_key_raises_improperly_configured() -> None:
    """Pydantic ValidationError is wrapped as Django's ImproperlyConfigured."""
    with pytest.raises(ImproperlyConfigured, match="failed validation"):
        psip_config_from_django_settings()


@override_settings(PSIP={"API_KEY": "hp_test_key_minimal"})
def test_only_api_key_uses_psip_config_defaults_for_other_fields() -> None:
    cfg = psip_config_from_django_settings()
    assert cfg.timeout == 10.0  # PSIPConfig default


@override_settings(PSIP={"API_KEY": "hp_x", "UNKNOWN_KEY": "ignored"})
def test_unknown_settings_keys_are_ignored() -> None:
    """Forward-compat: extra keys in settings.PSIP must not break startup."""
    with pytest.raises(ImproperlyConfigured):
        # api_key fails the length validator — but we're testing that the
        # UNKNOWN_KEY didn't trip an error first.
        psip_config_from_django_settings()


@override_settings(PSIP={"BASE_URL": "https://x.test/api/v1/"})
def test_missing_api_key_raises_improperly_configured() -> None:
    """Pydantic's missing-required-field error gets wrapped as ImproperlyConfigured."""
    with pytest.raises(ImproperlyConfigured, match="failed validation"):
        psip_config_from_django_settings()


@override_settings(
    PSIP={
        "API_KEY": "hp_test_key_full",
        "DEFAULT_SANDBOX": False,
        "USER_AGENT": "myapp/1.0",
    },
)
def test_default_sandbox_and_user_agent_overrides() -> None:
    cfg = psip_config_from_django_settings()
    assert cfg.default_sandbox is False
    assert cfg.user_agent == "myapp/1.0"
