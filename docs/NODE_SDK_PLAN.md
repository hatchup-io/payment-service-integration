# Node SDK Plan

Single living plan for the Node/TypeScript port of `hatchup-payment-service-integration` and its npm release pipeline. Append context here as work lands.

## Goal

Ship a TypeScript SDK at parity with the Python SDK's client surface, published to npm as **`@hatchup/payment-service-integration`** under the `@hatchup` scope. Same wire protocol, same error hierarchy, same webhook verify-by-default story — different idioms (async-only, Zod-validated).

## Non-goals (for v0.1)

- Framework adapters (Express, Fastify, Next.js, etc.). The Python SDK's Django integration came in 0.3.0, not 0.1.0; same staged approach here. Decided 2026-06-04.
- Bundling Stripe SDK passthrough. Same boundary as Python — see [STRIPE_PASSTHROUGH.md](STRIPE_PASSTHROUGH.md).
- Browser builds. The SDK holds an API key; consumers must run it server-side.
- CommonJS-only output if it forces awkward conditional exports. Dual ESM/CJS is fine via tsup; ESM-only is acceptable if Node consumers are all ≥20.

## Decisions locked (2026-06-04)

- **Repo location:** separate repo, e.g. `hatchup-io/payment-service-integration-node`. Clean tooling boundary from the Python repo; independent versioning.
- **Package name:** `@hatchup/payment-service-integration`. Requires claiming the `@hatchup` npm org. Mirrors the PyPI name; scoped publishing protects against typosquats.
- **v0.1 scope:** core SDK only — transport, resources, webhook parser + dispatcher, contract tripwire. No framework adapter.
- **Plan persistence:** this doc lives in the Python repo's `docs/` next to [PYPI_PUBLISH_PLAN.md](PYPI_PUBLISH_PLAN.md). Stays here even after the Node repo exists so both languages are coordinated from one source.

## Stack

| Concern | Choice | Why |
|---|---|---|
| Language | TypeScript 5.5+, `strict: true`, `noUncheckedIndexedAccess: true` | Mirrors mypy strict on the Python side |
| Runtime target | Node ≥20 LTS | Native `fetch`, native `AbortSignal.timeout`, `node:test` available if needed |
| HTTP | Native `fetch` + thin retry/timeout wrapper | No axios; one fewer dep, one fewer maintenance vector |
| Validation | Zod 3.x | Pydantic analog — runtime parse + inferred TS types from one schema |
| Build | `tsup` (esbuild) → ESM + CJS + `.d.ts` | Single config emits both module formats and types |
| Test | Vitest + MSW | Vitest is ESM-native and fast; MSW is the respx analog for `fetch` mocking |
| Lint/format | Biome | Single tool replaces eslint + prettier; matches the Python repo's "single tool" feel (ruff) |
| Typecheck | `tsc --noEmit` in CI | Build is esbuild-fast but tsc is still the truth for types |
| Package manager | pnpm | Faster, strict resolution; lockfile committed |
| Release | GitHub Actions on tag → `npm publish --provenance` | OIDC-based provenance, no long-lived NPM_TOKEN |

## Source layout (mirrors Python)

```
src/
  index.ts                  // public re-exports
  client.ts                 // PaymentServiceClient
  config.ts                 // PSIPConfig (Zod schema + parse)
  transport.ts              // fetch wrapper + retries + envelope decode + error classify
  exceptions.ts             // PSIPError hierarchy (same names as Python)
  resources/
    base.ts                 // shared request/response helpers
    payments.ts             // create, recreate
    verify.ts               // verify(orderId, price), verifySession(sessionId)
    transactions.ts         // list, get, iterAll (async generator)
    customers.ts            // create, list (incl. email filter), retrieve, update, delete
    invoices.ts             // list (with live-customer scope), retrieve
    catalog.ts              // ...
    paymentIntents.ts       // ...
    setupIntents.ts         // ...
    subscriptions.ts        // ...
    webhookEndpoints.ts     // ...
    webhooks.ts             // resource for forgery roundtrip
  models/
    envelope.ts             // ApiEnvelope<T> Zod schema
    payment.ts
    transaction.ts
    verify.ts
    customer.ts
    invoice.ts
    catalog.ts
    paymentIntent.ts
    setupIntent.ts
    subscription.ts
    webhook.ts
    webhookEndpoint.ts
  webhooks/
    parser.ts               // parsePaymentCompleted(body)
    verifier.ts             // verifyEvent(event, transactions)
    dispatcher.ts           // WebhookDispatcher (verify-by-default)
tests/
  unit/
  contract/
    serverContract.test.ts
    fixtures/
      server_contract.json  // SYMLINK or copy from python repo
  integration/              // opt-in via env vars (mirrors pytest live marker)
```

## Resource parity matrix

Every method must land in v0.1 to be considered at parity with the Python SDK. Pulled from [src/hatchup_psip/resources/](../src/hatchup_psip/resources/) and [src/hatchup_psip/__init__.py](../src/hatchup_psip/__init__.py).

