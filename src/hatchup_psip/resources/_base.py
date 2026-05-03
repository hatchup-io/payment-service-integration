"""Shared infrastructure for resource proxy classes.

Each resource holds a single :class:`Transport` reference (no resource owns
its own ``httpx.Client``). The ``_parse_response`` helper wraps
:class:`pydantic.ValidationError` raised while parsing a server response as
a :class:`PSIPProtocolError` — that way every server-contract failure
collapses into the SDK's exception hierarchy and consumers can catch a
single ``PSIPError`` root.

Note: ``ValidationError`` raised while *building* a request from user input
is **not** wrapped — that's a caller bug, and the user benefits from
pydantic's detailed error message.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError

from hatchup_psip.exceptions import PSIPProtocolError
from hatchup_psip.transport import Transport


class _Resource:
    """Base class for every resource proxy."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport


def _parse_response[M: BaseModel](model_cls: type[M], data: dict[str, Any]) -> M:
    """Validate ``data`` against ``model_cls`` and re-raise as PSIPProtocolError on mismatch."""
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise PSIPProtocolError(
            f"server response did not match expected {model_cls.__name__} shape: {exc}",
        ) from exc


__all__ = ["_Resource", "_parse_response"]
