# StudyStack

Most study apps assume a routine you don't have. They want a weekly schedule, a fixed block for each subject, a plan made on Sunday that you follow on Tuesday. If you work in bursts instead — three hours tonight on one thing, nothing for four days, then panic — those apps ask you to be someone else before they'll help you.

StudyStack tracks the work without demanding the schedule. Add what's due, break it into pieces, set deadlines that actually count down, and start a timer when the energy hits. **It counts what you did, not what you planned to do.**

I built it because that's how I study.

Two FastAPI services, one React frontend, one PostgreSQL database. Containerised, deployed, 120 tests.

---

## Screenshots

<!-- Screenshots live on GitHub user-attachment URLs. To replace one, drag a
     new file into the GitHub markdown editor and copy the URL it produces — it
     looks like https://github.com/user-attachments/assets/<id> — then swap that
     id below. Keep the ![alt](url) shape: pasting the editor's HTML snippet
     into the ( ) slot is what broke these before. -->

<table>
  <tr>
    <td width="50%">
      <img width="959" height="411" alt="image" src="https://github.com/user-attachments/assets/794a09b6-4e36-45bd-8cdd-ffb24c1a859b" />
     <br /><sub><b>Dashboard</b> — domains, tasks and the focus timer</sub>
    </td>
    <td width="50%">
      <img width="959" height="412" alt="image" src="https://github.com/user-attachments/assets/a5ff5d1a-df35-4323-8e45-543d0aa77b2a" />
      <br /><sub><b>Dashboard</b> — a block in progress</sub>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img width="956" height="418" alt="image" src="https://github.com/user-attachments/assets/7cf3b073-9bbf-46e7-8e68-849e473ac436" />
      <br /><sub><b>Analytics</b> — weekly split and the year heatmap</sub>
    </td>
    <td width="50%">
      <img width="959" height="410" alt="image" src="https://github.com/user-attachments/assets/8be0ab4b-dd79-4b8b-a9d8-29712341b5a2" />
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

## Tech stack

| Layer | Used |
|---|---|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.0 (typed `Mapped` models), Pydantic v2, Alembic |
| Database | PostgreSQL, psycopg 3 |
| Auth | HS256 JWT (PyJWT), Argon2 password hashing (`pwdlib`) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, React Router |
| Scheduling | APScheduler, running inside the task service's `lifespan` |
| Tests | pytest, one test database per service |
| Infra | Docker + Docker Compose, Vercel (frontend), Railway (services), Neon (PostgreSQL) |

---

## What it does

| Area | Features |
|---|---|
| **Deadlines** | Domains → tasks → subtasks. Optional due dates, `overdue` derived on read. |
| **Focus timer** | A finished block writes a study session against a domain. |
| **Analytics** | Hours per week, streak, overdue count, weekday split, per-domain completion (measured in subtasks where a domain has them), year heatmap. A day counts towards the streak if you ran a focus block **or** ticked a task. |
| **Reminders** | Per-task reminders fired by a 60-second scheduler that claims each row before it fires. |
| **Routines** | A domain marked `repeats_daily` untick itself each morning, with the history kept. |
| **Notes** | Folders, a date timeline, drag-to-reorder, pinning, search, markdown. |
| **Vision board** | Images you upload or paste in, then drag and resize freely. |
| **Accounts** | Short-lived access tokens with rotating refresh tokens; every request scoped to the caller's own data. |

---

## Architecture

```
                  ┌────────────────────┐
                  │    auth-service    │  :8000
                  │  register / login  │  owns: users, refresh_tokens
                  │  profile, avatar   │
                  └─────────┬──────────┘
                            │ JWT — verified by signature, no DB call
                            ↓
   ┌────────────────────────────────────────────────────────┐
   │            task-service (main-app)             :8001    │
   │                                                         │
   │  deadlines   domains → tasks → subtasks                 │
   │              due dates, derived overdue                 │
   │  reminders   + scheduler (60s tick)                     │
   │  sessions    focus timer records study sessions         │
   │  analytics   /analytics/summary, computed on request    │
   │  notes       note_folders → notes                       │
   │  vision      vision_items (image bytes)                 │
   └────────────────────────┬───────────────────────────────┘
                            ↓
                     ┌──────────────┐
                     │  PostgreSQL  │  one database, split table ownership
                     └──────────────┘
```

