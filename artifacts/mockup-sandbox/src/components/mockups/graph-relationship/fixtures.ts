import type { SearchResult } from "./entityDisplay";

export const MOCK_SEARCH_DATA: SearchResult = {
  matches_found: 12,
  grouped_results: {
    ERP_Instance_1: [
      { table_name: "production_orders", qualified_name: "dbo.PRODUCTION_ORDERS" },
      { table_name: "work_orders", qualified_name: "dbo.WORK_ORDERS" },
      { table_name: "order_lines", qualified_name: "dbo.ORDER_LINES" },
      { table_name: "quality_events", qualified_name: "dbo.QUALITY_EVENTS" },
      { table_name: "equipment_metrics", qualified_name: "dbo.EQUIPMENT_METRICS" },
      { table_name: "downtime_events", qualified_name: "dbo.DOWNTIME_EVENTS" },
      { table_name: "suppliers", qualified_name: "dbo.SUPPLIERS" },
      { table_name: "production_lines", qualified_name: "dbo.PRODUCTION_LINES" },
    ],
    semantic_layer: [
      { table_name: "orders_concept", qualified_name: "concepts/orders_concept" },
      { table_name: "quality_intent", qualified_name: "intents/quality_intent" },
      { table_name: "downtime_perspective", qualified_name: "perspectives/downtime_perspective" },
      { table_name: "suppliers_binding", qualified_name: "bindings/suppliers_binding" },
    ],
  },
};
