# payment-service-integration

[![PyPI](https://img.shields.io/pypi/v/hatchup-payment-service-integration.svg)](https://pypi.org/project/hatchup-payment-service-integration/)
[![Python](https://img.shields.io/pypi/pyversions/hatchup-payment-service-integration.svg)](https://pypi.org/project/hatchup-payment-service-integration/)
[![License](https://img.shields.io/pypi/l/hatchup-payment-service-integration.svg)](LICENSE)

The Python SDK for the [Hatchup Payment Service](https://github.com/hatchup-io/hatchup-payment-system), the internal Stripe Connect gateway. It is published on PyPI as `hatchup-payment-service-integration` and imported as `hatchup_psip`. Hatchup backends that take payments use it, for example `pathwise_backend`, `bayatgroup-backend` and `launchpad-backend-project`. The gateway it calls runs on the production swarm in the `payment_service` stack at `https://api.payment.service.hatchup.capital`; the production and `_dev` services of the consumers set `PSIP_BASE_URL` to `https://api.payment.service.hatchup.capital/api/v1/`.

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

## Use

### 30-second example

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
    print(response.payment_url)  # → redirect the buyer here
```

`PSIPConfig.from_env()` builds the config from `PSIP_API_KEY`, `PSIP_BASE_URL`, `PSIP_TIMEOUT` and `PSIP_DEFAULT_SANDBOX`. The built-in default base URL is `https://payments.hatchup.io/api/v1/`, which is not the deployed gateway, so set `PSIP_BASE_URL` (or `base_url`) to `https://api.payment.service.hatchup.capital/api/v1/`. API keys come from the gateway; never commit one.

### Documentation

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
- **Next**: TypeScript port as `@hatchup-io/payment-service-integration` in [`hatchup-io/payment-service-integration-node`](https://github.com/hatchup-io/payment-service-integration-node). Its client and REST resources are implemented; webhook parsing is pending and it is not on npm yet. See [`docs/NODE_SDK_PLAN.md`](docs/NODE_SDK_PLAN.md) (which still uses the earlier `@hatchup` scope).

## Test

There is no CI workflow for pull requests; run the checks locally before you open one. The release workflow runs `just all` and `just test` before it publishes.

```bash
# install dev deps
uv sync

# format + lint + types (ruff format, ruff check --fix, ruff check, mypy src)
just all

# run tests (skips `live` integration tests by default)
just test

# live integration tests against a local payment-system
just test-live

# coverage report
just cov

# pre-commit hooks (whitespace, YAML/TOML checks, ruff)
just pre-commit
```

## Release

Build a wheel and sdist locally with `just build`. To publish:

1. Bump `[project].version` in [`pyproject.toml`](pyproject.toml) and add a matching `## [X.Y.Z]` entry to [`CHANGELOG.md`](CHANGELOG.md).
2. Merge the change to `main` through a pull request.
3. Tag and push:
   ```bash
   git tag -a vX.Y.Z -m "release: vX.Y.Z"
   git push origin vX.Y.Z
   ```
4. [`.github/workflows/release.yml`](.github/workflows/release.yml) verifies the tag matches `pyproject` + changelog, runs `just all` + `just test` + `just build`, then publishes to PyPI via OIDC (no tokens). The publish job is gated behind the `pypi` GitHub environment.

## Related repositories

- [hatchup-payment-system](https://github.com/hatchup-io/hatchup-payment-system): the gateway this SDK calls.
- [payment-service-integration-node](https://github.com/hatchup-io/payment-service-integration-node): the TypeScript port.
- [pathwise_backend](https://github.com/hatchup-io/pathwise_backend), [bayatgroup-backend](https://github.com/hatchup-io/bayatgroup-backend) and [launchpad-backend-project](https://github.com/hatchup-io/launchpad-backend-project): backends that depend on it.
- [production](https://github.com/hatchup-io/production): deploys the `payment_service` stack and sets each consumer's `PSIP_BASE_URL`.

## License

MIT — see [LICENSE](LICENSE).
