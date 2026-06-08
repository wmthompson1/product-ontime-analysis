---
name: FK canonical graph model
description: How foreign keys are modeled in graph metadata, and the code-vs-live-data divergence to watch for.
---

# Foreign keys in the graph metadata model

Canonical FK representation (source of truth = `replit_integrations/export_graph_metadata.py`
and `graph_metadata_canonical_example.{md,json}`):

- **`foreign_key`** — a boolean attribute on the **column node** itself.
- **`references`** — a structural **edge** (`edge_family: structural`, `edge_type: references`,
  `perspective: system`) from the **child column node → parent column node**, carrying
  `references_table` / `references_column`.

There is **NO `FOREIGN_KEY` edge type** and **no `is_foreign_key` edge property**. Both are retired.
Frontend triple/relationship builders offer `references` (column→column), not `FOREIGN_KEY` (table→table).

**Why:** keeps frontend, fixtures, tests, and planning docs describing FK the same way the
exporter actually emits it.

**How to apply:** to read whether a column is an FK, read the node's `foreign_key` boolean; to
get the target, traverse the `references` edge (`FILTER e.edge_type == "references"`) and read the
parent vertex or the edge's `references_table`/`references_column`.

## Code-vs-live-data divergence (important)

The **live ArangoDB graph still carries the OLD model**: FK edges with an `is_foreign_key == true`
property, and column nodes that lack the `foreign_key` boolean. Code that is aligned to the canonical
model (the `Utilities/ArangoFixtures/*` AQL prototypes, `verify_load_and_naming.py`) therefore FAILS
against the un-migrated live graph even though it is correct.

**Why:** data migration is intentionally decoupled from code alignment — rewriting live edges/props
is a separate concern. The canonical-aligned fixtures are forward-looking validators that pass once a
migration populates `references` edges + `foreign_key` node attrs.

**How to apply:** don't "fix" these fixtures by reverting to `is_foreign_key`/`FOREIGN_KEY` when they
fail on live data — that's the expected state pre-migration. `scripts/post-merge.sh` does NOT run these
prototypes, so it stays green regardless.
