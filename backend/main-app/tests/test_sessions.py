
def test_create_study_session(client, domain_id):
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "duration_seconds": 25 * 60},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["domain_id"] == domain_id
    assert data["duration_seconds"] == 25 * 60
    assert data["finished_at"] is not None


def test_list_study_sessions(client, domain_id):
    client.post("/sessions", json={"domain_id": domain_id, "duration_seconds": 25 * 60})
    client.post("/sessions", json={"domain_id": domain_id, "duration_seconds": 50 * 60})

    response = client.get("/sessions")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_session_requires_a_positive_duration(client, domain_id):
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "duration_seconds": 0},
    )

    assert response.status_code == 422


def test_cannot_log_session_against_another_users_domain(
    second_user_client,
    domain_id,
):
    response = second_user_client.post(
        "/sessions",
        json={"domain_id": domain_id, "duration_seconds": 25 * 60},
    )

    assert response.status_code == 404


def test_sessions_are_scoped_to_their_owner(
    client,
    second_user_client,
    domain_id,
):
    client.post("/sessions", json={"domain_id": domain_id, "duration_seconds": 25 * 60})

    response = second_user_client.get("/sessions")

    assert response.status_code == 200
    assert response.json() == []


def test_a_session_can_be_recorded_against_a_task(client, domain_id):
    task = client.post(
        "/tasks", json={"domain_id": domain_id, "title": "Chapter 3"}
    ).json()

    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "task_id": task["id"], "duration_seconds": 90},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task["id"]
    # 90 seconds is preserved exactly; minutes would have rounded it.
    assert body["duration_seconds"] == 90


def test_a_session_cannot_target_a_task_in_another_domain(client, domain_id):
    other_domain = client.post("/domains", json={"name": "Elsewhere"}).json()
    foreign_task = client.post(
        "/tasks", json={"domain_id": other_domain["id"], "title": "Not mine"}
    ).json()

    response = client.post(
        "/sessions",
        json={
            "domain_id": domain_id,
            "task_id": foreign_task["id"],
            "duration_seconds": 60,
        },
    )

    assert response.status_code == 404


def test_a_short_block_survives_rounding(client, domain_id):
    client.post(
        "/sessions", json={"domain_id": domain_id, "duration_seconds": 40}
    )

    heatmap = client.get("/analytics/summary").json()["heatmap"]

    # 40 seconds rounds UP to a minute: it happened, so it must not read zero.
    assert heatmap[-1]["minutes"] == 1
