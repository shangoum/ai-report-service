from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ReportStatus


class EventIn(BaseModel):
    """An event that should trigger a report, e.g. an incoming customer call."""

    type: Literal["incoming_call", "manual_request"] = "incoming_call"
    customer_id: str = Field(min_length=1, max_length=64, examples=["C-1001"])


class EventAccepted(BaseModel):
    report_id: str
    status: ReportStatus


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    event_type: str
    status: ReportStatus
    content: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
