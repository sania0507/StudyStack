
import {
  createContext,
  useCallback,
  useEffect,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { createDomain, deleteDomain, getDomains, updateDomain } from "@/api/client"
import type { Domain } from "@/api/types"
import { useAuth } from "@/context/AuthContext"

type DomainsValue = {
  domains: Domain[]
  isLoading: boolean
  addDomain: (name: string, repeatsDaily?: boolean) => Promise<void>
  setRepeatsDaily: (id: string, repeatsDaily: boolean) => Promise<void>
  renameDomain: (id: string, name: string) => Promise<void>
  removeDomain: (id: string) => Promise<void>
  reloadDomains: () => Promise<void>
}

const DomainsContext = createContext<DomainsValue | null>(null)

export function DomainsProvider({ children }: { children: ReactNode }) {
  const [domains, setDomains] = useState<Domain[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const { user } = useAuth()

  // `user` is the trigger: domains load after login and clear on logout,
  // so one account never sees another's data.
  const loadDomains = useCallback(async () => {
    if (!user) {
      setDomains([])
      return
    }

    setIsLoading(true)

    try {
      setDomains(await getDomains())
    } catch (error) {
      console.error("Failed to load domains:", error)
    } finally {
      setIsLoading(false)
    }
  }, [user])

  useEffect(() => {
    loadDomains()
  }, [loadDomains])

  async function addDomain(name: string, repeatsDaily = false): Promise<void> {
    const clean = name.trim()

    if (!clean) return

    const newDomain = await createDomain(clean, repeatsDaily)

    setDomains((prev) => [...prev, newDomain])
  }

  async function setRepeatsDaily(id: string, repeatsDaily: boolean): Promise<void> {
    const updated = await updateDomain(id, { repeatsDaily })

    setDomains((prev) => prev.map((d) => (d.id === id ? updated : d)))
  }

  async function renameDomain(id: string, name: string): Promise<void> {
    const clean = name.trim()

    if (!clean) return

    const updated = await updateDomain(id, { name: clean })

    setDomains((prev) =>
      prev.map((domain) => (domain.id === id ? updated : domain)),
    )
  }

  async function removeDomain(id: string): Promise<void> {
    await deleteDomain(id)

    setDomains((prev) => prev.filter((domain) => domain.id !== id))
  }

  const value = useMemo(
    () => ({
      domains,
      isLoading,
      addDomain,
      setRepeatsDaily,
      renameDomain,
      removeDomain,
      reloadDomains: loadDomains,
    }),
    [domains, isLoading, loadDomains],
  )

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
