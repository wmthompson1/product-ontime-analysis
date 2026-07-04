---
title: MRP research term approval workflow
---
# MRP Research Term Approval Workflow

## What & Why
The stager already produces a reviewable CSV of proposed terms from the terminology `.docx`.
What's missing is a way to mark individual terms as approved or rejected and then commit
only the approved ones to the `mrp_research` ArangoDB graph (the intermediate research
sandbox — never the certified `manufacturing_graph`).

The approach follows the project's existing CSV-approval pattern (same model as
`masking_matrix.csv`, `field_descriptions.csv`): the CSV is the SME-facing approval
artifact. A reviewer edits the `reviewer_decision` column directly in the CSV, then
runs the committer script to push approved rows into the research graph.

## Done looks like
- The stager's CSV output gains a `reviewer_decision` column (default `proposed`;
  reviewer sets individual rows to `approved` or `rejected` before committing).
- `scripts/mrp_approval_committer.py` reads a staging run's reviewed CSV, filters for
  `reviewer_decision == approved`, and upserts those term nodes and their candidate edges
  into the `mrp_research` graph via the librarian's gated commit path.
- Default is a **dry run** — prints what would be committed without touching ArangoDB.
  A `--commit` flag triggers the actual write (mirrors the stager's own pattern).
- Running the committer on a CSV with no approved rows exits cleanly with a summary and
  touches nothing.
- A `--run-id` flag (or `--csv` path) lets the user point at any past staging run folder,
  not just the latest.
- The committer reuses the existing `commit_to_arangodb` guard in `librarian_server.py`
  so the certified graph is structurally unreachable.

## Out of scope
- A Gradio UI for review — the CSV is the review surface.
- Promoting terms from `mrp_research` into the certified `manufacturing_graph`
  (that is a separate, later step requiring full SME sign-off).
- Changes to the stager's extraction or anchoring logic.
- Bulk approve-all shortcut; every term requires an explicit `approved` decision.

## Steps
1. **Add `reviewer_decision` to stager output** — extend `mrp_terminology_stager.py`
   to include a `reviewer_decision` column (value `proposed`) in the CSV and a matching
   field in the JSON payload nodes, so every staging artifact is ready for review
   out of the box.
2. **Build `scripts/mrp_approval_committer.py`** — reads a staging run CSV, collects
   nodes whose `reviewer_decision == approved`, resolves their candidate edges from the
   companion `proposed_terms.json`, dry-runs by default, writes to `mrp_research` on
   `--commit`. Prints a per-term decision summary regardless of mode.
3. **Wire the committer into the librarian's `stage_terminology` tool** — add a note in
   the tool's return payload pointing at the staging folder path so the next step
   (running the committer) is self-documenting in the MCP response.
4. **Tests** — fixture staging CSV/JSON, assert approved-only filtering, dry-run produces
   no DB writes, and missing/invalid `reviewer_decision` values fail closed with a clear
   message.

## Relevant files
- `scripts/mrp_terminology_stager.py`
- `scripts/librarian_server.py`
- `mrp_research_staging/20260627T185639Z/proposed_terms.csv`
- `mrp_research_staging/20260627T185639Z/proposed_terms.json`
- `mrp_research_staging/20260627T185639Z/manifest.json`