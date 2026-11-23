# StudyStack

A study and assignment tracker built as two FastAPI services plus a React
frontend. Domains hold tasks, tasks hold subtasks, deadlines drive overdue
logic and reminders, and a focus timer records study sessions that feed an
analytics dashboard.

---

## Architecture

```
                        ┌────────────────────┐
                        │    auth-service    │
                        │  signup / login    │
                        │  JWT issuing       │
                        │  profile editing   │
                        └─────────┬──────────┘
                                  │ JWT
                                  ↓
   ┌────────────────────────────────────────────────────┐
   │            task-service (main-app)                 │
   │                                                    │
   │  Domains → Tasks → Subtasks                        │
   │  Due dates → Overdue logic                         │
   │  Reminders + scheduled job (60s tick)              │
   │  Study sessions                                    │
   │  Analytics summary                                 │
   └───────────────────┬────────────────────────────────┘
                       │ events (optional)
                       ↓
              ┌──────────────────┐
              │     RabbitMQ     │
              │  event log only  │
              └──────────────────┘
```

| Service | Port | Owns |
|---|---|---|
| `auth-service` | 8000 | `users` |
| `task-service` (`main-app`) | 8001 | `domains`, `tasks`, `subtasks`, `reminders`, `study_sessions` |
| frontend | 3000 (dev) | React app, deployed to Vercel |

Both services share one PostgreSQL database but own **separate tables**, each
with its own Alembic migration history.

### Why analytics lives inside the task service

Analytics was originally a third service fed by RabbitMQ. It was merged back
for one reason: **every number it reports is derived from tables the task
service already owns.** `study_sessions`, `tasks` and `domains` are all there,
so a separate service bought no isolation — only another deployment, another
CORS origin, another JWT check, and a message broker that had to stay running.

The broker is still wired up for the event log, but nothing depends on it:
publishing fails gracefully, and the analytics figures are computed from the
database directly. That means **the whole app runs from two services**, which
matters on free hosting tiers that cap service count.

---

## Database relationships

```
users (auth-service)
  └── owns ──> domains.user_id
                 │
                 └──< tasks
                        │
                        ├──< subtasks
                        └──< reminders

domains
  └──< study_sessions   (also keyed by user_id)
```

`overdue` is **never stored**. It is derived from `due_date`, `completed` and
the current time, so it can never go stale or disagree with reality.

Deleting a domain cascades to its tasks, subtasks, reminders and sessions, so
no rows are ever orphaned.

---

## Why these choices

**Why two services rather than one?** Authentication has genuinely different
concerns from task data: it issues and verifies tokens, and it is the only
service that touches password hashes. Keeping it separate means the task
service never sees a password, and a token problem can be diagnosed without
touching user data.

**Why PostgreSQL?** The data is relational — a task must belong to a domain that
belongs to a user — and referential integrity is enforced by foreign keys rather
than application code. `ON DELETE CASCADE` handles cleanup for free.

**Why FastAPI?** Pydantic validates every request body at the boundary, so
endpoint code always receives well-typed data. It also produces OpenAPI docs at
`/docs` for free, which is how the endpoints below were verified.

**Why RabbitMQ, if nothing depends on it?** It records a durable event log:
`session.completed` and `task.completed` are published with a unique `event_id`,
so a consumer could be replayed without double-counting. It is deliberately
optional — the roadmap this project follows warns against adding a broker
without a reason, and the honest reason here is observability, not throughput.

---

## How reminders work

1. A reminder row has `remind_at` and a nullable `sent_at`.
2. A scheduler inside the task service ticks every 60 seconds (`reminders.py`,
   started from the FastAPI `lifespan`).
3. It selects reminders where `remind_at <= now` and `sent_at IS NULL`.
4. Completed tasks and deleted tasks are closed out without firing.
5. Each processed reminder gets `sent_at` set, so **a reminder can never be
   sent twice** — even across restarts.

`max_instances=1` stops a slow tick from overlapping the next one.

> On hosts that sleep idle services, the tick pauses with the service. Reminders
> then fire on the next wake rather than exactly on time.

---

## How analytics works

`GET /analytics/summary` computes, per user:

- **hours/week** — session minutes inside the current Monday–Sunday window
- **streak** — consecutive days with at least one session (a streak stays alive
  if the last session was yesterday)
- **overdue count** — incomplete tasks whose `due_date` has passed
- plus total minutes, sessions/day, weekday split, per-domain completion and a
  daily heatmap

All of it is derived at request time — nothing is precomputed, so the numbers
can never disagree with the underlying data.

---

## API overview

