/*
  The wordmark. Three stacked bars = "stack". Kept as its own
  component so the landing page and navbar can't drift apart.
*/
export default function Logo({ size = "md" }: { size?: "md" | "lg" }) {
  const box = size === "lg" ? 32 : 24
  return (
    <span className="flex items-center gap-2.5">
      <span
        className="grid shrink-0 place-items-center rounded-lg bg-violet"
        style={{ width: box, height: box }}
        aria-hidden="true"
      >
        <span className="flex flex-col gap-[2.5px]">
          <span className="block h-[2.5px] rounded-full bg-ink" style={{ width: box * 0.5 }} />
          <span className="block h-[2.5px] rounded-full bg-ink/70" style={{ width: box * 0.38 }} />
          <span className="block h-[2.5px] rounded-full bg-ink/45" style={{ width: box * 0.26 }} />
        </span>
      </span>
      <span
        className={`font-display font-semibold tracking-tight text-ink ${size === "lg" ? "text-xl" : "text-[15px]"}`}
      >
        StudyStack
      </span>
    </span>
  )
}
