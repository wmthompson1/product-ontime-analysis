# Ontology as Intervals: Blind Queries, the Guitar Metaphor, and the Order-Type Matrix

*Saved from chat — July 5, 2026*

Continuation of the constraints/DBR thread: what separates ontology from relational
metadata, why entity relationships are the transferable knowledge, and how an ERP
order-type guide is really an ontology document in disguise.

---

## 1. Which work center is "the oven"? (the constraint isn't a column)

Asked "what is your most costly workstation?", the data gives three different answers
depending on which column you ask:

- **By hourly cost** — the Mazak Integrex 300 Turn-Mill (MC-002) at $315/hr all-in
  (run + burden), ahead of the DMG Mori HMC ($295) and Haas VF-4 ($280). If "too
  expensive to buy another" defines the drum, the Mazak is the oven.
- **By accumulated load** — the Haas VF-4 (MC-001): most machine hours (18 hrs across
  6 ops, ~$5,040 estimated). Among people, the AWS-certified welder (LB-005) at 20 hrs.
- **By open queue right now** — Assembly Tech (LB-003) and Quality Inspector (LB-004),
  with 7 open inspection ops queued.

And the twist: the data *does* have an oven — SV-002, Outside Heat Treat — but it's an
outside service. The shop's answer to "the oven is too expensive to buy" was *don't own
one at all*: the constraint got pushed outside the four walls, governed by vendor lead
time instead of machine capacity.

**Conclusion**: there is no column that says "constraint." Rate nominates the Mazak,
load history the VF-4, the live queue inspection, and the true oven isn't on the floor.
Naming the drum is SME judgment that belongs in the semantic layer as a declared role
(`:ConstrainedResource`). Once named, "the drum never starves" becomes a checkable
statement against on-hand and requirements — but the naming itself is human knowledge.

## 2. Relational metadata vs. ontology

> "SQL developers see views, not procedural placement. SQLMesh is really good at
> lineage, and AI is really good at field descriptions, but it's relational metadata.
> I've written queries without seeing the data because I understood the ontology."

- **Lineage and descriptions are backward-looking.** SQLMesh lineage says where a value
  came from; AI descriptions say what a column is called. Both answer "what is this
  thing I'm looking at?" — you need the artifact in front of you first. They annotate
  what exists; they can't tell you what to write.
- **Ontology is forward-looking.** Knowing that a work order *has* operations, that
  operations *consume* a resource's hours, that receipts *satisfy* requirements — the
  query writes itself before you've seen a row: joins that must exist, grain each table
  must have, direction the FKs must point. The data merely confirms what the ontology
  predicted; when it doesn't, you've found a data problem, not a modeling problem.
- **"Views, not procedural placement"** — a view is a declared relationship: what's
  true, not how to compute it. Thinking in views is already thinking ontologically.
- **Division of labor**: SQLMesh gets lineage (mechanical, derivable), AI gets
  descriptions (verbal, cheap, reviewable), but the relationships and roles —
  resolves-to, drum, "this metric doesn't apply here" — stay SME-authored, because
  they're the head start you carry when you write a query blind.

## 3. The guitar metaphor

> "It's like playing the guitar — I know what the song sounds like, I just have to
> figure out which string to pull. I have to know how one entity relates to another."

A guitarist who knows the song hears **intervals**, not finger positions. Change the
tuning and a memorizer is lost; the player who knows intervals adapts — same song,
different strings.

- **The song** = the business question ("which open orders are at risk because material
  hasn't arrived?"). You hear how it resolves: orders *demand* parts, receipts *satisfy*
  demand, lead times *offset* timing.
- **The string to pull** = the physical tables and join keys — mechanical once you hear
  the intervals.
- **A new ERP** = a re-tuning. A purchase order still satisfies a requirement whether
  the table is `po_detail` or `PURC_ORDER_LINE`. The layer keeps intervals (concepts,
  resolves-to, roles) separate from tuning (physical columns per dialect).
- **The palette** = a fake book, not sheet music: SME-verified chord changes so the next
  player can hear the song too. The mapping layer is the tab notation for *this* guitar.
- **The inverse**: someone can memorize finger positions and never hear the music —
  a dashboard user with lineage and field descriptions can reproduce a query but can't
  improvise a new one. Relational metadata gives fret positions, never intervals.

## 4. The order-type matrix is an ontology document

The attached "which order type" guide (Contract Order + MO, Release Order → MO, unlinked
MO, Direct MO, Repetitive MO, MO + Subcontract PO) encodes **relationship semantics**,
not table definitions:

- "Release Order → MO preserves demand lineage" is an interval.
- "Contract Order + Linked MO" exists because a CDRL deliverable must trace to its
  demand source — a governed relationship.
- The cautions are **negative assertions** in planner language: *"do not override
  releases with direct MOs"* is the "not elevate" pattern — an explicitly refused
  relationship, written down so nobody silently creates it.
- Every caution protects lineage. The whole matrix answers one question — "how much
  demand traceability does this scenario require?" — with order type as the mechanism.
  Unlinked MO at one end (no traceability, maximum simplicity), Contract Order + Linked
  MO at the other (full audit trail, maximum configuration burden). A spectrum an
  ontology can name.

The synthetic schema currently lives almost entirely in the "unlinked MO, MRP-driven, no
demand lineage" row. The matrix is a map of relationships the ontology could grow into:
demand-linked orders, release call-offs, subcontract MO→PO chains (outside-service
scaffolding already exists for the last one).

## 5. Warehouse-to-floor movement and throughput

Planning nets supply against demand in time buckets (the MRP grid). But warehouse-to-
floor issue moves at the pace of **throughput**, not the pace of the plan. The plan can
say material is "available" while it's still in the warehouse, unpicked, three days from
the machine that needs it.

The gap — **allocated vs. issued vs. staged at the resource** — is where "we'll probably
be short anyway" lives: the planning cycle sees supply and demand, but not *position*.
If the drum conversation becomes a showcase, that's the buffer's real definition — not
extra stock on a shelf, but stock *staged in front of the pacing resource*.

## Summary

| Knowledge type | Example | Who/what provides it |
|---|---|---|
| Lineage | which columns fed this transform | SQLMesh (mechanical) |
| Descriptions | what this column is called | AI (verbal, reviewable) |
| Intervals / relationships | orders demand parts; receipts satisfy demand | SME-authored ontology |
| Roles | drum, intentional buffer, subordinate station | SME-declared, governed |
| Refusals | "do not override releases with direct MOs" | Negative assertions |
