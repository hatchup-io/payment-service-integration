"""Tests for transaction.py models."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.transaction import TransactionListFilters
from hatchup_psip.models.transaction import TransactionPage

LIST_PAYLOAD = {
    "id": "11111111-1111-1111-1111-111111111111",
    "order_id": "ord_1",
    "amount": "9.99",
    "currency": "usd",
    "status": "succeeded",
    "is_test": True,
    "verified_at": None,
    "created_at": "2026-05-01T12:00:00Z",
}

DETAIL_PAYLOAD = LIST_PAYLOAD | {"stripe_checkout_session_id": "cs_xxx"}


class TestTransaction:
    def test_parses_list_payload(self) -> None:
        tx = Transaction.model_validate(LIST_PAYLOAD)
        assert tx.id == UUID("11111111-1111-1111-1111-111111111111")
        assert tx.amount == Decimal("9.99")  # string from server coerces to Decimal
        assert tx.status == "succeeded"
        assert tx.verified_at is None
        assert tx.stripe_checkout_session_id is None

    def test_parses_detail_payload(self) -> None:
        tx = Transaction.model_validate(DETAIL_PAYLOAD)
        assert tx.stripe_checkout_session_id == "cs_xxx"

    def test_parses_verified_at_datetime(self) -> None:
        payload = LIST_PAYLOAD | {"verified_at": "2026-05-02T13:00:00Z"}
        tx = Transaction.model_validate(payload)
        assert isinstance(tx.verified_at, datetime)

    def test_unknown_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Transaction.model_validate(LIST_PAYLOAD | {"status": "refunded"})

    def test_extra_fields_ignored(self) -> None:
        tx = Transaction.model_validate(LIST_PAYLOAD | {"_internal_flag": True})
        assert not hasattr(tx, "_internal_flag")

    def test_is_frozen(self) -> None:
        tx = Transaction.model_validate(LIST_PAYLOAD)
        with pytest.raises(ValidationError):
            tx.order_id = "ord_2"  # type: ignore[misc]


class TestTransactionListFilters:
    def test_defaults_emit_only_pagination(self) -> None:
        params = TransactionListFilters().to_query_params()
        assert params == {"page": "1", "page_size": "20"}

    def test_drops_none_values(self) -> None:
        filters = TransactionListFilters(status="succeeded", page=2)
        params = filters.to_query_params()
        assert "date_from" not in params
        assert params["status"] == "succeeded"
        assert params["page"] == "2"

    def test_dates_serialized_as_iso(self) -> None:
        filters = TransactionListFilters(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
        params = filters.to_query_params()
        assert params["date_from"] == "2026-01-01"
        assert params["date_to"] == "2026-01-31"

    @pytest.mark.parametrize(
        ("flag", "expected"),
        [(True, "true"), (False, "false")],
    )
    def test_booleans_serialized_as_lowercase_strings(self, flag: bool, expected: str) -> None:
        filters = TransactionListFilters(sandbox=flag, verified=flag)
        params = filters.to_query_params()
        assert params["sandbox"] == expected
        assert params["verified"] == expected

    def test_page_size_capped_at_100(self) -> None:
        with pytest.raises(ValidationError):
            TransactionListFilters(page_size=101)

    def test_page_must_be_at_least_one(self) -> None:
        with pytest.raises(ValidationError):
            TransactionListFilters(page=0)

    def test_order_id_startswith_default_omits_param(self) -> None:
        params = TransactionListFilters().to_query_params()
        assert "order_id_startswith" not in params

    def test_order_id_startswith_emitted_when_set(self) -> None:
        filters = TransactionListFilters(order_id_startswith="u_aBc_p_xYz_")
        params = filters.to_query_params()
        assert params["order_id_startswith"] == "u_aBc_p_xYz_"


class TestTransactionPage:
    def _page(self, *, results: int, page_size: int) -> TransactionPage:
        return TransactionPage.model_validate(
            {
                "results": [LIST_PAYLOAD] * results,
                "page": 1,
                "page_size": page_size,
                "count": results,
            },
        )

    def test_has_more_when_page_full(self) -> None:
        page = self._page(results=20, page_size=20)
        assert page.has_more is True

    def test_has_more_false_when_page_partial(self) -> None:
        page = self._page(results=5, page_size=20)
        assert page.has_more is False

    def test_results_validated_as_transactions(self) -> None:
        page = self._page(results=2, page_size=20)
        assert all(isinstance(tx, Transaction) for tx in page.results)
