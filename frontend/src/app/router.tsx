import { createBrowserRouter } from "react-router";

import { LandingPage } from "@/pages/LandingPage";
import { RouteErrorPage } from "@/pages/RouteErrorPage";

/**
 * Every route. A profile's screens share the app shell under `/p/:profileId`. Everything past
 * the landing page loads on demand, so the first paint ships only what it shows.
 */
export const router = createBrowserRouter([
  {
    // A blank page while a lazy route's code arrives on a direct visit.
    hydrateFallbackElement: <div className="min-h-dvh bg-surface" />,
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/", element: <LandingPage /> },
      {
        path: "/sign-in",
        lazy: async () => ({ Component: (await import("@/pages/SignInPage")).SignInPage }),
      },
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
            path: "journal",
            lazy: async () => ({ Component: (await import("@/pages/JournalPage")).JournalPage }),
          },
          {
            path: "taste",
            lazy: async () => ({ Component: (await import("@/pages/TastePage")).TastePage }),
          },
          {
            path: "taste/match",
            lazy: async () => ({ Component: (await import("@/pages/MatchPage")).MatchPage }),
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
        path: "/how-it-works",
        lazy: async () => ({
          Component: (await import("@/pages/HowItWorksPage")).HowItWorksPage,
        }),
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
