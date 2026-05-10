"""Customers resource — ``/customers`` endpoints (chunk 4.1)."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.customer import Customer
from hatchup_psip.models.customer import CustomerCreateRequest
from hatchup_psip.models.customer import CustomerListPage
from hatchup_psip.models.customer import CustomerPortalSession
from hatchup_psip.models.customer import CustomerPortalSessionRequest
from hatchup_psip.models.customer import CustomerUpdateRequest
from hatchup_psip.models.customer import PaymentMethodList
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _list_params(
    *,
    sandbox: bool | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if sandbox is not None:
        params["sandbox"] = "true" if sandbox else "false"
    return params


class CustomersResource(_Resource):
    """Manage Stripe customers through the gateway."""

    def create(
        self,
        request: CustomerCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Customer:
        req = request if request is not None else CustomerCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "customers", json=body)
        return _parse_response(Customer, data)

    def retrieve(self, stripe_customer_id: str, /) -> Customer:
        data = self._transport.request("GET", f"customers/{stripe_customer_id}")
        return _parse_response(Customer, data)

    def update(
        self,
        stripe_customer_id: str,
        /,
        request: CustomerUpdateRequest | None = None,
        **kwargs: Any,
    ) -> Customer:
        req = request if request is not None else CustomerUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", f"customers/{stripe_customer_id}", json=body)
        return _parse_response(Customer, data)

    def delete(self, stripe_customer_id: str, /) -> dict[str, Any]:
        return self._transport.request("DELETE", f"customers/{stripe_customer_id}")

    def list(
        self,
        *,
        sandbox: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CustomerListPage:
        data = self._transport.request(
            "GET",
            "customers",
            params=_list_params(sandbox=sandbox, page=page, page_size=page_size),
        )
        return _parse_response(CustomerListPage, data)

    def list_payment_methods(self, stripe_customer_id: str, /) -> PaymentMethodList:
        data = self._transport.request(
            "GET",
            f"customers/{stripe_customer_id}/payment-methods",
        )
        return _parse_response(PaymentMethodList, data)

    def create_portal_session(
        self,
        stripe_customer_id: str,
        /,
        *,
        return_url: str,
    ) -> CustomerPortalSession:
        body = CustomerPortalSessionRequest(return_url=return_url).model_dump(  # type: ignore[arg-type]
            mode="json",
        )
        data = self._transport.request(
            "POST",
            f"customers/{stripe_customer_id}/portal-sessions",
            json=body,
        )
        return _parse_response(CustomerPortalSession, data)


class AsyncCustomersResource(_AsyncResource):
    """Async equivalent of :class:`CustomersResource`."""

    async def create(
        self,
        request: CustomerCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Customer:
        req = request if request is not None else CustomerCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "customers", json=body)
        return _parse_response(Customer, data)

    async def retrieve(self, stripe_customer_id: str, /) -> Customer:
        data = await self._transport.request("GET", f"customers/{stripe_customer_id}")
        return _parse_response(Customer, data)

    async def update(
        self,
        stripe_customer_id: str,
        /,
        request: CustomerUpdateRequest | None = None,
        **kwargs: Any,
    ) -> Customer:
        req = request if request is not None else CustomerUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", f"customers/{stripe_customer_id}", json=body)
        return _parse_response(Customer, data)

    async def delete(self, stripe_customer_id: str, /) -> dict[str, Any]:
        return await self._transport.request("DELETE", f"customers/{stripe_customer_id}")

    async def list(
        self,
        *,
        sandbox: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CustomerListPage:
        data = await self._transport.request(
            "GET",
            "customers",
            params=_list_params(sandbox=sandbox, page=page, page_size=page_size),
        )
        return _parse_response(CustomerListPage, data)

    async def list_payment_methods(self, stripe_customer_id: str, /) -> PaymentMethodList:
        data = await self._transport.request(
            "GET",
            f"customers/{stripe_customer_id}/payment-methods",
        )
        return _parse_response(PaymentMethodList, data)

    async def create_portal_session(
        self,
        stripe_customer_id: str,
        /,
        *,
        return_url: str,
    ) -> CustomerPortalSession:
        body = CustomerPortalSessionRequest(return_url=return_url).model_dump(  # type: ignore[arg-type]
            mode="json",
        )
        data = await self._transport.request(
            "POST",
            f"customers/{stripe_customer_id}/portal-sessions",
            json=body,
        )
        return _parse_response(CustomerPortalSession, data)


__all__ = ["AsyncCustomersResource", "CustomersResource"]
