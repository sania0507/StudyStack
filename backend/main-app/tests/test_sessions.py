
def test_create_study_session(client, domain_id):
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "minutes": 25},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["domain_id"] == domain_id
    assert data["minutes"] == 25
    assert data["finished_at"] is not None


def test_list_study_sessions(client, domain_id):
    client.post("/sessions", json={"domain_id": domain_id, "minutes": 25})
    client.post("/sessions", json={"domain_id": domain_id, "minutes": 50})

    response = client.get("/sessions")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_session_requires_positive_minutes(client, domain_id):
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "minutes": 0},
    )

    assert response.status_code == 422


def test_cannot_log_session_against_another_users_domain(
    second_user_client,
    domain_id,
):
    response = second_user_client.post(
        "/sessions",
        json={"domain_id": domain_id, "minutes": 25},
    )

    assert response.status_code == 404


def test_sessions_are_scoped_to_their_owner(
    client,
    second_user_client,
    domain_id,
):
    client.post("/sessions", json={"domain_id": domain_id, "minutes": 25})

    response = second_user_client.get("/sessions")

    assert response.status_code == 200
    assert response.json() == []
