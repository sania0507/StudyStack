import { createContext, useEffect, useContext, useMemo, useState, type ReactNode } from "react"
import { type Domain } from "@/api/mock"

type DomainsValue = {
  domains: Domain[]
  addDomain: (name: string) => void
}

const DomainsContext = createContext<DomainsValue | null>(null)

export function DomainsProvider({ children }: { children: ReactNode }) {
  const [domains, setDomains] = useState<Domain[]>([])

  useEffect(() => {
    async function loadDomains() {
      const response = await fetch("http://localhost:8000/domains")

      if (!response.ok) {
        throw new Error("Failed to fetch domains")
      }

      const data: Domain[] = await response.json()

      console.log("DOMAINS FROM BACKEND:", data)

      setDomains(data)
    }

    loadDomains()
  }, [])

  async function addDomain(name: string) {
    const clean = name.trim()

    if (!clean) return

    const response = await fetch("http://localhost:8000/domains", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: clean,
      }),
    })

    if (!response.ok) {
      throw new Error("Failed to add domain")
    }

    const newDomain: Domain = await response.json()

    setDomains((prev) => [...prev, newDomain])
  }

  const value = useMemo(() => ({ domains, addDomain }), [domains])

  return (
    <DomainsContext.Provider value={value}>
      {children}
    </DomainsContext.Provider>
  )
}

export function useDomains() {
  const ctx = useContext(DomainsContext)

  if (!ctx) {
    throw new Error("useDomains must be used inside <DomainsProvider>")
  }

  return ctx
}