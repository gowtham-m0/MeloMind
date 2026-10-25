import type { TasteMapNode } from "@/shared/api/taste";

/** True when the node is a Qloo item the detail sheet can open (not an entry, a place, or a
 * favourite kept as text). */
export function opensDetail(node: TasteMapNode): boolean {
  return !/^(entry|journal|fav):/.test(node.id) && node.kind !== "place";
}
