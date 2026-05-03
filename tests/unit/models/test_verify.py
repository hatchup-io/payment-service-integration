"""Tests for verify.py models."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from hatchup_psip.models.verify import VerifyRequest
from hatchup_psip.models.verify import VerifyResponse


def test_verify_request_currency_lowercased() -> None:
    req = VerifyRequest(order_id="ord_1", price=Decimal("9.99"), currency="USD")
    assert req.currency == "usd"


def test_verify_request_defaults_to_usd() -> None:
    req = VerifyRequest(order_id="ord_1", price=Decimal("9.99"))
    assert req.currency == "usd"


def test_verify_request_rejects_non_positive_price() -> None:
    with pytest.raises(ValidationError):
        VerifyRequest(order_id="ord_1", price=Decimal("0"))


def test_verify_request_is_frozen() -> None:
    req = VerifyRequest(order_id="ord_1", price=Decimal("9.99"))
    with pytest.raises(ValidationError):
        req.order_id = "ord_2"  # type: ignore[misc]


def test_verify_response_parses() -> None:
    resp = VerifyResponse.model_validate({"order_id": "ord_1", "verified": True})
    assert resp.verified is True


def test_verify_response_ignores_extra_fields() -> None:
    resp = VerifyResponse.model_validate({"order_id": "ord_1", "verified": False, "extra": "x"})
    assert resp.verified is False
