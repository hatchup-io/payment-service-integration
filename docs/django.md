# Django integration

The optional `[django]` extra ships:

- `PSIPWebhookView` — a CSRF-exempt DRF endpoint that parses + verifies + dispatches webhooks
- `psip_config_from_django_settings()` — a `settings.PSIP` → `PSIPConfig` adapter
- `get_default_client()` / `get_default_dispatcher()` — lazy process-wide singletons for single-tenant deployments
- A `PSIPAppConfig` for optional boot-time settings validation

Importing `hatchup_psip` core does **not** require Django. Every Django import lives under `hatchup_psip.django.*`.

## Install

```bash
pip install "hatchup-payment-service-integration[django]"
```

## Three wiring options

### 1. Default singleton (single-tenant, recommended for most apps)

```python
# myproject/settings.py
PSIP = {
    "API_KEY": "hp_...",
    "BASE_URL": "https://payments.hatchup.io/api/v1/",   # optional
    "TIMEOUT": 10.0,                                     # optional
    "DEFAULT_SANDBOX": True,                             # optional
    "USER_AGENT": "myapp/1.0",                           # optional
}

INSTALLED_APPS = [
    # ...
    "hatchup_psip.django",   # OPTIONAL — adds boot-time validation of settings.PSIP
]

# myproject/urls.py
from django.urls import include, path

urlpatterns = [
    path("psip/webhook/", include("hatchup_psip.django.urls")),
]
```

Register handlers in your app's `ready()` hook:

```python
# myapp/apps.py
from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self):
        from hatchup_psip.django.client import get_default_dispatcher
        from myapp.models import Order

        dispatcher = get_default_dispatcher()

        @dispatcher.on("payment.completed")
        def mark_order_paid(event):
            Order.objects.filter(reference=event.order_id).update(paid=True)
```

`get_default_client()` and `get_default_dispatcher()` are `@cache`d — the client is built lazily on first access and reused for the process lifetime. Tests must call `.cache_clear()` between cases (see [`tests/django/conftest.py`](../tests/django/conftest.py) for the pattern).

### 2. Explicit injection via `as_view(client=..., dispatcher=...)`

For multi-tenant apps (e.g. one payment-system project per Company), build one `PaymentServiceClient` per tenant and route URLs accordingly:

```python
# myproject/urls.py
from django.urls import path
from hatchup_psip.django.views import PSIPWebhookView
from myapp.psip import client_for_company, dispatcher_for_company

def _build_view(company_id: str):
    client = client_for_company(company_id)
    dispatcher = dispatcher_for_company(company_id, client)
    return PSIPWebhookView.as_view(client=client, dispatcher=dispatcher)

urlpatterns = [
    path("psip/<str:company_id>/webhook/", _build_view, name="psip-webhook"),
]
```

Note: in practice you'd resolve `client`/`dispatcher` per-request (see option 3) rather than baking them into the URL conf.

### 3. Subclass and override `get_client` / `get_dispatcher`

For per-request resolution (e.g. tenant from URL kwargs):

```python
from hatchup_psip.django.views import PSIPWebhookView

class CompanyWebhookView(PSIPWebhookView):
    def get_client(self):
        company_id = self.kwargs["company_id"]
        return PaymentServiceClient(_psip_config_for(company_id))

    def get_dispatcher(self):
        # Cache per-company dispatcher externally so handler registration
        # doesn't repeat on every request.
        return _registry[self.kwargs["company_id"]]


# urls.py
urlpatterns = [
    path("psip/<str:company_id>/webhook/", CompanyWebhookView.as_view(), name="psip-webhook"),
]
```

## Status codes

| Outcome | Status |
|---|---|
| Body parsed, verified, all handlers ran cleanly | **200** |
| Body wasn't valid JSON or didn't match `PaymentCompletedEvent` | **400** |
| Verifier rejected the payload (forgery) | **403** |
| Any handler raised | **500** (Django default — `ExceptionGroup` propagates) |
| Wrong HTTP method | **405** |

## CSRF

`PSIPWebhookView.dispatch` is wrapped with `@method_decorator(csrf_exempt)` so external POSTs aren't rejected by Django's CSRF middleware. The `tests/django/test_views.py:test_csrf_exempt` case exercises this path with `Client(enforce_csrf_checks=True)`.

## Multi-tenant guidance

The default singleton (`get_default_client` / `get_default_dispatcher`) is appropriate when the entire Django process represents **one** payment-system project. If different parts of your system use different API keys (e.g. launchpad-backend, where each Company has its own credentials), bypass the singleton entirely:

- One `PaymentServiceClient` per tenant — cache externally (per-tenant `functools.cache` keyed on Company).
- One `WebhookDispatcher` per tenant. Register handlers separately on each, or share a closure-based handler that reads tenant-specific state.
- Use option 2 or 3 above to wire URL conf.

The default URL conf (`include("hatchup_psip.django.urls")`) only handles the single-tenant case. Multi-tenant deployments build their own URL conf and skip the include.

## `INSTALLED_APPS` is optional

Adding `"hatchup_psip.django"` to `INSTALLED_APPS` only buys you fail-fast validation of `settings.PSIP` at process boot (via `PSIPAppConfig.ready()`). The webhook view works without it. Multi-tenant deployments without a global `settings.PSIP` can still register the app — `ready()` is silent when `settings.PSIP` is undefined.

## Settings reference

```python
PSIP = {
    "API_KEY":         str,           # required — must start with "hp_"
    "BASE_URL":        str,           # optional — default https://payments.hatchup.io/api/v1/
    "TIMEOUT":         float | int,   # optional — default 10.0 seconds
    "DEFAULT_SANDBOX": bool,          # optional — default True
    "USER_AGENT":      str,           # optional — default "hatchup-psip/<ver> (api=v1)"
}
```

Unknown keys are silently ignored. Validation failures raise `django.core.exceptions.ImproperlyConfigured` with the underlying pydantic error.
