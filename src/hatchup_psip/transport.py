"""HTTP transport for the Hatchup Payment Service SDK.

Centralizes:

- header construction (``Authorization``, ``User-Agent``)
- envelope decoding (``{data, status, message}``)
- HTTP-status → exception classification
- bounded retries on transient server errors

Two transports are exposed: :class:`Transport` (sync) and
:class:`AsyncTransport` (async). They share envelope decoding and
error classification via the module-level helpers below — only the
HTTP call and sleep differ.

Resource classes never call :mod:`httpx` directly — they go through
``request()`` on the matching transport so error handling stays in
one place.
"""

from __future__ import annotations

import asyncio
import json as _json
import time
import uuid
from types import TracebackType
from typing import Any
from typing import Self

import httpx

from hatchup_psip.config import PSIPConfig
from hatchup_psip.exceptions import PSIPAPIError
from hatchup_psip.exceptions import PSIPAuthError
from hatchup_psip.exceptions import PSIPNetworkError
from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.exceptions import PSIPServerError
from hatchup_psip.exceptions import PSIPValidationError

_REQUEST_ID_HEADER = "X-Request-ID"
_IDEMPOTENCY_HEADER = "Idempotency-Key"
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class Transport:
    """Synchronous HTTP transport wrapping :class:`httpx.Client`.

    One instance per :class:`PSIPConfig`. Owned by the high-level
    :class:`PaymentServiceClient` (added in M1); also usable directly for
    advanced cases.

    Use as a context manager to ensure the underlying connection pool is
    released::

        with Transport(config) as transport:
            data = transport.request("POST", "payment", json={...})
    """

    def __init__(self, config: PSIPConfig, *, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key.get_secret_value()}",
                "User-Agent": config.user_agent,
                "Accept": "application/json",
            },
        )

    @property
    def config(self) -> PSIPConfig:
        return self._config

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute a request and return the envelope's ``data`` field.

        Mutating methods (``POST``/``PUT``/``PATCH``/``DELETE``) always carry
        an ``Idempotency-Key`` header. Callers can pin one via
        ``idempotency_key`` when they have a natural business key; otherwise
        a UUID4 is generated and reused across retries so the gateway treats
        retries of a failed request as the same call.

        Raises one of:

        - :class:`PSIPNetworkError` if the request never reached the server
          (after retries).
        - :class:`PSIPProtocolError` if the response body is not a valid
          ``{data, status, message}`` envelope, or the envelope contradicts
          a 2xx status code by saying ``status="failure"``.
        - :class:`PSIPAPIError` (one of its subclasses) on HTTP 4xx/5xx.
        """
        headers = _idempotency_headers(method, idempotency_key)
        retry = self._config.retry
        last_network_error: httpx.RequestError | None = None
        for attempt in range(retry.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers,
                )
            except httpx.RequestError as exc:
                last_network_error = exc
                if attempt < retry.max_retries:
                    time.sleep(retry.backoff_factor * (2**attempt))
                    continue
                raise PSIPNetworkError(f"transport failure calling {method} {path}: {exc}") from exc

            if response.status_code in retry.retry_on_status and attempt < retry.max_retries:
                time.sleep(retry.backoff_factor * (2**attempt))
                continue

            return self._handle_response(response)

        # Unreachable: every loop iteration either returns, continues, or raises.
        # Kept as a defensive barrier for type-checkers and as a tripwire if the
        # control flow is ever broken by future edits.
        raise PSIPNetworkError(  # pragma: no cover
            f"transport failure calling {method} {path}: {last_network_error}",
        )

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        return _handle_response(response)


# --------------------------------------------------------------------------- #
# Async transport
# --------------------------------------------------------------------------- #


class AsyncTransport:
    """Asynchronous HTTP transport wrapping :class:`httpx.AsyncClient`.

    Mirrors :class:`Transport` behavior — same envelope decoding, same
    error classification, same retry policy — but ``request()`` is a
    coroutine and ``time.sleep`` is replaced with ``asyncio.sleep`` so
    retries don't block the event loop.

    Use as an async context manager::

        async with AsyncTransport(config) as transport:
            data = await transport.request("POST", "payment", json={...})
    """

    def __init__(self, config: PSIPConfig, *, client: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._client = client or httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key.get_secret_value()}",
                "User-Agent": config.user_agent,
                "Accept": "application/json",
            },
        )

    @property
    def config(self) -> PSIPConfig:
        return self._config

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Execute an async request and return the envelope's ``data`` field.

        Same exception contract and idempotency-key semantics as
        :meth:`Transport.request`.
        """
        headers = _idempotency_headers(method, idempotency_key)
        retry = self._config.retry
        last_network_error: httpx.RequestError | None = None
        for attempt in range(retry.max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers,
                )
            except httpx.RequestError as exc:
                last_network_error = exc
                if attempt < retry.max_retries:
                    await asyncio.sleep(retry.backoff_factor * (2**attempt))
                    continue
                raise PSIPNetworkError(f"transport failure calling {method} {path}: {exc}") from exc

            if response.status_code in retry.retry_on_status and attempt < retry.max_retries:
                await asyncio.sleep(retry.backoff_factor * (2**attempt))
                continue

            return _handle_response(response)

        raise PSIPNetworkError(  # pragma: no cover
            f"transport failure calling {method} {path}: {last_network_error}",
        )


