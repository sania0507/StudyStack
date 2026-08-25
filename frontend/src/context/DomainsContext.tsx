import { createContext, useContext, useMemo, useState, type ReactNode } from "react"
import { domains as seedDomains, type Domain } from "@/api/mock"

/*
  ============================================================
  DomainsContext — the one source of truth for domains
  ============================================================
  Dashboard and TimerPanel both need the same list of domains.
  If Dashboard added a domain to its own useState, the timer's
  <select> would never hear about it. So the list lives here,
  above the router, and every consumer reads the same array.
*/

type DomainsValue = {
  domains: Domain[]
  addDomain: (name: string) => void
}

const DomainsContext = createContext<DomainsValue | null>(null)

const COLOURS = ["violet", "mint", "violet-soft"]

export function DomainsProvider({ children }: { children: ReactNode }) {
  const [domains, setDomains] = useState<Domain[]>(seedDomains)

  function addDomain(name: string) {
    const clean = name.trim()
    if (!clean) return
    setDomains((prev) => [
      ...prev,
      {
        id: `d_${Date.now()}`,
        name: clean,
        colour: COLOURS[prev.length % COLOURS.length],
        minutesThisWeek: 0,
      },
    ])
  }

  const value = useMemo(() => ({ domains, addDomain }), [domains])

  return <DomainsContext.Provider value={value}>{children}</DomainsContext.Provider>
}

export function useDomains() {
  const ctx = useContext(DomainsContext)
  if (!ctx) throw new Error("useDomains must be used inside <DomainsProvider>")
  return ctx
}
