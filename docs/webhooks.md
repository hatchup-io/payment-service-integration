# Webhooks

## Read this first: webhooks are not signed

The Hatchup Payment Service POSTs to your `success_webhook` URL when Stripe confirms a payment. The HTTP request carries **only `Content-Type: application/json`** — no `X-PSIP-Signature` header, no HMAC, no shared secret. (Server source, today: [`apps/payments/webhooks.py:37-46`](https://github.com/hatchup-io/hatchup-payment-system/blob/main/apps/payments/webhooks.py).)

That means: **anyone who learns or guesses your webhook URL can POST a forged `{order_id, status:"completed", amount, currency, transaction_id}` body**, and your handler has no cryptographic way to tell it apart from a real call.

The SDK closes that gap by round-tripping the server before any handler runs. The dispatcher defaults to `verify=True`, which calls `client.transactions.get(transaction_id)` and confirms `order_id`, `amount`, `currency`, and `status` match the payload. Mismatch → `PSIPWebhookForgeryError`, no handler is invoked.

**Treat `verify=False` as a development-only flag.** Production deployments should never disable it until payment-system gains HMAC signing (tracked separately — see "Pending server-side work" at the bottom of this doc).

## Quick wiring

```python
from hatchup_psip import PaymentServiceClient, PSIPConfig, WebhookDispatcher

client = PaymentServiceClient(PSIPConfig(api_key=...))
dispatcher = WebhookDispatcher(verifier=client.webhooks.verify_event)

@dispatcher.on("payment.completed")
def mark_order_paid(event):
    Order.objects.filter(reference=event.order_id).update(paid=True)

# In your HTTP handler:
event = client.webhooks.parse(request.body)
dispatcher.dispatch(event)   # verifies via server roundtrip first
```

For Django, [`docs/django.md`](django.md) shows how `PSIPWebhookView` wraps the same flow and reads from `settings.PSIP`.

## Parsing the body

`client.webhooks.parse()` accepts the raw body in any of three forms:

```python
event = client.webhooks.parse(request.body)              # bytes
event = client.webhooks.parse(request.body.decode())     # str
event = client.webhooks.parse(json.loads(request.body))  # dict
```

It JSON-decodes if needed and validates against `PaymentCompletedEvent`. Failures raise `PSIPWebhookValidationError` (subclass of `PSIPProtocolError`):

| Failure | Raised from |
|---|---|
| Body isn't valid JSON | parser |
| Body isn't a JSON object | parser |
| Body missing required field | pydantic validator |
| Body has unknown `status` | pydantic literal validator |
| Body has malformed UUID for `transaction_id` | pydantic validator |

Unknown fields are silently ignored (forward-compat — server can add fields without breaking older SDKs).

## The dispatcher

`WebhookDispatcher.on(event_type)` is a decorator. The current event_type emitted by payment-system is `"payment.completed"`; new event types can be registered as the server starts emitting them, no SDK upgrade required.

```python
@dispatcher.on("payment.completed")
def first_handler(event):
    ...

@dispatcher.on("payment.completed")
def second_handler(event):
    ...
```

`dispatcher.dispatch(event)`:

1. Calls the verifier (when `verify=True`). Forgery → `PSIPWebhookForgeryError` raised before any handler runs.
2. Calls every handler registered for the event's type.
3. If any handler raised, collects all exceptions and re-raises as a single `ExceptionGroup` — one bad handler does **not** prevent the next handler from running.

```python
try:
    dispatcher.dispatch(event)
except* ValueError as eg:
    log.warning("payment handlers raised %d ValueError(s): %s", len(eg.exceptions), eg)
except PSIPWebhookForgeryError:
    return HttpResponse(status=403)  # or your framework's equivalent
```

The decorator returns the function unchanged, so handlers stay directly callable in tests:

```python
def test_my_handler():
    event = PaymentCompletedEvent(order_id="ord_1", ...)
    mark_order_paid(event)        # call directly, no dispatcher needed
    assert Order.objects.get(reference="ord_1").paid
```

## Configuring the dispatcher

```python
WebhookDispatcher(verifier=client.webhooks.verify_event)
# verify=True (default) → roundtrip on every dispatch
# verify=False on dispatch() → skip the roundtrip (dev/test only)
```

If you build a dispatcher with no verifier and call `.dispatch(verify=True)`, you get a `RuntimeError` with a clear message. That's intentional — the only way to opt out of verification is to pass `verify=False` explicitly, which makes the security trade-off visible at the call site.

## What `verify_event` checks

After fetching the server's record via `client.transactions.get(event.transaction_id)`, the verifier compares:

| Field | Webhook | Server | Match rule |
|---|---|---|---|
| `order_id` | `event.order_id` | `tx.order_id` | exact |
| `amount` | `event.amount` (Decimal) | `tx.amount` (Decimal) | exact |
| `currency` | `event.currency` | `tx.currency` | case-insensitive |
| `status` | `"completed"` | `"succeeded"` | webhook→server mapping |

A `404` from the server is treated as forgery (the server has no record of the transaction the webhook claims).

The verifier returns the server's `Transaction` on success — handlers can use it as an authoritative replacement for the untrusted webhook payload.

## Pending server-side work

The roundtrip guard is a useful defence-in-depth even after signing lands, but until payment-system signs outbound webhooks, it is the **only** defence. Track the server-side issue:

- HMAC-SHA256 sign the outbound POST body.
- `X-PSIP-Signature: t=<unix_ts>,v1=<sig>` header.
- Per-API-key signing secret (rotatable).
- 5-minute timestamp tolerance to defeat replay.

Once that lands, the SDK gains a signature-verification path and the roundtrip becomes optional rather than mandatory.
