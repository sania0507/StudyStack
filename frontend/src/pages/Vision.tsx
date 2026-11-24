import { useCallback, useEffect, useRef, useState } from "react"
import { Plus, Trash2, Upload } from "lucide-react"
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
*/

const BOARD_HEIGHT_PX = 620
const IMAGE_SIZE_PX = 168

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
    x: 6 + (index % perRow) * 22,
    y: 8 + (Math.floor(index / perRow) % 4) * 22,
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

    const x = (leftPx / rect.width) * 100
    const y = (topPx / rect.height) * 100

    // Keep at least a sliver on the board: 0..100 of the *image's* top-left,
    // with a floor that still lets most of it hang over the edge.
    return {
      x: Math.min(100, Math.max(0, x)),
      y: Math.min(100, Math.max(0, y)),
    }
  }, [])

  function startDrag(event: React.PointerEvent, item: VisionItem) {
    // Ignore right-click and anything that is not a primary press.
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
      const spot = nextFreeSpot(items)
      const placed = await api.moveVisionItem(created.id, spot)
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
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Vision board</h1>
          <p className="mt-1 text-sm text-muted">
            Drag images anywhere. This is the reason the rest of it matters.
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
            <Plus size={14} /> Paste a link
          </Button>
        </div>
      </div>

      {showLink && (
        <Card>
          <form onSubmit={addLink} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Field
                label="Image address"
                placeholder="https://i.pinimg.com/....jpg"
                value={link}
                onChange={(e) => setLink(e.target.value)}
                autoFocus
              />
              <p className="mt-1 text-[11px] text-faint">
                On Pinterest: right-click the pin → Copy image address. The image is saved to
                your board, so it will not break later.
              </p>
            </div>
            <Button size="sm" type="submit" disabled={busy || !link.trim()}>
              Add to board
            </Button>
          </form>
        </Card>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      <div
        ref={boardRef}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={endDrag}
        className="relative overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface"
        style={{ height: BOARD_HEIGHT_PX }}
      >
        {loading && (
          <p className="absolute inset-0 grid place-items-center text-sm text-muted">
            Loading your board…
          </p>
        )}

        {!loading && items.length === 0 && (
          <div className="absolute inset-0 grid place-items-center px-6 text-center">
            <div className="flex flex-col items-center gap-2">
              <p className="font-display text-lg text-ink">A blank wall</p>
              <p className="max-w-sm text-sm text-muted">
                Upload an image, or paste a link to a pin. Then drag things around until it feels
                like yours.
              </p>
            </div>
          </div>
        )}

        {items.map((item) => (
          <VisionTile
            key={item.id}
            item={item}
            selected={selected === item.id}
            dragging={dragging?.id === item.id}
            onPointerDown={(e) => startDrag(e, item)}
            onDelete={() => remove(item.id)}
          />
        ))}
      </div>

      <p className="text-xs text-faint">
        {items.length} image{items.length === 1 ? "" : "s"} · click an image to reveal its delete
        button · positions save when you let go
      </p>
    </div>
  )
}

/** One draggable image, with its own lazily-fetched blob URL. */
function VisionTile({
  item,
  selected,
  dragging,
  onPointerDown,
  onDelete,
}: {
  item: VisionItem
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
        width: IMAGE_SIZE_PX,
        // touch-action: none is what stops the page scrolling instead of the
        // image moving on a phone or trackpad.
        touchAction: "none",
        cursor: dragging ? "grabbing" : "grab",
      }}
      className={cx(
        "absolute select-none rounded-xl bg-elevated shadow-lg transition-shadow",
        dragging ? "z-30 shadow-xl" : "z-10 hover:shadow-xl",
        selected && "ring-2 ring-violet-soft/70",
      )}
    >
      {src ? (
        <img
          src={src}
          alt={item.caption ?? "Vision board image"}
          draggable={false}
          className="pointer-events-none w-full rounded-xl object-cover"
          style={{ height: IMAGE_SIZE_PX }}
        />
      ) : (
        <div
          className="grid w-full place-items-center rounded-xl text-xs text-faint"
          style={{ height: IMAGE_SIZE_PX }}
        >
          loading…
        </div>
      )}

      {item.caption && (
        <p className="absolute inset-x-0 bottom-0 truncate rounded-b-xl bg-base/70 px-2 py-1 text-[11px] text-ink">
          {item.caption}
        </p>
      )}

      {selected && (
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={onDelete}
          aria-label="Remove from board"
          className="absolute -right-2 -top-2 grid h-7 w-7 place-items-center rounded-full border border-line bg-base text-faint hover:border-danger/50 hover:text-danger"
        >
          <Trash2 size={13} />
        </button>
      )}
    </div>
  )
}
