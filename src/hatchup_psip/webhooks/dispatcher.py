"""Decorator-based router for inbound webhook events.

Typical wiring::

    from hatchup_psip import PaymentServiceClient, PSIPConfig
    from hatchup_psip.webhooks import WebhookDispatcher

    client = PaymentServiceClient(PSIPConfig(...))
    dispatcher = WebhookDispatcher(verifier=client.webhooks.verify_event)

    @dispatcher.on("payment.completed")
    def mark_order_paid(event):
        Order.objects.filter(reference=event.order_id).update(paid=True)

    # In your HTTP handler:
    event = client.webhooks.parse(request.body)
    dispatcher.dispatch(event)   # verifies via server roundtrip first

The default ``verify=True`` is intentional — the payment-system does
**not** sign outbound webhooks today, so the roundtrip is the only
forgery defence. Passing ``verify=False`` is supported for tests and
local development; do not ship it to production.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable
from collections.abc import Callable

from hatchup_psip.models.webhook import PaymentCompletedEvent

EventHandler = Callable[[PaymentCompletedEvent], None]
EventVerifier = Callable[[PaymentCompletedEvent], object]
"""A callable that raises :class:`PSIPWebhookForgeryError` if the event is forged.

The return value (typically the server's :class:`Transaction`) is
ignored by the dispatcher — handlers receive the original
:class:`PaymentCompletedEvent`. The ``object`` return type accommodates
any verifier implementation.
"""

AsyncEventHandler = Callable[[PaymentCompletedEvent], Awaitable[None]]
AsyncEventVerifier = Callable[[PaymentCompletedEvent], Awaitable[object]]


def _event_type_for(event: PaymentCompletedEvent) -> str:
    return f"payment.{event.status}"


class WebhookDispatcher:
    """Routes parsed webhook events to ``@on``-registered handlers.

    Construct with ``verifier=client.webhooks.verify_event`` so
    :meth:`dispatch` defaults to safely round-tripping the server before
    invoking any handler.
    """

    def __init__(self, *, verifier: EventVerifier | None = None) -> None:
        self._verifier = verifier
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event_type: str) -> Callable[[EventHandler], EventHandler]:
        """Decorator that registers ``fn`` as a handler for ``event_type``.

        Today the only event the payment-system emits is
        ``"payment.completed"``. The decorator accepts any string so
        consumers don't need an SDK upgrade when payment-system starts
        emitting more events.
        """

        def decorator(fn: EventHandler) -> EventHandler:
            self._handlers.setdefault(event_type, []).append(fn)
            return fn

        return decorator

    def dispatch(self, event: PaymentCompletedEvent, *, verify: bool = True) -> None:
        """Invoke every handler registered for ``event``'s type.

        With ``verify=True`` (the default), the configured ``verifier``
        is called first; a forged event raises
        :class:`PSIPWebhookForgeryError` and no handler runs.

        With ``verify=False``, the verifier is skipped — only safe in
        tests or local development.

        Handler exceptions don't short-circuit each other: every
        registered handler is invoked, and any exceptions raised are
        collected into a single :class:`ExceptionGroup` re-raised after
        the last handler returns.
        """
        if verify:
            if self._verifier is None:
                raise RuntimeError(
                    "WebhookDispatcher.dispatch was called with verify=True but no verifier "
                    "was configured. Pass verifier=client.webhooks.verify_event when building "
                    "the dispatcher, or pass verify=False (insecure — for tests only).",
                )
            self._verifier(event)

        event_type = _event_type_for(event)
        handlers = self._handlers.get(event_type, [])
        errors: list[Exception] = []
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                # Collect every handler's failure so one bad handler doesn't
                # silently swallow the next handler's work; re-raised as group.
                errors.append(exc)
        if errors:
            raise ExceptionGroup(
                f"webhook handler(s) for {event_type!r} raised",
                errors,
            )


class AsyncWebhookDispatcher:
    """Async equivalent of :class:`WebhookDispatcher`.

    Accepts both async and sync handlers — sync handlers are called
    directly (no thread offload), async handlers are awaited. Same
    ``ExceptionGroup`` aggregation semantics as the sync dispatcher.

    The verifier must be async (typically ``async_client.webhooks.verify_event``).
    Mixing a sync verifier with this dispatcher is intentionally
    unsupported — wrap it in an ``async def`` if you need to.
    """

    def __init__(self, *, verifier: AsyncEventVerifier | None = None) -> None:
        self._verifier = verifier
        self._handlers: dict[str, list[AsyncEventHandler | EventHandler]] = {}

    def on(
        self,
        event_type: str,
    ) -> Callable[[AsyncEventHandler | EventHandler], AsyncEventHandler | EventHandler]:
        def decorator(
            fn: AsyncEventHandler | EventHandler,
        ) -> AsyncEventHandler | EventHandler:
            self._handlers.setdefault(event_type, []).append(fn)
            return fn

        return decorator

    async def dispatch(self, event: PaymentCompletedEvent, *, verify: bool = True) -> None:
        if verify:
            if self._verifier is None:
                raise RuntimeError(
                    "AsyncWebhookDispatcher.dispatch was called with verify=True but no "
                    "verifier was configured. Pass verifier=async_client.webhooks.verify_event "
                    "when building the dispatcher, or pass verify=False (insecure — for tests only).",
                )
            await self._verifier(event)

        event_type = _event_type_for(event)
        handlers = self._handlers.get(event_type, [])
        errors: list[Exception] = []
        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup(
                f"webhook handler(s) for {event_type!r} raised",
                errors,
            )


__all__ = [
    "AsyncEventHandler",
    "AsyncEventVerifier",
    "AsyncWebhookDispatcher",
    "EventHandler",
    "EventVerifier",
    "WebhookDispatcher",
]
