from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine, get_db
from app.knowledge import KnowledgeRetriever
from app.schemas import ApprovalInput, ConversationInput, ConversationResponse, FulfilmentInput, RequestCreate, RequestRead
from app.services import WorkflowService, classify_intent, compose_grounded_reply


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="ProcessPilot Cognitive Automation API", version="1.0.0", lifespan=lifespan)
# Ensures the schema exists for local runs and lightweight deployments.
# A production team can replace this with Alembic migrations without changing endpoints.
Base.metadata.create_all(bind=engine)


def require_orchestrate_token(x_orchestrate_token: str | None = Header(default=None)):
    expected = get_settings().orchestrate_shared_secret
    if expected and x_orchestrate_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Orchestrate token")


@app.get("/health")
def health():
    return {"status": "ok", "service": "processpilot"}


@app.post("/v1/conversations/message", response_model=ConversationResponse)
def conversation(payload: ConversationInput):
    intent, confidence = classify_intent(payload.message)
    sources = KnowledgeRetriever(get_settings()).search(payload.message)
    reply = compose_grounded_reply(intent, sources)
    return ConversationResponse(intent=intent, confidence=confidence, reply=reply, suggested_reply=reply, sources=sources)


@app.post("/v1/requests", response_model=RequestRead, status_code=status.HTTP_201_CREATED)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    return WorkflowService.create_request(db, payload)


@app.get("/v1/requests/{request_id}", response_model=RequestRead)
def get_request(request_id: str, db: Session = Depends(get_db)):
    return WorkflowService.get_request(db, request_id)


@app.post("/v1/requests/{request_id}/approvals", response_model=RequestRead)
def approve_request(request_id: str, payload: ApprovalInput, db: Session = Depends(get_db)):
    return WorkflowService.record_approval(db, request_id, payload)


@app.post("/v1/requests/{request_id}/fulfilments", response_model=RequestRead)
def fulfil_request(request_id: str, payload: FulfilmentInput, db: Session = Depends(get_db)):
    return WorkflowService.fulfil(db, request_id, payload)


# Watsonx Orchestrate skill endpoints. Configure these as HTTP skills using the YAML contract.
@app.post("/v1/orchestrate/skills/submit-request", response_model=RequestRead, dependencies=[Depends(require_orchestrate_token)])
def submit_request_skill(payload: RequestCreate, db: Session = Depends(get_db)):
    return WorkflowService.create_request(db, payload, actor="watsonx-orchestrate")


@app.post("/v1/orchestrate/skills/record-approval", response_model=RequestRead, dependencies=[Depends(require_orchestrate_token)])
def record_approval_skill(request_id: str, payload: ApprovalInput, db: Session = Depends(get_db)):
    return WorkflowService.record_approval(db, request_id, payload)


@app.post("/v1/orchestrate/skills/fulfil-request", response_model=RequestRead, dependencies=[Depends(require_orchestrate_token)])
def fulfil_request_skill(request_id: str, payload: FulfilmentInput, db: Session = Depends(get_db)):
    return WorkflowService.fulfil(db, request_id, payload)
