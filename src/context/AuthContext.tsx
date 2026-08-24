import { createContext, useContext, useMemo, useState, type ReactNode } from "react"
import * as api from "@/api/mock"
import type { User } from "@/api/mock"

/*
  ============================================================
  AuthContext — "who is logged in?" available everywhere
  ============================================================
  THE PROBLEM: the navbar needs the user's name. So does the
  profile page. So does the dashboard greeting. Passing `user`
  down through every component in between (prop drilling) gets
  miserable fast.

  THE FIX: Context. You put a value in at the top of the tree
  (the Provider) and any component below can pull it out with a
  hook, no matter how deep it is.

  Three pieces, always:
    1. createContext  — makes the "channel"
    2. <Provider>     — broadcasts a value into it (see App.tsx)
    3. useAuth()      — a component tunes in
*/

type AuthValue = {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
  patchUser: (patch: Partial<User>) => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  // `user` is state. When it changes, every component reading it re-renders.
  const [user, setUser] = useState<User | null>(null)

  async function login(email: string, password: string) {
    const u = await api.login(email, password) // throws on bad input — pages catch it
    setUser(u)
  }

  async function register(name: string, email: string, password: string) {
    const u = await api.register(name, email, password)
    setUser(u)
  }

  function logout() {
    setUser(null)
  }

  function patchUser(patch: Partial<User>) {
    // Never mutate state directly (user.name = "x"). Always build a NEW object,
    // or React won't know anything changed.
    setUser((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  // useMemo stops us handing a brand-new object to every consumer on each render.
  const value = useMemo(() => ({ user, login, register, logout, patchUser }), [user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Custom hook. Any component: `const { user } = useAuth()` */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>")
  return ctx
}
