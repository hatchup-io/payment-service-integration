"""DRF webhook endpoint for the Hatchup Payment Service."""

from __future__ import annotations

from typing import Any
from typing import ClassVar

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.django.client import get_default_client
from hatchup_psip.django.client import get_default_dispatcher
from hatchup_psip.exceptions import PSIPWebhookForgeryError
from hatchup_psip.exceptions import PSIPWebhookValidationError
from hatchup_psip.webhooks.dispatcher import WebhookDispatcher


class PSIPWebhookView(APIView):
    """CSRF-exempt endpoint that parses + dispatches inbound payment-system webhooks.

    Status codes:

    - **200**: payload parsed, verifier accepted it, every registered
      handler returned cleanly.
    - **400**: payload was not valid JSON or did not match
      :class:`PaymentCompletedEvent`.
    - **403**: server roundtrip refused the payload (forgery suspected).
    - **500** *(via Django's default exception view)*: a registered
      handler raised. The dispatcher collects every handler's failure
      into an :class:`ExceptionGroup` so one bad handler doesn't silently
      eat the next handler's work.

    Wiring options:

    1. **Default singleton (single-tenant)** — ``include("hatchup_psip.django.urls")``
       and define ``settings.PSIP``; the view reads from
       :func:`get_default_client` / :func:`get_default_dispatcher` on
       first request.
    2. **Explicit injection** — call
       ``PSIPWebhookView.as_view(client=..., dispatcher=...)`` from a
       custom URL conf. Required for multi-tenant deployments.
    3. **Subclassing** — override :meth:`get_client` /
       :meth:`get_dispatcher` for custom resolution (e.g. per-tenant
       lookup based on URL kwargs).
    """

    authentication_classes: ClassVar[list[type]] = []
    permission_classes: ClassVar[tuple[type, ...]] = (AllowAny,)

    # These are populated by as_view(client=..., dispatcher=..., verify=...)
    # or set on a subclass. ``None`` triggers fallback to the settings-backed
    # singletons in :mod:`hatchup_psip.django.client`.
    client: PaymentServiceClient | None = None
    dispatcher: WebhookDispatcher | None = None
    verify: bool = True

    @method_decorator(csrf_exempt)
    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        return super().dispatch(request, *args, **kwargs)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        client = self.get_client()
        dispatcher = self.get_dispatcher()

        try:
            event = client.webhooks.parse(request.body)
        except PSIPWebhookValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

        try:
            dispatcher.dispatch(event, verify=self.verify)
        except PSIPWebhookForgeryError as exc:
            return Response({"detail": str(exc)}, status=403)

        return Response(status=200)

    def get_client(self) -> PaymentServiceClient:
        """Return the client used to parse + verify the webhook.

        Default: :func:`get_default_client` (lazy, settings-backed).
        Override for per-request resolution (e.g. multi-tenant).
        """
        if self.client is not None:
            return self.client
        return get_default_client()

    def get_dispatcher(self) -> WebhookDispatcher:
        """Return the dispatcher that routes the parsed event to handlers.

        Default: :func:`get_default_dispatcher` (lazy, settings-backed).
        Override for per-request resolution.
        """
        if self.dispatcher is not None:
            return self.dispatcher
        return get_default_dispatcher()


__all__ = ["PSIPWebhookView"]
