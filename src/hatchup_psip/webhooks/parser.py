"""Parse the JSON payloads payment-system POSTs to the consumer's webhook URL."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.models.webhook import PaymentCompletedEvent


def parse_payment_completed(body: bytes | str | dict[str, Any]) -> PaymentCompletedEvent:
    """Parse a ``payment.completed`` webhook payload into a typed event.

    Accepts the raw HTTP body (``bytes``/``str`` from ``request.body`` /
    ``request.read()``) or a pre-decoded ``dict`` (handy in tests). Raises
    :class:`PSIPWebhookValidationError` on JSON-decode failure or schema
    mismatch.

    .. note::

       This step does **not** prove the payload is genuine. Because the
       payment-system sends webhooks unsigned, parsing is followed by a
       server roundtrip in
       :mod:`hatchup_psip.webhooks.verifier` — see ``docs/webhooks.md``.
    """
    if isinstance(body, dict):
        payload: Any = body
    else:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise PSIPWebhookValidationError(f"webhook body is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise PSIPWebhookValidationError(
            f"webhook body must be a JSON object, got {type(payload).__name__}",
        )

    try:
        return PaymentCompletedEvent.model_validate(payload)
    except ValidationError as exc:
        raise PSIPWebhookValidationError(
            f"webhook payload did not match PaymentCompletedEvent: {exc}",
        ) from exc


__all__ = ["parse_payment_completed"]
