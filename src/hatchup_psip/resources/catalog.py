"""Products + Prices resources — ``/products`` and ``/prices`` (chunk 4.2)."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.catalog import Price
from hatchup_psip.models.catalog import PriceCreateRequest
from hatchup_psip.models.catalog import PricePage
from hatchup_psip.models.catalog import Product
from hatchup_psip.models.catalog import ProductCreateRequest
from hatchup_psip.models.catalog import ProductPage
from hatchup_psip.models.catalog import ProductUpdateRequest
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _bool_str(v: bool | None) -> str | None:
    if v is None:
        return None
    return "true" if v else "false"


def _product_list_params(active: bool | None, page: int, page_size: int) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if (a := _bool_str(active)) is not None:
        params["active"] = a
    return params


def _price_list_params(
    product: str | None,
    active: bool | None,
    recurring: bool | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if product:
        params["product"] = product
    if (a := _bool_str(active)) is not None:
        params["active"] = a
    if (r := _bool_str(recurring)) is not None:
        params["recurring"] = r
    return params


class ProductsResource(_Resource):
    def create(
        self,
        request: ProductCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Product:
        req = request if request is not None else ProductCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "products", json=body)
        return _parse_response(Product, data)

    def retrieve(self, stripe_product_id: str, /) -> Product:
        data = self._transport.request("GET", f"products/{stripe_product_id}")
        return _parse_response(Product, data)

    def update(
        self,
        stripe_product_id: str,
        /,
        request: ProductUpdateRequest | None = None,
        **kwargs: Any,
    ) -> Product:
        req = request if request is not None else ProductUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", f"products/{stripe_product_id}", json=body)
        return _parse_response(Product, data)

    def list(
        self,
        *,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ProductPage:
        data = self._transport.request(
            "GET",
            "products",
            params=_product_list_params(active, page, page_size),
        )
        return _parse_response(ProductPage, data)


class PricesResource(_Resource):
    def create(
        self,
        request: PriceCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Price:
        req = request if request is not None else PriceCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "prices", json=body)
        return _parse_response(Price, data)

    def retrieve(self, stripe_price_id: str, /) -> Price:
        data = self._transport.request("GET", f"prices/{stripe_price_id}")
        return _parse_response(Price, data)

    def deactivate(self, stripe_price_id: str, /) -> dict[str, Any]:
        return self._transport.request("DELETE", f"prices/{stripe_price_id}")

    def list(
        self,
        *,
        product: str | None = None,
        active: bool | None = None,
        recurring: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PricePage:
        data = self._transport.request(
            "GET",
            "prices",
            params=_price_list_params(product, active, recurring, page, page_size),
        )
        return _parse_response(PricePage, data)


class AsyncProductsResource(_AsyncResource):
    async def create(
        self,
        request: ProductCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Product:
        req = request if request is not None else ProductCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "products", json=body)
        return _parse_response(Product, data)

    async def retrieve(self, stripe_product_id: str, /) -> Product:
        data = await self._transport.request("GET", f"products/{stripe_product_id}")
        return _parse_response(Product, data)

    async def update(
        self,
        stripe_product_id: str,
        /,
        request: ProductUpdateRequest | None = None,
        **kwargs: Any,
    ) -> Product:
        req = request if request is not None else ProductUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", f"products/{stripe_product_id}", json=body)
        return _parse_response(Product, data)

    async def list(
        self,
        *,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ProductPage:
        data = await self._transport.request(
            "GET",
            "products",
            params=_product_list_params(active, page, page_size),
        )
        return _parse_response(ProductPage, data)


class AsyncPricesResource(_AsyncResource):
    async def create(
        self,
        request: PriceCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Price:
        req = request if request is not None else PriceCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "prices", json=body)
        return _parse_response(Price, data)

    async def retrieve(self, stripe_price_id: str, /) -> Price:
        data = await self._transport.request("GET", f"prices/{stripe_price_id}")
        return _parse_response(Price, data)

    async def deactivate(self, stripe_price_id: str, /) -> dict[str, Any]:
        return await self._transport.request("DELETE", f"prices/{stripe_price_id}")

    async def list(
        self,
        *,
        product: str | None = None,
        active: bool | None = None,
        recurring: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PricePage:
        data = await self._transport.request(
            "GET",
            "prices",
            params=_price_list_params(product, active, recurring, page, page_size),
        )
        return _parse_response(PricePage, data)


__all__ = [
    "AsyncPricesResource",
    "AsyncProductsResource",
    "PricesResource",
    "ProductsResource",
]
