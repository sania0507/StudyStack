# tests/test_auth.py

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "pytest-user@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "pytest-user@example.com"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "TestPassword123!",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "email": "login-test@example.com",
            "password": "CorrectPassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login-test@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_login_success(client):
    # First, create a user.
    registration = client.post(
        "/auth/register",
        json={
            "email": "login-success@example.com",
            "password": "CorrectPassword123!",
        },
    )
    assert registration.status_code == 201

    # Then log in with the correct credentials.
    response = client.post(
        "/auth/login",
        json={
            "email": "login-success@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_me_with_valid_token(client):
    # Register a user.
    registration = client.post(
        "/auth/register",
        json={
            "email": "token-test@example.com",
            "password": "CorrectPassword123!",
        },
    )
    assert registration.status_code == 201
    registered_user = registration.json()

    # Log in to obtain a JWT.
    login = client.post(
        "/auth/login",
        json={
            "email": "token-test@example.com",
            "password": "CorrectPassword123!",
        },
    )
    assert login.status_code == 200

    token = login.json()["access_token"]

    # Send the JWT to the protected endpoint.
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    authenticated_user = response.json()
    assert authenticated_user["id"] == registered_user["id"]
    assert authenticated_user["email"] == "token-test@example.com"

