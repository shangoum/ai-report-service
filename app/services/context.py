"""Turns raw customer data into the prompt sent to the language model."""

from app.services.crm import CustomerData

SYSTEM_PROMPT = (
    "You are an assistant for bank advisors. From the customer data below, write a short "
    "report in Markdown with exactly these sections: '## Summary' (2-3 sentences on the "
    "customer and their recent requests), '## Opportunities' (bullet list of relevant "
    "products or actions), '## Suggested opener' (one sentence the advisor can say when "
    "picking up the call). Only use facts present in the data."
)


def build_context(customer: CustomerData, max_messages: int) -> str:
    """Build a compact, deterministic text context, most recent messages first."""
    recent = sorted(customer.messages, key=lambda m: m.sent_at, reverse=True)[:max_messages]

    lines = [
        f"Customer: {customer.name} ({customer.customer_id})",
        f"Segment: {customer.segment}",
        f"Products: {', '.join(customer.products) or 'none'}",
        f"Advisor notes: {customer.advisor_notes or 'none'}",
        "",
        f"Recent messages ({len(recent)}):",
    ]
    for m in recent:
        who = "Customer" if m.direction == "inbound" else "Bank"
        body = " ".join(m.body.split())  # normalise whitespace
        lines.append(f"- [{m.sent_at:%Y-%m-%d}] {who} - {m.subject}: {body}")
    if not recent:
        lines.append("- none")
    return "\n".join(lines)
