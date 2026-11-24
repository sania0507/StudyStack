# StudyStack

Most study apps assume a routine you don't have. They want a weekly schedule, a fixed block for each subject, a plan made on Sunday that you follow on Tuesday. If you work in bursts instead — three hours tonight on one thing, nothing for four days, then panic — those apps ask you to be someone else before they'll help you.

StudyStack tracks the work without demanding the schedule. You add what's due, break it into pieces, set deadlines that actually count down, and start a timer when the energy hits. It counts what you did, not what you planned to do.

I built it because that's how I study.

Two FastAPI services, one React frontend, one PostgreSQL database.

---

## Screenshots

<!-- Screenshots live on GitHub user-attachment URLs. To replace one, drag a
     new file into the GitHub markdown editor and copy the URL it produces —
     it looks like https://github.com/user-attachments/assets/<id> — then swap
     that id below. Keep the ![alt](url) shape: pasting the editor's HTML
     snippet into the ( ) slot is what broke these before. -->

<table>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/ae260e3d-a5f2-4327-afcb-977145852177" alt="Dashboard, with domains, tasks and the focus timer" />
      <br /><sub><b>Dashboard</b> — domains, tasks and the focus timer</sub>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/6d86da99-85a2-4ae1-ac16-21f419a5d2a2" alt="Dashboard, with the timer running" />
      <br /><sub><b>Dashboard</b> — a block in progress</sub>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/1750454f-763b-41df-846f-9e911af21d78" alt="Analytics, with the weekly bars and the activity heatmap" />
      <br /><sub><b>Analytics</b> — weekly split and the year heatmap</sub>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/aa553380-f79e-4e39-a103-6901bccb715d" alt="Analytics, with the activity feed" />
      <br /><sub><b>Analytics</b> — the recorded-session feed</sub>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/e2560c2a-8516-4087-ac39-8eda8bbf34b5" alt="Vision board, with draggable resized images" />
      <br /><sub><b>Vision board</b> — images you drag and resize</sub>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/dcdf1f66-482a-48d7-9bfb-2ff66746c5db" alt="Notes, with folders and the date timeline" />
      <br /><sub><b>Notes</b> — folders and a dated timeline</sub>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/a6f8cafc-b703-4900-816f-6451201641c4" alt="The landing page" />
      <br /><sub><b>Landing</b></sub>
    </td>
    <td width="50%">
      <img src="https://github.com/user-attachments/assets/944520c6-8a58-4aa5-83bf-30e07caa9756" alt="Profile, with the stored avatar" />
      <br /><sub><b>Profile</b> — the stored avatar</sub>
    </td>
  </tr>
</table>

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

- Accounts with short-lived access tokens and rotating refresh tokens; every
  request is scoped to the caller's own data.
- Login, registration, profile editing (name and email) and password change.
  Changing a password ends every other session.
- Domain CRUD.
- Task CRUD with optional due dates and completion tracking.
- Subtask CRUD.
- Overdue logic derived on read, never stored.
- Reminders with a scheduled job that claims each one before it fires, so it is
  never processed twice by the same process.
- A focus timer that records study sessions against a domain.
- Analytics: hours per week, streak, overdue count, weekday split, per-domain completion, daily heatmap.
- Recurring domains: mark a routine and its tasks untick themselves every morning, with the history kept.
- A vision board: images you upload or paste in, then drag and resize freely.
- Notes: folders, a date timeline, drag-to-reorder, pinning, search and markdown.
- Profile pictures stored in Postgres and served behind the owner's token.
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

## Events

There is no message broker. Events were part of the three-service design: the
task service published `session.completed` and `task.completed` to a RabbitMQ
topic exchange for an analytics consumer that no longer exists.

The publisher was removed once it was clear nothing would read from it. Every
analytics number is computed from the database on request, so the events were
write-only overhead: a broker connection opened and closed inside each request,
for messages that were discarded because no queue was ever bound to the
exchange.

If a real consumer appears later, the right starting point is the
transactional outbox pattern rather than a direct publish inside the request
path, so an event cannot be lost between the commit and the broker.

## Database Relationships

