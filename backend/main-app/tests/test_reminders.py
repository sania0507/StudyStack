from datetime import datetime, timedelta

from database import get_db
from main import app
from reminders import send_due_reminders
from models import Base, Task
from tests.conftest import TestingSessionLocal, test_engine


def future_time():
    return (datetime.now() + timedelta(hours=2)).isoformat()


def past_time():
    return (datetime.now() - timedelta(hours=2)).isoformat()


def test_create_reminder(client, task_id):
    response = client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert data["sent_at"] is None


def test_list_reminders_for_a_task(client, task_id):
    client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )
    client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )

    response = client.get("/reminders", params={"task_id": task_id})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_reminder_time(client, task_id):
    created = client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )
    reminder_id = created.json()["id"]

    new_time = (datetime.now() + timedelta(days=3)).isoformat()

    response = client.patch(
        f"/reminders/{reminder_id}",
        json={"remind_at": new_time},
    )

    assert response.status_code == 200
    assert response.json()["sent_at"] is None


def test_delete_reminder(client, task_id):
    created = client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )
    reminder_id = created.json()["id"]

    response = client.delete(f"/reminders/{reminder_id}")
    assert response.status_code == 200

    remaining = client.get("/reminders", params={"task_id": task_id})
    assert remaining.json() == []


def test_cannot_create_reminder_for_another_users_task(
    second_user_client,
    task_id,
):
    response = second_user_client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )

    assert response.status_code == 404


def test_unknown_reminder_returns_404(client):
    response = client.patch(
        "/reminders/00000000-0000-0000-0000-000000000000",
        json={"remind_at": future_time()},
    )

    assert response.status_code == 404


def test_worker_sends_due_reminder_once(client, task_id):
    created = client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": past_time()},
    )
    reminder_id = created.json()["id"]

    db = TestingSessionLocal()
    try:
        # First run processes the reminder that is already due.
        assert send_due_reminders(db) == 1

        # Second run must not send the same reminder again.
        assert send_due_reminders(db) == 0
    finally:
        db.close()

    sent = client.get("/reminders", params={"task_id": task_id}).json()
    assert sent[0]["id"] == reminder_id
    assert sent[0]["sent_at"] is not None


def test_worker_ignores_future_reminder(client, task_id):
    client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": future_time()},
    )

    db = TestingSessionLocal()
    try:
        assert send_due_reminders(db) == 0
    finally:
        db.close()

    pending = client.get("/reminders", params={"sent": False}).json()
    assert len(pending) == 1


def test_worker_skips_completed_task(client, task_id):
    client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": past_time()},
    )
    client.patch(f"/tasks/{task_id}", json={"completed": True})

    db = TestingSessionLocal()
    try:
        assert send_due_reminders(db) == 0
    finally:
        db.close()
