
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
    client.post("/sessions", json={"domain_id": domain_id, "minutes": 30})

    assert client.delete(f"/domains/{domain_id}").status_code == 200

    assert client.get("/tasks").json() == []
    assert client.get("/subtasks").json() == []
    assert client.get("/reminders").json() == []
    assert client.get("/sessions").json() == []


def test_deleting_an_empty_domain_still_works(client, domain_id):
    assert client.delete(f"/domains/{domain_id}").status_code == 200
    assert client.get("/domains").json() == []
