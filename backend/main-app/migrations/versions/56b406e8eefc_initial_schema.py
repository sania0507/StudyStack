"""initial schema

Creates the tables owned by the task service: domains, tasks, subtasks,
reminders and study_sessions.

The users table belongs to auth-service, so it is deliberately not
included here. Both services share one database, but each owns its own
tables.

Revision ID: 56b406e8eefc
Revises:
Create Date: 2026-11-23 12:13:51.082472
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '56b406e8eefc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'domains',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('colour', sa.String(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_domains_user_id'), 'domains', ['user_id'], unique=False)

    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('domain_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'subtasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'reminders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('remind_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_reminders_remind_at'), 'reminders', ['remind_at'], unique=False)
    op.create_index(op.f('ix_reminders_task_id'), 'reminders', ['task_id'], unique=False)

    op.create_table(
        'study_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('domain_id', sa.Uuid(), nullable=False),
        sa.Column('minutes', sa.Integer(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_study_sessions_domain_id'), 'study_sessions', ['domain_id'], unique=False)
    op.create_index(op.f('ix_study_sessions_finished_at'), 'study_sessions', ['finished_at'], unique=False)
    op.create_index(op.f('ix_study_sessions_user_id'), 'study_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_study_sessions_user_id'), table_name='study_sessions')
    op.drop_index(op.f('ix_study_sessions_finished_at'), table_name='study_sessions')
    op.drop_index(op.f('ix_study_sessions_domain_id'), table_name='study_sessions')
    op.drop_table('study_sessions')

    op.drop_index(op.f('ix_reminders_task_id'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_remind_at'), table_name='reminders')
    op.drop_table('reminders')

    op.drop_table('subtasks')
    op.drop_table('tasks')
    op.drop_index(op.f('ix_domains_user_id'), table_name='domains')
    op.drop_table('domains')
