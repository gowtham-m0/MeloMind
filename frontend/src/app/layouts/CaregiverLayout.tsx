import { cn } from "cn";
import { NavLink, Outlet, ScrollRestoration } from "react-router";

const navItems = [
  { to: "/", label: "Home", end: true },
  { to: "/profiles", label: "Profiles", end: false },
  { to: "/how-it-works", label: "How it works", end: false },
];

/** Caregiver screens: calm header navigation, 18 px base text and 44 px tap targets. */
export function CaregiverLayout() {
  return (
    <div className="min-h-dvh bg-background text-lg text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:inline-flex focus:min-h-11 focus:items-center focus:rounded-md focus:bg-background focus:px-4"
      >
        Skip to content
      </a>
      <header className="border-b">
        <nav
          aria-label="Main"
          className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2"
        >
          <span className="mr-auto text-xl font-semibold">MeloMind</span>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "inline-flex min-h-11 items-center rounded-md px-4 underline-offset-4 hover:underline",
                  isActive && "bg-secondary font-semibold",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main id="main" className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
      <ScrollRestoration />
    </div>
  );
}
