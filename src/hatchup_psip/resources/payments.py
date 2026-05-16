"""Payments resource: ``POST /api/v1/payment`` and ``POST /api/v1/repayment``."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.payment import CheckoutSessionVerifyResponse
from hatchup_psip.models.payment import PaymentCreateRequest
from hatchup_psip.models.payment import PaymentCreateResponse
from hatchup_psip.models.payment import RepaymentRequest
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _build_create_body(request: PaymentCreateRequest | None, kwargs: dict[str, Any]) -> dict[str, Any]:
    req = request if request is not None else PaymentCreateRequest(**kwargs)
    return req.model_dump(mode="json")


def _build_recreate_body(
    order_id: str,
    success_webhook: str | None,
    failure_webhook: str | None,
    sandbox: bool | None,
) -> dict[str, Any]:
    req = RepaymentRequest(
        order_id=order_id,
        success_webhook=success_webhook,  # type: ignore[arg-type]
        failure_webhook=failure_webhook,  # type: ignore[arg-type]
        sandbox=sandbox,
    )
    return req.model_dump(mode="json", exclude_none=True)


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
        body = _build_create_body(request, kwargs)
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
        body = _build_recreate_body(order_id, success_webhook, failure_webhook, sandbox)
        data = self._transport.request("POST", "repayment", json=body)
        return _parse_response(PaymentCreateResponse, data)

    def verify_session(self, session_id: str, /) -> CheckoutSessionVerifyResponse:
        """Retrieve the Checkout Session live from Stripe + apply completion.

        Client-initiated polling alternative to the webhook fan-out:
        useful when the success page is the only signal the user gives
        the application (browser closes before the webhook lands, or the
        webhook isn't configured at all). Idempotent server-side; safe
        to call repeatedly from "check again" UIs.

        ``payment_status`` mirrors Stripe — typically ``paid``, ``unpaid``,
        ``no_payment_required``. Only ``paid`` populates ``transaction_id``.
        """
        data = self._transport.request("POST", f"checkout-sessions/{session_id}/verify")
        return _parse_response(CheckoutSessionVerifyResponse, data)


class AsyncPaymentsResource(_AsyncResource):
    """Async equivalent of :class:`PaymentsResource`."""

    async def create(
        self,
        request: PaymentCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> PaymentCreateResponse:
        body = _build_create_body(request, kwargs)
        data = await self._transport.request("POST", "payment", json=body)
        return _parse_response(PaymentCreateResponse, data)

    async def recreate(
        self,
        order_id: str,
        /,
        *,
        success_webhook: str | None = None,
        failure_webhook: str | None = None,
        sandbox: bool | None = None,
    ) -> PaymentCreateResponse:
        body = _build_recreate_body(order_id, success_webhook, failure_webhook, sandbox)
        data = await self._transport.request("POST", "repayment", json=body)
        return _parse_response(PaymentCreateResponse, data)

    async def verify_session(self, session_id: str, /) -> CheckoutSessionVerifyResponse:
        data = await self._transport.request("POST", f"checkout-sessions/{session_id}/verify")
        return _parse_response(CheckoutSessionVerifyResponse, data)


__all__ = ["AsyncPaymentsResource", "PaymentsResource"]
