*Reference knowledge-base material for the aerospace MRP study sequence. The data model and every sample number below are grounded in the local synthetic SQLite database `hf-space-inventory-sqlgen/app_schema/manufacturing.db` (two tables: `work_order` and `operation`). Per project convention the synthetic target dialect is SQLite; the real Infor VISUAL T-SQL (`Live.dbo.WORK_ORDER`, `Live.dbo.OPERATION`) is a faithful reference benchmark only — never the synthetic target.*

# Shop Floor Work & Routing

## Aerospace Manufacturing Resource Planning (MRP) Environment

## 1. Executive Overview

This document explains how routed work moves across the shop floor in an aerospace MRP environment, and how the data left behind by that work feeds the **Knowledge Loop** (Plan → Execute → Capture → Analyze → Learn → Refine). It is the execution-side companion to the *Knowledge Loop Framework* document in this same knowledge base.

In plain language: a **work order** is the instruction to *build a quantity of a part*. A **routing** is the ordered list of **operations** (steps) needed to build it. Each operation runs at a **work station** — a machine, a cell, a labor grade, or an outside vendor. As people and machines do the work, they record what actually happened: which step started, which finished, and how many hours it really took versus the plan. That record is the raw material for continuous improvement.

Everything here is grounded in two real tables in the synthetic database:

| Table | What it holds | Rows (synthetic) |
| --- | --- | --- |
| `work_order` | One row per job: the part, the quantity, the dates, the status, the routing template | 120 |
| `operation` | One row per routed step: the sequence, the work station, the hours (planned and actual), the step status | 502 |

Those 502 operations are spread across **20 distinct work stations**. The whole document uses only these two tables joined on `operation.wo_id = work_order.wo_id`. A friendly work-station *name* (for example, "CNC Milling Cell #1") is mentioned in prose for readability, but it is **not** joined in — `operation.resource_id` is treated as the work station directly.

This mirrors APICS / closed-loop MRP framing:

| Knowledge Loop element | APICS mapping | Where it lives here |
| --- | --- | --- |
| Plan | MRP / MPS | `work_order` header + planned `operation` hours |
| Execute | Production Activity Control (PAC) | `operation.status` Q → S → C |
| Capture | Shop Floor Control | `act_setup_hrs`, `act_run_hrs`, `close_date` |
| Analyze | Performance Management | scheduled-vs-actual variance |
| Learn / Refine | Continuous Improvement | updated routing standards |

## 2. The `work_order` → `operation` Routing Data Model

The relationship is a simple **one-to-many**: one work order has many operations.

```
work_order (1) ───< operation (many)
   wo_id     ─────────  wo_id        (join key)
   part_id              sequence_no  (routing step order)
   quantity             resource_id  (the WORK STATION)
   status               operation_type_id (the KIND of step)
   routing_template     status       (Q / S / C)
   open_date            setup_hrs / run_hrs            (planned)
   required_date        act_setup_hrs / act_run_hrs    (actual)
   close_date           close_date
```

### 2.1 The `work_order` header — what is being built

Key columns used in this document:

- `wo_id` — the work order key (e.g. `WO-240003`). The synthetic data carries two ID styles, `WO-000xx` (70 rows) and `WO-240xxx` (50 rows); both behave identically.
- `part_id`, `part_description`, `quantity` — what and how many.
- `status` — the job's life stage: **unreleased → firmed → released → closed** (here, *firmed* means first lots of newly engineered parts).
- `routing_template` — the named recipe of steps the job follows (AIRFRAME, FASTENER, …).
- `open_date`, `required_date`, `close_date` — when it started, when it's due, when it finished.

### 2.2 The `operation` row — one routed step

- `sequence_no` — the step's place in the routing. **Gapped on purpose** (e.g. 30, 110, 230, 310…) so planners can insert a step later without renumbering everything.
- `resource_id` — **the work station**: where the step runs.
- `operation_type_id` — the *kind* of step (CNC, WELD, INSPECT, NDT, ANOD…).
- `status` — **Q** (Queued / waiting), **S** (Started / in work), **C** (Complete).
- `setup_hrs` + `run_hrs` — the **planned** time.
- `act_setup_hrs` + `act_run_hrs` — the **actual** time recorded.
- `close_date` — stamped when the step completes.

> **Synthetic vs. real-ERP note.** In real Infor VISUAL the work order key is a composite (`BASE_ID`, `LOT_ID`, `SPLIT_ID`, `SUB_ID`) and operations carry `OPERATION_SEQ_NO`. The synthetic model collapses the composite key into a single `wo_id` surrogate and uses `sequence_no`. The *meaning* is identical; only the key shape changes.

