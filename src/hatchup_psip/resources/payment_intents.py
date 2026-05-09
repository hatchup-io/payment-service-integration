"""PaymentIntents resource — ``/payment-intents`` endpoints (chunk 4.1)."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.payment_intent import PaymentIntent
from hatchup_psip.models.payment_intent import PaymentIntentCancelRequest
from hatchup_psip.models.payment_intent import PaymentIntentCaptureRequest
from hatchup_psip.models.payment_intent import PaymentIntentConfirmRequest
from hatchup_psip.models.payment_intent import PaymentIntentCreateRequest
from hatchup_psip.models.payment_intent import PaymentIntentPage
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _list_params(
    customer: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if customer:
        params["customer"] = customer
    if status:
        params["status"] = status
    return params


class PaymentIntentsResource(_Resource):
    def create(
        self,
        request: PaymentIntentCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> PaymentIntent:
        req = request if request is not None else PaymentIntentCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "payment-intents", json=body)
        return _parse_response(PaymentIntent, data)

    def retrieve(self, stripe_payment_intent_id: str, /) -> PaymentIntent:
        data = self._transport.request("GET", f"payment-intents/{stripe_payment_intent_id}")
        return _parse_response(PaymentIntent, data)

    def confirm(
        self,
        stripe_payment_intent_id: str,
        /,
        *,
        payment_method: str | None = None,
    ) -> PaymentIntent:
        body = PaymentIntentConfirmRequest(payment_method=payment_method).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = self._transport.request(
            "POST",
            f"payment-intents/{stripe_payment_intent_id}/confirm",
            json=body,
        )
        return _parse_response(PaymentIntent, data)

    def capture(
        self,
        stripe_payment_intent_id: str,
        /,
        *,
        amount_to_capture: Any | None = None,
    ) -> PaymentIntent:
        body = PaymentIntentCaptureRequest(amount_to_capture=amount_to_capture).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = self._transport.request(
            "POST",
            f"payment-intents/{stripe_payment_intent_id}/capture",
            json=body,
        )
        return _parse_response(PaymentIntent, data)

    def cancel(
        self,
        stripe_payment_intent_id: str,
        /,
        *,
        cancellation_reason: str | None = None,
    ) -> PaymentIntent:
        body = PaymentIntentCancelRequest(cancellation_reason=cancellation_reason).model_dump(  # type: ignore[arg-type]
            mode="json",
            exclude_none=True,
        )
        data = self._transport.request(
            "POST",
            f"payment-intents/{stripe_payment_intent_id}/cancel",
            json=body,
        )
        return _parse_response(PaymentIntent, data)

    def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaymentIntentPage:
        data = self._transport.request(
            "GET",
            "payment-intents",
            params=_list_params(customer, status, page, page_size),
        )
        return _parse_response(PaymentIntentPage, data)


class AsyncPaymentIntentsResource(_AsyncResource):
    async def create(
        self,
        request: PaymentIntentCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> PaymentIntent:
        req = request if request is not None else PaymentIntentCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "payment-intents", json=body)
        return _parse_response(PaymentIntent, data)

    async def retrieve(self, stripe_payment_intent_id: str, /) -> PaymentIntent:
        data = await self._transport.request("GET", f"payment-intents/{stripe_payment_intent_id}")
        return _parse_response(PaymentIntent, data)

    async def confirm(
        self,
        stripe_payment_intent_id: str,
        /,
        *,
        payment_method: str | None = None,
    ) -> PaymentIntent:
        body = PaymentIntentConfirmRequest(payment_method=payment_method).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = await self._transport.request(
            "POST",
            f"payment-intents/{stripe_payment_intent_id}/confirm",
            json=body,
        )
        return _parse_response(PaymentIntent, data)

    async def capture(
        self,
        stripe_payment_intent_id: str,
        /,
        *,
        amount_to_capture: Any | None = None,
    ) -> PaymentIntent:
        body = PaymentIntentCaptureRequest(amount_to_capture=amount_to_capture).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = await self._transport.request(
            "POST",
            f"payment-intents/{stripe_payment_intent_id}/capture",
            json=body,
        )
        return _parse_response(PaymentIntent, data)

    async def cancel(
        self,
        stripe_payment_intent_id: str,
        /,
        *,
        cancellation_reason: str | None = None,
    ) -> PaymentIntent:
        body = PaymentIntentCancelRequest(cancellation_reason=cancellation_reason).model_dump(  # type: ignore[arg-type]
            mode="json",
            exclude_none=True,
        )
        data = await self._transport.request(
            "POST",
            f"payment-intents/{stripe_payment_intent_id}/cancel",
            json=body,
        )
        return _parse_response(PaymentIntent, data)

    async def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaymentIntentPage:
        data = await self._transport.request(
            "GET",
            "payment-intents",
            params=_list_params(customer, status, page, page_size),
        )
        return _parse_response(PaymentIntentPage, data)


__all__ = ["AsyncPaymentIntentsResource", "PaymentIntentsResource"]
