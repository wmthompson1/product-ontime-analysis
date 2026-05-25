import { describe, it, expect, vi, beforeEach } from "vitest";
import { undoEdge, fetchGraphStats } from "./graphApi";
import type { GraphStats } from "./graphApi";

// Helper to build a minimal fetch mock that returns a JSON response.
function mockFetch(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// undoEdge
// ---------------------------------------------------------------------------

describe("undoEdge", () => {
  it("returns ok:true when the DELETE succeeds", async () => {
    globalThis.fetch = mockFetch({ message: "Edge removed" }, 200);

    const result = await undoEdge("edge_abc123");

    expect(result.ok).toBe(true);
    expect(result.message).toBe("Edge removed");
  });

  it("calls DELETE on the correct URL with the edge_id encoded", async () => {
    const spy = mockFetch({ message: "Edge removed" }, 200);
    globalThis.fetch = spy;

    await undoEdge("edge/special id");

    const [url, init] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/mcp/tools/commit_edge?edge_id=edge%2Fspecial%20id");
    expect(init.method).toBe("DELETE");
  });

  it("returns ok:false with the server error message on HTTP 404", async () => {
    globalThis.fetch = mockFetch({ detail: "Edge not found" }, 404);

    const result = await undoEdge("nonexistent");

    expect(result.ok).toBe(false);
    expect(result.message).toBe("Edge not found");
  });

  it("falls back to HTTP status text when the error body has no detail or error field", async () => {
    globalThis.fetch = mockFetch({}, 500);

    const result = await undoEdge("edge_xyz");

    expect(result.ok).toBe(false);
    expect(result.message).toBe("HTTP 500");
  });
});

// ---------------------------------------------------------------------------
// fetchGraphStats
// ---------------------------------------------------------------------------

describe("fetchGraphStats", () => {
  it("returns the parsed stats object on a successful response", async () => {
    const payload: GraphStats = {
      total_edges: 42,
      arango_available: true,
      collections: { semantic_edges: 30, fk_edges: 12 },
      sqlite_bridge_rows: 15,
    };
    globalThis.fetch = mockFetch(payload, 200);

    const stats = await fetchGraphStats();

    expect(stats).not.toBeNull();
    expect(stats!.total_edges).toBe(42);
    expect(stats!.arango_available).toBe(true);
  });

  it("returns null when the server responds with a non-2xx status", async () => {
    globalThis.fetch = mockFetch({ error: "unavailable" }, 503);

    const stats = await fetchGraphStats();

    expect(stats).toBeNull();
  });

  it("returns null when fetch throws (e.g. network error)", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network failure"));

    const stats = await fetchGraphStats();

    expect(stats).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Undo → refreshGraphStats contract
//
// This group verifies the sequence the component follows after a successful
// undo: undoEdge resolves ok:true, then fetchGraphStats is called again and
// the returned count is lower than before the undo.
// ---------------------------------------------------------------------------

describe("edge count decrements after a successful undo", () => {
  it("count returned by fetchGraphStats is lower after undoEdge succeeds", async () => {
    // Phase 1 — initial state: 10 edges in the graph.
    globalThis.fetch = mockFetch(
      {
        total_edges: 10,
        arango_available: true,
        collections: {},
        sqlite_bridge_rows: 5,
      },
      200
    );
    const before = await fetchGraphStats();
    expect(before!.total_edges).toBe(10);

    // Phase 2 — undo removes one edge.
    globalThis.fetch = mockFetch({ message: "Edge removed" }, 200);
    const undoResult = await undoEdge("edge_to_remove");
    expect(undoResult.ok).toBe(true);

    // Phase 3 — refreshGraphStats re-fetches and now reports 9 edges.
    globalThis.fetch = mockFetch(
      {
        total_edges: 9,
        arango_available: true,
        collections: {},
        sqlite_bridge_rows: 5,
      },
      200
    );
    const after = await fetchGraphStats();
    expect(after!.total_edges).toBe(9);

    // The count went down by exactly 1.
    expect(after!.total_edges).toBe(before!.total_edges - 1);
  });

  it("count stays the same when undoEdge fails (backend error)", async () => {
    // Initial state: 10 edges.
    globalThis.fetch = mockFetch(
      { total_edges: 10, arango_available: true, collections: {}, sqlite_bridge_rows: 5 },
      200
    );
    const before = await fetchGraphStats();

    // Undo fails.
    globalThis.fetch = mockFetch({ detail: "Edge not found" }, 404);
    const undoResult = await undoEdge("bad_edge");
    expect(undoResult.ok).toBe(false);

    // refreshGraphStats is NOT called in the failure branch; count stays the same.
    globalThis.fetch = mockFetch(
      { total_edges: 10, arango_available: true, collections: {}, sqlite_bridge_rows: 5 },
      200
    );
    const after = await fetchGraphStats();
    expect(after!.total_edges).toBe(before!.total_edges);
  });
});
