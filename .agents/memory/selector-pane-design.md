---
name: Shared selector pane design
description: Design contract for the app-wide Selector tab / shared selection pane (abstract tags vs concrete cascade).
---

# Shared selector pane design

Rule: the tag filter (CheckboxGroup) uses the 15 **stakeholder perspectives** from `schema_perspectives` — the same vocabulary as the Define Relationship category chips (Quality, Payables, Work_Orders, …), ordered by `perspective_id`. Never use abstract intent categories as tags or cascade levels; the user rejected them. The cascade itself is fully concrete: physical Table → Column (✦ marks columns with a `resolves_to` edge) → Concept → Intent (weight=1 elevations) → Ground-truth query — exactly 5 dropdowns in one row. Tag filtering flows through `schema_perspective_concepts` (concepts/tables) and `schema_intent_perspectives` (intents).

**Why:** user explicitly said abstract terms are "best used for lightweight tag filtering" and their standing pref is concrete filter levels, max 5 per selector row, narrow dropdowns. The Selector tab is meant to become the shared selection pane merged into the majority of tabs.

**How to apply:** when adding selectors to other tabs, reuse this shape (tags on top, concrete chain below) instead of inventing per-tab hierarchies. Coverage gaps must be surfaced honestly in the summary panel (e.g. "no tables mapped for these tags", "no ground-truth queries — chain ends here"), never silently empty or padded with fallbacks. Packed choice values use `||` with maxsplit parsing so the free-text last segment (query name) may contain the separator.
