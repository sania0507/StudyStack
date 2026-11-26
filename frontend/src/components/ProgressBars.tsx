import type { DomainProgress } from "@/api/client"

/*
  ============================================================
  ProgressBars — how far through each domain you actually are
  ============================================================
  One bar per domain, sorted by percentage so the thing you
  are furthest through sits at the top.

  The percentage is subtask-based: University → Compiler Design
  → { Introduction, LR0, SLR, CLR, LALR } means finishing four
  of those five topics is 80%, not "0 of 1 subjects done".

  A domain with no subtasks at all falls back to counting its
  tasks, so a plain to-do list still moves the bar.
*/

/** Sort highest-completion first; ties keep a stable, alphabetical order. */
function byProgress(domains: DomainProgress[]) {
  return [...domains].sort(
    (a, b) => b.completionPercent - a.completionPercent || a.name.localeCompare(b.name),
  )
}

/** "4/5 topics" for subtask-tracked domains, "2/3 tasks" otherwise. */
function unitLabel(entry: DomainProgress) {
  if (entry.totalSubtasks > 0) {
    return {
      done: entry.completedSubtasks,
      total: entry.totalSubtasks,
      noun: entry.totalSubtasks === 1 ? "topic" : "topics",
    }
  }

  return {
    done: entry.completedTasks,
    total: entry.totalTasks,
    noun: entry.totalTasks === 1 ? "task" : "tasks",
  }
}

export default function ProgressBars({ domains }: { domains: DomainProgress[] }) {
  if (domains.length === 0) {
    return <p className="text-sm text-muted">No domains yet.</p>
  }

  const ordered = byProgress(domains)

  return (
    <div className="flex flex-col gap-5">
      {ordered.map((domain) => {
        const { done, total, noun } = unitLabel(domain)
        const pct = Math.min(100, Math.max(0, domain.completionPercent))

        return (
          <div key={domain.domainId} className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between gap-3">
              <span className="truncate text-sm text-ink">{domain.name}</span>
              <span className="shrink-0 text-xs tabular-nums text-faint">
                {total > 0 ? `${done}/${total} ${noun}` : "no tasks yet"}
              </span>
            </div>

            {/* The track is the full width; the fill is the percentage.
                role + aria-label so the number is available without colour. */}
            <div
              className="h-2.5 w-full overflow-hidden rounded-full bg-elevated"
              role="img"
              aria-label={`${domain.name}: ${pct}% complete (${done} of ${total} ${noun})`}
            >
              <div
                className="h-full rounded-full bg-violet transition-[width] duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>

            <div className="flex items-baseline justify-between gap-3">
              <span className="text-xs text-faint">
                {domain.totalSubtasks > 0
                  ? `${domain.completedTasks}/${domain.totalTasks} subjects finished`
                  : " "}
              </span>
              <span className="text-xs font-medium tabular-nums text-violet-soft">
                {pct % 1 === 0 ? pct.toFixed(0) : pct.toFixed(1)}%
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
