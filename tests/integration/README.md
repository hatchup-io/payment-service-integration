# Integration tests

These tests exercise the SDK against a **real running instance** of `hatchup-payment-system`. They are skipped by default so `pytest` (no flags) stays fast and offline.

```bash
just test             # runs everything except `live`-marked tests (default)
just test-live        # runs only `live`-marked tests
```

## What they verify

- A live `payments.create()` returns a real Stripe Checkout URL.
- `transactions.list()` and `transactions.get()` parse responses from the real server.
- `verify(order_id, price)` reflects post-payment state.

The Stripe-side fanout still uses **test mode keys** (configured per-project on the payment-system dashboard). No real money moves.

## Prerequisites

1. **A running payment-system.** Use the docker-compose at `hatchup-payment-system/docker-compose.yml`:

   ```bash
   cd /path/to/hatchup-payment-system
   docker compose up -d
   ```

2. **A project + API key.** The dashboard at `http://localhost:8010/login/` (or whatever port your compose maps) lets you create a project and generate a key. Copy the `hp_…` key — it's shown **once**.

3. **Stripe test keys configured on the project.** Through the dashboard, set the project's `stripe_test_publishable_key`, `stripe_test_secret_key`, and `stripe_webhook_secret_test` to your Stripe test-mode credentials.

## Environment

Set these before running:

```bash
export PSIP_INTEGRATION_BASE_URL="http://localhost:8010/api/v1/"
export PSIP_INTEGRATION_API_KEY="hp_..."         # the key from step 2
export PSIP_INTEGRATION_SUCCESS_URL="https://example.test/cb/ok"
export PSIP_INTEGRATION_FAILURE_URL="https://example.test/cb/fail"
```

Tests skip gracefully if these are unset (no surprise failures in CI).

## Running

```bash
# All live tests
uv run pytest -m live

# Or via just:
just test-live

# Verbose, single test:
uv run pytest tests/integration/test_live_e2e.py::test_create_checkout_returns_real_stripe_url -v
```

## CI

CI does **not** run live tests. They are intentionally manual — the Stripe sandbox is shared, and rate-limiting an entire CI fleet against it is a footgun.

If you want CI coverage of the live path, gate it behind a manual workflow trigger and provide secrets via the CI's secret store.