## 3. Routing Fundamentals

A routing answers the question: *"What are the steps, in what order, and where does each one run?"*

### 3.1 Sequence numbers

Operations are ordered by `sequence_no`. The numbers are spaced out (20, 80, 220…) so an engineer can drop a new inspection at, say, sequence 90 without touching the rest. **Job progress is read from each step's `status` and `close_date`, not from the sequence number** — a high sequence number does not by itself mean "done".

### 3.2 Routing templates

Each work order points at a named routing template. The synthetic shop uses six, covering the full job mix:

| `routing_template` | Work orders | Typical flow |
| --- | --- | --- |
| AIRFRAME | 33 | machine → outside process → inspect → assemble → finish |
| FASTENER | 28 | turn → heat treat → plate → inspect |
| WELDMENT | 18 | weld → heat treat → NDT → machine → inspect |
| MACHINED | 18 | mill/turn → deburr → inspect |
| COMPOSITE | 12 | layup → cure → trim → inspect |
| BRACKET | 11 | cut → form → finish → inspect |

A template is the *starting standard*. The Knowledge Loop is what keeps that standard honest over time (Section 9).

### 3.3 Operation type vs. work station

Two different ideas that are easy to confuse:

- **Operation type** (`operation_type_id`) = *what kind* of work (e.g. `CNC`, `NDT`).
- **Work station** (`resource_id`) = *where* it physically runs (e.g. `CNC-MILL-1`, `SV-003`).

The same operation type can run at different work stations, and one work station can host several operation types.

## 4. Shop-Floor Execution / Production Activity Control (PAC)

Once a work order is **released**, its operations become live work on the floor. This is the APICS **Production Activity Control** phase: dispatch the work, track its progress, and manage work-in-process (WIP).

### 4.1 The operation status lifecycle

Each operation walks through three states:

```
Q (Queued)  ──►  S (Started)  ──►  C (Complete)
 waiting          in work           finished, close_date stamped
```

Across the 502 synthetic operations:

| `status` | Meaning | Count |
| --- | --- | --- |
| C | Complete | 339 |
| Q | Queued (waiting) | 140 |
| S | Started (in work) | 23 |

That distribution is a snapshot of the floor: most steps are done, a healthy backlog is queued, and a small number are actively in work — exactly what you'd expect from a mix of closed, released, and unreleased jobs.

### 4.2 Dispatch and WIP

- **Dispatch list** = the queued (`Q`) operations at a given work station, in routing order — the "what to run next" list.
- **WIP** = operations that are `S` (started) but not yet `C` — work the floor is currently holding.

Because every operation carries both its work station and its status, the dispatch list and WIP picture for any station fall straight out of the two-table join.

## 5. The Work-Station View (`resource_id` as the Work Station)

Re-grouping the same operations **by `resource_id`** turns the routing view into a **shop view**: how busy is each station, and how does its real time compare to plan? This is exactly what Query 2 in the grounding file produces. Top stations by routed-operation count:

| Work station (`resource_id`) | Routed ops | Completed | Started | Queued | Sched hrs | Actual hrs |
| --- | --- | --- | --- | --- | --- | --- |
| OUTSIDE | 76 | 49 | 6 | 21 | 0.0 | 77.5 |
| LB-004 | 70 | 42 | 2 | 26 | 60.0 | 0.0 |
| INSPECT-CMM | 50 | 31 | 3 | 16 | 40.2 | 16.3 |
| SV-001 | 37 | 21 | 3 | 13 | 0.0 | 0.0 |
| CNC-MILL-1 | 25 | 21 | 0 | 4 | 61.8 | 34.2 |
| MC-003 | 19 | 11 | 0 | 8 | 114.0 | 0.0 |
| LB-003 | 19 | 10 | 1 | 8 | 190.0 | 0.0 |

Reading it in plain language:

- **`OUTSIDE`** carries the most steps (76) and shows 0 scheduled in-house hours but 77.5 actual — that's bought vendor time, not floor time (see Section 7).
- **`LB-004`** (a Quality Inspector labor grade) carries 70 steps with 26 still queued — a load worth watching for a backlog.
- **`INSPECT-CMM`** (the CMM inspection station) ran 16.3 hours against 40.2 planned — it is beating the estimate so far.

> **Synthetic vs. real-ERP note.** `resource_id` here is both machines (`CNC-MILL-1`), labor grades (`LB-004`), and outside vendors (`OUTSIDE`, `SV-*`). Friendly names — "Quality Inspector — Level II", "CMM Inspection, Zeiss Contura G2" — live in a separate `shop_resource` table that is deliberately **not** joined in this two-table grounding. They are quoted here for readability only.