| Service | Port | Owns |
|---|---|---|
| `auth-service` | 8000 | `users`, `refresh_tokens` |
| `task-service` (`main-app`) | 8001 | `domains`, `tasks`, `subtasks`, `reminders`, `study_sessions`, `task_completions`, `note_folders`, `notes`, `vision_items` |
| frontend | 3000 (dev) | React app, hosted on Vercel |

Both services share one database but own separate tables, and each has its own Alembic revision table (`alembic_version_auth`, `alembic_version_tasks`) because two services writing to one `alembic_version` corrupt each other's revision chain.

### Where the notes and the vision board fit

Both are **routers inside the task service**, not services of their own — `routers/notes.py` and `routers/vision.py`, with `models/note.py` and `models/vision_item.py`.

```
task-service
  ├── deadlines   domains → tasks → subtasks
  ├── sessions / analytics
  ├── notes       note_folders ──< notes        ← separate aggregate
  └── vision      vision_items                  ← separate aggregate
```

Why they belong in the same process:

- **They are plain per-user CRUD.** Two small tables, no scheduled work, no aggregation, no cross-service reads. A third and fourth service would add two deployments, two CORS origins and two JWT checks and buy no isolation.
- **They inherit the same ownership model as everything else.** Every row carries `user_id`; every lookup goes through an `owned_note` / `owned_folder` / `owned_item` helper that scopes the query, so a note or a board tile is only ever visible to its owner. "Not yours" returns 404 rather than 403, because 404 does not confirm the id exists.
- **They are deliberately not joined to `domains`.** A folder is modelled like a domain but kept separate, because deleting a study domain must not take a diary entry with it. Same reasoning for the vision board: separate aggregate, separate cascade, no foreign key into the study graph.
- **The only external I/O is on save.** A pasted image link is fetched once when the item is created; nothing on the board depends on a third-party host at render time.

The one thing they add that the rest of the app does not have: **binary data in Postgres.** `vision_items.image_data` and the user's avatar are `LargeBinary` columns, and both are served by an endpoint behind the owner's token (`GET /vision-items/{id}/image`, `GET /auth/me/avatar`). Because `<img src>` cannot send an `Authorization` header, the frontend fetches the bytes and wraps them in a blob URL. That costs one extra request per image and no browser caching across reloads — an accepted trade for keeping every image private by default.

That choice is right at this size and wrong at a few hundred boards; object storage is the upgrade path, and only these two tables would change.

### Data model

```
users (auth-service)
  ├──< refresh_tokens            hashed, rotated, grouped by family_id
  └── owns everything below, by user_id

domains
  ├──< tasks
  │     ├──< subtasks
  │     ├──< reminders
  │     └──< task_completions    unique per (task, day) — routine history
  └──< study_sessions            keeps domain_name/task_title snapshots

note_folders ──< notes           separate aggregate: a domain delete
vision_items                     must not take a diary entry with it
```

Deleting a domain deletes the study graph — its tasks, and from there subtasks and reminders — but it does **not** delete the history. `study_sessions` and `task_completions` use `ON DELETE SET NULL`: the row survives with its link cleared, so totals, the heatmap and the streak still count hours you really spent and days you really ticked something. Sessions carry a snapshot of the domain name and task title taken when the block was recorded, so the activity feed can still say *what* a deleted-domain session was; `task_completions` carries its own `user_id` for the same reason. No rows are left orphaned, and none are quietly discarded.

`overdue` is never stored. It is computed from `due_date`, `completed` and the current time on every read, so it can never disagree with the rows.

---

## Decisions worth knowing

**Overdue is derived, not stored.** A boolean column would need a job to flip it and would be wrong between runs. Deriving it means the state is always a fact about the data, not a copy of it.

**Claim before work.** Two places need "exactly once" and both use the same trick — a single conditional update that succeeds or fails, rather than a read followed by a write.

- *Refresh tokens:* `UPDATE ... WHERE id = ? AND revoked_at IS NULL`. Read-then-revoke would let two concurrent refreshes both pass the check and both issue tokens.
- *Reminders:* `sent_at` is claimed the same way, so a reminder cannot fire twice, including across a restart.

**Refresh tokens rotate, and reuse revokes the family.** Access tokens are 30-minute HS256 JWTs, verified by signature alone, so neither service touches the database to authenticate a request. The refresh token is 30 days, opaque, and stored as a SHA-256 hash — not Argon2, deliberately: it is 48 random bytes, so there is nothing to brute force and every refresh needs a fast lookup. Reuse of an already-rotated token means the client or an attacker holds it, and one row cannot say which, so the whole `family_id` is revoked and both parties log in again. On the client, refresh is single-flight: five simultaneous 401s produce one refresh, not five.

