import { useCallback, useEffect, useMemo, useState } from "react"
import {
  FolderPlus,
  GripVertical,
  Pin,
  PinOff,
  Pencil,
  Search,
  StickyNote,
  Trash2,
  X,
} from "lucide-react"
import * as api from "@/api/client"
import type { Note, NoteFolder } from "@/api/types"
import { Button, Card, Field, cx } from "@/components/ui"

/*
  ============================================================
  Notes — folders on the left, a date timeline on the right
  ============================================================
  The timeline is the point: notes are ordered by created_at,
  newest first, because a diary reads as "what happened lately".
  Pinned notes break that rule on purpose and sit above it.

  Why editing does not reorder: created_at is the anchor and
  updated_at is only an "edited" stamp. Editing an old note
  should not push it to the top of the list.

  Markdown is rendered by the tiny function at the bottom rather
  than a library: bold, italic, inline code, headings, lists.
  Anything unrecognised is escaped and shown as text, so a note
  can never inject markup.
*/

type Draft = {
  id?: string
  title: string
  body: string
}

const EMPTY_DRAFT: Draft = { title: "", body: "" }

/** Escapes HTML first, then applies the handful of patterns we support. */
function renderMarkdown(source: string): string {
  const escaped = source
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")

  const lines = escaped.split("\n")
  const html: string[] = []
  let inList = false

  const closeList = () => {
    if (inList) {
      html.push("</ul>")
      inList = false
    }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()

    if (/^###\s+/.test(line)) {
      closeList()
      html.push(`<h3>${inline(line.replace(/^###\s+/, ""))}</h3>`)
      continue
    }
    if (/^##\s+/.test(line)) {
      closeList()
      html.push(`<h2>${inline(line.replace(/^##\s+/, ""))}</h2>`)
      continue
    }
    if (/^#\s+/.test(line)) {
      closeList()
      html.push(`<h1>${inline(line.replace(/^#\s+/, ""))}</h1>`)
      continue
    }
    if (/^[-*]\s+/.test(line)) {
      if (!inList) {
        html.push("<ul>")
        inList = true
      }
      html.push(`<li>${inline(line.replace(/^[-*]\s+/, ""))}</li>`)
      continue
    }

    closeList()

    if (line.trim() === "") {
      html.push('<p class="h-2"></p>')
      continue
    }

    html.push(`<p>${inline(line)}</p>`)
  }

  closeList()

  return html.join("")
}

function inline(text: string): string {
  return text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
}

function formatDate(iso: string): string {
  const date = new Date(iso)

  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: date.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
  })
}

/** "Today" / "Yesterday" reads better than a date on a day-old note. */
function dayLabel(iso: string): string {
  const date = new Date(iso)
  const today = new Date()

  const days = Math.floor(
    (new Date(today.toDateString()).getTime() - new Date(date.toDateString()).getTime()) /
      86_400_000,
  )

  if (days === 0) return "Today"
  if (days === 1) return "Yesterday"
  if (days < 7) return `${days} days ago`

  return formatDate(iso)
}

