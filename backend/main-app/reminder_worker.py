"""Standalone reminder worker.

Runs the same scheduler the app starts in its lifespan, but without a web
server. Useful for hosts that run workers as a separate process, and for
`docker compose` where the API container should not also be the worker.
"""
import time

from reminders import start_scheduler


def main() -> None:
    start_scheduler()
    print("Reminder worker running.")

    # Block forever; the scheduler runs on its own thread.
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
