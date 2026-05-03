"""Tests for PSIPConfig and RetryPolicy."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from pydantic import ValidationError

from hatchup_psip._version import __version__
from hatchup_psip.config import DEFAULT_BASE_URL
from hatchup_psip.config import PSIPConfig
from hatchup_psip.config import RetryPolicy


def test_minimal_config_uses_defaults() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.timeout == 10.0
    assert cfg.default_sandbox is True
    assert cfg.user_agent == f"hatchup-psip/{__version__} (api=v1)"
    assert cfg.retry == RetryPolicy()


def test_api_key_must_have_hp_prefix() -> None:
    with pytest.raises(ValidationError, match="must start with 'hp_'"):
        PSIPConfig(api_key=SecretStr("sk_test_key"))


def test_api_key_must_not_be_too_short() -> None:
    with pytest.raises(ValidationError, match="too short"):
        PSIPConfig(api_key=SecretStr("hp_x"))


def test_base_url_requires_scheme() -> None:
    with pytest.raises(ValidationError, match="http://"):
        PSIPConfig(api_key=SecretStr("hp_test_key"), base_url="payments.hatchup.io/api/v1/")


def test_base_url_trailing_slash_added_when_missing() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"), base_url="https://x.test/api/v1")
    assert cfg.base_url == "https://x.test/api/v1/"


def test_base_url_trailing_slash_preserved() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"), base_url="https://x.test/api/v1/")
    assert cfg.base_url == "https://x.test/api/v1/"


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PSIPConfig(api_key=SecretStr("hp_test_key"), timeout=0)


def test_user_agent_must_not_be_empty() -> None:
    with pytest.raises(ValidationError, match="user_agent"):
        PSIPConfig(api_key=SecretStr("hp_test_key"), user_agent="   ")


def test_config_is_frozen() -> None:
    cfg = PSIPConfig(api_key=SecretStr("hp_test_key"))
    with pytest.raises(ValidationError):
        cfg.timeout = 99.0  # type: ignore[misc]


def test_retry_policy_defaults() -> None:
    policy = RetryPolicy()
    assert policy.max_retries == 2
    assert policy.backoff_factor == 0.5
    assert policy.retry_on_status == (502, 503, 504)


def test_retry_policy_caps_max_retries() -> None:
    with pytest.raises(ValidationError):
        RetryPolicy(max_retries=20)


class TestFromEnv:
    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ("PSIP_API_KEY", "PSIP_BASE_URL", "PSIP_TIMEOUT", "PSIP_DEFAULT_SANDBOX"):
            monkeypatch.delenv(key, raising=False)

    def test_reads_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PSIP_API_KEY", "hp_envkey123")
        cfg = PSIPConfig.from_env()
        assert cfg.api_key.get_secret_value() == "hp_envkey123"

    def test_reads_optional_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PSIP_API_KEY", "hp_envkey123")
        monkeypatch.setenv("PSIP_BASE_URL", "https://staging.payments.hatchup.io/api/v1")
        monkeypatch.setenv("PSIP_TIMEOUT", "5.5")
        monkeypatch.setenv("PSIP_DEFAULT_SANDBOX", "false")
        cfg = PSIPConfig.from_env()
        assert cfg.base_url == "https://staging.payments.hatchup.io/api/v1/"
        assert cfg.timeout == 5.5
        assert cfg.default_sandbox is False

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("anything-else", False),
        ],
    )
    def test_default_sandbox_parsing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        raw: str,
        expected: bool,
    ) -> None:
        monkeypatch.setenv("PSIP_API_KEY", "hp_envkey123")
        monkeypatch.setenv("PSIP_DEFAULT_SANDBOX", raw)
        cfg = PSIPConfig.from_env()
        assert cfg.default_sandbox is expected

    def test_overrides_beat_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PSIP_API_KEY", "hp_envkey123")
        monkeypatch.setenv("PSIP_TIMEOUT", "5.5")
        cfg = PSIPConfig.from_env(timeout=99.0)
        assert cfg.timeout == 99.0

    def test_custom_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FOO_API_KEY", "hp_fookey1234")
        cfg = PSIPConfig.from_env(prefix="FOO_")
        assert cfg.api_key.get_secret_value() == "hp_fookey1234"

    def test_missing_api_key_in_env_raises(self) -> None:
        with pytest.raises(ValidationError):
            PSIPConfig.from_env()
