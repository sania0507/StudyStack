import { cx } from "@/components/ui"

/*
  ============================================================
  Heatmap — a year of showing up, GitHub-contribution style
  ============================================================
  Two things count as showing up: minutes on the timer, and tasks finished.
  A day where you ticked off six tasks but never started a timer is still a
  day you worked, so the level takes the higher of the two scores rather than
  only looking at minutes.

  The layout trick: one CSS grid flowing in COLUMNS (grid-flow-col + 7 rows).
  Each column becomes a week, each row a weekday.
*/

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

// level 0..4 -> a colour. Darker shades at the low end, because on a
// near-black page a 25%-opacity purple is invisible.
const LEVEL_CLASS: Record<number, string> = {
  0: "bg-elevated",
  1: "bg-violet/40",
  2: "bg-violet/60",
  3: "bg-violet/80",
  4: "bg-violet",
}

const TASKS_PER_LEVEL = 3 // 3 tasks = level 1, 6 = level 2, 9 = level 3, 12 = level 4
const MINUTES_PER_LEVEL = 30

function levelForTasks(count: number): number {
  if (count <= 0) return 0
  return Math.min(4, Math.ceil(count / TASKS_PER_LEVEL))
}

function levelForMinutes(minutes: number): number {
  if (minutes <= 0) return 0
  return Math.min(4, Math.ceil(minutes / MINUTES_PER_LEVEL))
}

/** Effort is whichever signal is stronger: hours or tasks. */
function levelFor(day: HeatmapDay): number {
  return Math.max(levelForTasks(day.tasksCompleted), levelForMinutes(day.minutes))
}

type HeatmapDay = {
  date: string
  minutes: number
  tasksCompleted: number
}

export default function Heatmap({ days }: { days: HeatmapDay[] }) {
  const totalDays = days.length
  const activeDays = days.filter((d) => levelFor(d) > 0).length

  return (
    <div className="flex flex-col gap-3">
      <span className="sr-only">
        Days you showed up: activity on {activeDays} of {totalDays} days, from Less to More.
      </span>

      <div className="ml-8 flex min-w-[680px] justify-between pr-1 text-xs text-faint">
        {MONTHS.map((m) => (
          <span key={m}>{m}</span>
        ))}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        <div className="flex w-6 shrink-0 flex-col justify-between py-0.5 text-xs text-faint">
          <span>Sun</span>
          <span>Wed</span>
          <span>Fri</span>
        </div>

        <div
          role="img"
          aria-label="Days you showed up, one cell per day"
          className="grid min-w-[660px] grid-flow-col grid-rows-7 gap-1"
        >
          {days.map((d) => {
            const level = levelFor(d)
            const summary =
              d.minutes === 0 && d.tasksCompleted === 0
                ? "nothing tracked"
                : [
                    d.minutes > 0 ? `${d.minutes} min` : null,
                    d.tasksCompleted > 0
                      ? `${d.tasksCompleted} task${d.tasksCompleted === 1 ? "" : "s"}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(", ")

            return (
              <span
                key={d.date}
                title={`${d.date}: ${summary}`}
                aria-label={`${d.date}: ${summary}`}
                className={cx(
                  "h-3.5 w-3.5 rounded-[3px]",
                  LEVEL_CLASS[level],
                  level === 4 && "ring-1 ring-violet-soft/40",
                )}
              />
            )
          })}
        </div>
      </div>

      <div className="flex items-center justify-end gap-1.5 text-xs text-faint">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((l) => (
          <span key={l} className={cx("h-3.5 w-3.5 rounded-[3px]", LEVEL_CLASS[l])} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
