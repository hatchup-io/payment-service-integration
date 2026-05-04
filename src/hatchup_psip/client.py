"""High-level client facades — synchronous and asynchronous.

Both :class:`PaymentServiceClient` and :class:`AsyncPaymentServiceClient`
wire a :class:`PSIPConfig` to the four resource proxies (``payments``,
``verify``, ``transactions``, ``webhooks``). The client owns the
underlying transport and is responsible for closing it.

Multi-tenant note: there is **no** module-level singleton. Consumers that
hold per-tenant credentials (e.g. launchpad-backend, where each Company
has its own payment-system API key) construct one client per tenant.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from hatchup_psip.config import PSIPConfig
from hatchup_psip.resources.payments import AsyncPaymentsResource
from hatchup_psip.resources.payments import PaymentsResource
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.resources.verify import AsyncVerifyResource
from hatchup_psip.resources.verify import VerifyResource
from hatchup_psip.resources.webhooks import AsyncWebhooksResource
from hatchup_psip.resources.webhooks import WebhooksResource
from hatchup_psip.transport import AsyncTransport
from hatchup_psip.transport import Transport


class PaymentServiceClient:
    """Synchronous entrypoint for every Hatchup Payment Service operation.

    Typical usage::

        config = PSIPConfig(api_key=SecretStr("hp_..."))
        with PaymentServiceClient(config) as client:
            response = client.payments.create(
                price="9.99",
                order_id="ord_1",
                success_webhook="https://app.example/cb/ok",
                failure_webhook="https://app.example/cb/fail",
            )
            transaction = client.transactions.get(response.order_id)
    """

    def __init__(self, config: PSIPConfig, *, transport: Transport | None = None) -> None:
        self._transport = transport if transport is not None else Transport(config)
        self.payments = PaymentsResource(self._transport)
        self.verify = VerifyResource(self._transport)
        self.transactions = TransactionsResource(self._transport)
        self.webhooks = WebhooksResource(transactions=self.transactions)

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
    """Asynchronous entrypoint — same surface as :class:`PaymentServiceClient`, awaitable.

    Typical usage::

        config = PSIPConfig(api_key=SecretStr("hp_..."))
        async with AsyncPaymentServiceClient(config) as client:
            response = await client.payments.create(
                price="9.99",
                order_id="ord_1",
                success_webhook="https://app.example/cb/ok",
                failure_webhook="https://app.example/cb/fail",
            )
            transaction = await client.transactions.get(response.order_id)
    """

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
