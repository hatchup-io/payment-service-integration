"""Minimal Django settings for the SDK's Django-integration tests."""

from __future__ import annotations

SECRET_KEY = "psip-test-only-not-a-real-secret"

DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "hatchup_psip.django",
]

MIDDLEWARE: list[str] = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

ROOT_URLCONF = "tests.django.urls"
USE_TZ = True

# Test PSIP config — points respx mocks at this base.
PSIP = {
    "API_KEY": "hp_test_django_key_xyz",
    "BASE_URL": "https://test.example.com/api/v1/",
    "TIMEOUT": 5.0,
}
