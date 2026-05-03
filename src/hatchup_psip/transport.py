"""HTTP transport for the Hatchup Payment Service SDK.

Centralizes:

- header construction (``Authorization``, ``User-Agent``)
- envelope decoding (``{data, status, message}``)
- HTTP-status → exception classification
- bounded retries on transient server errors

Resource classes never call :mod:`httpx` directly — they go through
:meth:`Transport.request` so error handling stays in one place.
"""

from __future__ import annotations

import json as _json
import time
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
    ) -> dict[str, Any]:
        """Execute a request and return the envelope's ``data`` field.

        Raises one of:

        - :class:`PSIPNetworkError` if the request never reached the server
          (after retries).
        - :class:`PSIPProtocolError` if the response body is not a valid
          ``{data, status, message}`` envelope, or the envelope contradicts
          a 2xx status code by saying ``status="failure"``.
        - :class:`PSIPAPIError` (one of its subclasses) on HTTP 4xx/5xx.
        """
        retry = self._config.retry
        last_network_error: httpx.RequestError | None = None
        for attempt in range(retry.max_retries + 1):
            try:
                response = self._client.request(method, path, json=json, params=params)
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
        envelope = self._decode_envelope(response)
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
        raise self._classify_error(
            status_code=response.status_code,
            message=message,
            raw=raw,
            request_id=request_id,
        )

    @staticmethod
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

    @staticmethod
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


__all__ = ["Transport"]