**Routines reset on read.** A `repeats_daily` domain's tasks are unticked when `GET /tasks` sees a completion from before today. That makes the reset idempotent and needs no scheduler. Every completion also writes a `task_completions` row, so clearing the tick does not erase the evidence of the work; the heatmap reads both sources and takes the larger per day.

**A streak counts days you did something, not just days you timed.** The streak used to read `study_sessions` alone, so an account that ticked tasks every day and never started the timer reported 0 — the heatmap counted the ticks and the streak did not, which is worse than either behaviour alone. Both now read the same two sources: a day is active if it has a timed block or a ticked task.

**History outlives the thing it happened in.** Deleting a domain is a statement about the current plan, not a retraction of the past, so it removes the domain and its tasks while `study_sessions` and `task_completions` survive with their foreign keys set to `NULL`. Snapshots (`domain_name`, `task_title`) are written at record time so a surviving row can still name itself. The consequence to be aware of: per-domain completion percentage naturally stops listing a domain that no longer exists, because there is no domain left to compute it for.

**Notes: `created_at` is the timeline, `position` is not a date.** Drag-to-reorder sets `position` and never touches `created_at`, and editing only moves `updated_at` — so the date beside a note says when it was written and dragging it is not editing. Markdown is rendered by a small escape-first function rather than a library, so a note cannot inject markup.

**Vision board: images are bytes, positions are percentages.** Pinterest image URLs expire, so a board holding only links would quietly develop holes — a pasted link is fetched once on save and the bytes kept. Positions are percentages of a fixed-height board, so "40% from the top" means the same thing on a laptop and a phone, and height follows the image's own aspect ratio instead of cropping to a square. Dragging uses pointer events with `setPointerCapture` and one PATCH on release, not one per move.

**Two services, not three.** Analytics was originally its own service fed by RabbitMQ events. It read the same database, wrote nothing, and shared the task service's data completely — the split gave no isolation and no independent scaling, while the event publisher opened a broker connection inside each request to publish messages no queue was ever bound to. It is now a router (`/analytics/summary`) computed on request. One fewer deployment, CORS origin, JWT check and broker. If a real consumer ever appears, the right starting point is a transactional outbox, not a publish inside the request path.

---

## API overview

### auth-service (8000)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | 409 if the email exists; `name` optional |
| POST | `/auth/login` | returns an access token, a refresh token and `token_type` |
| POST | `/auth/refresh` | new pair; 401 if unknown, expired, revoked or already rotated |
| POST | `/auth/logout` | 204; revokes the presented token, idempotent and unauthenticated |
| GET / PATCH | `/auth/me` | read, or update `name` and/or `email` (409 if taken) |
| POST | `/auth/change-password` | 204; revokes every refresh token for the user |
| POST / GET / DELETE | `/auth/me/avatar` | upload (PNG/JPEG/WebP, 512 KB), fetch behind the token, clear |

### task-service (8001)

Every route requires a Bearer token and is scoped to the caller's own data.

| Method | Path |
|---|---|
| POST / GET | `/domains` · PATCH / DELETE `/domains/{id}` |
| POST / GET | `/tasks` (filters: `completed`, `overdue`, `domain_id`) · PATCH / DELETE `/tasks/{id}` |
| POST / GET | `/subtasks` · PATCH / DELETE `/subtasks/{id}` |
| POST / GET | `/reminders` (filters: `task_id`, `sent`) · PATCH / DELETE `/reminders/{id}` |
| POST / GET | `/sessions` (filter: `domain_id`) |
| GET | `/analytics/summary?heatmap_days=30` |
| POST / GET | `/vision-items` · POST `/vision-items/upload` · GET `/vision-items/{id}/image` · PATCH / DELETE `/vision-items/{id}` |
| POST / GET | `/note-folders` · PATCH / DELETE `/note-folders/{id}` |
| POST / GET | `/notes` (filters: `folder_id`, `search`) · POST `/notes/reorder` · PATCH / DELETE `/notes/{id}` |
| GET | `/health` |

`TaskOut` includes `next_reminder_at`, the soonest pending reminder, so the UI can show a reminder badge without a second request. Interactive docs are at `/docs` on both services.

