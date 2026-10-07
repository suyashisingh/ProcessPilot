from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_request():
    response = client.post("/v1/requests", json={
        "category": "it",
        "request_type": "application_access",
        "requester_email": "alex@example.com",
        "summary": "Need Salesforce access for pipeline reporting",
        "details": {"application": "Salesforce"},
    })
    assert response.status_code == 201
    return response.json()


def test_request_approval_and_fulfilment_is_audited():
    request = create_request()
    request_id = request["id"]

    approved = client.post(f"/v1/requests/{request_id}/approvals", json={
        "approver": "manager@example.com", "approved": True, "note": "Required for role"
    })
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    fulfilled = client.post(f"/v1/requests/{request_id}/fulfilments", json={
        "fulfiller": "it-automation", "note": "Assigned standard role"
    })
    assert fulfilled.status_code == 200
    assert fulfilled.json()["status"] == "fulfilled"

    result = client.get(f"/v1/requests/{request_id}").json()
    assert [event["event_type"] for event in result["audit_events"]] == [
        "request.submitted", "approval.requested", "approval.approved", "fulfilment.queued", "fulfilment.completed"
    ]


def test_cannot_fulfil_before_approval():
    request = create_request()
    response = client.post(f"/v1/requests/{request['id']}/fulfilments", json={"fulfiller": "it-team"})
    assert response.status_code == 409


def test_grounded_reply_has_approved_source():
    response = client.post("/v1/conversations/message", json={"message": "I need Salesforce access"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "it.access_request"
    assert body["sources"][0]["title"] == "Software access policy"


def test_fallback_does_not_invent_an_answer():
    response = client.post("/v1/conversations/message", json={"message": "Tell me about lunar real estate"})
    assert response.status_code == 200
    assert response.json()["intent"] == "fallback"
    assert response.json()["sources"] == []
