# StudyStack

A microservice-based study and assignment tracker. Domains hold tasks, tasks
hold subtasks, deadlines drive overdue logic and reminders, and a focus timer
records study sessions that feed an analytics service.

---

## Architecture

```
                        ┌────────────────────┐
                        │    auth-service    │
                        │  signup / login    │
                        │  JWT issuing       │
                        └─────────┬──────────┘
                                  │ JWT
                                  ↓
   ┌──────────────────────────────────────────────┐
   │              task-service (main-app)         │
   │                                              │
   │  Domains → Tasks → Subtasks                  │
   │  Due dates → Overdue logic                   │
   │  Reminders + scheduled worker                │
   │  Study sessions                              │
   └───────────────┬──────────────────────────────┘
                   │ events (RabbitMQ)
                   ↓
        ┌────────────────────────────┐
        │     analytics-service      │
        │  hours/week                │
        │  streaks                   │
        │  overdue count             │
        │  heatmap / weekday split   │
        └────────────────────────────┘
```

| Service | Port | Owns |
|---|---|---|
| `auth-service` | 8000 | `users` |
| `task-service` (`main-app`) | 8001 | `domains`, `tasks`, `subtasks`, `reminders`, `study_sessions` |
| `analytics-service` | 8002 | `processed_events` (read-mostly over the tables above) |
| `reminder-worker` | — | runs the scheduled reminder job |
| `analytics-consumer` | — | consumes RabbitMQ events |
| frontend | 3000 | React app |

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

---

## Why these choices

**Why microservices?** The three services have genuinely different jobs: auth
issues and verifies tokens, the task service owns all mutable user data, and
analytics is read-heavy. Splitting them means the analytics queries can never
lock a user's task writes, and each can scale or be redeployed on its own.

**Why PostgreSQL?** The data is relational — a task must belong to a domain
that belongs to a user — and referential integrity is enforced by foreign keys
rather than application code. `ON DELETE CASCADE` on subtasks, reminders and
sessions means deleting a domain never orphans rows.

**Why FastAPI?** Pydantic validates every request body at the boundary, so
endpoint code always receives well-typed data. It also produces OpenAPI docs at
`/docs` for free, which is how the endpoints below were verified.

**Why RabbitMQ?** Not for throughput — StudyStack's write volume is tiny. It is
for **decoupling and durability**: creating a session never blocks on the
analytics service, and if the consumer is down, events queue up instead of being
lost. The trade-off is accepted deliberately; the PDF roadmap warns against
adding a broker without a reason, and this is the reason.

---

## How reminders work

1. A reminder row has `remind_at` and a nullable `sent_at`.
2. The scheduled worker ticks every 60 seconds (`reminders.py`).
3. It selects reminders where `remind_at <= now` and `sent_at IS NULL`.
4. Completed tasks and deleted tasks are closed out without firing.
5. Each processed reminder gets `sent_at` set, so **a reminder can never be
   sent twice** — even across worker restarts.

`max_instances=1` stops a slow tick from overlapping the next one.

---

## How analytics works

The analytics service computes, per user:

- **hours/week** — session minutes inside the current Monday–Sunday window
- **streak** — consecutive days with at least one session (a streak stays
  alive if the last session was yesterday)
- **overdue count** — incomplete tasks whose `due_date` has passed
- plus total minutes, sessions/day, weekday split, per-domain completion and a
  daily heatmap

Events arrive over RabbitMQ and are recorded in `processed_events`. Because
brokers deliver **at least once**, the table has a unique constraint on
`event_id`, so a redelivered message is ignored rather than double-counted.

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
| GET | `/health` |

### analytics-service (8002)
| Method | Path |
|---|---|
| GET | `/analytics/summary` (`?heatmap_days=30`) |
| GET | `/health` |

---

## Running locally

```bash
docker compose up --build
```

Then open <http://localhost:3000>. The RabbitMQ management UI is at
<http://localhost:15672> (guest / guest).

Without Docker, run each service in its own shell:

```bash
cd backend/main-app      && uvicorn main:app --port 8001
cd backend/auth-service  && uvicorn main:app --port 8000
cd backend/analytics-service && uvicorn main:app --port 8002
cd frontend              && npm run dev
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

cd backend/analytics-service
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_analytics_test \
  pytest
```

The analytics test database must be owned by `studystack_user`:

```bash
sudo -u postgres psql -d studystack_analytics_test \
  -c "ALTER DATABASE studystack_analytics_test OWNER TO studystack_user;"
```

---

## Migrations

`create_all()` is no longer the source of truth. Each service owns its own
Alembic migrations and its own version table, because both share one database:

| Service | Revision table | Owns |
|---|---|---|
| `task-service` | `alembic_version_tasks` | domains, tasks, subtasks, reminders, study_sessions |
| `auth-service` | `alembic_version_auth` | users |

Migrations run automatically at container start (`MIGRATE_ON_START=true` in
`docker-compose.yml` and `render.yaml`), so a first deploy against an empty
database is prepared without a manual step. To run them by hand:

```bash
cd backend/main-app     && alembic upgrade head
cd backend/auth-service && alembic upgrade head
```

Two services writing to a single `alembic_version` table would corrupt each
other's revision chain — that is why the tables are separate.

---

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | all services | PostgreSQL connection string |
| `JWT_SECRET_KEY` | all services | signs and verifies tokens |
| `RABBITMQ_URL` | task + analytics | event broker |
| `CORS_ORIGINS` | all services | comma-separated allowed origins |
| `VITE_AUTH_URL` | frontend | auth-service base URL |
| `VITE_MAIN_URL` | frontend | task-service base URL |
| `VITE_ANALYTICS_URL` | frontend | analytics-service base URL |

Never commit `.env` files. See each service folder for the keys it needs.
