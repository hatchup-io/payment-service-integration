"""Tests for HMAC-SHA256 signature verification (chunk 1.5+).

Covers ``hatchup_psip.webhooks.verifier.verify_signature`` — the new
``X-Hatchup-Signature: t=<unix>,v1=<hex>`` scheme that signs
:class:`WebhookEndpoint` deliveries.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.webhooks.verifier import verify_signature

SECRET = "whsec_test_abc123"
BODY = json.dumps({"event_type": "payment_intent.succeeded", "data": {"id": "pi_x"}})


def _sign(secret: str, timestamp: int, body: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _header(timestamp: int, digest: str) -> str:
    return f"t={timestamp},v1={digest}"


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_verifies_a_valid_signature() -> None:
    timestamp = 1700000000
    digest = _sign(SECRET, timestamp, BODY)
    # Returns None on success; raise = test fails.
    verify_signature(
        body=BODY,
        signing_secret=SECRET,
        header_value=_header(timestamp, digest),
        now_func=lambda: float(timestamp),
    )


def test_accepts_bytes_body() -> None:
    timestamp = 1700000000
    digest = _sign(SECRET, timestamp, BODY)
    verify_signature(
        body=BODY.encode("utf-8"),
        signing_secret=SECRET,
        header_value=_header(timestamp, digest),
        now_func=lambda: float(timestamp),
    )


def test_tolerates_extra_unknown_signature_schemes() -> None:
    """Forward-compat: ``v2=...`` is silently ignored."""
    timestamp = 1700000000
    digest = _sign(SECRET, timestamp, BODY)
    header = f"t={timestamp},v1={digest},v2=anything"
    verify_signature(
        body=BODY,
        signing_secret=SECRET,
        header_value=header,
        now_func=lambda: float(timestamp),
    )


# --------------------------------------------------------------------------- #
# Failure modes
# --------------------------------------------------------------------------- #


def test_signature_mismatch_raises_forgery() -> None:
    timestamp = 1700000000
    bad_digest = _sign("whsec_other_secret", timestamp, BODY)
    with pytest.raises(PSIPWebhookForgeryError, match="signature mismatch"):
        verify_signature(
            body=BODY,
            signing_secret=SECRET,
            header_value=_header(timestamp, bad_digest),
            now_func=lambda: float(timestamp),
        )


def test_body_tampering_raises_forgery() -> None:
    timestamp = 1700000000
    digest = _sign(SECRET, timestamp, BODY)
    with pytest.raises(PSIPWebhookForgeryError):
        verify_signature(
            body=BODY + "{tampered}",
            signing_secret=SECRET,
            header_value=_header(timestamp, digest),
            now_func=lambda: float(timestamp),
        )


def test_old_timestamp_outside_tolerance_raises_forgery() -> None:
    signed_at = 1700000000
    digest = _sign(SECRET, signed_at, BODY)
    far_future = signed_at + 600  # 10 minutes later, default tolerance is 5
    with pytest.raises(PSIPWebhookForgeryError, match="outside tolerance"):
        verify_signature(
            body=BODY,
            signing_secret=SECRET,
            header_value=_header(signed_at, digest),
            now_func=lambda: float(far_future),
        )


def test_tolerance_can_be_widened() -> None:
    """A long-running consumer may want a larger tolerance — the kwarg honors it."""
    signed_at = 1700000000
    digest = _sign(SECRET, signed_at, BODY)
    far_future = signed_at + 600
    verify_signature(
        body=BODY,
        signing_secret=SECRET,
        header_value=_header(signed_at, digest),
        tolerance_seconds=900,
        now_func=lambda: float(far_future),
    )


def test_missing_header_raises_forgery() -> None:
    with pytest.raises(PSIPWebhookForgeryError, match="missing"):
        verify_signature(body=BODY, signing_secret=SECRET, header_value="")


def test_malformed_header_raises_validation_error() -> None:
    with pytest.raises(PSIPWebhookValidationError, match="missing"):
        # No `v1=...` segment.
        verify_signature(
            body=BODY,
            signing_secret=SECRET,
            header_value="t=1700000000",
        )


def test_empty_secret_raises_validation_error() -> None:
    digest = _sign(SECRET, 1700000000, BODY)
    with pytest.raises(PSIPWebhookValidationError, match="signing_secret"):
        verify_signature(
            body=BODY,
            signing_secret="",
            header_value=_header(1700000000, digest),
        )
