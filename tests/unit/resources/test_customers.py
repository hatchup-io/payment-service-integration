"""Tests for CustomersResource (chunk 4.1)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.models.customer import Customer
from hatchup_psip.models.customer import CustomerListPage
from hatchup_psip.models.customer import CustomerPortalSession
from hatchup_psip.models.customer import PaymentMethodList

BASE = "https://test.example.com/api/v1"
CUSTOMERS_URL = f"{BASE}/customers"
CUSTOMER_DETAIL_URL = f"{BASE}/customers/cus_test"


def _envelope(data: object, message: str = "") -> dict[str, object]:
    return {"data": data, "status": "ok", "message": message}


def _customer_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "cus_test",
        "object": "customer",
        "email": "buyer@example.com",
        "name": "Jane",
        "phone": "",
        "description": "",
        "metadata": {},
        "is_test": True,
        "deleted_at": None,
        "created_at": "2026-05-09T12:00:00Z",
        "updated_at": "2026-05-09T12:00:00Z",
    }
    base.update(overrides)
    return base


class TestCreate:
    def test_happy_path_forwards_body(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(CUSTOMERS_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_customer_payload())),
            )
            customer = psip_client.customers.create(
                email="buyer@example.com",
                name="Jane",
                metadata={"signup": "landing"},
                sandbox=True,
            )
        assert isinstance(customer, Customer)
        assert customer.id == "cus_test"

        sent = json.loads(route.calls.last.request.content)
        # ``exclude_none=True`` should keep the body lean.
        assert sent["email"] == "buyer@example.com"
        assert sent["metadata"] == {"signup": "landing"}
        assert "phone" not in sent
        assert "description" not in sent

    def test_invalid_input_raises_validation_error_unwrapped(
        self,
        psip_client: PaymentServiceClient,
    ) -> None:
        # description is capped at 500 chars in the request model.
        with pytest.raises(ValidationError):
            psip_client.customers.create(description="x" * 501)

    def test_malformed_server_response_raises_protocol_error(
        self,
        psip_client: PaymentServiceClient,
    ) -> None:
        with respx.mock:
            respx.post(CUSTOMERS_URL).mock(
                return_value=httpx.Response(200, json=_envelope({"id": "cus_test"})),  # missing required fields
            )
            with pytest.raises(PSIPProtocolError, match="Customer"):
                psip_client.customers.create(email="buyer@example.com")


class TestRetrieveUpdateDelete:
    def test_retrieve(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.get(CUSTOMER_DETAIL_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_customer_payload())),
            )
            customer = psip_client.customers.retrieve("cus_test")
        assert customer.email == "buyer@example.com"

    def test_update_only_sends_set_fields(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.post(CUSTOMER_DETAIL_URL).mock(
                return_value=httpx.Response(200, json=_envelope(_customer_payload(name="New name"))),
            )
            psip_client.customers.update("cus_test", name="New name")
        sent = json.loads(route.calls.last.request.content)
        assert sent == {"name": "New name"}

    def test_delete_returns_envelope_data(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.delete(CUSTOMER_DETAIL_URL).mock(
                return_value=httpx.Response(200, json=_envelope({"id": "cus_test", "deleted": True})),
            )
            data = psip_client.customers.delete("cus_test")
        assert data == {"id": "cus_test", "deleted": True}

    def test_retrieve_404_raises_not_found(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.get(CUSTOMER_DETAIL_URL).mock(
                return_value=httpx.Response(
                    404,
                    json={"data": {}, "status": "failure", "message": "Customer not found"},
                ),
            )
            with pytest.raises(PSIPNotFoundError):
                psip_client.customers.retrieve("cus_test")


class TestList:
    def test_list_passes_pagination_params(self, psip_client: PaymentServiceClient) -> None:
        page = {"results": [_customer_payload()], "page": 2, "page_size": 5, "count": 1}
        with respx.mock:
            route = respx.get(CUSTOMERS_URL).mock(
                return_value=httpx.Response(200, json=_envelope(page)),
            )
            result = psip_client.customers.list(sandbox=True, page=2, page_size=5)
        assert isinstance(result, CustomerListPage)
        assert result.page == 2

        params = dict(route.calls.last.request.url.params)
        assert params == {"page": "2", "page_size": "5", "sandbox": "true"}


class TestPaymentMethodsAndPortal:
    def test_list_payment_methods(self, psip_client: PaymentServiceClient) -> None:
        body = {
            "object": "list",
            "results": [
                {
                    "id": "pm_card_visa",
                    "type": "card",
                    "card": {"brand": "visa", "last4": "4242", "exp_month": 12, "exp_year": 2030},
                    "customer": "cus_test",
                },
            ],
        }
        with respx.mock:
            respx.get(f"{CUSTOMER_DETAIL_URL}/payment-methods").mock(
                return_value=httpx.Response(200, json=_envelope(body)),
            )
            result = psip_client.customers.list_payment_methods("cus_test")
        assert isinstance(result, PaymentMethodList)
        assert result.results[0].card is not None
        assert result.results[0].card.last4 == "4242"

    def test_create_portal_session(self, psip_client: PaymentServiceClient) -> None:
        body = {"id": "bps_test", "url": "https://billing.stripe.com/session/bps_test"}
        with respx.mock:
            route = respx.post(f"{CUSTOMER_DETAIL_URL}/portal-sessions").mock(
                return_value=httpx.Response(200, json=_envelope(body)),
            )
            result = psip_client.customers.create_portal_session(
                "cus_test",
                return_url="https://app.example.com/account",
            )
        assert isinstance(result, CustomerPortalSession)
        assert result.url.startswith("https://billing.stripe.com/")

        sent = json.loads(route.calls.last.request.content)
        # HttpUrl normalises by appending a trailing slash on bare-host URLs.
        assert sent["return_url"].startswith("https://app.example.com/account")
