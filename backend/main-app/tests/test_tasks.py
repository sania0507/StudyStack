
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



def test_cannot_create_task_in_another_users_domain(
    second_user_client, domain_id
):
    response = second_user_client.post(
        "/tasks",
        json={
            "domain_id": domain_id,
            "title": "Unauthorized task",
        },
    )

    assert response.status_code == 404
