import { RouterProvider } from "react-router/dom";

import { AppProviders } from "./providers";
import { router } from "./router";

/** Root component: app-wide providers around the router. */
export function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
