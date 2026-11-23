#!/usr/bin/env bash
# Prepares the database this service owns, then starts the server.
# Runs inside the container before the app.
set -e

# Which service this container is. Set by the blueprint/compose; defaults to
# the auth service so a bare `docker run` still does something sensible.
SERVICE="${SERVICE_NAME:-auth-service}"

SERVICE_DIR="/app/$SERVICE"

if [ ! -d "$SERVICE_DIR" ]; then
  echo "Unknown SERVICE_NAME '$SERVICE' (looked in $SERVICE_DIR)" >&2
  exit 1
fi

cd "$SERVICE_DIR"

# Render passes dockerCommand as ONE string such as
#   "cd /app/auth-service && uvicorn main:app --port 8000"
# Compose passes a list. If a command is supplied, honour it; otherwise fall
# back to the image CMD, and if that is empty, start the service directly.
if [ "$#" -gt 0 ]; then
  COMMAND="$*"
  # Strip a redundant leading "cd /app/<service> &&" so we do not cd twice.
  COMMAND=$(echo "$COMMAND" | sed -E 's#^cd /app/[^&]+&& *##')
else
  COMMAND=""
fi

# Three DB modes:
#   MIGRATE_ON_START=true   run alembic upgrade head
#   CREATE_TABLES_ON_START  create_all() for services with simple tables
#   neither                 do nothing
if [ "${MIGRATE_ON_START:-false}" = "true" ]; then
  echo "Running database migrations in $PWD ..."
  alembic upgrade head
  echo "Migrations complete."
elif [ "${CREATE_TABLES_ON_START:-true}" = "true" ]; then
  echo "Creating tables in $PWD ..."
  python - <<'PY'
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)
print("Database tables are ready.")
PY
else
  echo "Skipping table creation for this service."
fi

# Never rely on CMD being present: Render may or may not pass one.
if [ -z "$COMMAND" ]; then
  COMMAND="uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
fi

echo "Starting in $PWD: $COMMAND"
exec sh -c "$COMMAND"
