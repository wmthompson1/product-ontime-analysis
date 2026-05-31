---
name: Solder Pattern — graph architecture principles
description: Core architectural rules for the manufacturing semantic layer graph. Prevents wrong assumptions about node types, predicates, and AI role.
---

## Graph node types
Exactly two: **tables** and **columns**. Perspectives, intents, concepts, bindings, and categories are NOT nodes — they are edge properties or separate semantic collections (not in the structural containment graph).

## ELEVATES is the universal semantic predicate
MEASURES, SIGNALS, GROUPS_BY, CONTRIBUTES_TO, INSPECTS — all of these collapse into ELEVATES. The binary weight (1/0) and the `perspective` edge property do the differentiation. Do not add new semantic predicates for nuance; use edge properties instead.

## ELEVATES weight semantics
Weight is a **binary gate**, not a score:
- weight=1 → this table/column is in the candidate set for its Concept
- weight=0 → exists in graph but deactivated (switchboard is dark)
Not "high confidence" — deterministic metadata set by an SME.

## AI role
Selection only — never generation. Given a question, the graph returns all weight=1 edges for the matched concept. The LLM picks among those pre-approved SQL snippets. This is the Solder Pattern.

## Column names carry meaning
`quality_events.defect_count → ELEVATES → DefectSeverity` is deterministic metadata, not probabilistic. The column name IS the semantic claim — the ERP developer baked it in. Column-level ELEVATES is more precise than table-level ELEVATES for this reason.

## SUPPRESSES does not exist
ELEVATES with weight=0 is the suppression mechanism. Do not add SUPPRESSES back.

## Perspective is an edge property
Perspective is never a graph node. It lives as a property on bridge rows (Perspective_Intents, Perspective_Concepts) and on edges. OPERATES_WITHIN scopes an intent to a perspective domain via an edge property.
