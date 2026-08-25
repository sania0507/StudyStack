import { heatmap } from "@/api/mock"
import { cx } from "@/components/ui"

/*
  ============================================================
  Heatmap — a year of focus, GitHub-contribution style
  ============================================================
  The layout trick: one CSS grid flowing in COLUMNS
  (grid-flow-col + 7 rows). Each column becomes a week, each
  row a weekday. Feed it a flat array of days and the grid
  arranges itself — no manual week-chunking needed.

  We render ~53 weeks. On narrow screens the container scrolls
  horizontally rather than squashing the squares.
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

export default function Heatmap() {
  // Screen-reader summary derived from the data, so the chart isn't purely visual.
  const totalDays = heatmap.length
  const activeDays = heatmap.filter((d) => d.level > 0).length

  return (
    <div className="flex flex-col gap-3">
      {/* off-screen text summary of the year */}
      <span className="sr-only">
        Days you showed up: sessions on {activeDays} of {totalDays} days in the past year, from Less to More.
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
          {heatmap.map((d) => (
            <span
              key={d.date}
              title={`${d.date}: ${d.level === 0 ? "no sessions" : `level ${d.level}`}`}
              aria-label={`${d.date}: ${d.level === 0 ? "no sessions" : `level ${d.level}`}`}
              className={cx("h-[11px] w-[11px] rounded-[2.5px]", LEVEL_CLASS[d.level])}
            />
          ))}
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
