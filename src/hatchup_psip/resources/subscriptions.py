"""Subscriptions resource — ``/subscriptions`` endpoints (chunk 4.2)."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.subscription import Subscription
from hatchup_psip.models.subscription import SubscriptionCancelRequest
from hatchup_psip.models.subscription import SubscriptionCreateRequest
from hatchup_psip.models.subscription import SubscriptionPage
from hatchup_psip.models.subscription import SubscriptionUpdateRequest
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _list_params(customer: str | None, status: str | None, page: int, page_size: int) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if customer:
        params["customer"] = customer
    if status:
        params["status"] = status
    return params


class SubscriptionsResource(_Resource):
    def create(
        self,
        request: SubscriptionCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Subscription:
        req = request if request is not None else SubscriptionCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "subscriptions", json=body)
        return _parse_response(Subscription, data)

    def retrieve(self, stripe_subscription_id: str, /) -> Subscription:
        data = self._transport.request("GET", f"subscriptions/{stripe_subscription_id}")
        return _parse_response(Subscription, data)

    def update(
        self,
        stripe_subscription_id: str,
        /,
        request: SubscriptionUpdateRequest | None = None,
        **kwargs: Any,
    ) -> Subscription:
        req = request if request is not None else SubscriptionUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request(
            "POST",
            f"subscriptions/{stripe_subscription_id}",
            json=body,
        )
        return _parse_response(Subscription, data)

    def cancel(
        self,
        stripe_subscription_id: str,
        /,
        request: SubscriptionCancelRequest | None = None,
        **kwargs: Any,
    ) -> Subscription:
        req = request if request is not None else SubscriptionCancelRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request(
            "POST",
            f"subscriptions/{stripe_subscription_id}/cancel",
            json=body,
        )
        return _parse_response(Subscription, data)

    def resume(self, stripe_subscription_id: str, /) -> Subscription:
        data = self._transport.request(
            "POST",
            f"subscriptions/{stripe_subscription_id}/resume",
        )
        return _parse_response(Subscription, data)

    def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SubscriptionPage:
        data = self._transport.request(
            "GET",
            "subscriptions",
            params=_list_params(customer, status, page, page_size),
        )
        return _parse_response(SubscriptionPage, data)


class AsyncSubscriptionsResource(_AsyncResource):
    async def create(
        self,
        request: SubscriptionCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> Subscription:
        req = request if request is not None else SubscriptionCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "subscriptions", json=body)
        return _parse_response(Subscription, data)

    async def retrieve(self, stripe_subscription_id: str, /) -> Subscription:
        data = await self._transport.request("GET", f"subscriptions/{stripe_subscription_id}")
        return _parse_response(Subscription, data)

    async def update(
        self,
        stripe_subscription_id: str,
        /,
        request: SubscriptionUpdateRequest | None = None,
        **kwargs: Any,
    ) -> Subscription:
        req = request if request is not None else SubscriptionUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request(
            "POST",
            f"subscriptions/{stripe_subscription_id}",
            json=body,
        )
        return _parse_response(Subscription, data)

    async def cancel(
        self,
        stripe_subscription_id: str,
        /,
        request: SubscriptionCancelRequest | None = None,
        **kwargs: Any,
    ) -> Subscription:
        req = request if request is not None else SubscriptionCancelRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request(
            "POST",
            f"subscriptions/{stripe_subscription_id}/cancel",
            json=body,
        )
        return _parse_response(Subscription, data)

    async def resume(self, stripe_subscription_id: str, /) -> Subscription:
        data = await self._transport.request(
            "POST",
            f"subscriptions/{stripe_subscription_id}/resume",
        )
        return _parse_response(Subscription, data)

    async def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SubscriptionPage:
        data = await self._transport.request(
            "GET",
            "subscriptions",
            params=_list_params(customer, status, page, page_size),
        )
        return _parse_response(SubscriptionPage, data)


__all__ = ["AsyncSubscriptionsResource", "SubscriptionsResource"]
