# Target Entity Panel — Source Panel Parity

## What & Why
The "Select Target Entity" column in `DefineRelationship.tsx` is currently a bare search input + a plain `<select>` dropdown. The "Select Source Entity" column next to it has full interactive search with match-mode selection, live match count, and a grouped scrollable results list with selection highlighting and qualified-name sub-labels. Bringing Target Entity to parity makes the two panels consistent and gives the same power-user search controls on both sides of the relationship builder.

## Done looks like
The Target Entity column contains, in order:
1. **Search input + Match Mode dropdown** — same row layout as Source Entity; input placeholder changes dynamically based on the active mode (Wildcard → `"*_orders, quality_*"`, Regex → `"^quality_.*$"`, others → `"Search..."`); dropdown shows Contains / Starts with / Wildcard / Regex with Regex labelled "advanced"; selecting a mode closes the dropdown.
2. **Match count label** — `"{n} match(es)" · {mode} "{query}"` (query part only shown when search is non-empty), identical to Source.
3. **Grouped results list** — scrollable (`max-h-[140px]`), grouped by source namespace (e.g. ERP_Instance_1, semantic_layer), with group header rows (bold, uppercase, record count), and per-row: `▸ {table_name}` with `{qualified_name}` as a muted sub-label. Selected row highlighted with left accent border (`border-emerald-400`) and `text-emerald-300` text. Uses the same `searchEntities(targetSearch, targetMode)` function already defined in the file so that Wildcard / Regex / Starts-with modes work correctly.
4. **Context block** — unchanged from today: label "Context:", value "Collection: {SELECTED_TARGET}".

## State additions
Add two new state variables to the `DefineRelationship` component (alongside the existing `sourceMode` / `sourceModeOpen`):
- `targetMode: MatchMode` — default `"Contains"`
- `targetModeOpen: boolean` — default `false`

## Derived value
Add one derived value (alongside `sourceResults`):
- `targetResults = searchEntities(targetSearch, targetMode)`

The `selectedTarget` click handler updates `setSelectedTarget` with `"${rec.table_name} (${source})"` — same display format as Source Entity.

## File
`artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`

No other files need changing.
