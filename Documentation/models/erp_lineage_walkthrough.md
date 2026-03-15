# ERP Lineage Walkthrough

Narrative documentation for all staging models sourced from the ERP schema catalog.
This file satisfies the parity_verifier_001 skill requirement that every table in
`schema_catalog.db` has a corresponding documentation entry.

---

## 🏭 Manufacturing Operations & Supply Chain

### stg_operation

**Grain / Primary Key**: `workorder_type`, `workorder_base_id`, `workorder_lot_id`, `workorder_split_id`, `workorder_sub_id`, `sequence_no`

The central fact table for all shop-floor activities; captures the execution state of work orders. Each row represents a single operation step on a work order, including scheduled vs actual hours, costs (labor, burden, service), scrap/yield percentages, and status. This is the primary table the Schema Traversal Agent uses as a BFS root when traversing manufacturing dimension chains.

---

### stg_operation_audit

**Grain / Primary Key**: `schedule_id`, `attempt_no`, `resource_id`, `unit_no`

Tracks structural changes to operation scheduling attempts, ensuring a history of process modifications is preserved. Each row captures a scheduling direction (forward/backward), result code, and supply chain linkage. Used by the parity auditor to verify scheduling integrity across work order passes.

---

### stg_operation_binary

**Grain / Primary Key**: `workorder_type`, `workorder_base_id`, `workorder_lot_id`, `workorder_split_id`, `workorder_sub_id`, `sequence_no`, `type`

Metadata reference for operational binary attachments (drawings, inspection images, process documents). Actual BLOB (`BITS`) data is excluded from the staging layer to maintain pipeline performance — only `bits_length` is staged to allow completeness auditing without transferring binary payloads.

---

### stg_operation_resource

**Grain / Primary Key**: `workorder_type`, `workorder_base_id`, `workorder_lot_id`, `workorder_split_id`, `workorder_sub_id`, `sequence_no`, `resource_id`

Physical equipment or tool assignments sourced directly from the ERP catalog. Each row binds a specific resource (machine, tool, labor group) to an operation sequence on a work order, including scheduled capacity usage and segment sizing constraints. This is the table the Intent Mapping Agent uses to resolve which masking level applies to resource identifiers.

---

### stg_operation_resource_dispatch

**Grain / Primary Key**: `workorder_type`, `workorder_base_id`, `workorder_lot_id`, `workorder_split_id`, `workorder_sub_id`, `sequence_no`, `resource_id`

Maps the dispatch sequence of resources between work centers and staging areas. A lightweight extension of `stg_operation_resource` that captures the order in which resources are dispatched during finite capacity scheduling runs.

---

### stg_operation_sched

**Grain / Primary Key**: `schedule_id`, `workorder_type`, `workorder_base_id`, `workorder_lot_id`, `workorder_split_id`, `workorder_sub_id`, `sequence_no`, `resource_id`, `unit_assigned`

The finite capacity schedule; defines exactly when a resource is committed to a specific operation. Contains start/finish dates (both scheduled and could-start/could-finish), setup and run hours, concurrent scheduling flags, and delay reason codes. This is the primary table for on-time delivery analysis and OEE scheduling KPIs.

---

### stg_operation_summary

**Grain / Primary Key**: `spid`, `workorder_type`, `workorder_base_id`, `workorder_lot_id`, `workorder_split_id`, `workorder_sub_id`, `sequence_no`

Aggregated operational cost and throughput metrics scoped to a scheduling process ID (`spid`). Used for daily shift reporting, capturing estimated vs remaining labor, burden, and service costs alongside run hours and setup status. Feeds OEE calculations and standard cost variance reporting.

---

### stg_operation_type

**Grain / Primary Key**: `id`, `site_id`

Categorical classification of operation types (e.g., Setup, Run, Teardown, Inspection). The dimension table that provides default resource, cost, and yield parameters for new operations. The `site_id` composite key supports multi-site ERP configurations.

---

### stg_non_conformant_materials

**Grain / Primary Key**: `nc_id` (non-conformance identifier)

Tracks materials that failed quality inspection gates before, during, or after manufacturing operations. Initiates the rework/scrap decision workflow. In the masking engine, technician and inspector identifiers in this table are Level 3 Faker targets (persona: "George Torres" — quality inspector).

---

### stg_production_schedule

**Grain / Primary Key**: `prod_sched_id`

The master production record that synchronizes Bill of Materials (BOM) requirements with machine availability and finite capacity constraints. Acts as the coordination layer between `stg_operation_sched` (resource commitment) and `stg_products` (finished goods demand). Central to on-time delivery rate calculations.

---

### stg_products

**Grain / Primary Key**: `product_id`

The finished goods and sub-assembly dimension; the anchor for all manufacturing routings and BOM hierarchies. Every work order in `stg_operation` traces back to a product in this table. The Schema Traversal Agent's BFS always terminates at `stg_products` as the highest-level dimension node.

---

### stg_suppliers

**Grain / Primary Key**: `supplier_id`

External vendor dimension; links procurement costs to standard cost variance in operations. Contains supplier identity, performance tier, and lead time attributes. In the masking engine, supplier name and contact fields are Level 3 Faker targets. On-time delivery rate from `stg_daily_deliveries` joins to this table on `supplier_id`.

---

*Generated by: documentation-writer (Quill) · Plan-004 pod902 · 2026-03-15*
