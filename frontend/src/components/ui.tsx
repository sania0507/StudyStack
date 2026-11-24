import { useEffect, useState } from "react"
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react"
import { fetchAvatarObjectUrl } from "@/api/client"

/*
  ============================================================
  Small reusable primitives
  ============================================================
  A "component" is just a function that returns JSX. That's it.

  These exist so buttons and cards look identical everywhere.
  When you want to restyle every button in StudyStack, you edit
  this one file — not 40 pages.

  Note the `...rest` pattern below: it forwards any extra props
  (onClick, type, disabled, aria-label) straight to the real
  <button>, so our wrapper never blocks native behaviour.
*/

/** Joins class names and drops falsy ones. Saves messy template strings. */
export function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ember" | "ghost" | "outline" | "danger"
  size?: "sm" | "md" | "lg"
  full?: boolean
}

export function Button({ variant = "primary", size = "md", full, className, ...rest }: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 disabled:opacity-45 disabled:cursor-not-allowed active:scale-[0.98]"

  const variants = {
    // Primary is the only place purple carries an action, so it stays rare.
    primary: "bg-violet text-ink hover:brightness-115 shadow-lg shadow-violet/20",
    // Neutral high-contrast alternative, for when two actions sit side by side.
    ember: "bg-ink text-base hover:bg-ink/90",
    ghost: "text-muted hover:text-ink hover:bg-elevated",
    outline: "border border-line text-ink hover:bg-elevated hover:border-violet-soft/50",
    danger: "border border-danger/40 text-danger hover:bg-danger/10",
  }

  const sizes = {
    sm: "h-8 px-3 text-xs",
    md: "h-10 px-4 text-sm",
    lg: "h-12 px-6 text-[15px]",
  }

  return <button className={cx(base, variants[variant], sizes[size], full && "w-full", className)} {...rest} />
}

/** A labelled text input. Grouping label+input keeps forms accessible. */
type FieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }

export function Field({ label, hint, id, className, ...rest }: FieldProps) {
  const inputId = id ?? `f_${label.toLowerCase().replace(/\s+/g, "-")}`
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-xs font-medium text-faint">
        {label}
      </label>
      <input
        id={inputId}
        className={cx(
          "h-11 rounded-xl border border-line bg-elevated px-3.5 text-sm text-ink",
          "placeholder:text-faint/70 transition-colors",
          "focus:border-violet-soft/60 focus:outline-none",
          className,
        )}
        {...rest}
      />
      {hint && <span className="text-xs text-faint">{hint}</span>}
    </div>
  )
}

/** The panel every block of content sits in. */
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("rounded-[var(--radius-card)] border border-line bg-surface p-5", className)}>{children}</div>
  )
}

/** Small stat block: label, big number, optional thin progress bar. */
export function StatCard({
  label,
  value,
  caption,
  progress,
  accent = "violet",
}: {
  label: string
  value: string
  caption: string
  progress?: number // 0..1 — only render the bar when meaningfully supplied
  // Two accents, two jobs: violet measures time, ember measures momentum.
  accent?: "violet" | "ember"
}) {
  return (
    <Card className="flex flex-col gap-3">
      <span className="text-xs text-faint">{label}</span>
      <span className="font-display text-3xl font-semibold tracking-tight text-ink">{value}</span>
      {progress !== undefined && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-elevated">
          <div
            className={cx(
              "h-full rounded-full transition-[width] duration-700",
              accent === "ember" ? "bg-ink/45" : "bg-violet",
            )}
            style={{ width: `${Math.min(100, Math.max(0, progress * 100))}%` }}
          />
        </div>
      )}
      <span className="text-xs text-faint">{caption}</span>
    </Card>
  )
}

/**
 * Stack motif: three descending bars echoing the logo mark. Used as a
 * progress indicator where the number alone can't carry the proportion.
 */
export function StackBar({
  progress,
  colour = "bg-violet",
  className,
}: {
  progress: number
  colour?: string // a bg-colour token class, e.g. "bg-mint"
  className?: string
}) {
  const pct = `${Math.min(100, Math.max(0, progress * 100))}%`
  const widths = ["100%", "72%", "44%"]
  return (
    <div className={cx("flex flex-col gap-[3px]", className)} aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-[5px] overflow-hidden rounded-full bg-elevated" style={{ width: widths[i] }}>
          <div className={cx("h-full rounded-full transition-[width] duration-700", colour)} style={{ width: pct }} />
        </div>
      ))}
    </div>
  )
}

/** Rounded pill used for tags / streaks. */
export function Pill({ children, tone = "violet" }: { children: ReactNode; tone?: "violet" | "mint" | "neutral" }) {
  const tones = {
    violet: "bg-violet/15 text-violet-soft",
    mint: "bg-mint/15 text-mint",
    neutral: "bg-elevated text-muted",
  }
  return <span className={cx("rounded-full px-2.5 py-1 text-xs font-medium", tones[tone])}>{children}</span>
}

/** Avatar: shows an image if we have one, otherwise the first letter. */
/**
 * The user's face, wherever it appears.
 *
 * `hasAvatar` is a boolean, NOT a URL, on purpose. The avatar endpoint needs an
 * Authorization header and an <img src> cannot send one, so handing a protected
 * URL to an <img> produces a 401 and a broken-image icon. This component fetches
 * the bytes with the token and wraps them in a blob URL instead.
 *
 * Anything that goes wrong — 401, CORS, deleted avatar, offline — falls back to
 * the initial, because a letter always beats a broken icon.
 */
export function Avatar({
  name,
  hasAvatar,
  size = 36,
}: {
  name: string
  hasAvatar?: boolean
  size?: number
}) {
  const [src, setSrc] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!hasAvatar) {
      setSrc(null)
      setFailed(false)
      return
    }

    let cancelled = false
    let objectUrl: string | null = null

    fetchAvatarObjectUrl()
      .then((url) => {
        objectUrl = url
        if (url && !cancelled) setSrc(url)
        else if (!cancelled) setFailed(true)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [hasAvatar])

  if (hasAvatar && src && !failed) {
    return (
      <img
        src={src}
        alt={`${name}'s profile picture`}
        width={size}
        height={size}
        onError={() => setFailed(true)}
        className="shrink-0 rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      className="flex shrink-0 items-center justify-center rounded-full bg-violet font-display font-semibold text-ink"
      style={{ width: size, height: size, fontSize: size * 0.42 }}
    >
      {name.charAt(0).toUpperCase()}
    </span>
  )
}