export default function Notes() {
  const [folders, setFolders] = useState<NoteFolder[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [activeFolder, setActiveFolder] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [newFolder, setNewFolder] = useState("")
  const [addingFolder, setAddingFolder] = useState(false)
  const [busy, setBusy] = useState(false)

  // Drag-to-reorder. The pointer never moves the DOM; it only changes the
  // order of ids in state, and the list re-renders. On release we send that
  // order to the server once.
  const [dragId, setDragId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)

  const load = useCallback(async () => {
    const [folderList, noteList] = await Promise.all([
      api.getFolders(),
      api.getNotes({
        folderId: activeFolder ?? undefined,
        search: search.trim() || undefined,
      }),
    ])

    setFolders(folderList)
    setNotes(noteList)
  }, [activeFolder, search])

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    load()
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load your notes.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [load])

  const totalNotes = useMemo(
    () => folders.reduce((sum, folder) => sum + folder.noteCount, 0),
    [folders],
  )

  async function commitFolder(event: React.FormEvent) {
    event.preventDefault()

    const name = newFolder.trim()
    if (!name) return

    setBusy(true)
    setError(null)

    try {
      const created = await api.createFolder(name)
      setFolders((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setNewFolder("")
      setAddingFolder(false)
      setActiveFolder(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create that folder.")
    } finally {
      setBusy(false)
    }
  }

  async function removeFolder(folder: NoteFolder) {
    if (!window.confirm(`Delete "${folder.name}" and its ${folder.noteCount} note(s)?`)) return

    try {
      await api.deleteFolder(folder.id)
      setFolders((prev) => prev.filter((f) => f.id !== folder.id))
      if (activeFolder === folder.id) setActiveFolder(null)
      await load()
    } catch {
      setError("Could not delete that folder.")
    }
  }

  async function saveDraft(event: React.FormEvent) {
    event.preventDefault()
    if (!draft || !draft.title.trim()) return

    setBusy(true)
    setError(null)

    try {
      if (draft.id) {
        await api.updateNote(draft.id, { title: draft.title, body: draft.body })
      } else {
        if (!activeFolder) {
          setError("Pick a folder first.")
          return
        }
        await api.createNote({
          folderId: activeFolder,
          title: draft.title,
          body: draft.body,
        })
      }

      setDraft(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that note.")
    } finally {
      setBusy(false)
    }
  }

  async function togglePin(note: Note) {
    // Optimistic: the star flips immediately and only the list order moves.
    setNotes((prev) =>
      prev.map((n) => (n.id === note.id ? { ...n, pinned: !n.pinned } : n)),
    )

    try {
      await api.updateNote(note.id, { pinned: !note.pinned })
      await load()
    } catch {
      setError("Could not pin that note.")
      await load()
    }
  }

  async function removeNote(note: Note) {
    const snapshot = notes
    setNotes((prev) => prev.filter((n) => n.id !== note.id))

    try {
      await api.deleteNote(note.id)
      setFolders((prev) =>
        prev.map((f) =>
          f.id === note.folderId ? { ...f, noteCount: Math.max(0, f.noteCount - 1) } : f,
        ),
      )
    } catch {
      setNotes(snapshot)
      setError("Could not delete that note.")
    }
  }

  async function moveNote(note: Note, folderId: string) {
    if (folderId === note.folderId) return

    try {
      await api.updateNote(note.id, { folderId })
      await load()
    } catch {
      setError("Could not move that note.")
    }
  }

  // If the pointer is released over a gap, the handle, or outside the list,
  // the per-article pointerup never fires. One document listener closes it.
  useEffect(() => {
    if (!dragId) return

    function finish() {
      void commitOrder()
    }

    document.addEventListener("pointerup", finish, { once: true })

    return () => document.removeEventListener("pointerup", finish)
  }, [dragId, notes])

  function moveNoteInList(sourceId: string, targetId: string) {
    if (sourceId === targetId) return

    setNotes((prev) => {
      const next = [...prev]
      const from = next.findIndex((n) => n.id === sourceId)
      const to = next.findIndex((n) => n.id === targetId)

      if (from === -1 || to === -1) return prev

      const [moved] = next.splice(from, 1)
      next.splice(to, 0, moved)

      return next
    })
  }

  async function commitOrder() {
    const order = notes.map((n) => n.id)

    setDragId(null)
    setOverId(null)

    try {
      // created_at is untouched by the server; only the order changes.
      await api.reorderNotes(order)
    } catch {
      setError("Could not save that order.")
      await load()
    }
  }

  const activeName = folders.find((f) => f.id === activeFolder)?.name ?? "All notes"

  return (
    <div className="flex flex-col gap-5">
      <div className="ss-rise flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Notes</h1>
          <p className="mt-1 text-sm text-muted">
            {totalNotes} note{totalNotes === 1 ? "" : "s"} across {folders.length} folder
            {folders.length === 1 ? "" : "s"} · newest first
          </p>
        </div>

        <Button
          size="sm"
          onClick={() => setDraft({ ...EMPTY_DRAFT })}
          disabled={folders.length === 0}
          title={folders.length === 0 ? "Create a folder first" : undefined}
        >
          <StickyNote size={14} /> New note
        </Button>
      </div>

      {error && (
        <p className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex flex-col gap-5 lg:flex-row">
        {/* ---------------- folder rail ---------------- */}
        <aside className="w-full shrink-0 lg:w-[236px]">
          <Card className="flex flex-col gap-1 p-2">
            <button
              type="button"
              onClick={() => setActiveFolder(null)}
              className={cx(
                "flex items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors",
                activeFolder === null
                  ? "bg-elevated text-ink"
                  : "text-muted hover:bg-elevated/60 hover:text-ink",
              )}
            >
              <span>All notes</span>
              <span className="text-xs tabular-nums text-faint">{totalNotes}</span>
            </button>

            {folders.map((folder) => (
              <div
                key={folder.id}
                className={cx(
                  "group flex items-center rounded-lg transition-colors",
                  activeFolder === folder.id
                    ? "bg-elevated text-ink"
                    : "text-muted hover:bg-elevated/60 hover:text-ink",
                )}
              >
                <button
                  type="button"
                  onClick={() => setActiveFolder(folder.id)}
                  className="flex min-w-0 flex-1 items-center justify-between px-3 py-2 text-left text-sm"
                >
                  <span className="truncate">{folder.name}</span>
                  <span className="ml-2 shrink-0 text-xs tabular-nums text-faint">
                    {folder.noteCount}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => removeFolder(folder)}
                  aria-label={`Delete folder ${folder.name}`}
                  className="mr-1 grid h-6 w-6 shrink-0 place-items-center rounded-md text-faint opacity-0 transition-opacity hover:bg-danger/15 hover:text-danger group-hover:opacity-100 focus:opacity-100"
                >
                  <X size={12} strokeWidth={2.5} />
                </button>
              </div>
            ))}

            {addingFolder ? (
              <form onSubmit={commitFolder} className="flex flex-col gap-2 p-2">
                <Field
                  label="Folder name"
                  placeholder="DSA, diary, college…"
                  value={newFolder}
                  onChange={(e) => setNewFolder(e.target.value)}
                  autoFocus
                />
                <div className="flex gap-2">
                  <Button size="sm" type="submit" disabled={busy || !newFolder.trim()}>
                    Create
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setAddingFolder(false)
                      setNewFolder("")
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAddingFolder(true)}
                className="mt-1 justify-start"
              >
                <FolderPlus size={14} /> New folder
              </Button>
            )}
          </Card>
        </aside>

        {/* ---------------- timeline ---------------- */}
        <main className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="relative">
            <Search
              size={15}
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${activeFolder ? "in this folder" : "all notes"}…`}
              aria-label="Search notes"
              className="h-10 w-full rounded-xl border border-line bg-surface pl-9 pr-3 text-sm text-ink placeholder:text-faint focus:border-violet-soft/60 focus:outline-none"
            />
          </div>

          {draft && (
            <Card className="ss-rise">
              <form onSubmit={saveDraft} className="flex flex-col gap-3">
                <Field
                  label="Title"
                  placeholder="What is this about?"
                  value={draft.title}
                  onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  autoFocus
                />
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="note-body" className="text-xs font-medium text-faint">
                    Note · markdown: **bold**, *italic*, `code`, - list, # heading
                  </label>
                  <textarea
                    id="note-body"
                    value={draft.body}
                    onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                    rows={6}
                    placeholder="Write it down before it evaporates…"
                    className="w-full resize-y rounded-xl border border-line bg-surface px-3 py-2 text-sm leading-relaxed text-ink placeholder:text-faint focus:border-violet-soft/60 focus:outline-none"
                  />
                </div>
                <div className="flex gap-2">
                  <Button size="sm" type="submit" disabled={busy || !draft.title.trim()}>
                    {draft.id ? "Save changes" : "Add note"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setDraft(null)}>
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {loading && <p className="text-sm text-muted">Loading…</p>}

          {!loading && notes.length === 0 && (
            <Card className="flex flex-col items-center gap-2 py-12 text-center">
              <span className="grid h-12 w-12 place-items-center rounded-2xl border border-line bg-elevated text-violet-soft">
                <StickyNote size={20} aria-hidden="true" />
              </span>
              <p className="font-display text-base text-ink">
                {search ? "Nothing matches that" : `${activeName} is empty`}
              </p>
              <p className="max-w-xs text-sm text-muted">
                {search
                  ? "Try a shorter word, or clear the search."
                  : folders.length === 0
                    ? "Make a folder on the left — DSA, diary, whatever fits."
                    : "Add your first note to start the timeline."}
              </p>
            </Card>
          )}

          {/* Notes are rendered as one continuous timeline with a date spine. */}
          <div className="flex flex-col">
            {notes.map((note) => (
              <article
                key={note.id}
                onPointerEnter={() => {
                  if (!dragId || dragId === note.id) return
                  // Reorder live as the pointer crosses each note, so the list
                  // moves under your finger like a real sortable list.
                  setOverId(note.id)
                  moveNoteInList(dragId, note.id)
                }}
                className={cx(
                  "group relative flex gap-3 pb-4 transition-opacity",
                  dragId === note.id && "opacity-60",
                )}
              >
                {/* Drag handle. Kept separate from the note so selecting text
                    inside a note never starts a drag. */}
                <div className="flex w-6 shrink-0 flex-col items-center pt-1">
                  <button
                    type="button"
                    aria-label="Drag to reorder"
                    title="Drag to reorder"
                    onPointerDown={(e) => {
                      e.currentTarget.setPointerCapture(e.pointerId)
                      setDragId(note.id)
                      setOverId(note.id)
                    }}
                    style={{ touchAction: "none" }}
                    className={cx(
                      "cursor-grab rounded-md p-0.5 text-faint transition-opacity",
                      "opacity-0 group-hover:opacity-100 focus:opacity-100",
                      dragId === note.id && "cursor-grabbing opacity-100 text-violet-soft",
                    )}
                  >
                    <GripVertical size={14} />
                  </button>
                </div>

                {/* spine */}
                <div className="flex w-5 shrink-0 flex-col items-center pt-1">
                  <span
                    className={cx(
                      "h-2.5 w-2.5 rounded-full ring-4 ring-base",
                      note.pinned ? "bg-violet-soft" : "bg-line group-hover:bg-violet/60",
                    )}
                  />
                  <span className="mt-1 w-px flex-1 bg-line" aria-hidden="true" />
                </div>

                <Card
                  className={cx(
                    "min-w-0 flex-1 transition-colors",
                    overId === note.id && dragId && dragId !== note.id
                      ? "border-violet-soft/70"
                      : "hover:border-violet-soft/30",
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="truncate font-display text-[15px] font-medium text-ink">
                          {note.title}
                        </h3>
                        {note.pinned && (
                          <span className="rounded-full border border-violet-soft/40 px-1.5 py-0.5 text-[10px] text-violet-soft">
                            pinned
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-[11px] text-faint">
                        {dayLabel(note.createdAt)} · {formatDate(note.createdAt)}
                        {activeFolder === null && (
                          <>
                            {" · "}
                            {folders.find((f) => f.id === note.folderId)?.name ?? "unknown"}
                          </>
                        )}
                      </p>
                    </div>

                    <div className="flex shrink-0 gap-1">
                      <button
                        type="button"
                        onClick={() => togglePin(note)}
                        aria-label={note.pinned ? "Unpin note" : "Pin note"}
                        className="grid h-7 w-7 place-items-center rounded-md text-faint transition-colors hover:bg-elevated hover:text-violet-soft"
                      >
                        {note.pinned ? <PinOff size={13} /> : <Pin size={13} />}
                      </button>
                      <button
                        type="button"
                        onClick={() => setDraft({ id: note.id, title: note.title, body: note.body })}
                        aria-label="Edit note"
                        className="grid h-7 w-7 place-items-center rounded-md text-faint transition-colors hover:bg-elevated hover:text-ink"
                      >
                        <Pencil size={13} />
                      </button>
                      <button
                        type="button"
                        onClick={() => removeNote(note)}
                        aria-label="Delete note"
                        className="grid h-7 w-7 place-items-center rounded-md text-faint transition-colors hover:bg-danger/15 hover:text-danger"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {note.body && (
                    <div
                      className="note-body mt-3 text-sm leading-relaxed text-muted"
                      // Rendered from escaped text: see renderMarkdown.
                      dangerouslySetInnerHTML={{ __html: renderMarkdown(note.body) }}
                    />
                  )}

                  {folders.length > 1 && (
                    <div className="mt-3 flex items-center gap-2 border-t border-line pt-2">
                      <label
                        htmlFor={`move-${note.id}`}
                        className="text-[11px] text-faint"
                      >
                        Move to
                      </label>
                      <select
                        id={`move-${note.id}`}
                        value={note.folderId}
                        onChange={(e) => moveNote(note, e.target.value)}
                        className="rounded-md border border-line bg-surface px-2 py-1 text-[11px] text-muted focus:border-violet-soft/60 focus:outline-none"
                      >
                        {folders.map((folder) => (
                          <option key={folder.id} value={folder.id}>
                            {folder.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </Card>
              </article>
            ))}
          </div>
        </main>
      </div>
    </div>
  )
}
