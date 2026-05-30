import type { SearchResult } from "./entityDisplay";

export const MOCK_SEARCH_DATA: SearchResult = {
  matches_found: 8,
  grouped_results: {
    ERP_Instance_1: [
      { table_name: "production_schedule", qualified_name: "dbo.PRODUCTION_SCHEDULE" },
      { table_name: "downtime_events", qualified_name: "dbo.DOWNTIME_EVENTS" },
      { table_name: "product_lines", qualified_name: "dbo.PRODUCT_LINES" },
      { table_name: "quality_incidents", qualified_name: "dbo.QUALITY_INCIDENTS" },
      { table_name: "equipment_metrics", qualified_name: "dbo.EQUIPMENT_METRICS" },
      { table_name: "production_quality", qualified_name: "dbo.PRODUCTION_QUALITY" },
      { table_name: "suppliers", qualified_name: "dbo.SUPPLIERS" },
      { table_name: "production_lines", qualified_name: "dbo.PRODUCTION_LINES" },
    ],
  },
};
