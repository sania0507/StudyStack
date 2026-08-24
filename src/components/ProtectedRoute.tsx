import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"

/*
  ============================================================
  ProtectedRoute — "you must be logged in past this point"
  ============================================================
  A route guard is just a component that either renders <Outlet />
  (let them through) or <Navigate /> (bounce them elsewhere).

  `replace` swaps the history entry instead of adding one, so the
  back button doesn't ping-pong them into the same redirect.

  NOTE: this is UX, not security. Real protection happens on the
  server. Anyone can edit client-side JS — never rely on this to
  hide actual secrets.
*/
export default function ProtectedRoute() {
  const { user } = useAuth()
  return user ? <Outlet /> : <Navigate to="/login" replace />
}
