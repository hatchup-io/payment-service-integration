"""Invoices resource — ``/invoices`` endpoints (chunk 4.2)."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.invoice import Invoice
from hatchup_psip.models.invoice import InvoicePage
from hatchup_psip.models.invoice import UpcomingInvoice
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _list_params(
    customer: str | None,
    subscription: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if customer:
        params["customer"] = customer
    if subscription:
        params["subscription"] = subscription
    if status:
        params["status"] = status
    return params


def _upcoming_params(customer: str, sandbox: bool | None) -> dict[str, Any]:
    params: dict[str, Any] = {"customer": customer}
    if sandbox is not None:
        params["sandbox"] = "true" if sandbox else "false"
    return params


class InvoicesResource(_Resource):
    def retrieve(self, stripe_invoice_id: str, /) -> Invoice:
        data = self._transport.request("GET", f"invoices/{stripe_invoice_id}")
        return _parse_response(Invoice, data)

    def list(
        self,
        *,
        customer: str | None = None,
        subscription: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> InvoicePage:
        data = self._transport.request(
            "GET",
            "invoices",
            params=_list_params(customer, subscription, status, page, page_size),
        )
        return _parse_response(InvoicePage, data)

    def upcoming(self, *, customer: str, sandbox: bool | None = None) -> UpcomingInvoice:
        data = self._transport.request(
            "GET",
            "invoices/upcoming",
            params=_upcoming_params(customer, sandbox),
        )
        return _parse_response(UpcomingInvoice, data)

    def pay(self, stripe_invoice_id: str, /) -> Invoice:
        data = self._transport.request("POST", f"invoices/{stripe_invoice_id}/pay")
        return _parse_response(Invoice, data)

    def void(self, stripe_invoice_id: str, /) -> Invoice:
        data = self._transport.request("POST", f"invoices/{stripe_invoice_id}/void")
        return _parse_response(Invoice, data)


class AsyncInvoicesResource(_AsyncResource):
    async def retrieve(self, stripe_invoice_id: str, /) -> Invoice:
        data = await self._transport.request("GET", f"invoices/{stripe_invoice_id}")
        return _parse_response(Invoice, data)

    async def list(
        self,
        *,
        customer: str | None = None,
        subscription: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> InvoicePage:
        data = await self._transport.request(
            "GET",
            "invoices",
            params=_list_params(customer, subscription, status, page, page_size),
        )
        return _parse_response(InvoicePage, data)

    async def upcoming(self, *, customer: str, sandbox: bool | None = None) -> UpcomingInvoice:
        data = await self._transport.request(
            "GET",
            "invoices/upcoming",
            params=_upcoming_params(customer, sandbox),
        )
        return _parse_response(UpcomingInvoice, data)

    async def pay(self, stripe_invoice_id: str, /) -> Invoice:
        data = await self._transport.request("POST", f"invoices/{stripe_invoice_id}/pay")
        return _parse_response(Invoice, data)

    async def void(self, stripe_invoice_id: str, /) -> Invoice:
        data = await self._transport.request("POST", f"invoices/{stripe_invoice_id}/void")
        return _parse_response(Invoice, data)


__all__ = ["AsyncInvoicesResource", "InvoicesResource"]
