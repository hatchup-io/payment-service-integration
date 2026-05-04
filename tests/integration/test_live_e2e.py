"""End-to-end tests against a live payment-system server.

Marked ``live`` and skipped by default — see ``tests/integration/README.md``
for setup. Run with ``just test-live`` or ``pytest -m live``.

These tests do not run in CI. They exist so that, before each release, a
maintainer can confirm the SDK still parses real-server responses and the
contract snapshot in ``tests/contract/`` is still accurate.
"""

from __future__ import annotations

import time

import pytest

from hatchup_psip.client import PaymentServiceClient
from hatchup_psip.exceptions import PSIPNotFoundError

pytestmark = pytest.mark.live


def _unique_order_id(prefix: str = "psip_int_test") -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


def test_create_checkout_returns_real_stripe_url(
    live_client: PaymentServiceClient,
    webhooks: tuple[str, str],
) -> None:
    success, failure = webhooks
    order_id = _unique_order_id()
    response = live_client.payments.create(
        price="9.99",
        order_id=order_id,
        success_webhook=success,
        failure_webhook=failure,
        sandbox=True,
    )

    assert response.order_id == order_id
    assert response.session_id  # truthy non-empty
    assert "stripe.com" in response.payment_url or "checkout.stripe" in response.payment_url


def test_verify_unpaid_order_returns_unverified(
    live_client: PaymentServiceClient,
    webhooks: tuple[str, str],
) -> None:
    """Verify a brand-new order — the buyer hasn't paid, so server should say verified=False."""
    success, failure = webhooks
    order_id = _unique_order_id()
    live_client.payments.create(
        price="9.99",
        order_id=order_id,
        success_webhook=success,
        failure_webhook=failure,
        sandbox=True,
    )

    result = live_client.verify(order_id, "9.99")
    assert result.order_id == order_id
    # Server returns verified=False for orders without a SUCCEEDED transaction.
    assert result.verified is False


def test_transactions_list_returns_typed_page(live_client: PaymentServiceClient) -> None:
    """List endpoint — typed pydantic page without forcing any specific item count."""
    page = live_client.transactions.list(page_size=5)
    assert page.page == 1
    assert page.page_size == 5
    assert isinstance(page.results, list)


def test_transactions_get_unknown_order_id_raises_not_found(
    live_client: PaymentServiceClient,
) -> None:
    with pytest.raises(PSIPNotFoundError):
        live_client.transactions.get(_unique_order_id("psip_does_not_exist"))
