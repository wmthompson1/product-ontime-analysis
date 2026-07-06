---
name: Shared selector pane design
description: Design contract for the app-wide Selector tab / shared selection pane (abstract tags vs concrete cascade).
---

# Shared selector pane design

Rule: the tag filter is a **searchable multi-select** (type-to-filter, not chips) over the 15 stakeholder perspectives from `schema_perspectives` — the same vocabulary/order as the Define Relationship category chips. Never use abstract intent categories as tags or cascade levels; the user rejected them. The cascade is fully concrete: Table → Column → Concept → Intent → Ground-truth query — exactly 5 dropdowns in one horizontal row.

**Why:** user said abstract terms are for lightweight tag filtering only; standing prefs are concrete filter levels, max 5 per row, narrow dropdowns, and search/contains multi-select (they rejected a CheckboxGroup of chips). The Selector tab is meant to become the shared selection pane merged into most tabs.

**How to apply:** reuse this shape (tag filter on top, concrete chain below) on other tabs. Tags filter tables/concepts via `schema_perspective_concepts` but must NOT filter intents — `schema_intent_perspectives` is sparse and double-filtering cuts valid chains (Finance showed 0 queries despite reachable ones). Surface coverage honestly and *up front*: show the reachable ground-truth query count as soon as tags are picked (computed live, never a hardcoded list), so users don't drill 4 levels into a dead end. Ground-truth queries exist only for defect_*/supplier_* intents today; all inventory_* intents have zero.
