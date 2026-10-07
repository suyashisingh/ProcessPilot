# ProcessPilot — Cognitive Automation Assistant

ProcessPilot turns HR and IT service requests into auditable, approval-aware workflows. It combines a Watsonx Assistant conversation design, Watsonx Orchestrate skill contracts, a FastAPI automation API, PostgreSQL persistence, and a knowledge-grounded agent-assist layer.

## What it delivers

- **Conversational intake**: intents, entity collection, actions, and safe fallback handling for common HR/IT requests.
- **Cognitive agent assist**: suggested replies are grounded only in approved knowledge-base articles. When no supporting article is found, the assistant asks a clarifying question instead of inventing an answer.
- **Automation**: approval and fulfilment run through Orchestrate-compatible skill endpoints; a deterministic local workflow engine is included for development and demos.
- **Auditability**: every request, workflow transition, approval, and fulfilment event is recorded in PostgreSQL.
- **Deployment readiness**: Docker Compose, health checks, migrations-on-start, pytest coverage, and GitHub Actions CI.

## Architecture

```text
Watsonx Assistant ──► /v1/conversations/message ──► FastAPI
   intents/actions                                  │
                                                    ├─ KnowledgeRetriever (Watson Discovery or local KB)
Watsonx Orchestrate ─► /v1/orchestrate/skills/* ────┤
                                                    ├─ WorkflowService (approval → fulfilment)
                                                    └─ PostgreSQL (requests + immutable audit events)
```

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`, with interactive docs at `/docs`.

For a local, dependency-free test run:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
pytest
```

## Example flow

1. `POST /v1/conversations/message` with “I need access to Salesforce”.
2. The API detects `it.access_request`, returns a guided response, and creates a request when required fields are supplied.
3. Watsonx Orchestrate calls `POST /v1/orchestrate/skills/submit-request` and then `POST /v1/orchestrate/skills/record-approval`.
4. On approval, `POST /v1/orchestrate/skills/fulfil-request` records fulfilment and emits audit events.

## Watson configuration

Import [`watsonx-assistant/dialog.yaml`](watsonx-assistant/dialog.yaml) into Watsonx Assistant as the conversation blueprint. Configure actions to call the endpoints documented in [`watsonx-orchestrate/skills.yaml`](watsonx-orchestrate/skills.yaml).

Set `WATSON_DISCOVERY_URL`, `WATSON_DISCOVERY_APIKEY`, and `WATSON_DISCOVERY_PROJECT_ID` to enable IBM Watson Discovery retrieval. Without these variables, ProcessPilot uses the curated local knowledge base so development remains fully functional.

## API highlights

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/conversations/message` | Intent-aware conversation and grounded reply suggestions |
| `POST /v1/requests` | Create a service request |
| `POST /v1/requests/{id}/approvals` | Record an approval decision |
| `POST /v1/requests/{id}/fulfilments` | Complete an approved request |
| `GET /v1/requests/{id}` | Request plus audit history |
| `POST /v1/orchestrate/skills/*` | Orchestrate-friendly skill endpoints |

## Quality and security notes

- Incoming skill requests can be protected with `ORCHESTRATE_SHARED_SECRET` via `X-Orchestrate-Token`.
- API keys are read only from environment variables and never logged.
- Audit logs capture actor, event type, metadata, and timestamp.
- The database uses a SQLite fallback only for local tests; deployed containers use PostgreSQL.
