import uuid

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _admin_headers() -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_update_and_list_retention_intervention():
    headers = _admin_headers()
    note = f"retention-test-{uuid.uuid4().hex}"

    create_response = client.post(
        "/api/v1/retention/interventions",
        headers=headers,
        json={
            "customer_id": "1",
            "offer_type": "Offer Discount",
            "status": "planned",
            "notes": note,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["customer_id"] == "1"
    assert created["status"] == "planned"
    assert created["created_by"] == "admin"

    update_response = client.patch(
        f"/api/v1/retention/interventions/{created['intervention_id']}",
        headers=headers,
        json={"status": "sent"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "sent"

    list_response = client.get(
        "/api/v1/retention/interventions?customer_id=1&status=sent",
        headers=headers,
    )

    assert list_response.status_code == 200
    interventions = list_response.json()
    assert any(item["intervention_id"] == created["intervention_id"] for item in interventions)


def test_create_retention_intervention_rejects_missing_customer():
    headers = _admin_headers()

    response = client.post(
        "/api/v1/retention/interventions",
        headers=headers,
        json={
            "customer_id": "missing-customer",
            "offer_type": "Offer Discount",
            "status": "planned",
        },
    )

    assert response.status_code == 404