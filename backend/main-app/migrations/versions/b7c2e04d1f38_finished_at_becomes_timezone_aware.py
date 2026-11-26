"""study_sessions.finished_at becomes timezone-aware

The column was a naive `DateTime`, written with `datetime.now()` - the server's
wall clock, with no offset. Serialised as "2026-11-26T12:30:00", a browser in
another timezone read it as *its own* local time, so a session recorded seconds
ago displayed as "6h ago" for anyone east or west of the server.

timestamptz stores an absolute instant instead, so every reader agrees.

Existing rows are naive. They were written by `datetime.now()` on the server,
and this project has only ever run its services with a UTC clock (containers,
Railway, and the test host), so they are interpreted as UTC - which is what
`AT TIME ZONE 'UTC'` does here. Anything inserted after this migration is
written as an aware datetime and is unambiguous.

Revision ID: b7c2e04d1f38
Revises: a4e8f13d92c0
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2e04d1f38"
down_revision: Union[str, None] = "a4e8f13d92c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # USING is required: Postgres will not implicitly cast timestamp -> timestamptz
    # because the result depends on a session setting, so it refuses to guess.
    # 'AT TIME ZONE' states the assumption out loud instead of relying on it.

    # Every column that holds an instant, not just the one that showed the bug:
    # tasks.due_date and tasks.completed_at were naive too, so comparing them
    # against an aware "now" raised TypeError as soon as the clock became aware.
    for table, column in (
        ("study_sessions", "finished_at"),
        ("tasks", "due_date"),
        ("tasks", "completed_at"),
    ):
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column} TYPE timestamptz
            USING {column} AT TIME ZONE 'UTC'
            """
        )


def downgrade() -> None:
    # Back to naive columns, keeping the UTC wall clock. Lossy in the sense that
    # the offset is dropped, not that the instant moves.
    for table, column in (
        ("study_sessions", "finished_at"),
        ("tasks", "due_date"),
        ("tasks", "completed_at"),
    ):
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column} TYPE timestamp
            USING {column} AT TIME ZONE 'UTC'
            """
        )
