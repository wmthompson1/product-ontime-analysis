# Documentation / Plan

This folder is the **central task registry** for the Herald multi-agent orchestration system. Herald reads from and writes to this folder to manage the full lifecycle of every delegated task.

When Herald receives a new objective, it creates `documentation/plan/{plan-NNN}-{slug}/plan.yaml` with the objective, steps, and sections. It decomposes work into a `tasks:` array (inline in plan.yaml) or a separate `tasks.yaml` with wave numbers and dependency chains. Herald assigns each task to a subagent by capability match, sets status to `pending`, then begins wave-1 delegation. As agents complete tasks, Herald updates statuses and logs activity entries. Herald never executes tasks directly — it only routes, tracks, and synthesizes.

---

## Folder Structure

```
documentation/
└── plan/
    ├── README.md
    ├── plan-001-sql-semantic-layer/
    │   ├── plan.yaml
    │   └── tasks.yaml
    ├── plan-002-agent-coordination/
    │   ├── plan.yaml
    │   └── tasks.yaml
    └── plan-003-herald-dashboard/
        ├── plan.yaml
        └── tasks.yaml
```

Each plan directory may also contain sub-artifacts (`.yaml` or `.md`) referenced by `artifact:` fields in `tasks.yaml`.

---

## Plan File Formats

Each plan is a **directory** named `plan-{NNN}-{slug}/` containing at minimum `plan.yaml` and `tasks.yaml`. Sub-artifacts (`.yaml` or `.md`) live alongside them in the same directory, referenced by `artifact:` fields in `tasks.yaml`.

### plan.yaml (required)

```yaml
plan_id: plan-004-sqlmesh-marts
title: "Plan-004: SQLMesh Marts Layer"
topic: "Data Warehouse — Aggregated KPIs and Dimensional Models"
created: "2026-03-15"
status: Draft          # Draft | Delegated | In Progress | Completed

objective: >
  One-paragraph description of what this plan accomplishes.

steps:
  - number: 1
    title: Step title
    description: >
      Detailed description of what this step involves.

sections:
  - name: Section Name
    content: >
      Prose content for this section.

agent_activity:
  - timestamp: "2026-03-15T04:00:00.000Z"
    agent: Herald
    action: Plan Created
    details: "Initialized plan-004-sqlmesh-marts"
```

### tasks.yaml (required — separate task registry)

```yaml
plan_id: plan-004-sqlmesh-marts
tasks:
  - task_id: 004-1
    title: First task
    status: pending           # pending | delegated | in_progress | completed | failed
    assigned_to: sqlmesh-devops
    wave: 1
    dependencies: []
    artifact: plan-004-1a.yaml   # optional — links to sub-artifact in same directory

  - task_id: 004-2
    title: Second task
    status: pending
    assigned_to: documentation-writer
    wave: 2
    dependencies: [004-1]
```

### Inline tasks (alternative — tasks inside plan.yaml)

Plans may also define tasks inline in `plan.yaml` using a slightly different schema:

```yaml
tasks:
  - id: task-001
    title: First task
    status: pending
    assigned_to: documentation-writer
    wave: 1
    depends_on: []
    completed_at: null

  - id: task-002
    title: Second task
    status: pending
    assigned_to: sqlmesh-devops
    wave: 2
    depends_on: [task-001]
```

The API normalizes both formats — `task_id`/`dependencies`/`artifact` (tasks.yaml) and `id`/`depends_on`/`completed_at` (inline) — into a unified task schema.

### Markdown plan.md (legacy fallback)

If `plan.yaml` is not found in a directory, the API falls back to `plan.md`. Flat `.md` or `.yaml` files at the `documentation/plan/` root are also supported for backward compatibility but are not the preferred format for new plans.

```markdown
# Plan-NNN: Title

## Plan Details
- **Plan-Id:** plan-NNN-descriptive-slug
- **Topic:** Topic name
- **Created:** YYYY-MM-DD
- **Status:** Draft | Delegated | In Progress | Completed

## Objective
...

## Tasks

| Task ID | Title | Status | Assigned To | Wave | Depends On |
|---------|-------|--------|-------------|------|------------|
| task-001 | First task | pending | agent-name | 1 | — |
| task-002 | Second task | pending | agent-name | 2 | task-001 |

## Steps
1. **Step title** — description

## Agent Activity Log
| Timestamp | Agent | Action | Details |
|-----------|-------|--------|---------|
| ...       | ...   | ...    | ...     |
```

