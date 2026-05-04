"""Resource proxy classes — one per logical area of the payment-system API."""

from hatchup_psip.resources.payments import AsyncPaymentsResource
from hatchup_psip.resources.payments import PaymentsResource
from hatchup_psip.resources.transactions import AsyncTransactionsResource
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.resources.verify import AsyncVerifyResource
from hatchup_psip.resources.verify import VerifyResource
from hatchup_psip.resources.webhooks import AsyncWebhooksResource
from hatchup_psip.resources.webhooks import WebhooksResource

__all__ = [
    "AsyncPaymentsResource",
    "AsyncTransactionsResource",
    "AsyncVerifyResource",
    "AsyncWebhooksResource",
    "PaymentsResource",
    "TransactionsResource",
    "VerifyResource",
    "WebhooksResource",
]
