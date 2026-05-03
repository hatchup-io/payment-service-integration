"""Tests for PaymentsResource."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.models.payment import PaymentCreateRequest
from hatchup_psip.models.payment import PaymentCreateResponse

PAYMENT_URL = "https://test.example.com/api/v1/payment"
REPAYMENT_URL = "https://test.example.com/api/v1/repayment"
SUCCESS_PAYLOAD = {
    "data": {
        "payment_url": "https://checkout.stripe.com/c/pay/cs_xxx",
        "session_id": "cs_xxx",
        "order_id": "ord_1",
    },
    "status": "ok",
    "message": "",
}


class TestCreate:
    def _kwargs(self) -> dict[str, object]:
        return {
            "price": "25.99",
            "order_id": "ord_1",
            "success_webhook": "https://app.example/cb/ok",
            "failure_webhook": "https://app.example/cb/fail",
        }

    def test_kwargs_path(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(PAYMENT_URL).mock(return_value=httpx.Response(200, json=SUCCESS_PAYLOAD))
            response = psip_client.payments.create(**self._kwargs())

        assert isinstance(response, PaymentCreateResponse)
        assert response.session_id == "cs_xxx"
        sent = json.loads(route.calls.last.request.content)
        assert sent["price"] == "25.99"
        assert sent["order_id"] == "ord_1"
        assert sent["payment_type"] == "one_time"
        assert sent["sandbox"] is True

    def test_model_path(self, psip_client: PaymentServiceClient) -> None:
        req = PaymentCreateRequest(**self._kwargs())  # type: ignore[arg-type]
        with respx.mock:
            respx.post(PAYMENT_URL).mock(return_value=httpx.Response(200, json=SUCCESS_PAYLOAD))
            response = psip_client.payments.create(req)
        assert response.session_id == "cs_xxx"

    def test_invalid_user_input_raises_validation_error_not_wrapped(
        self,
        psip_client: PaymentServiceClient,
    ) -> None:
        with pytest.raises(ValidationError):
            psip_client.payments.create(price="-1", order_id="ord_1", success_webhook="x", failure_webhook="x")

    def test_malformed_server_response_raises_protocol_error(
        self,
        psip_client: PaymentServiceClient,
    ) -> None:
        bad = {"data": {"payment_url": "x"}, "status": "ok", "message": ""}  # missing session_id, order_id
        with respx.mock:
            respx.post(PAYMENT_URL).mock(return_value=httpx.Response(200, json=bad))
            with pytest.raises(PSIPProtocolError, match="PaymentCreateResponse"):
                psip_client.payments.create(**self._kwargs())

    def test_currency_lowercased_in_request(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(PAYMENT_URL).mock(return_value=httpx.Response(200, json=SUCCESS_PAYLOAD))
            psip_client.payments.create(**self._kwargs() | {"currency": "EUR"})
        sent = json.loads(route.calls.last.request.content)
        assert sent["currency"] == "eur"


class TestRecreate:
    def test_only_order_id_omits_optional_fields(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(REPAYMENT_URL).mock(return_value=httpx.Response(200, json=SUCCESS_PAYLOAD))
            response = psip_client.payments.recreate("ord_1")

        sent = json.loads(route.calls.last.request.content)
        assert sent == {"order_id": "ord_1"}
        assert response.session_id == "cs_xxx"

    def test_overrides_passed_through(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(REPAYMENT_URL).mock(return_value=httpx.Response(200, json=SUCCESS_PAYLOAD))
            psip_client.payments.recreate(
                "ord_1",
                success_webhook="https://app.example/cb/ok",
                failure_webhook="https://app.example/cb/fail",
                sandbox=False,
            )
        sent = json.loads(route.calls.last.request.content)
        assert sent["sandbox"] is False
        assert "success_webhook" in sent
        assert "failure_webhook" in sent
