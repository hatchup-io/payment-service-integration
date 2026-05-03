# Hatchup Payment Service Integration

Python SDK for integrating with the [Hatchup Payment Service](https://github.com/hatchup-io/hatchup-payment-system) — a multi-tenant Stripe Connect gateway.

> **Status:** Pre-alpha. M0 (toolchain bootstrap) only. Public API does not exist yet.

## What this is

A framework-agnostic Python client for any Hatchup product that needs to take payments. The SDK proxies every Hatchup Payment Service feature behind typed resource classes, parses inbound webhooks, and ships an optional Django integration. Direct Stripe SDK access is intentionally out of scope — see [`docs/STRIPE_PASSTHROUGH.md`](docs/STRIPE_PASSTHROUGH.md) (forthcoming).

## Install

```bash
pip install hatchup-payment-service-integration
# with Django helpers
pip install "hatchup-payment-service-integration[django]"
```

Requires Python 3.12+.

## Roadmap

- **M0 — toolchain bootstrap** _(current)_: `pyproject.toml`, ruff/mypy/pytest, `justfile`, package skeleton.
- **M1 — sync client + webhooks**: `PaymentServiceClient` covering `payments`, `verify`, `transactions`; `WebhookDispatcher` with verify-by-default forgery guard.
- **M2 — Django integration**: `PSIPWebhookView`, settings adapter.
- **M3 — async client**.

See the design notes in [`docs/`](docs/) once they land.

## Development

```bash
# install dev deps
uv sync

# format + lint + types
just all

# run tests (skips `live` integration tests by default)
just test

# build wheel + sdist
just build
```

## License

MIT — see [LICENSE](LICENSE).
