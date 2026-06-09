// M7-undo — Remove a previously committed edge by its edge_id
// Live: DELETE /mcp/tools/commit_edge?edge_id=...
export async function undoEdge(edgeId: string): Promise<{ ok: boolean; message: string }> {
  const res = await fetch(`/mcp/tools/commit_edge?edge_id=${encodeURIComponent(edgeId)}`, {
    method: "DELETE",
  });
  const data = await res.json();
  if (!res.ok) return { ok: false, message: data.detail ?? data.error ?? `HTTP ${res.status}` };
  return { ok: true, message: data.message ?? "Edge removed" };
}

// M8-graph-stats — Fetch total edge count from the backend graph_stats endpoint.
// Live: GET /mcp/tools/graph_stats
export type GraphStats = {
  total_edges: number;
  arango_available: boolean;
  collections: Record<string, number>;
  sqlite_bridge_rows: number;
  sql_graph_authored_rows?: number;
};

export async function fetchGraphStats(): Promise<GraphStats | null> {
  try {
    const res = await fetch("/mcp/tools/graph_stats");
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
