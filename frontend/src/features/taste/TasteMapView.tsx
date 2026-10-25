import { useEffect, useRef, useState } from "react";

import type { TasteMap, TasteMapNode } from "@/shared/api/taste";
import { Skeleton } from "@/shared/ui/states";

const KIND_VARS: Record<string, string> = {
  artist: "--music",
  song: "--music",
  movie: "--film",
  tv_show: "--tv",
  book: "--book",
  place: "--muted",
  entry: "--line",
};

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#999";
}

interface TasteMapViewProps {
  map: TasteMap;
  onOpen: (node: TasteMapNode) => void;
}

/**
 * The taste map as a graph (Cytoscape.js, loaded only on this page): round thumbnails coloured
 * by type, journal entries as small dots, and the `because_of` and `mentions` links between
 * them. Tap a node to open it. The list view next to it shows the same data for keyboards and
 * screen readers.
 */
export function TasteMapView({ map, onOpen }: TasteMapViewProps) {
  const container = useRef<HTMLDivElement>(null);
  const onOpenRef = useRef(onOpen);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    onOpenRef.current = onOpen;
  }, [onOpen]);

  useEffect(() => {
    let destroyed = false;
    let destroy: () => void = () => undefined;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    void import("cytoscape").then(({ default: cytoscape }) => {
      if (destroyed || !container.current) {
        return;
      }
      const byId = new Map(map.nodes.map((node) => [node.id, node]));
      const graph = cytoscape({
        container: container.current,
        elements: [
          ...map.nodes.map((node) => ({
            data: {
              id: node.id,
              label: node.kind === "entry" ? "" : node.title,
              image: node.image_url ?? "",
              color: cssVar(KIND_VARS[node.kind] ?? "--muted"),
              size: node.kind === "entry" ? 14 : 34 + Math.round(node.weight * 18),
            },
          })),
          ...map.links.map((link, index) => ({
            data: { id: `l${index}`, source: link.from, target: link.to, kind: link.kind },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              width: "data(size)",
              height: "data(size)",
              shape: "ellipse",
              "background-color": "data(color)",
              "background-opacity": 0.9,
              "border-width": 3,
              "border-color": "data(color)",
              label: "data(label)",
              "font-family": "Switzer, system-ui, sans-serif",
              "font-size": 11,
              "font-weight": 600,
              color: cssVar("--ink"),
              "text-valign": "bottom",
              "text-margin-y": 6,
              "text-wrap": "ellipsis",
              "text-max-width": "96px",
              "text-background-color": "#ffffff",
              "text-background-opacity": 0.85,
              "text-background-padding": "2px",
              "text-background-shape": "roundrectangle",
            },
          },
          {
            selector: "node[image != '']",
            style: {
              "background-image": "data(image)",
              "background-fit": "cover",
              // "null" loads images without CORS (Cytoscape supports it; its types don't list
              // it). The canvas is never read back, so a cross-origin image is fine here.
              "background-image-crossorigin": "null" as "anonymous",
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.5,
              "line-color": cssVar("--line"),
              "curve-style": "bezier",
            },
          },
          {
            selector: "edge[kind = 'because_of']",
            style: { "line-style": "dashed", "line-color": cssVar("--primary") },
          },
        ],
        layout: {
          name: "cose",
          animate: !reduceMotion,
          animationDuration: 400,
          padding: 24,
          nodeRepulsion: () => 9000,
          idealEdgeLength: () => 70,
        },
        minZoom: 0.4,
        maxZoom: 2.5,
        wheelSensitivity: 0.3,
      });
      graph.on("tap", "node", (event) => {
        const node = byId.get(event.target.id() as string);
        if (node) {
          onOpenRef.current(node);
        }
      });
      destroy = () => graph.destroy();
      setReady(true);
    });

    return () => {
      destroyed = true;
      destroy();
    };
  }, [map]);

  return (
    <div className="relative h-[420px] w-full overflow-hidden rounded-2xl border border-hairline bg-[radial-gradient(circle_at_center,var(--surface)_0%,var(--surface-2)_100%)] md:h-[520px]">
      {!ready && <Skeleton className="absolute inset-4" />}
      <div
        ref={container}
        className="size-full"
        role="img"
        aria-label="Your taste map. Use the list view for the same items."
      />
    </div>
  );
}
