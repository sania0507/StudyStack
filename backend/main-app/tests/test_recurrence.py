"""Daily routines: the tick resets tomorrow, the history does not."""

from datetime import date, datetime, timedelta
from uuid import UUID

from models import TaskCompletion
from services.recurrence import reset_recurring_tasks


def make_domain(client, name="Prayers", repeats=True):
    response = client.post("/domains", json={"name": name, "repeats_daily": repeats})
    assert response.status_code == 200
    return response.json()


def make_task(client, domain_id, title):
    return client.post("/tasks", json={"domain_id": domain_id, "title": title}).json()


def test_domain_exposes_its_repeat_rule(client):
    routine = make_domain(client, repeats=True)
    ordinary = make_domain(client, name="Assignments", repeats=False)

    assert routine["repeats_daily"] is True
    assert ordinary["repeats_daily"] is False


def test_the_rule_can_be_turned_on_later(client):
    domain = make_domain(client, repeats=False)
    make_task(client, domain["id"], "Fajr")

    patched = client.patch(f"/domains/{domain['id']}", json={"repeats_daily": True})

    assert patched.status_code == 200
    assert patched.json()["repeats_daily"] is True


def test_yesterdays_tick_is_reset_tomorrow(client, db_session, user_a):
    domain = make_domain(client, repeats=True)
    task = make_task(client, domain["id"], "Fajr")

    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    # Pretend the completion happened yesterday.
    db_session.execute(
        __import__("sqlalchemy").text(
            "UPDATE tasks SET completed_at = :y WHERE id = :i"
        ),
        {"y": datetime.now() - timedelta(days=1), "i": task["id"]},
    )
    db_session.commit()

    reset_recurring_tasks(db_session, user_a)

    after = [t for t in client.get("/tasks").json() if t["id"] == task["id"]][0]
    assert after["completed"] is False

    # ...but the day it was done is still on record.
    logged = db_session.query(TaskCompletion).filter(
        TaskCompletion.task_id == __import__("uuid").UUID(task["id"])
    ).all()
    assert len(logged) == 1


def test_ticking_today_is_not_reset_today(client):
    domain = make_domain(client, repeats=True)
    task = make_task(client, domain["id"], "Zuhr")

    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    # Reading the list must not immediately undo a tick made today.
    listed = [t for t in client.get("/tasks").json() if t["id"] == task["id"]][0]

    assert listed["completed"] is True


def test_a_non_recurring_task_is_never_reset(client, db_session, user_a):
    domain = make_domain(client, name="Assignments", repeats=False)
    task = make_task(client, domain["id"], "Submit report")

    client.patch(f"/tasks/{task['id']}", json={"completed": True})
    db_session.execute(
        __import__("sqlalchemy").text("UPDATE tasks SET completed_at = :y WHERE id = :i"),
        {"y": datetime.now() - timedelta(days=3), "i": task["id"]},
    )
    db_session.commit()

    reset_recurring_tasks(db_session, user_a)

    after = [t for t in client.get("/tasks").json() if t["id"] == task["id"]][0]
    assert after["completed"] is True


def test_the_log_keeps_one_row_per_day(client, db_session):
    domain = make_domain(client, repeats=True)
    task = make_task(client, domain["id"], "Asr")

    client.patch(f"/tasks/{task['id']}", json={"completed": True})
    client.patch(f"/tasks/{task['id']}", json={"completed": False})
    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    rows = db_session.query(TaskCompletion).filter(
        TaskCompletion.task_id == UUID(task["id"])
    ).all()

    assert len(rows) == 1


def test_the_log_records_the_owner(client, db_session, user_a):
    """The row must carry user_id: it has to outlive the task and the domain."""
    domain = make_domain(client, repeats=True)
    task = make_task(client, domain["id"], "Fajr")

    client.patch(f"/tasks/{task['id']}", json={"completed": True})

    row = db_session.query(TaskCompletion).one()

    assert row.user_id == user_a
    assert row.task_id == UUID(task["id"])
