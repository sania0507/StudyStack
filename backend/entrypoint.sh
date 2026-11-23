#!/usr/bin/env bash
# Prepares the database this service owns, then hands over to the real command.
# Runs inside the container before uvicorn starts.
set -e

# Three modes, chosen per service:
#   MIGRATE_ON_START=true   run alembic upgrade head (task service, production)
#   CREATE_TABLES_ON_START  create_all() for services that own simple tables
#   neither                 do nothing (analytics: init_tables.py handles it)
#
# Several services start at the same time, so exactly one of them is
# responsible for the shared schema to avoid racing.

if [ "${MIGRATE_ON_START:-false}" = "true" ]; then
  echo "Running database migrations..."

  # Render runs the image from /app, so move into the service folder where
  # alembic.ini lives. Docker Compose already sets this via working_dir.
  if [ -f "$PWD/alembic.ini" ]; then
    alembic upgrade head
  elif [ -f "$PWD/main-app/alembic.ini" ]; then
    (cd main-app && alembic upgrade head)
  else
    echo "No alembic.ini found; cannot migrate." >&2
    exit 1
  fi

  echo "Migrations complete."
elif [ "${CREATE_TABLES_ON_START:-true}" = "true" ]; then
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
