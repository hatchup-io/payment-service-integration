"""Payments resource: ``POST /api/v1/payment`` and ``POST /api/v1/repayment``."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.payment import PaymentCreateRequest
from hatchup_psip.models.payment import PaymentCreateResponse
from hatchup_psip.models.payment import RepaymentRequest
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


class PaymentsResource(_Resource):
    """Create and re-create Stripe Checkout sessions through the payment-system."""

    def create(
        self,
        request: PaymentCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> PaymentCreateResponse:
        """Create a Checkout session for a new order.

        Accepts either a fully-built :class:`PaymentCreateRequest` or
        keyword arguments forwarded to its constructor. The returned
        :class:`PaymentCreateResponse` carries the hosted ``payment_url``
        the consumer redirects the buyer to.
        """
        req = request if request is not None else PaymentCreateRequest(**kwargs)
        body = req.model_dump(mode="json")
        data = self._transport.request("POST", "payment", json=body)
        return _parse_response(PaymentCreateResponse, data)

    def recreate(
        self,
        order_id: str,
        /,
        *,
        success_webhook: str | None = None,
        failure_webhook: str | None = None,
        sandbox: bool | None = None,
    ) -> PaymentCreateResponse:
        """Re-issue a Checkout session for an existing order whose previous attempt failed/expired.

        The server re-uses the original PaymentRequest's webhook URLs and
        ``sandbox`` flag unless they're overridden here.
        """
        req = RepaymentRequest(
            order_id=order_id,
            success_webhook=success_webhook,  # type: ignore[arg-type]
            failure_webhook=failure_webhook,  # type: ignore[arg-type]
            sandbox=sandbox,
        )
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "repayment", json=body)
        return _parse_response(PaymentCreateResponse, data)


__all__ = ["PaymentsResource"]
