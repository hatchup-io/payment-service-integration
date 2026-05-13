"""Tests for the synchronous Transport.

Uses ``respx`` to mock the underlying ``httpx.Client``. No real network calls.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy
from hatchup_psip.exceptions import PSIPAPIError
from hatchup_psip.exceptions import PSIPAuthError
from hatchup_psip.exceptions import PSIPNetworkError
from hatchup_psip.exceptions import PSIPNotFoundError
from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.exceptions import PSIPServerError
from hatchup_psip.exceptions import PSIPValidationError
from hatchup_psip.transport import Transport

BASE = "https://test.example.com/api/v1/"
URL = "https://test.example.com/api/v1/payment"


def _envelope(data: Any = None, status: str = "ok", message: str = "") -> dict[str, Any]:
    return {"data": data, "status": status, "message": message}


@pytest.fixture
def fast_config() -> PSIPConfig:
    """Config with retries disabled — most tests only care about a single response."""
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


@pytest.fixture
def transport(fast_config: PSIPConfig) -> Transport:
    return Transport(fast_config)


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


def test_returns_data_dict_on_2xx(transport: Transport) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(200, json=_envelope(data={"order_id": "ord_1"})),
        )
        data = transport.request("POST", "payment", json={"price": "1.00"})
    assert data == {"order_id": "ord_1"}


def test_sets_authorization_and_user_agent_headers(fast_config: PSIPConfig) -> None:
    with respx.mock:
        route = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(data={"ok": True})))
        with Transport(fast_config) as t:
            t.request("GET", "payment")

    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer hp_test_key_12345"
    assert sent.headers["User-Agent"].startswith("hatchup-psip/")
    assert "api=v1" in sent.headers["User-Agent"]
    assert sent.headers["Accept"] == "application/json"


def test_passes_json_and_params(transport: Transport) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=_envelope(data={})))
        transport.request("POST", "payment", json={"price": "9.99"}, params={"sandbox": "true"})

    sent = route.calls.last.request
    assert sent.url.params["sandbox"] == "true"
    assert b'"price"' in sent.content


# --------------------------------------------------------------------------- #
# Idempotency-Key header
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutating_methods_send_idempotency_key(transport: Transport, method: str) -> None:
    with respx.mock:
        route = respx.route(method=method, url=URL).mock(
            return_value=httpx.Response(200, json=_envelope(data={})),
        )
        transport.request(method, "payment", json={} if method != "DELETE" else None)

    sent = route.calls.last.request
    assert sent.headers["Idempotency-Key"]
    # Default keys are uuid4 hex — 32 lowercase hex chars.
    assert len(sent.headers["Idempotency-Key"]) == 32


def test_get_does_not_send_idempotency_key(transport: Transport) -> None:
    with respx.mock:
        route = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(data={})))
        transport.request("GET", "payment")

    assert "Idempotency-Key" not in route.calls.last.request.headers


def test_caller_supplied_idempotency_key_is_used_verbatim(transport: Transport) -> None:
    with respx.mock:
        route = respx.post(URL).mock(return_value=httpx.Response(200, json=_envelope(data={})))
        transport.request("POST", "payment", json={}, idempotency_key="wallet-deposit-42")

    assert route.calls.last.request.headers["Idempotency-Key"] == "wallet-deposit-42"


def test_idempotency_key_is_stable_across_retries(fast_config_with_retries: PSIPConfig) -> None:
    """A single logical request must reuse the same key across retries —
    otherwise the gateway treats each retry as a brand-new call and the
    idempotency guarantee is lost.
    """
    responses = [
        httpx.Response(503, json=_envelope(status="failure", message="busy")),
        httpx.Response(200, json=_envelope(data={"ok": True})),
    ]
    with respx.mock:
        route = respx.post(URL).mock(side_effect=responses)
        with Transport(fast_config_with_retries) as t:
            t.request("POST", "payment", json={})

    assert route.call_count == 2
    first_key = route.calls[0].request.headers["Idempotency-Key"]
    second_key = route.calls[1].request.headers["Idempotency-Key"]
    assert first_key
    assert first_key == second_key


# --------------------------------------------------------------------------- #
# HTTP-status → exception mapping
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("status_code", "exc_cls"),
    [
        (400, PSIPValidationError),
        (401, PSIPAuthError),
        (404, PSIPNotFoundError),
        (500, PSIPServerError),
        (502, PSIPServerError),
    ],
)
def test_http_errors_map_to_typed_exceptions(
    transport: Transport,
    status_code: int,
    exc_cls: type[PSIPAPIError],
) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(
                status_code,
                json=_envelope(status="failure", message="bad thing"),
            ),
        )
        with pytest.raises(exc_cls) as exc_info:
            transport.request("POST", "payment", json={})

    err = exc_info.value
    assert err.status_code == status_code
    assert err.message == "bad thing"
    assert err.raw["status"] == "failure"


def test_unmapped_4xx_falls_back_to_validation_error(transport: Transport) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(
                418,
                json=_envelope(status="failure", message="teapot"),
            ),
        )
        with pytest.raises(PSIPValidationError) as exc_info:
            transport.request("POST", "payment")
    assert exc_info.value.status_code == 418


def test_request_id_extracted_from_header(transport: Transport) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(
                400,
                json=_envelope(status="failure", message="bad"),
                headers={"X-Request-ID": "req_abc"},
            ),
        )
        with pytest.raises(PSIPValidationError) as exc_info:
            transport.request("POST", "payment")
    assert exc_info.value.request_id == "req_abc"


def test_4xx_without_json_body_still_raises_typed_error(transport: Transport) -> None:
    """Load balancer 502 with HTML body still yields a meaningful PSIPServerError."""
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(502, text="<html>Bad Gateway</html>"),
        )
        # 502 retries are disabled in fast_config (max_retries=0)
        with pytest.raises(PSIPServerError) as exc_info:
            transport.request("POST", "payment")
    assert exc_info.value.status_code == 502
    assert exc_info.value.raw == {}


def test_4xx_with_non_dict_json_body_still_raises_typed_error(transport: Transport) -> None:
    """A 4xx whose JSON happens to be a list (not an envelope) is still classified by status."""
    with respx.mock:
        respx.post(URL).mock(return_value=httpx.Response(400, json=[1, 2, 3]))
        with pytest.raises(PSIPValidationError) as exc_info:
            transport.request("POST", "payment")
    assert exc_info.value.status_code == 400
    assert exc_info.value.raw == {}


# --------------------------------------------------------------------------- #
# Protocol errors (server contract violations)
# --------------------------------------------------------------------------- #


def test_2xx_with_non_json_body_raises_protocol_error(transport: Transport) -> None:
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(200, text="not json", headers={"content-type": "text/plain"}),
        )
        with pytest.raises(PSIPProtocolError, match="non-JSON"):
            transport.request("POST", "payment")


def test_2xx_with_non_object_json_raises_protocol_error(transport: Transport) -> None:
    with respx.mock:
        respx.post(URL).mock(return_value=httpx.Response(200, json=[1, 2, 3]))
        with pytest.raises(PSIPProtocolError, match="object envelope"):
            transport.request("POST", "payment")


def test_2xx_with_non_dict_data_field_raises_protocol_error(transport: Transport) -> None:
    with respx.mock:
        respx.post(URL).mock(return_value=httpx.Response(200, json=_envelope(data="oops")))
        with pytest.raises(PSIPProtocolError, match="non-dict 'data'"):
            transport.request("POST", "payment")


def test_2xx_with_envelope_status_failure_raises_protocol_error(transport: Transport) -> None:
    """Server contradicting itself (200 OK + envelope says failure) — refuse to guess."""
    with respx.mock:
        respx.post(URL).mock(
            return_value=httpx.Response(200, json=_envelope(status="failure", message="weird")),
        )
        with pytest.raises(PSIPProtocolError, match="status='failure'"):
            transport.request("POST", "payment")


# --------------------------------------------------------------------------- #
# Network errors and retries
# --------------------------------------------------------------------------- #


def test_network_error_after_retries_raises_psip_network_error(
    fast_config_with_retries: PSIPConfig,
) -> None:
    with respx.mock:
        respx.post(URL).mock(side_effect=httpx.ConnectError("nope"))
        with Transport(fast_config_with_retries) as t, pytest.raises(PSIPNetworkError):
            t.request("POST", "payment")


def test_retries_recover_from_transient_network_error(
    fast_config_with_retries: PSIPConfig,
) -> None:
    responses: list[Any] = [
        httpx.ConnectError("first"),
        httpx.Response(200, json=_envelope(data={"recovered": True})),
    ]
    with respx.mock:
        respx.post(URL).mock(side_effect=responses)
        with Transport(fast_config_with_retries) as t:
            data = t.request("POST", "payment")
    assert data == {"recovered": True}


def test_503_retried_then_succeeds(fast_config_with_retries: PSIPConfig) -> None:
    responses = [
        httpx.Response(503, json=_envelope(status="failure", message="upstream busy")),
        httpx.Response(200, json=_envelope(data={"order_id": "x"})),
    ]
    with respx.mock:
        respx.post(URL).mock(side_effect=responses)
        with Transport(fast_config_with_retries) as t:
            data = t.request("POST", "payment")
    assert data == {"order_id": "x"}


def test_503_retries_exhausted_raises_server_error(fast_config_with_retries: PSIPConfig) -> None:
    response = httpx.Response(503, json=_envelope(status="failure", message="still busy"))
    with respx.mock:
        route = respx.post(URL).mock(return_value=response)
        with Transport(fast_config_with_retries) as t, pytest.raises(PSIPServerError):
            t.request("POST", "payment")
    # Should have called max_retries + 1 times = 3
    assert route.call_count == 3


def test_400_does_not_retry(fast_config_with_retries: PSIPConfig) -> None:
    """Deterministic 4xx errors must not be retried."""
    response = httpx.Response(400, json=_envelope(status="failure", message="invalid"))
    with respx.mock:
        route = respx.post(URL).mock(return_value=response)
        with Transport(fast_config_with_retries) as t, pytest.raises(PSIPValidationError):
            t.request("POST", "payment")
    assert route.call_count == 1


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


def test_close_closes_underlying_client(fast_config: PSIPConfig) -> None:
    t = Transport(fast_config)
    t.close()
    assert t._client.is_closed


def test_context_manager_closes_client(fast_config: PSIPConfig) -> None:
    with Transport(fast_config) as t:
        client = t._client
        assert not client.is_closed
    assert client.is_closed


def test_config_property_exposes_input_config(fast_config: PSIPConfig) -> None:
    t = Transport(fast_config)
    try:
        assert t.config is fast_config
    finally:
        t.close()