## 6. Scheduled-vs-Actual Variance (Hours and Cost)

This is where execution data earns its keep. Every operation stores both the **plan** (`setup_hrs + run_hrs`) and the **actual** (`act_setup_hrs + act_run_hrs`). The difference is **variance**:

```
hrs_variance = (act_setup_hrs + act_run_hrs) − (setup_hrs + run_hrs)
```

- **Negative** variance = the floor beat the estimate (faster than planned).
- **Positive** variance = the step overran the estimate.

Across completed operations with recorded actuals, the in-house stations are largely running **under** their estimates:

| Work station | Scheduled hrs | Actual hrs | Variance |
| --- | --- | --- | --- |
| ASSEM-LINE-2 | 55.0 | 17.6 | −37.4 |
| CNC-MILL-1 | 52.2 | 34.2 | −18.0 |
| INSPECT-CMM | 27.0 | 16.3 | −10.7 |
| ASSEM-LINE-1 | 38.5 | 30.2 | −8.3 |
| CNC-MILL-2 | 25.2 | 18.6 | −6.6 |
| WELD-A | 9.1 | 5.2 | −3.9 |
| LATHE-1 | 4.8 | 2.3 | −2.5 |

A consistent negative variance is a signal that the **planned standard is too generous** — a prime candidate for refinement (Section 9). The work order also carries actual cost buckets (`act_lab_cost`, `act_bur_cost`, `act_ser_cost`, `act_mat_cost`) and each operation carries estimated-vs-actual labor/burden/service cost, so the same variance logic extends from hours to dollars.

## 7. Outside-Service Operations

Aerospace routings frequently send parts out for special processing — heat treat, anodize, NDT, plating, paint. The synthetic model marks these on the operation row via `service_id` and `vendor_id`. **168 of the 502 operations** are outside-service steps.

How to recognize them:

- The work station is `OUTSIDE` or an `SV-*` code (SV-001 Anodize, SV-002 Heat Treat, SV-003 NDT, SV-004 Chemical Film, SV-005 Paint).
- In-house scheduled hours are typically **0** because the labor is purchased, not run on a machine — note in the work-station table how `OUTSIDE` shows `sched_hrs = 0` but `act_hrs = 77.5`.
- The work order's `outside_service` flag is set to 1 when any of its steps route outside.
- Dispatch/receipt dates (`last_disp_date`, `last_recv_date`, `service_begin_date`) track the part leaving and returning.

Outside steps matter for the Knowledge Loop because they are a common source of lead-time variability — a late vendor ripples through every downstream step in the routing.

## 8. Aerospace Compliance Angle

Routing data is not just a scheduling tool in aerospace — it is part of the **conformance record**.

### 8.1 Inspection and NDT as routed steps

Quality is built into the routing, not bolted on afterward. Inspection (`INSPECT`, `FINSP`) and Non-Destructive Test (`NDT`) appear as their own operations with their own work stations (`INSPECT-CMM`, `SV-003`). Because they are routed steps, they are sequenced, dispatched, and signed off exactly like production steps — so the build *cannot* progress past a required inspection without it being recorded.

### 8.2 Traceability and configuration control

- **AS9100 / FAA Part 21 / Part 145** expect full traceability: every step, who/what ran it, and when it completed (`close_date`).
- The gapped `sequence_no` supports **configuration control** — an engineering change can insert or revise a step without destroying the history of the steps around it.
- The estimated-vs-actual record on every operation is an auditable trail of how the part was actually made versus how it was planned.

### 8.3 Why the work-station view matters for compliance

Knowing *which station* ran each step (`resource_id`) ties a build to specific certified equipment and certified labor grades (e.g. "Welder AWS D1.1"). That station-level link is what makes a recurring-defect investigation possible.

## 9. Enabling Knowledge Loop Iteration

This is the heart of the document: how the captured execution data **closes the loop** and refines the routing standards it came from.

```
        ┌─────────────────────────────────────────────┐
        │                                             │
   (Plan) routing_template + planned setup/run hours  │
        │                                             │
        ▼                                             │
  (Execute) operation.status  Q ─► S ─► C             │
        │                                             │
        ▼                                             │
  (Capture) act_setup_hrs, act_run_hrs, close_date    │
        │                                             │
        ▼                                             │
  (Analyze) scheduled-vs-actual variance per station  │
        │                                             │
        ▼                                             │
  (Learn) which standards are wrong, which stations   │
        │        recur as bottlenecks / defect sources│
        ▼                                             │
  (Refine) update planned hours + routing template ───┘
```

