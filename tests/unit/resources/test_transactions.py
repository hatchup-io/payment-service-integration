"""Tests for TransactionsResource."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import pytest
import respx

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.models.transaction import TransactionListFilters

LIST_URL = "https://test.example.com/api/v1/transactions"
DETAIL_BASE = "https://test.example.com/api/v1/transactions/"

TX_FIXTURE = {
    "id": "11111111-1111-1111-1111-111111111111",
    "order_id": "ord_1",
    "amount": "9.99",
    "currency": "usd",
    "status": "succeeded",
    "is_test": True,
    "verified_at": None,
    "created_at": "2026-05-01T12:00:00Z",
}


def _page(*, results: int = 1, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    return {
        "data": {
            "results": [TX_FIXTURE] * results,
            "page": page,
            "page_size": page_size,
            "count": results,
        },
        "status": "ok",
        "message": "",
    }


class TestList:
    def test_default_filters(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=_page()))
            page = psip_client.transactions.list()

        assert len(page.results) == 1
        sent_params = route.calls.last.request.url.params
        assert sent_params["page"] == "1"
        assert sent_params["page_size"] == "20"
        assert "status" not in sent_params

    def test_kwargs_path(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            route = respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=_page()))
            psip_client.transactions.list(status="succeeded", sandbox=False, page_size=50)

        params = route.calls.last.request.url.params
        assert params["status"] == "succeeded"
        assert params["sandbox"] == "false"
        assert params["page_size"] == "50"

    def test_model_path(self, psip_client: PaymentServiceClient) -> None:
        filters = TransactionListFilters(status="failed", page=2, page_size=10)
        with respx.mock:
            route = respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=_page()))
            psip_client.transactions.list(filters)

        params = route.calls.last.request.url.params
        assert params["status"] == "failed"
        assert params["page"] == "2"
        assert params["page_size"] == "10"


class TestGet:
    def test_by_uuid(self, psip_client: PaymentServiceClient) -> None:
        tx_id = UUID("11111111-1111-1111-1111-111111111111")
        with respx.mock:
            respx.get(DETAIL_BASE + str(tx_id)).mock(
                return_value=httpx.Response(200, json={"data": TX_FIXTURE, "status": "ok", "message": ""}),
            )
            tx = psip_client.transactions.get(tx_id)
        assert tx.order_id == "ord_1"

    def test_by_order_id_string(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.get(DETAIL_BASE + "ord_1").mock(
                return_value=httpx.Response(200, json={"data": TX_FIXTURE, "status": "ok", "message": ""}),
            )
            tx = psip_client.transactions.get("ord_1")
        assert tx.order_id == "ord_1"

    def test_malformed_response_raises_protocol_error(self, psip_client: PaymentServiceClient) -> None:
        with respx.mock:
            respx.get(DETAIL_BASE + "ord_1").mock(
                return_value=httpx.Response(200, json={"data": {"id": "not-a-uuid"}, "status": "ok", "message": ""}),
            )
            with pytest.raises(PSIPProtocolError, match="Transaction"):
                psip_client.transactions.get("ord_1")


class TestIterAll:
    def test_single_page(self, psip_client: PaymentServiceClient) -> None:
        """A page that's not full ends iteration after one fetch."""
        with respx.mock:
            route = respx.get(LIST_URL).mock(
                return_value=httpx.Response(200, json=_page(results=3, page_size=20)),
            )
            txs = list(psip_client.transactions.iter_all())
        assert len(txs) == 3
        assert route.call_count == 1

    def test_walks_multiple_pages(self, psip_client: PaymentServiceClient) -> None:
        """A full first page triggers a second fetch; partial second page ends iteration."""
        responses = [
            httpx.Response(200, json=_page(results=2, page=1, page_size=2)),
            httpx.Response(200, json=_page(results=1, page=2, page_size=2)),
        ]
        with respx.mock:
            route = respx.get(LIST_URL).mock(side_effect=responses)
            txs = list(psip_client.transactions.iter_all(page_size=2))

        assert len(txs) == 3
        assert route.call_count == 2
        # Page param incremented across calls
        assert route.calls[0].request.url.params["page"] == "1"
        assert route.calls[1].request.url.params["page"] == "2"

    def test_filters_passed_through_to_each_page(self, psip_client: PaymentServiceClient) -> None:
        responses = [
            httpx.Response(200, json=_page(results=2, page=1, page_size=2)),
            httpx.Response(200, json=_page(results=0, page=2, page_size=2)),
        ]
        with respx.mock:
            route = respx.get(LIST_URL).mock(side_effect=responses)
            list(psip_client.transactions.iter_all(status="succeeded", page_size=2))

        for call in route.calls:
            assert call.request.url.params["status"] == "succeeded"

    def test_model_path(self, psip_client: PaymentServiceClient) -> None:
        filters = TransactionListFilters(status="pending", page_size=2)
        with respx.mock:
            respx.get(LIST_URL).mock(return_value=httpx.Response(200, json=_page(results=1, page_size=2)))
            txs = list(psip_client.transactions.iter_all(filters))
        assert len(txs) == 1
