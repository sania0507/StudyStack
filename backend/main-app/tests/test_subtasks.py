
def test_create_subtask(client, task_id):
    response = client.post(
        "/subtasks",
        json={
            "task_id": task_id,
            "title": "Read chapter one",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Read chapter one"
    assert data["task_id"] == task_id
    assert data["completed"] is False


def test_list_subtasks(client, task_id):
    client.post(
        "/subtasks",
        json={"task_id": task_id, "title": "Read chapter one"},
    )
    client.post(
        "/subtasks",
        json={"task_id": task_id, "title": "Solve exercises"},
    )

    response = client.get("/subtasks")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_complete_subtask(client, task_id):
    created = client.post(
        "/subtasks",
        json={"task_id": task_id, "title": "Read chapter one"},
    )
    subtask_id = created.json()["id"]

    response = client.patch(
        f"/subtasks/{subtask_id}",
        json={"completed": True},
    )

    assert response.status_code == 200
    assert response.json()["completed"] is True



def test_cannot_create_subtask_for_another_users_task(
    second_user_client, task_id
):
    response = second_user_client.post(
        "/subtasks",
        json={
            "task_id": task_id,
            "title": "Unauthorized subtask",
        },
    )

    assert response.status_code == 404