### 9.1 From actuals to better standards

The variance table in Section 6 is the loop in action. When `CNC-MILL-1` repeatedly runs 18 hours under its 52-hour plan, that is direct evidence the **planned `run_hrs` standard is too high**. Feeding the real average back into the routing template tightens future MRP capacity plans and quotes. The define-once routing template means one corrected standard improves *every* future job that uses it.

### 9.2 From completion timing to better scheduling

`close_date` plus the dispatch/receipt dates reveal *real* step durations and queue times — especially for outside services. Comparing planned dates to actual `close_date` exposes where jobs actually wait, which refines lead-time assumptions back in planning.

### 9.3 From work-station load to better capacity decisions

The work-station rollup (Section 5) shows where work piles up. A station that is always deep in queued (`Q`) operations is a bottleneck; that insight feeds capacity planning — add a shift, add a machine, or re-balance the routing to a less-loaded station.

### 9.4 From recurring variance to root cause

When the *same* station or operation type keeps overrunning, that is a Learn-stage signal: investigate tooling, fixturing, or work instructions, fix the root cause, and update the standard. The two-table join is the evidence base for that investigation.

## 10. Shop-Floor Metrics

All of the following come straight from the two-table join:

| Metric | How it's computed | APICS category |
| --- | --- | --- |
| Schedule adherence | completed (`C`) ops vs. planned, by `close_date` | PAC |
| Work-station load | `COUNT(*)` of ops grouped by `resource_id` | Capacity |
| WIP | ops with `status = 'S'` | Shop Floor Control |
| Queue depth | ops with `status = 'Q'` per station | PAC |
| Hours variance | `act_setup+act_run` − `setup+run` | Performance Mgmt |
| Cost variance | actual vs. estimated labor/burden/service cost | Cost Mgmt |
| Outside-service share | ops with `service_id`/`vendor_id` ÷ total ops | Procurement |

## 11. The Grounding Query

The companion file `manufacturing_shopfloorrouting_20260704_000003.sql` (archived under `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/_archived/`) holds two runnable SQLite queries, both **strict two-table joins** of `work_order` and `operation`. The core of Query 1:

```sql
SELECT
    wo.wo_id,
    wo.routing_template,
    wo.status                                   AS wo_status,
    op.sequence_no,
    op.resource_id                              AS work_station,
    op.operation_type_id                        AS op_type,
    op.status                                   AS op_status,
    ROUND(op.setup_hrs + op.run_hrs, 2)         AS sched_hrs,
    ROUND(op.act_setup_hrs + op.act_run_hrs, 2) AS act_hrs,
    ROUND((op.act_setup_hrs + op.act_run_hrs)
          - (op.setup_hrs + op.run_hrs), 2)     AS hrs_variance,
    ROUND(op.est_atl_lab_cost + op.est_atl_bur_cost
          + op.est_atl_ser_cost, 2)             AS sched_cost,
    ROUND(op.act_atl_lab_cost + op.act_atl_bur_cost
          + op.act_atl_ser_cost, 2)             AS act_cost
FROM work_order wo
JOIN operation op
    ON op.wo_id = wo.wo_id
WHERE wo.wo_id = 'WO-240003'
ORDER BY op.sequence_no;
```

### 11.1 What it does, in plain language

It reads one work order and walks its routing in order. For each routed step it shows the work station, the kind of step, whether it's queued/started/complete, the planned hours, the actual hours, the gap between them, and the planned-vs-actual cost (labor + burden + outside-service) — the full "traveler" for that job.

### 11.2 Verified sample output

Running Query 1 against `manufacturing.db` returns the complete, closed routing for an AIRFRAME job (cost columns rounded to whole dollars here for readability):

| wo_id | routing_template | sequence_no | work_station | op_type | op_status | sched_hrs | act_hrs | hrs_variance | sched_cost | act_cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WO-240003 | AIRFRAME | 30 | CNC-MILL-1 | CNC | C | 3.0 | 2.85 | −0.15 | 6165 | 7028 |
| WO-240003 | AIRFRAME | 110 | CNC-MILL-2 | CNC | C | 2.1 | 1.56 | −0.54 | 5119 | 4437 |
| WO-240003 | AIRFRAME | 230 | OUTSIDE | HTRT | C | 0.0 | 1.56 | 1.56 | 2160 | 2124 |
| WO-240003 | AIRFRAME | 310 | INSPECT-CMM | INSPECT | C | 1.0 | 0.72 | −0.28 | 1296 | 1166 |
| WO-240003 | AIRFRAME | 430 | ASSEM-LINE-1 | ASSY | C | 3.5 | 3.58 | 0.08 | 4158 | 4962 |
| WO-240003 | AIRFRAME | 550 | OUTSIDE | ANOD | C | 0.0 | 3.58 | 3.58 | 1530 | 1439 |

