
def test_create_task(client, domain_id):
    response = client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Study DBMS",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Study DBMS"
    assert data["domain_id"] == domain_id
    assert data["completed"] is False
    assert data["overdue"] is False


def test_cannot_create_task_in_another_users_domain(
    second_user_client,
    domain_id,
):
    response = second_user_client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Try accessing another user's domain",
        },
    )

    assert response.status_code == 404


def test_complete_task(client, task_id):
    response = client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["completed"] is True
    assert data["completed_at"] is not None



def test_cannot_update_another_users_task(client, task_id, second_user_client):
    # Regression: this test used to share its name with the create-ownership
    # test above, so Python kept only the later definition and this assertion
    # never ran.
    response = second_user_client.patch(
        f"/tasks/{task_id}",
        json={"completed": True},
    )

    assert response.status_code == 404


def test_can_clear_a_due_date(client, domain_id):
    # Regression: PATCH skipped due_date when it was None, so a deadline could
    # be set but never removed.
    created = client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Has a deadline",
            "due_date": "2030-01-01T09:00:00",
        },
    ).json()
    assert created["due_date"] is not None

    response = client.patch(
        f"/tasks/{created['id']}",
        json={"due_date": None},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is None
    assert response.json()["overdue"] is False


def test_omitting_due_date_leaves_it_unchanged(client, domain_id):
    created = client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Keeps its deadline",
            "due_date": "2030-01-01T09:00:00",
        },
    ).json()

    response = client.patch(
        f"/tasks/{created['id']}",
        json={"title": "Renamed only"},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] == created["due_date"]


def test_overdue_filter_is_computed_by_the_database(client, domain_id):
    overdue = client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Late",
            "due_date": "2020-01-01T00:00:00",
        },
    ).json()
    future = client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Later",
            "due_date": "2030-01-01T00:00:00",
        },
    ).json()
    no_deadline = client.post(
        "/tasks",
        json={"domain_id": domain_id, "title": "No deadline"},
    ).json()

    only_overdue = client.get("/tasks", params={"overdue": "true"}).json()
    assert [task["id"] for task in only_overdue] == [overdue["id"]]

    not_overdue = client.get("/tasks", params={"overdue": "false"}).json()
    assert {task["id"] for task in not_overdue} == {future["id"], no_deadline["id"]}

    # Completing an overdue task removes it from the overdue set.
    client.patch(f"/tasks/{overdue['id']}", json={"completed": True})
    assert client.get("/tasks", params={"overdue": "true"}).json() == []
