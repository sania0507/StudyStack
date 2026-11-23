# tests/test_profile.py

REGISTERED = {
    "email": "profile-user@example.com",
    "password": "OriginalPassword123!",
    "name": "Myra",
}


def register_and_login(client, payload=None):
    payload = payload or REGISTERED

    client.post("/auth/register", json=payload)

    response = client.post(
        "/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_stores_the_name(client):
    client.post("/auth/register", json=REGISTERED)

    token = client.post(
        "/auth/login",
        json={
            "email": REGISTERED["email"],
            "password": REGISTERED["password"],
        },
    ).json()["access_token"]

    response = client.get("/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["name"] == "Myra"


def test_register_without_a_name_still_works(client):
    payload = {
        "email": "no-name@example.com",
        "password": "OriginalPassword123!",
    }

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] is None


def test_update_name_persists(client):
    token = register_and_login(client)

    response = client.patch(
        "/auth/me",
        json={"name": "Renamed"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"

    # Read it back to prove it was stored, not just echoed.
    again = client.get("/auth/me", headers=auth_headers(token))
    assert again.json()["name"] == "Renamed"


def test_update_email_persists_and_allows_login(client):
    token = register_and_login(client)

    response = client.patch(
        "/auth/me",
        json={"email": "changed-address@example.com"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "changed-address@example.com"

    # The new address must now work for login.
    login = client.post(
        "/auth/login",
        json={
            "email": "changed-address@example.com",
            "password": REGISTERED["password"],
        },
    )
    assert login.status_code == 200


def test_cannot_take_another_users_email(client):
    register_and_login(client)

    # A second account.
    other = {
        "email": "other-user@example.com",
        "password": "OriginalPassword123!",
    }
    client.post("/auth/register", json=other)
    other_token = client.post(
        "/auth/login",
        json={"email": other["email"], "password": other["password"]},
    ).json()["access_token"]

    response = client.patch(
        "/auth/me",
        json={"email": REGISTERED["email"]},
        headers=auth_headers(other_token),
    )

    assert response.status_code == 409


def test_clearing_the_name_stores_null(client):
    token = register_and_login(client)

    response = client.patch(
        "/auth/me",
        json={"name": "   "},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["name"] is None


def test_change_password_succeeds_and_old_password_stops_working(client):
    token = register_and_login(client)

    response = client.post(
        "/auth/change-password",
        json={
            "current_password": REGISTERED["password"],
            "new_password": "BrandNewPassword456!",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 204

    # Old password rejected...
    old = client.post(
        "/auth/login",
        json={
            "email": REGISTERED["email"],
            "password": REGISTERED["password"],
        },
    )
    assert old.status_code == 401

    # ...new password accepted.
    new = client.post(
        "/auth/login",
        json={
            "email": REGISTERED["email"],
            "password": "BrandNewPassword456!",
        },
    )
    assert new.status_code == 200


def test_change_password_rejects_wrong_current_password(client):
    token = register_and_login(client)

    response = client.post(
        "/auth/change-password",
        json={
            "current_password": "NotTheRealPassword123!",
            "new_password": "BrandNewPassword456!",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 401


def test_change_password_rejects_short_new_password(client):
    token = register_and_login(client)

    response = client.post(
        "/auth/change-password",
        json={
            "current_password": REGISTERED["password"],
            "new_password": "short",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_profile_endpoints_require_authentication(client):
    assert client.get("/auth/me").status_code == 401
    assert client.patch("/auth/me", json={"name": "x"}).status_code == 401
    assert client.post(
        "/auth/change-password",
        json={"current_password": "a", "new_password": "b"},
    ).status_code == 401
