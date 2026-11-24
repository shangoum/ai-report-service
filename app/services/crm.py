"""Customer data source.

In a real system this would call internal APIs (CRM, mailbox, ...). Here a JSON file plays
that role so the project runs anywhere, behind the same async interface.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from importlib import resources
from typing import Protocol


class CustomerNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class Message:
    sent_at: datetime
    direction: str  # "inbound" (from the customer) or "outbound" (from the bank)
    subject: str
    body: str


@dataclass(frozen=True)
class CustomerData:
    customer_id: str
    name: str
    segment: str
    products: list[str]
    advisor_notes: str
    messages: list[Message] = field(default_factory=list)


class CustomerSource(Protocol):
    async def get_customer(self, customer_id: str) -> CustomerData: ...


class JsonCustomerSource:
    """Reads customers from a JSON file shipped with the package."""

    def __init__(self, raw: dict | None = None) -> None:
        if raw is None:
            text = resources.files("app.data").joinpath("customers.json").read_text("utf-8")
            raw = json.loads(text)
        self._customers = raw

    async def get_customer(self, customer_id: str) -> CustomerData:
        item = self._customers.get(customer_id)
        if item is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        messages = [
            Message(
                sent_at=datetime.fromisoformat(m["sent_at"]),
                direction=m["direction"],
                subject=m["subject"],
                body=m["body"],
            )
            for m in item.get("messages", [])
        ]
        return CustomerData(
            customer_id=customer_id,
            name=item["name"],
            segment=item["segment"],
            products=item.get("products", []),
            advisor_notes=item.get("advisor_notes", ""),
            messages=messages,
        )
