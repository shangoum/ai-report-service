from datetime import datetime

from app.services.context import build_context
from app.services.crm import CustomerData, Message


def _message(day: int, subject: str) -> Message:
    return Message(
        sent_at=datetime(2026, 11, day, 9, 0),
        direction="inbound",
        subject=subject,
        body="Hello,\n   multi-line    body",
    )


def test_context_keeps_most_recent_messages_first():
    customer = CustomerData(
        customer_id="C-1",
        name="Test User",
        segment="Retail",
        products=["Current account"],
        advisor_notes="",
        messages=[_message(1, "old"), _message(20, "newest"), _message(10, "middle")],
    )

    context = build_context(customer, max_messages=2)

    assert "Recent messages (2):" in context
    assert context.index("newest") < context.index("middle")
    assert "old" not in context
    assert "Hello, multi-line body" in context  # whitespace normalised
    assert "Advisor notes: none" in context


def test_context_without_messages():
    customer = CustomerData("C-2", "No Mail", "Retail", [], "")
    context = build_context(customer, max_messages=5)
    assert "Products: none" in context
    assert "- none" in context
