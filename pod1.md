# Pod 1 — Herald Multi-Agent Dashboard

## Purpose
A unified dashboard for the Herald multi-agent orchestration system built on top of the manufacturing analytics SQLMesh data warehouse. Provides visibility into agent status, MCP skill execution, and task routing.

## Agent Suite

| Agent | Role | Skills |
|-------|------|--------|
| **Herald** | Orchestrator — routes tasks to specialists | Task routing, plan management |
| **sqlmesh-devops** | SQLMesh operations specialist | `environment_fix`, `surgical_purge`, `pii_masking`, `schema_impact` |
| **hashed-data-inspector** | Data quality & hashed field inspection | Column profiling, PII detection, hash verification |
| **documentation-writer** | Auto-generates markdown documentation | `auto_docs`, parity checking, plan generation |
| **test-data-synthesizer** | Generates realistic manufacturing seed data | Faker-based CSV synthesis, referential integrity |

## Dashboard Components

1. **Herald Control Panel** — Active task, routing decisions, agent health
2. **Specialist Agent Cards** — Per-agent status, last run, skill triggers
3. **MCP Skills Sidebar** — One-click skill execution from `.agents/skills/sqlmesh.yaml`
4. **Activity Log** — Real-time task and event stream
5. **Manufacturing KPI Strip** — On-time rate, OEE, defect rate from SQLMesh staging layer

## File Layout

```
.github/agents/
  herald.agent.md
  sqlmesh-devops.agent.md
  hashed-data-inspector.agent.md
  documentation-writer.agent.md
  test-data-synthesizer.agent.md

.agents/skills/
  sqlmesh.yaml          ← MCP skill contracts (existing)

multi_agent_dashboard.html   ← Standalone dashboard UI
pod1.md                      ← This spec
```

## Data Sources
- SQLMesh staging layer: `Utilities/SQLMesh/models/staging/`
- Schema: `schema/schema_sqlite.sql`
- Seed data: `025_Entry_Point_DDL_to_SQLMesh_Part2.py`
- MCP skills: `.agents/sqlmesh.yaml.txt`

## Agent Flow
```
User → Herald → routes by intent →
  ├─ sqlmesh-devops     (env issues, schema changes, PII)
  ├─ hashed-data-inspector  (data quality, column profiling)
  ├─ documentation-writer   (plan docs, README updates)
  └─ test-data-synthesizer  (seed CSV generation)
```
