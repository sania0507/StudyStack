# StudyStack

Most study apps assume a routine you don't have. They want a weekly schedule, a fixed block for each subject, a plan made on Sunday that you follow on Tuesday. If you work in bursts instead — three hours tonight on one thing, nothing for four days, then panic — those apps ask you to be someone else before they'll help you.

StudyStack tracks the work without demanding the schedule. You add what's due, break it into pieces, set deadlines that actually count down, and start a timer when the energy hits. It counts what you did, not what you planned to do.

I built it because that's how I study.

Two FastAPI services, one React frontend, one PostgreSQL database.

---

## The Problem It Solves

An erratic routine has two failure modes: deadlines you forgot, and no record of the effort you did put in. Both make it easy to conclude you're not doing enough when you are.

StudyStack addresses each directly:

- **Deadlines don't depend on discipline.** A due date is stored, and overdue is computed from it. Nothing needs you to check in for the system to know you're late.
- **Effort is recorded where you work.** The timer writes a session against a domain when it finishes. There is no separate journal to keep up.
- **Streaks reward consistency without requiring it.** A streak survives a day with no session, so one slow day doesn't wipe out three good ones.

The design assumption is that you'll show up unpredictably. Bursts are expected, not treated as failure.

---

## What Is Included

- Accounts with JWT authentication; every request is scoped to the caller's own data.
- Login, registration, profile editing (name and email) and password change.
- Domain CRUD.
- Task CRUD with optional due dates and completion tracking.
- Subtask CRUD.
- Overdue logic derived on read, never stored.
- Reminders with a scheduled job that fires each one exactly once.
- A focus timer that records study sessions against a domain.
- Analytics: hours per week, streak, overdue count, weekday split, per-domain completion, daily heatmap.
- Docker Compose for local development.
- Alembic migrations for both services.

---

## Architecture

```
                    ┌────────────────────┐
                    │    auth-service    │
                    │  register / login  │
                    │  JWT issuing       │
                    │  profile editing   │
                    └─────────┬──────────┘
                              │ JWT
                              ↓
        ┌─────────────────────────────────────────┐
        │        task-service (main-app)          │
        │                                         │
        │  Domains → Tasks → Subtasks             │
        │  Due dates → Overdue logic              │
        │  Reminders + scheduled job (60s tick)   │
        │  Study sessions                         │
        │  Analytics summary                      │
        └────────────────┬────────────────────────┘
                         │
                         ↓
                  ┌──────────────┐
                  │  PostgreSQL  │
                  │  (one DB,    │
                  │  split       │
                  │  ownership)  │
                  └──────────────┘
```

| Service | Port | Owns |
|---|---|---|
| `auth-service` | 8000 | `users` |
| `task-service` (`main-app`) | 8001 | `domains`, `tasks`, `subtasks`, `reminders`, `study_sessions` |
| frontend | 3000 (dev) | React app, hosted on Vercel |

Both services share one database but own separate tables. Each has its own Alembic revision table (`alembic_version_auth`, `alembic_version_tasks`) because two services writing to one `alembic_version` corrupt each other's revision chain.

---

## From Three Services To Two

The original plan had three services: auth, tasks/deadlines, and analytics, with analytics fed by a RabbitMQ event stream. All three were built and ran locally.

Railway's free tier allows two services per project. Keeping analytics separate would have meant paying for a personal study tracker to keep a deployment boundary that was not doing any work.

Analytics reads `study_sessions`, `tasks` and `domains` and writes nothing. It shared the task service's data completely, so the split gave no isolation and no independent scaling. It is now a router (`/analytics/summary`) in the task service, computing everything from the database on each request.

Analytics queries now share a process with task writes. For a single-user tracker that is not a bottleneck, and it removed a deployment, a CORS origin, a JWT check and a broker requirement.

---

## RabbitMQ Status

`backend/main-app/events.py` still publishes `session.completed` and `task.completed` to a durable topic exchange, each with a unique `event_id`. It returns `False` if the broker is unreachable rather than raising, so a broker outage cannot break a request.

There is no consumer. The consumer belonged to the three-service design and was removed when analytics moved in-process, so nothing currently reads these events. Analytics numbers come from the database and are correct with RabbitMQ absent entirely.

`RABBITMQ_URL` is therefore optional. Omit it and the app runs normally.

Removing the publisher outright would mean deleting `events.py`, two router calls, the `pika` dependency and four tests. It is left in place as a durable event log that a consumer could pick up without changing any endpoint.

---

## Database Relationships

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

`overdue` is never stored. It is computed from `due_date`, `completed` and the current time on every read.

Deleting a domain cascades to its tasks, and from there to subtasks and reminders; sessions cascade directly from the domain. No rows are left orphaned.

