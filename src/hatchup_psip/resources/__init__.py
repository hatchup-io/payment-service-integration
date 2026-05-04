"""Resource proxy classes — one per logical area of the payment-system API."""

from hatchup_psip.resources.payments import PaymentsResource
from hatchup_psip.resources.transactions import TransactionsResource
from hatchup_psip.resources.verify import VerifyResource
from hatchup_psip.resources.webhooks import WebhooksResource

__all__ = [
    "PaymentsResource",
    "TransactionsResource",
    "VerifyResource",
    "WebhooksResource",
]
