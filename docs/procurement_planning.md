# Procurement Planning — The SolderEngine Interaction Trace

**Audience:** procurement / planning leaders and reviewers (non-engineers welcome).
**Purpose:** show *exactly* how a plain-English procurement question becomes a
trusted, SME-approved SQL answer — without a language model ever writing SQL.
**Dialect:** SQLite (`manufacturing.db`), the synthetic ground-truth target.

> **The one-sentence promise (the "Solder Pattern").** The system uses AI to
> *understand the question*, and a governed semantic layer to *choose a
> pre-approved answer*. The AI selects; it never generates. Every SQL statement
> that runs was written and approved by a subject-matter expert (SME) ahead of
> time. If the question can't be mapped to an approved answer, the system
> **refuses** rather than inventing SQL.

---

## 1. The procurement question we will trace

> **"What do I need to reorder?"**

In plain terms: *which parts have fallen to or below their reorder point and
should trigger a replenishment purchase order?* This is the front door of
procurement planning — the daily "what do I buy today" question.

We will follow this exact question through five stages, then contrast it with a
second question ("what's my economic order quantity?") that takes a slightly
different internal route. Both are grounded in the real approved inventory views
in this repository — nothing here is invented for the example.

---

## 2. The five stages at a glance

```
  "What do I need to reorder?"
              │
              ▼
  ┌───────────────────────────────────────────────────────────┐
  │ STAGE 1 · INTENT DETERMINATION                             │
  │ Closed-vocabulary router (ProductionDispatcher)            │
  │  → intent, concepts, perspective, confidence               │
  │  (an LLM classifies; it does NOT write SQL)                │
  └───────────────────────────────────────────────────────────┘
              │  intent=inventory_planning
              │  concepts=[ReorderPoint]  perspective=Inventory_Transactions
              ▼
  ┌───────────────────────────────────────────────────────────┐
  │ STAGE 2 · ONTOLOGICAL MAPPING SELECTION                    │
  │ Semantic layer (SolderEngine + graph)                      │
  │  primary-binding-key fast path  OR  concept-path resolution │
  │  perspective filter · elevate/suppress weights · resolves_to│
  └───────────────────────────────────────────────────────────┘
              │  concept ReorderPoint  ─resolves_to→  part.reorder_point
              │  binding_key = inventory_reorderpoint_20260703_000001
              ▼
  ┌───────────────────────────────────────────────────────────┐
  │ STAGE 3 · GROUND-TRUTH SQL RESOLUTION                      │
  │ reviewer_manifest.json  →  the physical approved .sql file  │
  │  (validation_status must be APPROVED)                       │
  └───────────────────────────────────────────────────────────┘
              │  reads inventory_reorderpoint_20260703_000001.sql (as text)
              ▼
  ┌───────────────────────────────────────────────────────────┐
  │ STAGE 4 · STRUCTURAL MATCH + ASSEMBLY                      │
  │ SQLGlot parses the AST; match is on physical TABLES,       │
  │  not on CTE wording; then transpile to the target dialect  │
  └───────────────────────────────────────────────────────────┘
              │
              ▼
      Governed SQL, ready to run (SQLite)
```

---

## 3. Stage 1 — Intent determination (understand, don't generate)

**Component:** `ProductionDispatcher` (`hf-space-inventory-sqlgen/production_dispatcher.py`).

The dispatcher's only job is to map free text onto a **closed vocabulary** of
Intents, Concepts, and Perspectives that already exist in the semantic model. It
is explicitly a *Semantic Router, not a SQL generator*.

Two interchangeable routers produce the same shape of answer:

| Router | When it runs | How it decides |
|---|---|---|
| **Live LLM** (Mistral-7B-Instruct via HuggingFace) | Normal operation | A system prompt lists every allowed Intent/Concept/Perspective and forces a JSON-only reply. Anything the model returns that is *not* in the vocabulary is filtered out or down-graded to low confidence. |
| **Mock keyword router** | Demo mode / when the API is unavailable (cost-conscious fallback) | Deterministic keyword match against `MOCK_ROUTES` (e.g. `"reorder"`, `"replenish"`). |

For our question the word **"reorder"** maps to:

