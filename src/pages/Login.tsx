import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import AuthShell from "@/components/AuthShell"
import { Button, Field } from "@/components/ui"

/*
  ============================================================
  Login — your first proper look at forms + state
  ============================================================
  A "controlled input" is the core React form pattern:

      value={email}                        <- React owns the text
      onChange={e => setEmail(e.target.value)}  <- typing updates state

  The input doesn't remember anything itself. State is the single
  source of truth, and the input just displays it. Feels like extra
  work at first, but it means you can validate, reset, or prefill
  any field from code.

  Also note the FOUR pieces of state below. That's typical for a
  form: the values, plus `error` and `busy` for feedback.
*/
export default function Login() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    // Without this the browser does a full page reload and React unmounts.
    // You will forget it once, see the page flash, and never forget it again.
    e.preventDefault()

    setError("")
    setBusy(true)
    try {
      await login(email, password)
      navigate("/dashboard") // success — into the app
    } catch (err) {
      // Our mock api throws Error objects; show the message to the user.
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      // `finally` runs whether we succeeded or failed, so the button
      // never gets stuck in its loading state.
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Pick up where your streak left off."
      footer={
        <>
          New here?{" "}
          <Link to="/register" className="font-medium text-violet-soft hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@studystack.app"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          placeholder="At least 6 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {/*
          Conditional rendering with &&: if `error` is an empty
          string it's falsy, so React renders nothing at all.
          role="alert" makes screen readers announce it.
        */}
        {error && (
          <p role="alert" className="rounded-lg border border-violet-soft/30 bg-violet/10 px-3 py-2 text-xs text-ink">
            {error}
          </p>
        )}

        <Button type="submit" size="lg" full disabled={busy} className="mt-1">
          {busy ? "Signing in…" : "Log in"}
          {!busy && <ArrowRight size={16} />}
        </Button>

        <p className="text-center text-xs leading-relaxed text-faint">
          Frontend demo — any email and a 6-character password will let you in.
        </p>
      </form>
    </AuthShell>
  )
}
