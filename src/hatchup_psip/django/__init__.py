"""Optional Django integration for hatchup_psip.

Importing the SDK core (``import hatchup_psip``) does **not** require
Django. Django imports happen only inside this submodule, so consumers
who don't install the ``[django]`` extra can still use the rest of the
SDK.

Wiring overview:

- :func:`hatchup_psip.django.settings.psip_config_from_django_settings`
  reads ``settings.PSIP``.
- :func:`hatchup_psip.django.client.get_default_client` /
  :func:`hatchup_psip.django.client.get_default_dispatcher` are lazy,
  process-wide singletons used by the default :class:`PSIPWebhookView`
  for single-tenant deployments.
- Multi-tenant consumers (each tenant has its own API key) bypass the
  defaults and pass their own ``client``/``dispatcher`` to
  ``PSIPWebhookView.as_view(...)``.
"""