```json
{
  "intent":      "inventory_planning",
  "concepts":    ["ReorderPoint"],
  "perspective": "Inventory_Transactions",
  "confidence":  "mock"
}
```

> The `confidence` value depends on the router: the deterministic keyword router
> returns `"mock"`, while the live LLM returns its own `"high"`/`"medium"`/`"low"`
> self-assessment (and anything out-of-vocabulary is forced to `"low"`).

Key guarantees at this stage:

- **The output is a classification, never SQL.** The model chooses *labels* from
  a fixed list; it cannot emit a query.
- **Out-of-vocabulary answers are rejected.** An unknown intent is flagged
  low-confidence; concepts not in the catalog are dropped.
- **Off-topic questions stop here.** Anything unrelated to manufacturing returns
  `OUT_OF_SCOPE` with a helpful hint, and no SQL is produced (see §7).

---

## 4. Stage 2 — Ontological mapping selection (choose the approved answer)

**Components:** `SolderEngine` (`solder_engine.py`) + the semantic graph
(SQLite bridge tables, mirrored to ArangoDB).

Now the system turns *labels* into *a specific approved answer*. There are two
routes, and which one runs depends on the intent.

### 4a. The fast path — primary binding key

Some intents are pinned directly to one approved snippet via a
`primary_binding_key` on the intent record. If present, the dispatcher resolves
that key immediately and skips concept reasoning. (Our contrast question, EOQ,
takes this path — see §6.)

### 4b. The concept path — perspective, weights, and `resolves_to`

`inventory_planning` (our reorder question) has **no** primary binding key, so
the engine resolves through the concept graph. Three graph mechanics drive the
choice:

1. **Perspective filter.** The question carries a *perspective* —
   `Inventory_Transactions` — that scopes which meaning of a concept applies.
   The same field can mean different things to Finance vs. Inventory; the
   perspective is the lens.

2. **Elevate / suppress weights (a binary gate, not a score).** Each Intent →
   Concept link carries a weight: `+1` = elevated (actively selected), `0` =
   neutral, `-1` = suppressed (explicitly excluded). For `inventory_planning`
   the graph elevates:

   | Intent | Concept | Weight | Meaning |
   |---|---|---|---|
   | inventory_planning | ReorderPoint | **+1** | elevated |
   | inventory_planning | LeadTime | +1 | elevated |
   | inventory_planning | OnHandQuantity | +1 | elevated |

   The router extracted **ReorderPoint** as the concept in play, and it is
   elevated, so it is kept.

3. **`resolves_to` — concept to physical column.** The elevated concept binds to
   a real column through a `resolves_to` edge:

   ```
   ReorderPoint  ──resolves_to──▶  part.reorder_point
   context hint: "Part reorder point — replenishment trigger level"
   ```

The result of Stage 2 is a single **binding key**:
`inventory_reorderpoint_20260703_000001` — the address of an approved snippet.

> **The ArangoDB / graph-topology angle.** These Intent→Concept→Column links are
> real edges in the semantic graph. The graph is a *navigation layer*: it maps a
> question's concept to its anchor column and perspective. It deliberately does
> **not** encode row-level rules (e.g. "only active parts") — those live in the
> approved SQL. Routing is the graph's job; the definition is the snippet's job.
> This is what keeps the graph metadata stable while SQL definitions evolve.

A note on ambiguity: the runtime dispatcher keeps whichever elevated concept(s)
the router extracted and resolves each independently (a concept is only dropped
when its weight is suppressed, i.e. `<= -1`). The *formal* "there must be exactly
one valid meaning" guarantee — where two equally-valid concepts for the same
(intent, field) is flagged as an **ambiguous** modeling error and zero valid
concepts as an **incomplete perspective** — is defined in the standalone
resolution algorithm (`semantic_reasoning.py`), which the SME modeling process
uses to keep the graph clean. The two work together: the modeling algorithm
guarantees the graph is unambiguous, so the runtime path lands on a single
binding (see §7).

---

## 5. Stage 3 — Ground-truth SQL resolution (governance gate)

**Artifact:** `app_schema/ground_truth/reviewer_manifest.json`.

The binding key is looked up in the reviewer manifest — the SME sign-off ledger.
Its entry for our key reads (abridged):

