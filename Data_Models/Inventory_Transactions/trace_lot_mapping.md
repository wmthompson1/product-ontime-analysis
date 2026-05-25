**Trace Lot Mapping**

- **Path:** `Documentation/Data Models/Inventory_Transactions/trace_lot_mapping.md`
- **Last updated:** 2025-12-10

Summary
- **Logical field:** lot (physical location detail)
- **Physical storage:** `TRACE.APROPERTY_1` (flex user-defined field)

Details
- In this installation the business value commonly referred to as the "lot"
  for returned raw materials (used for physical-location labeling or bin
  identification) is stored in the trace table's flex field `APROPERTY_1`.
- The `TRACE` table also contains `LOT_ID` and `SERIAL_ID`; however those
  columns may represent different concepts or system-assigned identifiers.

Mapping Example
- Requirement -> Inventory -> Trace linkage
  - `REQUIREMENT.PART_ID` = inventory part
  - `INVENTORY_TRANS.TRANSACTION_ID` → `TRACE_INV_TRANS.TRANSACTION_ID`
  - `TRACE_INV_TRANS.TRACE_ID` → `TRACE.ID`
  - `TRACE.APROPERTY_1` contains the physical lot/bin detail for this site

Notes & Next Steps
- The word "lot" is ambiguous across ERP: sometimes `TRACE.LOT_ID`
  stores a system lot identifier; in other cases the human-friendly location
  or batch label is stored in a flex field such as `APROPERTY_1`.
- We should disambiguate the usage of "lot" in downstream reports and
  documentation. If you prefer the human-friendly location label in reports,
  use `TRACE.APROPERTY_1` (as currently selected in the Data Models SQL).
- If you want the system lot identifier instead, use `TRACE.LOT_ID`.
- When you have the canonical mapping decisions, I will update the SQL and
  documentation to reflect the chosen canonical field and remove the other
  if necessary.

Contact / Ownership
- Please confirm or extend this mapping. When you provide the final
  disambiguation rules, paste them here or tell me where to find them and I
  will update the docs and queries.

  