### auth-service (8000)
| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | 409 if the email exists; `name` optional |
| POST | `/auth/login` | returns a JWT |
| GET | `/auth/me` | requires `Authorization: Bearer <token>` |
| PATCH | `/auth/me` | update `name` and/or `email`; 409 if the email is taken |
| POST | `/auth/change-password` | 204 on success, 401 if the current password is wrong |

### task-service (8001)
All routes require a Bearer token and are scoped to the caller's own data.

| Method | Path |
|---|---|
| POST / GET | `/domains` |
| PATCH / DELETE | `/domains/{domain_id}` |
| POST / GET | `/tasks` (filters: `completed`, `overdue`, `domain_id`) |
| PATCH / DELETE | `/tasks/{task_id}` |
| POST / GET | `/subtasks` |
| PATCH / DELETE | `/subtasks/{subtask_id}` |
| POST / GET | `/reminders` (filters: `task_id`, `sent`) |
| PATCH / DELETE | `/reminders/{reminder_id}` |
| POST / GET | `/sessions` (filter: `domain_id`) |
| GET | `/analytics/summary` (`?heatmap_days=30`) |
| GET | `/health` |

`TaskOut` includes `next_reminder_at`, the soonest reminder still pending, so
the UI can show a bell without a second request.

---

## Running locally

```bash
docker compose up --build
```

Then open <http://localhost:3000>. The RabbitMQ management UI is at
<http://localhost:15672> (guest / guest).

Without Docker, run each piece in its own shell (each service needs its own
`.env` — copy the matching `.env.example`):

```bash
cd backend/auth-service && uvicorn main:app --port 8000
cd backend/main-app     && uvicorn main:app --port 8001
cd frontend             && npm run dev
```

---

## Tests

Each service has its own dedicated test database, and the test fixtures refuse
to run against any other database name.

```bash
cd backend/main-app
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_main_test \
  pytest

cd backend/auth-service
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_auth_test \
  pytest
```

Create the databases once:

```bash
sudo -u postgres psql -c "CREATE DATABASE studystack_main_test OWNER studystack_user;"
sudo -u postgres psql -c "CREATE DATABASE studystack_auth_test OWNER studystack_user;"
```

---

## Migrations

`create_all()` is not the source of truth. Each service owns its own Alembic
migrations and its own version table, because both share one database:

| Service | Revision table | Owns |
|---|---|---|
| `task-service` | `alembic_version_tasks` | domains, tasks, subtasks, reminders, study_sessions |
| `auth-service` | `alembic_version_auth` | users |

Migrations run automatically at container start when `MIGRATE_ON_START=true`,
so a first deploy against an empty database needs no manual step. To run them by
hand:

```bash
cd backend/main-app     && alembic upgrade head
cd backend/auth-service && alembic upgrade head
```

Two services writing to a single `alembic_version` table would corrupt each
other's revision chain — that is why the tables are separate.

---

## Deployment

Both services build from **one shared image**. The container picks its folder
from `SERVICE_NAME`, so the two deployments differ only by environment.

| Variable | auth | tasks | Notes |
|---|---|---|---|
| `SERVICE_NAME` | `auth-service` | `main-app` | selects the service folder |
| `DATABASE_URL` | ✅ | ✅ | must include `+psycopg` |
| `JWT_SECRET_KEY` | ✅ | ✅ | **must be identical on both** |
| `CORS_ORIGINS` | ✅ | ✅ | comma-separated, no trailing slash |
| `MIGRATE_ON_START` | `true` | `true` | runs `alembic upgrade head` |
| `RABBITMQ_URL` | — | optional | event publishing only |
| `PORT` | platform-set | platform-set | the entrypoint honours it |

The image exposes both an `ENTRYPOINT` and a `CMD`, so it starts correctly
whether the host supplies a command, a command string, or nothing at all.

Frontend (Vercel): set **Root Directory** to `frontend`, then supply
`VITE_AUTH_URL` and `VITE_MAIN_URL`. Analytics shares the task-service URL, so
no third variable is needed.

---

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | both services | PostgreSQL connection string |
| `JWT_SECRET_KEY` | both services | signs and verifies tokens |
| `RABBITMQ_URL` | task service (optional) | event broker |
| `CORS_ORIGINS` | both services | comma-separated allowed origins |
| `SERVICE_NAME` | container | which service folder to run |
| `MIGRATE_ON_START` | container | run migrations before starting |
| `PORT` | container | port to bind |
| `VITE_AUTH_URL` | frontend | auth-service base URL |
| `VITE_MAIN_URL` | frontend | task-service base URL |

Never commit `.env` files. Copy the `.env.example` in each service folder.