| Python (sync class · async class) | Node equivalent | v0.1 |
|---|---|---|
| `PaymentsResource` · `AsyncPaymentsResource` — `.create()`, `.recreate()` | `client.payments.create()`, `.recreate()` | ✅ |
| `VerifyResource` — `client.verify(orderId, price)`, `.verifySession(sessionId)` | `client.verify(orderId, price)`, `client.verify.session(sessionId)` | ✅ |
| `TransactionsResource` — `.list()`, `.get()`, `.iterAll()` | `client.transactions.list()`, `.get()`, `.iterAll()` (async generator) | ✅ |
| `CustomersResource` — incl. `.list({ email })` | `client.customers.*` | ✅ |
| `InvoicesResource` — live-Stripe scoping when `customer=` provided | `client.invoices.*` | ✅ |
| `CatalogResource` | `client.catalog.*` | ✅ |
| `PaymentIntentsResource` | `client.paymentIntents.*` | ✅ |
| `SetupIntentsResource` | `client.setupIntents.*` | ✅ |
| `SubscriptionsResource` | `client.subscriptions.*` | ✅ |
| `WebhookEndpointsResource` | `client.webhookEndpoints.*` | ✅ |
| `WebhooksResource` (composes Transactions for forgery roundtrip) | `client.webhooks.*` | ✅ |

Naming: snake_case → camelCase for methods and fields on the public API; Zod schemas use `z.object({...}).transform(...)` if the wire payload uses snake_case but we want camelCase on the TS side. Recommend keeping the **wire shape** intact (snake_case in JSON) and exposing camelCase **on the parsed object** so consumers get idiomatic TS without confusing wire vs SDK types.

## Webhook handling

Same contract as Python:

- `parsePaymentCompleted(body: Uint8Array | string | object)` → throws `PSIPWebhookValidationError` on JSON/schema failure.
- `verifyEvent(event, transactions)` → server roundtrip forgery guard. Maps webhook `"completed"` → server `"succeeded"`. Aggregates every mismatch into one error.
- `new WebhookDispatcher({ verify: true })`, `dispatcher.on("payment.completed", handler)`, `await dispatcher.dispatch(event)`.
- Handlers can be sync or async; sync handlers awaited directly (no thread offload — Node is async).
- Multiple handler errors aggregated via `AggregateError` (Node analog to Python's `ExceptionGroup`).

## Contract tripwire

Reuse the Python repo's [tests/contract/fixtures/server_contract.json](../tests/contract/fixtures/server_contract.json) as the source of truth. Two implementations to consider:

- **Copy + CI sync check:** copy the JSON into the Node repo, CI job fetches the latest from the Python repo's `main` and diffs. Fails loudly if drifted. Pro: Node repo is self-contained. Con: two copies to keep in sync.
- **Git submodule:** Node repo includes the Python repo as a submodule pinned to a known SHA. Test reads the fixture out of the submodule. Pro: one source of truth. Con: submodules are friction.
- **Recommendation:** start with copy + CI sync check; revisit if drift becomes painful.

## Versioning & release

- npm package version is the single source of truth; mirrors Python's `pyproject.toml` policy.
- Tag `v0.1.0` etc. on the Node repo; release workflow on tag push.
- `npm publish --provenance --access public` from CI using GitHub OIDC. No `NPM_TOKEN` secret in CI.
- Maintainers configure the npm package's "Trusted Publisher" settings under the `@hatchup` org's package settings to allow OIDC from `hatchup-io/payment-service-integration-node/.github/workflows/release.yml`.

Release workflow sketch:

```yaml
name: Release
on:
  push:
    tags: ["v*"]
permissions: {}
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: npm
    permissions:
      id-token: write   # OIDC
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          registry-url: https://registry.npmjs.org
      - run: pnpm install --frozen-lockfile
      - run: pnpm run check       # biome + tsc
      - run: pnpm run test
      - run: pnpm run build       # tsup
      - run: npm publish --provenance --access public
```

## Roadmap

Mirror the Python staging — each milestone leaves a usable, releasable artifact.

- **M0 — toolchain bootstrap (0.1.0):** repo, tsconfig, biome, tsup, vitest, pnpm workspace if needed, `package.json`, license, README scaffold, CI lint+typecheck+test on PR.
- **M1 — transport + client + resources + webhooks (0.2.0):** all 11 resources from the parity matrix, webhook parser + dispatcher, exception hierarchy. Smoke-tested against the running payment-system in `tests/integration/` (opt-in).
- **M2 — contract tripwire (0.3.0):** copy fixture from Python repo, CI sync check, per-model assertion tests.
- **M3 — production-hardened release pipeline (0.4.0):** OIDC publish, provenance, signed releases, changelog automation, badge.
- **M4 — framework adapter (0.5.0):** Express middleware mirroring `PSIPWebhookView`. Triggered by the first Node consumer asking for it; not before.
- **1.0.0:** stabilize after first internal Node consumer integrates end-to-end.

## Open questions

- **Does `@hatchup` exist on npm?** Need to check `npm org ls @hatchup` (requires being a member). If not, claim it before publishing. If taken by someone else, fall back to `@hatchup-io`.
- **First Node consumer.** Which Hatchup product needs this in Node? Without a real consumer the API risks drifting from real-world usage. Likely candidate: any future Node-based product surface that takes payments (Landing? a Next.js admin?). Until one exists, treat the SDK as protocol-driven (Zod schemas match the server) rather than usage-driven.
- **Dual ESM/CJS vs ESM-only.** Tsup supports both at low cost; default to dual unless a CJS-only dep elsewhere forces ESM-only.
- **Decimal handling.** Python uses `Decimal`; JS has no native decimal. Money fields cross the wire as strings (already true in the envelope). Decide whether to expose them as `string` on the TS side (safest) or convert to `number` (lossy for cents-level precision). Recommend keeping `string` and shipping a `parseAmount(amount: string): { major: bigint, minor: bigint }` helper if consumers ask for one.
- **License.** Python is MIT. Match it.
