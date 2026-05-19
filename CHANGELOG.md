# Changelog

All notable changes to `hatchup-payment-service-integration` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.4] — 2026-05-19

### Added

- **`PaymentCreateRequest.create_invoice`** — opt the hosted Checkout into Stripe Invoice generation. When `True` (and `payment_type="one_time"`), the gateway forwards `invoice_creation={"enabled": True}` to `stripe.checkout.Session.create()` so the session completion materializes a real Invoice (with `number`, `hosted_invoice_url`, `invoice_pdf`). Required by wallet-funding flows that surface a billing history. Default `False` — existing callers see no behaviour change.

### Compatibility

- Additive; defaults preserve existing behaviour.
- Server-side support: requires the matching payment-system bump. Older gateways ignore the new request field; the SDK still serializes it, so a forward-incompatible deployment won't error — it just won't generate the invoice.

### Notes

- Pairs with a gateway change to `GET /api/v1/invoices` that flips to a **live Stripe list** (with local-mirror upsert) when the request scopes to a specific `customer=`. Before, the gateway returned only invoices that had landed in the local mirror via webhook; subscription dunning + one-off invoices created on deployments that never received our webhook were invisible. No SDK API change — same `invoices.list(customer=…, page=…, page_size=…)` call, just more complete data.

## [1.1.3] — 2026-05-19

### Added

- **`Invoice.number`** — Stripe's human-readable invoice number (e.g. `IN_TEST-0001`) is now mirrored on `Invoice` and surfaced by `invoices.list()` / `invoices.retrieve()`. Was always returned by Stripe but dropped during gateway serialization; both sides now preserve it. Optional (`None` for invoices Stripe hasn't numbered yet).
- **`PaymentCreateRequest.customer`** — optional Stripe Customer id (`cus_…`) attaches the Checkout Session to a known Customer so saved cards + the Billing Portal can resolve back to it. Required for wallet-funding flows that need card-on-file behaviour. Server passes through to `stripe.checkout.Session.create(customer=…)`.

### Compatibility

