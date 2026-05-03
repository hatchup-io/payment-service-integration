"""Generic envelope model.

Every Hatchup Payment Service response is wrapped in
``{data, status, message}``. :class:`hatchup_psip.transport.Transport`
unwraps this envelope before resources see anything, so :class:`ApiEnvelope`
is **not** load-bearing at runtime — it exists for documentation, for
parsing fixtures in tests, and for anyone reaching for a typed view of a
raw response (e.g. when introspecting a webhook log).
"""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict


class ApiEnvelope[T](BaseModel):
    """Standard ``{data, status, message}`` response envelope."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    data: T
    status: Literal["ok", "failure"]
    message: str = ""

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"


__all__ = ["ApiEnvelope"]
