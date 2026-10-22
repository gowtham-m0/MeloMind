import { Link, Outlet, useParams } from "react-router";

/**
 * Person mode: full screen, large text and no navigation. The only way out is the
 * caregiver unlock, which is a plain link here until the 3-second long press is built.
 */
export function PersonLayout() {
  const { id } = useParams();

  return (
    <div className="fixed inset-0 flex flex-col bg-background text-2xl text-foreground">
      <div className="flex justify-end p-2">
        <Link
          to={id ? `/profiles/${id}` : "/profiles"}
          className="inline-flex min-h-11 min-w-11 items-center rounded-md px-3 text-base text-muted-foreground"
        >
          Caregiver unlock (placeholder)
        </Link>
      </div>
      <main className="flex flex-1 items-center justify-center overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
