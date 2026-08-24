import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import Logo from "@/components/Logo"

/*
  ============================================================
  AuthShell — the frame shared by Login and Register
  ============================================================
  Both auth pages need: the centred card, the logo, a heading,
  a subtitle, and a footer link. Only the FORM differs.

  So we extract the frame and pass the changing bits in as
  props — including `children`, which is the special prop that
  holds whatever you nest inside the tags:

      <AuthShell title="...">
        <form>...</form>     <-- this becomes `children`
      </AuthShell>

  This is composition. It's how you avoid copy-pasting layout.
*/
export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}) {
  return (
    <div className="relative grid min-h-dvh place-items-center overflow-hidden bg-base px-5 py-10">
      {/* one soft glow, top-left — the only decoration on this screen */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-24 -top-32 h-80 w-80 rounded-full bg-violet/15 blur-[100px]"
      />

      <div className="ss-rise relative w-full max-w-sm">
        <Link to="/" className="mb-8 flex justify-center">
          <Logo size="lg" />
        </Link>

        <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6 sm:p-7">
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">{title}</h1>
          <p className="mt-1.5 text-sm leading-relaxed text-muted">{subtitle}</p>

          <div className="mt-6">{children}</div>
        </div>

        <p className="mt-5 text-center text-sm text-muted">{footer}</p>
      </div>
    </div>
  )
}
