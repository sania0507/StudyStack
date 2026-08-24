import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import AuthShell from "@/components/AuthShell"
import { Button, Field } from "@/components/ui"

/*
  ============================================================
  Register — same pattern as Login, one object instead of 3 states
  ============================================================
  On Login I used a separate useState per field. Here I use ONE
  state object. Both are fine — this version scales better once
  a form has 4+ fields.

  The trade-off is you must spread the old state when updating:

      setForm({ ...form, name: "x" })

  Miss the spread and you wipe every other field. This is the
  "state is immutable" rule again: build a new object, don't edit
  the old one.
*/
export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "" })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const { register } = useAuth()
  const navigate = useNavigate()

  // One handler for every field. `key` says which one to overwrite.
  function update(key: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setBusy(true)
    try {
      await register(form.name, form.email, form.password)
      navigate("/dashboard")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Start your stack"
      subtitle="Four domains, one timer, zero guilt."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-violet-soft hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <Field
          label="Name"
          autoComplete="name"
          placeholder="What should we call you?"
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
          required
        />

        <Field
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@studystack.app"
          value={form.email}
          onChange={(e) => update("email", e.target.value)}
          required
        />

        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 6 characters"
          hint="Six characters minimum. That's the only rule."
          value={form.password}
          onChange={(e) => update("password", e.target.value)}
          required
        />

        {error && (
          <p role="alert" className="rounded-lg border border-violet-soft/30 bg-violet/10 px-3 py-2 text-xs text-ink">
            {error}
          </p>
        )}

        <Button type="submit" size="lg" full disabled={busy} className="mt-1">
          {busy ? "Creating account…" : "Create account"}
          {!busy && <ArrowRight size={16} />}
        </Button>
      </form>
    </AuthShell>
  )
}
