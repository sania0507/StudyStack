
def test_deleting_a_domain_removes_its_tasks(client, domain_id):
    # Regression: tasks.domain_id had no ON DELETE CASCADE, so this returned
    # 500 instead of deleting.
    client.post("/tasks", json={"domain_id": domain_id, "title": "Orphan"})

    response = client.delete(f"/domains/{domain_id}")

    assert response.status_code == 200
    assert client.get("/tasks").json() == []
    assert client.get("/domains").json() == []


def test_deleting_a_domain_removes_nested_children(client, domain_id):
    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Parent"}
    ).json()
    client.post("/subtasks", json={"task_id": task["id"], "title": "Child"})
    client.post(
        "/reminders",
        json={"task_id": task["id"], "remind_at": "2030-01-01T09:00:00"},
    )
    client.post("/sessions", json={"domain_id": domain_id, "duration_seconds": 30 * 60})

    assert client.delete(f"/domains/{domain_id}").status_code == 200

    # The study graph goes: those rows belong to the domain.
    assert client.get("/tasks").json() == []
    assert client.get("/subtasks").json() == []
    assert client.get("/reminders").json() == []

    # The history stays. A deleted domain must not delete the hours spent on
    # it, so the session survives with its link removed and its name kept.
    sessions = client.get("/sessions").json()

    assert len(sessions) == 1
    assert sessions[0]["domain_id"] is None
    assert sessions[0]["domain_name"] == "University"
    assert sessions[0]["duration_seconds"] == 30 * 60


def test_deleting_an_empty_domain_still_works(client, domain_id):
    assert client.delete(f"/domains/{domain_id}").status_code == 200
    assert client.get("/domains").json() == []


def test_deleting_a_domain_keeps_analytics_history(client, domain_id):
    """The whole point: totals, heatmap and streak survive the delete."""
    from datetime import date

    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Finish the essay"}
    ).json()
    client.patch(f"/tasks/{task['id']}", json={"completed": True})
    client.post("/sessions", json={"domain_id": domain_id, "duration_seconds": 45 * 60})

    before = client.get("/analytics/summary").json()

    assert client.delete(f"/domains/{domain_id}").status_code == 200

    after = client.get("/analytics/summary").json()

    # Nothing about the work disappears.
    assert after["total_minutes"] == before["total_minutes"] == 45
    assert after["total_sessions"] == 1
    assert after["streak"] == 1

    today = next(
        day for day in after["heatmap"] if day["day"] == date.today().isoformat()
    )
    assert today["minutes"] == 45
    assert today["tasks_completed"] == 1

    # The domain itself is gone, so per-domain completion has nothing to show.
    assert after["domain_completion"] == []


def test_deleting_a_domain_keeps_the_task_completion_log(client, domain_id, db_session):
    """The day survives; only the link to the deleted task is cleared.

    Read through the db_session fixture, which is bound to the test database.
    Using database.SessionLocal() here would read DATABASE_URL from .env and
    point at a real database instead.
    """
    from models import TaskCompletion

    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Revision block"}
    ).json()
    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    assert client.delete(f"/domains/{domain_id}").status_code == 200

    # The API has no completions endpoint, so go straight to the rows.
    (row,) = db_session.query(TaskCompletion).all()

    assert row.task_id is None
    assert row.user_id is not None
