"""SetupIntents + PaymentMethod.detach (chunk 4.1)."""

from __future__ import annotations

from typing import Any

from hatchup_psip.models.setup_intent import DetachedPaymentMethod
from hatchup_psip.models.setup_intent import SetupIntent
from hatchup_psip.models.setup_intent import SetupIntentConfirmRequest
from hatchup_psip.models.setup_intent import SetupIntentCreateRequest
from hatchup_psip.models.setup_intent import SetupIntentPage
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


class SetupIntentsResource(_Resource):
    def create(
        self,
        request: SetupIntentCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> SetupIntent:
        req = request if request is not None else SetupIntentCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = self._transport.request("POST", "setup-intents", json=body)
        return _parse_response(SetupIntent, data)

    def retrieve(self, stripe_setup_intent_id: str, /) -> SetupIntent:
        data = self._transport.request("GET", f"setup-intents/{stripe_setup_intent_id}")
        return _parse_response(SetupIntent, data)

    def confirm(
        self,
        stripe_setup_intent_id: str,
        /,
        *,
        payment_method: str | None = None,
    ) -> SetupIntent:
        body = SetupIntentConfirmRequest(payment_method=payment_method).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = self._transport.request(
            "POST",
            f"setup-intents/{stripe_setup_intent_id}/confirm",
            json=body,
        )
        return _parse_response(SetupIntent, data)

    def cancel(self, stripe_setup_intent_id: str, /) -> SetupIntent:
        data = self._transport.request("POST", f"setup-intents/{stripe_setup_intent_id}/cancel")
        return _parse_response(SetupIntent, data)

    def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SetupIntentPage:
        data = self._transport.request(
            "GET",
            "setup-intents",
            params=_list_params(customer, status, page, page_size),
        )
        return _parse_response(SetupIntentPage, data)


class PaymentMethodsResource(_Resource):
    """Detach a saved payment method from its customer."""

    def detach(self, payment_method_id: str, /) -> DetachedPaymentMethod:
        data = self._transport.request("POST", f"payment-methods/{payment_method_id}/detach")
        return _parse_response(DetachedPaymentMethod, data)


class AsyncSetupIntentsResource(_AsyncResource):
    async def create(
        self,
        request: SetupIntentCreateRequest | None = None,
        /,
        **kwargs: Any,
    ) -> SetupIntent:
        req = request if request is not None else SetupIntentCreateRequest(**kwargs)
        body = req.model_dump(mode="json", exclude_none=True)
        data = await self._transport.request("POST", "setup-intents", json=body)
        return _parse_response(SetupIntent, data)

    async def retrieve(self, stripe_setup_intent_id: str, /) -> SetupIntent:
        data = await self._transport.request("GET", f"setup-intents/{stripe_setup_intent_id}")
        return _parse_response(SetupIntent, data)

    async def confirm(
        self,
        stripe_setup_intent_id: str,
        /,
        *,
        payment_method: str | None = None,
    ) -> SetupIntent:
        body = SetupIntentConfirmRequest(payment_method=payment_method).model_dump(
            mode="json",
            exclude_none=True,
        )
        data = await self._transport.request(
            "POST",
            f"setup-intents/{stripe_setup_intent_id}/confirm",
            json=body,
        )
        return _parse_response(SetupIntent, data)

    async def cancel(self, stripe_setup_intent_id: str, /) -> SetupIntent:
        data = await self._transport.request(
            "POST",
            f"setup-intents/{stripe_setup_intent_id}/cancel",
        )
        return _parse_response(SetupIntent, data)

    async def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SetupIntentPage:
        data = await self._transport.request(
            "GET",
            "setup-intents",
            params=_list_params(customer, status, page, page_size),
        )
        return _parse_response(SetupIntentPage, data)


class AsyncPaymentMethodsResource(_AsyncResource):
    async def detach(self, payment_method_id: str, /) -> DetachedPaymentMethod:
        data = await self._transport.request("POST", f"payment-methods/{payment_method_id}/detach")
        return _parse_response(DetachedPaymentMethod, data)


__all__ = [
    "AsyncPaymentMethodsResource",
    "AsyncSetupIntentsResource",
    "PaymentMethodsResource",
    "SetupIntentsResource",
]
