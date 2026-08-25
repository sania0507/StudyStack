import { Link } from "react-router-dom"
import { ArrowRight, Boxes, Flame, LineChart, Timer } from "lucide-react"
import Logo from "@/components/Logo"
import { Button, Card, Pill } from "@/components/ui"

/*
  ============================================================
  Landing — the public front door
  ============================================================
  A "page" is just a component that happens to be mounted by a
  route. Nothing special about it.

  This one is all presentation: no state, no context, no data
  fetching. It only needs <Link> to send people to /login and
  /register.
*/

const FEATURES = [
  {
    icon: Boxes,
    title: "Domains, not to-do soup",
    body: "Group everything you're learning into domains. Tasks live inside them, so your list never becomes one endless scroll.",
  },
  {
    icon: Timer,
    title: "A timer that stays put",
    body: "Start a focus block and move around the app freely. The countdown follows you and keeps ticking.",
  },
  {
    icon: LineChart,
    title: "Proof you showed up",
    body: "A year of focus in one grid. Streaks, monthly totals, and the days you skipped — no guilt, just facts.",
  },
]

export default function Landing() {
  return (
    <div className="min-h-dvh bg-base">
      {/* ---------------- nav ---------------- */}
      <header className="sticky top-0 z-20 border-b border-line/60 bg-base/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-5">
          <Logo />
          <div className="ml-auto flex items-center gap-2">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Log in
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ---------------- hero ---------------- */}
      <section className="mx-auto max-w-6xl px-5 pb-16 pt-16 sm:pt-24">
        <div className="ss-rise flex max-w-2xl flex-col items-start gap-6">
          <Pill>
            <span className="inline-flex items-center gap-1.5">
              <Flame size={11} /> built for people who keep restarting
            </span>
          </Pill>

          <h1 className="font-display text-4xl font-semibold leading-[1.08] tracking-tight text-ink text-balance sm:text-6xl">
            Stack your focus,
            <br />
            <span className="text-violet-soft">one block at a time.</span>
          </h1>

          <p className="max-w-xl text-[15px] leading-relaxed text-muted text-pretty sm:text-base">
            StudyStack turns studying into something you can actually see. Pick a domain, start a block, and watch the
            hours pile up into a streak worth protecting.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link to="/register">
              <Button size="lg">
                Start your first block <ArrowRight size={16} />
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline">
                I already have an account
              </Button>
            </Link>
          </div>
        </div>

        {/* ---- the signature element: a fake timer that sells the idea ---- */}
        <div className="ss-rise mt-14 sm:mt-20" style={{ animationDelay: "120ms" }}>
          <Card className="relative overflow-hidden">
            <div className="relative flex flex-col items-center gap-8 py-6 sm:flex-row sm:items-center sm:gap-12 sm:px-6">
              <div className="relative grid h-40 w-40 shrink-0 place-items-center">
                <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90">
                  <circle cx="90" cy="90" r="78" fill="none" stroke="var(--color-line)" strokeWidth="3" />
                  <circle
                    cx="90"
                    cy="90"
                    r="78"
                    fill="none"
                    stroke="var(--color-violet)"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeDasharray={2 * Math.PI * 78}
                    strokeDashoffset={2 * Math.PI * 78 * 0.32}
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="font-display text-3xl font-semibold tabular-nums tracking-tight text-ink">
                    41:12
                  </span>
                  <span className="mt-1 text-xs text-faint">focusing</span>
                </div>
              </div>

              <div className="flex flex-1 flex-col gap-4">
                <span className="text-xs text-faint">Currently stacking</span>
                <span className="font-display text-2xl font-semibold tracking-tight text-ink">Data Structures</span>
                <div className="flex flex-wrap gap-2">
                  <Pill tone="mint">39 day streak</Pill>
                  <Pill tone="neutral">11h 22m this month</Pill>
                  <Pill tone="neutral">4 domains</Pill>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* ---------------- features ---------------- */}
      <section className="mx-auto max-w-6xl px-5 pb-20">
        <h2 className="mb-6 font-display text-xl font-semibold tracking-tight text-ink">
          Three things, done properly
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {/*
            .map() over an array to render a list. React needs a
            unique `key` on each item so it can tell them apart
            when the list changes.
          */}
          {FEATURES.map((f) => (
            <Card key={f.title} className="flex flex-col gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-violet/15 text-violet-soft">
                <f.icon size={17} />
              </span>
              <h3 className="font-display text-[15px] font-semibold text-ink">{f.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{f.body}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* ---------------- closing ---------------- */}
      <section className="mx-auto max-w-6xl px-5 pb-24">
        <Card className="flex flex-col items-center gap-5 py-12 text-center">
          <h2 className="max-w-md font-display text-2xl font-semibold tracking-tight text-ink text-balance sm:text-3xl">
            Your first block starts in about four seconds.
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-muted">
            No credit card, no onboarding tour. Make an account and press start.
          </p>
          <Link to="/register">
            <Button size="lg">
              Create my account <ArrowRight size={16} />
            </Button>
          </Link>
        </Card>
      </section>

      <footer className="border-t border-line/60 py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 px-5 sm:flex-row">
          <Logo />
          <span className="text-xs text-faint sm:ml-auto">A focus tracker that respects your time.</span>
        </div>
      </footer>
    </div>
  )
}
