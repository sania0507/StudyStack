"""Notes: folders, the date timeline, pinning, search, editing and ownership."""

from models import Note


def make_folder(client, name="DSA"):
    response = client.post("/note-folders", json={"name": name})
    assert response.status_code == 200, response.text
    return response.json()


def make_note(client, folder_id, title="Big-O intuition", body="O(n) means..."):
    response = client.post(
        "/notes",
        json={"folder_id": folder_id, "title": title, "body": body},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_a_folder_starts_empty_and_counts_its_notes(client):
    folder = make_folder(client)

    assert folder["note_count"] == 0

    make_note(client, folder["id"])

    listed = client.get("/note-folders").json()
    assert listed[0]["note_count"] == 1


def test_duplicate_folder_names_are_refused(client):
    make_folder(client, "diary")

    # Case-insensitive: "Diary" and "diary" are the same drawer.
    response = client.post("/note-folders", json={"name": "Diary"})

    assert response.status_code == 409


def test_notes_are_newest_first(client):
    folder = make_folder(client)

    older = make_note(client, folder["id"], title="Older")
    newer = make_note(client, folder["id"], title="Newer")

    titles = [n["title"] for n in client.get("/notes").json()]
    ids = {n["id"] for n in client.get("/notes").json()}

    assert titles.index("Newer") < titles.index("Older")
    assert ids == {older["id"], newer["id"]}


def test_pinned_notes_sort_above_newer_ones(client):
    folder = make_folder(client)
    old = make_note(client, folder["id"], title="Pinned but old")
    make_note(client, folder["id"], title="Recent")

    client.patch(f"/notes/{old['id']}", json={"pinned": True})

    assert client.get("/notes").json()[0]["title"] == "Pinned but old"


def test_search_matches_title_and_body(client):
    folder = make_folder(client)
    make_note(client, folder["id"], title="Graphs", body="breadth first search")
    make_note(client, folder["id"], title="Sorting", body="quicksort partition")

    by_title = client.get("/notes", params={"search": "graph"}).json()
    by_body = client.get("/notes", params={"search": "quicksort"}).json()

    assert [n["title"] for n in by_title] == ["Graphs"]
    assert [n["title"] for n in by_body] == ["Sorting"]


def test_search_stays_inside_the_selected_folder(client):
    dsa = make_folder(client, "DSA")
    diary = make_folder(client, "diary")
    make_note(client, dsa["id"], title="arrays")
    make_note(client, diary["id"], title="arrays again")

    only_dsa = client.get(
        "/notes", params={"folder_id": dsa["id"], "search": "arrays"}
    ).json()

    assert len(only_dsa) == 1
    assert only_dsa[0]["folder_id"] == dsa["id"]


def test_editing_a_note_updates_it_without_moving_the_timeline(client):
    folder = make_folder(client)
    note = make_note(client, folder["id"])

    edited = client.patch(
        f"/notes/{note['id']}",
        json={"title": "Renamed", "body": "**markdown** body"},
    )

    assert edited.status_code == 200
    assert edited.json()["title"] == "Renamed"
    assert edited.json()["body"] == "**markdown** body"
    # created_at is the timeline anchor and must not move.
    assert edited.json()["created_at"] == note["created_at"]


def test_a_note_can_move_to_another_folder(client):
    source = make_folder(client, "DSA")
    target = make_folder(client, "dev")
    note = make_note(client, source["id"])

    moved = client.patch(f"/notes/{note['id']}", json={"folder_id": target["id"]})

    assert moved.status_code == 200
    assert moved.json()["folder_id"] == target["id"]


def test_a_note_cannot_move_into_someone_elses_folder(client, second_user_client):
    mine = make_folder(client)
    their_folder = second_user_client.post(
        "/note-folders", json={"name": "private"}
    ).json()
    note = make_note(client, mine["id"])

    response = client.patch(
        f"/notes/{note['id']}", json={"folder_id": their_folder["id"]}
    )

    assert response.status_code == 404


def test_deleting_a_folder_takes_its_notes(client, db_session):
    folder = make_folder(client)
    make_note(client, folder["id"])

    assert client.delete(f"/note-folders/{folder['id']}").status_code == 200

    assert client.get("/notes").json() == []
    assert db_session.query(Note).count() == 0


def test_notes_are_invisible_to_another_user(client, second_user_client):
    folder = make_folder(client)
    note = make_note(client, folder["id"])

    assert second_user_client.get("/notes").json() == []
    assert second_user_client.get("/note-folders").json() == []
    assert (
        second_user_client.patch(
            f"/notes/{note['id']}", json={"title": "hijacked"}
        ).status_code
        == 404
    )
    assert second_user_client.delete(f"/notes/{note['id']}").status_code == 404


def test_a_note_needs_a_title(client):
    folder = make_folder(client)

    response = client.post(
        "/notes",
        json={"folder_id": folder["id"], "title": "", "body": "no title"},
    )

    assert response.status_code == 422


def test_a_note_cannot_be_written_into_a_missing_folder(client):
    import uuid

    response = client.post(
        "/notes",
        json={"folder_id": str(uuid.uuid4()), "title": "orphan"},
    )

    assert response.status_code == 404
