"""Tests for InvoicesResource (chunk 4.2)."""

from __future__ import annotations

import httpx
import respx

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.models.invoice import Invoice
from hatchup_psip.models.invoice import InvoicePage
from hatchup_psip.models.invoice import UpcomingInvoice

BASE = "https://test.example.com/api/v1"
INV_URL = f"{BASE}/invoices"
INV_DETAIL = f"{BASE}/invoices/in_test"


def _envelope(data: object) -> dict[str, object]:
    return {"data": data, "status": "ok", "message": ""}


def _invoice_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "in_test",
        "object": "invoice",
        "customer": "cus_test",
        "subscription": "sub_test",
        "status": "paid",
        "amount_due": "19.99",
        "amount_paid": "19.99",
        "amount_remaining": "0",
        "currency": "usd",
        "period_start": "2026-05-01T00:00:00Z",
        "period_end": "2026-06-01T00:00:00Z",
        "hosted_invoice_url": "https://invoice.stripe.com/in_test",
        "invoice_pdf": "https://invoice.stripe.com/in_test.pdf",
        "metadata": {},
        "is_test": True,
        "paid_at": "2026-05-01T00:00:00Z",
        "voided_at": None,
        "created_at": "2026-05-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def test_retrieve_invoice(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.get(INV_DETAIL).mock(
            return_value=httpx.Response(200, json=_envelope(_invoice_payload())),
        )
        invoice = psip_client.invoices.retrieve("in_test")
    assert isinstance(invoice, Invoice)
    assert invoice.status == "paid"


def test_list_filters_by_subscription_and_status(psip_client: PaymentServiceClient) -> None:
    page = {"results": [_invoice_payload()], "page": 1, "page_size": 20, "count": 1}
    with respx.mock:
        route = respx.get(INV_URL).mock(return_value=httpx.Response(200, json=_envelope(page)))
        result = psip_client.invoices.list(subscription="sub_test", status="paid")
    assert isinstance(result, InvoicePage)
    params = dict(route.calls.last.request.url.params)
    assert params["subscription"] == "sub_test"
    assert params["status"] == "paid"


def test_upcoming_invoice_preview(psip_client: PaymentServiceClient) -> None:
    body = {
        "object": "invoice",
        "preview": True,
        "customer": "cus_test",
        "subscription": "sub_test",
        "amount_due": "9.99",
        "amount_paid": "0",
        "amount_remaining": "9.99",
        "currency": "usd",
        "period_start": "2026-06-01T00:00:00Z",
        "period_end": "2026-07-01T00:00:00Z",
    }
    with respx.mock:
        route = respx.get(f"{INV_URL}/upcoming").mock(
            return_value=httpx.Response(200, json=_envelope(body)),
        )
        result = psip_client.invoices.upcoming(customer="cus_test")
    assert isinstance(result, UpcomingInvoice)
    assert result.preview is True

    params = dict(route.calls.last.request.url.params)
    assert params == {"customer": "cus_test"}


def test_pay_invoice(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.post(f"{INV_DETAIL}/pay").mock(
            return_value=httpx.Response(200, json=_envelope(_invoice_payload(status="paid"))),
        )
        invoice = psip_client.invoices.pay("in_test")
    assert invoice.status == "paid"


def test_void_invoice(psip_client: PaymentServiceClient) -> None:
    with respx.mock:
        respx.post(f"{INV_DETAIL}/void").mock(
            return_value=httpx.Response(
                200,
                json=_envelope(_invoice_payload(status="void", paid_at=None)),
            ),
        )
        invoice = psip_client.invoices.void("in_test")
    assert invoice.status == "void"
