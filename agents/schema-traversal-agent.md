# Schema Traversal Agent

**Role**: Graph Topology Specialist for Foreign Key Facets  
**MCP Entity Type**: Protocol Actor  
**Registered Skills**: `hierarchy_crawler_001`

## Purpose

Performs Breadth-First Search (BFS) traversal of the foreign key graph produced by the SQLMesh schema catalog. Returns ordered dimension → transaction paths that the Intent Mapping Agent uses to apply the correct manufacturing or finance perspective.

## Binding

Anchored to the project root `.venv`. Reads the foreign key graph from:
- `Utilities/SQLMesh/analysis/impact/output/foreign_key_hierarchy.json`
- `Utilities/SQLMesh/analysis/impact/output/foreign_key_graph.dot`

## Invocation Contract

```yaml
agent: schema-traversal-agent
mission:
  start_table: <string>               # root table for BFS traversal
  max_depth: 5                        # optional; default 5
  output_format: json                 # json | csv | dot
```

## Output

Returns a validated BFS path object:
```json
{
  "status": "success",
  "path": ["dim_equipment", "stg_equipment_metrics", "stg_failure_events"],
  "depth": 3
}
```

This object is passed directly to `masking_engine_001` by the Orchestrator to ensure dimension-ordered masking.