---

## Plan Lifecycle

```
Draft ──► Delegated ──► In Progress ──► Completed
                                      ↘ Failed (see logs/)
```

| Status | Meaning |
|--------|---------|
| `Draft` | Created but not yet assigned to an agent |
| `Delegated` | Herald has assigned the plan to one or more agents |
| `In Progress` | The assigned agent is actively working |
| `Completed` | All steps finished and parity-verified |

---

## How Plans Are Created

Herald creates plans by delegating to **documentation-writer** with `task_type: documentation`. Herald scans plan directories to resolve existing `plan_id` values.

**Herald constructs this input:**
```json
{
  "task_id": "task-004-doc-01",
  "plan_id": "plan-004-sqlmesh-marts",
  "plan_path": "documentation/plan/plan-004-sqlmesh-marts/plan.yaml",
  "task_definition": {
    "task_type": "documentation",
    "output_path": "documentation/plan/plan-004-sqlmesh-marts/",
    "title": "Plan-004: SQLMesh Marts Layer",
    "source_files": ["Utilities/SQLMesh/models/staging/"],
    "sections": ["objective", "tasks", "steps", "agent_activity"]
  }
}
```

**documentation-writer responds with:**
```json
{
  "status": "completed",
  "task_id": "task-004-doc-01",
  "plan_id": "plan-004-sqlmesh-marts",
  "summary": "Created plan-004-sqlmesh-marts/ with plan.yaml and tasks.yaml",
  "extra": {
    "docs_created": [
      { "path": "documentation/plan/plan-004-sqlmesh-marts/plan.yaml", "title": "Plan-004: SQLMesh Marts Layer", "type": "yaml" },
      { "path": "documentation/plan/plan-004-sqlmesh-marts/tasks.yaml", "type": "yaml" }
    ],
    "parity_verified": true,
    "coverage_percentage": 100
  }
}
```

**Herald then:**
1. Appends to `agent_activity` in the new plan's `plan.yaml`
2. Updates task statuses in `tasks.yaml`

---

## How Plans Are Updated

Plans are updated when:
- A task wave completes and its status changes
- A new sub-artifact is delegated (adds a file to the plan directory and an `artifact:` reference in tasks.yaml)
- An agent appends to `agent_activity`

Herald sends `task_type: update` to **documentation-writer**:
```json
{
  "task_id": "task-003-log-02",
  "plan_id": "plan-003-herald-dashboard",
  "plan_path": "documentation/plan/plan-003-herald-dashboard/plan.yaml",
  "task_definition": {
    "task_type": "update",
    "target_path": "documentation/plan/plan-003-herald-dashboard/",
    "changes": "Append agent_activity: documentation-writer completed README task; update task-004 status to completed in tasks.yaml"
  }
}
```

---

## How Plans Are Rendered

The **API server** (Express/TypeScript at `artifacts/api-server/src/routes/plans.ts`) scans this folder and exposes:

| Endpoint | Returns |
|----------|---------|
| `GET /api/plans` | List of all plans (planId, title, status, fileName) |
| `GET /api/plans/:planId` | Full plan detail (rawContent, steps[], tasks[], agentActivity[]) |

**Routing rules:**
- `:planId` matches by `plan_id` from file content **or** by directory name (e.g., both `/api/plans/plan-001` and `/api/plans/plan-001-sql-semantic-layer` resolve plan-001)
- Sub-artifacts are resolved via `artifact:` references in tasks.yaml (e.g., `/api/plans/plan-001-1a` resolves the sub-artifact `plan-001-1a.yaml` inside `plan-001-sql-semantic-layer/`)
- Legacy flat files at `documentation/plan/` root are supported as a backward-compatible fallback

