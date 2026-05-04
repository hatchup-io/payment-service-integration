"""Exception hierarchy for the Hatchup Payment Service SDK.

All errors raised by the SDK derive from :class:`PSIPError`. Resource methods
never leak ``httpx`` errors directly — :class:`hatchup_psip.transport.Transport`
classifies every failure into one of the types below so callers can ``except``
on a single hierarchy.
"""

from __future__ import annotations

from typing import Any


class PSIPError(Exception):
    """Base class for every exception the SDK raises."""


class PSIPNetworkError(PSIPError):
    """Underlying transport failed before a response was received.

    Wraps :class:`httpx.RequestError` (timeouts, DNS failures, connection
    resets). Retries have already been exhausted by the time this is raised.
    """


class PSIPProtocolError(PSIPError):
    """The server response or webhook payload did not match the documented shape.

    Raised when:

    - HTTP status is 2xx but the body is not valid JSON, or doesn't contain the
      ``{data, status, message}`` envelope.
    - HTTP status is 2xx but the envelope's ``status`` is ``"failure"`` — the
      server is contradicting itself and we refuse to guess.
    - A webhook payload fails schema validation.
    """


class PSIPAPIError(PSIPError):
    """The server returned a documented error response (HTTP 4xx/5xx + envelope ``status="failure"``).

    The HTTP status code drives which subclass is raised. Always carries
    ``status_code``, ``message`` (the server's human-readable string), the
    raw envelope as ``raw``, and ``request_id`` if the server emits one
    (today it doesn't — value is ``None``).
    """

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        raw: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message
        self.raw: dict[str, Any] = raw or {}
        self.request_id = request_id


class PSIPAuthError(PSIPAPIError):
    """HTTP 401 — API key missing, invalid, inactive, or IP-restricted."""


class PSIPValidationError(PSIPAPIError):
    """HTTP 400 — request body or query params failed server-side validation."""


class PSIPNotFoundError(PSIPAPIError):
    """HTTP 404 — the requested resource (transaction, order_id, …) does not exist."""


class PSIPServerError(PSIPAPIError):
    """HTTP 5xx — the payment-system or upstream Stripe failed unexpectedly."""


class PSIPWebhookValidationError(PSIPProtocolError):
    """The inbound webhook body wasn't valid JSON or didn't match the documented event shape."""


class PSIPWebhookForgeryError(PSIPProtocolError):
    """Server roundtrip refused to confirm the webhook payload.

    Raised by :class:`hatchup_psip.webhooks.dispatcher.WebhookDispatcher`
    (with ``verify=True``) when ``client.webhooks.verify_event`` finds
    that the server's record of the transaction is missing or differs
    from what the webhook claimed (mismatched ``order_id``, ``amount``,
    ``currency``, or ``status``).

    Treat this exception as "do not trust this payload" — never let user
    handlers run after it's raised. The payment-system does not
    cryptographically sign outbound webhooks today, so this round-trip
    is the SDK's only forgery defence.
    """


__all__ = [
    "PSIPAPIError",
    "PSIPAuthError",
    "PSIPError",
    "PSIPNetworkError",
    "PSIPNotFoundError",
    "PSIPProtocolError",
    "PSIPServerError",
    "PSIPValidationError",
    "PSIPWebhookForgeryError",
    "PSIPWebhookValidationError",
]
