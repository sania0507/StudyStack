from uuid import uuid4


def test_event_is_processed_once(db):
    from consumer import handle_event

    message = {
        "event_id": str(uuid4()),
        "event": "session.completed",
        "payload": {"minutes": 25},
    }

    assert handle_event(db, message) is True

    # Replaying the same event (at-least-once delivery) must be a no-op.
    assert handle_event(db, message) is False


def test_event_without_id_is_rejected(db):
    from consumer import handle_event

    assert handle_event(db, {"event": "session.completed"}) is False


def test_event_with_invalid_id_is_rejected(db):
    from consumer import handle_event

    message = {"event_id": "not-a-uuid", "event": "session.completed"}

    assert handle_event(db, message) is False
