"""Vision board: ownership, positions, both ways of adding an image."""

import uuid

from models import VisionItem

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def add_by_upload(client, caption=None):
    response = client.post(
        "/vision-items/upload",
        files={"file": ("dream.png", PNG, "image/png")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_uploading_an_image_appears_on_the_board(client):
    item = add_by_upload(client)

    listed = client.get("/vision-items").json()

    assert [i["id"] for i in listed] == [item["id"]]
    assert listed[0]["x"] == 0
    assert listed[0]["y"] == 0


def test_the_image_is_served_back(client):
    item = add_by_upload(client)

    image = client.get(f"/vision-items/{item['id']}/image")

    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/png")
    assert image.content == PNG


def test_a_position_survives_a_patch(client):
    item = add_by_upload(client)

    moved = client.patch(
        f"/vision-items/{item['id']}",
        json={"x": 42.5, "y": 18},
    )

    assert moved.status_code == 200
    assert moved.json()["x"] == 42.5
    assert moved.json()["y"] == 18

    # ...and it is persisted, not just echoed.
    listed = client.get("/vision-items").json()[0]
    assert listed["x"] == 42.5


def test_positions_outside_the_board_are_rejected(client):
    item = add_by_upload(client)

    assert client.patch(f"/vision-items/{item['id']}", json={"x": 140}).status_code == 422
    assert client.patch(f"/vision-items/{item['id']}", json={"y": -5}).status_code == 422


def test_a_caption_can_be_set(client):
    item = add_by_upload(client)

    patched = client.patch(f"/vision-items/{item['id']}", json={"caption": "  Own it  "})

    assert patched.json()["caption"] == "Own it"


def test_another_user_cannot_see_or_touch_the_board(client, second_user_client):
    item = add_by_upload(client)

    assert second_user_client.get("/vision-items").json() == []
    assert second_user_client.get(f"/vision-items/{item['id']}/image").status_code == 404
    assert second_user_client.patch(
        f"/vision-items/{item['id']}", json={"x": 10}
    ).status_code == 404
    assert second_user_client.delete(f"/vision-items/{item['id']}").status_code == 404


def test_deleting_removes_it(client, db_session):
    item = add_by_upload(client)

    assert client.delete(f"/vision-items/{item['id']}").status_code == 200
    assert client.get("/vision-items").json() == []
    assert db_session.query(VisionItem).count() == 0


def test_upload_rejects_a_non_image(client):
    response = client.post(
        "/vision-items/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422


def test_upload_rejects_an_oversized_image(client):
    response = client.post(
        "/vision-items/upload",
        files={"file": ("big.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")},
    )

    assert response.status_code == 413


def test_a_link_that_is_not_an_image_is_refused(client):
    # No network in tests: this asserts the failure path, which is what a dead
    # Pinterest link would hit.
    response = client.post(
        "/vision-items",
        json={"image_url": "https://example.invalid/nope.png"},
    )

    assert response.status_code == 422
