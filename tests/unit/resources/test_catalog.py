"""Tests for Products + Prices resources (chunk 4.2)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.models.catalog import Price
from hatchup_psip.models.catalog import PricePage
from hatchup_psip.models.catalog import Product
from hatchup_psip.models.catalog import ProductPage

BASE = "https://test.example.com/api/v1"
PRODUCTS_URL = f"{BASE}/products"
PRODUCT_DETAIL = f"{BASE}/products/prod_test"
PRICES_URL = f"{BASE}/prices"
PRICE_DETAIL = f"{BASE}/prices/price_test"


def _envelope(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


def _product_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "prod_test",
        "object": "product",
        "name": "Pro plan",
        "description": "",
        "metadata": {},
        "is_active": True,
        "is_test": True,
        "created_at": "2026-05-09T12:00:00Z",
        "updated_at": "2026-05-09T12:00:00Z",
    }
    base.update(overrides)
    return base


def _price_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "price_test",
        "object": "price",
        "product": "prod_test",
        "unit_amount": "19.99",
        "currency": "usd",
        "recurring": {"interval": "month", "interval_count": 1},
        "nickname": None,
        "metadata": {},
        "is_active": True,
        "is_test": True,
        "created_at": "2026-05-09T12:00:00Z",
        "updated_at": "2026-05-09T12:00:00Z",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #


class TestProducts:
    def test_create(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(PRODUCTS_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_product_payload())),
            )
            product = psip_client.products.create(name="Pro plan")
        assert isinstance(product, Product)

        sent = json.loads(route.calls.last.request.content)
        assert sent == {"name": "Pro plan", "sandbox": True}

    def test_update_partial(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(PRODUCT_DETAIL).mock(
                return_value=httpx.Response(
                    200,
                    json=_envelope(_product_payload(name="Renamed", is_active=False)),
                ),
            )
            psip_client.products.update("prod_test", name="Renamed", is_active=False)

        sent = json.loads(route.calls.last.request.content)
        assert sent == {"name": "Renamed", "is_active": False}

    def test_list_filters_active(self, psip_client: PaymentServiceClient) -> None:
        page = {"results": [_product_payload()], "page": 1, "page_size": 20, "count": 1}
        with respx.mock:
            route = respx.get(PRODUCTS_URL).mock(
                return_value=httpx.Response(200, json=_envelope(page)),
            )
            result = psip_client.products.list(active=True)
        assert isinstance(result, ProductPage)
        params = dict(route.calls.last.request.url.params)
        assert params["active"] == "true"


# --------------------------------------------------------------------------- #
# Prices
# --------------------------------------------------------------------------- #


class TestPrices:
    def test_create_recurring_forwards_block(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(PRICES_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_price_payload())),
            )
            price = psip_client.prices.create(
                product="prod_test",
                unit_amount="19.99",
                recurring_interval="month",
            )
        assert isinstance(price, Price)
        assert price.recurring is not None
        assert price.recurring.interval == "month"

        sent = json.loads(route.calls.last.request.content)
        assert sent["product"] == "prod_test"
        assert sent["recurring_interval"] == "month"
        assert sent["unit_amount"] == "19.99"
        assert sent["currency"] == "usd"

    def test_create_zero_amount_rejected(self, psip_client: PaymentServiceClient) -> None:
        with pytest.raises(ValidationError):
            psip_client.prices.create(product="prod_test", unit_amount="0")

    def test_deactivate_returns_envelope_data(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.delete(PRICE_DETAIL).mock(
                return_value=httpx.Response(
                    200,
                    json=_envelope({"id": "price_test", "is_active": False}),
                ),
            )
            data = psip_client.prices.deactivate("price_test")
        assert data == {"id": "price_test", "is_active": False}

    def test_list_recurring_only(self, psip_client: PaymentServiceClient) -> None:
        page = {"results": [_price_payload()], "page": 1, "page_size": 20, "count": 1}
        with respx.mock:
            route = respx.get(PRICES_URL).mock(
                return_value=httpx.Response(200, json=_envelope(page)),
            )
            result = psip_client.prices.list(product="prod_test", recurring=True)
        assert isinstance(result, PricePage)

        params = dict(route.calls.last.request.url.params)
        assert params == {
            "page": "1",
            "page_size": "20",
            "product": "prod_test",
            "recurring": "true",
        }
