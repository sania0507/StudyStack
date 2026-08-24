import { useState } from "react"
import { Check, Plus } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { domains, tasks as seedTasks, stats } from "@/api/mock"
import { Button, Card, Pill, StatCard, cx } from "@/components/ui"

/*
  ============================================================
  Dashboard — domains + tasks, with real interactivity
  ============================================================
  New idea here: DERIVED state.

  I keep ONE piece of state (`tasks`). Everything else — the
  filtered list, the completed count, the progress percentage —
  is CALCULATED from it during render. I don't store those in
  useState, because then I'd have two sources of truth that can
  disagree.

  Rule of thumb: if you can compute it from existing state,
  compute it. Don't store it.
*/
export default function Dashboard() {
  const { user } = useAuth()

  // Copy the mock array into state so we can toggle checkboxes.
  const [tasks, setTasks] = useState(seedTasks)
  const [activeDomain, setActiveDomain] = useState<string | null>(null)

  // --- derived values: recalculated on every render, never stored ---
  const visible = activeDomain ? tasks.filter((t) => t.domainId === activeDomain) : tasks
  const done = tasks.filter((t) => t.completed).length
  const totalMinutes = domains.reduce((sum, d) => sum + d.minutesThisWeek, 0)

  function toggleTask(id: string) {
    // .map() returns a NEW array with one item replaced — immutable update.
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t)))
  }

  const hours = Math.floor(stats.deepWorkThisMonth / 60)
  const mins = stats.deepWorkThisMonth % 60

  return (
    <div className="flex flex-col gap-6">
      {/* ---------------- greeting ---------------- */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
            Hey {user?.name?.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {done} of {tasks.length} tasks cleared. {stats.streakDays} days without breaking the chain.
            
          </p>
        </div>
        <Pill tone="mint">{stats.streakDays} day streak</Pill>
      </div>

      {/* ---------------- stats ---------------- */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Deep work this month"
          value={`${hours}h ${mins}m`}
          caption={`${Math.round((stats.deepWorkThisMonth / stats.weeklyGoalMinutes) * 100)}% of goal`}
          progress={stats.deepWorkThisMonth / stats.weeklyGoalMinutes}
        />
        <StatCard
          label="Current streak"
          value={`${stats.streakDays} days`}
          caption="Building momentum"
          progress={Math.min(1, stats.streakDays / 50)}
        />
        <StatCard
          label="Missed this week"
          value={`${stats.missedThisWeek} / 7`}
          caption={`${7 - stats.missedThisWeek} days with sessions`}
          progress={(7 - stats.missedThisWeek) / 7}
        />
      </div>

      {/* ---------------- domains ---------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-ink">Your domains</h2>
          <Button variant="ghost" size="sm">
            <Plus size={14} /> New domain
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {domains.map((d) => {
            const isActive = activeDomain === d.id
            const share = totalMinutes === 0 ? 0 : d.minutesThisWeek / totalMinutes
            return (
              // Clicking a domain filters the task list below. One state change,
              // two parts of the UI react to it.
              <button
                key={d.id}
                onClick={() => setActiveDomain(isActive ? null : d.id)}
                className={cx(
                  "rounded-[var(--radius-card)] border p-4 text-left transition-all",
                  isActive
                    ? "border-violet-soft/60 bg-elevated"
                    : "border-line bg-surface hover:border-violet-soft/30 hover:bg-elevated",
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-display text-[15px] font-medium text-ink">{d.name}</span>
                  <span className="shrink-0 text-xs tabular-nums text-faint">
                    {Math.floor(d.minutesThisWeek / 60)}h {d.minutesThisWeek % 60}m
                  </span>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-base">
                  <div
                    className={cx(
                      "h-full rounded-full transition-[width] duration-700",
                      d.colour === "mint" ? "bg-mint" : d.colour === "violet-soft" ? "bg-violet-soft" : "bg-violet",
                    )}
                    style={{ width: `${share * 100}%` }}
                  />
                </div>
                <span className="mt-2 block text-xs text-faint">
                  {tasks.filter((t) => t.domainId === d.id && !t.completed).length} open tasks
                </span>
              </button>
            )
          })}
        </div>
      </section>

      {/* ---------------- tasks ---------------- */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-base font-semibold text-ink">
            {activeDomain ? domains.find((d) => d.id === activeDomain)?.name : "All tasks"}
          </h2>
          {activeDomain && (
            <Button variant="ghost" size="sm" onClick={() => setActiveDomain(null)}>
              Clear filter
            </Button>
          )}
        </div>

        <Card className="flex flex-col gap-1 p-2">
          {visible.length === 0 && <p className="p-4 text-center text-sm text-faint">Nothing here. Enjoy the quiet.</p>}

          {visible.map((t) => (
            <button
              key={t.id}
              onClick={() => toggleTask(t.id)}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-elevated"
            >
              {/* Custom checkbox: a span we style ourselves. */}
              <span
                className={cx(
                  "grid h-[18px] w-[18px] shrink-0 place-items-center rounded-md border transition-colors",
                  t.completed ? "border-violet bg-violet text-ink" : "border-line",
                )}
                aria-hidden="true"
              >
                {t.completed && <Check size={12} strokeWidth={3} />}
              </span>

              <span
                className={cx(
                  "min-w-0 flex-1 truncate text-sm transition-colors",
                  t.completed ? "text-faint line-through" : "text-ink",
                )}
              >
                {t.title}
              </span>

              <span className="hidden shrink-0 text-[11px] text-faint sm:block">
                {domains.find((d) => d.id === t.domainId)?.name}
              </span>
            </button>
          ))}
        </Card>
      </section>
    </div>
  )
}
