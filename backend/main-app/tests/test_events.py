from unittest.mock import patch


def test_publish_returns_false_when_broker_is_unreachable():
    from unittest.mock import patch

    import events

    # Point at a port nothing listens on, so this stays true whether or not
    # a real broker happens to be running.
    unreachable = events.settings.model_copy(
        update={"rabbitmq_url": "amqp://guest:guest@127.0.0.1:1/"}
    )

    with patch.object(events, "settings", unreachable):
        result = events.publish_event("session.completed", {"minutes": 25})

    assert result is False


def test_creating_a_session_succeeds_without_a_broker(client, domain_id):
    response = client.post(
        "/sessions",
        json={"domain_id": domain_id, "minutes": 25},
    )

    # Analytics being down must never break the user's own write.
    assert response.status_code == 200
    assert response.json()["minutes"] == 25


def test_completing_a_task_publishes_an_event(client, task_id):
    from events import publish_task_completed

    with patch("routers.tasks.publish_task_completed", wraps=publish_task_completed) as spy:
        response = client.patch(
            f"/tasks/{task_id}",
            json={"completed": True},
        )

    assert response.status_code == 200
    spy.assert_called_once()

    args = spy.call_args.kwargs
    assert str(args["task_id"]) == task_id
    assert args["domain_id"] is not None


def test_uncompleting_a_task_does_not_publish(client, task_id):
    client.patch(f"/tasks/{task_id}", json={"completed": True})

    with patch("routers.tasks.publish_task_completed") as spy:
        response = client.patch(
            f"/tasks/{task_id}",
            json={"completed": False},
        )

    assert response.status_code == 200
    spy.assert_not_called()
