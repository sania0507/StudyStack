/*
  ============================================================
  src/api/client.ts  —  the real backend
  ============================================================
  Every function here talks to one of the three FastAPI
  services. Components never call fetch() directly; they go
  through this file, so there is exactly one place that knows
  about URLs, tokens and error shapes.

  Which service lives where:
    auth-service       -> /auth/register, /auth/login, /auth/me
    main-app           -> /domains, /tasks, /subtasks, /reminders,
                          /sessions, /analytics/summary
*/

import type { Domain, Session, Subtask, Task, User } from "@/api/types"

// An env var that exists but is EMPTY is not caught by ??, which would leave
// the base URL as "" and send requests to the frontend's own origin.
// A var WITHOUT a scheme is worse: fetch() treats "host.name/path" as a
// RELATIVE path, so the request goes to the frontend's own domain and Vercel
// answers 405. Both cases are handled here.
function envUrl(value: string | undefined, fallback: string): string {
  const trimmed = value?.trim()
  if (!trimmed) return fallback

  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`

  return withScheme.replace(/\/+$/, "")
}

const AUTH_URL = envUrl(import.meta.env.VITE_AUTH_URL, "http://localhost:8000")
const MAIN_URL = envUrl(import.meta.env.VITE_MAIN_URL, "http://localhost:8001")

// Analytics is served by the task service now, so it needs no separate URL.
// VITE_ANALYTICS_URL is still honoured if set, for anyone still running the
// old standalone service.
const ANALYTICS_URL = envUrl(import.meta.env.VITE_ANALYTICS_URL, MAIN_URL)

const TOKEN_KEY = "studystack.token"
const REFRESH_KEY = "studystack.refresh"

/* ---------------- token storage ---------------- */

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setRefreshToken(token: string | null) {
  if (token) localStorage.setItem(REFRESH_KEY, token)
  else localStorage.removeItem(REFRESH_KEY)
}

/** Ends the session client-side. The server-side revocation is best effort. */
export function clearTokens() {
  setToken(null)
  setRefreshToken(null)
}

/* ---------------- the one place errors are shaped ---------------- */

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/*
  Refresh is single-flight. Five dashboard requests can all receive a 401 at
  the same moment; without this, all five would present the same refresh token
  and the server would treat the four losers as reuse and revoke the family,
  logging the user out for no reason. The first caller starts the refresh, the
  rest await the same promise.
*/
let refreshInFlight: Promise<boolean> | null = null

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    // Deliberately not via request(): that would attach the dead access token
    // and could recurse into refresh.
    const response = await fetch(`${AUTH_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!response.ok) {
      clearTokens()
      return false
    }

    const pair = (await response.json()) as TokenResponse
    setToken(pair.access_token)
    setRefreshToken(pair.refresh_token)
    return true
  } catch {
    // Network failure: keep the tokens and let the caller surface the error,
    // so a brief outage does not log the user out.
    return false
  }
}

function refreshOnce(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight

  refreshInFlight = refreshAccessToken().finally(() => {
    refreshInFlight = null
  })

  return refreshInFlight
}

async function request<T>(
  baseUrl: string,
  path: string,
  init: RequestInit = {},
  isRetry = false,
): Promise<T> {
  const token = getToken()

  // Only declare JSON when a body is actually being sent. A DELETE with
  // Content-Type triggers an extra CORS preflight for no reason, and if the
  // preflight is rejected the request dies before it reaches the server.
  const headers: Record<string, string> = {}

  if (init.body !== undefined && init.body !== null) {
    headers["Content-Type"] = "application/json"
  }

  Object.assign(headers, (init.headers as Record<string, string>) ?? {})

  if (token) headers.Authorization = `Bearer ${token}`

  let response = await fetch(`${baseUrl}${path}`, { ...init, headers })

  // One retry only. Excluded: the retry itself, and the refresh endpoint,
  // which has no access token to be expired.
  if (response.status === 401 && !isRetry && !path.startsWith("/auth/refresh")) {
    const refreshed = await refreshOnce()

    if (refreshed) {
      const retryToken = getToken()
      const retryHeaders = { ...headers }
      if (retryToken) retryHeaders.Authorization = `Bearer ${retryToken}`

      response = await fetch(`${baseUrl}${path}`, { ...init, headers: retryHeaders })
    }
  }

  // Still 401 after a refresh means the session is really over; drop the
  // tokens so ProtectedRoute sends the user back to /login.
  if (response.status === 401) {
    clearTokens()
  }

  if (!response.ok) {
    const detail = await readDetail(response)
    throw new ApiError(response.status, detail)
  }

  // 204 and empty bodies have nothing to parse.
  if (response.status === 204) return undefined as T

  return (await response.json()) as T
}

