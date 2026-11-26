"""Analytics now lives in the task service, so these run with its fixtures."""
from datetime import datetime, timedelta


def add_session(client, domain_id, minutes):
    """Sessions are created through the API, which stamps finished_at itself."""
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "duration_seconds": minutes * 60},
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


def test_streak_counts_ticked_tasks_without_any_timer_session(client, task_id):
    """Regression: the streak only read study_sessions, so ticking tasks all
    week and never running the timer reported 0."""
    assert client.patch(f"/tasks/{task_id}", json={"completed": True}).status_code == 200

    data = client.get("/analytics/summary").json()

    assert data["total_sessions"] == 0
    assert data["streak"] == 1


def test_streak_spans_task_completions(client, domain_id, db_session):
    """Two consecutive days, each with a completion and no session."""
    from datetime import date, timedelta
    from uuid import UUID, uuid4

    from models import TaskCompletion

    yesterday = date.today() - timedelta(days=1)

    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Read chapter"}
    ).json()
    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    # A completion logged yesterday, as the recurring-domain reset would leave.
    db_session.add(
        TaskCompletion(
            id=uuid4(),
            user_id=UUID(client.headers["X-Test-User-ID"]),
            task_id=UUID(task["id"]),
            completed_on=yesterday,
        )
    )
    db_session.commit()

    assert client.get("/analytics/summary").json()["streak"] == 2


def test_streak_ignores_other_users_completions(client, second_user_client, task_id):
    assert client.patch(f"/tasks/{task_id}", json={"completed": True}).status_code == 200

    assert second_user_client.get("/analytics/summary").json()["streak"] == 0


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


def make_subject(client, domain_id, title, topics, done):
    """A task with `topics` subtasks, the first `done` of them ticked."""
    task = client.post("/tasks", json={"domain_id": domain_id, "title": title}).json()

    for index in range(topics):
        subtask = client.post(
            "/subtasks", json={"task_id": task["id"], "title": f"Topic {index + 1}"}
        ).json()

        if index < done:
            client.patch(f"/subtasks/{subtask['id']}", json={"completed": True})

    return task


def test_domain_percent_is_measured_in_subtasks(client, domain_id):
    """4 of 5 compiler topics is 80%, not "0 of 1 subjects done"."""
    make_subject(client, domain_id, "Compiler Design", topics=5, done=4)

    progress = client.get("/analytics/summary").json()["domain_completion"][0]

    assert progress["total_subtasks"] == 5
    assert progress["completed_subtasks"] == 4
    assert progress["completion_percent"] == 80.0
    # Not every topic is ticked, so the subject itself is not finished.
    assert progress["completed_tasks"] == 0


def test_a_subject_counts_as_done_when_every_topic_is(client, domain_id):
    """The task's own tick is irrelevant once it has subtasks."""
    make_subject(client, domain_id, "Compiler Design", topics=3, done=3)

    progress = client.get("/analytics/summary").json()["domain_completion"][0]

    assert progress["completed_tasks"] == 1
    assert progress["completion_percent"] == 100.0


def test_a_task_with_no_subtasks_falls_back_to_its_own_tick(client, domain_id):
    """Hybrid rule: a plain to-do is not stuck at 0% forever."""
    plain = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Email the tutor"}
    ).json()
    client.patch(f"/tasks/{plain['id']}", json={"completed": True})

    progress = client.get("/analytics/summary").json()["domain_completion"][0]

    assert progress["total_subtasks"] == 0
    assert progress["total_tasks"] == 1
    assert progress["completed_tasks"] == 1
    assert progress["completion_percent"] == 100.0


def test_subtask_progress_mixes_with_plain_tasks(client, domain_id):
    """A subject tracked by topics and a plain to-do in the same domain."""
    make_subject(client, domain_id, "Compiler Design", topics=2, done=2)
    plain = client.post("/tasks", json={"domain_id": domain_id, "title": "Reading"}).json()
    client.patch(f"/tasks/{plain['id']}", json={"completed": True})

    progress = client.get("/analytics/summary").json()["domain_completion"][0]

    # Percentage comes from subtasks, because the domain has some.
    assert progress["total_subtasks"] == 2
    assert progress["completed_subtasks"] == 2
    assert progress["completion_percent"] == 100.0
    assert progress["completed_tasks"] == 2


def test_an_empty_domain_reports_zero_without_dividing_by_zero(client, domain_id):
    progress = client.get("/analytics/summary").json()["domain_completion"][0]

    assert progress["total_tasks"] == 0
    assert progress["total_subtasks"] == 0
    assert progress["completion_percent"] == 0.0


def test_domain_progress_is_scoped_to_the_owner(
    client, second_user_client, domain_id
):
    make_subject(client, domain_id, "Compiler Design", topics=4, done=4)

    # The other user has no domains, so there is nothing to report.
    assert second_user_client.get("/analytics/summary").json()["domain_completion"] == []


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


def test_heatmap_counts_tasks_completed_not_only_minutes(client, domain_id):
    # A day with finished tasks but no timer session still counts as activity.
    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Finish me"}
    ).json()
    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    heatmap = client.get("/analytics/summary").json()["heatmap"]
    today = heatmap[-1]

    assert today["minutes"] == 0
    assert today["tasks_completed"] == 1


def test_heatmap_counts_every_task_finished_on_the_same_day(client, domain_id):
    for n in range(3):
        task = client.post(
            "/tasks", json={"domain_id": domain_id, "title": f"Task {n}"}
        ).json()
        client.patch(f"/tasks/{task['id']}", json={"completed": True})

    today = client.get("/analytics/summary").json()["heatmap"][-1]

    assert today["tasks_completed"] == 3


def test_heatmap_never_reports_a_future_day(client):
    heatmap = client.get("/analytics/summary").json()["heatmap"]

    assert [day["day"] for day in heatmap] == sorted(day["day"] for day in heatmap)
    assert heatmap[-1]["day"] == __import__("datetime").date.today().isoformat()


def test_task_totals_attribute_time_to_the_right_task(client, domain_id):
    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Essay"}
    ).json()

    client.post(
        "/sessions",
        json={"domain_id": domain_id, "task_id": task["id"], "duration_seconds": 3600},
    )
    # A domain-only session must not be attributed to any task.
    client.post("/sessions", json={"domain_id": domain_id, "duration_seconds": 600})

    totals = client.get("/analytics/summary").json()["task_totals"]

    assert totals == [{"task_id": task["id"], "seconds": 3600}]
