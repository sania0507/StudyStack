"""Refresh token rotation, reuse detection and revocation."""

from datetime import datetime, timedelta, timezone

import pytest

from models import RefreshToken
from security import hash_refresh_token


def register_and_login(client, email="refresh@example.com"):
    payload = {"email": email, "password": "TestPassword123!"}

    client.post("/auth/register", json=payload)
    response = client.post("/auth/login", json=payload)

    assert response.status_code == 200
    return response.json()


def test_login_returns_both_tokens(client):
    tokens = register_and_login(client)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] != tokens["refresh_token"]


def test_refresh_returns_a_new_pair(client):
    tokens = register_and_login(client)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200

    new_tokens = response.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # The new access token works.
    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me.status_code == 200


def test_old_refresh_token_stops_working_after_rotation(client):
    tokens = register_and_login(client)

    assert client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 200

    # Reuse of the rotated token revokes the family, so it stays rejected.
    second = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert second.status_code == 401


def test_reuse_revokes_the_whole_family(client):
    tokens = register_and_login(client)

    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert rotated.status_code == 200

    newest = rotated.json()["refresh_token"]

    # Presenting the already-rotated token is treated as theft.
    client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    # The token issued by that rotation is revoked too: both parties are out.
    after = client.post("/auth/refresh", json={"refresh_token": newest})
    assert after.status_code == 401


def test_unknown_refresh_token_is_rejected(client):
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )

    assert response.status_code == 401


def test_expired_refresh_token_is_rejected(client, db_session):
    tokens = register_and_login(client, email="expired@example.com")

    record = db_session.query(RefreshToken).filter(
        RefreshToken.token_hash == hash_refresh_token(tokens["refresh_token"])
    ).one()

    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401


def test_logout_revokes_the_refresh_token(client):
    tokens = register_and_login(client, email="logout@example.com")

    assert client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 204

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401


def test_logout_is_idempotent(client):
    tokens = register_and_login(client, email="logout-twice@example.com")

    first = client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    second = client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )

    assert first.status_code == 204
    assert second.status_code == 204


def test_changing_password_revokes_every_session(client):
    tokens = register_and_login(client, email="rotate-password@example.com")

    changed = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "current_password": "TestPassword123!",
            "new_password": "AnotherPassword123!",
        },
    )
    assert changed.status_code == 204

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401


def test_only_the_hashed_token_is_stored(client, db_session):
    tokens = register_and_login(client, email="hashed@example.com")

    stored = db_session.query(RefreshToken).all()

    assert len(stored) == 1
    assert stored[0].token_hash != tokens["refresh_token"]
    assert stored[0].token_hash == hash_refresh_token(tokens["refresh_token"])
