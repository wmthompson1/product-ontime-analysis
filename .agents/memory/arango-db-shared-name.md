---
name: ARANGO_DB points at the certified graph
description: Why external/private-repo scripts must not default a scratch/research Arango DB to the shared ARANGO_DB env var in this repo.
---

# ARANGO_DB is the certified database here

In this repo the `ARANGO_DB` environment variable resolves to the **certified**
`manufacturing_graph` database (the approved semantic layer). Many scripts copied
in from the private Windows repo were written for a standalone context and default
their database to `os.getenv("ARANGO_DB", "<scratch>")`.

**Rule:** any *non-canonical* graph (research, scratch, ingestion, experiment)
must get its own dedicated env var and default — never fall back to `ARANGO_DB`.
Example: the MRP librarian uses `MRP_RESEARCH_ARANGO_DB` (default `mrp_research`)
and deliberately does NOT read `ARANGO_DB`.

**Why:** falling back to `ARANGO_DB` silently points "research" writes at the
certified `manufacturing_graph`, contaminating the approved layer. This was caught
only because a verification print showed `arango db: manufacturing_graph` instead
of the intended isolated DB. A gated/disabled writer hides the bug until someone
flips the enable flag.

**How to apply:** when adapting any private-repo script that talks to ArangoDB,
grep for `getenv("ARANGO_DB"` / `ARANGO_DATABASE` and confirm a non-canonical
target uses its own knob. Keep writers gated off by default, but fix the DB
resolution regardless of the gate — separation must hold the moment writes turn on.
