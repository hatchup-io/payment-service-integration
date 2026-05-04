"""Tests for WebhookDispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.webhooks.dispatcher import WebhookDispatcher

PAYLOAD = {
    "order_id": "ord_1",
    "status": "completed",
    "amount": "9.99",
    "currency": "usd",
    "transaction_id": "11111111-1111-1111-1111-111111111111",
}


def _event() -> PaymentCompletedEvent:
    return PaymentCompletedEvent.model_validate(PAYLOAD)


def test_register_and_dispatch_invokes_handler() -> None:
    verifier = MagicMock(return_value=None)
    dispatcher = WebhookDispatcher(verifier=verifier)
    received: list[PaymentCompletedEvent] = []

    @dispatcher.on("payment.completed")
    def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    event = _event()
    dispatcher.dispatch(event)
    assert received == [event]
    verifier.assert_called_once_with(event)


def test_unknown_event_type_with_no_handler_is_a_no_op() -> None:
    """Forward-compat: unknown event types must not crash."""
    verifier = MagicMock(return_value=None)
    dispatcher = WebhookDispatcher(verifier=verifier)
    dispatcher.dispatch(_event())  # no handlers registered — OK
    verifier.assert_called_once()


def test_multiple_handlers_for_same_event_all_invoked() -> None:
    dispatcher = WebhookDispatcher(verifier=MagicMock(return_value=None))
    calls: list[str] = []

    @dispatcher.on("payment.completed")
    def first(_: PaymentCompletedEvent) -> None:
        calls.append("first")

    @dispatcher.on("payment.completed")
    def second(_: PaymentCompletedEvent) -> None:
        calls.append("second")

    dispatcher.dispatch(_event())
    assert calls == ["first", "second"]


def test_handler_exception_aggregated_with_exception_group() -> None:
    """One failing handler must not block others — all errors collected."""
    dispatcher = WebhookDispatcher(verifier=MagicMock(return_value=None))
    calls: list[str] = []

    @dispatcher.on("payment.completed")
    def first(_: PaymentCompletedEvent) -> None:
        raise ValueError("first failed")

    @dispatcher.on("payment.completed")
    def second(_: PaymentCompletedEvent) -> None:
        calls.append("second")

    @dispatcher.on("payment.completed")
    def third(_: PaymentCompletedEvent) -> None:
        raise RuntimeError("third failed")

    with pytest.raises(ExceptionGroup) as exc_info:
        dispatcher.dispatch(_event())

    assert calls == ["second"]
    types = [type(e) for e in exc_info.value.exceptions]
    assert ValueError in types
    assert RuntimeError in types


def test_verifier_runs_before_handlers() -> None:
    """A failed verify must prevent any handler from running."""
    verifier = MagicMock(side_effect=PSIPWebhookForgeryError("forged"))
    dispatcher = WebhookDispatcher(verifier=verifier)
    calls: list[str] = []

    @dispatcher.on("payment.completed")
    def handle(_: PaymentCompletedEvent) -> None:
        calls.append("ran")  # pragma: no cover — should never reach here

    with pytest.raises(PSIPWebhookForgeryError):
        dispatcher.dispatch(_event())
    assert calls == []


def test_verify_false_skips_verifier() -> None:
    verifier = MagicMock()
    dispatcher = WebhookDispatcher(verifier=verifier)
    dispatcher.dispatch(_event(), verify=False)
    verifier.assert_not_called()


def test_verify_true_without_verifier_raises_runtime_error() -> None:
    """Programmer error: opting into verification without a verifier is a footgun."""
    dispatcher = WebhookDispatcher()
    with pytest.raises(RuntimeError, match="verifier"):
        dispatcher.dispatch(_event())


def test_no_verifier_with_verify_false_works() -> None:
    """Test/dev path: dispatcher with no verifier still runs when verify=False."""
    dispatcher = WebhookDispatcher()
    received: list[PaymentCompletedEvent] = []

    @dispatcher.on("payment.completed")
    def handle(event: PaymentCompletedEvent) -> None:
        received.append(event)

    dispatcher.dispatch(_event(), verify=False)
    assert len(received) == 1


def test_decorator_returns_function_unchanged() -> None:
    """@on() decorator must not wrap the function — handlers stay directly callable."""
    dispatcher = WebhookDispatcher()

    def plain_handler(_: PaymentCompletedEvent) -> None:
        pass

    decorated = dispatcher.on("payment.completed")(plain_handler)
    assert decorated is plain_handler
