"""Tests for VerifyResource."""

from __future__ import annotations

import json
from decimal import Decimal

import httpx
import pytest
import respx

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.exceptions import PSIPProtocolError

URL = "https://test.example.com/api/v1/verify"
SUCCESS = {"data": {"order_id": "ord_1", "verified": True}, "status": "ok", "message": ""}


def test_callable_path(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=SUCCESS))
        response = psip_client.verify("ord_1", "9.99")

    assert response.verified is True
    assert response.order_id == "ord_1"
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"order_id": "ord_1", "price": "9.99", "currency": "usd"}


@pytest.mark.parametrize(
    "price",
    [Decimal("9.99"), "9.99", 9.99, 10],
)
def test_accepts_various_price_types(
    psip_client: PaymentServiceClient,
    price: object,
) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=SUCCESS))
        psip_client.verify("ord_1", price)  # type: ignore[arg-type]
    # All inputs should serialize as a fixed-precision decimal string
    sent = json.loads(route.calls.last.request.content)
    assert isinstance(sent["price"], str)
    assert Decimal(sent["price"]) > 0


def test_currency_override(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=SUCCESS))
        psip_client.verify("ord_1", "9.99", currency="EUR")
    sent = json.loads(route.calls.last.request.content)
    assert sent["currency"] == "eur"


def test_malformed_response_raises_protocol_error(psip_client: PaymentServiceClient) -> None:
    bad = {"data": {"order_id": "ord_1"}, "status": "ok", "message": ""}  # missing 'verified'
    with respx.mock:
        respx.post(URL).mock(return_value=httpx.Response(200, json=bad))
        with pytest.raises(PSIPProtocolError, match="VerifyResponse"):
            psip_client.verify("ord_1", "9.99")