```
users (auth-service)
  ├──< refresh_tokens   (one row per issued token, hashed)
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

## Authentication

Login issues two tokens. The access token is a 30-minute HS256 JWT and is
verified by signature alone, so neither service touches the database to
authenticate a request. The refresh token is 30 days, opaque, and stored hashed
in `refresh_tokens` in the auth service.

A refresh token is a bearer credential, so the table keeps only its SHA-256
hash and never the token itself. SHA-256 is deliberate here and Argon2 would be
wrong: the token is 48 random bytes, so there is nothing to brute force, and
every refresh needs a fast lookup.

Rotation works like this:

1. Look up `sha256(token)`. Unknown is a 401.
2. Already revoked means the token was presented twice. Either the client or an
   attacker holds it, and one row cannot say which, so the **whole family** is
   revoked and both parties are forced to log in again.
3. Otherwise claim it with a single conditional update,
   `UPDATE ... WHERE id = ? AND revoked_at IS NULL`. If zero rows are affected,
   another request rotated it first: same reuse treatment.
4. Issue a new pair in the same family.

`family_id` groups every token descended from one login, which is what makes
step 2 possible. `replaced_by_id` records which token superseded which, so the
chain is auditable.

Step 3 is the part that has to be atomic. Reading the row and then revoking it
would let two concurrent refreshes both pass the check and both issue tokens,
silently breaking rotation. It is the same claim-before-work pattern the
reminder worker needs.

Expired rows are pruned whenever a new token is issued, keeping the table from
growing without bound.

On the client, `frontend/src/api/client.ts` refreshes once on a 401 and retries
the request exactly once. Refresh is single-flight: five requests failing at
the same moment produce one refresh, not five, because five would rotate the
same token four times too many and trip the reuse detector.

---

## Routines

A morning routine is the same five things every day, so a plain task list is
the wrong shape for it: tick them once and they stay ticked forever.

A domain can be marked `repeats_daily`. Its tasks keep the ordinary `completed`
flag, but a task completed before today is unticked on the next read.

<img src="https://github.com/user-attachments/assets/6d86da99-85a2-4ae1-ac16-21f419a5d2a2" alt="A dashboard with a daily routine domain" width="760" />

The reset runs on `GET /tasks`, which makes it idempotent and removes the need
for a scheduler: opening the app on a new day is enough. Clearing the tick
would erase the evidence of the work, so every completion also writes a row to
`task_completions`, unique per (task, day). The heatmap reads both sources and
takes the larger per day, so a task still ticked today is never counted twice.

---

## Vision board

A wall of images you drag around, because the reason to do the work is easier
to remember as a picture than as a task list.

<img src="https://github.com/user-attachments/assets/e2560c2a-8516-4087-ac39-8eda8bbf34b5" alt="The vision board" width="760" />

Images are stored as bytes, not as links. The obvious build is "paste a
Pinterest URL and render it", but Pinterest image URLs expire, so that board
would quietly develop holes. A pasted link is fetched once on save and the
bytes are kept, which also means uploads and links share one storage path.

Positions and widths are percentages of the board rather than pixels, and the
board is a fixed height on purpose: "40% from the top" then means the same
thing on a laptop and a phone. Height is automatic, so a tall pin is tall
rather than cropped to a square.

Dragging uses pointer events with `setPointerCapture`, so an image keeps
following the cursor even when the cursor outruns it, and `touch-action: none`
so a trackpad moves the image rather than the page. One PATCH is sent on
release, not one per `pointermove`.

---

## Notes

A place for the writing that does not belong to a deadline: DSA notes, dev
notes, a diary.

<img src="https://github.com/user-attachments/assets/dcdf1f66-482a-48d7-9bfb-2ff66746c5db" alt="The notes page" width="760" />

Folders are modelled like `domains` but kept separate on purpose — deleting a
study domain should not take a diary entry with it.

Two decisions that shape the page:

- `created_at` anchors the timeline and `updated_at` is only an "edited" stamp.
  Editing an old note must not push it to the top of the list.
- Drag-to-reorder sets a `position` and **never touches `created_at`**: the
  date beside a note says when it was written, and moving it is not editing.

Pinned notes break the ordering deliberately and sort above it. Search is
case-insensitive across title and body, and combines with the folder filter, so
"search inside this folder" needs no second endpoint.

Markdown is rendered by a small function that escapes HTML first and then
applies headings, lists, bold, italic and inline code. No dependency, and a
note can never inject markup.

---

## API Overview

### auth-service (8000)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | 409 if the email exists; `name` optional |
| POST | `/auth/login` | returns an access token, a refresh token and `token_type` |
| POST | `/auth/refresh` | exchanges a refresh token for a new pair; 401 if unknown, expired, revoked or already rotated |
| POST | `/auth/logout` | 204; revokes the presented refresh token. Idempotent and unauthenticated, so an expired client can still end its session |
| GET | `/auth/me` | requires `Authorization: Bearer <token>` |
| PATCH | `/auth/me` | update `name` and/or `email`; 409 if the email is taken |
| POST | `/auth/change-password` | 204 on success, 401 if the current password is wrong. Revokes every refresh token for the user |
| POST | `/auth/me/avatar` | multipart upload, PNG/JPEG/WebP, 512 KB cap |
| GET | `/auth/me/avatar` | the image bytes, behind the bearer token |
| DELETE | `/auth/me/avatar` | clears it |

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
| POST / GET | `/vision-items` (GET returns positions and widths; POST takes `image_url`) |
| POST | `/vision-items/upload` (multipart, 2 MB cap) |
| GET | `/vision-items/{item_id}/image` |
| PATCH / DELETE | `/vision-items/{item_id}` (`x`, `y`, `width`, `caption`) |
| POST / GET | `/note-folders` |
| PATCH / DELETE | `/note-folders/{folder_id}` |
| POST / GET | `/notes` (filters: `folder_id`, `search`) |
| POST | `/notes/reorder` (a whole list, in its new order) |
| PATCH / DELETE | `/notes/{note_id}` (`folder_id` moves it between folders) |
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

83 tests in the task service, 33 in auth.

Covered: registration and duplicate email, login and wrong password, profile
updates, password change, refresh rotation and reuse detection revoking the
family, refresh-token expiry, logout idempotency, CRUD for every resource,
cross-user isolation on read, update and delete, completion timestamps, overdue
derivation across all four due-date cases, clearing a due date, reminder
idempotency, domain cascade to tasks and nested children, and analytics
windowing and scoping.

Running the suites inside the compose network avoids Docker Desktop's WSL port
forwarding, which is unreliable for PostgreSQL connections:

```bash
DB=postgresql+psycopg://studystack_user:studystack_dev_password@postgres:5432

