from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AuditEvent, ServiceRequest
from app.schemas import ApprovalInput, FulfilmentInput, RequestCreate


def audit(db: Session, request_id: str, event_type: str, actor: str, metadata: dict | None = None) -> None:
    db.add(AuditEvent(request_id=request_id, event_type=event_type, actor=actor, metadata_json=metadata or {}))


class WorkflowService:
    """The state machine used by API endpoints and Orchestrate skills alike."""

    @staticmethod
    def create_request(db: Session, payload: RequestCreate, actor: str | None = None) -> ServiceRequest:
        request = ServiceRequest(**payload.model_dump())
        db.add(request)
        db.flush()
        audit(db, request.id, "request.submitted", actor or payload.requester_email, {"request_type": request.request_type})
        audit(db, request.id, "approval.requested", "processpilot", {"route": "manager"})
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def get_request(db: Session, request_id: str) -> ServiceRequest:
        request = db.get(ServiceRequest, request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Service request not found")
        return request

    @classmethod
    def record_approval(cls, db: Session, request_id: str, payload: ApprovalInput) -> ServiceRequest:
        request = cls.get_request(db, request_id)
        if request.status != "submitted":
            raise HTTPException(status_code=409, detail=f"Cannot approve a request in '{request.status}' state")
        request.status = "approved" if payload.approved else "rejected"
        audit(db, request.id, "approval.approved" if payload.approved else "approval.rejected", payload.approver, {"note": payload.note})
        if payload.approved:
            audit(db, request.id, "fulfilment.queued", "processpilot", {"target": "automation"})
        db.commit()
        db.refresh(request)
        return request

    @classmethod
    def fulfil(cls, db: Session, request_id: str, payload: FulfilmentInput) -> ServiceRequest:
        request = cls.get_request(db, request_id)
        if request.status != "approved":
            raise HTTPException(status_code=409, detail="Only approved requests can be fulfilled")
        request.status = "fulfilled"
        audit(db, request.id, "fulfilment.completed", payload.fulfiller, {"note": payload.note})
        db.commit()
        db.refresh(request)
        return request


INTENTS = {
    "it.access_request": ("access", "permission", "salesforce", "application"),
    "it.password_reset": ("password", "reset", "locked", "login"),
    "hr.leave_request": ("leave", "vacation", "pto", "absence"),
    "hr.onboarding": ("onboard", "new hire", "joiner", "laptop"),
}


def classify_intent(message: str) -> tuple[str, float]:
    words = set(message.lower().split())
    scored = [(intent, len(words.intersection(keywords)) / len(keywords)) for intent, keywords in INTENTS.items()]
    intent, score = max(scored, key=lambda value: value[1])
    return (intent, round(score, 2)) if score > 0 else ("fallback", 0.0)


def compose_grounded_reply(intent: str, sources: list[dict]) -> str:
    if not sources:
        return "I don’t have an approved knowledge-base answer for that yet. Could you tell me whether this is an HR or IT request and what outcome you need?"
    article = sources[0]
    return f"For {intent.replace('.', ' ')}, the approved guidance is: {article['excerpt']} Would you like me to start a service request?"
