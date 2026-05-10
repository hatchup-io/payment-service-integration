"""WebhookEndpoint subscription management — ``/webhook-endpoints`` (chunk 4.2).

Lets a project register URLs payment-system should fan signed events to.
The ``signing_secret`` is returned ONLY on create + rotate; subsequent
reads return blank. Persist it on creation.
"""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.webhook_endpoint import WebhookEndpoint
from hatchup_psip.models.webhook_endpoint import WebhookEndpointCreateRequest
from hatchup_psip.models.webhook_endpoint import WebhookEndpointPage
from hatchup_psip.models.webhook_endpoint import WebhookEndpointUpdateRequest
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _list_params(active: bool | None, page: int, page_size: int) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if active is not None:
        params["active"] = "true" if active else "false"
    return params


class WebhookEndpointsResource(_Resource):
    def create(
        self,
        request: WebhookEndpointCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> WebhookEndpoint:
        req = request if request is not None else WebhookEndpointCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "webhook-endpoints", json=body)
        return _parse_response(WebhookEndpoint, data)

    def retrieve(self, endpoint_id: str, /) -> WebhookEndpoint:
        data = self._transport.request("GET", f"webhook-endpoints/{endpoint_id}")
        return _parse_response(WebhookEndpoint, data)

    def update(
        self,
        endpoint_id: str,
        /,
        request: WebhookEndpointUpdateRequest | None = None,
        **kwargs: Any,
    ) -> WebhookEndpoint:
        req = request if request is not None else WebhookEndpointUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", f"webhook-endpoints/{endpoint_id}", json=body)
        return _parse_response(WebhookEndpoint, data)

    def delete(self, endpoint_id: str, /) -> dict[str, Any]:
        return self._transport.request("DELETE", f"webhook-endpoints/{endpoint_id}")

    def rotate_secret(self, endpoint_id: str, /) -> WebhookEndpoint:
        """Returns a fresh ``signing_secret``; old secret stops verifying immediately."""
        data = self._transport.request(
            "POST",
            f"webhook-endpoints/{endpoint_id}/rotate-secret",
        )
        return _parse_response(WebhookEndpoint, data)

    def list(
        self,
        *,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> WebhookEndpointPage:
        data = self._transport.request(
            "GET",
            "webhook-endpoints",
            params=_list_params(active, page, page_size),
        )
        return _parse_response(WebhookEndpointPage, data)


class AsyncWebhookEndpointsResource(_AsyncResource):
    async def create(
        self,
        request: WebhookEndpointCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> WebhookEndpoint:
        req = request if request is not None else WebhookEndpointCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "webhook-endpoints", json=body)
        return _parse_response(WebhookEndpoint, data)

    async def retrieve(self, endpoint_id: str, /) -> WebhookEndpoint:
        data = await self._transport.request("GET", f"webhook-endpoints/{endpoint_id}")
        return _parse_response(WebhookEndpoint, data)

    async def update(
        self,
        endpoint_id: str,
        /,
        request: WebhookEndpointUpdateRequest | None = None,
        **kwargs: Any,
    ) -> WebhookEndpoint:
        req = request if request is not None else WebhookEndpointUpdateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request(
            "POST",
            f"webhook-endpoints/{endpoint_id}",
            json=body,
        )
        return _parse_response(WebhookEndpoint, data)

    async def delete(self, endpoint_id: str, /) -> dict[str, Any]:
        return await self._transport.request("DELETE", f"webhook-endpoints/{endpoint_id}")

    async def rotate_secret(self, endpoint_id: str, /) -> WebhookEndpoint:
        data = await self._transport.request(
            "POST",
            f"webhook-endpoints/{endpoint_id}/rotate-secret",
        )
        return _parse_response(WebhookEndpoint, data)

    async def list(
        self,
        *,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> WebhookEndpointPage:
        data = await self._transport.request(
            "GET",
            "webhook-endpoints",
            params=_list_params(active, page, page_size),
        )
        return _parse_response(WebhookEndpointPage, data)


__all__ = ["AsyncWebhookEndpointsResource", "WebhookEndpointsResource"]