// FastAPI sends either {detail: "message"} or {detail: [{msg: ...}]}
async function readDetail(response: Response): Promise<string> {
  try {
    const body = await response.json()
    const detail = body?.detail

    if (typeof detail === "string") return detail

    if (Array.isArray(detail) && detail.length > 0) {
      // Validation errors: show the first problem clearly.
      return detail[0]?.msg ?? "That input isn't valid."
    }

    return "Something went wrong."
  } catch {
    return "Something went wrong."
  }
}

/* ---------------- auth ---------------- */

type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

type BackendUser = {
  id: string
  email: string
  name: string | null
  created_at: string
}

// Prefer the name the user chose; fall back to the email prefix so new
// accounts still show something friendly.
function toUser(user: BackendUser): User {
  const fallback = user.email.split("@")[0]
  const name = user.name?.trim() || fallback

  return {
    id: user.id,
    name: name.charAt(0).toUpperCase() + name.slice(1),
    email: user.email,
    avatarUrl: "",
    joinedAt: user.created_at,
  }
}

export async function login(
  email: string,
  password: string,
): Promise<User> {
  const pair = await request<TokenResponse>(AUTH_URL, "/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })

  setToken(pair.access_token)
  setRefreshToken(pair.refresh_token)

  return currentUser()
}

export async function register(
  name: string,
  email: string,
  password: string,
): Promise<User> {
  await request<BackendUser>(AUTH_URL, "/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  })

  // Registering does not return a token, so log straight in.
  return login(email, password)
}

export async function currentUser(): Promise<User> {
  const user = await request<BackendUser>(AUTH_URL, "/auth/me")

  return toUser(user)
}

export function logout() {
  const refreshToken = getRefreshToken()

  // Best effort: revoking server-side is what makes logout mean anything,
  // but a failed call must never trap the user in a session.
  if (refreshToken) {
    void fetch(`${AUTH_URL}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => undefined)
  }

  clearTokens()
}

/* ---------------- domains ---------------- */

type BackendDomain = {
  id: string
  name: string
  colour: string
  user_id: string
}

export async function getDomains(): Promise<Domain[]> {
  const domains = await request<BackendDomain[]>(MAIN_URL, "/domains")

  return domains.map((domain) => ({
    id: domain.id,
    name: domain.name,
    colour: domain.colour,
    // Filled in from analytics so the dashboard can show week totals.
    minutesThisWeek: 0,
  }))
}

export async function createDomain(name: string): Promise<Domain> {
  const domain = await request<BackendDomain>(MAIN_URL, "/domains", {
    method: "POST",
    body: JSON.stringify({ name }),
  })

  return {
    id: domain.id,
    name: domain.name,
    colour: domain.colour,
    minutesThisWeek: 0,
  }
}

export async function updateDomain(
  id: string,
  patch: { name?: string; colour?: string },
): Promise<Domain> {
  const domain = await request<BackendDomain>(MAIN_URL, `/domains/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  })

  return {
    id: domain.id,
    name: domain.name,
    colour: domain.colour,
    minutesThisWeek: 0,
  }
}

export async function deleteDomain(id: string): Promise<void> {
  await request<void>(MAIN_URL, `/domains/${id}`, { method: "DELETE" })
}

/* ---------------- tasks ---------------- */

type BackendTask = {
  id: string
  domain_id: string
  title: string
  completed: boolean
  completed_at: string | null
  due_date: string | null
  overdue: boolean
  next_reminder_at: string | null
}

type BackendSubtask = {
  id: string
  task_id: string
  title: string
  completed: boolean
}

function toTask(task: BackendTask, subtasks: Subtask[]): Task {
  return {
    id: task.id,
    domainId: task.domain_id,
    title: task.title,
    completed: task.completed,
    dueDate: task.due_date ?? undefined,
    remindAt: task.next_reminder_at ?? undefined,
    overdue: task.overdue,
    subtasks: subtasks.filter((sub) => sub.taskId === task.id),
  }
}

function toSubtask(subtask: BackendSubtask): Subtask {
  return {
    id: subtask.id,
    title: subtask.title,
    completed: subtask.completed,
    taskId: subtask.task_id,
  }
}

// Tasks and subtasks come from two endpoints, so they are stitched here.
export async function getTasks(): Promise<Task[]> {
  const [tasks, subtasks] = await Promise.all([
    request<BackendTask[]>(MAIN_URL, "/tasks"),
    request<BackendSubtask[]>(MAIN_URL, "/subtasks"),
  ])

  const mappedSubtasks = subtasks.map(toSubtask)

  return tasks.map((task) => toTask(task, mappedSubtasks))
}

export async function createTask(input: {
  domainId: string
  title: string
  dueDate?: string
}): Promise<Task> {
  const task = await request<BackendTask>(MAIN_URL, "/tasks", {
    method: "POST",
    body: JSON.stringify({
      domain_id: input.domainId,
      title: input.title,
      due_date: input.dueDate ?? null,
    }),
  })

  return toTask(task, [])
}

export async function updateTask(
  id: string,
  patch: {
    title?: string
    completed?: boolean
    dueDate?: string | null
  },
): Promise<Task> {
  const body: Record<string, unknown> = {}

  if (patch.title !== undefined) body.title = patch.title
  if (patch.completed !== undefined) body.completed = patch.completed
  if (patch.dueDate !== undefined) body.due_date = patch.dueDate

  const task = await request<BackendTask>(MAIN_URL, `/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })

  return toTask(task, [])
}

export async function deleteTask(id: string): Promise<void> {
  await request<void>(MAIN_URL, `/tasks/${id}`, { method: "DELETE" })
}

/* ---------------- subtasks ---------------- */

export async function createSubtask(
  taskId: string,
  title: string,
): Promise<Subtask> {
  const subtask = await request<BackendSubtask>(MAIN_URL, "/subtasks", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId, title }),
  })

  return toSubtask(subtask)
}

export async function updateSubtask(
  id: string,
  patch: { title?: string; completed?: boolean },
): Promise<Subtask> {
  const subtask = await request<BackendSubtask>(
    MAIN_URL,
    `/subtasks/${id}`,
    { method: "PATCH", body: JSON.stringify(patch) },
  )

  return toSubtask(subtask)
}

export async function deleteSubtask(id: string): Promise<void> {
  await request<void>(MAIN_URL, `/subtasks/${id}`, { method: "DELETE" })
}

/* ---------------- reminders ---------------- */

export async function createReminder(
  taskId: string,
  remindAt: string,
): Promise<void> {
  await request(MAIN_URL, "/reminders", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId, remind_at: remindAt }),
  })
}

/* ---------------- sessions ---------------- */

export async function createSession(input: {
  domainId: string
  minutes: number
}): Promise<Session> {
  const session = await request<{
    id: string
    domain_id: string
    minutes: number
    finished_at: string
  }>(MAIN_URL, "/sessions", {
    method: "POST",
    body: JSON.stringify({
      domain_id: input.domainId,
      minutes: input.minutes,
    }),
  })

  return {
    id: session.id,
    domainId: session.domain_id,
    minutes: session.minutes,
    finishedAt: session.finished_at,
  }
}

export async function getSessions(): Promise<Session[]> {
  const sessions = await request<
    { id: string; domain_id: string; minutes: number; finished_at: string }[]
  >(MAIN_URL, "/sessions")

  return sessions.map((session) => ({
    id: session.id,
    domainId: session.domain_id,
    minutes: session.minutes,
    finishedAt: session.finished_at,
  }))
}

/* ---------------- analytics ---------------- */

export type AnalyticsSummary = {
  hoursPerWeek: number
  streak: number
  overdueCount: number
  totalMinutes: number
  totalSessions: number
  daysWithSessions: number
  sessionsPerDay: number
  weekdayMinutes: { day: string; minutes: number }[]
  domainCompletion: {
    domainId: string
    name: string
    totalTasks: number
    completedTasks: number
    completionPercent: number
  }[]
  heatmap: { date: string; minutes: number; tasksCompleted: number }[]
}

export async function getAnalytics(): Promise<AnalyticsSummary> {
  const summary = await request<{
    hours_per_week: number
    streak: number
    overdue_count: number
    total_minutes: number
    total_sessions: number
    days_with_sessions: number
    sessions_per_day: number
    weekday_minutes: { weekday: string; minutes: number }[]
    domain_completion: {
      domain_id: string
      name: string
      total_tasks: number
      completed_tasks: number
      completion_percent: number
    }[]
    heatmap: { day: string; minutes: number; tasks_completed: number }[]
  }>(ANALYTICS_URL, "/analytics/summary")

  return {
    hoursPerWeek: summary.hours_per_week,
    streak: summary.streak,
    overdueCount: summary.overdue_count,
    totalMinutes: summary.total_minutes,
    totalSessions: summary.total_sessions,
    daysWithSessions: summary.days_with_sessions,
    sessionsPerDay: summary.sessions_per_day,
    weekdayMinutes: summary.weekday_minutes.map((entry) => ({
      day: entry.weekday.slice(0, 3),
      minutes: entry.minutes,
    })),
    domainCompletion: summary.domain_completion.map((entry) => ({
      domainId: entry.domain_id,
      name: entry.name,
      totalTasks: entry.total_tasks,
      completedTasks: entry.completed_tasks,
      completionPercent: entry.completion_percent,
    })),
    heatmap: summary.heatmap.map((entry) => ({
      date: entry.day,
      minutes: entry.minutes,
      tasksCompleted: entry.tasks_completed,
    })),
  }
}

/* ---------------- profile ---------------- */

// The backend returns the updated user, so the context can trust the result.
export async function updateProfile(
  patch: { name?: string; email?: string },
): Promise<User> {
  const user = await request<BackendUser>(AUTH_URL, "/auth/me", {
    method: "PATCH",
    body: JSON.stringify(patch),
  })

  return toUser(user)
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await request<void>(AUTH_URL, "/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}
