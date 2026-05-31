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
// Faux column fixtures for tables that exist only in the mockup (not in
// manufacturing.db). Seeded into the per-instance cache on first call so the
// real endpoint is never hit for these names.
// ---------------------------------------------------------------------------
const FIXTURE_COLUMNS: Record<string, ColumnMeta[]> = {
  customer: [
    { column_name: "customer_id", data_type: "INTEGER", not_null: true,  primary_key: true,  qualified_name: "customer.customer_id" },
    { column_name: "first_name",  data_type: "TEXT",    not_null: true,  primary_key: false, qualified_name: "customer.first_name" },
    { column_name: "last_name",   data_type: "TEXT",    not_null: true,  primary_key: false, qualified_name: "customer.last_name" },
    { column_name: "email",       data_type: "TEXT",    not_null: false, primary_key: false, qualified_name: "customer.email" },
    { column_name: "phone",       data_type: "TEXT",    not_null: false, primary_key: false, qualified_name: "customer.phone" },
    { column_name: "created_at",  data_type: "DATETIME",not_null: true,  primary_key: false, qualified_name: "customer.created_at" },
  ],
  customer_address: [
    { column_name: "address_id",  data_type: "INTEGER", not_null: true,  primary_key: true,  qualified_name: "customer_address.address_id" },
    { column_name: "customer_id", data_type: "INTEGER", not_null: true,  primary_key: false, qualified_name: "customer_address.customer_id" },
    { column_name: "street",      data_type: "TEXT",    not_null: true,  primary_key: false, qualified_name: "customer_address.street" },
    { column_name: "city",        data_type: "TEXT",    not_null: true,  primary_key: false, qualified_name: "customer_address.city" },
    { column_name: "state",       data_type: "TEXT",    not_null: true,  primary_key: false, qualified_name: "customer_address.state" },
    { column_name: "zip",         data_type: "TEXT",    not_null: false, primary_key: false, qualified_name: "customer_address.zip" },
  ],
  sales: [
    { column_name: "sale_id",      data_type: "INTEGER", not_null: true,  primary_key: true,  qualified_name: "sales.sale_id" },
    { column_name: "customer_id",  data_type: "INTEGER", not_null: true,  primary_key: false, qualified_name: "sales.customer_id" },
    { column_name: "sale_date",    data_type: "DATETIME",not_null: true,  primary_key: false, qualified_name: "sales.sale_date" },
    { column_name: "amount_dollars",data_type:"NUMERIC", not_null: true,  primary_key: false, qualified_name: "sales.amount_dollars" },
    { column_name: "product_line", data_type: "TEXT",    not_null: false, primary_key: false, qualified_name: "sales.product_line" },
  ],
};

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

    // Seed fixture tables into cache so the network is never hit for them.
    if (!cache.current.has(table) && FIXTURE_COLUMNS[table]) {
      cache.current.set(table, FIXTURE_COLUMNS[table]);
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
        // 500/502/503 = proxy unreachable or backend not yet up.
        // Treat as "no columns available" so the UI degrades gracefully
        // rather than showing a red error. Don't cache — next table switch
        // will retry automatically.
        if (!res.ok) {
          if (cancelled) return;
          setState({ columns: [], isLoading: false, error: `unavailable:${res.status}` });
          return null;
        }
        return res.json() as Promise<{ columns: ColumnMeta[] }>;
      })
      .then((data) => {
        if (!data || cancelled) return;
        cache.current.set(table, data.columns);
        setState({ columns: data.columns, isLoading: false, error: null });
      })
      .catch(() => {
        // Network error (ECONNREFUSED proxied as 502, fetch throws on DNS/TLS
        // failures). Same soft-degrade: show empty, don't cache, allow retry.
        if (cancelled) return;
        setState({ columns: [], isLoading: false, error: "unavailable:network" });
      });

    return () => {
      cancelled = true;
    };
  }, [tableName, edgeType]);

  return state;
}
