# JSON-LD Concept Reference — Job-Costing Ledger SKOS Scheme

Reference for every concept in the committed SKOS concept scheme
`poc/ontop-ontology-poc/ontology/ledger_skos.jsonld` (namespace
`ledger:` = `http://example.org/manufacturing/ledger#`, scheme
`ledger:JobCostingLedgerScheme`). The JSON-LD file is the single source of
truth; this page is documentation only — regenerate it by re-reading the file
whenever the scheme changes.

The scheme is loaded fail-closed at runtime by
`hf-space-inventory-sqlgen/skos_ledger.py` (missing labels/definitions,
dangling broader/narrower pairs, duplicates, or out-of-scheme concepts abort
the load). Physical-table bindings live in the separate governed map
`poc/ontop-ontology-poc/ledger_binding_map.json` (loader
`ledger_bindings.py`) — a concept absent from that map is simply unbound.

## Concept scheme

| URI | prefLabel | Definition (abridged) |
|---|---|---|
| `ledger:JobCostingLedgerScheme` | Job-Costing Ledger Concept Scheme | SKOS scheme for the synthetic job-costing ledger: the endurant inventory accounts (RM, WIP, FG), the job cost detail register, and the perdurant cost-accumulation event vocabulary that moves cost between them. |

## Top concepts — endurant accounts and registers

| URI | prefLabel | altLabel | Physical twin | Definition |
|---|---|---|---|---|
| `ledger:RawMaterialsInventory` | Raw Materials Inventory | Inventory | `gl_raw_materials_inventory` | Endurant inventory account holding the cost of unprocessed input material owned but not yet consumed by a job. Cost leaves this account and enters WIP when material is issued to a work order. |
| `ledger:WIPInventory` | WIP Inventory | WIP | `gl_wip_inventory` | Endurant inventory account accumulating job cost while work is in process: material issued from Raw Materials, labor applied from labor tickets, and overhead (burden) applied on top of labor. Relieved into Finished Goods at job completion. |
| `ledger:FinishedGoodsInventory` | Finished Goods Inventory | FG | `gl_finished_goods_inventory` | Endurant inventory account holding the accumulated cost of completed jobs after WIP is relieved at job completion. The flow stops here (no COGS/shipment costing exists yet). |
| `ledger:JobCostDetail` | Job Cost Detail | — | `gl_job_cost_detail` | The per-event cost register: one row per cost-accumulation event, typed by cost element and keyed to the job (work order), telling the full job-costing story line by line. |
| `ledger:CostAccumulationEvent` | Cost Accumulation Event | Ledger Event | `gl_events` | Perdurant event vocabulary: the four posting events that move cost through the ledger flow Raw Materials → WIP → Finished Goods. |

## Narrower concepts — raw-material subtypes (vocabulary-only, deliberately unbound)

All four have `skos:broader ledger:RawMaterialsInventory` and no physical
table binding.

| URI | prefLabel | altLabel | Definition |
|---|---|---|---|
| `ledger:StandardsRawMaterial` | Standards | Standard Hardware | Catalog standard hardware (fasteners, rivets, inserts, bushings) bought to a published specification and consumed across many jobs. |
| `ledger:DetailPartsRawMaterial` | Detail Parts | — | Make-from or buy detail parts machined or formed to a drawing, consumed as direct material by downstream assembly jobs. |
| `ledger:ComponentsRawMaterial` | Components | — | Purchased components and sub-assemblies (motors, valves, connectors) consumed as direct material without further transformation. |
| `ledger:SheetMetalRawMaterial` | Sheet Metal | Sheet Stock | Sheet and plate stock (aluminum, steel, titanium) issued by area or weight and cut/formed on the shop floor. |

## Narrower concepts — the four posting events

All four have `skos:broader ledger:CostAccumulationEvent`. Their
`skos:notation` values are exactly the physical `gl_events.event_type`
strings — this is the cross-layer coherence check `ledger_bindings.py`
enforces against the OWL event classes' `skos:closeMatch` targets.

| URI | prefLabel | altLabel | notation (`gl_events.event_type`) | Definition |
|---|---|---|---|---|
| `ledger:MaterialIssued` | Material Issued | — | `RM_ISSUE` | Material issued from Raw Materials Inventory into WIP for a job, posted at the issue's total cost on its data-derived issue date. |
| `ledger:LaborApplied` | Labor Applied | — | `LABOR` | Direct labor from a labor ticket applied into WIP for a job at the ticket's labor cost. |
| `ledger:OverheadApplied` | Overhead Applied | Burden Applied | `BURDEN` | Overhead (burden) applied into WIP on top of a labor ticket's labor, at the ticket's burden cost. |
| `ledger:JobCompletion` | Job Completion | — | `FG_COMPLETION` | A closed work order's accumulated WIP relieved into Finished Goods Inventory on the job's close date. |

## The OWL event layer beside the scheme

`poc/ontop-ontology-poc/ontology/ledger_events.ttl` adds OWL event *classes*
(`:LedgerEvent`, `:WIPAdditionEvent`, `:MaterialIssueEvent`,
`:LaborApplicationEvent`, `:OverheadApplicationEvent`,
`:JobCompletionEvent`), the `:WorkOrder` entity class (grounded 1:1 on
`work_order` keyed by `wo_id`), the closed `:WorkOrderLifecycleState` vocabulary
mirroring `work_order.status` exactly (unreleased / firmed / released /
closed), and the flow properties `:consumesMaterial`, `:addsCostToWIP`,
`:producesFinishedGoods`, `:forJob`, `:hasLifecycleState` — in the *same*
namespace. OWL classes and SKOS concepts stay distinct terms linked by
`skos:closeMatch`, never `owl:equivalentClass` (the POC's safe-annotation
convention). See the [ontology diagram](diagrams/ledger_ontology.svg) for
the full picture.
