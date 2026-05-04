"""Tests for AsyncWebhookDispatcher."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.webhooks.dispatcher import AsyncWebhookDispatcher

PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}


def _event() -> PaymentCompletedEvent:
    return PaymentCompletedEvent.model_validate(PAYLOAD)


async def test_async_handler_is_awaited() -> None:
    verifier = AsyncMock(return_value=None)
    dispatcher = AsyncWebhookDispatcher(verifier=verifier)
    received: list[PaymentCompletedEvent] = []

    @dispatcher.on("payment.completed")
    async def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    await dispatcher.dispatch(_event())
    assert len(received) == 1
    verifier.assert_awaited_once()


async def test_sync_handler_is_called_directly() -> None:
    """Sync handlers registered on the async dispatcher run synchronously, no thread offload."""
    dispatcher = AsyncWebhookDispatcher(verifier=AsyncMock(return_value=None))
    received: list[PaymentCompletedEvent] = []

    @dispatcher.on("payment.completed")
    def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    await dispatcher.dispatch(_event())
    assert len(received) == 1


async def test_mixed_sync_and_async_handlers() -> None:
    dispatcher = AsyncWebhookDispatcher(verifier=AsyncMock(return_value=None))
    calls: list[str] = []

    @dispatcher.on("payment.completed")
    def first_sync(_: PaymentCompletedEvent) -> None:
        calls.append("sync")

    @dispatcher.on("payment.completed")
    async def second_async(_: PaymentCompletedEvent) -> None:
        calls.append("async")

    await dispatcher.dispatch(_event())
    assert calls == ["sync", "async"]


async def test_handler_exceptions_aggregated() -> None:
    dispatcher = AsyncWebhookDispatcher(verifier=AsyncMock(return_value=None))

    @dispatcher.on("payment.completed")
    async def failing_async(_: PaymentCompletedEvent) -> None:
        raise ValueError("async failed")

    @dispatcher.on("payment.completed")
    def failing_sync(_: PaymentCompletedEvent) -> None:
        raise RuntimeError("sync failed")

    with pytest.raises(ExceptionGroup) as exc_info:
        await dispatcher.dispatch(_event())

    types = {type(e) for e in exc_info.value.exceptions}
    assert types == {ValueError, RuntimeError}


async def test_unknown_event_type_no_op() -> None:
    dispatcher = AsyncWebhookDispatcher(verifier=AsyncMock(return_value=None))
    await dispatcher.dispatch(_event())  # no handlers — no error


async def test_verifier_runs_before_handlers() -> None:
    verifier = AsyncMock(side_effect=PSIPWebhookForgeryError("forged"))
    dispatcher = AsyncWebhookDispatcher(verifier=verifier)
    calls: list[str] = []

    @dispatcher.on("payment.completed")
    async def handle(_: PaymentCompletedEvent) -> None:
        calls.append("ran")  # pragma: no cover — should never reach

    with pytest.raises(PSIPWebhookForgeryError):
        await dispatcher.dispatch(_event())
    assert calls == []


async def test_verify_false_skips_verifier() -> None:
    verifier = AsyncMock()
    dispatcher = AsyncWebhookDispatcher(verifier=verifier)
    await dispatcher.dispatch(_event(), verify=False)
    verifier.assert_not_called()


async def test_verify_true_without_verifier_raises_runtime_error() -> None:
    dispatcher = AsyncWebhookDispatcher()
    with pytest.raises(RuntimeError, match="verifier"):
        await dispatcher.dispatch(_event())


async def test_no_verifier_with_verify_false_works() -> None:
    dispatcher = AsyncWebhookDispatcher()
    received: list[PaymentCompletedEvent] = []

    @dispatcher.on("payment.completed")
    async def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    await dispatcher.dispatch(_event(), verify=False)
    assert len(received) == 1


async def test_decorator_returns_function_unchanged() -> None:
    dispatcher = AsyncWebhookDispatcher()

    async def plain(_: PaymentCompletedEvent) -> None:
        pass

    decorated: Any = dispatcher.on("payment.completed")(plain)
    assert decorated is plain
