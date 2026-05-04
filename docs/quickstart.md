# Quickstart

`hatchup-payment-service-integration` is a Python client for the Hatchup Payment Service — an internal Stripe Connect gateway. Every Stripe-side action goes through payment-system; this SDK is the typed, tested client.

## Install

```bash
pip install hatchup-payment-service-integration
# with the Django integration
pip install "hatchup-payment-service-integration[django]"
```

Requires Python 3.12+.

## A 30-second example

```python
from pydantic import SecretStr
from hatchup_psip import PaymentServiceClient, PSIPConfig

config = PSIPConfig(
    api_key=SecretStr("hp_..."),
    base_url="https://payments.hatchup.io/api/v1/",
)

with PaymentServiceClient(config) as client:
    # Create a Checkout session for a new order.
    response = client.payments.create(
        price="9.99",
        order_id="ord_2026_05_001",
        success_webhook="https://app.example/psip/webhook/",
        failure_webhook="https://app.example/psip/webhook/",
    )
    print(response.payment_url)        # → redirect the buyer here
    print(response.session_id)         # Stripe Checkout session id

    # Later, after the buyer pays:
    transaction = client.transactions.get("ord_2026_05_001")
    assert transaction.status == "succeeded"
```

## Constructing a config

Three sources, in priority order:

```python
# 1. Explicit kwargs (always win):
PSIPConfig(api_key=SecretStr("hp_..."), timeout=15.0)

# 2. PSIP_* env vars:
PSIPConfig.from_env()
# Reads PSIP_API_KEY, PSIP_BASE_URL, PSIP_TIMEOUT, PSIP_DEFAULT_SANDBOX.
# Explicit kwargs to from_env() override env values:
PSIPConfig.from_env(timeout=30.0)

# 3. Django settings:
from hatchup_psip.django.settings import psip_config_from_django_settings
psip_config_from_django_settings()   # reads settings.PSIP — see docs/django.md
```

There is intentionally **no module-level singleton client**. Multi-tenant consumers (each tenant has its own API key) build one `PaymentServiceClient` per tenant.

## Client lifecycle

`PaymentServiceClient` owns an `httpx.Client` (a connection pool). Use it as a context manager so the pool is released cleanly:

```python
with PaymentServiceClient(config) as client:
    ...
# pool released here
```

For long-lived processes, build the client once at startup and call `.close()` at shutdown. Don't construct one per request.

## Resources

| Attribute | Methods | Endpoint |
|---|---|---|
| `client.payments` | `create(req \| **kwargs)` | `POST /payment` |
| | `recreate(order_id, **overrides)` | `POST /repayment` |
| `client.verify` | `__call__(order_id, price, currency="usd")` | `POST /verify` |
| `client.transactions` | `list(filters \| **kwargs)` | `GET /transactions` |
| | `get(id_or_order_id)` | `GET /transactions/{x}` |
| | `iter_all(**filters)` | paginates `list()` |
| `client.webhooks` | `parse(body)` | (no HTTP) |
| | `verify_event(event)` | round-trips `transactions.get` |

Write methods accept either a built pydantic request model or kwargs forwarded to its constructor:

```python
# Kwargs path:
client.payments.create(price="9.99", order_id="ord_1", success_webhook=..., failure_webhook=...)

# Model path (useful when building requests in batch / from forms):
from hatchup_psip.models import PaymentCreateRequest
req = PaymentCreateRequest(price="9.99", order_id="ord_1", ...)
client.payments.create(req)
```

`iter_all` walks every page until the server returns a partial page (`len(results) < page_size`). Note the server's `count` field is the *current page length*, not the total — don't rely on it for pagination.

## Errors

Every SDK-raised exception derives from `PSIPError`:

```
PSIPError
├── PSIPNetworkError              transport failure (after retries)
├── PSIPProtocolError             server response or webhook payload malformed
│   ├── PSIPWebhookValidationError    webhook body bad
│   └── PSIPWebhookForgeryError       webhook didn't match server's record
└── PSIPAPIError                  HTTP 4xx/5xx
    ├── PSIPAuthError                 401
    ├── PSIPValidationError           400
    ├── PSIPNotFoundError             404
    └── PSIPServerError               5xx
```

Every `PSIPAPIError` carries `.status_code`, `.message`, `.raw`, and `.request_id` (None until payment-system emits one).

User-input validation errors (e.g. negative `price`) propagate as `pydantic.ValidationError` — they're caller bugs, not server contract failures, and pydantic's detailed messages are the most useful debugging artifact.

## Where next

- [`docs/webhooks.md`](webhooks.md) — receiving webhooks from payment-system. **Read this before deploying** — webhook payloads are not signed today, and the dispatcher's verify-by-default behavior is the SDK's only forgery defence.
- [`docs/django.md`](django.md) — wiring `PSIPWebhookView`, settings.PSIP, multi-tenant patterns.
- [`docs/STRIPE_PASSTHROUGH.md`](STRIPE_PASSTHROUGH.md) — why this SDK does not wrap the Stripe SDK directly.
