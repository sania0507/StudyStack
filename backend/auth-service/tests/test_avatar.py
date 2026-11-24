"""Avatar upload, serving and removal."""

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"  # signature is enough for these tests; nothing decodes it
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\nIDAT\x78\x9c\x63\x00\x01\x00\x00\x05\x00"
    b"\x01\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def authenticated(client, email="avatar@example.com"):
    payload = {"email": email, "password": "TestPassword123!"}
    client.post("/auth/register", json=payload)
    token = client.post("/auth/login", json=payload).json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def test_new_user_has_no_avatar(client):
    headers = authenticated(client)

    me = client.get("/auth/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["has_avatar"] is False
    assert client.get("/auth/me/avatar", headers=headers).status_code == 404


def test_upload_stores_and_serves_the_image(client):
    headers = authenticated(client, email="upload@example.com")

    uploaded = client.post(
        "/auth/me/avatar",
        headers=headers,
        files={"file": ("me.png", PNG_BYTES, "image/png")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["has_avatar"] is True

    served = client.get("/auth/me/avatar", headers=headers)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")
    assert served.content == PNG_BYTES


def test_avatar_survives_a_new_login(client):
    # The bug this replaces: Profile.tsx used a blob URL, which died with the tab.
    payload = {"email": "persist@example.com", "password": "TestPassword123!"}
    client.post("/auth/register", json=payload)
    first = client.post("/auth/login", json=payload).json()["access_token"]

    client.post(
        "/auth/me/avatar",
        headers={"Authorization": f"Bearer {first}"},
        files={"file": ("me.png", PNG_BYTES, "image/png")},
    )

    second = client.post("/auth/login", json=payload).json()["access_token"]
    headers = {"Authorization": f"Bearer {second}"}

    assert client.get("/auth/me", headers=headers).json()["has_avatar"] is True
    assert client.get("/auth/me/avatar", headers=headers).content == PNG_BYTES


def test_delete_removes_the_avatar(client):
    headers = authenticated(client, email="delete-avatar@example.com")
    client.post(
        "/auth/me/avatar",
        headers=headers,
        files={"file": ("me.png", PNG_BYTES, "image/png")},
    )

    removed = client.delete("/auth/me/avatar", headers=headers)

    assert removed.status_code == 200
    assert removed.json()["has_avatar"] is False
    assert client.get("/auth/me/avatar", headers=headers).status_code == 404


def test_rejects_a_non_image_content_type(client):
    headers = authenticated(client, email="badtype@example.com")

    response = client.post(
        "/auth/me/avatar",
        headers=headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422


def test_rejects_an_oversized_avatar(client):
    headers = authenticated(client, email="toobig@example.com")

    response = client.post(
        "/auth/me/avatar",
        headers=headers,
        files={"file": ("big.png", b"x" * (512 * 1024 + 1), "image/png")},
    )

    assert response.status_code == 413


def test_avatar_requires_authentication(client):
    assert client.get("/auth/me/avatar").status_code == 401
