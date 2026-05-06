"""Tests for payment.py models."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from hatchup_psip.models.payment import PaymentCreateRequest
from hatchup_psip.models.payment import PaymentCreateResponse
from hatchup_psip.models.payment import RepaymentRequest


class TestPaymentCreateRequest:
    def _valid_kwargs(self) -> dict[str, object]:
        return {
            "price": Decimal("25.99"),
            "order_id": "ord_1",
            "success_webhook": "https://example.test/cb/ok",
            "failure_webhook": "https://example.test/cb/fail",
        }

    def test_accepts_minimum_required_fields(self) -> None:
        req = PaymentCreateRequest(**self._valid_kwargs())
        assert req.currency == "usd"
        assert req.payment_type == "one_time"
        assert req.sandbox is True

    def test_currency_is_lowercased(self) -> None:
        req = PaymentCreateRequest(**self._valid_kwargs() | {"currency": "EUR"})
        assert req.currency == "eur"

    def test_price_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"price": Decimal("0")})

    def test_price_must_have_at_most_two_decimal_places(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"price": Decimal("1.999")})

    def test_price_accepts_string_input(self) -> None:
        req = PaymentCreateRequest(**self._valid_kwargs() | {"price": "9.50"})
        assert req.price == Decimal("9.50")

    def test_payment_type_choices(self) -> None:
        for pt in ("one_time", "subscription"):
            req = PaymentCreateRequest(**self._valid_kwargs() | {"payment_type": pt})
            assert req.payment_type == pt
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"payment_type": "weekly"})

    def test_invalid_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"success_webhook": "not-a-url"})

    def test_order_id_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"order_id": ""})

    def test_currency_length_bounds(self) -> None:
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"currency": "a"})
        with pytest.raises(ValidationError):
            PaymentCreateRequest(**self._valid_kwargs() | {"currency": "a" * 11})

    def test_model_is_frozen(self) -> None:
        req = PaymentCreateRequest(**self._valid_kwargs())
        with pytest.raises(ValidationError):
            req.sandbox = False  # type: ignore[misc]

    def test_metadata_default_is_none(self) -> None:
        req = PaymentCreateRequest(**self._valid_kwargs())
        assert req.metadata is None
        # Server omits the field from the wire when None.
        dumped = req.model_dump(mode="json", exclude_none=True)
        assert "metadata" not in dumped

    def test_metadata_passed_through_to_dump(self) -> None:
        req = PaymentCreateRequest(
            **self._valid_kwargs(),
            metadata={"user_slug": "u_aBc", "project_slug": "p_xYz"},
        )
        dumped = req.model_dump(mode="json")
        assert dumped["metadata"] == {"user_slug": "u_aBc", "project_slug": "p_xYz"}


class TestPaymentCreateResponse:
    def test_parses_envelope_data(self) -> None:
        payload = {
            "payment_url": "https://checkout.stripe.com/c/pay/cs_xxx",
            "session_id": "cs_xxx",
            "order_id": "ord_1",
        }
        resp = PaymentCreateResponse.model_validate(payload)
        assert resp.session_id == "cs_xxx"
        assert resp.payment_url.startswith("https://")

    def test_extra_fields_are_ignored(self) -> None:
        payload = {
            "payment_url": "https://x.test",
            "session_id": "cs_1",
            "order_id": "ord_1",
            "_debug_info": "ignored",
        }
        resp = PaymentCreateResponse.model_validate(payload)
        assert not hasattr(resp, "_debug_info")


class TestRepaymentRequest:
    def test_only_order_id_required(self) -> None:
        req = RepaymentRequest(order_id="ord_1")
        assert req.success_webhook is None
        assert req.failure_webhook is None
        assert req.sandbox is None
        assert req.metadata is None

    def test_optional_fields_passthrough(self) -> None:
        req = RepaymentRequest(
            order_id="ord_1",
            success_webhook="https://x.test/ok",  # type: ignore[arg-type]
            failure_webhook="https://x.test/fail",  # type: ignore[arg-type]
            sandbox=False,
        )
        assert req.sandbox is False
        assert str(req.success_webhook).startswith("https://")
