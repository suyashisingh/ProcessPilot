from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class RequestCreate(BaseModel):
    category: Literal["hr", "it"]
    request_type: str = Field(min_length=3, max_length=80)
    requester_email: EmailStr
    summary: str = Field(min_length=5, max_length=2000)
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalInput(BaseModel):
    approver: EmailStr
    approved: bool
    note: str = Field(default="", max_length=1000)


class FulfilmentInput(BaseModel):
    fulfiller: str = Field(min_length=2, max_length=255)
    note: str = Field(default="", max_length=1000)


class AuditEventRead(BaseModel):
    event_type: str
    actor: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class RequestRead(BaseModel):
    id: str
    category: str
    request_type: str
    requester_email: str
    summary: str
    details: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime | None
    audit_events: list[AuditEventRead] = []

    model_config = {"from_attributes": True}


class ConversationInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    requester_email: EmailStr | None = None


class Source(BaseModel):
    title: str
    excerpt: str
    confidence: float


class ConversationResponse(BaseModel):
    intent: str
    confidence: float
    reply: str
    suggested_reply: str
    sources: list[Source]
