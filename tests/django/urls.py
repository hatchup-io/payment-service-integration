"""URL conf for the Django-integration test suite."""

from __future__ import annotations

from django.urls import include
from django.urls import path

urlpatterns = [
    # Default singleton path — exercises settings-backed wiring.
    path("psip/webhook/", include("hatchup_psip.django.urls")),
]
