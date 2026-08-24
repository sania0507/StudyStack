import { useRef, useState } from "react"
import { Camera, Trash2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import * as api from "@/api/mock"
import { Avatar, Button, Card, Field } from "@/components/ui"

/*
  ============================================================
  Profile — editing existing data, plus file input via useRef
  ============================================================
  Two new things worth slowing down for:

  1. INITIALISING STATE FROM PROPS/CONTEXT
       useState(user?.name ?? "")
     The argument to useState is only used on the FIRST render.
     It's an initial value, not a live link. That's exactly what
     you want in an edit form: the user can type freely without
     context changes yanking the text out from under them.

  2. useRef FOR DOM ACCESS
     A styled "Upload photo" button can't be a raw <input file>,
     those are ugly and unstyleable. So we hide the real input,
     keep a ref to it, and call fileRef.current.click() from our
     pretty button. useRef is the escape hatch for reaching a
     real DOM node.
*/
export default function Profile() {
  const { user, patchUser, logout } = useAuth()

  // --- details form ---
  const [name, setName] = useState(user?.name ?? "")
  const [email, setEmail] = useState(user?.email ?? "")
  const [detailsBusy, setDetailsBusy] = useState(false)
  const [detailsMsg, setDetailsMsg] = useState("")

  // --- password form ---
  const [pw, setPw] = useState({ current: "", next: "" })
  const [pwBusy, setPwBusy] = useState(false)
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const fileRef = useRef<HTMLInputElement>(null)

  async function saveDetails(e: React.FormEvent) {
    e.preventDefault()
    setDetailsBusy(true)
    setDetailsMsg("")
    try {
      const patch = await api.updateProfile({ name, email })
      patchUser(patch) // push the change up into context -> navbar updates instantly
      setDetailsMsg("Saved.")
    } finally {
      setDetailsBusy(false)
    }
  }

  async function savePassword(e: React.FormEvent) {
    e.preventDefault()
    setPwBusy(true)
    setPwMsg(null)
    try {
      await api.changePassword(pw.current, pw.next)
      setPwMsg({ ok: true, text: "Password updated." })
      setPw({ current: "", next: "" }) // clear the fields on success
    } catch (err) {
      setPwMsg({ ok: false, text: err instanceof Error ? err.message : "Could not update password." })
    } finally {
      setPwBusy(false)
    }
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    // URL.createObjectURL gives us a local preview URL without any upload.
    // A real app would POST the file and store the returned URL instead.
    patchUser({ avatarUrl: URL.createObjectURL(file) })
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Profile</h1>
        <p className="mt-1 text-sm text-muted">Your name, your email, your face. All editable.</p>
      </div>

      {/* ---------------- avatar ---------------- */}
      <Card className="flex flex-col items-start gap-5 sm:flex-row sm:items-center">
        <Avatar name={user?.name ?? "?"} url={user?.avatarUrl} size={72} />

        <div className="flex flex-col gap-1">
          <span className="font-display text-lg font-semibold text-ink">{user?.name}</span>
          <span className="text-sm text-muted">{user?.email}</span>
          <span className="text-xs text-faint">Stacking since {user?.joinedAt}</span>
        </div>

        <div className="flex gap-2 sm:ml-auto">
          {/* The real input is hidden but fully functional. */}
          <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
          <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
            <Camera size={14} /> Change photo
          </Button>
          {user?.avatarUrl && (
            <Button variant="ghost" size="sm" onClick={() => patchUser({ avatarUrl: "" })} aria-label="Remove photo">
              <Trash2 size={14} />
            </Button>
          )}
        </div>
      </Card>

      {/* ---------------- details + password ---------------- */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="flex flex-col gap-4">
          <h2 className="font-display text-base font-semibold text-ink">Details</h2>
          <form onSubmit={saveDetails} className="flex flex-col gap-4">
            <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            <Field
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={detailsBusy}>
                {detailsBusy ? "Saving…" : "Save changes"}
              </Button>
              {detailsMsg && <span className="text-xs text-mint">{detailsMsg}</span>}
            </div>
          </form>
        </Card>

        <Card className="flex flex-col gap-4">
          <h2 className="font-display text-base font-semibold text-ink">Password</h2>
          <form onSubmit={savePassword} className="flex flex-col gap-4">
            <Field
              label="Current password"
              type="password"
              autoComplete="current-password"
              value={pw.current}
              onChange={(e) => setPw((p) => ({ ...p, current: e.target.value }))}
            />
            <Field
              label="New password"
              type="password"
              autoComplete="new-password"
              hint="At least 6 characters."
              value={pw.next}
              onChange={(e) => setPw((p) => ({ ...p, next: e.target.value }))}
            />
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={pwBusy}>
                {pwBusy ? "Updating…" : "Update password"}
              </Button>
              {pwMsg && (
                <span className={pwMsg.ok ? "text-xs text-mint" : "text-xs text-violet-soft"}>{pwMsg.text}</span>
              )}
            </div>
          </form>
        </Card>
      </div>

      {/* ---------------- danger zone ---------------- */}
      <Card className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="font-display text-base font-semibold text-ink">Log out</h2>
          <p className="mt-1 text-sm text-muted">Your streak is saved. Come back tomorrow.</p>
        </div>
        <Button variant="danger" className="sm:ml-auto" onClick={logout}>
          Log out
        </Button>
      </Card>
    </div>
  )
}
