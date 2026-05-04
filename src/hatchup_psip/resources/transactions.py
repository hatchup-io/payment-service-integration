"""Transactions resource: ``GET /api/v1/transactions`` (list) and ``GET /api/v1/transactions/{id}`` (detail)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Iterator
from typing import Any
from uuid import UUID

from hatchup_psip.models.transaction import Transaction
from hatchup_psip.models.transaction import TransactionListFilters
from hatchup_psip.models.transaction import TransactionPage
from hatchup_psip.resources._base import _AsyncResource
from hatchup_psip.resources._base import _parse_response
from hatchup_psip.resources._base import _Resource


def _resolve_filters(
    filters: TransactionListFilters | None,
    kwargs: dict[str, Any],
) -> TransactionListFilters:
    return filters if filters is not None else TransactionListFilters(**kwargs)


class TransactionsResource(_Resource):
    """List, retrieve, and iterate transactions."""

    def list(
        self,
        filters: TransactionListFilters | None = None,
        /,
        **kwargs: Any,
    ) -> TransactionPage:
        """Fetch a single page of transactions.

        Accepts either a built :class:`TransactionListFilters` or kwargs
        forwarded to its constructor. Use :meth:`iter_all` to walk every
        page.
        """
        f = _resolve_filters(filters, kwargs)
        data = self._transport.request("GET", "transactions", params=f.to_query_params())
        return _parse_response(TransactionPage, data)

    def get(self, id_or_order_id: str | UUID, /) -> Transaction:
        """Fetch a transaction by its UUID or by its consumer-supplied ``order_id``."""
        data = self._transport.request("GET", f"transactions/{id_or_order_id}")
        return _parse_response(Transaction, data)

    def iter_all(
        self,
        filters: TransactionListFilters | None = None,
        /,
        **kwargs: Any,
    ) -> Iterator[Transaction]:
        """Yield every transaction matching ``filters`` across all pages.

        The server's ``count`` field is the *current page length*, not
        the total — so this iterator exhausts pages by detecting a
        partial page (``len(results) < page_size``), not by reading
        ``count``.
        """
        f = _resolve_filters(filters, kwargs)
        page = f.page
        while True:
            current = f.model_copy(update={"page": page})
            result = self.list(current)
            yield from result.results
            if not result.has_more:
                return
            page += 1


class AsyncTransactionsResource(_AsyncResource):
    """Async equivalent of :class:`TransactionsResource`."""

    async def list(
        self,
        filters: TransactionListFilters | None = None,
        /,
        **kwargs: Any,
    ) -> TransactionPage:
        f = _resolve_filters(filters, kwargs)
        data = await self._transport.request("GET", "transactions", params=f.to_query_params())
        return _parse_response(TransactionPage, data)

    async def get(self, id_or_order_id: str | UUID, /) -> Transaction:
        data = await self._transport.request("GET", f"transactions/{id_or_order_id}")
        return _parse_response(Transaction, data)

    async def iter_all(
        self,
        filters: TransactionListFilters | None = None,
        /,
        **kwargs: Any,
    ) -> AsyncIterator[Transaction]:
        f = _resolve_filters(filters, kwargs)
        page = f.page
        while True:
            current = f.model_copy(update={"page": page})
            result = await self.list(current)
            for tx in result.results:
                yield tx
            if not result.has_more:
                return
            page += 1


__all__ = ["AsyncTransactionsResource", "TransactionsResource"]
