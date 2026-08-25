import { recentSessions, stats, weekdayMinutes } from "@/api/mock"
import { Avatar, Card, StatCard, StackBar } from "@/components/ui"
import Heatmap from "@/components/Heatmap"
import { useAuth } from "@/context/AuthContext"
import { useDomains } from "@/context/DomainsContext"

/*
  ============================================================
  Analytics — read-only reporting
  ============================================================
  Zero useState in this whole file. It takes data in and draws
  it. When a page has no interactivity, don't invent any.

  Two small helpers at the top: extracting `formatMinutes` and
  `timeAgo` keeps the JSX below readable. If you find yourself
  writing maths inside JSX, pull it out into a function.
*/

function formatMinutes(total: number) {
  const h = Math.floor(total / 60)
  const m = total % 60
  return h === 0 ? `${m}m` : `${h}h ${m}m`
}

function timeAgo(iso: string) {
  const then = new Date(iso).getTime()
  const now = new Date("2026-08-25T10:00:00Z").getTime() // fixed "now" for the demo
  const mins = Math.round((now - then) / 60000)
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.round(hrs / 24)}d ago`
}

export default function Analytics() {
  const { user } = useAuth()
  const { domains } = useDomains()
  const peak = Math.max(...weekdayMinutes.map((d) => d.minutes))
  const totalWeek = weekdayMinutes.reduce((s, d) => s + d.minutes, 0)
  const domainTotal = domains.reduce((s, d) => s + d.minutesThisWeek, 0)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Analytics</h1>
        <p className="mt-1 text-sm text-muted">Everything you&apos;ve stacked, laid out honestly.</p>
      </div>

      {/* ---------------- headline stats ---------------- */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Deep work this month"
          value={formatMinutes(stats.deepWorkThisMonth)}
          caption={`Goal ${formatMinutes(stats.weeklyGoalMinutes)}`}
          progress={stats.deepWorkThisMonth / stats.weeklyGoalMinutes}
        />
        <StatCard
          label="Deep work streak"
          value={`${stats.streakDays} days`}
          caption="Building momentum"
          progress={Math.min(1, stats.streakDays / 50)}
        />
        <StatCard
          label="Days with sessions"
          value={`${7 - stats.missedThisWeek} / 7`}
          caption={`${7 - stats.missedThisWeek} days with sessions this week`}
          progress={(7 - stats.missedThisWeek) / 7}
        />
      </div>

      {/* ---------------- heatmap ---------------- */}
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-base font-semibold text-ink">Days you showed up</h2>
        <Card>
          <Heatmap />
        </Card>
      </section>

      {/* ---------------- weekday bars + domain split ---------------- */}
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card className="flex flex-col gap-5">
          <div className="flex items-baseline justify-between">
            <h2 className="font-display text-base font-semibold text-ink">This week</h2>
            <span className="text-xs text-faint">{formatMinutes(totalWeek)} total</span>
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
          <div className="flex flex-col gap-4">
            {domains.map((d) => {
              const share = domainTotal === 0 ? 0 : d.minutesThisWeek / domainTotal
              return (
                <div key={d.id} className="flex flex-col gap-2">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm text-ink">{d.name}</span>
                    <span className="shrink-0 text-xs tabular-nums text-faint">{Math.round(share * 100)}%</span>
                  </div>
                  <StackBar
                    progress={share}
                    colour={d.colour === "mint" ? "bg-mint" : d.colour === "violet-soft" ? "bg-violet-soft" : "bg-violet"}
                  />
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {/* ---------------- activity feed ---------------- */}
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-base font-semibold text-ink">Your activity</h2>
        <Card className="flex flex-col gap-1 p-2">
          {recentSessions.map((s) => (
            <div key={s.id} className="flex items-center gap-3 rounded-xl px-3 py-3">
              <Avatar name={user?.name ?? "?"} url={user?.avatarUrl} size={30} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-ink">
                  You completed {formatMinutes(s.minutes)} of deep work in{" "}
                  <span className="text-violet-soft">{domains.find((d) => d.id === s.domainId)?.name}</span>
                </p>
                <p className="mt-0.5 text-xs text-faint">{timeAgo(s.finishedAt)}</p>
              </div>
            </div>
          ))}
        </Card>
      </section>
    </div>
  )
}
