---
title: Field Description Pipeline + DAB Tab
---
# Field Description Pipeline + DAB Tab

## What & Why
Build the end-to-end field-description (data-dictionary) pipeline and turn the
existing read-only "📋 Field Descriptions" Gradio tab into the authoring surface
for it. This pipeline is the local stand-in for the company's DAB (Data Asset
Bundle): structural column → drafted description → SME edit → certify →
published DAB.

The scaffolding already exists but is inert:
- `api_field_descriptions` (SME display_name / description / example) — 14 seeded rows.
- `dab_field_definitions` (certified DAB definitions) — **empty**.
- `sync_db_to_dab_config.py` — pushes certified rows into `dab_config.json` (tested, but nothing certified to push).
- The Field Descriptions tab — **read-only** browse of the unified schema; cannot author, generate, certify, or publish.

The goal is to make these pieces a working loop the user can drive from the tab.

## Done looks like
- From the Field Descriptions tab the user picks a table + column and sees its
  current display name, description, example value, and certified state.
- The user can edit those fields and save them (persists to `api_field_descriptions`).
- The user can generate an AI-drafted description for the selected column on
  demand (one explicit click, one column at a time), review/edit it, then save.
- An offline/demo fallback produces a deterministic draft when AI is not used,
  so the pipeline works with no API spend.
- The user can mark a definition "certified," which writes the DAB stand-in
  (`dab_field_definitions`).
- A "Publish to DAB" action runs the existing sync so certified definitions flow
  into `dab_config.json`, and the tab reports how many were published.
- The tab shows coverage: how many columns are described / certified per table
  and overall.
- The full described set can also be (re)generated headlessly from one
  idempotent script.

## Out of scope
- The graph export / ArangoDB layer — field descriptions are an overlay, not part
  of the canonical graph export, so no graph regen or Arango reload.
- The Solder resolution report format — already updated in prior work.
- Automatic bulk AI generation across all columns. AI drafting is on-demand,
  per-column, and explicit, to respect the project's cost-conscious preference.

## Steps
1. **Pipeline core** — Add a generation/curation module that builds a draft
   description (display name, plain-language meaning, example) for a given column
   from the structural schema. It exposes an optional AI-assisted draft used only
   on explicit request, plus a deterministic non-AI fallback for demo/offline
   mode. Persists via idempotent upsert into `api_field_descriptions` (reusing the
   existing save helper).
2. **DAB stand-in population** — Wire the certify path so SME-approved
   definitions are written to `dab_field_definitions`, and surface the existing
   `sync_db_to_dab_config` flow as a "Publish to DAB" action so certified rows
   publish into `dab_config.json`.
3. **Make the tab interactive** — Extend the read-only tab with column selection,
   editable fields, and Save / Generate AI Draft / Certify / Publish-to-DAB
   controls; show per-table and overall coverage and certified state; refresh the
   view after each action.
4. **Headless pipeline entry** — Extend the existing seed so the whole described
   set can be regenerated idempotently from one script (the stand-in DAB loader),
   keeping it safe to re-run.
5. **Tests** — Cover pipeline upsert idempotency, the certify → `dab_field_definitions`
   write, and that the tab helper functions return the expected rows. Keep the
   post-merge suite green.

## Relevant files
- `hf-space-inventory-sqlgen/app.py:360-573`
- `hf-space-inventory-sqlgen/app.py:2859-2895`
- `hf-space-inventory-sqlgen/app.py:5142-5216`
- `hf-space-inventory-sqlgen/scripts/sync_db_to_dab_config.py`
- `hf-space-inventory-sqlgen/dab_config.json`
- `hf-space-inventory-sqlgen/production_dispatcher.py:184`
- `hf-space-inventory-sqlgen/solder_engine.py:624-649`
- `hf-space-inventory-sqlgen/tests/test_sync_db_to_dab_config.py`
- `replit_integrations/seed_field_descriptions.py`
- `scripts/post-merge.sh`