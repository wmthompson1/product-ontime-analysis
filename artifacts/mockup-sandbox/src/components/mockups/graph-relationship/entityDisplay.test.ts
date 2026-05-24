import { describe, it, expect } from "vitest";
import { getFirstEntityDisplay } from "./entityDisplay";
import type { SearchResult } from "./entityDisplay";

describe("getFirstEntityDisplay", () => {
  it("returns '<table_name> (<source>)' for the first entity in grouped_results", () => {
    const data: SearchResult = {
      matches_found: 3,
      grouped_results: {
        ERP_Instance_1: [
          { table_name: "production_orders", qualified_name: "dbo.PRODUCTION_ORDERS" },
          { table_name: "work_orders", qualified_name: "dbo.WORK_ORDERS" },
        ],
        semantic_layer: [
          { table_name: "orders_concept", qualified_name: "concepts/orders_concept" },
        ],
      },
    };

    expect(getFirstEntityDisplay(data)).toBe("production_orders (ERP_Instance_1)");
  });

  it("returns an empty string when grouped_results is empty", () => {
    const data: SearchResult = { matches_found: 0, grouped_results: {} };
    expect(getFirstEntityDisplay(data)).toBe("");
  });

  it("returns an empty string when the first group has no records", () => {
    const data: SearchResult = {
      matches_found: 0,
      grouped_results: { ERP_Instance_1: [] },
    };
    expect(getFirstEntityDisplay(data)).toBe("");
  });

  it("uses the first group key even when multiple groups exist", () => {
    const data: SearchResult = {
      matches_found: 2,
      grouped_results: {
        alpha: [{ table_name: "alpha_table", qualified_name: "dbo.ALPHA" }],
        beta: [{ table_name: "beta_table", qualified_name: "dbo.BETA" }],
      },
    };
    expect(getFirstEntityDisplay(data)).toBe("alpha_table (alpha)");
  });
});
