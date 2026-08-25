/*
  ============================================================
  src/api/mock.ts  —  the fake backend
  ============================================================
  Right now every function here just returns made-up data after
  a short delay. Later, when your FastAPI service is running,
  you replace the *body* of each function with a real fetch():

      export async function login(email, password) {
        const res = await fetch("http://localhost:8000/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        })
        if (!res.ok) throw new Error("Invalid credentials")
        return res.json()
      }

  Nothing in your components changes. That is why we keep all
  data access in one folder instead of calling fetch() inside
  a page.
*/

export type User = {
  id: string
  name: string
  email: string
  avatarUrl: string
  joinedAt: string
}

export type Domain = {
  id: string
  name: string
  colour: string // a token name, e.g. "violet"
  minutesThisWeek: number
}

export type Subtask = {
  id: string
  title: string
  completed: boolean
}

export type Task = {
  id: string
  domainId: string
  title: string
  completed: boolean
  dueDate?: string // "YYYY-MM-DD" — optional deadline
  remindAt?: string // "YYYY-MM-DDTHH:mm" — optional reminder
  subtasks: Subtask[]
}

export type Session = {
  id: string
  domainId: string
  minutes: number
  finishedAt: string // ISO string
}

/** Pretend the network took a moment. Lets you see loading states. */
const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms))

/* ---------------- auth ---------------- */

const FAKE_USER: User = {
  id: "u_1",
  name: "Myra",
  email: "myra@studystack.app",
  avatarUrl: "",
  joinedAt: "2026-02-14",
}

export async function login(email: string, password: string): Promise<User> {
  await delay()
  if (!email.includes("@")) throw new Error("That doesn't look like an email address.")
  if (password.length < 6) throw new Error("Password must be at least 6 characters.")
  return { ...FAKE_USER, email }
}

export async function register(name: string, email: string, password: string): Promise<User> {
  await delay()
  if (name.trim().length < 2) throw new Error("Please tell us your name.")
  if (!email.includes("@")) throw new Error("That doesn't look like an email address.")
  if (password.length < 6) throw new Error("Password must be at least 6 characters.")
  return { ...FAKE_USER, name: name.trim(), email }
}

export async function updateProfile(patch: Partial<User>): Promise<Partial<User>> {
  await delay(500)
  return patch
}

export async function changePassword(current: string, next: string): Promise<void> {
  await delay(500)
  if (current.length < 6) throw new Error("Current password is incorrect.")
  if (next.length < 6) throw new Error("New password must be at least 6 characters.")
}

/* ---------------- domains & tasks ---------------- */

export const domains: Domain[] = [
  { id: "d_1", name: "Data Structures", colour: "violet", minutesThisWeek: 412 },
  { id: "d_2", name: "Backend / FastAPI", colour: "mint", minutesThisWeek: 288 },
  { id: "d_3", name: "Linear Algebra", colour: "violet-soft", minutesThisWeek: 156 },
  { id: "d_4", name: "Side Projects", colour: "violet", minutesThisWeek: 95 },
]

export const tasks: Task[] = [
  {
    id: "t_1",
    domainId: "d_1",
    title: "Finish binary tree traversals",
    completed: false,
    dueDate: "2026-08-27",
    remindAt: "2026-08-27T09:00",
    subtasks: [
      { id: "st_1_1", title: "Write iterative in-order traversal", completed: true },
      { id: "st_1_2", title: "Write recursive pre-order traversal", completed: false },
      { id: "st_1_3", title: "Compare stack usage for both", completed: false },
    ],
  },
  { id: "t_2", domainId: "d_1", title: "Re-do the graph problem set", completed: true, subtasks: [] },
  {
    id: "t_3",
    domainId: "d_2",
    title: "Write POST /tasks with Pydantic",
    completed: false,
    subtasks: [
      { id: "st_3_1", title: "Draft the TaskIn schema", completed: true },
      { id: "st_3_2", title: "Handle validation errors", completed: false },
    ],
  },
  { id: "t_4", domainId: "d_2", title: "Read up on SQLAlchemy relationships", completed: false, subtasks: [] },
  { id: "t_5", domainId: "d_3", title: "Eigenvalues — practice sheet 4", completed: true, subtasks: [] },
  {
    id: "t_6",
    domainId: "d_4",
    title: "Ship the StudyStack landing page",
    completed: false,
    dueDate: "2026-08-26",
    subtasks: [
      { id: "st_6_1", title: "Write the hero copy", completed: true },
      { id: "st_6_2", title: "Wire up the CTA buttons", completed: false },
    ],
  },
]

export const recentSessions: Session[] = [
  { id: "s_1", domainId: "d_2", minutes: 60, finishedAt: "2026-08-25T09:10:00Z" },
  { id: "s_2", domainId: "d_1", minutes: 90, finishedAt: "2026-08-25T07:30:00Z" },
  { id: "s_3", domainId: "d_4", minutes: 45, finishedAt: "2026-08-24T18:05:00Z" },
  { id: "s_4", domainId: "d_3", minutes: 30, finishedAt: "2026-08-24T14:20:00Z" },
  { id: "s_5", domainId: "d_1", minutes: 60, finishedAt: "2026-08-23T20:00:00Z" },
]

/* ---------------- analytics ---------------- */

export const stats = {
  deepWorkThisMonth: 682, // minutes
  streakDays: 39,
  missedThisWeek: 1,
  weeklyGoalMinutes: 900,
}

/**
 * 371 days of fake activity for the contribution-style heatmap.
 * Each entry: 0 = nothing, 1..4 = increasing intensity.
 */
export const heatmap: { date: string; level: number }[] = (() => {
  const out: { date: string; level: number }[] = []
  const today = new Date("2026-08-25T00:00:00Z")
  for (let i = 370; i >= 0; i--) {
    const d = new Date(today)
    d.setUTCDate(d.getUTCDate() - i)
    // deterministic pseudo-random so the chart looks the same on every reload
    const seed = (d.getUTCDate() * 7 + d.getUTCMonth() * 31 + i * 13) % 11
    const weekend = d.getUTCDay() === 0 || d.getUTCDay() === 6
    let level = seed > 7 ? 4 : seed > 5 ? 3 : seed > 3 ? 2 : seed > 1 ? 1 : 0
    if (weekend && seed % 2 === 0) level = Math.max(0, level - 2)
    out.push({ date: d.toISOString().slice(0, 10), level })
  }
  return out
})()

/** Minutes per weekday, for the bar chart. */
export const weekdayMinutes = [
  { day: "Mon", minutes: 145 },
  { day: "Tue", minutes: 90 },
  { day: "Wed", minutes: 172 },
  { day: "Thu", minutes: 60 },
  { day: "Fri", minutes: 128 },
  { day: "Sat", minutes: 42 },
  { day: "Sun", minutes: 75 },
]
