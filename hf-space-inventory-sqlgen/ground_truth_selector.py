"""
ground_truth_selector.py
------------------------
Reusable master-detail selector element for browsing ground-truth queries.

Every approved snippet in the reviewer manifest is rendered as a SAME-LENGTH
label built from a simplified 6-slot scheme (an echo of the graph's fixed
6-slot composite key convention):

    PER:CONCEPT_ANCHOR      :PERSPECTIVE   :LOG:BASE_TABLE  +N:T
     0        1                   2          3       4        5

    slot 0  perspective, 3-char abbreviation (INV, QUA, OPE, PAY ...) — a
            fast-scan grouping prefix for slot 2 (category and perspective
            are the same axis; only the perspective is used)
    slot 1  concept_anchor, fixed width, '…' when truncated
    slot 2  perspective, fixed width, '…' when truncated
    slot 3  logic_type, 3-char abbreviation (DIR, AGG ...)
    slot 4  first base table from the structural fingerprint + '+N' extras
    slot 5  time-phasing marker: '⏱' time-phased · '·' point-in-time · '?' unknown

Because the width of each slot is fixed, every label has an identical length,
so a monospace dropdown reads as an aligned master table for SMEs.

Cascading selector (Ontology Mosaic)
------------------------------------
`SelectorCascade` wraps the flat entry list in a reusable cascading component:

    Category  →  Concept anchor  →  Query / perspective

* **Category** comes from the reviewer manifest's `category` field. Raw labels
  are normalized for DISPLAY ONLY (near-duplicates such as `Quality` and
  `quality_control` merge under one clean label) — the manifest itself is
  never edited.
* **Concept anchor** shows the concept + table-list style
  (e.g. ``SAFETYSTOCK  [part, customer_order_line, …]``).
* **Query** keeps the fixed-width 6-slot summary labels for orientation, and
  resolves to a single manifest `binding_key`. When an anchor has exactly one
  query the cascade auto-resolves it.

Extension seam (read this before adding a filter or a second consumer)
----------------------------------------------------------------------
The cascade is built from an ordered list of `CascadeFilter` objects — the
Category cascade is just **filter #1**. Each filter declares:

    name          stable identifier (also the key in the selections dict)
    choices(entries)             -> [(display_label, value), ...]
    apply(entries, value)        -> the surviving subset of entries

To add a future filter (say, time-phasing), append one more `CascadeFilter`
to `default_filters()` (or pass a custom list to `SelectorCascade`) — the
resolution pipeline `narrow() → anchor_choices() → query_choices() →
resolve()` applies every filter in order with **no tab-side rewiring**: the
tabs only ever consume the cascade's choice lists and the resolved
`binding_key`.

A second consumer (e.g. a metrics ontology mosaic) reuses the component by
constructing `SelectorCascade(entries, filters=...)` over its OWN entry list
— any list of dicts carrying `category`, `concept_anchor`, `base_tables`,
and `binding_key` works; nothing in the cascade is specific to ground-truth
SQL snippets.

If NO entry carries a category, `has_categories()` is False and callers fall
back to the flat 6-slot selector (`selector_choices`) unchanged.

Pure metadata — nothing here executes SQL against a database.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

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
            _abbrev3(entry.get("perspective", "")),
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
        "`PER : CONCEPT : PERSPECTIVE : LOGIC : TABLES+N : TIME`  —  "
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

    entries.sort(key=lambda e: (e["perspective"], e["concept_anchor"]))
    return entries


def selector_choices(entries: List[dict]) -> List[Tuple[str, str]]:
    """(label, binding_key) pairs for a Gradio Dropdown master selector."""
    return [(slot_label(e), e["binding_key"]) for e in entries]


# ---------------------------------------------------------------------------
# Cascading selector component (Ontology Mosaic)
# ---------------------------------------------------------------------------

# Display-only normalization of near-duplicate raw category labels.
# Keys are the CANONICAL category key; values are the raw variants that fold
# into it. The manifest is never edited — this only shapes the dropdown.
_CATEGORY_ALIASES = {
    "quality_control": {"quality", "quality_control"},
}

_ANCHOR_TABLES_SHOWN = 3  # tables displayed in an anchor label before "…"


def normalize_category(raw: str) -> str:
    """Canonical category KEY for a raw manifest label ('' stays '')."""
    key = "_".join(
        part for part in "".join(
            c.lower() if c.isalnum() else " " for c in (raw or "")
        ).split()
    )
    for canonical, variants in _CATEGORY_ALIASES.items():
        if key in variants:
            return canonical
    return key


def category_label(key: str) -> str:
    """Human display label for a canonical category key."""
    if not key:
        return "(uncategorized)"
    return " ".join(w.capitalize() for w in key.split("_"))


def has_categories(entries: List[dict]) -> bool:
    """True when at least one entry carries a non-empty category."""
    return any((e.get("category") or "").strip() for e in entries)


def anchor_label(anchor: str, entries: List[dict]) -> str:
    """Concept + table-list label, e.g. ``SAFETYSTOCK  [part, work_order, …]``."""
    tables: List[str] = []
    seen: set = set()
    for e in entries:
        if e.get("concept_anchor") != anchor:
            continue
        for t in e.get("base_tables") or []:
            if t not in seen:
                seen.add(t)
                tables.append(t)
    if not tables:
        return f"{anchor}  [—]"
    shown = tables[:_ANCHOR_TABLES_SHOWN]
    ell = ", …" if len(tables) > len(shown) else ""
    return f"{anchor}  [{', '.join(shown)}{ell}]"


@dataclass
class CascadeFilter:
    """One filter stage in the cascade. See the module docstring's
    "Extension seam" section: append a new CascadeFilter to add a filter —
    the tabs need no rewiring."""
    name: str
    choices: Callable[[List[dict]], List[Tuple[str, str]]]
    apply: Callable[[List[dict], Optional[str]], List[dict]]


def _category_choices(entries: List[dict]) -> List[Tuple[str, str]]:
    keys: List[str] = []
    seen: set = set()
    for e in entries:
        k = normalize_category(e.get("category") or "")
        if k not in seen:
            seen.add(k)
            keys.append(k)
    keys.sort(key=lambda k: (k == "", category_label(k)))
    return [(category_label(k), k) for k in keys]


def _category_apply(entries: List[dict], value: Optional[str]) -> List[dict]:
    if value is None:
        return list(entries)
    return [
        e for e in entries
        if normalize_category(e.get("category") or "") == value
    ]


def category_filter() -> CascadeFilter:
    """Filter #1: the Category cascade (normalized, display-only)."""
    return CascadeFilter(
        name="category",
        choices=_category_choices,
        apply=_category_apply,
    )


