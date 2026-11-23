import { useEffect, useState } from "react"
import { Bell, CalendarDays, Check, ChevronDown, Plus, X } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { useDomains } from "@/context/DomainsContext"
import * as api from "@/api/client"
import type { Task } from "@/api/types"
import { Button, Card, Field, Pill, StackBar, StatCard, cx } from "@/components/ui"
import FrogCard from "@/components/FrogCard"

/*
  ============================================================
  Dashboard — domains + tasks, backed by the real API
  ============================================================
  Derived state rule: `visible`, `done`, and `totalMinutes` are
  CALCULATED from existing state during render — never stored.

  Domain list is shared (DomainsContext). Tasks load from the
  backend and every edit writes through, so a refresh no longer
  loses your work.
*/

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

function formatDue(due: string) {
  const [, m, d] = due.split("-")
  return `${MONTHS[Number(m) - 1]} ${Number(d)}`
}

function formatReminder(iso: string) {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
}

export default function Dashboard() {
  const { user } = useAuth()
  const { domains, addDomain, removeDomain } = useDomains()

  // --- page state ---
  const [tasks, setTasks] = useState<Task[]>([])
  const [activeDomain, setActiveDomain] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string[]>([])

  // Real analytics numbers replace the old hardcoded `stats` object.
  const [analytics, setAnalytics] = useState<api.AnalyticsSummary | null>(null)

  useEffect(() => {
    async function loadTasks() {
      try {
        setTasks(await api.getTasks())
      } catch (error) {
        console.error("Failed to load tasks:", error)
      }
    }

    async function loadAnalytics() {
      try {
        setAnalytics(await api.getAnalytics())
      } catch (error) {
        // Analytics is a nice-to-have here; the task list still works.
        console.error("Failed to load analytics:", error)
      }
    }

    loadTasks()
    loadAnalytics()
  }, [])

  // Live 12h clock for the greeting.
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(id)
  }, [])

  // New-domain form.
  const [addingDomain, setAddingDomain] = useState(false)
  const [newDomainName, setNewDomainName] = useState("")

  // New-task form.
  const [addingTask, setAddingTask] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const [newDomainId, setNewDomainId] = useState(domains[0]?.id ?? "d_1")
  const [newDue, setNewDue] = useState("")
  const [newRemind, setNewRemind] = useState(false)
  const [newRemindAt, setNewRemindAt] = useState("")

  // Inline subtask form.
  const [subtaskFor, setSubtaskFor] = useState<string | null>(null)
  const [subtaskTitle, setSubtaskTitle] = useState("")

  // --- derived values: recalculated on every render, never stored ---
  const visible = activeDomain ? tasks.filter((t) => t.domainId === activeDomain) : tasks
  const done = tasks.filter((t) => t.completed).length
  const totalMinutes = domains.reduce((sum, d) => sum + d.minutesThisWeek, 0)

  const dateStr = now.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })
  const timeStr = now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })

  // --- actions ---
  async function toggleTask(id: string) {
    const task = tasks.find((t) => t.id === id)
    if (!task) return

    // Optimistic update: flip it locally, then correct course if the API fails.
    const nextCompleted = !task.completed
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, completed: nextCompleted } : t)))

    try {
      await api.updateTask(id, { completed: nextCompleted })
    } catch (error) {
      console.error("Failed to update task:", error)
      setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, completed: task.completed } : t)))
    }
  }

  async function toggleSubtask(_taskId: string, subtaskId: string) {
    const found = tasks.flatMap((t) => t.subtasks).find((st) => st.id === subtaskId)
    if (!found) return

    const nextCompleted = !found.completed

    setTasks((prev) =>
      prev.map((t) => ({
        ...t,
        subtasks: t.subtasks.map((st) => (st.id === subtaskId ? { ...st, completed: nextCompleted } : st)),
      })),
    )

    try {
      await api.updateSubtask(subtaskId, { completed: nextCompleted })
    } catch (error) {
      console.error("Failed to update subtask:", error)
      setTasks((prev) =>
        prev.map((t) => ({
          ...t,
          subtasks: t.subtasks.map((st) => (st.id === subtaskId ? { ...st, completed: found.completed } : st)),
        })),
      )
    }
  }

  function toggleExpanded(id: string) {
    setExpanded((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function commitDomain() {
    if (!newDomainName.trim()) return
    await addDomain(newDomainName)
    setNewDomainName("")
    setAddingDomain(false)
  }

  function openAddTask() {
    setNewTitle("")
    setNewDue("")
    setNewRemind(false)
    setNewRemindAt("")
    if (!activeDomain) setNewDomainId(domains[0]?.id ?? "")
    setAddingTask(true)
  }

  async function commitTask() {
    const title = newTitle.trim()
    if (!title) return

    const domainId = activeDomain ?? newDomainId
    if (!domainId) return

    try {
      const created = await api.createTask({ domainId, title, dueDate: newDue || undefined })

      // A reminder is a separate resource, so it is created after the task.
      if (newRemind && newRemindAt) {
        await api.createReminder(created.id, new Date(newRemindAt).toISOString())

        // Re-read the task so the bell badge shows the reminder time,
        // which the backend now includes on each task.
        const refreshed = await api.getTasks()
        setTasks(refreshed)
      } else {
        setTasks((prev) => [...prev, created])
      }

      setAddingTask(false)
    } catch (error) {
      console.error("Failed to create task:", error)
    }
  }

  async function commitSubtask(taskId: string) {
    const title = subtaskTitle.trim()
    if (!title) return

    try {
      const created = await api.createSubtask(taskId, title)

      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, subtasks: [...t.subtasks, created] } : t)))
      setSubtaskFor(null)
      setSubtaskTitle("")
    } catch (error) {
      console.error("Failed to create subtask:", error)
    }
  }

  // --- deletes: confirm first, then remove locally so the UI updates at once ---

  async function deleteTaskById(id: string) {
    if (!window.confirm("Delete this task and its subtasks?")) return

    try {
      await api.deleteTask(id)
      setTasks((prev) => prev.filter((t) => t.id !== id))
    } catch (error) {
      // Tell the user instead of failing silently in the console.
      window.alert(
        `Could not delete the task: ${error instanceof Error ? error.message : "unknown error"}`,
      )
    }
  }

  async function deleteSubtaskById(taskId: string, subtaskId: string) {
    if (!window.confirm("Delete this subtask?")) return

    try {
      await api.deleteSubtask(subtaskId)
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId ? { ...t, subtasks: t.subtasks.filter((st) => st.id !== subtaskId) } : t,
        ),
      )
    } catch (error) {
      window.alert(
        `Could not delete the subtask: ${error instanceof Error ? error.message : "unknown error"}`,
      )
    }
  }

  async function deleteDomainById(id: string) {
    // Deleting a domain cascades to every task, subtask and session under it,
    // so this one spells that out.
    if (!window.confirm("Delete this domain? Its tasks, subtasks and study sessions go with it.")) return

    try {
      await removeDomain(id)

      // Drop the local copies too, so the list does not wait for a reload.
      setTasks((prev) => prev.filter((t) => t.domainId !== id))
      setActiveDomain((prev) => (prev === id ? null : prev))
    } catch (error) {
      window.alert(
        `Could not delete the domain: ${error instanceof Error ? error.message : "unknown error"}`,
      )
    }
  }

  // Fall back to zeroes so the page renders before analytics arrives.
  const totalMinutesThisWeek = analytics ? Math.round(analytics.hoursPerWeek * 60) : 0
  const streakDays = analytics?.streak ?? 0
  const weeklyGoalMinutes = 900

  const hours = Math.floor(totalMinutesThisWeek / 60)
  const mins = totalMinutesThisWeek % 60

  return (
    <div className="flex flex-col gap-6">
      {/* ---------------- greeting + live clock ---------------- */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
            Hey {user?.name?.split(" ")[0]}
          </h1>
          <p className="mt-1 flex flex-wrap items-baseline gap-x-2 text-sm text-muted">
            <span className="tabular-nums">{dateStr}</span>
            <span className="text-faint" aria-hidden="true">
              ·
            </span>
            <span className="font-medium tabular-nums text-ink">{timeStr}</span>
          </p>
          <p className="mt-0.5 text-xs text-faint">
            {done} of {tasks.length} tasks cleared. {streakDays} days in a row.
          </p>
        </div>
        <Pill tone="mint">{streakDays} day streak</Pill>
      </div>

      {/* ---------------- frog nudge ---------------- */}
      <FrogCard />

      {/* ---------------- stats ---------------- */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Time tracked this week"
          value={`${hours}h ${mins}m`}
          caption={`${Math.round((totalMinutesThisWeek / weeklyGoalMinutes) * 100)}% of goal`}
        />
        <StatCard label="Current streak" value={`${streakDays} days`} caption="Building momentum" />
        <StatCard
          label="Overdue"
          value={`${analytics?.overdueCount ?? 0}`}
          caption="Tasks past their due date"
        />
      </div>

      {/* ---------------- domains ---------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-ink">Your domains</h2>
          <Button variant="ghost" size="sm" onClick={() => setAddingDomain((v) => !v)}>
            <Plus size={14} /> New domain
          </Button>
        </div>

        {addingDomain && (
          <Card className="flex flex-col gap-3">
            <Field
              label="Domain name"
              placeholder="e.g. Operating Systems"
              value={newDomainName}
              onChange={(e) => setNewDomainName(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={commitDomain} disabled={!newDomainName.trim()}>
                Add domain
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setAddingDomain(false)
                  setNewDomainName("")
                }}
              >
                Cancel
              </Button>
            </div>
          </Card>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {domains.map((d) => {
            const isActive = activeDomain === d.id
            const share = totalMinutes === 0 ? 0 : d.minutesThisWeek / totalMinutes
            return (
              // A div (not a button) because the delete control inside it is
              // itself a button, and nested buttons are invalid HTML.
              // role/tabIndex/onKeyDown keep it keyboard-accessible.
              <div
                key={d.id}
                role="button"
                tabIndex={0}
                onClick={() => setActiveDomain(isActive ? null : d.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    setActiveDomain(isActive ? null : d.id)
                  }
                }}
                className={cx(
                  "group relative cursor-pointer rounded-[var(--radius-card)] border p-4 text-left transition-all",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-soft/60",
                  isActive
                    ? "border-violet-soft/60 bg-elevated"
                    : "border-line bg-surface hover:border-violet-soft/30 hover:bg-elevated",
                )}
              >
                {/* Revealed on hover or keyboard focus so the card stays clean. */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteDomainById(d.id)
                  }}
                  aria-label={`Delete ${d.name}`}
                  title="Delete domain"
                  className={cx(
                    "absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-md text-faint",
                    "opacity-0 transition-opacity hover:bg-danger/15 hover:text-danger",
                    "group-hover:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-danger/50",
                  )}
                >
                  <X size={13} strokeWidth={2.5} />
                </button>

                <div className="flex items-center justify-between gap-3 pr-6">
                  <span className="font-display text-[15px] font-medium text-ink">{d.name}</span>
                  <span className="shrink-0 text-xs tabular-nums text-faint">
                    {Math.floor(d.minutesThisWeek / 60)}h {d.minutesThisWeek % 60}m
                  </span>
                </div>
                <StackBar
                  progress={share}
                  colour={d.colour === "mint" ? "bg-mint" : d.colour === "violet-soft" ? "bg-violet-soft" : "bg-violet"}
                  className="mt-3"
                />
                <span className="mt-2 block text-xs text-faint">
                  {tasks.filter((t) => t.domainId === d.id && !t.completed).length} open tasks
                </span>
              </div>
            )
          })}
        </div>
      </section>

      {/* ---------------- tasks ---------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-base font-semibold text-ink">
            {activeDomain ? domains.find((d) => d.id === activeDomain)?.name : "All tasks"}
          </h2>
          <div className="flex items-center gap-2">
            {activeDomain && (
              <Button variant="ghost" size="sm" onClick={() => setActiveDomain(null)}>
                Clear filter
              </Button>
            )}
            <Button size="sm" onClick={openAddTask}>
              <Plus size={14} /> Add task
            </Button>
          </div>
        </div>

        {addingTask && (
          <Card className="flex flex-col gap-3">
            <Field
              label="Task"
              placeholder="e.g. Finish the problem set"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              autoFocus
            />

            {!activeDomain && (
              <div className="flex flex-col gap-1.5">
                <label htmlFor="task-domain" className="text-xs font-medium text-faint">
                  Domain
                </label>
                <select
                  id="task-domain"
                  value={newDomainId}
                  onChange={(e) => setNewDomainId(e.target.value)}
                  className="h-11 rounded-xl border border-line bg-elevated px-3.5 text-sm text-ink focus:border-violet-soft/60 focus:outline-none"
                >
                  {domains.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <Field
                label="Due date (optional)"
                type="date"
                value={newDue}
                onChange={(e) => setNewDue(e.target.value)}
              />
              <div className="flex flex-col gap-1.5">
                <label className="flex items-center gap-2 text-xs font-medium text-faint">
                  <input
                    type="checkbox"
                    checked={newRemind}
                    onChange={(e) => setNewRemind(e.target.checked)}
                    className="h-4 w-4 rounded border-line bg-elevated accent-[var(--color-violet)]"
                  />
                  Remind me on this date at this time
                </label>
                <input
                  type="datetime-local"
                  value={newRemindAt}
                  onChange={(e) => setNewRemindAt(e.target.value)}
                  disabled={!newRemind}
                  aria-label="Reminder date and time"
                  className="h-11 rounded-xl border border-line bg-elevated px-3.5 text-sm text-ink disabled:opacity-45 focus:border-violet-soft/60 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <Button size="sm" onClick={commitTask} disabled={!newTitle.trim()}>
                Add task
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setAddingTask(false)}>
                Cancel
              </Button>
            </div>
          </Card>
        )}

        <Card className="flex flex-col gap-1 p-2">
          {visible.length === 0 && <p className="p-4 text-center text-sm text-faint">Nothing here. Enjoy the quiet.</p>}

          {visible.map((t) => {
            const isOpen = expanded.includes(t.id)
            const domainName = domains.find((d) => d.id === t.domainId)?.name
            return (
              <div key={t.id} className="group/task rounded-xl transition-colors hover:bg-elevated">
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3">
                    {/* Real checkbox control — styled visually, bound to the task state. */}
                    <input
                      type="checkbox"
                      checked={t.completed}
                      onChange={() => toggleTask(t.id)}
                      aria-label={`Mark ${t.title} complete`}
                      className="peer sr-only"
                    />
                    <span
                      aria-hidden="true"
                      className={cx(
                        "grid h-[18px] w-[18px] shrink-0 place-items-center rounded-md border transition-colors",
                        "border-line peer-checked:border-violet peer-checked:bg-violet peer-checked:text-ink",
                      )}
                    >
                      {t.completed && <Check size={12} strokeWidth={3} />}
                    </span>
                    <span
                      className={cx(
                        "min-w-0 truncate text-sm transition-colors",
                        t.completed ? "text-faint line-through" : "text-ink",
                      )}
                    >
                      {t.title}
                    </span>
                  </label>

                  {t.dueDate && (
                    <span className="hidden shrink-0 items-center gap-1 rounded-full border border-line bg-elevated px-2 py-0.5 text-xs text-faint sm:flex">
                      <CalendarDays size={12} aria-hidden="true" />
                      {formatDue(t.dueDate)}
                    </span>
                  )}

                  {t.remindAt && (
                    <span className="hidden shrink-0 items-center gap-1 rounded-full border border-line bg-elevated px-2 py-0.5 text-xs text-faint sm:flex">
                      <Bell size={12} aria-hidden="true" />
                      {formatReminder(t.remindAt)}
                    </span>
                  )}

                  <span className="hidden shrink-0 text-xs text-faint md:block">{domainName}</span>

                  <button
                    type="button"
                    onClick={() => deleteTaskById(t.id)}
                    aria-label={`Delete ${t.title}`}
                    title="Delete task"
                    className={cx(
                      "grid h-7 w-7 shrink-0 place-items-center rounded-lg text-faint",
                      "opacity-0 transition-opacity hover:bg-danger/15 hover:text-danger",
                      "group-hover/task:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-danger/50",
                    )}
                  >
                    <X size={14} strokeWidth={2.5} />
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleExpanded(t.id)}
                    aria-expanded={isOpen}
                    aria-label={`${isOpen ? "Collapse" : "Expand"} subtasks for ${t.title}`}
                    className="grid h-7 w-7 shrink-0 place-items-center rounded-lg text-faint transition-colors hover:bg-elevated hover:text-ink"
                  >
                    <ChevronDown size={16} className={cx("transition-transform", isOpen && "rotate-180")} />
                  </button>
                </div>

                {isOpen && (
                  <div className="ml-[38px] mr-3 flex flex-col gap-0.5 border-l border-line pb-1 pl-3">
                    {t.subtasks.map((st) => (
                      <div
                        key={st.id}
                        className="group/sub flex items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-elevated"
                      >
                        {/* The label covers only the checkbox and title, so the
                            delete button beside it does not toggle completion. */}
                        <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5">
                          <input
                            type="checkbox"
                            checked={st.completed}
                            onChange={() => toggleSubtask(t.id, st.id)}
                            aria-label={`Mark ${st.title} complete`}
                            className="peer sr-only"
                          />
                          <span
                            aria-hidden="true"
                            className={cx(
                              "grid h-4 w-4 shrink-0 place-items-center rounded border transition-colors",
                              "border-line peer-checked:border-violet peer-checked:bg-violet peer-checked:text-ink",
                            )}
                          >
                            {st.completed && <Check size={10} strokeWidth={3} />}
                          </span>
                          <span className={cx("min-w-0 flex-1 truncate text-sm", st.completed ? "text-faint line-through" : "text-ink")}>
                            {st.title}
                          </span>
                        </label>

                        <button
                          type="button"
                          onClick={() => deleteSubtaskById(t.id, st.id)}
                          aria-label={`Delete subtask ${st.title}`}
                          title="Delete subtask"
                          className={cx(
                            "grid h-5 w-5 shrink-0 place-items-center rounded text-faint",
                            "opacity-0 transition-opacity hover:bg-danger/15 hover:text-danger",
                            "group-hover/sub:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-danger/50",
                          )}
                        >
                          <X size={11} strokeWidth={3} />
                        </button>
                      </div>
                    ))}

                    {subtaskFor === t.id ? (
                      <form
                        onSubmit={(e) => {
                          e.preventDefault()
                          commitSubtask(t.id)
                        }}
                        className="flex items-center gap-2 py-1.5 pl-2"
                      >
                        <input
                          autoFocus
                          value={subtaskTitle}
                          onChange={(e) => setSubtaskTitle(e.target.value)}
                          placeholder="Subtask title"
                          aria-label="Subtask title"
                          className="h-8 min-w-0 flex-1 rounded-lg border border-line bg-elevated px-2.5 text-sm text-ink focus:border-violet-soft/60 focus:outline-none"
                        />
                        <Button type="submit" size="sm" disabled={!subtaskTitle.trim()}>
                          Add
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSubtaskFor(null)
                            setSubtaskTitle("")
                          }}
                        >
                          Cancel
                        </Button>
                      </form>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setSubtaskFor(t.id)
                          setSubtaskTitle("")
                        }}
                        className="flex items-center gap-1.5 self-start rounded-lg px-2 py-1.5 text-xs text-faint transition-colors hover:bg-elevated hover:text-ink"
                      >
                        <Plus size={12} /> Add subtask
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </Card>
      </section>
    </div>
  )
}
