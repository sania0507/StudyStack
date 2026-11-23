#!/usr/bin/env bash
# Prepares the database this service owns, then hands over to the real command.
# Runs inside the container before the server starts.
set -e

if [ "$#" -eq 0 ]; then
  echo "No command supplied." >&2
  exit 1
fi

# Render passes dockerCommand as ONE string, e.g.
#   "cd /app/auth-service && uvicorn main:app --port 8000"
# Docker Compose passes a list, e.g. ["uvicorn", "main:app"].
COMMAND="$*"

# Work out which folder this service should run from. Compose sets it via
# working_dir, so $PWD is already correct and the "cd" is skipped. On Render
# the only hint is the leading "cd /app/<service> &&" in the command, which
# also has to happen BEFORE migrations run.
case "$COMMAND" in
  "cd "*"&&"*)
    SERVICE_DIR=$(echo "$COMMAND" | sed -E 's/^cd ([^&]+)&&.*/\1/' | tr -d ' ')
    if [ -d "$SERVICE_DIR" ]; then
      cd "$SERVICE_DIR"
    fi
    ;;
esac

# Three modes, chosen per service:
#   MIGRATE_ON_START=true   run alembic upgrade head
#   CREATE_TABLES_ON_START  create_all() for services with simple tables
#   neither                 do nothing (analytics: init_tables.py handles it)
#
# Exactly one service owns the shared schema, so nothing races.
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

# Run the command through a shell: a bare exec of the compound string would
# fail with status 128 because the whole string is one argument.
echo "Starting: $COMMAND"
exec sh -c "$COMMAND"
