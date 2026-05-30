import { useState, useEffect, useRef } from "react";

// ---------------------------------------------------------------------------
// Column shape returned by GET /mcp/tools/list_table_columns?table=TABLE_NAME
// ---------------------------------------------------------------------------
export type ColumnMeta = {
  column_name: string;
  data_type: string;
  not_null: boolean;
  primary_key: boolean;
  qualified_name: string; // "TABLE.COLUMN"
};

type FetchState = {
  columns: ColumnMeta[];
  isLoading: boolean;
  error: string | null;
};

const IDLE: FetchState = { columns: [], isLoading: false, error: null };

// ---------------------------------------------------------------------------
// useColumnsByTable
//
// Binds the column list to the currently selected source table.
// Only fires when edgeType === "CONTAINS" and tableName is non-empty.
// Results are cached in-memory by table name for the component lifetime —
// switching tables and back doesn't trigger a redundant network round-trip.
//
// Usage:
//   const { columns, isLoading, error } = useColumnsByTable(sourceTable, selectedEdgeType);
//
// When edgeType !== "CONTAINS" the hook returns IDLE immediately so the
// caller can branch on edgeType without needing an extra conditional.
// ---------------------------------------------------------------------------
export function useColumnsByTable(
  tableName: string,
  edgeType: string,
): FetchState {
  const [state, setState] = useState<FetchState>(IDLE);

  // In-memory cache: tableName → ColumnMeta[].
  // Keyed by the raw table name string so mixed-case variants stay separate.
  const cache = useRef<Map<string, ColumnMeta[]>>(new Map());

  useEffect(() => {
    // Only active for CONTAINS edges.
    if (edgeType !== "CONTAINS") {
      setState(IDLE);
      return;
    }

    const table = tableName.trim();
    if (!table) {
      setState(IDLE);
      return;
    }

    // Cache hit — no fetch needed.
    if (cache.current.has(table)) {
      setState({ columns: cache.current.get(table)!, isLoading: false, error: null });
      return;
    }

    let cancelled = false;
    setState({ columns: [], isLoading: true, error: null });

    fetch(`/mcp/tools/list_table_columns?table=${encodeURIComponent(table)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ columns: ColumnMeta[] }>;
      })
      .then(({ columns }) => {
        if (cancelled) return;
        cache.current.set(table, columns);
        setState({ columns, isLoading: false, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setState({ columns: [], isLoading: false, error: msg });
      });

    return () => {
      cancelled = true;
    };
  }, [tableName, edgeType]);

  return state;
}
