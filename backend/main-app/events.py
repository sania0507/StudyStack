import json
from datetime import datetime
import uuid

import pika

from settings import settings


EXCHANGE_NAME = "studystack.events"


# Publishes one event to RabbitMQ.
# Returns True when the broker accepted it and False when it did not, so a
# broker outage never breaks the HTTP request that triggered the event.
def publish_event(event_type: str, payload: dict) -> bool:
    message = {
        # A stable ID lets the consumer discard duplicate deliveries.
        "event_id": str(uuid.uuid4()),
        "event": event_type,
        "payload": payload,
        "occurred_at": datetime.now().isoformat(),
    }

    try:
        connection = pika.BlockingConnection(
            pika.URLParameters(settings.rabbitmq_url)
        )
        channel = connection.channel()

        # Declaring both sides keeps the exchange alive even if the
        # analytics consumer has not started yet.
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=event_type,
            body=json.dumps(message).encode(),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persist the message across broker restarts
                content_type="application/json",
            ),
        )

        connection.close()
        return True

    except Exception:
        # Analytics is a read-only concern. If it cannot be reached, the
        # user's own request must still succeed.
        return False


def publish_session_completed(
    user_id: uuid.UUID,
    domain_id: uuid.UUID,
    minutes: int,
) -> bool:
    return publish_event(
        "session.completed",
        {
            "user_id": str(user_id),
            "domain_id": str(domain_id),
            "minutes": minutes,
        },
    )


def publish_task_completed(
    user_id: uuid.UUID,
    task_id: uuid.UUID,
    domain_id: uuid.UUID,
) -> bool:
    return publish_event(
        "task.completed",
        {
            "user_id": str(user_id),
            "task_id": str(task_id),
            "domain_id": str(domain_id),
        },
    )
