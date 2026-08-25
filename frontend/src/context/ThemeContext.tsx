import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

/*
  ============================================================
  ThemeContext — dark/light toggle, persisted locally
  ============================================================
  The tokens in index.css are dark-first. Toggling to light
  swaps the same CSS variables on <html>, so no component ever
  has to know which theme is active — they just keep writing
  bg-base / text-ink.
*/

type Theme = "dark" | "light"

type ThemeValue = {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeValue | null>(null)

function initialTheme(): Theme {
  if (typeof window === "undefined") return "dark"
  return window.localStorage.getItem("studystack-theme") === "light" ? "light" : "dark"
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme)

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle("light", theme === "light")
    root.classList.toggle("dark", theme === "dark")
    root.style.colorScheme = theme
    window.localStorage.setItem("studystack-theme", theme)

    // Keep the browser chrome in step with the page.
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", theme === "dark" ? "#0B0A0F" : "#F7F6F9")
  }, [theme])

  const value = useMemo(
    () => ({
      theme,
      toggleTheme: () => setTheme((t) => (t === "dark" ? "light" : "dark")),
    }),
    [theme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>")
  return ctx
}
