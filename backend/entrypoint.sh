#!/usr/bin/env bash
# Creates the tables this service owns, then hands over to the real command.
# Runs inside the container before uvicorn starts.
set -e

# Several services start at the same time. Only the task service owns the
# shared schema (domains/tasks/subtasks/reminders/sessions), so the others
# set CREATE_TABLES_ON_START=false to avoid racing it.
if [ "${CREATE_TABLES_ON_START:-true}" = "true" ]; then
  python - <<'PY'
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)
print("Database tables are ready.")
PY
else
  echo "Skipping table creation for this service."
fi

exec "$@"
