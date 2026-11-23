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
    main-app           -> /domains, /tasks, /subtasks, /reminders, /sessions
    analytics-service  -> /analytics/summary
*/

import type { Domain, Session, Subtask, Task, User } from "@/api/types"

const AUTH_URL = import.meta.env.VITE_AUTH_URL ?? "http://localhost:8000"
const MAIN_URL = import.meta.env.VITE_MAIN_URL ?? "http://localhost:8001"
const ANALYTICS_URL =
  import.meta.env.VITE_ANALYTICS_URL ?? "http://localhost:8002"

const TOKEN_KEY = "studystack.token"

/* ---------------- token storage ---------------- */

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/* ---------------- the one place errors are shaped ---------------- */

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(
  baseUrl: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  }

  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${baseUrl}${path}`, { ...init, headers })

  // 401 means the stored token is gone or expired; drop it so the
  // ProtectedRoute sends the user back to /login.
  if (response.status === 401) {
    setToken(null)
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

type TokenResponse = { access_token: string; token_type: string }

type BackendUser = {
  id: string
  email: string
  created_at: string
}

// The backend has no name or avatar yet, so we derive them for display.
function toUser(user: BackendUser): User {
  const name = user.email.split("@")[0]

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
  const token = await request<TokenResponse>(AUTH_URL, "/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })

  setToken(token.access_token)

  return currentUser()
}

export async function register(
  name: string,
  email: string,
  password: string,
): Promise<User> {
  await request<BackendUser>(AUTH_URL, "/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })

  // Registering does not return a token, so log straight in.
  return login(email, password)
}

export async function currentUser(): Promise<User> {
  const user = await request<BackendUser>(AUTH_URL, "/auth/me")

  return toUser(user)
}

export function logout() {
  setToken(null)
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
  heatmap: { date: string; minutes: number }[]
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
    heatmap: { day: string; minutes: number }[]
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
    })),
  }
}

/* ---------------- profile ---------------- */

// The auth service has no update endpoint yet, so these stay local.
export async function updateProfile(
  patch: Partial<User>,
): Promise<Partial<User>> {
  return patch
}

export async function changePassword(
  current: string,
  next: string,
): Promise<void> {
  if (current.length < 6) throw new Error("Current password is incorrect.")
  if (next.length < 6) throw new Error("New password must be at least 6 characters.")
}
