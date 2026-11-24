import { useCallback, useEffect, useRef, useState } from "react"
import { ImagePlus, Link2, Sparkles, Trash2, Upload } from "lucide-react"
import * as api from "@/api/client"
import type { VisionItem } from "@/api/types"
import { Button, Card, Field, cx } from "@/components/ui"

/*
  ============================================================
  Vision — a board you drag images around, to remember why
  ============================================================
  THE BOARD IS FIXED HEIGHT on purpose. Positions are stored as
  percentages of the board, so a fixed box means the layout the
  user arranged is the layout they get back on any screen size.
  A board that grew with its content would make "40% from the
  top" mean something different every time.

  THE DRAG TRICK:
    1. pointerdown on an image: remember where the pointer
       started and where the image started (grab offset).
    2. pointermove: convert the pointer position into a
       percentage of the board, clamp it, and update state so
       the image follows the finger.
    3. pointerup: send ONE patch. Not one per move — that would
       be ~80 requests per drag.

  setPointerCapture is what makes the image keep receiving
  events even when the cursor outruns it.

  Everything decorative (.ss-board-grid, .ss-drift, .ss-pop) is
  pointer-events-none: a pretty gradient must never swallow a
  drag.
*/

const BOARD_HEIGHT_PX = 620
const TILE_WIDTH_PX = 172

/** Loose rotation per tile, derived from the id so it never jitters on re-render. */
function tiltFor(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i += 1) hash = (hash * 31 + id.charCodeAt(i)) % 1000

  // -4 .. +4 degrees: enough to feel hand-placed, not enough to look broken.
  return (hash / 1000) * 8 - 4
}

type Dragging = {
  id: string
  // Offset from the image's top-left to where the pointer grabbed it.
  grabX: number
  grabY: number
}

/** New images appear in a loose grid so they never stack on top of each other. */
function nextFreeSpot(items: VisionItem[]): { x: number; y: number } {
  const perRow = 4
  const index = items.length

  return {
    x: 5 + (index % perRow) * 23,
    y: 7 + (Math.floor(index / perRow) % 4) * 23,
  }
}

