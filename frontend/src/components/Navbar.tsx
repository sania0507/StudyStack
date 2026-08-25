import { Link, NavLink, useNavigate } from "react-router-dom"
import { LogOut, Moon, Sun } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { useTimer, formatClock } from "@/context/TimerContext"
import { useTheme } from "@/context/ThemeContext"
import { Avatar, cx } from "@/components/ui"
import Logo from "@/components/Logo"

/*
  ============================================================
  Navbar — shown on every logged-in page
  ============================================================
  Two React Router pieces to learn here:

  <Link>    = a client-side anchor. Swaps the page without a
              full browser reload.
  <NavLink> = the same, but it tells you if it's the ACTIVE
              route, so you can highlight the current tab.
              Its className can be a function: ({isActive}) => ...
*/

const LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/analytics", label: "Analytics" },
]

export default function Navbar() {
  const { user, logout } = useAuth()
  const { secondsLeft, isRunning } = useTimer()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate() // lets us redirect from JS, not a click

  function handleLogout() {
    logout()
    navigate("/") // send them back to the landing page
  }

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-base/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center gap-4 px-4 sm:px-6">
        <Link to="/dashboard" className="shrink-0">
          <Logo />
        </Link>

        <nav className="ml-2 hidden items-center gap-1 sm:flex">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                cx(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-elevated text-ink" : "text-muted hover:text-ink",
                )
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          {/* Mini timer readout — reassures you it's still running. */}
          <span className="hidden items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs tabular-nums text-muted xs:flex">
            <span
              className={cx("h-1.5 w-1.5 rounded-full", isRunning ? "animate-pulse bg-mint" : "bg-faint")}
              aria-hidden="true"
            />
            {formatClock(secondsLeft)}
          </span>

          <button
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="grid h-9 w-9 place-items-center rounded-lg text-faint transition-colors hover:bg-elevated hover:text-ink"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          <NavLink
            to="/profile"
            className={({ isActive }) =>
              cx(
                "flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 transition-colors",
                isActive ? "border-violet-soft/60 bg-elevated" : "border-line hover:bg-elevated",
              )
            }
          >
            <Avatar name={user?.name ?? "?"} url={user?.avatarUrl} size={28} />
            <span className="text-xs font-medium text-ink">{user?.name?.split(" ")[0]}</span>
          </NavLink>

          <button
            onClick={handleLogout}
            aria-label="Log out"
            className="grid h-9 w-9 place-items-center rounded-lg text-faint transition-colors hover:bg-elevated hover:text-ink"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </header>
  )
}
