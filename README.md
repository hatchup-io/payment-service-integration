# Hatchup Payment Service Integration

[![PyPI](https://img.shields.io/pypi/v/hatchup-payment-service-integration.svg)](https://pypi.org/project/hatchup-payment-service-integration/)
[![Python](https://img.shields.io/pypi/pyversions/hatchup-payment-service-integration.svg)](https://pypi.org/project/hatchup-payment-service-integration/)
[![License](https://img.shields.io/pypi/l/hatchup-payment-service-integration.svg)](LICENSE)

Python SDK for integrating with the [Hatchup Payment Service](https://github.com/hatchup-io/hatchup-payment-system) — an internal Stripe Connect gateway.

> **Status:** 1.1.x on PyPI — sync + async client, full gateway-surface mirror (payments, refunds, customers, invoices, subscriptions, payment/setup intents, catalog, webhook endpoints), inbound-webhook HMAC + roundtrip verifiers, Django integration, contract tripwire.

## What this is

A framework-agnostic Python client for any Hatchup product that needs to take payments. The SDK proxies every Hatchup Payment Service feature behind typed resource classes, parses inbound webhooks, and ships an optional Django integration. Direct Stripe SDK access is intentionally out of scope — see [`docs/STRIPE_PASSTHROUGH.md`](docs/STRIPE_PASSTHROUGH.md).

## Install

```bash
pip install hatchup-payment-service-integration
# with Django helpers
pip install "hatchup-payment-service-integration[django]"
```

Requires Python 3.12+.

## 30-second example

```python
from pydantic import SecretStr
from hatchup_psip import PaymentServiceClient, PSIPConfig

with PaymentServiceClient(PSIPConfig(api_key=SecretStr("hp_..."))) as client:
    response = client.payments.create(
        price="9.99",
        order_id="ord_2026_05_001",
        success_webhook="https://app.example/psip/webhook/",
        failure_webhook="https://app.example/psip/webhook/",
    )
    print(response.payment_url)   # → redirect the buyer here
```

## Documentation

- [`docs/quickstart.md`](docs/quickstart.md) — install, construct a client, call every resource, error hierarchy.
- [`docs/webhooks.md`](docs/webhooks.md) — **read before deploying**. Webhooks are not signed today; the SDK's verify-by-default dispatcher is the only forgery defence.
- [`docs/django.md`](docs/django.md) — `PSIPWebhookView`, `settings.PSIP`, three wiring patterns.
- [`docs/STRIPE_PASSTHROUGH.md`](docs/STRIPE_PASSTHROUGH.md) — why the SDK does not wrap the Stripe SDK directly.
- [`CHANGELOG.md`](CHANGELOG.md) — release notes.

## Roadmap

- **M0 — toolchain bootstrap** _(0.1.0, shipped)_
- **M1 — sync client + webhooks** _(0.2.0, shipped)_
- **M2 — Django integration** _(0.3.0, shipped)_
- **M3 — async client** _(0.4.0, shipped)_: `AsyncPaymentServiceClient`, paired async resources, `AsyncWebhookDispatcher`.
- **1.0.0** _(planned)_: stabilization after launchpad-backend's first integration cycle.

## Development

```bash
# install dev deps
uv sync

# format + lint + types
just all

# run tests (skips `live` integration tests by default)
just test

# coverage report
just cov

# build wheel + sdist
just build
```

## License

MIT — see [LICENSE](LICENSE).