# --------------------------------------------------------------------------- #
# Shared response / error helpers
# --------------------------------------------------------------------------- #


def _idempotency_headers(method: str, idempotency_key: str | None) -> dict[str, str] | None:
    """Build per-request headers, attaching an ``Idempotency-Key`` for
    mutating methods. The same key is reused across SDK-level retries so
    the gateway recognizes them as one call.
    """
    if method.upper() not in _MUTATING_METHODS:
        return None
    return {_IDEMPOTENCY_HEADER: idempotency_key or uuid.uuid4().hex}


def _handle_response(response: httpx.Response) -> dict[str, Any]:
    envelope = _decode_envelope(response)
    request_id = response.headers.get(_REQUEST_ID_HEADER)

    if 200 <= response.status_code < 300:
        if envelope.get("status") == "failure":
            raise PSIPProtocolError(
                f"server returned 2xx with envelope status='failure': {envelope.get('message', '')!r}",
            )
        data = envelope.get("data")
        if not isinstance(data, dict):
            raise PSIPProtocolError(
                f"server returned 2xx with non-dict 'data' field: {type(data).__name__}",
            )
        return data

    message = str(envelope.get("message") or response.reason_phrase or "")
    raw = envelope if envelope else {}
    raise _classify_error(
        status_code=response.status_code,
        message=message,
        raw=raw,
        request_id=request_id,
    )


def _decode_envelope(response: httpx.Response) -> dict[str, Any]:
    """Decode the response body as a SDK envelope.

    On 4xx/5xx with a non-JSON body (e.g. an HTML 502 from a load
    balancer), return an empty dict so the caller can still raise a
    meaningful :class:`PSIPAPIError` with the HTTP status code. On 2xx
    with a non-envelope body, this returns ``{}`` and the caller raises
    :class:`PSIPProtocolError`.
    """
    try:
        body = response.json()
    except (_json.JSONDecodeError, ValueError):
        if 200 <= response.status_code < 300:
            raise PSIPProtocolError(
                f"non-JSON body on 2xx response (content-type={response.headers.get('content-type')!r})",
            ) from None
        return {}

    if not isinstance(body, dict):
        if 200 <= response.status_code < 300:
            raise PSIPProtocolError(
                f"expected JSON object envelope, got {type(body).__name__}",
            )
        return {}
    return body


def _classify_error(
    *,
    status_code: int,
    message: str,
    raw: dict[str, Any],
    request_id: str | None,
) -> PSIPAPIError:
    kwargs: dict[str, Any] = {
        "status_code": status_code,
        "message": message,
        "raw": raw,
        "request_id": request_id,
    }
    if status_code == 401:
        return PSIPAuthError(**kwargs)
    if status_code == 404:
        return PSIPNotFoundError(**kwargs)
    if 400 <= status_code < 500:
        return PSIPValidationError(**kwargs)
    if 500 <= status_code < 600:
        return PSIPServerError(**kwargs)
    return PSIPAPIError(**kwargs)  # pragma: no cover -- 1xx/3xx unreachable via httpx


__all__ = ["AsyncTransport", "Transport"]