---

## API Overview

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

`TaskOut` includes `next_reminder_at`, the soonest pending reminder, so the UI shows a reminder badge without a second request.

---

## Reminders

1. A reminder row has `remind_at` and a nullable `sent_at`.
2. A scheduler inside the task service ticks every 60 seconds, started from the FastAPI `lifespan`.
3. It selects reminders where `remind_at <= now` and `sent_at IS NULL`.
4. Completed and deleted tasks are closed out without firing.
5. Each processed reminder gets `sent_at` set, so one is never sent twice, including across restarts.

`max_instances=1` prevents a slow tick overlapping the next.

On hosts that sleep idle services the tick pauses with the service, so reminders fire on the next wake rather than exactly on time.

---

## Analytics

`GET /analytics/summary` returns, per user:

- hours/week: session minutes inside the current Monday-Sunday window
- streak: consecutive days with at least one session, still alive if the last session was yesterday
- overdue count: incomplete tasks whose `due_date` has passed
- total minutes, sessions per day, weekday split, per-domain completion and a daily heatmap

Everything is computed on request, so the numbers always match the underlying rows.

---

## Local Setup

```bash
docker compose up --build
```

Open http://localhost:3000.

Without Docker, run each piece in its own shell. Each service needs its own `.env`; copy the matching `.env.example`:

```bash
cd backend/auth-service && uvicorn main:app --port 8000
cd backend/main-app     && uvicorn main:app --port 8001
cd frontend             && npm install && npm run dev
```

The frontend reads `VITE_AUTH_URL` and `VITE_MAIN_URL`, defaulting to `http://localhost:8000` and `http://localhost:8001`. Analytics uses the task-service URL, so there is no third variable.

---

## Tests

Each service has its own test database and the fixtures refuse to run against any other name.

```bash
cd backend/main-app
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_main_test pytest

cd backend/auth-service
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_auth_test pytest
```

60 tests: 44 in the task service, 16 in auth.

Covered: registration and duplicate email, login and wrong password, profile updates, password change, CRUD for every resource, cross-user isolation, completion timestamps, overdue derivation across all four due-date cases, reminder idempotency, domain cascade to tasks and nested children, analytics windowing and scoping, and event publishing degrading when the broker is unreachable.

Create the test databases once:

```bash
sudo -u postgres psql -c "CREATE DATABASE studystack_main_test OWNER studystack_user;"
sudo -u postgres psql -c "CREATE DATABASE studystack_auth_test OWNER studystack_user;"
```

---

## Migrations

Alembic owns the schema.

| Service | Revision table | Owns |
|---|---|---|
| `task-service` | `alembic_version_tasks` | domains, tasks, subtasks, reminders, study_sessions |
| `auth-service` | `alembic_version_auth` | users |

Migrations run at container start when `MIGRATE_ON_START=true`, so a first deploy against an empty database needs no manual step. To run by hand:

```bash
cd backend/main-app     && alembic upgrade head
cd backend/auth-service && alembic upgrade head
```

---

## Deployment

- React + Vite frontend on Vercel, with Root Directory set to `frontend`.
- Two FastAPI services on Railway, built from one shared Dockerfile.
- PostgreSQL on Neon, passed in as `DATABASE_URL` and using the `+psycopg` driver.

Both services build from the same image and pick their folder from `SERVICE_NAME`.

| Variable | auth | tasks | Notes |
|---|---|---|---|
| `SERVICE_NAME` | `auth-service` | `main-app` | selects the service folder |
| `DATABASE_URL` | required | required | must include `+psycopg` |
| `JWT_SECRET_KEY` | required | required | must be identical on both |
| `CORS_ORIGINS` | required | required | comma-separated, no trailing slash |
| `MIGRATE_ON_START` | `true` | `true` | runs `alembic upgrade head` |
| `RABBITMQ_URL` | not used | optional | publishing only, no consumer |
| `PORT` | platform-set | platform-set | honoured by the entrypoint |

`JWT_SECRET_KEY` must match across both. If they differ, login succeeds but every later request returns 401, because auth signs tokens the task service cannot verify.

The image defines both an `ENTRYPOINT` and a `CMD`, so it starts whether the host passes a command string or nothing.

---

## Notes

- Deleting a domain removes its tasks, subtasks, reminders and sessions.
- Reminder delivery is a line in the server log. Swapping in email or push does not change the bookkeeping.
- The analytics week runs Monday to Sunday in server-local time.
- Dashboard deletes are optimistic: the row disappears immediately and returns with an inline error banner if the server rejects it.
- Passwords are hashed with Argon2 through `pwdlib` and hashes are never returned by any endpoint.
- Access tokens expire after 30 minutes with no refresh token, so long sessions require re-login.
