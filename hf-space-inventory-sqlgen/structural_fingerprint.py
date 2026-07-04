"""Structural fingerprints for SME-approved SQL snippets.

A snippet's *structural fingerprint* is the **set of base tables it touches** —
deliberately style-agnostic. Two snippets that read the same base tables are
structurally equivalent even if they rename/reorder CTEs, reorder joins, or
change windowing / bucketing logic. This is the governance gate that lets an SME
rewrite an approved snippet freely, while the Solder Engine still refuses SQL
that reaches into a different set of base tables.

The extraction is a single source of truth (SQLGlot, SQLite dialect, CTE names
excluded) so runtime validation and manifest backfill can never disagree:
``solder_engine._extract_tables_from_sql`` delegates to ``raw_base_tables`` here.

The engine NEVER generates, infers, or mutates SQL — this module only *reads*
and *compares* the SQL an SME already approved.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import sqlglot
from sqlglot import exp

# The dialect the synthetic ground truth is authored in. Fingerprints are always
# extracted in this dialect so extraction is deterministic and reproducible.
FINGERPRINT_DIALECT = "sqlite"

# Stable identifier for the extraction method, stored on each manifest entry so
# an SME can see exactly how the fingerprint was derived.
EXTRACTOR_ID = "sqlglot-sqlite-base-tables-v1"


class FingerprintParseError(ValueError):
    """Raised when SQLGlot cannot parse a snippet, so no fingerprint can be
    established. Callers treat this as a fail-closed condition (condition 4)."""


def raw_base_tables(sql_text: str) -> List[str]:
    """Real base-table names referenced in ``sql_text`` (with duplicates).

    CTE alias names are excluded: SQLGlot surfaces them as ``exp.Table`` nodes in
    the outer SELECT's FROM clause, but they are virtual tables defined within the
    same statement, not schema objects. Names are lowercased so comparison is
    case-insensitive. Parse errors are swallowed here (return best-effort) — the
    strict, fail-closed variant is :func:`base_table_set` with ``strict=True``.
    """
    tables: List[str] = []
    try:
        statements = sqlglot.parse(sql_text, dialect=FINGERPRINT_DIALECT)
    except Exception:
        return tables
    for stmt in statements:
        if stmt is None:
            continue
        cte_names = {
            cte.alias.lower() for cte in stmt.find_all(exp.CTE) if cte.alias
        }
        for node in stmt.find_all(exp.Table):
            name = node.name
            if name and name.lower() not in cte_names:
                tables.append(name.lower())
    return tables


def base_table_set(sql_text: str, strict: bool = False) -> List[str]:
    """The fingerprint: the sorted, de-duplicated set of base tables.

    With ``strict=True`` a SQLGlot parse failure raises
    :class:`FingerprintParseError` instead of degrading to an empty list — used
    by the runtime validator so an unparseable snippet fails closed rather than
    silently fingerprinting as "touches no tables".
    """
    if strict:
        try:
            sqlglot.parse(sql_text, dialect=FINGERPRINT_DIALECT)
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed error
            raise FingerprintParseError(str(exc)) from exc
    return sorted(set(raw_base_tables(sql_text)))


def validate_fingerprint(
    sql_text: str, approved_base_tables: Optional[List[str]]
) -> Tuple[bool, Optional[str]]:
    """Validate a snippet's *structure* (base-table set) against its approved
    fingerprint. Style — CTE names, join order, windowing/bucketing — is ignored.

    Returns ``(ok, reason)``. ``reason`` is None on success, else a human-readable
    string naming why validation failed (fail-closed condition 4):
      * SQLGlot cannot parse the snippet, OR
      * the current base-table set differs from the approved fingerprint.

    A missing/empty approved fingerprint is NOT a fingerprint failure here — the
    caller decides whether an un-fingerprinted binding may serve (with a warning).
    Parse failure always fails closed: without a parse we cannot establish the
    structure at all.
    """
    try:
        current = base_table_set(sql_text, strict=True)
    except FingerprintParseError as exc:
        return False, f"SQLGlot could not parse the snippet: {exc}"

    if not approved_base_tables:
        return True, None

    approved = sorted(set(t.lower() for t in approved_base_tables))
    if current != approved:
        missing = [t for t in approved if t not in current]
        extra = [t for t in current if t not in approved]
        parts = []
        if extra:
            parts.append(f"unexpected base table(s): {', '.join(extra)}")
        if missing:
            parts.append(f"missing base table(s): {', '.join(missing)}")
        detail = "; ".join(parts) if parts else "base-table set differs"
        return (
            False,
            f"structural fingerprint mismatch ({detail}); "
            f"approved={approved}, actual={current}",
        )
    return True, None
