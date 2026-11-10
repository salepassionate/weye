"""Basic reservation API smoke tests for the demonstration environment."""
from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

def test_health():
    # Verify that the API can respond to a health request.
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"

def test_availability_and_idempotent_booking():
    # Choose future dates to keep the test valid over time.
    arrival = date.today() + timedelta(days=30)
    departure = arrival + timedelta(days=2)
    stay = {"check_in": arrival.isoformat(), "check_out": departure.isoformat(), "guests": 2}
    with TestClient(app) as client:
        rooms = client.post("/availability", json=stay)
        assert rooms.status_code == 200
        assert rooms.json()["rooms"]
        room_id = rooms.json()["rooms"][0]["room_type_id"]
        payload = {**stay, "room_type_id": room_id, "guest_name": "Demo Guest", "idempotency_key": str(uuid4())}
        first = client.post("/reservations", json=payload)
        assert first.status_code == 201
        second = client.post("/reservations", json=payload)
        assert second.status_code == 201
        assert first.json()["reference"] == second.json()["reference"]

def test_invalid_stay_dates():
    # Reject stays where checkout is not after checkin.
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    with TestClient(app) as client:
        response = client.post("/availability", json={"check_in": tomorrow, "check_out": tomorrow, "guests": 1})
        assert response.status_code == 422
