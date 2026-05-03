"""Verify resource: ``POST /api/v1/verify``.

The resource is implemented as a callable so the natural-reading idiom
``client.verify(order_id, price)`` works directly.
"""

from __future__ import annotations

from decimal import Decimal

from hatchup_psip.models.verify import VerifyRequest
from hatchup_psip.models.verify import VerifyResponse
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


class VerifyResource(_Resource):
    """Confirm a payment's amount + currency match what the consumer expected.

    Used both as the standalone verification call and as the webhook
    forgery guard — see :class:`hatchup_psip.webhooks.dispatcher.WebhookDispatcher`
    once that ships in the next milestone.
    """

    def __call__(
        self,
        order_id: str,
        price: Decimal | str | int | float,
        /,
        *,
        currency: str = "usd",
    ) -> VerifyResponse:
        req = VerifyRequest(
            order_id=order_id,
            price=Decimal(str(price)),
            currency=currency,
        )
        body = req.model_dump(mode="json")
        data = self._transport.request("POST", "verify", json=body)
        return _parse_response(VerifyResponse, data)


__all__ = ["VerifyResource"]