Read top to bottom, this is the whole life of the part: rough machining at CNC-MILL-1, second machining at CNC-MILL-2, out for heat treat, CMM inspection, assembly, and finally out for anodize. The gapped sequence numbers (30, 110, 230…) leave room to insert steps later. The in-house machining and inspection steps all came in slightly **under** plan on hours; on cost the picture is mixed — the first CNC step and the assembly step ran **over** their estimates while the rest came in under, which is exactly the kind of plan-vs-actual signal the Knowledge Loop feeds on. The two `OUTSIDE` steps show 0 planned in-house hours because that time is bought from a vendor, yet they still carry a real outside-service cost.

### 11.3 Query 2 — the shop view

The second query in the file rolls every operation up to its work station across all 120 work orders, producing the load-and-variance table used in Sections 5 and 6. It is also a strict two-table join, grouped by `resource_id`.

## 12. Failure Patterns to Watch

| Pattern | What you'd see in the data | Risk |
| --- | --- | --- |
| Standard too generous | persistent large **negative** variance at a station | inflated capacity plans, over-quoting |
| Standard too tight | persistent **positive** variance | missed schedules, hidden overtime |
| Bottleneck station | deep `Q` queue that never drains | jobs late despite floor "looking busy" |
| Outside-service drag | long gaps between `last_disp_date` and `last_recv_date` | lead-time blowouts that ripple downstream |
| Skipped inspection | a required `INSPECT`/`NDT` step left non-`C` while later steps complete | compliance / conformance gap |

## 13. APICS Terminology Mapping

| Term | Plain meaning | Where it lives here |
| --- | --- | --- |
| Routing | The ordered steps to make a part | `operation` rows ordered by `sequence_no` |
| Operation | One step in the routing | a single `operation` row |
| Work center / station | Where a step runs | `operation.resource_id` |
| PAC | Running and tracking the work | `operation.status` Q→S→C |
| WIP | Work currently in process | ops with `status = 'S'` |
| Dispatch list | What to run next at a station | queued ops per `resource_id` |
| Standard hours | Planned time for a step | `setup_hrs + run_hrs` |
| Variance | Plan vs. actual gap | actual hours − planned hours |

## 14. Summary

Shop-floor work and routing turn a *plan* (a work order and its routing template) into a *record* (operations with real statuses, hours, and completion dates). Two tables — `work_order` and `operation`, joined on `wo_id`, with `resource_id` as the work station — are enough to:

- walk any job's routing in order (the traveler),
- see how loaded each work station is,
- compare planned vs. actual hours and cost,
- track outside-service steps,
- and prove conformance through routed inspection/NDT steps.

Most importantly, that captured execution data **closes the Knowledge Loop**: real actuals refine the planned standards they came from, so every future job built on the same routing template is planned a little more accurately than the last.

## 15. Appendix — Field Reference

### 15.1 `work_order` (header)

| Column | Meaning |
| --- | --- |
| `wo_id` | Work order key |
| `part_id`, `part_description` | What is being built |
| `quantity` | How many |
| `status` | unreleased / firmed / released / closed |
| `routing_template` | Named recipe of steps |
| `open_date`, `required_date`, `close_date` | Start, due, finish |
| `act_lab_cost`, `act_bur_cost`, `act_ser_cost`, `act_mat_cost` | Actual cost buckets |
| `outside_service` | 1 if any step routes to an outside vendor |

### 15.2 `operation` (routed step)

| Column | Meaning |
| --- | --- |
| `wo_id` | Parent work order (join key) |
| `sequence_no` | Routing step order (gapped) |
| `resource_id` | **The work station** |
| `operation_type_id` | The kind of step (CNC, NDT, …) |
| `status` | Q (Queued) / S (Started) / C (Complete) |
| `setup_hrs`, `run_hrs` | Planned hours |
| `act_setup_hrs`, `act_run_hrs` | Actual hours |
| `est_atl_*` / `act_atl_*` cost columns | Estimated vs. actual labor / burden / service cost |
| `service_id`, `vendor_id` | Set for outside-service steps |
| `close_date` | Stamped when the step completes |
| `sched_start_date`, `sched_finish_date` | Planned step dates |
| `last_disp_date`, `last_recv_date`, `service_begin_date` | Outside-service dispatch / receipt tracking |
