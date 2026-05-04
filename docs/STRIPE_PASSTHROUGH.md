# Stripe SDK passthrough — policy

## TL;DR

This SDK does **not** wrap the Stripe SDK directly. Every Stripe-side action goes through the Hatchup Payment Service. As payment-system grows its surface (refunds, disputes, customers, subscriptions, etc.), the SDK adds matching proxies. We never `import stripe` in the SDK core.

If a feature you need is not yet exposed by payment-system, the answer is "open an issue against payment-system to add the endpoint", not "add `import stripe` to the SDK."

## Why

The whole reason payment-system exists is to centralize Stripe access. Going around it means giving up:

- **Audit trail.** Every API call hits payment-system's `RequestLog` table — who called what, when, with what payload. Direct Stripe calls bypass that.
- **Authentication and authorization.** payment-system enforces per-project API keys, IP restriction, and (eventually) HMAC-signed webhooks. Direct Stripe calls would need a separate credential set with no such checks.
- **Fee enforcement.** payment-system applies the platform's `application_fee_amount` on Checkout sessions and Payment Intents. Direct Stripe calls would skip this and quietly under-charge the platform.
- **Single credential surface.** Adding a direct path means consumers manage two sets of secrets (payment-system API key + raw Stripe keys). Two paths, two audit trails, two places where misconfiguration can leak money.
- **Rate limit / circuit breaker logic.** payment-system can add rate limits, retry policies, and outage circuit breakers in one place. The SDK inheriting them automatically is the whole point of having a gateway.

The common counter-argument — "Stripe has features payment-system doesn't expose; let me reach past the gateway" — is solving the wrong problem. The right fix is to add those features to payment-system, where they get the benefits above. Anything urgent enough to bypass the gateway is urgent enough to file a ticket.

## What's in scope today

Today payment-system exposes:

- Checkout session creation (`POST /payment`)
- Repayment / re-issue checkout (`POST /repayment`)
- Order verification (`POST /verify`)
- Transaction listing and detail (`GET /transactions`, `GET /transactions/{id}`)
- One inbound webhook event from Stripe: `checkout.session.completed`

The SDK exposes proxies for all of the above (see `client.payments`, `client.verify`, `client.transactions`, and `client.webhooks`).

## What's not in scope today

These are Stripe SDK features the SDK does **not** wrap:

- Refunds (`refund` create / list / cancel)
- Disputes / chargebacks
- Customer objects (create / update / lookup)
- Payment Intents — the direct flow (Stripe Elements, mobile SDKs)
- Subscriptions — payment-system has the `payment_type="subscription"` field but no subscription-management endpoints (no `subscription` create / cancel / update)
- Stripe Connect account onboarding (Express / Custom dashboards)
- Stripe Tax, Stripe Identity, Stripe Issuing, Stripe Terminal, etc.
- Direct Stripe webhook events other than `checkout.session.completed`

For each: if your product needs it, file an issue against `hatchup-payment-system` requesting an endpoint. The SDK adds the matching proxy in the next minor release.

## Adding a new endpoint

When payment-system ships, e.g., `POST /api/v1/refunds`:

1. Add the request/response models to `src/hatchup_psip/models/refund.py`. Field names mirror payment-system's serializer 1:1 (the contract test in `tests/contract/` will fail otherwise).
2. Add `RefundsResource` to `src/hatchup_psip/resources/refunds.py`.
3. Wire it on `PaymentServiceClient.__init__` as `self.refunds = RefundsResource(self._transport)`.
4. Bump the SDK minor version. Document in `docs/quickstart.md`.

The transport and exception hierarchy don't change — `RefundsResource` uses `self._transport.request(...)` exactly like every other resource.

## Escape hatches

There are no first-party escape hatches. A consumer who installs `stripe` directly and uses it alongside the SDK is on their own — that's outside the SDK's contract, won't be tested, and silently breaks the audit guarantees above. If you find yourself reaching for that, it's a signal that payment-system is missing something — open an issue there.

## Revisiting this policy

This policy is not load-bearing in any code; it's a coordination decision. If the cost-benefit shifts (e.g. payment-system stops being maintained, or the platform pivots away from Stripe Connect), revisit it explicitly rather than letting `import stripe` creep in via a one-off PR.