def default_filters() -> List[CascadeFilter]:
    """The shipped filter chain. Future filters append here (see docstring)."""
    return [category_filter()]


@dataclass
class Selection:
    """Resolved cascade state the tabs consume."""
    filters: dict = field(default_factory=dict)   # filter name -> chosen value
    anchor: Optional[str] = None
    binding_key: Optional[str] = None
    auto_resolved: bool = False                   # single-match auto-selection


class SelectorCascade:
    """Reusable Category → Concept anchor → Query cascade over selector
    entries. State-free per call: every method takes the current selections
    and returns fresh choice lists, so any UI (or a second consumer such as a
    metrics mosaic) can drive it."""

    def __init__(self, entries: List[dict], filters: Optional[List[CascadeFilter]] = None):
        self.entries = list(entries)
        self.filters = filters if filters is not None else default_filters()

    def filter_choices(self, name: str, selections: Optional[dict] = None) -> List[Tuple[str, str]]:
        """Choices for one filter, narrowed by every EARLIER filter's pick."""
        pool = self.entries
        for f in self.filters:
            if f.name == name:
                return f.choices(pool)
            pool = f.apply(pool, (selections or {}).get(f.name))
        raise KeyError(f"unknown cascade filter: {name}")

    def narrow(self, selections: Optional[dict] = None) -> List[dict]:
        """Entries surviving every filter in order."""
        pool = self.entries
        for f in self.filters:
            pool = f.apply(pool, (selections or {}).get(f.name))
        return pool

    def anchor_choices(self, selections: Optional[dict] = None) -> List[Tuple[str, str]]:
        pool = self.narrow(selections)
        anchors: List[str] = []
        seen: set = set()
        for e in pool:
            a = e.get("concept_anchor") or ""
            if a and a not in seen:
                seen.add(a)
                anchors.append(a)
        anchors.sort()
        return [(anchor_label(a, pool), a) for a in anchors]

    def query_choices(
        self, selections: Optional[dict] = None, anchor: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        pool = self.narrow(selections)
        if anchor:
            pool = [e for e in pool if e.get("concept_anchor") == anchor]
        return [(slot_label(e), e["binding_key"]) for e in pool]

    def resolve(
        self,
        selections: Optional[dict] = None,
        anchor: Optional[str] = None,
        binding_key: Optional[str] = None,
    ) -> Selection:
        """Resolve the current picks to a Selection. A single surviving query
        auto-resolves; an explicit binding_key wins when still valid."""
        sel = Selection(filters=dict(selections or {}), anchor=anchor)
        choices = self.query_choices(selections, anchor)
        valid = {bk for _, bk in choices}
        if binding_key and binding_key in valid:
            sel.binding_key = binding_key
        elif len(choices) == 1:
            sel.binding_key = choices[0][1]
            sel.auto_resolved = True
        return sel
