import { createBrowserRouter } from "react-router";

import { AppShell } from "@/features/shell/AppShell";
import { DiscoverPage } from "@/pages/DiscoverPage";
import { HomePage } from "@/pages/HomePage";
import { LandingPage } from "@/pages/LandingPage";
import { NewProfilePage } from "@/pages/NewProfilePage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilesPage } from "@/pages/ProfilesPage";
import { SavedPage } from "@/pages/SavedPage";

/** Every route. A profile's screens share the app shell under `/p/:profileId`. */
export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/profiles", element: <ProfilesPage /> },
  { path: "/profiles/new", element: <NewProfilePage /> },
  {
    path: "/p/:profileId",
    element: <AppShell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "discover", element: <DiscoverPage /> },
      { path: "discover/:type", element: <DiscoverPage /> },
      { path: "saved", element: <SavedPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
