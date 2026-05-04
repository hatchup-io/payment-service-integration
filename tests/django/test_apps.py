"""Tests for the optional PSIPAppConfig validation."""

from __future__ import annotations

from typing import Any

import pytest
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from hatchup_psip.django.apps import PSIPAppConfig


def test_app_config_registered() -> None:
    cfg = apps.get_app_config("hatchup_psip")
    assert isinstance(cfg, PSIPAppConfig)


@override_settings(PSIP={"API_KEY": "wrong_prefix"})
def test_ready_fails_fast_on_invalid_settings() -> None:
    cfg = apps.get_app_config("hatchup_psip")
    with pytest.raises(ImproperlyConfigured):
        cfg.ready()


def test_ready_is_silent_when_psip_not_set(settings: Any) -> None:
    """Multi-tenant deployments may have no settings.PSIP — ready() must not insist."""
    del settings.PSIP
    cfg = apps.get_app_config("hatchup_psip")
    # No exception expected.
    cfg.ready()
