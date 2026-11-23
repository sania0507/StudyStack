from datetime import datetime, timedelta


def test_task_includes_next_reminder_at(client, task_id):
    remind_at = (datetime.now() + timedelta(hours=3)).isoformat()

    client.post(
        "/reminders",
        json={"task_id": task_id, "remind_at": remind_at},
    )

    response = client.get("/tasks")
    assert response.status_code == 200

    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["next_reminder_at"] is not None


def test_task_without_reminders_has_null_next_reminder(client, task_id):
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json()[0]["next_reminder_at"] is None


def test_next_reminder_is_the_soonest_pending_one(client, task_id):
    now = datetime.now()
    soon = (now + timedelta(hours=1)).isoformat()
    later = (now + timedelta(days=5)).isoformat()

    client.post("/reminders", json={"task_id": task_id, "remind_at": later})
    client.post("/reminders", json={"task_id": task_id, "remind_at": soon})

    tasks = client.get("/tasks").json()
    returned = datetime.fromisoformat(tasks[0]["next_reminder_at"])

    # Should be the sooner one, not the later.
    assert abs((returned - (now + timedelta(hours=1))).total_seconds()) < 60


def test_sent_reminders_do_not_count_as_pending(client, task_id):
    from reminders import send_due_reminders
    from tests.conftest import TestingSessionLocal

    past = (datetime.now() - timedelta(hours=2)).isoformat()
    client.post("/reminders", json={"task_id": task_id, "remind_at": past})

    db = TestingSessionLocal()
    try:
        send_due_reminders(db)
    finally:
        db.close()

    tasks = client.get("/tasks").json()

    # Once sent, there is nothing pending to display.
    assert tasks[0]["next_reminder_at"] is None
