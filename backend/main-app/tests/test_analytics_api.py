"""Analytics now lives in the task service, so these run with its fixtures."""
from datetime import datetime, timedelta


def add_session(client, domain_id, minutes):
    """Sessions are created through the API, which stamps finished_at itself."""
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "minutes": minutes},
    )
    assert response.status_code == 200
    return response.json()


def test_summary_is_empty_for_a_new_user(client):
    response = client.get("/analytics/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["hours_per_week"] == 0
    assert data["streak"] == 0
    assert data["overdue_count"] == 0
    assert data["total_minutes"] == 0
    assert data["total_sessions"] == 0


def test_summary_counts_a_logged_session(client, domain_id):
    add_session(client, domain_id, 45)

    data = client.get("/analytics/summary").json()

    assert data["total_minutes"] == 45
    assert data["total_sessions"] == 1
    assert data["days_with_sessions"] == 1
    assert data["streak"] >= 1
    # 45 minutes this week rounds to 0.75 hours.
    assert data["hours_per_week"] == 0.75


def test_summary_counts_overdue_tasks_only(client, domain_id):
    past = (datetime.now() - timedelta(days=2)).isoformat()

    overdue = client.post(
        "/tasks",
        json={"domain_id": domain_id, "title": "Late", "due_date": past},
    ).json()
    client.post(
        "/tasks",
        json={"domain_id": domain_id, "title": "No deadline"},
    )

    # One overdue, one with no due date at all.
    assert client.get("/analytics/summary").json()["overdue_count"] == 1

    # Completing it must remove it from the count.
    client.patch(f"/tasks/{overdue['id']}", json={"completed": True})
    assert client.get("/analytics/summary").json()["overdue_count"] == 0


def test_summary_domain_completion(client, domain_id):
    client.post("/tasks", json={"domain_id": domain_id, "title": "A"})
    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "B"}
    ).json()
    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    progress = client.get("/analytics/summary").json()["domain_completion"]

    assert len(progress) == 1
    assert progress[0]["total_tasks"] == 2
    assert progress[0]["completed_tasks"] == 1
    assert progress[0]["completion_percent"] == 50.0


def test_heatmap_length_is_adjustable(client, domain_id):
    add_session(client, domain_id, 30)

    data = client.get("/analytics/summary", params={"heatmap_days": 7}).json()

    assert len(data["heatmap"]) == 7
    assert data["heatmap"][-1]["minutes"] == 30


def test_weekday_split_covers_the_whole_week(client, domain_id):
    add_session(client, domain_id, 30)

    weekdays = client.get("/analytics/summary").json()["weekday_minutes"]

    assert len(weekdays) == 7
    assert sum(day["minutes"] for day in weekdays) == 30


def test_summary_is_scoped_to_the_caller(
    client, second_user_client, domain_id
):
    add_session(client, domain_id, 60)

    # The other user must not see the first user's minutes.
    other = second_user_client.get("/analytics/summary").json()
    assert other["total_minutes"] == 0


def test_summary_requires_authentication(client):
    # The TestClient always sends a test user, so check the real guard instead.
    from auth import get_current_user_id
    from main import app

    saved = app.dependency_overrides.pop(get_current_user_id, None)
    try:
        response = client.get("/analytics/summary")
        assert response.status_code == 401
    finally:
        if saved is not None:
            app.dependency_overrides[get_current_user_id] = saved
