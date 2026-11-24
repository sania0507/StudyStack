import { Outlet, useLocation } from "react-router-dom"
import Navbar from "@/components/Navbar"
import TimerPanel from "@/components/TimerPanel"

/*
  ============================================================
  AppLayout — the shell every logged-in page renders inside
  ============================================================
  THIS is the answer to "timer on the side no matter which page".

  <Outlet /> is a hole in this component. React Router swaps the
  matched child route into that hole. So when you go from
  /dashboard to /analytics, ONLY the Outlet's contents change —
  the Navbar and TimerPanel are never unmounted, never re-created,
  and the countdown never restarts.

  In App.tsx you'll see this expressed as nested routes:

      <Route element={<AppLayout />}>      <- shell
        <Route path="/dashboard" ... />    <- goes in the Outlet
        <Route path="/analytics" ... />    <- goes in the Outlet
      </Route>
*/
export default function AppLayout() {
  // Pages that are not about doing the work do not need a clock beside them.
  // The provider stays mounted (it lives in App.tsx, above the router), so a
  // running timer keeps running and is still there when you come back — only
  // the panel is hidden.
  const { pathname } = useLocation()
  const showTimer = !["/vision", "/notes"].includes(pathname)

  return (
    <div className="min-h-dvh bg-base">
      <Navbar />

      <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6">
        {/*
          Layout: single column on mobile, sidebar + content on lg+.
          The sidebar is `sticky` so the timer follows you as you scroll.
        */}
        <div className="flex flex-col gap-6 lg:flex-row">
          {showTimer && (
            <aside className="w-full shrink-0 lg:sticky lg:top-[5.5rem] lg:w-[268px] lg:self-start">
              <TimerPanel />
            </aside>
          )}

          <main className="min-w-0 flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
