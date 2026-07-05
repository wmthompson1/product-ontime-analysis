"""
ground_truth_selector.py
------------------------
Reusable master-detail selector element for browsing ground-truth queries.

Every approved snippet in the reviewer manifest is rendered as a SAME-LENGTH
label built from a simplified 6-slot scheme (an echo of the graph's fixed
6-slot composite key convention):

    CAT:CONCEPT_ANCHOR      :PERSPECTIVE   :LOG:BASE_TABLE  +N:T
     0        1                   2          3       4        5

    slot 0  category, 3-char abbreviation (INV, QUA, OPE, FIN, CUS ...)
    slot 1  concept_anchor, fixed width, '…' when truncated
    slot 2  perspective, fixed width, '…' when truncated
    slot 3  logic_type, 3-char abbreviation (DIR, AGG ...)
    slot 4  first base table from the structural fingerprint + '+N' extras
    slot 5  time-phasing marker: '⏱' time-phased · '·' point-in-time · '?' unknown

Because the width of each slot is fixed, every label has an identical length,
so a monospace dropdown reads as an aligned master table for SMEs.

Pure metadata — nothing here executes SQL against a database.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import List, Optional, Tuple

# Fixed slot widths (characters)
W_CATEGORY = 3
W_CONCEPT = 18
W_PERSPECTIVE = 14
W_LOGIC = 3
W_TABLE = 12   # includes the "+N" extras suffix
W_TIME = 1

TIME_PHASED_MARK = "⏱"
POINT_IN_TIME_MARK = "·"
UNKNOWN_MARK = "?"


def _abbrev3(value: str) -> str:
    """First 3 alphanumeric characters, uppercased — same rule as the uid grammar."""
    letters = [c for c in (value or "") if c.isalnum()]
    return "".join(letters[:3]).upper().ljust(3, "_")


def _fit(value: str, width: int) -> str:
    """Pad or truncate to an exact width; truncation is marked with '…'."""
    value = value or ""
    if len(value) > width:
        return value[: width - 1] + "…"
    return value.ljust(width)


def _tables_slot(base_tables: List[str]) -> str:
    """'first_table+N' fitted to W_TABLE; '(none)' when the fingerprint is empty."""
    if not base_tables:
        return _fit("(none)", W_TABLE)
    extras = len(base_tables) - 1
    suffix = f"+{extras}" if extras > 0 else ""
    room = W_TABLE - len(suffix)
    first = base_tables[0]
    if len(first) > room:
        first = first[: room - 1] + "…"
    return (first + suffix).ljust(W_TABLE)


def _time_slot(time_phased: Optional[bool]) -> str:
    if time_phased is None:
        return UNKNOWN_MARK
    return TIME_PHASED_MARK if time_phased else POINT_IN_TIME_MARK


def slot_label(entry: dict) -> str:
    """Build the fixed-width 6-slot label for one selector entry."""
    return ":".join(
        [
            _abbrev3(entry.get("category", "")),
            _fit(entry.get("concept_anchor", ""), W_CONCEPT),
            _fit(entry.get("perspective", ""), W_PERSPECTIVE),
            _abbrev3(entry.get("logic_type", "")),
            _tables_slot(entry.get("base_tables") or []),
            _time_slot(entry.get("time_phased")),
        ]
    )


def slot_legend() -> str:
    """One-line legend describing the 6 slots, for display above the selector."""
    return (
        "`CAT : CONCEPT : PERSPECTIVE : LOGIC : TABLES+N : TIME`  —  "
        f"time slot: `{TIME_PHASED_MARK}` time-phased · `{POINT_IN_TIME_MARK}` "
        f"point-in-time · `{UNKNOWN_MARK}` not yet extracted"
    )


def load_selector_entries(
    manifest_path: str,
    db_path: Optional[str] = None,
) -> List[dict]:
    """Load all APPROVED manifest snippets as selector entries.

    Each entry carries: binding_key, concept_anchor, perspective, category,
    logic_type, base_tables (from the structural fingerprint), file_path,
    sme_justification, and time_phased (looked up from sql_view_ontology when
    a seeded ontology row exists for the binding key; None otherwise).
    """
    if not os.path.exists(manifest_path):
        return []
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        return []

    time_by_binding = {}
    if db_path and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT binding_key, time_phased FROM sql_view_ontology"
                ).fetchall()
                time_by_binding = {bk: bool(tp) for bk, tp in rows}
            finally:
                conn.close()
        except Exception:
            time_by_binding = {}

    entries: List[dict] = []
    for binding_key, snip in manifest.get("approved_snippets", {}).items():
        if snip.get("validation_status") != "APPROVED":
            continue
        fingerprint = snip.get("structural_fingerprint") or {}
        entries.append(
            {
                "binding_key": binding_key,
                "concept_anchor": snip.get("concept_anchor", binding_key.upper()),
                "perspective": snip.get("perspective", ""),
                "category": snip.get("category", ""),
                "logic_type": snip.get("logic_type", ""),
                "base_tables": fingerprint.get("base_tables") or [],
                "file_path": snip.get("file_path", ""),
                "sme_justification": snip.get("sme_justification", ""),
                "time_phased": time_by_binding.get(binding_key),
            }
        )

    entries.sort(
        key=lambda e: (e["category"], e["perspective"], e["concept_anchor"])
    )
    return entries


def selector_choices(entries: List[dict]) -> List[Tuple[str, str]]:
    """(label, binding_key) pairs for a Gradio Dropdown master selector."""
    return [(slot_label(e), e["binding_key"]) for e in entries]
