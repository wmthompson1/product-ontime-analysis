# Gate isSelfLoop by structural mode

## What & Why
The code review for Task #144 flagged a UX inconsistency: `isSelfLoop` is currently
derived without checking `isStructural`, so if a user types "FOREIGN_KEY" in the
semantic mode free-text predicate field with the same table selected as both source
and target, "Add to Graph" is silently disabled but no warning is ever shown (the
amber warning renders inside the `isStructural` branch only). This violates the
principle that a disabled button must always have a visible reason.

FOREIGN_KEY is a structural predicate — it has no semantic-mode meaning. Gating
`isSelfLoop` with `isStructural` is the correct fix: the guard applies only where
FOREIGN_KEY is a valid, selectable predicate.

## Done looks like
- In structural mode: FOREIGN_KEY self-loop still shows the amber warning and
  disables the button — behaviour unchanged.
- In semantic mode: typing "FOREIGN_KEY" with matching source and target no longer
  disables the button silently; "Add to Graph" remains enabled (as it is for any
  other custom semantic predicate).
- One-line change; no new UI elements, no backend changes.

## Out of scope
- Any other predicate guards or semantic-mode validation.
- Changes to the FastAPI backend or test suite.

## Steps
1. **Tighten `isSelfLoop` derivation** — Prepend `isStructural &&` to the existing
   `isSelfLoop` boolean so the self-loop guard is only active in structural mode
   where FOREIGN_KEY is a valid, selectable predicate.

## Relevant files
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx:525`