docker compose run --rm -e SERVICE_NAME=auth-service   -e TEST_DATABASE_URL=$DB/studystack_auth_test   task-service python -m pytest -q

docker compose run --rm -e SERVICE_NAME=main-app   -e TEST_DATABASE_URL=$DB/studystack_main_test   task-service python -m pytest -q
```

`SERVICE_NAME` is what selects the folder: the entrypoint changes into that
service's directory and runs its migrations before starting the command, so
`-w` has no effect.

Create the test databases once:

```bash
docker compose exec postgres psql -U studystack_user -d studystack   -c "CREATE DATABASE studystack_auth_test;"   -c "CREATE DATABASE studystack_main_test;"
```

---

## Migrations

Alembic owns the schema.

| Service | Revision table | Owns |
|---|---|---|
| `task-service` | `alembic_version_tasks` | domains, tasks, subtasks, reminders, study_sessions, task_completions, vision_items, note_folders, notes |
| `auth-service` | `alembic_version_auth` | users, refresh_tokens |

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
| `PORT` | platform-set | platform-set | honoured by the entrypoint |

`JWT_SECRET_KEY` must match across both. If they differ, login succeeds but every later request returns 401, because auth signs tokens the task service cannot verify.

The image defines both an `ENTRYPOINT` and a `CMD`, so it starts whether the host passes a command string or nothing.

---

## Notes

- Deleting a domain removes its tasks, subtasks, reminders and sessions.
- Reminder delivery is a line in the server log. Swapping in email or push does not change the bookkeeping.
- `max_instances=1` only stops overlapping runs inside one process. Two API
  instances would still both scan the same rows, so a second instance needs an
  atomic claim or a worker outside the web process.
- No endpoint paginates. Every list returns everything the user owns.
- Analytics aggregates in Python, one pass per request. Fine for a personal
  tracker, a timeout for years of history. The fix is `GROUP BY` in SQL.
- The task service verifies the JWT signature without querying the database, so
  a token issued to a deleted user still decodes until it expires.
- No rate limiting on `/auth/login` or `/auth/register`.
- Vision and note images are stored in Postgres as bytes. Fine at this size,
  wrong at scale: object storage is the answer once a few hundred users have
  boards.
- Note search is a `LIKE` scan, not full-text search. It will get slow at
  thousands of notes; Postgres `tsvector` is the upgrade path.
- Avatar and vision images are fetched with the bearer token and wrapped in
  blob URLs, because `<img src>` cannot send headers. That means one extra
  request per image and no browser caching across reloads.
- The analytics week runs Monday to Sunday in server-local time.
- Dashboard deletes are optimistic: the row disappears immediately and returns with an inline error banner if the server rejects it.
- Passwords are hashed with Argon2 through `pwdlib` and hashes are never returned by any endpoint.
- Access tokens expire after 30 minutes; a refresh token buys a new pair without
  asking for the password again. Refresh tokens are rotated on every use, and
  reuse of an old one revokes the whole family.
- Tokens live in `localStorage`, so one XSS is a stolen session. `HttpOnly`
  cookies would be safer and would need CSRF handling plus a same-site
  deployment.
