"""Verify resource: ``POST /api/v1/verify``.

Both sync and async variants are callable so the natural-reading
idiom — ``client.verify(order_id, price)`` and
``await async_client.verify(order_id, price)`` — works directly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hatchup_psip.models.verify import VerifyRequest
from hatchup_psip.models.verify import VerifyResponse
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _build_verify_body(
    order_id: str,
    price: Decimal | str | int | float,
    currency: str,
) -> dict[str, Any]:
    req = VerifyRequest(
        order_id=order_id,
        price=Decimal(str(price)),
        currency=currency,
    )
    return req.model_dump(mode="json")


class VerifyResource(_Resource):
    """Confirm a payment's amount + currency match what the consumer expected.

    Used both as the standalone verification call and as the webhook
    forgery guard — see :class:`hatchup_psip.webhooks.dispatcher.WebhookDispatcher`.
    """

    def __call__(
        self,
        order_id: str,
        price: Decimal | str | int | float,
        /,
        *,
        currency: str = "usd",
    ) -> VerifyResponse:
        body = _build_verify_body(order_id, price, currency)
        data = self._transport.request("POST", "verify", json=body)
        return _parse_response(VerifyResponse, data)


class AsyncVerifyResource(_AsyncResource):
    """Async equivalent of :class:`VerifyResource`."""

    async def __call__(
        self,
        order_id: str,
        price: Decimal | str | int | float,
        /,
        *,
        currency: str = "usd",
    ) -> VerifyResponse:
        body = _build_verify_body(order_id, price, currency)
        data = await self._transport.request("POST", "verify", json=body)
        return _parse_response(VerifyResponse, data)


__all__ = ["AsyncVerifyResource", "VerifyResource"]
