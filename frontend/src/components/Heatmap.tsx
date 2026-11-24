import { cx } from "@/components/ui"

/*
  ============================================================
  Heatmap — a year of showing up, GitHub-contribution style
  ============================================================
  Two things count as showing up: minutes on the timer, and tasks finished.
  A day where you ticked off six tasks but never started a timer is still a
  day you worked, so the level takes the higher of the two scores.

  EVERY day in the window gets a cell, including days with no activity at
  all. An empty day is a cell at level 0, not a gap: a calendar with holes
  in it looks broken rather than quiet.

  THE ALIGNMENT TRICK: the window is padded at the front with blanks so the
  first real day sits on its true weekday, then chunked into weeks of seven.
  Without that padding the first column starts mid-week and every row label
  is a lie.

  Month labels are measured in weeks and drawn in a row above the grid, so
  they line up with the columns they describe instead of being spread evenly
  across the width.
*/

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

const CELL_PX = 14
const GAP_PX = 4
const WEEK_STRIDE = CELL_PX + GAP_PX

// level 0..4 -> a colour. The low end is still clearly purple, because on a
// near-black page a 25%-opacity fill is indistinguishable from empty.
const LEVEL_CLASS: Record<number, string> = {
  0: "bg-elevated",
  1: "bg-violet/40",
  2: "bg-violet/60",
  3: "bg-violet/80",
  4: "bg-violet",
}

const TASKS_PER_LEVEL = 3 // 3 tasks = level 1, 6 = level 2, 9 = level 3
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

/** Weekday of a YYYY-MM-DD string, 0 = Sunday. Parsed as local, not UTC. */
function weekdayOf(isoDate: string): number {
  const [y, m, d] = isoDate.split("-").map(Number)
  return new Date(y, m - 1, d).getDay()
}

type HeatmapDay = {
  date: string
  minutes: number
  tasksCompleted: number
}

export default function Heatmap({ days }: { days: HeatmapDay[] }) {
  // Pad the front so the first real day lands on its true weekday.
  const leadingBlanks = days.length > 0 ? weekdayOf(days[0].date) : 0

  const cells: (HeatmapDay | null)[] = [
    ...Array.from({ length: leadingBlanks }, () => null),
    ...days,
  ]

  const weeks: (HeatmapDay | null)[][] = []
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7))
  }

  // One label per month, anchored to the week that month starts in.
  const monthMarks: { label: string; week: number }[] = []

  weeks.forEach((week, weekIndex) => {
    const first = week.find((day) => day !== null)
    if (!first) return

    const [, month] = first.date.split("-")
    const label = MONTHS[Number(month) - 1]
    const previous = monthMarks[monthMarks.length - 1]

    if (!previous || previous.label !== label) {
      monthMarks.push({ label, week: weekIndex })
    }
  })

  const totalDays = days.length
  const activeDays = days.filter((d) => levelFor(d) > 0).length
  const gridWidth = weeks.length * WEEK_STRIDE

  return (
    <div className="flex flex-col gap-3">
      <span className="sr-only">
        Days you showed up: activity on {activeDays} of {totalDays} days, from Less to More.
      </span>

      <div className="overflow-x-auto pb-1">
        <div className="flex gap-2">
          {/* weekday rail */}
          <div
            className="flex w-6 shrink-0 flex-col justify-between text-xs text-faint"
            style={{ height: 7 * WEEK_STRIDE - GAP_PX, paddingTop: 18 }}
            aria-hidden="true"
          >
            <span>Sun</span>
            <span>Wed</span>
            <span>Fri</span>
          </div>

          <div className="shrink-0">
            {/* Month labels sit in their own row, positioned by week so each
                one lines up with the columns below it. */}
            <div className="relative mb-1 h-4" style={{ width: gridWidth }}>
              {monthMarks.map((mark, index) => {
                const next = monthMarks[index + 1]
                const spanPx = next
                  ? (next.week - mark.week) * WEEK_STRIDE
                  : gridWidth - mark.week * WEEK_STRIDE

                return (
                  <span
                    key={`${mark.label}-${mark.week}`}
                    className="absolute top-0 overflow-hidden whitespace-nowrap text-xs text-faint"
                    style={{ left: mark.week * WEEK_STRIDE, width: spanPx }}
                  >
                    {mark.label}
                  </span>
                )
              })}
            </div>

            <div
              role="img"
              aria-label={`Days you showed up: one cell per day for ${totalDays} days`}
              className="grid grid-flow-col grid-rows-7 gap-1"
              style={{ gridTemplateColumns: `repeat(${weeks.length}, ${CELL_PX}px)` }}
            >
              {cells.map((day, index) => {
                if (!day) {
                  // Blank before the window starts: keeps rows aligned without
                  // inventing a day that has no data behind it.
                  return <span key={`blank-${index}`} aria-hidden="true" />
                }

                const level = levelFor(day)
                const summary =
                  day.minutes === 0 && day.tasksCompleted === 0
                    ? "nothing tracked"
                    : [
                        day.minutes > 0 ? `${day.minutes} min` : null,
                        day.tasksCompleted > 0
                          ? `${day.tasksCompleted} task${day.tasksCompleted === 1 ? "" : "s"}`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(", ")

                return (
                  <span
                    key={day.date}
                    title={`${day.date}: ${summary}`}
                    aria-label={`${day.date}: ${summary}`}
                    className={cx(
                      "rounded-[3px]",
                      LEVEL_CLASS[level],
                      level === 4 && "ring-1 ring-violet-soft/40",
                    )}
                    style={{ width: CELL_PX, height: CELL_PX }}
                  />
                )
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end gap-1.5 text-xs text-faint">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((l) => (
          <span
            key={l}
            className={cx("rounded-[3px]", LEVEL_CLASS[l])}
            style={{ width: CELL_PX, height: CELL_PX }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
