# Graph Key/ID Guardrail

## What & Why
ArangoDB `_key`/`_id` values are currently built in several inconsistent, *lossy*
ways across the repo (naive `/`→`_` replacement, regex-strip + SHA-1 truncation,
and raw `table::`/`column::` concatenation). None are reversible, so two distinct
source names can collapse to the same key, and an illegal character can still slip
through. The private repo solves this with a single **reversible hex-encoding
scheme** that the user observed in production:

- `_x5F_` = hex `5F` = `_` (underscore)
- `_x2E_` = hex `2E` = `.` (period)
- e.g. `table_x5F_Live_x2E_dbo_x2E_HOLD_x5F_REASON` decodes to
  `table_Live.dbo.HOLD_REASON`

We will centralize key generation behind one shared, reversible codec + a
validation guardrail so every key is ArangoDB-legal and round-trips back to its
source name.

## Hard constraints (from ArangoDB + the private repo)
- A `_key` may **never contain `/`** — `/` is the collection/key separator inside
  `_id` (`collection/_key`). It must be encoded or the build must hard-fail.
- `_key` also disallows spaces and many punctuation chars, is max 254 bytes, and
  is case-sensitive. Legal set is letters, digits, and a limited punctuation set.
- Encoding must be **reversible**: `decode(encode(x)) == x` for any source name,
  including names that already contain `_x..._`-looking substrings.
- Source case is preserved (the live graph keeps `EMPLOYEE`, `corrective_actions`,
  `Staging.WODS_Output`, `dbo.*` verbatim).

## Done looks like
- One shared codec is the *only* way keys are generated; calling it on a name like
  `Live.dbo.HOLD_REASON` yields the `_x2E_`/`_x5F_` encoded form and decodes back
  exactly.
- Any attempt to produce a `_key` containing `/` (or other illegal characters) is
  either safely encoded or rejected with a clear, actionable error — never silently
  written.
- The metadata export and the central persistence layer both route through the
  shared codec, replacing the ad-hoc sanitizers.
- Automated tests prove round-trip identity, `/` safety, and known vectors, and run
  as part of the post-merge suite.

## Out of scope
- Migrating/re-encoding the data already stored in the live ArangoDB graph.
- Changing the semantic-layer model (perspective/intent/concept stay edge
  properties, not nodes).
- Finalizing which prefix convention is canonical beyond documenting the decision
  (see the constraint note below).

## Steps
1. **Reversible key codec** — Add a shared module that encodes every character
   outside a safe alphanumeric whitelist as `_xHH_` (2-digit lowercase hex, e.g.
   `_`→`_x5F_`, `.`→`_x2E_`) and a decoder that reverses it. Define and test
   behavior for characters above `0xFF` (wider hex or explicit rejection) and
   enforce the 254-byte limit.
2. **Validation guardrail** — Add a function that asserts a finished `_key` has no
   `/`, no spaces, only ArangoDB-legal characters, and is within the length limit,
   raising a clear error otherwise; plus a helper that assembles `_id` as
   `collection/_key` only after the key passes validation.
3. **Adopt in the metadata export** — Route the export's table/column keys and
   CONTAINS edges through the shared codec + guardrail. Document whether the export
   should emit the literal `column::dbo.X.Y` convention or the hex `_xHH_`
   convention (the two live collections differ — see constraint note).
4. **Unify the existing sanitizers** — Replace the three lossy ad-hoc sanitizers so
   the whole repo uses the one reversible codec, keeping their call sites working.
5. **Tests + CI wiring** — Add round-trip identity tests, a `/`-always-safe test,
   and known-vector tests (e.g. `Live.dbo.HOLD_REASON` ↔ its encoded form), and
   add them to the post-merge test suite.

## Architectural constraint to confirm
The private repo shows **two** live key conventions: a literal one
(`columns/column::dbo.INVENTORY_BALANCE.POSTING_DATE`, keeping `::` and `.`) and a
hex-encoded one (`manufacturing_graph_node/table_x5F_Live_x2E_dbo_x2E_HOLD_x5F_REASON`).
The executor must confirm which convention each output should target before
finalizing, because it determines whether `.`/`:` are kept literal or hex-encoded.
The `/` prohibition and reversibility requirement apply to both.

## Relevant files
- `replit_integrations/export_graph_metadata.py`
- `arangodb_persistence.py:161-164`
- `normalize_nodes_with_schema.py:50-67`
- `scripts/utils/graph_naming_adapters.py`
- `scripts/verify_metadata_meaning.py:295-310`
- `hf-space-inventory-sqlgen/arangodb_helpers/manufacturing_graph_version_0_0_1.py:66-100`