- Additive; existing callers are unaffected.
- Server-side support for both fields requires the matching payment-system bump (see [STRIPE_GATEWAY_PLAN.md](https://github.com/hatchup-io/hatchup-payment-system/blob/main/docs/STRIPE_GATEWAY_PLAN.md)). Older servers ignore the new request field and omit `number` from responses (deserializes as `None`).

### Notes for consumers

- Outbound webhook bodies on the gateway now include a stable `event_id` of the form `<event_type>:<resource_id>` (e.g. `payment.completed:cs_test_123`). Pure server change — no SDK API change — but parsers can rely on the field being present going forward, and the [INTEGRATION_GUIDE](https://github.com/hatchup-io/hatchup-payment-system/blob/main/docs/INTEGRATION_GUIDE.md) §11 promise is now backed by code.

## [1.1.2] — 2026-05-16

### Added

- **`payments.verify_session(session_id)`** (sync + async) — wraps the new payment-system endpoint `POST /api/v1/checkout-sessions/<session_id>/verify`. Retrieves the Checkout Session live from Stripe and applies the completion to the local Transaction on the gateway side; idempotent. Use as a client-initiated fallback when the webhook fan-out can't be relied on (the user closes the tab right after paying, the webhook isn't configured yet, etc.). Returns a `CheckoutSessionVerifyResponse` with the session_id, order_id, payment_status (`paid`/`unpaid`/`no_payment_required`), amount, currency, and transaction_id (populated only when `paid`).

### Compatibility

- Additive; existing callers are unaffected.
- Server-side support: requires payment-system at commit `1d13b63` or later. Older servers return a 404 on the new path.

## [1.1.1] — 2026-05-13

### Added

- **`email` filter on `customers.list()`** (sync + async) — forwards to the existing `?email=` query param on the gateway's `GET /api/v1/customers` (case-insensitive exact match). Lets consumers implement a get-or-create pattern by recovering from a 409 on `customers.create()` and adopting the existing row.

### Compatibility

- New kwarg is keyword-only with a `None` default; existing `customers.list()` callers are unaffected.
- Server-side support: the `email` query param has been present on the payment-system since the customers endpoint was introduced — no payment-system bump required.

## [0.5.0] — 2026-05-06

### Added

- **`PaymentCreateRequest.metadata`** and **`RepaymentRequest.metadata`** — optional `dict[str, str]` field forwarded to the Stripe Checkout Session's metadata. Used by SHARED-mode launchpad consumers to attribute Stripe-side reporting back to the right user/project. Server enforces Stripe's constraints (≤50 keys, ≤40-char keys, ≤500-char values, scalar-only values) and silently strips the reserved `payment_request_id` key on merge.
- **`TransactionListFilters.order_id_startswith`** — server-side prefix filter on `Transaction.order_id`. SHARED-mode consumers pass the project's slug prefix here so the server filters before responding instead of returning every other project's rows. Composes with the existing date / status / sandbox / verified filters.

### Changed

- `tests/contract/fixtures/server_contract.json` updated to include `metadata` on the payment/repayment requests and `order_id_startswith` on the transactions list query params. Captured against `hatchup-payment-system feat/integrate-with-PISP @ 9d32b43`.

### Compatibility

- Both fields are optional with empty/no-filter defaults — every 0.4.0 caller continues to work unchanged.
- Server-side support: requires payment-system at commit 9d32b43 or later. Older servers will return a 400 if you pass `metadata` (unknown body key) or silently ignore `order_id_startswith` (unknown query param). Don't bump to 0.5.0 in your consumer until the server is updated.

## [0.4.0] — 2026-05-04

### Added

- **Async client (M3)**:
  - `AsyncTransport` (in `transport.py`) — `httpx.AsyncClient` wrapper. Same envelope decoding + error classification as `Transport` (the helpers are now module-level functions shared by both); retries use `asyncio.sleep` so they don't block the event loop.
  - `AsyncPaymentServiceClient` (in `client.py`) — same surface as `PaymentServiceClient`, awaitable. Async context manager via `__aenter__`/`__aexit__`/`aclose()`.
  - Async resource pairs sharing request-build/response-parse helpers with the sync versions: `AsyncPaymentsResource`, `AsyncVerifyResource`, `AsyncTransactionsResource` (with `async for` `iter_all`), `AsyncWebhooksResource`.
  - `AsyncWebhookDispatcher` — accepts both async and sync handlers (sync handlers are called directly, no thread offload). Same `ExceptionGroup` aggregation. Async verifier (typically `async_client.webhooks.verify_event`).
  - `async_verify_event(event, transactions)` — async forgery guard.

### Changed

- Refactored `Transport`'s `_handle_response`, `_decode_envelope`, `_classify_error` from class statics to module-level functions so `AsyncTransport` shares them — no behavior change for `Transport`.
- Added `pytest-asyncio` (>=0.24) to dev deps; `asyncio_mode = "auto"` in `[tool.pytest.ini_options]` so async test functions don't need a marker.

### Tests

- Added test suites for `AsyncTransport`, `AsyncPaymentServiceClient`, async resource pairs, `AsyncWebhookDispatcher`, and `async_verify_event`.

## [0.3.5] — 2026-05-04

### Added

- **Server-contract tripwire** (`tests/contract/`) — captured digest of payment-system's `apps/payments/schema.py` plus 11 test cases that diff each SDK pydantic model's field set against the snapshot. Catches schema drift (server adding/removing/renaming a field without an SDK update).
- **Live-server integration skeleton** (`tests/integration/`) — `pytest -m live` opt-in, env-var based config (`PSIP_INTEGRATION_*`), README documenting docker-compose setup. CI does not run these.

## [0.3.0] — 2026-05-04

### Added

- **Django integration** (optional `[django]` extra):
  - `PSIPWebhookView` — CSRF-exempt DRF `APIView` that parses, verifies, and dispatches inbound webhooks. Returns 200/400/403 for accepted/parse-failure/forgery; 405 on wrong method.
  - `psip_config_from_django_settings()` — reads `settings.PSIP = {"API_KEY": ..., ...}` and wraps `pydantic.ValidationError` as `django.core.exceptions.ImproperlyConfigured`.
  - `get_default_client()` / `get_default_dispatcher()` — `@cache`d process-wide singletons used by the default URL conf for single-tenant setups.
  - `PSIPAppConfig` — optional `INSTALLED_APPS` entry that fail-fast validates `settings.PSIP` at boot when defined.
  - `hatchup_psip.django.urls` — one path mapping for `include()`-based mounting.
- `docs/quickstart.md`, `docs/webhooks.md`, `docs/django.md`, `docs/STRIPE_PASSTHROUGH.md`.

### Notes

- Importing `hatchup_psip` core does **not** require Django. Every Django import lives under `hatchup_psip.django.*`.
- Multi-tenant deployments (per-tenant API keys) bypass the singleton helpers and pass their own `client`/`dispatcher` to `PSIPWebhookView.as_view(...)` — see `docs/django.md`.

## [0.2.0] — 2026-05-04

### Added

- `PaymentServiceClient` — the high-level synchronous facade. Owns a `Transport`, exposes `payments`, `verify`, `transactions`, and `webhooks` resources. Context-manager safe.
- Resource proxies:
  - `PaymentsResource.create()` and `recreate()` — accept either a built `PaymentCreateRequest`/`RepaymentRequest` or kwargs.
  - `VerifyResource.__call__()` — `client.verify(order_id, price)` reads naturally; coerces price from `Decimal | str | int | float`.
  - `TransactionsResource.list()`, `get()`, and `iter_all()` — `iter_all` paginates via `has_more` (server's `count` is page-length, not total).
  - `WebhooksResource` — composes `TransactionsResource` for the forgery roundtrip.
- Pydantic v2 models for every endpoint request/response (`PaymentCreateRequest/Response`, `RepaymentRequest`, `VerifyRequest/Response`, `Transaction`, `TransactionListFilters`, `TransactionPage`, `PaymentCompletedEvent`, plus a generic `ApiEnvelope[T]`).
- Webhook handling:
  - `parse_payment_completed(body)` — accepts `bytes | str | dict`, raises `PSIPWebhookValidationError` on JSON or schema failure.
  - `verify_event(event, transactions)` — server roundtrip forgery guard. Maps webhook `"completed"` → server `"succeeded"`. Aggregates every mismatch into one error message.
  - `WebhookDispatcher` — `@on(event_type)` decorator, `dispatch(event, verify=True)` runs the verifier first, handler exceptions aggregated as `ExceptionGroup`.
- New exceptions: `PSIPWebhookValidationError`, `PSIPWebhookForgeryError` (both subclass `PSIPProtocolError`).

## [0.1.0] — 2026-05-04

### Added

- Initial toolchain bootstrap: `pyproject.toml` (`[tool.uv] package = true`), `.python-version` (3.12), pre-commit, `justfile`, `py.typed` marker.
- `PSIPConfig` (pydantic v2, frozen) with `from_env()` factory and `RetryPolicy` for transient-error retries (502/503/504 only).
- Synchronous `Transport` wrapping `httpx.Client`. Centralizes envelope decoding, `Authorization`/`User-Agent` headers, retry policy, and HTTP-status → exception classification.
- Exception hierarchy rooted at `PSIPError`: `PSIPNetworkError`, `PSIPProtocolError`, `PSIPAPIError` (with `PSIPAuthError`, `PSIPValidationError`, `PSIPNotFoundError`, `PSIPServerError` subclasses).
- Test scaffolding: `pytest` + `respx` for HTTP mocking. `--import-mode=importlib`. Coverage gate.

[Unreleased]: https://github.com/hatchup-io/payment-service-integration/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/hatchup-io/payment-service-integration/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/hatchup-io/payment-service-integration/compare/v0.3.5...v0.4.0
[0.3.5]: https://github.com/hatchup-io/payment-service-integration/compare/v0.3.0...v0.3.5
[0.3.0]: https://github.com/hatchup-io/payment-service-integration/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/hatchup-io/payment-service-integration/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hatchup-io/payment-service-integration/releases/tag/v0.1.0
