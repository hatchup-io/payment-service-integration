"""High-level client facades — synchronous and asynchronous.

Both :class:`PaymentServiceClient` and :class:`AsyncPaymentServiceClient`
wire a :class:`PSIPConfig` to every resource proxy. The client owns the
underlying transport and is responsible for closing it.

Multi-tenant note: there is **no** module-level singleton. Consumers that
hold per-tenant credentials (e.g. launchpad-backend, where each Company
has its own payment-system API key) construct one client per tenant.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from hatchup_psip.config import PSIPConfig
from hatchup_psip.resources.catalog import AsyncPricesResource
from hatchup_psip.resources.catalog import AsyncProductsResource
from hatchup_psip.resources.catalog import PricesResource
from hatchup_psip.resources.catalog import ProductsResource
from hatchup_psip.resources.customers import AsyncCustomersResource
from hatchup_psip.resources.customers import CustomersResource
from hatchup_psip.resources.invoices import AsyncInvoicesResource
from hatchup_psip.resources.invoices import InvoicesResource
from hatchup_psip.resources.payment_intents import AsyncPaymentIntentsResource
from hatchup_psip.resources.payment_intents import PaymentIntentsResource
from hatchup_psip.resources.payments import AsyncPaymentsResource
from hatchup_psip.resources.payments import PaymentsResource
from hatchup_psip.resources.setup_intents import AsyncPaymentMethodsResource
from hatchup_psip.resources.setup_intents import AsyncSetupIntentsResource
from hatchup_psip.resources.setup_intents import PaymentMethodsResource
from hatchup_psip.resources.setup_intents import SetupIntentsResource
from hatchup_psip.resources.subscriptions import AsyncSubscriptionsResource
from hatchup_psip.resources.subscriptions import SubscriptionsResource
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.resources.verify import AsyncVerifyResource
from hatchup_psip.resources.verify import VerifyResource
from hatchup_psip.resources.webhook_endpoints import AsyncWebhookEndpointsResource
from hatchup_psip.resources.webhook_endpoints import WebhookEndpointsResource
from hatchup_psip.resources.webhooks import AsyncWebhooksResource
from hatchup_psip.resources.webhooks import WebhooksResource
from hatchup_psip.transport import AsyncTransport
from hatchup_psip.transport import Transport


class PaymentServiceClient:
    """Synchronous entrypoint for every Hatchup Payment Service operation.

    Resources::

        client.payments              # Checkout sessions
        client.transactions          # transaction lookup
        client.verify                # mark transaction verified
        client.webhooks              # legacy verify-by-roundtrip dispatch
        client.customers             # Stripe Customer + saved-method + portal
        client.payment_intents       # PaymentIntent lifecycle
        client.setup_intents         # SetupIntent lifecycle
        client.payment_methods       # detach
        client.products / .prices    # catalog
        client.subscriptions         # subscription lifecycle
        client.invoices              # invoice list / retrieve / pay / void / upcoming
        client.webhook_endpoints     # project-level webhook subscription mgmt
    """

    def __init__(self, config: PSIPConfig, *, transport: Transport | None = None) -> None:
        self._transport = transport if transport is not None else Transport(config)
        self.payments = PaymentsResource(self._transport)
        self.verify = VerifyResource(self._transport)
        self.transactions = TransactionsResource(self._transport)
        self.webhooks = WebhooksResource(transactions=self.transactions)
        self.customers = CustomersResource(self._transport)
        self.payment_intents = PaymentIntentsResource(self._transport)
        self.setup_intents = SetupIntentsResource(self._transport)
        self.payment_methods = PaymentMethodsResource(self._transport)
        self.products = ProductsResource(self._transport)
        self.prices = PricesResource(self._transport)
        self.subscriptions = SubscriptionsResource(self._transport)
        self.invoices = InvoicesResource(self._transport)
        self.webhook_endpoints = WebhookEndpointsResource(self._transport)

    @property
    def config(self) -> PSIPConfig:
        return self._transport.config

    @property
    def transport(self) -> Transport:
        """The underlying :class:`Transport`. Exposed for advanced use; prefer the resources."""
        return self._transport

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncPaymentServiceClient:
    """Asynchronous entrypoint — same surface as :class:`PaymentServiceClient`, awaitable."""

    def __init__(
        self,
        config: PSIPConfig,
        *,
        transport: AsyncTransport | None = None,
    ) -> None:
        self._transport = transport if transport is not None else AsyncTransport(config)
        self.payments = AsyncPaymentsResource(self._transport)
        self.verify = AsyncVerifyResource(self._transport)
        self.transactions = AsyncTransactionsResource(self._transport)
        self.webhooks = AsyncWebhooksResource(transactions=self.transactions)
        self.customers = AsyncCustomersResource(self._transport)
        self.payment_intents = AsyncPaymentIntentsResource(self._transport)
        self.setup_intents = AsyncSetupIntentsResource(self._transport)
        self.payment_methods = AsyncPaymentMethodsResource(self._transport)
        self.products = AsyncProductsResource(self._transport)
        self.prices = AsyncPricesResource(self._transport)
        self.subscriptions = AsyncSubscriptionsResource(self._transport)
        self.invoices = AsyncInvoicesResource(self._transport)
        self.webhook_endpoints = AsyncWebhookEndpointsResource(self._transport)

    @property
    def config(self) -> PSIPConfig:
        return self._transport.config

    @property
    def transport(self) -> AsyncTransport:
        return self._transport

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


__all__ = ["AsyncPaymentServiceClient", "PaymentServiceClient"]