```json
"inventory_reorderpoint_20260703_000001": {
  "concept_anchor":    "REORDERPOINT",
  "perspective":       "Inventory_Transactions",
  "file_path":         ".../sql_snippets/inventory_reorderpoint_20260703_000001.sql",
  "validation_status": "APPROVED",
  "sme_justification": "Parts at or below reorder point — replenishment trigger
                        report ... primary MRP replenishment planning query"
}
```

Two hard rules enforce governance here:

- **Only `APPROVED` entries load.** Any snippet marked `ARCHIVED` (or anything
  other than `APPROVED`) is skipped entirely — it can never be served.
- **The SQL is read from a file, verbatim.** The engine opens the `.sql` file
  and uses its text as-is. Nothing is synthesized. The approved file *is* the
  definition.

The approved reorder view (`inventory_reorderpoint_20260703_000001.sql`):

```sql
SELECT
    p.part_id,
    p.part_description,
    p.part_class,
    p.unit_of_measure,
    p.on_hand_qty,
    p.reorder_point,
    p.lead_time_days,
    ROUND(p.on_hand_qty - p.reorder_point, 2) AS qty_vs_reorder,
    CASE
        WHEN p.on_hand_qty <= 0                THEN 'STOCKOUT'
        WHEN p.on_hand_qty <= p.reorder_point  THEN 'REORDER'
        ELSE 'OK'
    END AS replenishment_status
FROM part p
WHERE p.active = 1
ORDER BY (p.on_hand_qty - p.reorder_point) ASC
```

Notice the `resolves_to` promise from Stage 2 is literally satisfied: the concept
**ReorderPoint** maps to `part.reorder_point`, and the query is built around that
column.

---

## 6. Stage 4 — Assembly and transpilation (SQLGlot)

**Component:** SQLGlot AST parsing and transpilation in `solder_engine.py`.

At request time the approved SQL is parsed into an Abstract Syntax Tree (AST) —
a structured representation of what the query actually *does* — and then
**transpiled** to the requested dialect (SQLite by default; the *same* approved
definition can also emit T-SQL, PostgreSQL, etc. without being rewritten by
hand). The governed SQL is returned, ready to run. Working on the AST rather than
raw string-editing is what makes cross-dialect output reliable.

### The structural principle behind the AST (a design rule, not a per-request gate)

The reason the AST matters is a governance principle: **the identity of a view is
its physical tables and joins, not its CTE wording.** A snippet can be rewritten
with different helper-CTE names, comments, or formatting; what must stay stable is
the set of real tables it reads and how they join.

This principle is made concrete by `view_ontology_extractor.py`, which reads each
approved view's AST and records its structural fingerprint into the
`sql_view_ontology` metadata table. Importantly, this runs at **boot / seeding
time** (in `app.py`), building a durable catalog — it is *not* a per-request
validation gate inside the dispatch call. For each view it extracts:

- **Physical tables** (for the reorder view: `part`) — real tables, excluding CTE aliases.
- **Joins** — the relationships (the reorder view is single-table, so none).
- **State predicates** — set-membership rules like `p.active = 1`.
- **Grain** — what one row represents (here: one active part).

So the structural guarantee is established once, up front, when the approved views
are catalogued — and the request-time path simply parses and transpiles the view
that governance already blessed.

### A useful contrast — the EOQ question takes the fast path

Ask instead: **"What's my economic order quantity?"**

- **Stage 1:** `"eoq"` → intent `inventory_eoq`, concept `EconomicOrderQuantity`,
  perspective `Inventory_Transactions`.
- **Stage 2:** `inventory_eoq` *does* carry a `primary_binding_key`
  (`inventory_eoq_20260703_000010`), so the engine takes the **fast path** — it
  resolves that key directly, no concept-weight reasoning needed.
- **Stages 3–4:** identical governance and assembly. The approved EOQ view joins
  `po_line` to `purchase_order` (to exclude cancelled POs); its structural
  fingerprint — catalogued at boot time — records *both* physical tables, again
  keyed on tables rather than the helper subquery's wording.

Same pattern, same guarantees; only Stage 2's entry point differs. This is why
the architecture is robust: every question converges on an approved, file-backed
definition.

---

## 7. Fail-closed behavior (what happens when it *can't* answer)

The system is built to **refuse rather than hallucinate**. Each stage has an
explicit stop:

