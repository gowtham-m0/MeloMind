import { createBrowserRouter } from "react-router";

import { LandingPage } from "@/pages/LandingPage";

/**
 * Every route. A profile's screens share the app shell under `/p/:profileId`. Everything past
 * the landing page loads on demand, so the first paint ships only what it shows.
 */
export const router = createBrowserRouter([
  {
    // A blank page while a lazy route's code arrives on a direct visit.
    hydrateFallbackElement: <div className="min-h-dvh bg-surface" />,
    children: [
      { path: "/", element: <LandingPage /> },
      {
        path: "/profiles",
        lazy: async () => ({ Component: (await import("@/pages/ProfilesPage")).ProfilesPage }),
      },
      {
        path: "/profiles/new",
        lazy: async () => ({
          Component: (await import("@/pages/NewProfilePage")).NewProfilePage,
        }),
      },
      {
        path: "/p/:profileId",
        lazy: async () => ({ Component: (await import("@/features/shell/AppShell")).AppShell }),
        children: [
          {
            index: true,
            lazy: async () => ({ Component: (await import("@/pages/HomePage")).HomePage }),
          },
          {
            path: "discover",
            lazy: async () => ({ Component: (await import("@/pages/DiscoverPage")).DiscoverPage }),
          },
          {
            path: "discover/:type",
            lazy: async () => ({ Component: (await import("@/pages/DiscoverPage")).DiscoverPage }),
          },
          {
            path: "saved",
            lazy: async () => ({ Component: (await import("@/pages/SavedPage")).SavedPage }),
          },
          {
            path: "settings",
            lazy: async () => ({ Component: (await import("@/pages/SettingsPage")).SettingsPage }),
          },
        ],
      },
      {
        path: "/styleguide",
        lazy: async () => ({
          Component: (await import("@/pages/StyleguidePage")).StyleguidePage,
        }),
      },
      {
        path: "*",
        lazy: async () => ({ Component: (await import("@/pages/NotFoundPage")).NotFoundPage }),
      },
    ],
  },
]);
