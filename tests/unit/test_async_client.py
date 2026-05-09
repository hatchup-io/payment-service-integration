"""Tests for AsyncPaymentServiceClient."""

from __future__ import annotations

from pydantic import SecretStr

from hatchup_psip.client import AsyncPaymentServiceClient
from hatchup_psip.config import PSIPConfig
from hatchup_psip.resources.catalog import AsyncPricesResource
from hatchup_psip.resources.catalog import AsyncProductsResource
from hatchup_psip.resources.customers import AsyncCustomersResource
from hatchup_psip.resources.invoices import AsyncInvoicesResource
from hatchup_psip.resources.payment_intents import AsyncPaymentIntentsResource
from hatchup_psip.resources.payments import AsyncPaymentsResource
from hatchup_psip.resources.setup_intents import AsyncPaymentMethodsResource
from hatchup_psip.resources.setup_intents import AsyncSetupIntentsResource
from hatchup_psip.resources.subscriptions import AsyncSubscriptionsResource
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.resources.verify import AsyncVerifyResource
from hatchup_psip.resources.webhook_endpoints import AsyncWebhookEndpointsResource
from hatchup_psip.resources.webhooks import AsyncWebhooksResource
from hatchup_psip.transport import AsyncTransport


async def test_constructs_async_transport_from_config() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    client = AsyncPaymentServiceClient(cfg)
    try:
        assert isinstance(client.transport, AsyncTransport)
        assert client.config is cfg
    finally:
        await client.aclose()


async def test_accepts_external_transport() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    transport = AsyncTransport(cfg)
    client = AsyncPaymentServiceClient(cfg, transport=transport)
    try:
        assert client.transport is transport
    finally:
        await client.aclose()


async def test_resources_are_wired() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    async with AsyncPaymentServiceClient(cfg) as client:
        assert isinstance(client.payments, AsyncPaymentsResource)
        assert isinstance(client.verify, AsyncVerifyResource)
        assert isinstance(client.transactions, AsyncTransactionsResource)
        assert isinstance(client.webhooks, AsyncWebhooksResource)
        # v1.0 resources (Phase 4):
        assert isinstance(client.customers, AsyncCustomersResource)
        assert isinstance(client.payment_intents, AsyncPaymentIntentsResource)
        assert isinstance(client.setup_intents, AsyncSetupIntentsResource)
        assert isinstance(client.payment_methods, AsyncPaymentMethodsResource)
        assert isinstance(client.products, AsyncProductsResource)
        assert isinstance(client.prices, AsyncPricesResource)
        assert isinstance(client.subscriptions, AsyncSubscriptionsResource)
        assert isinstance(client.invoices, AsyncInvoicesResource)
        assert isinstance(client.webhook_endpoints, AsyncWebhookEndpointsResource)


async def test_webhooks_share_transactions() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    async with AsyncPaymentServiceClient(cfg) as client:
        assert client.webhooks._transactions is client.transactions


async def test_aclose_closes_transport() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    client = AsyncPaymentServiceClient(cfg)
    inner = client.transport._client
    await client.aclose()
    assert inner.is_closed


async def test_async_context_manager_closes_transport() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    async with AsyncPaymentServiceClient(cfg) as client:
        inner = client.transport._client
        assert not inner.is_closed
    assert inner.is_closed
