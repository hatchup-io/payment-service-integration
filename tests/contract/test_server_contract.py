"""Contract tests — assert SDK pydantic models match the captured server contract.

The fixture at ``tests/contract/fixtures/server_contract.json`` is a manual
digest of payment-system's ``apps/payments/schema.py``. When payment-system
adds, removes, or renames a field, the matching SDK pydantic model and the
fixture must be updated in the same PR — these tests are the tripwire.

These tests are pure-Python, no network. They run on every ``pytest`` invocation
and don't need any pytest marker.

Refresh procedure:
    1. Run payment-system locally and ``curl host/api/schema/`` (or open the
       drf-spectacular Swagger UI) to confirm the latest field list.
    2. Edit ``tests/contract/fixtures/server_contract.json`` to match.
    3. Adjust the SDK pydantic model — run these tests until they pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from hatchup_psip.models.envelope import ApiEnvelope
from hatchup_psip.models.payment import PaymentCreateRequest
from hatchup_psip.models.payment import PaymentCreateResponse
from hatchup_psip.models.payment import RepaymentRequest
from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.transaction import TransactionListFilters
from hatchup_psip.models.transaction import TransactionPage
from hatchup_psip.models.verify import VerifyRequest
from hatchup_psip.models.verify import VerifyResponse
from hatchup_psip.models.webhook import PaymentCompletedEvent

FIXTURE = Path(__file__).parent / "fixtures" / "server_contract.json"

# Fields the SDK adds for ergonomics that are NOT on the wire — these are
# stripped from the comparison so the test only catches real schema drift.
_SDK_ONLY_FIELDS = {
    PaymentCompletedEvent: {"received_at"},  # SDK-stamped on parse
}


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def _model_fields(model: type, *, drop_sdk_only: bool = True) -> set[str]:
    fields = set(model.model_fields.keys())  # type: ignore[attr-defined]
    if drop_sdk_only:
        fields -= _SDK_ONLY_FIELDS.get(model, set())
    return fields


def _diff(label: str, expected: set[str], actual: set[str]) -> str:
    missing = expected - actual
    extra = actual - expected
    parts = []
    if missing:
        parts.append(f"missing in SDK: {sorted(missing)}")
    if extra:
        parts.append(f"extra in SDK: {sorted(extra)}")
    return f"{label} drift — {'; '.join(parts)}" if parts else ""


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #


def test_payment_create_request_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["POST /api/v1/payment"]["request_fields"])
    sdk = _model_fields(PaymentCreateRequest)
    assert sdk == server, _diff("PaymentCreateRequest", server, sdk)


def test_repayment_request_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["POST /api/v1/repayment"]["request_fields"])
    sdk = _model_fields(RepaymentRequest)
    assert sdk == server, _diff("RepaymentRequest", server, sdk)


def test_verify_request_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["POST /api/v1/verify"]["request_fields"])
    sdk = _model_fields(VerifyRequest)
    assert sdk == server, _diff("VerifyRequest", server, sdk)


def test_transactions_list_query_params_match_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["GET /api/v1/transactions"]["query_params"])
    sdk = _model_fields(TransactionListFilters)
    assert sdk == server, _diff("TransactionListFilters", server, sdk)


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #


def test_payment_create_response_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["POST /api/v1/payment"]["response_data_fields"])
    sdk = _model_fields(PaymentCreateResponse)
    assert sdk == server, _diff("PaymentCreateResponse", server, sdk)


def test_verify_response_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["POST /api/v1/verify"]["response_data_fields"])
    sdk = _model_fields(VerifyResponse)
    assert sdk == server, _diff("VerifyResponse", server, sdk)


def test_transaction_detail_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["GET /api/v1/transactions/{id_or_order_id}"]["response_data_fields"])
    sdk = _model_fields(Transaction)
    assert sdk == server, _diff("Transaction (detail)", server, sdk)


def test_transaction_list_item_is_subset_of_detail(contract: dict[str, Any]) -> None:
    """List endpoint returns fewer fields than detail; SDK uses one Transaction model.

    The detail-only field (``stripe_checkout_session_id``) must be optional on
    the model so list-shaped payloads still validate.
    """
    list_fields = set(
        contract["endpoints"]["GET /api/v1/transactions"]["results_item_fields"],
    )
    detail_fields = set(
        contract["endpoints"]["GET /api/v1/transactions/{id_or_order_id}"]["response_data_fields"],
    )
    sdk = _model_fields(Transaction)
    assert list_fields <= detail_fields, "server list result must be a subset of detail"
    assert sdk >= list_fields, _diff("Transaction (list subset)", list_fields, sdk)


def test_transaction_page_matches_server(contract: dict[str, Any]) -> None:
    server = set(contract["endpoints"]["GET /api/v1/transactions"]["response_data_fields"])
    sdk = _model_fields(TransactionPage)
    assert sdk == server, _diff("TransactionPage", server, sdk)


# --------------------------------------------------------------------------- #
# Envelope + webhook
# --------------------------------------------------------------------------- #


def test_envelope_fields_match_server(contract: dict[str, Any]) -> None:
    server = set(contract["envelope"]["fields"])
    sdk = _model_fields(ApiEnvelope)
    assert sdk == server, _diff("ApiEnvelope", server, sdk)


def test_payment_completed_event_matches_outbound_webhook(contract: dict[str, Any]) -> None:
    server = set(contract["webhook_outbound"]["fields"])
    sdk = _model_fields(PaymentCompletedEvent)  # received_at is SDK-only, already stripped
    assert sdk == server, _diff("PaymentCompletedEvent", server, sdk)
