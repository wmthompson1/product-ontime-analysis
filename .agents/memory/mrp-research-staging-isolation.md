---
name: MRP research-staging isolation
description: How document-derived terminology is staged as proposals without ever touching the certified graph; the governance invariants that must hold.
---

# Document-derived terminology → mrp_research (proposals only)

The librarian can read a terminology document and STAGE proposed terms into the
SEPARATE `mrp_research` ArangoDB graph, anchored to the SME-approved
perspectives/categories. Document content is PROPOSALS, never certified ground truth.

**Why:** Solder Pattern — definitions are SME-approved; LLM/document content must
never become approved SQL/perspective definitions or contaminate `manufacturing_graph`.

**How to apply (invariants that must keep holding):**
- All live writes go through ONE chokepoint: the librarian's guarded targets resolver
  inside the commit path. It refuses any DB resolving to the certified graph
  (`ARANGO_DB`, `manufacturing_graph`, `semantic_graph`) and any collection not
  namespaced under `ai_research`. Keep new write paths routed through this, not a
  second connector.
- The commit gate (`MRP_ENABLE_GRAPH_COMMIT`) is an EXTERNAL operator control. A
  `--commit`/`commit=True` flag expresses INTENT only; it must NOT auto-enable the
  gate. Both the flag and the env must be true to write.
- Approved perspectives/categories are COPIED into the research graph as
  reference/anchor nodes; candidate edges point at those research-side anchors, so no
  edge ever references a certified-graph handle. Edge handles are normalized with the
  call-time guarded collection (never an import-time global), and any handle outside
  the research node collection is rejected.
- Extraction is deterministic by default (glossary `Term — definition` parsing +
  token-overlap anchoring); AI is intentionally off. Node wording stays
  unmistakably non-authoritative: `proposed_definition`, `approval_status:proposed`,
  `source_type:document_extraction`, `certified:false`.
- Keys are stable slugs (per-term), so re-staging is idempotent (upsert, no dup).
  Per-run artifacts land under a gitignored staging root.
