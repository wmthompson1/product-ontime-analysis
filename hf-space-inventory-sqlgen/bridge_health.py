"""
bridge_health.py
================
Standalone helper for the Bridge Health panel.

Extracted from app.py so that the logic can be unit-tested without importing
the full FastAPI + Gradio application stack.
"""

from __future__ import annotations

import os

BRIDGE_HEALTH_MAP: dict[str, str] = {
    "Perspective_Intents": "schema_intent_perspectives",
    "Perspective_Concepts": "schema_perspective_concepts",
}


def run_bridge_health_check_impl(
    sqlite_db_path: str,
    bridge_map: dict,
    *,
    _os_path_exists=None,
    _sqlite_connect=None,
    _arango_env_getter=None,
    _arango_factory=None,
) -> tuple[str, str, str]:
    """Core logic for the Bridge Health panel.

    Parameters
    ----------
    sqlite_db_path:
        Filesystem path to the SQLite database.
    bridge_map:
        Mapping of ``{arango_collection_name: sqlite_table_name}``.
    _os_path_exists:
        Injection seam — replaces ``os.path.exists`` in tests.
    _sqlite_connect:
        Injection seam — replaces ``sqlite3.connect`` in tests.
    _arango_env_getter:
        Injection seam — replaces ``os.environ.get`` for the ARANGO_HOST
        lookup in tests.
    _arango_factory:
        Injection seam — callable that returns a mock ArangoDB ``db`` object
        in tests. When *None* (production), the real ``graph_sync`` helpers
        are used.

    Returns
    -------
    tuple[str, str, str]
        ``(overall_status, timestamp, detail_text)``
    """
    import sqlite3 as _sqlite3
    import datetime as _dt

    _exists = _os_path_exists if _os_path_exists is not None else os.path.exists
    _connect = _sqlite_connect if _sqlite_connect is not None else _sqlite3.connect
    _env_get = _arango_env_getter if _arango_env_getter is not None else (
        lambda key: os.environ.get(key)
    )

    timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not _exists(sqlite_db_path):
        return (
            "⚠️  SKIP — SQLite DB not found",
            timestamp,
            f"SQLite DB not found at: {sqlite_db_path}",
        )

    sqlite_counts: dict = {}
    conn = _connect(sqlite_db_path)
    try:
        for sqlite_table in bridge_map.values():
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {sqlite_table}"
                ).fetchone()
                sqlite_counts[sqlite_table] = row[0] if row else 0
            except Exception as exc:
                sqlite_counts[sqlite_table] = f"ERROR: {exc}"
    finally:
        conn.close()

    if not _env_get("ARANGO_HOST"):
        lines = ["ArangoDB: NOT CONFIGURED (ARANGO_HOST not set)", ""]
        lines.append(
            f"{'Collection':<28} {'ArangoDB':>12} {'SQLite':>12} {'Match':>8}"
        )
        lines.append("-" * 64)
        for arango_coll, sqlite_table in bridge_map.items():
            sqlite_n = sqlite_counts.get(sqlite_table, "?")
            lines.append(
                f"{arango_coll:<28} {'N/A':>12} {str(sqlite_n):>12} {'—':>8}"
            )
        lines.append("")
        lines.append("Set ARANGO_HOST to enable the ArangoDB side of this check.")
        return (
            "⚠️  SKIP — ARANGO_HOST not set",
            timestamp,
            "\n".join(lines),
        )

    if _arango_factory is not None:
        try:
            db = _arango_factory()
        except Exception as exc:
            return (
                f"⚠️  SKIP — ArangoDB connection failed: {exc}",
                timestamp,
                f"Could not connect to ArangoDB:\n{exc}",
            )
    else:
        try:
            from graph_sync import get_arango_client, get_arango_db
            client = get_arango_client()
            db = get_arango_db(client)
        except Exception as exc:
            return (
                f"⚠️  SKIP — ArangoDB connection failed: {exc}",
                timestamp,
                f"Could not connect to ArangoDB:\n{exc}",
            )

    arango_counts: dict = {}
    for coll_name in bridge_map:
        try:
            if db.has_collection(coll_name):
                arango_counts[coll_name] = db.collection(coll_name).count()
            else:
                arango_counts[coll_name] = -1
        except Exception as exc:
            arango_counts[coll_name] = f"ERROR: {exc}"

    lines = []
    lines.append(
        f"{'Collection':<28} {'ArangoDB':>12} {'SQLite':>12} {'Match':>8}"
    )
    lines.append("-" * 64)

    all_ok = True
    for arango_coll, sqlite_table in bridge_map.items():
        arango_n = arango_counts.get(arango_coll)
        sqlite_n = sqlite_counts.get(sqlite_table, "?")

        if isinstance(arango_n, str):
            match_icon = "ERROR"
            all_ok = False
        elif arango_n == -1:
            match_icon = "MISSING"
            all_ok = False
        elif arango_n == sqlite_n:
            match_icon = "✅"
        else:
            match_icon = "❌"
            all_ok = False

        arango_display = "MISSING" if arango_n == -1 else str(arango_n)
        lines.append(
            f"{arango_coll:<28} {arango_display:>12} {str(sqlite_n):>12} {match_icon:>8}"
        )

    lines.append("")
    if all_ok:
        lines.append("All bridge collection counts match the SQLite source data.")
        overall = "✅  IN SYNC — all counts match"
    else:
        lines.append(
            "Count mismatch detected. Re-run 'Sync to ArangoDB' on the Graph Sync tab."
        )
        overall = "❌  OUT OF SYNC — counts differ (see details below)"

    return overall, timestamp, "\n".join(lines)
