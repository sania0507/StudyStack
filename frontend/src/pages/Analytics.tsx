import { useEffect, useState } from "react"
import { Avatar, Card, StatCard, StackBar } from "@/components/ui"
import Heatmap from "@/components/Heatmap"
import { useAuth } from "@/context/AuthContext"
import * as api from "@/api/client"
import type { Domain, Session } from "@/api/types"

/*
  ============================================================
  Analytics — read-only reporting
  ============================================================
  No interactivity beyond loading, so the only state is the
  fetched data. All the arithmetic lives in helper functions
  below the component rather than inside JSX.
*/

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

function formatMinutes(total: number) {
  const h = Math.floor(total / 60)
  const m = total % 60
  return h === 0 ? `${m}m` : `${h}h ${m}m`
}

// `now` is a real timestamp here — the old version was pinned to a demo date.
function timeAgo(iso: string) {
  const then = new Date(iso).getTime()
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000))
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.round(hrs / 24)}d ago`
}

function formatDay(iso: string) {
  const [, m, d] = iso.split("-")
  return `${MONTHS_SHORT[Number(m) - 1]} ${Number(d)}`
}

export default function Analytics() {
  const { user } = useAuth()

  const [summary, setSummary] = useState<api.AnalyticsSummary | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [domains, setDomains] = useState<Domain[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [analytics, recent, domainList] = await Promise.all([
          api.getAnalytics(),
          api.getSessions(),
          api.getDomains(),
        ])

        setSummary(analytics)
        setSessions(recent)
        setDomains(domainList)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load analytics.")
      }
    }

    load()
  }, [])

  if (error) {
    return (
      <Card>
        <p className="text-sm text-danger">{error}</p>
      </Card>
    )
  }

  // Nothing to draw until the first response lands.
  if (!summary) {
    return (
      <Card>
        <p className="text-sm text-muted">Loading analytics…</p>
      </Card>
    )
  }

  const weekdayMinutes = summary.weekdayMinutes
  const peak = Math.max(1, ...weekdayMinutes.map((d) => d.minutes))
  // weekdayMinutes is one bucket per weekday across all history, not the
  // current Monday-to-Sunday. The real weekly figure comes from the backend.
  const weekMinutes = Math.round(summary.hoursPerWeek * 60)
  const weeklyGoalMinutes = 900

  // Most recent first, capped so the feed stays a feed.
  const recentSessions = [...sessions]
    .sort((a, b) => new Date(b.finishedAt).getTime() - new Date(a.finishedAt).getTime())
    .slice(0, 6)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Analytics</h1>
        <p className="mt-1 text-sm text-muted">Everything you&apos;ve stacked, laid out honestly.</p>
      </div>

      {/* ---------------- headline stats ---------------- */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Time tracked this week"
          value={formatMinutes(weekMinutes)}
          caption={`Goal ${formatMinutes(weeklyGoalMinutes)}`}
          progress={Math.min(1, weekMinutes / weeklyGoalMinutes)}
        />
        <StatCard
          label="Deep work streak"
          value={`${summary.streak} days`}
          caption="Building momentum"
          progress={Math.min(1, summary.streak / 50)}
          accent="ember"
        />
        <StatCard
          label="Overdue tasks"
          value={`${summary.overdueCount}`}
          caption="Incomplete and past due"
          accent="ember"
        />
      </div>

      {/* ---------------- heatmap ---------------- */}
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-base font-semibold text-ink">Days you showed up</h2>
        <Card>
          <Heatmap days={summary.heatmap} />
        </Card>
      </section>

      {/* ---------------- weekday bars + domain split ---------------- */}
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card className="flex flex-col gap-5">
          <div className="flex items-baseline justify-between">
            <h2 className="font-display text-base font-semibold text-ink">Time by weekday</h2>
            <span className="text-xs text-faint">{formatMinutes(weekMinutes)} this week</span>
          </div>

          {/* A bar chart built from divs. For anything more complex than
              this, reach for a charting library instead. */}
          <div className="flex h-40 items-end gap-2 sm:gap-3">
            {weekdayMinutes.map((d) => (
              <div key={d.day} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                <span className="text-xs tabular-nums text-faint">{d.minutes}</span>
                <div
                  className="w-full rounded-t-md bg-violet/80 transition-all duration-700 hover:bg-violet"
                  style={{ height: `${(d.minutes / peak) * 100}%` }}
                  role="img"
                  aria-label={`${d.day}: ${formatMinutes(d.minutes)}`}
                />
                <span className="text-xs text-faint">{d.day}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="flex flex-col gap-4">
          <h2 className="font-display text-base font-semibold text-ink">By domain</h2>

          {summary.domainCompletion.length === 0 ? (
            <p className="text-sm text-muted">No domains yet.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {summary.domainCompletion.map((d) => (
                <div key={d.domainId} className="flex flex-col gap-2">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm text-ink">{d.name}</span>
                    <span className="shrink-0 text-xs tabular-nums text-faint">
                      {d.completedTasks}/{d.totalTasks} done
                    </span>
                  </div>
                  <StackBar progress={d.completionPercent / 100} colour="bg-violet" />
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* ---------------- activity feed ---------------- */}
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-base font-semibold text-ink">Your activity</h2>
        <Card className="flex flex-col gap-1 p-2">
          {recentSessions.length === 0 ? (
            <p className="px-3 py-3 text-sm text-muted">
              No sessions yet — finish a timer block and it shows up here.
            </p>
          ) : (
            recentSessions.map((s) => {
              const domain = domains.find((d) => d.id === s.domainId)

              return (
                <div key={s.id} className="flex items-center gap-3 rounded-xl px-3 py-3">
                  <Avatar name={user?.name ?? "?"} url={user?.avatarUrl} size={30} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-ink">
                      You tracked {formatMinutes(s.minutes)} in{" "}
                      <span className="text-violet-soft">{domain?.name ?? "a deleted domain"}</span>
                    </p>
                    <p className="mt-0.5 text-xs text-faint">
                      {formatDay(s.finishedAt.slice(0, 10))} · {timeAgo(s.finishedAt)}
                    </p>
                  </div>
                </div>
              )
            })
          )}
        </Card>
      </section>
    </div>
  )
}
