import json
from datetime import datetime
import uuid

import pika
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Base, ProcessedEvent
from settings import settings


EXCHANGE_NAME = "studystack.events"
QUEUE_NAME = "analytics.events"
ROUTING_KEYS = ["session.completed", "task.completed"]


# Handles one decoded event. Returns True when the event was applied and
# False when it had already been processed, which makes reruns harmless.
def handle_event(db: Session, message: dict) -> bool:
    raw_event_id = message.get("event_id")

    if not raw_event_id:
        # Without an ID the event cannot be deduplicated, so ignore it.
        return False

    try:
        event_id = uuid.UUID(raw_event_id)
    except (ValueError, TypeError):
        return False

    already_processed = db.scalar(
        select(ProcessedEvent).where(ProcessedEvent.event_id == event_id)
    )

    if already_processed is not None:
        return False

    db.add(
        ProcessedEvent(
            id=uuid.uuid4(),
            event_id=event_id,
            event_type=message.get("event", "unknown"),
            received_at=datetime.now(),
        )
    )

    db.commit()

    return True


# Called once when the consumer starts, so a fresh database has the
# analytics-owned tables.
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def on_message(channel, method, properties, body) -> None:
    db = SessionLocal()

    try:
        message = json.loads(body)
        handle_event(db, message)
        # Acknowledge only after the event is committed, so a crash
        # before this point causes a safe redelivery.
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception:
        db.rollback()
        # Requeue once instead of dropping the event on the floor.
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        db.close()


def main() -> None:
    connection = pika.BlockingConnection(
        pika.URLParameters(settings.rabbitmq_url)
    )
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type="topic",
        durable=True,
    )

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    for key in ROUTING_KEYS:
        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_NAME,
            routing_key=key,
        )

    # One unacknowledged event at a time keeps the consumer honest.
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=on_message,
    )

    print("Analytics consumer waiting for events...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
