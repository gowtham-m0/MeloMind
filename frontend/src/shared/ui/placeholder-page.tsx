import type { ReactNode } from "react";
import { useParams } from "react-router";

interface PlaceholderPageProps {
  title: string;
  children?: ReactNode;
}

/** Stand-in for a page a later phase builds. Lists the route's params so routing is visible. */
export function PlaceholderPage({ title, children }: PlaceholderPageProps) {
  const params = Object.entries(useParams());

  return (
    <section aria-labelledby="page-title" className="space-y-4">
      <h1 id="page-title" className="text-3xl font-semibold">
        {title}
      </h1>
      {children ?? <p className="text-muted-foreground">This page is a placeholder.</p>}
      {params.length > 0 && (
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-muted-foreground">
          {params.map(([name, value]) => (
            <div key={name} className="flex gap-2">
              <dt>{name}:</dt>
              <dd className="font-mono">{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
