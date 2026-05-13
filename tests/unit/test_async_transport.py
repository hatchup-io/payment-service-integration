"""Tests for AsyncTransport — mirrors test_transport.py for the async path."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy
from hatchup_psip.exceptions import PSIPAuthError
from hatchup_psip.exceptions import PSIPNetworkError
from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.exceptions import PSIPServerError
from hatchup_psip.exceptions import PSIPValidationError
from hatchup_psip.transport import AsyncTransport

BASE = "https://test.example.com/api/v1/"
URL = "https://test.example.com/api/v1/payment"


def _envelope(data: Any = None, status: str = "ok", message: str = "") -> dict[str, Any]:
    return {"data": data, "status": status, "message": message}


@pytest.fixture
def fast_config() -> PSIPConfig:
    return PSIPConfig(
        api_key=SecretStr("hp_test_key_12345"),
        base_url=BASE,
        retry=RetryPolicy(max_retries=0, backoff_factor=0),
    )


@pytest.fixture
def fast_config_with_retries() -> PSIPConfig:
    return PSIPConfig(
        api_key=SecretStr("hp_test_key_12345"),
        base_url=BASE,
        retry=RetryPolicy(max_retries=2, backoff_factor=0),
    )


# --------------------------------------------------------------------------- #
# Happy path + headers
# --------------------------------------------------------------------------- #


async def test_returns_data_dict(fast_config: PSIPConfig) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(200, json=_envelope(data={"order_id": "ord_1"})),
        )
        async with AsyncTransport(fast_config) as t:
            data = await t.request("POST", "payment", json={"price": "1.00"})
    assert data == {"order_id": "ord_1"}


async def test_sets_authorization_and_user_agent(fast_config: PSIPConfig) -> None:
    with respx.mock:
        route = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(data={"ok": True})))
        async with AsyncTransport(fast_config) as t:
            await t.request("GET", "payment")

    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer hp_test_key_12345"
    assert "hatchup-psip/" in sent.headers["User-Agent"]


# --------------------------------------------------------------------------- #
# Idempotency-Key header
# --------------------------------------------------------------------------- #


async def test_post_sends_idempotency_key(fast_config: PSIPConfig) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=_envelope(data={})))
        async with AsyncTransport(fast_config) as t:
            await t.request("POST", "payment", json={})

    assert len(route.calls.last.request.headers["Idempotency-Key"]) == 32


async def test_get_does_not_send_idempotency_key(fast_config: PSIPConfig) -> None:
    with respx.mock:
        route = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(data={})))
        async with AsyncTransport(fast_config) as t:
            await t.request("GET", "payment")

    assert "Idempotency-Key" not in route.calls.last.request.headers


async def test_caller_supplied_idempotency_key_is_used_verbatim(fast_config: PSIPConfig) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=_envelope(data={})))
        async with AsyncTransport(fast_config) as t:
            await t.request("POST", "payment", json={}, idempotency_key="wallet-deposit-42")

    assert route.calls.last.request.headers["Idempotency-Key"] == "wallet-deposit-42"


async def test_idempotency_key_stable_across_retries(fast_config_with_retries: PSIPConfig) -> None:
    responses = [
        httpx.Response(503, json=_envelope(status="failure", message="busy")),
        httpx.Response(200, json=_envelope(data={"ok": True})),
    ]
    with respx.mock:
        route = respx.post(URL).mock(side_effect=responses)
        async with AsyncTransport(fast_config_with_retries) as t:
            await t.request("POST", "payment", json={})

    assert route.call_count == 2
    first_key = route.calls[0].request.headers["Idempotency-Key"]
    second_key = route.calls[1].request.headers["Idempotency-Key"]
    assert first_key
    assert first_key == second_key


# --------------------------------------------------------------------------- #
# Error mapping (the underlying _classify_error is shared with sync — one smoke each)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("status_code", "exc_cls"),
    [
        (400, PSIPValidationError),
        (401, PSIPAuthError),
        (404, PSIPNotFoundError),
        (500, PSIPServerError),
    ],
)
async def test_http_errors_map_to_typed_exceptions(
    fast_config: PSIPConfig,
    status_code: int,
    exc_cls: type[Exception],
) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(
                status_code,
                json=_envelope(status="failure", message="bad"),
            ),
        )
        async with AsyncTransport(fast_config) as t:
            with pytest.raises(exc_cls):
                await t.request("POST", "payment")


async def test_protocol_error_on_non_envelope(fast_config: PSIPConfig) -> None:
    with respx.mock:
        respx.post(URL).mock(return_value=httpx.Response(200, json=[1, 2, 3]))
        async with AsyncTransport(fast_config) as t:
            with pytest.raises(PSIPProtocolError):
                await t.request("POST", "payment")


# --------------------------------------------------------------------------- #
# Retries (the only meaningfully-async logic — uses asyncio.sleep)
# --------------------------------------------------------------------------- #


async def test_503_retried_then_succeeds(fast_config_with_retries: PSIPConfig) -> None:
    responses = [
        httpx.Response(503, json=_envelope(status="failure", message="busy")),
        httpx.Response(200, json=_envelope(data={"order_id": "x"})),
    ]
    with respx.mock:
        respx.post(URL).mock(side_effect=responses)
        async with AsyncTransport(fast_config_with_retries) as t:
            data = await t.request("POST", "payment")
    assert data == {"order_id": "x"}


async def test_503_retries_exhausted_raises_server_error(
    fast_config_with_retries: PSIPConfig,
) -> None:
    response = httpx.Response(503, json=_envelope(status="failure", message="still busy"))
    with respx.mock:
        route = respx.post(URL).mock(return_value=response)
        async with AsyncTransport(fast_config_with_retries) as t:
            with pytest.raises(PSIPServerError):
                await t.request("POST", "payment")
    assert route.call_count == 3


async def test_400_does_not_retry(fast_config_with_retries: PSIPConfig) -> None:
    response = httpx.Response(400, json=_envelope(status="failure", message="invalid"))
    with respx.mock:
        route = respx.post(URL).mock(return_value=response)
        async with AsyncTransport(fast_config_with_retries) as t:
            with pytest.raises(PSIPValidationError):
                await t.request("POST", "payment")
    assert route.call_count == 1


async def test_network_error_retries_then_recovers(fast_config_with_retries: PSIPConfig) -> None:
    responses: list[Any] = [
        httpx.ConnectError("first"),
        httpx.Response(200, json=_envelope(data={"recovered": True})),
    ]
    with respx.mock:
        respx.post(URL).mock(side_effect=responses)
        async with AsyncTransport(fast_config_with_retries) as t:
            data = await t.request("POST", "payment")
    assert data == {"recovered": True}


async def test_network_error_after_retries_raises(fast_config_with_retries: PSIPConfig) -> None:
    with respx.mock:
        respx.post(URL).mock(side_effect=httpx.ConnectError("nope"))
        async with AsyncTransport(fast_config_with_retries) as t:
            with pytest.raises(PSIPNetworkError):
                await t.request("POST", "payment")


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


async def test_aclose_closes_underlying_client(fast_config: PSIPConfig) -> None:
    t = AsyncTransport(fast_config)
    await t.aclose()
    assert t._client.is_closed


async def test_async_context_manager_closes(fast_config: PSIPConfig) -> None:
    async with AsyncTransport(fast_config) as t:
        client = t._client
        assert not client.is_closed
    assert client.is_closed


async def test_config_property(fast_config: PSIPConfig) -> None:
    t = AsyncTransport(fast_config)
    try:
        assert t.config is fast_config
    finally:
        await t.aclose()
