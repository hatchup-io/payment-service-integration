"""Tests for the v1.0 webhook parsers (chunk 4.4).

Covers ``parse_payment_intent_*``, ``parse_customer_event``,
``parse_subscription_event``, ``parse_invoice_event``. The legacy
``parse_payment_completed`` is covered in ``test_parser.py``.
"""

from __future__ import annotations

import json

import pytest

from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.models.webhook import CustomerEvent
from hatchup_psip.models.webhook import InvoiceEvent
from hatchup_psip.models.webhook import PaymentIntentFailedEvent
from hatchup_psip.models.webhook import PaymentIntentSucceededEvent
from hatchup_psip.models.webhook import SubscriptionEvent
from hatchup_psip.webhooks.parser import parse_customer_event
from hatchup_psip.webhooks.parser import parse_invoice_event
from hatchup_psip.webhooks.parser import parse_payment_intent_failed
from hatchup_psip.webhooks.parser import parse_payment_intent_succeeded
from hatchup_psip.webhooks.parser import parse_subscription_event

# --------------------------------------------------------------------------- #
# PaymentIntent events
# --------------------------------------------------------------------------- #


def test_payment_intent_succeeded_parses() -> None:
    payload = {
        "event": "payment_intent.succeeded",
        "id": "pi_x",
        "status": "succeeded",
        "amount": "12.50",
        "currency": "usd",
        "metadata": {"order_ref": "abc"},
    }
    event = parse_payment_intent_succeeded(json.dumps(payload).encode("utf-8"))
    assert isinstance(event, PaymentIntentSucceededEvent)
    assert event.id == "pi_x"
    assert event.metadata["order_ref"] == "abc"


def test_payment_intent_failed_carries_error_message() -> None:
    payload = {
        "event": "payment_intent.payment_failed",
        "id": "pi_x",
        "status": "requires_payment_method",
        "amount": "12.50",
        "currency": "usd",
        "error": "Your card was declined.",
        "metadata": {},
    }
    event = parse_payment_intent_failed(payload)
    assert isinstance(event, PaymentIntentFailedEvent)
    assert event.error == "Your card was declined."


def test_payment_intent_succeeded_rejects_wrong_event_string() -> None:
    payload = {
        "event": "payment_intent.payment_failed",  # wrong event for the parser
        "id": "pi_x",
        "status": "requires_payment_method",
        "amount": "1.00",
        "currency": "usd",
    }
    with pytest.raises(PSIPWebhookValidationError):
        parse_payment_intent_succeeded(payload)


# --------------------------------------------------------------------------- #
# Customer events
# --------------------------------------------------------------------------- #


def test_customer_created_parses() -> None:
    payload = {
        "event": "customer.created",
        "id": "cus_x",
        "email": "x@example.com",
        "name": "Buyer",
        "metadata": {},
    }
    event = parse_customer_event(payload)
    assert isinstance(event, CustomerEvent)
    assert event.event == "customer.created"


def test_customer_event_rejects_unknown_event_type() -> None:
    with pytest.raises(PSIPWebhookValidationError):
        parse_customer_event({"event": "customer.deleted", "id": "cus_x"})


# --------------------------------------------------------------------------- #
# Subscription events
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "event_name",
    ["subscription.created", "subscription.updated", "subscription.deleted", "subscription.trial_will_end"],
)
def test_subscription_event_accepts_all_four_types(event_name: str) -> None:
    payload = {
        "event": event_name,
        "id": "sub_x",
        "status": "active",
        "customer": "cus_x",
        "current_period_end": 1702592000,
        "cancel_at_period_end": True,
        "trial_end": None,
        "metadata": {},
    }
    event = parse_subscription_event(payload)
    assert isinstance(event, SubscriptionEvent)
    assert event.event == event_name
    assert event.cancel_at_period_end is True


def test_subscription_event_rejects_stripe_prefix() -> None:
    """Server strips the Stripe ``customer.`` prefix before fanning out;
    the SDK should reject the raw Stripe name to catch implementation drift.
    """
    payload = {
        "event": "customer.subscription.updated",  # raw Stripe name — wrong
        "id": "sub_x",
        "status": "active",
    }
    with pytest.raises(PSIPWebhookValidationError):
        parse_subscription_event(payload)


# --------------------------------------------------------------------------- #
# Invoice events
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "event_name",
    ["invoice.paid", "invoice.payment_failed", "invoice.upcoming"],
)
def test_invoice_event_accepts_all_three_types(event_name: str) -> None:
    payload = {
        "event": event_name,
        "id": "in_x",
        "status": "paid",
        "customer": "cus_x",
        "subscription": "sub_x",
        "amount_due": "9.99",
        "amount_paid": "9.99",
        "currency": "usd",
        "hosted_invoice_url": "https://invoice.stripe.com/in_x",
        "metadata": {},
    }
    event = parse_invoice_event(payload)
    assert isinstance(event, InvoiceEvent)
    assert event.event == event_name


# --------------------------------------------------------------------------- #
# Generic decode failures (covers all parsers via the shared ``_decode``)
# --------------------------------------------------------------------------- #


def test_invalid_json_raises_validation_error() -> None:
    with pytest.raises(PSIPWebhookValidationError, match="not valid JSON"):
        parse_customer_event(b"not-json")


def test_non_object_body_raises_validation_error() -> None:
    with pytest.raises(PSIPWebhookValidationError, match="JSON object"):
        parse_customer_event(b"[1, 2]")
