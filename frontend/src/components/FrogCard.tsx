import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { cx } from "@/components/ui"

/*
  ============================================================
  FrogCard — the one anti-procrastination nudge
  ============================================================
  The quote is the hook. Tapping the card unfolds a short,
  actionable summary of the Eat the Frog method — no fluff,
  five steps, enough to act on today.
*/

const QUOTE =
  "If it's your job to eat a frog, it's best to do it first thing in the morning. And if it's your job to eat two frogs, it's best to eat the biggest one first."

const STEPS = [
  {
    title: "Decide on your frog",
    body: "The one task you're most likely to dodge — usually important, not urgent. That's today's frog.",
  },
  {
    title: "Keep it to 1–4 hours",
    body: "Bigger than half a day? Break it down and make the first concrete step today's frog.",
  },
  {
    title: "Prepare it the night before",
    body: "Close the tabs, leave the first step open and obvious. The next morning starts itself.",
  },
  {
    title: "Eat it first",
    body: "Before email, chats, and feeds. Not a morning person? Use your best hours — 8am or 8pm, same rule.",
  },
  {
    title: "One frog is enough",
    body: "Any day you eat your frog is a good day. Don't plan a whole week of frogs in advance.",
  },
]

export default function FrogCard() {
  const [open, setOpen] = useState(false)

  return (
    <button
      type="button"
      onClick={() => setOpen((o) => !o)}
      aria-expanded={open}
      className="w-full rounded-[var(--radius-card)] border border-line bg-surface p-5 text-left transition-colors hover:bg-elevated"
    >
      <span className="flex items-start justify-between gap-4">
        <span className="font-display text-[15px] font-medium leading-relaxed text-ink text-pretty">
          “{QUOTE}”
        </span>
        <ChevronDown
          size={16}
          className={cx("mt-1 shrink-0 text-faint transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
      </span>
      <span className="mt-2 block text-xs text-faint">Mark Twain, attributed · tap for the how</span>

      {open && (
        <span className="mt-4 flex flex-col gap-3 border-t border-line pt-4">
          {STEPS.map((s, i) => (
            <span key={s.title} className="flex gap-3 text-left">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-violet/15 text-xs font-medium tabular-nums text-violet-soft">
                {i + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-ink">{s.title}</span>
                <span className="mt-0.5 block text-sm leading-relaxed text-muted">{s.body}</span>
              </span>
            </span>
          ))}
        </span>
      )}
    </button>
  )
}
