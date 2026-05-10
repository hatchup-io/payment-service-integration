"""Parse the JSON payloads payment-system POSTs to the consumer's webhook URL.

Each ``parse_*`` helper accepts the raw HTTP body (``bytes`` / ``str`` from
``request.body`` / ``request.read()``) or a pre-decoded ``dict`` and returns
a typed event. Schema or JSON-decode failures raise
:class:`PSIPWebhookValidationError`.

Verification (signature or roundtrip) is **separate** — see
:mod:`hatchup_psip.webhooks.verifier`.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError

from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.models.webhook import CustomerEvent
from hatchup_psip.models.webhook import InvoiceEvent
from hatchup_psip.models.webhook import PaymentCompletedEvent
from hatchup_psip.models.webhook import PaymentIntentFailedEvent
from hatchup_psip.models.webhook import PaymentIntentSucceededEvent
from hatchup_psip.models.webhook import SubscriptionEvent


def _decode(body: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(body, dict):
        return body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PSIPWebhookValidationError(f"webhook body is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PSIPWebhookValidationError(
            f"webhook body must be a JSON object, got {type(payload).__name__}",
        )
    return payload


def _parse[E: BaseModel](model_cls: type[E], body: bytes | str | dict[str, Any]) -> E:
    payload = _decode(body)
    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise PSIPWebhookValidationError(
            f"webhook payload did not match {model_cls.__name__}: {exc}",
        ) from exc


def parse_payment_completed(body: bytes | str | dict[str, Any]) -> PaymentCompletedEvent:
    """Parse a ``payment.completed`` webhook.

    Legacy unsigned per-row delivery — pair with the verify-by-default
    dispatcher in :mod:`hatchup_psip.webhooks.dispatcher` so a forged
    payload can't reach a user handler.
    """
    return _parse(PaymentCompletedEvent, body)


def parse_payment_intent_succeeded(body: bytes | str | dict[str, Any]) -> PaymentIntentSucceededEvent:
    return _parse(PaymentIntentSucceededEvent, body)


def parse_payment_intent_failed(body: bytes | str | dict[str, Any]) -> PaymentIntentFailedEvent:
    return _parse(PaymentIntentFailedEvent, body)


def parse_customer_event(body: bytes | str | dict[str, Any]) -> CustomerEvent:
    """Parse a ``customer.created`` or ``customer.updated`` webhook."""
    return _parse(CustomerEvent, body)


def parse_subscription_event(body: bytes | str | dict[str, Any]) -> SubscriptionEvent:
    """Parse a ``subscription.{created,updated,deleted,trial_will_end}`` webhook."""
    return _parse(SubscriptionEvent, body)


def parse_invoice_event(body: bytes | str | dict[str, Any]) -> InvoiceEvent:
    """Parse a ``invoice.{paid,payment_failed,upcoming}`` webhook."""
    return _parse(InvoiceEvent, body)


__all__ = [
    "parse_customer_event",
    "parse_invoice_event",
    "parse_payment_completed",
    "parse_payment_intent_failed",
    "parse_payment_intent_succeeded",
    "parse_subscription_event",
]