export default function Vision() {
  const [items, setItems] = useState<VisionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [link, setLink] = useState("")
  const [showLink, setShowLink] = useState(false)
  const [dragging, setDragging] = useState<Dragging | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  const boardRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let cancelled = false

    api
      .getVisionItems()
      .then((list) => {
        if (!cancelled) setItems(list)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load your board.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  /** Pointer position as a percentage of the board, clamped to stay visible. */
  const toPercent = useCallback((clientX: number, clientY: number, grab: Dragging) => {
    const board = boardRef.current
    if (!board) return null

    const rect = board.getBoundingClientRect()

    const leftPx = clientX - grab.grabX - rect.left
    const topPx = clientY - grab.grabY - rect.top

    return {
      x: Math.min(100, Math.max(0, (leftPx / rect.width) * 100)),
      y: Math.min(100, Math.max(0, (topPx / rect.height) * 100)),
    }
  }, [])

  function startDrag(event: React.PointerEvent, item: VisionItem) {
    if (event.button !== 0) return

    const target = event.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()

    target.setPointerCapture(event.pointerId)

    setSelected(item.id)
    setDragging({
      id: item.id,
      grabX: event.clientX - rect.left,
      grabY: event.clientY - rect.top,
    })
  }

  function onPointerMove(event: React.PointerEvent) {
    if (!dragging) return

    const next = toPercent(event.clientX, event.clientY, dragging)
    if (!next) return

    setItems((prev) =>
      prev.map((i) => (i.id === dragging.id ? { ...i, x: next.x, y: next.y } : i)),
    )
  }

  async function endDrag() {
    if (!dragging) return

    const item = items.find((i) => i.id === dragging.id)
    setDragging(null)

    if (!item) return

    try {
      await api.moveVisionItem(item.id, { x: item.x, y: item.y })
    } catch {
      setError("Could not save that position.")
    }
  }

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    setBusy(true)
    setError(null)

    try {
      const created = await api.addVisionFromUpload(file)
      const placed = await api.moveVisionItem(created.id, nextFreeSpot(items))
      setItems((prev) => [...prev, placed])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add that image.")
    } finally {
      setBusy(false)
      event.target.value = ""
    }
  }

  async function addLink(event: React.FormEvent) {
    event.preventDefault()

    const url = link.trim()
    if (!url) return

    setBusy(true)
    setError(null)

    try {
      const created = await api.addVisionFromUrl(url)
      const placed = await api.moveVisionItem(created.id, nextFreeSpot(items))
      setItems((prev) => [...prev, placed])
      setLink("")
      setShowLink(false)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not fetch that image. Try right-clicking the pin and copying the image address.",
      )
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    const snapshot = items
    setItems((prev) => prev.filter((i) => i.id !== id))
    setSelected(null)

    try {
      await api.deleteVisionItem(id)
    } catch {
      setItems(snapshot)
      setError("Could not delete that image.")
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* ---------------- header ---------------- */}
      <div className="ss-rise flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 font-display text-2xl font-semibold tracking-tight text-ink">
            Vision board
            <Sparkles size={18} className="text-violet-soft" aria-hidden="true" />
          </h1>
          <p className="mt-1 text-sm text-muted">
            The version of you this is all for. Drag things until it feels right.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={handleFile}
            className="hidden"
          />
          <Button size="sm" onClick={() => fileRef.current?.click()} disabled={busy}>
            <Upload size={14} /> {busy ? "Working…" : "Upload image"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowLink((v) => !v)}
            disabled={busy}
          >
            <Link2 size={14} /> Paste a link
          </Button>
        </div>
      </div>

      {/* ---------------- paste-a-link panel ---------------- */}
      {showLink && (
        <Card className="ss-rise">
          <form onSubmit={addLink} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Field
                label="Image address"
                placeholder="https://i.pinimg.com/....jpg"
                value={link}
                onChange={(e) => setLink(e.target.value)}
                autoFocus
              />
              <p className="mt-1.5 text-[11px] leading-relaxed text-faint">
                On Pinterest: right-click the pin → <b className="font-medium text-muted">Copy
                image address</b>. We save the picture itself, so the tile will not break later
                when Pinterest changes its links.
              </p>
            </div>
            <Button size="sm" type="submit" disabled={busy || !link.trim()}>
              Add to board
            </Button>
          </form>
        </Card>
      )}

      {error && (
        <p className="ss-rise rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      {/* ---------------- the board ---------------- */}
      <div
        ref={boardRef}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={endDrag}
        className="ss-board-grid relative overflow-hidden rounded-[calc(var(--radius-card)+6px)] border border-line bg-base"
        style={{ height: BOARD_HEIGHT_PX }}
      >
        {/* Soft violet wash in the corners. Decorative only. */}
        <div
          aria-hidden="true"
          className="ss-drift pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-violet/20 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="ss-drift-slow pointer-events-none absolute -bottom-28 -right-20 h-80 w-80 rounded-full bg-violet-soft/15 blur-3xl"
        />

        {loading && (
          <p className="absolute inset-0 grid place-items-center text-sm text-muted">
            Loading your board…
          </p>
        )}

        {!loading && items.length === 0 && (
          <div className="absolute inset-0 grid place-items-center px-6 text-center">
            <div className="ss-rise flex max-w-sm flex-col items-center gap-3">
              <span className="grid h-14 w-14 place-items-center rounded-2xl border border-line bg-surface text-violet-soft shadow-lg">
                <ImagePlus size={22} aria-hidden="true" />
              </span>
              <p className="font-display text-lg text-ink">A blank wall, for now</p>
              <p className="text-sm leading-relaxed text-muted">
                Upload a picture, or paste a link to a pin. Then drag things around until the
                board looks like the life you are aiming at.
              </p>
              <div className="mt-1 flex gap-2">
                <Button size="sm" onClick={() => fileRef.current?.click()} disabled={busy}>
                  <Upload size={14} /> Upload
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowLink(true)}>
                  <Link2 size={14} /> Paste a link
                </Button>
              </div>
            </div>
          </div>
        )}

        {items.map((item) => (
          <VisionTile
            key={item.id}
            item={item}
            tilt={tiltFor(item.id)}
            selected={selected === item.id}
            dragging={dragging?.id === item.id}
            onPointerDown={(e) => startDrag(e, item)}
            onDelete={() => remove(item.id)}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-faint">
        <span>
          {items.length} image{items.length === 1 ? "" : "s"} · click a tile for its delete button
        </span>
        <span>Positions save when you let go</span>
      </div>
    </div>
  )
}

/** One draggable image, with its own lazily-fetched blob URL. */
function VisionTile({
  item,
  tilt,
  selected,
  dragging,
  onPointerDown,
  onDelete,
}: {
  item: VisionItem
  tilt: number
  selected: boolean
  dragging: boolean
  onPointerDown: (event: React.PointerEvent) => void
  onDelete: () => void
}) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let revoked = false
    let objectUrl: string | null = null

    api
      .fetchVisionImage(item.id)
      .then((url) => {
        objectUrl = url
        if (url && !revoked) setSrc(url)
      })
      .catch(() => undefined)

    return () => {
      revoked = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [item.id])

  return (
    <div
      onPointerDown={onPointerDown}
      style={{
        left: `${item.x}%`,
        top: `${item.y}%`,
        width: TILE_WIDTH_PX,
        // The resting tilt is a transform, and a dragged tile straightens up:
        // "picked it off the wall", then it settles back.
        transform: dragging ? "scale(1.04) rotate(0deg)" : `rotate(${tilt}deg)`,
        touchAction: "none",
        cursor: dragging ? "grabbing" : "grab",
      }}
      className={cx(
        "ss-pop absolute select-none rounded-2xl border border-line/60 bg-elevated p-1.5 shadow-xl",
        "transition-[transform,box-shadow] duration-200 will-change-transform",
        dragging ? "z-40 shadow-2xl ring-2 ring-violet-soft/60" : "z-10 hover:shadow-2xl",
        selected && !dragging && "ring-2 ring-violet-soft/70",
      )}
    >
      {src ? (
        <img
          src={src}
          alt={item.caption ?? "Vision board image"}
          draggable={false}
          className="pointer-events-none w-full rounded-xl object-cover"
          style={{ height: TILE_WIDTH_PX }}
        />
      ) : (
        <div
          className="grid w-full place-items-center rounded-xl bg-surface text-xs text-faint"
          style={{ height: TILE_WIDTH_PX }}
        >
          loading…
        </div>
      )}

      {item.caption && (
        <p className="absolute inset-x-1.5 bottom-1.5 truncate rounded-b-xl bg-base/75 px-2 py-1 text-[11px] text-ink backdrop-blur-sm">
          {item.caption}
        </p>
      )}

      {selected && (
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={onDelete}
          aria-label="Remove from board"
          className="absolute -right-2.5 -top-2.5 grid h-7 w-7 place-items-center rounded-full border border-line bg-base text-faint shadow-lg transition-colors hover:border-danger/50 hover:text-danger"
        >
          <Trash2 size={13} />
        </button>
      )}
    </div>
  )
}