**Parsing rules:**
- `plan.yaml` — structured fields parsed directly (`plan_id`, `title`, `status`, `steps`, `sections`, `agent_activity`)
- `tasks.yaml` — task registry parsed and normalized (both `task_id`/`dependencies` and `id`/`depends_on` schemas)
- `.md` files — regex-parsed: bold labels for metadata, numbered lists for steps, pipe tables for activity log

The **Herald Dashboard** (React+Vite at `artifacts/herald-dashboard/`) renders plan listings in a repository-style view, with a detail modal showing the Document tab (rendered markdown) and the Steps & Log tab (structured activity table).

---

## Where Task Completion Is Documented

| Location | What Is Recorded | When |
|----------|-----------------|------|
| **`agent_activity` in plan.yaml** | Agent name, action, timestamp, details | Every task completion, delegation, and status change |
| **`tasks.yaml` status field** | Task status (pending → delegated → in_progress → completed/failed) | Every task state transition |
| **`walkthroughs/`** | Full wave/session summary (what was built, outcomes, next steps) | At the end of each completed wave |
| **`documentation-writer` JSON response** | `status`, `summary`, `docs_created`, `parity_verified` | Returned to Herald immediately on task completion |
| **`logs/`** | Failure type, error details, retry count | Only on `status: failed` |

### Completion Entry Format (agent_activity)

```yaml
agent_activity:
  - timestamp: "2026-03-15T04:06:33.000Z"
    agent: documentation-writer
    action: Task Completed
    details: "task-readme-01 — Created documentation/plan/README.md explaining plan lifecycle"
```

### Walkthrough File Format

```markdown
# Walkthrough: Wave 1 Completion
**plan_id:** plan-003-herald-dashboard
**timestamp:** 2026-03-15T04:06:33.000Z
**agent:** documentation-writer

## Overview
Brief description of the work completed in this wave.

## Tasks Completed
- task-readme-01: Created documentation/plan/README.md

## Outcomes
The plan folder is now self-describing.

## Next Steps
- Build the marts layer (plan-004)
```

---

## Naming Conventions

| Artifact | Pattern | Example |
|----------|---------|---------|
| Plan directory | `plan-{NNN}-{slug}/` | `plan-004-sqlmesh-marts/` |
| Plan metadata | `plan.yaml` (inside directory) | `plan-004-sqlmesh-marts/plan.yaml` |
| Task registry | `tasks.yaml` (inside directory) | `plan-004-sqlmesh-marts/tasks.yaml` |
| Sub-artifact (YAML) | `plan-{NNN}-{letter}.yaml` | `plan-001-1a.yaml` |
| Sub-artifact (MD) | `plan-{NNN}-{letter}.md` | `plan-001-1b.md` |
| Walkthrough | `walkthroughs/walkthrough-completion-{timestamp}.md` | `walkthrough-completion-20260315T040633.md` |
| Failure log | `logs/{agent}_{task_id}_{timestamp}.yaml` | `logs/documentation-writer_task-003-doc-01_20260315.yaml` |

> **Slug rule:** use lowercase kebab-case. The slug should describe what the plan delivers — not just the number. `plan-004-sqlmesh-marts` is better than `plan-004`.

---

## Current Plans

Authoritative list is in **`plan-index.yaml`** at the folder root. Herald reads this first.

| plan_id | Title | Status | Directory |
|---------|-------|--------|-----------|
| plan-001-sql-semantic-layer | SQL Semantic Layer Foundation | In Progress | `plan-001-sql-semantic-layer/` |
| plan-002-agent-coordination | Agent Coordination Protocol | Draft | `plan-002-agent-coordination/` |
| plan-003-herald-dashboard | Herald Multi-Agent Orchestration Dashboard | In Progress | `plan-003-herald-dashboard/` |

---

## Reference Documents

| File | Purpose |
|------|---------|
| `plan-003-herald-dashboard/plan.yaml` § Herald Orchestration Protocol | Defines phase detection, delegation flow, task lifecycle, wave execution, failure handling, and activity logging |
| `artifacts/api-server/src/routes/plans.ts` | Express route that scans plan directories, parses plan.yaml + tasks.yaml, resolves sub-artifacts |
| `lib/api-zod/src/generated/api.ts` | Zod schemas for `PlanTask`, `GetPlanResponse`, `ListPlansResponse` |
