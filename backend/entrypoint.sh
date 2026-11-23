#!/usr/bin/env bash
# Prepares the database this service owns, then starts the server.
# Runs inside the container before the app.
set -e

# Which service this container is (auth-service, main-app, analytics-service).
SERVICE="${SERVICE_NAME:-auth-service}"
SERVICE_DIR="/app/$SERVICE"

if [ ! -d "$SERVICE_DIR" ]; then
  echo "Unknown SERVICE_NAME '$SERVICE' (looked in $SERVICE_DIR)" >&2
  exit 1
fi

cd "$SERVICE_DIR"

# Render passes dockerCommand as ONE string, e.g.
#   "cd /app/auth-service && uvicorn main:app --port 8000"
# Docker Compose passes a list. Either way the command often still contains
# the service's own "cd /app/<service> &&", which is now redundant.
if [ "$#" -gt 0 ]; then
  COMMAND="$*"
  COMMAND=$(echo "$COMMAND" | sed -E 's#^cd /app/[^&]+&& *##')
else
  COMMAND=""
fi

# If nothing usable arrived, start the API server ourselves.
case "$COMMAND" in
  ""|cd*)
    COMMAND="uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
    ;;
esac

# Honour the platform's port even when the command hardcoded one.
if [ -n "${PORT:-}" ]; then
  COMMAND=$(echo "$COMMAND" | sed -E "s#--port [0-9]+#--port ${PORT}#")
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

echo "Starting in $PWD: $COMMAND"
exec sh -c "$COMMAND"