---

## Run it locally

```bash
docker compose up --build
```

Then open http://localhost:3000. Migrations run on container start, so an empty database needs no manual step.

Without Docker, one shell per piece. Each service needs its own `.env`, copied from its `.env.example`:

```bash
cd backend/auth-service && uvicorn main:app --port 8000
cd backend/main-app     && uvicorn main:app --port 8001
cd frontend             && npm install && npm run dev
```

The frontend reads `VITE_AUTH_URL` and `VITE_MAIN_URL`, defaulting to `http://localhost:8000` and `http://localhost:8001`. Analytics is served by the task service, so there is no third variable.

---

## Tests

120 tests — 87 in the task service, 33 in auth. Each service has its own test database, and the fixtures refuse to run against any other name.

```bash
cd backend/main-app
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_main_test pytest

cd backend/auth-service
TEST_DATABASE_URL=postgresql+psycopg://studystack_user:PASSWORD@localhost:5432/studystack_auth_test pytest
```

Covered: registration and duplicate email, login and wrong password, refresh rotation and reuse detection revoking the family, token expiry, logout idempotency, profile and password change; CRUD for every resource including notes and the vision board; cross-user isolation on read, update and delete; completion timestamps; overdue derivation across all four due-date cases; reminder idempotency; domain cascade to tasks and nested children, and the history that survives the delete; the streak counting ticked tasks as well as timed blocks; routine reset and the `task_completions` history; analytics windowing and scoping.

Create the test databases once:

```bash
docker compose exec postgres psql -U studystack_user -d studystack \
  -c "CREATE DATABASE studystack_auth_test;" \
  -c "CREATE DATABASE studystack_main_test;"
```

---

## Migrations

Alembic owns the schema; `create_all()` is not used in production.

| Service | Revision table | Owns |
|---|---|---|
| `task-service` | `alembic_version_tasks` | domains, tasks, subtasks, reminders, study_sessions, task_completions, vision_items, note_folders, notes |
| `auth-service` | `alembic_version_auth` | users, refresh_tokens |

Migrations run at container start when `MIGRATE_ON_START=true`. To run by hand: `alembic upgrade head` from either service directory.

---

## Deployment

- React + Vite frontend on **Vercel**, with Root Directory set to `frontend`.
- Two FastAPI services on **Railway**, built from one shared image and told apart by `SERVICE_NAME`.
- PostgreSQL on **Neon**, passed in as `DATABASE_URL` and using the `+psycopg` driver.

| Variable | auth | tasks | Notes |
|---|---|---|---|
| `SERVICE_NAME` | `auth-service` | `main-app` | selects the service folder |
| `DATABASE_URL` | required | required | must include `+psycopg` |
| `JWT_SECRET_KEY` | required | required | must be identical on both |
| `CORS_ORIGINS` | required | required | comma-separated, no trailing slash |
| `MIGRATE_ON_START` | `true` | `true` | runs `alembic upgrade head` |
| `PORT` | platform-set | platform-set | honoured by the entrypoint |

`JWT_SECRET_KEY` must match across both. If they differ, login succeeds and every later request returns 401, because auth signs tokens the task service cannot verify.

---

## Known limitations

- No rate limiting on `/auth/login` or `/auth/register`.
- Tokens live in `localStorage`, so one XSS is a stolen session. `HttpOnly` cookies would be safer and would need CSRF handling plus a same-site deployment.
- No endpoint paginates; every list returns everything the user owns. Note search is a `LIKE` scan, not full-text — Postgres `tsvector` is the upgrade path.
- Analytics aggregates in Python, one pass per request. Fine for a personal tracker, a timeout for years of history; the fix is `GROUP BY` in SQL.
- Reminder delivery is a line in the server log. Swapping in email or push does not change the bookkeeping.
- `max_instances=1` only stops overlapping runs inside one process. Two API instances would both scan the same rows, so a second instance needs an atomic claim or a worker outside the web process.
- On hosts that sleep idle services the reminder tick pauses with the service, so reminders fire on the next wake rather than exactly on time.
- The task service verifies the JWT signature without querying the database, so a token issued to a deleted user still decodes until it expires.
- Vision and avatar images are stored in Postgres as bytes. Fine at this size, wrong at scale.
- The analytics week runs Monday to Sunday in server-local time.
- Dashboard deletes are optimistic: the row disappears immediately and returns with an inline error banner if the server rejects it.
