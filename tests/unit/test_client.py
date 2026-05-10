"""Tests for PaymentServiceClient."""

from __future__ import annotations

from pydantic import SecretStr

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.config import PSIPConfig
from hatchup_psip.resources.catalog import PricesResource
from hatchup_psip.resources.catalog import ProductsResource
from hatchup_psip.resources.customers import CustomersResource
from hatchup_psip.resources.invoices import InvoicesResource
from hatchup_psip.resources.payment_intents import PaymentIntentsResource
from hatchup_psip.resources.payments import PaymentsResource
from hatchup_psip.resources.setup_intents import PaymentMethodsResource
from hatchup_psip.resources.setup_intents import SetupIntentsResource
from hatchup_psip.resources.subscriptions import SubscriptionsResource
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.resources.verify import VerifyResource
from hatchup_psip.resources.webhook_endpoints import WebhookEndpointsResource
from hatchup_psip.resources.webhooks import WebhooksResource
from hatchup_psip.transport import Transport


def test_client_constructs_transport_from_config() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    client = PaymentServiceClient(cfg)
    try:
        assert isinstance(client.transport, Transport)
        assert client.config is cfg
    finally:
        client.close()


def test_client_accepts_external_transport() -> None:
    """Useful for tests + advanced cases (custom httpx.Client wiring)."""
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    transport = Transport(cfg)
    client = PaymentServiceClient(cfg, transport=transport)
    try:
        assert client.transport is transport
    finally:
        client.close()


def test_resources_are_wired() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    with PaymentServiceClient(cfg) as client:
        assert isinstance(client.payments, PaymentsResource)
        assert isinstance(client.verify, VerifyResource)
        assert isinstance(client.transactions, TransactionsResource)
        assert isinstance(client.webhooks, WebhooksResource)
        # v1.0 resources (Phase 4):
        assert isinstance(client.customers, CustomersResource)
        assert isinstance(client.payment_intents, PaymentIntentsResource)
        assert isinstance(client.setup_intents, SetupIntentsResource)
        assert isinstance(client.payment_methods, PaymentMethodsResource)
        assert isinstance(client.products, ProductsResource)
        assert isinstance(client.prices, PricesResource)
        assert isinstance(client.subscriptions, SubscriptionsResource)
        assert isinstance(client.invoices, InvoicesResource)
        assert isinstance(client.webhook_endpoints, WebhookEndpointsResource)


def test_webhooks_share_transactions_with_client() -> None:
    """WebhooksResource composes the same transactions instance for the forgery roundtrip."""
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    with PaymentServiceClient(cfg) as client:
        assert client.webhooks._transactions is client.transactions


def test_close_closes_underlying_transport() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    client = PaymentServiceClient(cfg)
    inner_client = client.transport._client
    client.close()
    assert inner_client.is_closed


def test_context_manager_closes_transport() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    with PaymentServiceClient(cfg) as client:
        inner_client = client.transport._client
        assert not inner_client.is_closed
    assert inner_client.is_closed
