---
name: sqlmesh-staging-summary
description: Use when the user asks to summarize SQLMesh models by category, especially for staging models under Utilities/SQLMesh/models/staging. Trigger phrases include "summarize sqlmesh models", "categorize staging models", "group SQLMesh staging files", and "inventory staging models".
---

# SQLMesh Staging Model Summary

## Purpose
Summarize SQLMesh staging models by category using files in `Utilities/SQLMesh/models/staging`.

## When to use
- User asks for SQLMesh model inventory by category.
- User asks for a summary of staging models.
- User asks what model groups exist in SQLMesh staging.

## Workflow
1. Enumerate model files under `Utilities/SQLMesh/models/staging`.
2. Group files by practical category inferred from naming and path patterns.
3. Provide counts per category and list model file names.
4. Call out uncategorized or ambiguous files separately.

## Category heuristics
- Use folder names first if present.
- Use filename prefixes/keywords next (for example: supplier, delivery, defect, ncm, production, inventory, quality, finance).
- If no clear signal exists, place in `uncategorized`.

## Response format
1. One-line scope statement with total model count.
2. Category table with `category`, `count`, and representative files.
3. `uncategorized` section (if any).
4. Brief recommendations for cleanup (naming consistency, folder structure), if useful.

## Guardrails
- Use repository-relative paths in output.
- Do not invent files; only report discovered files.
- Keep summary concise and structured.
