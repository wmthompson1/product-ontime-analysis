#!/usr/bin/env python3
"""
SQLGlot lift for Ontop-generated SQL on the SQLite backend.
===========================================================

Ontop treats SQLite as a limited dialect. When a SPARQL query uses a
*multi-triple* ``OPTIONAL`` (a nested LEFT JOIN) — especially combined with
``GROUP BY`` and an aggregate — Ontop serializes it as SQL with *stacked* ``ON``
clauses, e.g.::

    A LEFT OUTER JOIN B JOIN C ON <inner> ON <outer>

The SQLite parser rejects that with ``near "ON": syntax error``. The fix is
purely about *associativity*: the inner ``B JOIN C`` must be parenthesized into a
group before being LEFT-joined to ``A``::

    A LEFT OUTER JOIN (B JOIN C ON <inner>) ON <outer>

This is semantically required (flattening the joins would change LEFT JOIN
semantics), and SQLite accepts the parenthesized join group while still exposing
the inner aliases to the outer query.

This module captures Ontop's generated SQL (from its DEBUG log) and re-transpiles
it with SQLGlot — which the POC stack already uses. The two functions are pure
and have no I/O, so they can be unit-tested and reused (e.g. by a future live
SPARQL endpoint) without the Ontop toolchain.
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

# Ontop logs the SQL it will execute on this line (at DEBUG level), e.g.
#   12:34:56.789 ... - Resulting native query:
# followed by the SQL on subsequent lines, up to the next timestamped log line.
_NATIVE_MARKER = "Resulting native query:"
_TIMESTAMP_RE = re.compile(r"^\d\d:\d\d:\d\d\.\d{3}\b")

# How SQLite reports the constructs Ontop emits for the unsupported shapes.
_RAW_FAILURE_RE = re.compile(r'SQLiteException|near "[^"]*": syntax error', re.IGNORECASE)


def extract_native_sql(log_text: str) -> str:
    """Return the native SQL Ontop logged for the (last) reformulated query.

    Fails closed: raises ``ValueError`` if the marker is absent or no SELECT
    follows it, so a caller never silently proceeds on a missing capture.
    """
    lines = log_text.splitlines()
    marker_idxs = [i for i, ln in enumerate(lines) if _NATIVE_MARKER in ln]
    if not marker_idxs:
        raise ValueError(f"no {_NATIVE_MARKER!r} marker found in the Ontop log")
    # Use the last occurrence: it is the final reformulated query.
    start = marker_idxs[-1] + 1
    block: list[str] = []
    for ln in lines[start:]:
        if _TIMESTAMP_RE.match(ln):
            break
        block.append(ln)
    select_idx = next(
        (i for i, ln in enumerate(block) if ln.strip().upper().startswith("SELECT")),
        None,
    )
    if select_idx is None:
        raise ValueError("no SELECT statement found after the native-query marker")
    sql = "\n".join(block[select_idx:]).strip()
    if not sql:
        raise ValueError("the captured native SQL block was empty")
    return sql


def lift_join_groups(sql: str) -> tuple[str, int]:
    """Parenthesize nested join groups so SQLite accepts Ontop's stacked-ON SQL.

    SQLGlot parses ``A LEFT JOIN B JOIN C ON inner ON outer`` as a single join
    whose ``this`` is a table (``B``) that itself carries the inner join to
    ``C`` — and the generator renders that flat (the broken stacked-``ON`` form).
    Wrapping that ``this`` in a :class:`sqlglot.exp.Subquery` makes the generator
    emit ``LEFT JOIN (B JOIN C ON inner) ON outer``.

    Returns ``(lifted_sql, num_groups_wrapped)``. The transform is a no-op
    (0 wrapped) when no join carries a nested join, so it is safe to run on any
    Ontop SQL.
    """
    tree = sqlglot.parse_one(sql, read="sqlite")
    wrapped = 0
    for join in tree.find_all(exp.Join):
        target = join.this
        if isinstance(target, (exp.Table, exp.Subquery)) and target.args.get("joins"):
            join.set("this", exp.Subquery(this=target.copy()))
            wrapped += 1
    return tree.sql(dialect="sqlite"), wrapped


def raw_sql_rejected_by_sqlite(log_text: str) -> bool:
    """True if the Ontop log shows SQLite rejected the generated SQL (so the lift
    is actually needed for this query)."""
    return bool(_RAW_FAILURE_RE.search(log_text))
