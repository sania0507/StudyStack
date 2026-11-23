import { cx } from "@/components/ui"

/*
  ============================================================
  Heatmap — a year of focus, GitHub-contribution style
  ============================================================
  The layout trick: one CSS grid flowing in COLUMNS
  (grid-flow-col + 7 rows). Each column becomes a week, each
  row a weekday. Feed it a flat array of days and the grid
  arranges itself — no manual week-chunking needed.

  Data now comes from the analytics service as real minutes
  per day, so this component converts minutes into a level
  instead of receiving levels directly.
*/

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

// level 0..4 -> a colour. Kept as a lookup object instead of nested ternaries.
const LEVEL_CLASS: Record<number, string> = {
  0: "bg-elevated",
  1: "bg-violet/25",
  2: "bg-violet/45",
  3: "bg-violet/70",
  4: "bg-violet",
}

// Minutes are unbounded, levels are 0..4, so bucket them.
function levelForMinutes(minutes: number): number {
  if (minutes <= 0) return 0
  if (minutes < 30) return 1
  if (minutes < 60) return 2
  if (minutes < 120) return 3
  return 4
}

type HeatmapDay = {
  date: string
  minutes: number
}

export default function Heatmap({ days }: { days: HeatmapDay[] }) {
  // Screen-reader summary derived from the data, so the chart isn't purely visual.
  const totalDays = days.length
  const activeDays = days.filter((d) => d.minutes > 0).length

  return (
    <div className="flex flex-col gap-3">
      {/* off-screen text summary of the period */}
      <span className="sr-only">
        Days you showed up: sessions on {activeDays} of {totalDays} days, from Less to More.
      </span>

      {/* month labels — evenly spread, indicative rather than pixel-exact */}
      <div className="ml-8 flex min-w-[680px] justify-between pr-1 text-xs text-faint">
        {MONTHS.map((m) => (
          <span key={m}>{m}</span>
        ))}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {/* weekday labels down the left */}
        <div className="flex w-6 shrink-0 flex-col justify-between py-[1px] text-xs text-faint">
          <span>Sun</span>
          <span>Wed</span>
          <span>Fri</span>
        </div>

        <div
          role="img"
          aria-label="Days you showed up, one cell per day"
          className="grid min-w-[660px] grid-flow-col grid-rows-7 gap-[3px]"
        >
          {days.map((d) => {
            const level = levelForMinutes(d.minutes)

            return (
              <span
                key={d.date}
                title={`${d.date}: ${d.minutes === 0 ? "no sessions" : `${d.minutes} min`}`}
                aria-label={`${d.date}: ${d.minutes === 0 ? "no sessions" : `${d.minutes} minutes`}`}
                className={cx("h-[11px] w-[11px] rounded-[2.5px]", LEVEL_CLASS[level])}
              />
            )
          })}
        </div>
      </div>

      {/* legend */}
      <div className="flex items-center justify-end gap-1.5 text-xs text-faint">
        <span>Less</span>
        {[0, 1, 2, 3, 4].map((l) => (
          <span key={l} className={cx("h-[11px] w-[11px] rounded-[2.5px]", LEVEL_CLASS[l])} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
