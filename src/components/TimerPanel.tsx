import { Pause, Play, RotateCcw } from "lucide-react"
import { useTimer, formatClock } from "@/context/TimerContext"
import { domains } from "@/api/mock"
import { Button, Card, cx } from "@/components/ui"

/*
  ============================================================
  TimerPanel — reads the shared timer, owns no state itself
  ============================================================
  Notice this component has NO useState. It's a "presentational"
  component: it asks the context for the numbers and draws them.

  That separation is why the same panel can appear on the
  dashboard, analytics AND profile page and always agree.
*/

const PRESETS = [
  { label: "25m", minutes: 25 },
  { label: "1h", minutes: 60 },
  { label: "2h", minutes: 120 },
]

export default function TimerPanel() {
  const { secondsLeft, totalSeconds, isRunning, domainId, setDomainId, setPreset, start, pause, reset, completedCount } =
    useTimer()

  // Maths for the SVG ring: stroke-dashoffset draws a partial circle.
  const radius = 78
  const circumference = 2 * Math.PI * radius
  const progress = totalSeconds === 0 ? 0 : 1 - secondsLeft / totalSeconds
  const dashOffset = circumference * (1 - progress)

  return (
    <Card className="flex flex-col gap-5">
      {/* ---- the ring ---- */}
      <div className="relative mx-auto grid aspect-square w-full max-w-[208px] place-items-center">
        <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90">
          <circle cx="90" cy="90" r={radius} fill="none" stroke="var(--color-line)" strokeWidth="3" />
          <circle
            cx="90"
            cy="90"
            r={radius}
            fill="none"
            stroke="var(--color-violet)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className="transition-[stroke-dashoffset] duration-1000 ease-linear"
          />
        </svg>

        <div className="absolute flex flex-col items-center">
          <span className="font-display text-[2.75rem] font-semibold tabular-nums leading-none tracking-tight text-ink">
            {formatClock(secondsLeft)}
          </span>
          <span className="mt-1.5 text-[11px] uppercase tracking-[0.16em] text-faint">
            {isRunning ? "focusing" : secondsLeft === 0 ? "done" : "paused"}
          </span>
        </div>
      </div>

      {/* ---- which domain am I studying? ---- */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="timer-domain" className="text-xs font-medium text-faint">
          Domain
        </label>
        <select
          id="timer-domain"
          value={domainId}
          onChange={(e) => setDomainId(e.target.value)}
          className="h-10 rounded-xl border border-line bg-elevated px-3 text-sm text-ink focus:border-violet-soft/60 focus:outline-none"
        >
          {domains.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>

      {/* ---- presets ---- */}
      <div className="flex gap-2">
        {PRESETS.map((p) => {
          const active = totalSeconds === p.minutes * 60
          return (
            <button
              key={p.label}
              onClick={() => setPreset(p.minutes)}
              className={cx(
                "h-9 flex-1 rounded-lg border text-xs font-medium transition-colors",
                active
                  ? "border-violet bg-violet/15 text-violet-soft"
                  : "border-line text-muted hover:border-violet-soft/40 hover:text-ink",
              )}
            >
              {p.label}
            </button>
          )
        })}
      </div>

      {/* ---- controls ---- */}
      <div className="flex gap-2">
        {isRunning ? (
          <Button variant="outline" full onClick={pause}>
            <Pause size={16} /> Pause
          </Button>
        ) : (
          <Button full onClick={start} disabled={secondsLeft === 0}>
            <Play size={16} /> Start
          </Button>
        )}
        <Button variant="ghost" onClick={reset} aria-label="Reset timer" className="px-3">
          <RotateCcw size={16} />
        </Button>
      </div>

      <p className="border-t border-line pt-4 text-center text-xs text-faint">
        {completedCount} block{completedCount === 1 ? "" : "s"} finished this session
      </p>
    </Card>
  )
}
