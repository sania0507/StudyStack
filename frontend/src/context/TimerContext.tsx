import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { createSession } from "@/api/client"
import { useDomains } from "@/context/DomainsContext"

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
  /** Optional task the finished block is recorded against. */
  taskId: string
  setTaskId: (id: string) => void
  /** Message for a finished block that could not be saved, or null. */
  saveError: string | null
  isRetrying: boolean
  retrySave: () => void
  dismissSaveError: () => void
  setDomainId: (id: string) => void
  setPreset: (minutes: number) => void
  setCustomSeconds: (seconds: number) => void
  start: () => void
  pause: () => void
  reset: () => void
}

const TimerContext = createContext<TimerValue | null>(null)

export function TimerProvider({ children }: { children: ReactNode }) {
  const [totalSeconds, setTotalSeconds] = useState(60 * 60) // default 1h
  const [secondsLeft, setSecondsLeft] = useState(60 * 60)
  const [isRunning, setIsRunning] = useState(false)
  const [domainId, setDomainId] = useState("")
  // Empty means "record against the domain only", which stays the default so
  // starting a timer never requires choosing a task first.
  const [taskId, setTaskId] = useState("")
  const [completedCount, setCompletedCount] = useState(0)

  // A finished block that could not be saved used to be a console.error and
  // nothing else, so a backend outage silently ate the user's study time.
  // Keeping the failed block here lets the panel show it and retry it.
  const [failedSave, setFailedSave] = useState<{
    domainId: string
    durationSeconds: number
    taskId?: string
  } | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [isRetrying, setIsRetrying] = useState(false)

  // The timer's domain picker defaults to the first real domain.
  const { domains } = useDomains()

  useEffect(() => {
    // Only set a default when nothing is chosen yet, so the user's own
    // pick is never overwritten.
    if (!domainId && domains.length > 0) {
      setDomainId(domains[0].id)
    }

    // A task belongs to a domain, so switching domain invalidates it.
    setTaskId("")

    // If the selected domain was deleted, fall back to the first one.
    if (domainId && !domains.some((domain) => domain.id === domainId)) {
      setDomainId(domains[0]?.id ?? "")
    }
  }, [domains, domainId])

  // useRef holds a value that survives re-renders but does NOT trigger one.
  const tickRef = useRef<number | null>(null)
  const audioRef = useRef<AudioContext | null>(null)

  useEffect(() => {
    // This effect runs whenever `isRunning` flips.
    if (!isRunning) return

    tickRef.current = window.setInterval(() => {
      // Pure updater: just count down. The "finished" side effects live
      // in their own effect below so they run exactly once per finish.
      setSecondsLeft((s) => Math.max(0, s - 1))
    }, 1000)

    // Cleanup clears the interval before re-runs and on unmount. Forgetting
    // this is the #1 cause of "my timer speeds up" bugs.
    return () => {
      if (tickRef.current) window.clearInterval(tickRef.current)
    }
  }, [isRunning])

  // When the clock hits zero while running: stop, record the block, beep.
  useEffect(() => {
    if (secondsLeft === 0 && isRunning) {
      setIsRunning(false)
      beep()

      // Persist the finished block in seconds.
      //
      // The old code rounded to whole minutes, which turned a 40-second block
      // into one minute and a 5-second one into nothing. totalSeconds is what
      // the timer actually counted, so it is the honest number to store.
      const durationSeconds = Math.max(1, Math.round(totalSeconds))

      if (domainId) {
        saveBlock({ domainId, durationSeconds, taskId: taskId || undefined })
      }
    }
  }, [secondsLeft, isRunning, totalSeconds, domainId])

  // Saves one finished block. On failure the block is kept in state instead of
  // being dropped, so the panel can offer a retry once the backend is reachable.
  async function saveBlock(block: {
    domainId: string
    durationSeconds: number
    taskId?: string
  }) {
    try {
      await createSession(block)
      setCompletedCount((c) => c + 1)
      setFailedSave(null)
      setSaveError(null)
    } catch (error) {
      console.error("Failed to save study session:", error)
      setFailedSave(block)
      setSaveError(
        error instanceof Error
          ? error.message
          : "This session could not be saved.",
      )
    }
  }

  function retrySave() {
    if (!failedSave || isRetrying) return

    setIsRetrying(true)
    saveBlock(failedSave).finally(() => setIsRetrying(false))
  }

  function dismissSaveError() {
    setFailedSave(null)
    setSaveError(null)
  }

  /** Lazily create/resume an AudioContext. Browsers require a user gesture,
      so we resume it inside start() — which is always a click. */
  function ensureAudio() {
    if (typeof window === "undefined") return null
    const Ctx =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctx) return null
    if (!audioRef.current) audioRef.current = new Ctx()
    if (audioRef.current.state === "suspended") void audioRef.current.resume()
    return audioRef.current
  }

  /** Two short tones — enough to notice, not enough to annoy. */
  function beep() {
    try {
      const ctx = ensureAudio()
      if (!ctx) return
      const t = ctx.currentTime
      const tone = (freq: number, start: number, dur: number) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.type = "sine"
        osc.frequency.value = freq
        gain.gain.setValueAtTime(0.0001, t + start)
        gain.gain.exponentialRampToValueAtTime(0.25, t + start + 0.02)
        gain.gain.exponentialRampToValueAtTime(0.0001, t + start + dur)
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.start(t + start)
        osc.stop(t + start + dur + 0.02)
      }
      tone(880, 0, 0.25)
      tone(659, 0.35, 0.4)
    } catch {
      // Audio blocked by the browser — the timer still completes silently.
    }
  }

  function applySeconds(secs: number) {
    const s = Math.max(0, Math.round(secs))
    setTotalSeconds(s)
    setSecondsLeft(s)
    setIsRunning(false)
  }

  const value = useMemo<TimerValue>(
    () => ({
      secondsLeft,
      totalSeconds,
      isRunning,
      domainId,
      taskId,
      setTaskId,
      completedCount,
      saveError,
      isRetrying,
      retrySave,
      dismissSaveError,
      setDomainId,
      setPreset: (minutes: number) => applySeconds(minutes * 60),
      setCustomSeconds: applySeconds,
      start: () => {
        if (secondsLeft > 0) {
          ensureAudio() // user gesture — let the browser hear us before the beep
          setIsRunning(true)
        }
      },
      pause: () => setIsRunning(false),
      reset: () => {
        setIsRunning(false)
        setSecondsLeft(totalSeconds)
      },
    }),
    [secondsLeft, totalSeconds, isRunning, domainId, taskId, completedCount, saveError, isRetrying],
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
