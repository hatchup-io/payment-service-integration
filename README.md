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
- [`docs/webhooks.md`](docs/webhooks.md) — **read before deploying**. Covers HMAC signature verification (`verify_signature`) for new `WebhookEndpoint` deliveries and the verify-by-default roundtrip dispatcher for legacy per-row webhooks.
- [`docs/django.md`](docs/django.md) — `PSIPWebhookView`, `settings.PSIP`, three wiring patterns.
- [`docs/STRIPE_PASSTHROUGH.md`](docs/STRIPE_PASSTHROUGH.md) — why the SDK does not wrap the Stripe SDK directly.
- [`docs/PYPI_PUBLISH_PLAN.md`](docs/PYPI_PUBLISH_PLAN.md) — release pipeline (OIDC, tag-driven workflow, versioning policy).
- [`CHANGELOG.md`](CHANGELOG.md) — release notes.

## Roadmap

- **M0 — toolchain bootstrap** _(0.1.0)_ — shipped
- **M1 — sync client + webhooks** _(0.2.0)_ — shipped
- **M2 — Django integration** _(0.3.0)_ — shipped
- **M3 — async client** _(0.4.0)_ — shipped: `AsyncPaymentServiceClient`, paired async resources, `AsyncWebhookDispatcher`.
- **M4 — full gateway-surface mirror** _(1.0.0)_ — shipped: customers, payment/setup intents, catalog, subscriptions, invoices, webhook endpoints + outbound-webhook taxonomy parsers + HMAC signature verifier for `X-Hatchup-Signature`.
- **1.1.x** — shipped on PyPI: per-request `Idempotency-Key` headers, customer-attached checkout sessions, invoice number passthrough, opt-in Stripe Invoice generation, `payments.refund(transaction_id, ...)`.
- **Next**: TypeScript port at `@hatchup/payment-service-integration` on npm — see [`docs/NODE_SDK_PLAN.md`](docs/NODE_SDK_PLAN.md).

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

### Cutting a release

1. Bump `[project].version` in [`pyproject.toml`](pyproject.toml) and add a matching `## [X.Y.Z]` entry to [`CHANGELOG.md`](CHANGELOG.md).
2. Commit on `main`.
3. Tag and push:
   ```bash
   git tag -a vX.Y.Z -m "release: vX.Y.Z"
   git push origin vX.Y.Z
   ```
4. [`.github/workflows/release.yml`](.github/workflows/release.yml) verifies the tag matches `pyproject` + changelog, runs `just all` + `just test` + `just build`, then publishes to PyPI via OIDC (no tokens). The publish job is gated behind the `pypi` GitHub environment.

## License

MIT — see [LICENSE](LICENSE).