| Situation | Where it's caught | What the user gets |
|---|---|---|
| Question is off-topic | Stage 1 (runtime) | `OUT_OF_SCOPE` + a hint listing valid topics; **no SQL**. |
| Intent recognized but no concept extracted | Stage 1→2 (runtime) | A "be more specific" message; **no SQL**. |
| Two equally-valid meanings for the same (intent, field) | Stage 2 (modeling algorithm) | Flagged as an *ambiguous modeling error* by `semantic_reasoning.py` — caught before the graph is published, not guessed. |
| No valid meaning for a field | Stage 2 (modeling algorithm) | Flagged as an *incomplete perspective* (missing path) by `semantic_reasoning.py`. |
| Binding key missing or not `APPROVED` | Stage 3 (runtime) | Empty SQL + an explicit "missing ground truth" warning. |
| Transpilation to the target dialect fails | Stage 4 (runtime) | The SQLite text is returned with a warning rather than a silently broken query. |

The through-line: **no fallback ever fabricates SQL.** Silence or an explicit
error is always preferred over an unverified answer — exactly what a regulated
aerospace-manufacturing environment requires.

---

## 8. How this maps to the architecture diagram

This trace corresponds one-to-one with the three-layer architecture diagram:

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. STRUCTURAL MAPPING                                        │
  │  • ArangoDB (tracks edge topologies & 'resolves_to' paths)  │
  │  • Ontop / SPARQL (defines virtual ontology skeleton views) │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 2. THE COMPILATION HINGE                                     │
  │  • ProductionDispatcher (closed intent classification)      │
  │  • SolderEngine (extracts metadata / matches ground-truth)  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 3. PROCESSING WORKBENCH                                      │
  │  • SQLGlot (parses AST tables & transpiles target dialect)  │
  └─────────────────────────────────────────────────────────────┘
```

| Diagram layer | Stage(s) in this trace |
|---|---|
| **1 · Structural Mapping** — ArangoDB edge topologies & `resolves_to` paths; Ontop / SPARQL virtual ontology skeleton | Stage 2's *substrate*: the perspective filter, elevate/suppress weights, and `resolves_to` edges live here as the graph that maps concept → anchor column. |
| **2 · The Compilation Hinge** — ProductionDispatcher + SolderEngine | Stages 1→3: the dispatcher does closed-vocabulary intent classification, then the SolderEngine matches that intent/concept to a ground-truth binding and loads the APPROVED `.sql` file. This is the pivot where an understood question becomes an approved definition. |
| **3 · Processing Workbench** — SQLGlot | Stage 4: runtime AST parse + dialect transpile, keyed on the physical-table fingerprint catalogued at boot. |

---

## 9. Summary — why procurement can trust the answer

1. **AI understands, SMEs decide.** The model only classifies the question into a
   fixed vocabulary; it can never write or alter SQL.
2. **Every answer is pre-approved.** SQL comes from files whose manifest entry is
   `APPROVED`. Archived or unapproved definitions can never be served.
3. **Meaning is governed, not guessed.** Perspective + weights + `resolves_to`
   edges force each concept onto exactly one physical column definition.
4. **Structure is catalogued.** Each approved view's physical-table fingerprint is
   extracted into metadata at boot time, and SQLGlot transpiles the blessed view
   cleanly across dialects at request time.
5. **It fails closed.** Ambiguity, off-topic questions, or a missing approved
   mapping produce an explicit refusal — never a fabricated query.

---

### Referenced source files

- `hf-space-inventory-sqlgen/production_dispatcher.py` — intent determination (Stage 1)
- `hf-space-inventory-sqlgen/solder_engine.py` — mapping, resolution, assembly (Stages 2–4)
- `hf-space-inventory-sqlgen/semantic_reasoning.py` — formal resolution algorithm & ambiguity detection
- `hf-space-inventory-sqlgen/view_ontology_extractor.py` — AST structural extraction (Stage 4)
- `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json` — SME sign-off ledger (Stage 3)
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_reorderpoint_20260703_000001.sql` — the traced approved view
- `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/inventory_eoq_20260703_000010.sql` — the fast-path contrast view
- `docs/mrp_set_semantics_criteria.md` — the set-semantics standard behind the inventory concepts
