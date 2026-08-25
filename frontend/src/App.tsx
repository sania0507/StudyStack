import { Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider } from "@/context/AuthContext"
import { DomainsProvider } from "@/context/DomainsContext"
import { ThemeProvider } from "@/context/ThemeContext"
import { TimerProvider } from "@/context/TimerContext"
import AppLayout from "@/components/AppLayout"
import ProtectedRoute from "@/components/ProtectedRoute"

import Landing from "@/pages/Landing"
import Login from "@/pages/Login"
import Register from "@/pages/Register"
import Dashboard from "@/pages/Dashboard"
import Analytics from "@/pages/Analytics"
import Profile from "@/pages/Profile"

/*
  ============================================================
  App.tsx — the map of the entire application
  ============================================================
  Read the JSX below like an outline of your app. This is the
  file you open when you ask "what pages exist and who can see
  them?"

  Structure, outside in:

    AuthProvider        who is logged in
      TimerProvider     the countdown  (above the router, so it
                        survives every navigation)
        Routes
          /             Landing   — public
          /login        Login     — public
          /register     Register  — public

          ProtectedRoute          — logged in only
            AppLayout             — navbar + timer sidebar
              /dashboard
              /analytics
              /profile

  Nesting <Route> inside <Route> means "render the child into
  the parent's <Outlet />". Two levels of nesting here:
  the guard, then the layout.
*/
export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <DomainsProvider>
          <TimerProvider>
            <Routes>
              {/* ---------- public ---------- */}
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* ---------- private ---------- */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/profile" element={<Profile />} />
                </Route>
              </Route>

              {/* Anything unrecognised goes home. */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </TimerProvider>
        </DomainsProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
