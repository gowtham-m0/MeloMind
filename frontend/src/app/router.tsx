import { createBrowserRouter } from "react-router";

import { BridgePage } from "@/pages/BridgePage";
import { HomePage } from "@/pages/HomePage";
import { HowItWorksPage } from "@/pages/HowItWorksPage";
import { MemoriesPage } from "@/pages/MemoriesPage";
import { MemoryNodePage } from "@/pages/MemoryNodePage";
import { NewProfilePage } from "@/pages/NewProfilePage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PersonModePage } from "@/pages/PersonModePage";
import { PlanSessionPage } from "@/pages/PlanSessionPage";
import { ProfileEditPage } from "@/pages/ProfileEditPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { ProfilesPage } from "@/pages/ProfilesPage";
import { ReviewPage } from "@/pages/ReviewPage";
import { SessionPage } from "@/pages/SessionPage";
import { SessionPlayPage } from "@/pages/SessionPlayPage";

import { CaregiverLayout } from "./layouts/CaregiverLayout";
import { PersonLayout } from "./layouts/PersonLayout";

/** Every route. Person mode gets its own full-screen layout with no navigation. */
export const router = createBrowserRouter([
  {
    element: <CaregiverLayout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/profiles", element: <ProfilesPage /> },
      { path: "/profiles/new", element: <NewProfilePage /> },
      { path: "/profiles/:id", element: <ProfilePage /> },
      { path: "/profiles/:id/edit", element: <ProfileEditPage /> },
      { path: "/profiles/:id/plan", element: <PlanSessionPage /> },
      { path: "/profiles/:id/memories", element: <MemoriesPage /> },
      { path: "/profiles/:id/memories/:nodeId", element: <MemoryNodePage /> },
      { path: "/profiles/:id/review", element: <ReviewPage /> },
      { path: "/profiles/:id/bridge", element: <BridgePage /> },
      { path: "/sessions/:id", element: <SessionPage /> },
      { path: "/sessions/:id/play", element: <SessionPlayPage /> },
      { path: "/how-it-works", element: <HowItWorksPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "/profiles/:id/person",
    element: <PersonLayout />,
    children: [{ index: true, element: <PersonModePage /> }],
  },
]);
