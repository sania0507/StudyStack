from datetime import date, datetime, timedelta


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_empty_state_returns_zeroes(client):
    response = client.get("/analytics/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["hours_per_week"] == 0
    assert data["streak"] == 0
    assert data["overdue_count"] == 0
    assert data["total_minutes"] == 0
    assert data["total_sessions"] == 0


def test_hours_per_week_sums_only_this_week(
    client, db, user_a, domain_id, add_session
):
    today = datetime.now()

    # This week: 30 + 30 minutes = 1.0 hour.
    add_session(db, user_a, domain_id, 30, today)
    add_session(db, user_a, domain_id, 30, today)

    # Last week: must not be counted.
    add_session(db, user_a, domain_id, 60, today - timedelta(days=10))

    response = client.get("/analytics/summary")
    data = response.json()

    assert data["hours_per_week"] == 1.0
    assert data["total_minutes"] == 120


def test_streak_counts_consecutive_days(
    client, db, user_a, domain_id, add_session
):
    now = datetime.now()

    add_session(db, user_a, domain_id, 20, now)
    add_session(db, user_a, domain_id, 20, now - timedelta(days=1))
    add_session(db, user_a, domain_id, 20, now - timedelta(days=2))
    # Gap on day 3, so the streak stops at 3.
    add_session(db, user_a, domain_id, 20, now - timedelta(days=4))

    response = client.get("/analytics/summary")

    assert response.json()["streak"] == 3


def test_streak_survives_a_day_with_no_session_yet(
    client, db, user_a, domain_id, add_session
):
    # Streak should still be alive if the last session was yesterday.
    yesterday = datetime.now() - timedelta(days=1)
    add_session(db, user_a, domain_id, 20, yesterday)
    add_session(db, user_a, domain_id, 20, yesterday - timedelta(days=1))

    response = client.get("/analytics/summary")

    assert response.json()["streak"] == 2


def test_overdue_count_ignores_completed_tasks(
    client, db, user_a, domain_id, add_task
):
    past = datetime.now() - timedelta(days=2)
    future = datetime.now() + timedelta(days=2)

    add_task(db, domain_id, completed=False, due_date=past)
    add_task(db, domain_id, completed=True, due_date=past)
    add_task(db, domain_id, completed=False, due_date=future)
    add_task(db, domain_id, completed=False, due_date=None)

    response = client.get("/analytics/summary")

    assert response.json()["overdue_count"] == 1


def test_domain_completion_percentage(
    client, db, user_a, domain_id, add_task
):
    add_task(db, domain_id, completed=True)
    add_task(db, domain_id, completed=False)

    response = client.get("/analytics/summary")
    progress = response.json()["domain_completion"]

    assert len(progress) == 1
    assert progress[0]["total_tasks"] == 2
    assert progress[0]["completed_tasks"] == 1
    assert progress[0]["completion_percent"] == 50.0


def test_heatmap_has_one_entry_per_day(
    client, db, user_a, domain_id, add_session
):
    add_session(db, user_a, domain_id, 45, datetime.now())

    response = client.get("/analytics/summary", params={"heatmap_days": 7})
    heatmap = response.json()["heatmap"]

    assert len(heatmap) == 7
    assert heatmap[-1]["day"] == date.today().isoformat()
    assert heatmap[-1]["minutes"] == 45


def test_weekday_minutes_cover_every_weekday(
    client, db, user_a, domain_id, add_session
):
    add_session(db, user_a, domain_id, 30, datetime.now())

    response = client.get("/analytics/summary")
    weekdays = response.json()["weekday_minutes"]

    assert len(weekdays) == 7
    assert sum(day["minutes"] for day in weekdays) == 30


def test_another_users_sessions_are_not_counted(
    client, db, user_a, domain_id, add_session
):
    from uuid import uuid4

    other_user = uuid4()

    # A second user with their own domain and sessions.
    other_domain = uuid4()
    from models import Domain

    db.add(
        Domain(
            id=other_domain,
            name="Other",
            colour="violet",
            user_id=other_user,
        )
    )
    db.commit()

    add_session(db, other_user, other_domain, 90, datetime.now())
    add_session(db, user_a, domain_id, 30, datetime.now())

    response = client.get("/analytics/summary")
    data = response.json()

    assert data["total_minutes"] == 30
    assert data["total_sessions"] == 1
