import type { DomainProgress } from "@/api/client"

/*
  ============================================================
  WorkShareChart — where the effort is going
  ============================================================
  A donut whose segments are each domain's *share of the work
  done*. If University has 12 subtasks ticked and Gym has 3,
  University is 80% of the ring.

  Why share-of-done and not share-of-progress: the bars beside
  this already show how complete each domain is. This one
  answers a different question — "which domain am I putting the
  most work into?" — so it must be weighted by work completed,
  not by percentage. A domain at 100% of three tiny tasks should
  not outrank one at 40% of forty.

  Built from a single SVG circle per segment, using
  strokeDasharray/strokeDashoffset. No charting dependency:
  two circles of arithmetic is cheaper than a library.
*/

/** Segments are shaded from one hue so they read as one family. */
const SHADES = [
  "var(--color-violet)",
  "var(--color-violet-soft)",
  "var(--color-mint)",
  "oklch(0.66 0.18 330)",
  "oklch(0.62 0.16 265)",
  "oklch(0.72 0.14 200)",
  "oklch(0.7 0.12 120)",
]

const RADIUS = 60
const STROKE = 22
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

type Slice = {
  domainId: string
  name: string
  /** Units of work done: subtasks where they exist, otherwise tasks. */
  units: number
  percent: number
  colour: string
  /** How complete that domain is, shown in the legend. */
  domainPercent: number
}

function workDone(entry: DomainProgress) {
  return entry.totalSubtasks > 0 ? entry.completedSubtasks : entry.completedTasks
}

function buildSlices(domains: DomainProgress[]): Slice[] {
  const done = domains
    .map((entry) => ({ entry, units: workDone(entry) }))
    .filter((item) => item.units > 0)

  const total = done.reduce((sum, item) => sum + item.units, 0)

  if (total === 0) return []

  return done
    .sort((a, b) => b.units - a.units)
    .map((item, index) => ({
      domainId: item.entry.domainId,
      name: item.entry.name,
      units: item.units,
      percent: (item.units / total) * 100,
      colour: SHADES[index % SHADES.length],
      domainPercent: item.entry.completionPercent,
    }))
}

export default function WorkShareChart({ domains }: { domains: DomainProgress[] }) {
  const slices = buildSlices(domains)

  if (slices.length === 0) {
    return (
      <p className="text-sm text-muted">
        Nothing ticked off yet — finish a task or a topic and the split appears here.
      </p>
    )
  }

  // Each segment starts where the previous one ended.
  let offset = 0

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
      <div className="relative shrink-0">
        <svg
          viewBox="0 0 160 160"
          className="h-40 w-40 -rotate-90"
          role="img"
          aria-label={`Work split: ${slices
            .map((s) => `${s.name} ${Math.round(s.percent)}%`)
            .join(", ")}`}
        >
          {/* Track, so a small share still reads as part of a whole. */}
          <circle
            cx="80"
            cy="80"
            r={RADIUS}
            fill="none"
            stroke="var(--color-elevated)"
            strokeWidth={STROKE}
          />

          {slices.map((slice) => {
            const length = (slice.percent / 100) * CIRCUMFERENCE
            // A 1px gap between segments, but never so much that a thin slice
            // disappears.
            const gap = slices.length > 1 ? Math.min(1.5, length / 4) : 0

            const dash = Math.max(0, length - gap)
            const dashOffset = -offset
            offset += length

            return (
              <circle
                key={slice.domainId}
                cx="80"
                cy="80"
                r={RADIUS}
                fill="none"
                stroke={slice.colour}
                strokeWidth={STROKE}
                strokeLinecap="butt"
                strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
                strokeDashoffset={dashOffset}
                className="transition-all duration-700"
              />
            )
          })}
        </svg>

        {/* Centre label. `-rotate-90` is on the svg only, so this stays upright. */}
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-2xl font-semibold text-ink">
            {slices.length}
          </span>
          <span className="text-[11px] text-faint">
            {slices.length === 1 ? "domain" : "domains"}
          </span>
        </div>
      </div>

      <ul className="flex w-full flex-col gap-2">
        {slices.map((slice) => (
          <li key={slice.domainId} className="flex items-center gap-2.5">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: slice.colour }}
              aria-hidden="true"
            />
            <span className="min-w-0 flex-1 truncate text-sm text-ink">{slice.name}</span>
            <span className="shrink-0 text-xs tabular-nums text-faint">
              {Math.round(slice.domainPercent)}% done
            </span>
            <span className="w-10 shrink-0 text-right text-xs font-medium tabular-nums text-violet-soft">
              {Math.round(slice.percent)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
