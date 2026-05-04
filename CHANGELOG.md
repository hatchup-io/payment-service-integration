# Changelog

All notable changes to `hatchup-payment-service-integration` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/hatchup-io/payment-service-integration/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/hatchup-io/payment-service-integration/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/hatchup-io/payment-service-integration/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hatchup-io/payment-service-integration/releases/tag/v0.1.0
