import { useEffect, useState } from "react"
import { Avatar, Card, StatCard } from "@/components/ui"
import Heatmap from "@/components/Heatmap"
import ProgressBars from "@/components/ProgressBars"
import WorkShareChart from "@/components/WorkShareChart"
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

/* A recorded block, from seconds. Short blocks read as minutes, not "0h 0m". */
function formatSeconds(total: number) {
  const hours = Math.floor(total / 3600)
  const minutes = Math.round((total % 3600) / 60)

  if (hours === 0) return `${Math.max(1, minutes)}m`
  if (minutes === 0) return `${hours}h`

  return `${hours}h ${minutes}m`
}

function formatMinutes(total: number) {
  const h = Math.floor(total / 60)
  const m = total % 60
  return h === 0 ? `${m}m` : `${h}h ${m}m`
}

/*
  Belt and braces for timestamps.

  `new Date("2026-11-26T12:30:00")` — no Z, no offset — is parsed as LOCAL time
  by every browser. When the API sent naive server timestamps, that made a
  session recorded seconds ago read as "6h ago" for anyone not on the server's
  clock. The backend now sends timestamptz, but an environment that has not yet
  run that migration still emits the naive form, so pin a missing offset to UTC
  rather than letting the browser guess.
*/
function parseTimestamp(iso: string): number {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso)
  return new Date(hasZone ? iso : `${iso}Z`).getTime()
}

function timeAgo(iso: string) {
  const then = parseTimestamp(iso)

  // Clamp at zero: a small clock difference must not print "-1 min ago".
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000))
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} min ago`

  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`

  return `${Math.round(hrs / 24)}d ago`
}

/** "Nov 26", from the same instant the relative label uses. */
function formatDay(iso: string) {
  const date = new Date(parseTimestamp(iso))
  return `${MONTHS_SHORT[date.getMonth()]} ${date.getDate()}`
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
        // Names come from each session's own snapshot, so this page no longer
        // has to fetch the task list just to label the feed.
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

  // Topics/tasks finished overall, and out of how many. Subtasks are the unit
  // where a domain has them, so "4 of 5 topics" is not flattened to "0 of 1".
  const totals = summary.domainCompletion.reduce(
    (acc, d) => {
      const done = d.totalSubtasks > 0 ? d.completedSubtasks : d.completedTasks
      const total = d.totalSubtasks > 0 ? d.totalSubtasks : d.totalTasks
      return { done: acc.done + done, total: acc.total + total }
    },
    { done: 0, total: 0 },
  )

  // Most recent first, capped so the feed stays a feed.
  const recentSessions = [...sessions]
    .sort((a, b) => parseTimestamp(b.finishedAt) - parseTimestamp(a.finishedAt))
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
          label="Topics finished"
          value={`${totals.done}`}
          caption={`of ${totals.total} across ${summary.domainCompletion.length} ${
            summary.domainCompletion.length === 1 ? "domain" : "domains"
          }`}
          progress={totals.total > 0 ? totals.done / totals.total : 0}
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

      {/* ---------------- progress bars + work share ---------------- */}
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card className="flex flex-col gap-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="font-display text-base font-semibold text-ink">Domain progress</h2>
            <span className="shrink-0 text-xs text-faint">{formatMinutes(weekMinutes)} this week</span>
          </div>

          <ProgressBars domains={summary.domainCompletion} />
        </Card>

        <Card className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="font-display text-base font-semibold text-ink">Where the work is going</h2>
            <p className="text-xs text-faint">Share of everything you&apos;ve finished</p>
          </div>

          <WorkShareChart domains={summary.domainCompletion} />
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

              // The snapshot is the truth: it was captured when the block was
              // recorded, so it still names a domain that has since been
              // deleted. The lookup is only a fallback for rows that predate it.
              const label = s.taskTitle ?? s.domainName ?? domain?.name

              return (
                <div key={s.id} className="flex items-center gap-3 rounded-xl px-3 py-3">
                  <Avatar name={user?.name ?? "?"} hasAvatar={Boolean(user?.avatarUrl)} size={30} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-ink">
                      You tracked {formatSeconds(s.durationSeconds)}
                      {" "}
                      {s.taskTitle ? "on" : "in"}{" "}
                      <span className="text-violet-soft">
                        {label ?? "a deleted domain"}
                      </span>
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
