import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"

/*
  ============================================================
  TimerContext — the timer that survives page changes
  ============================================================
  THE KEY IDEA you asked about:

  If the countdown state lived inside the Dashboard page, then
  navigating to /analytics would UNMOUNT that page, React would
  throw the state away, and your timer would reset to 60:00.

  So we lift the state ABOVE the router. The provider sits in
  App.tsx wrapping every route, so it never unmounts while you
  move between pages — the interval just keeps ticking.

  Lesson: state lives at the lowest component that still
  contains everyone who needs it. Here that's the whole app.
*/

type TimerValue = {
  secondsLeft: number
  totalSeconds: number
  isRunning: boolean
  domainId: string
  completedCount: number
  setDomainId: (id: string) => void
  setPreset: (minutes: number) => void
  start: () => void
  pause: () => void
  reset: () => void
}

const TimerContext = createContext<TimerValue | null>(null)

export function TimerProvider({ children }: { children: ReactNode }) {
  const [totalSeconds, setTotalSeconds] = useState(60 * 60) // default 1h
  const [secondsLeft, setSecondsLeft] = useState(60 * 60)
  const [isRunning, setIsRunning] = useState(false)
  const [domainId, setDomainId] = useState("d_1")
  const [completedCount, setCompletedCount] = useState(0)

  // useRef holds a value that survives re-renders but does NOT trigger one.
  // Perfect for storing an interval id.
  const tickRef = useRef<number | null>(null)

  useEffect(() => {
    // This effect runs whenever `isRunning` flips.
    if (!isRunning) return

    tickRef.current = window.setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          setIsRunning(false)
          setCompletedCount((c) => c + 1)
          return 0
        }
        return s - 1
      })
    }, 1000)

    // The returned function is CLEANUP. React calls it before the effect
    // re-runs and when the component unmounts. Forgetting this is the
    // #1 cause of "my timer speeds up" bugs — you stack intervals.
    return () => {
      if (tickRef.current) window.clearInterval(tickRef.current)
    }
  }, [isRunning])

  function setPreset(minutes: number) {
    const secs = Math.round(minutes * 60)
    setTotalSeconds(secs)
    setSecondsLeft(secs)
    setIsRunning(false)
  }

  const value = useMemo<TimerValue>(
    () => ({
      secondsLeft,
      totalSeconds,
      isRunning,
      domainId,
      completedCount,
      setDomainId,
      setPreset,
      start: () => secondsLeft > 0 && setIsRunning(true),
      pause: () => setIsRunning(false),
      reset: () => {
        setIsRunning(false)
        setSecondsLeft(totalSeconds)
      },
    }),
    [secondsLeft, totalSeconds, isRunning, domainId, completedCount],
  )

  return <TimerContext.Provider value={value}>{children}</TimerContext.Provider>
}

export function useTimer() {
  const ctx = useContext(TimerContext)
  if (!ctx) throw new Error("useTimer must be used inside <TimerProvider>")
  return ctx
}

/** 3725 -> "62:05". Kept here so every component formats time the same way. */
export function formatClock(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}
