"""
ontop_ontology_selector.py
--------------------------
Master-detail selector entries for browsing the Ontop OBDA mappings — the
virtual OWL/SPARQL republication of the governed SQL layer.

Mirrors ground_truth_selector.py: every OBDA mapping in
poc/ontop-ontology-poc/mapping/*.obda is rendered as a SAME-LENGTH label
built from the same simplified 6-slot scheme:

    MOD:MAPPING_ID        :CLASS         :DxL:BASE_TABLE  +N:T
     0        1                  2         3       4        5

    slot 0  module (showcase), 3-char abbreviation (SHO, INV, CUS, CAP ...)
    slot 1  mappingId (leading 'map-' stripped), fixed width, '…' truncated
    slot 2  minted subject class from the target triples, fixed width
    slot 3  triple mix: <n>D<m> = n datatype facts, m object links minted
    slot 4  first base table of the SOURCE SQL + '+N' extras
    slot 5  time-phasing of the source SQL: '⏱' / '·' / '?' (same marks)

The SOURCE SQL of each mapping is exactly "what the solder sees" — the
governed SQL that Ontop rewrites SPARQL onto. Ontology term annotations
(rdfs:label / rdfs:comment) are read from the matching ontology/*.ttl.

Pure metadata — nothing here executes SQL against a database.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

from ground_truth_selector import (
    _abbrev3,
    _fit,
    _tables_slot,
    _time_slot,
    W_CONCEPT,
    W_PERSPECTIVE,
    TIME_PHASED_MARK,
    POINT_IN_TIME_MARK,
    UNKNOWN_MARK,
)

# Default POC location, relative to this file (repo_root/poc/ontop-ontology-poc)
DEFAULT_POC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "poc", "ontop-ontology-poc")
)


# ── .obda parsing ────────────────────────────────────────────────────────────

def parse_obda(path: str) -> List[dict]:
    """Parse one .obda file into [{mapping_id, target, source}] (order kept).

    The Ontop .obda text format is line-based: 'mappingId', 'target' and
    'source' keywords each start a field; 'source' SQL may span lines until
    the next 'mappingId' or the closing ']]'.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    mappings: List[dict] = []
    current: Optional[dict] = None
    field: Optional[str] = None

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("mappingId"):
            if current:
                mappings.append(current)
            current = {
                "mapping_id": line[len("mappingId"):].strip(),
                "target": "",
                "source": "",
            }
            field = None
        elif line.startswith("target") and current is not None:
            current["target"] = line[len("target"):].strip()
            field = "target"
        elif line.startswith("source") and current is not None:
            current["source"] = line[len("source"):].strip()
            field = "source"
        elif line == "]]":
            break
        elif current is not None and field and line:
            current[field] += " " + line
    if current:
        mappings.append(current)
    return mappings


def _target_terms(target: str) -> Tuple[str, List[str], List[str]]:
    """(subject_class, datatype_property_terms, object_property_terms).

    The subject class is the object of the `a :Class` triple. Fact-only
    mappings (no class mint) fall back to the subject IRI template name in
    parentheses, e.g. `(delivery)`. A predicate is an object link when its
    object is an IRI template (`:x/{...}`), otherwise it is a datatype fact
    (`{col}^^xsd:type`).
    """
    subject_class = ""
    m = re.search(r"\ba\s+:(\w+)", target)
    if m:
        subject_class = m.group(1)
    else:
        subj_m = re.match(r"\s*:(\w+)/", target)
        if subj_m:
            subject_class = f"({subj_m.group(1)})"

    datatype_terms: List[str] = []
    object_terms: List[str] = []
    # predicate-object pairs: `:pred {col}^^xsd:t` or `:pred :iri/{col}`
    for pred, obj in re.findall(r":(\w+)\s+(\{[^}]+\}\^\^\S+|:\S+/\{[^}]+\})", target):
        if obj.startswith(":"):
            object_terms.append(pred)
        else:
            datatype_terms.append(pred)
    return subject_class, datatype_terms, object_terms


# ── .ttl parsing (annotations only) ──────────────────────────────────────────

def parse_ttl_annotations(path: str) -> dict:
    """Extract rdfs:label / rdfs:comment per term, plus the ontology header.

    Lightweight regex reader for the POC's consistently formatted OWL 2 QL
    files — not a general Turtle parser.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Drop Turtle comment lines so a leading '# …' banner never hides the
    # subject at the start of a block.
    text = "\n".join(
        ln for ln in raw_text.splitlines() if not ln.lstrip().startswith("#")
    )

    result = {"ontology_label": "", "ontology_comment": "", "terms": {}}

    # Split on statement-terminating '.' at end of line
    for block in re.split(r"\.\s*\n", text):
        block = block.strip()
        subj_m = re.match(r"\s*(<[^>]+>|:\w+)\s", block)
        if not subj_m:
            continue
        subject = subj_m.group(1)
        label_m = re.search(r'rdfs:label\s+"((?:[^"\\]|\\.)*)"', block)
        comment_m = re.search(r'rdfs:comment\s+"((?:[^"\\]|\\.)*)"', block)
        kind_m = re.search(r"\ba\s+owl:(\w+)", block)
        info = {
            "kind": kind_m.group(1) if kind_m else "",
            "label": label_m.group(1) if label_m else "",
            "comment": comment_m.group(1) if comment_m else "",
        }
        if subject.startswith("<"):
            if info["kind"] == "Ontology":
                result["ontology_label"] = info["label"]
                result["ontology_comment"] = info["comment"]
        else:
            result["terms"][subject.lstrip(":")] = info
    return result


# ── selector entries ─────────────────────────────────────────────────────────

def _module_title(module: str) -> str:
    return module.replace("_", " ").title()


def _mix_slot(n_datatype: int, n_object: int) -> str:
    """3-char triple-mix slot: <n>D<m>, capped at 9."""
    return f"{min(n_datatype, 9)}D{min(n_object, 9)}"


def slot_label(entry: dict) -> str:
    """Fixed-width 6-slot label for one Ontop mapping entry."""
    return ":".join(
        [
            _abbrev3(entry.get("module", "")),
            _fit(entry.get("mapping_short", ""), W_CONCEPT),
            _fit(entry.get("subject_class", ""), W_PERSPECTIVE),
            _mix_slot(len(entry.get("datatype_terms") or []), len(entry.get("object_terms") or [])),
            _tables_slot(entry.get("base_tables") or []),
            _time_slot(entry.get("time_phased")),
        ]
    )


def slot_legend() -> str:
    """One-line legend describing the 6 slots, for display above the selector."""
    return (
        "`MOD : MAPPING : CLASS : DxL : TABLES+N : TIME`  —  "
        "`DxL`: datatype facts × object links minted · time slot: "
        f"`{TIME_PHASED_MARK}` time-phased · `{POINT_IN_TIME_MARK}` "
        f"point-in-time · `{UNKNOWN_MARK}` not extracted"
    )


def load_ontop_entries(poc_dir: str = DEFAULT_POC_DIR) -> List[dict]:
    """Load every OBDA mapping across all showcase modules as selector entries.

    Each entry carries: entry_key (module/mapping_id), module, mapping_id,
    mapping_short, subject_class, datatype_terms, object_terms, target,
    source_sql, base_tables (parsed from the source SQL by SQLGlot),
    time_phased (from the same pure-AST extraction; None on failure), and
    the ontology annotations (ontology_label/comment + per-term dict).
    """
    mapping_dir = os.path.join(poc_dir, "mapping")
    ontology_dir = os.path.join(poc_dir, "ontology")
    if not os.path.isdir(mapping_dir):
        return []

    entries: List[dict] = []
    for fname in sorted(os.listdir(mapping_dir)):
        if not fname.endswith(".obda"):
            continue
        module = fname[: -len(".obda")]
        obda_path = os.path.join(mapping_dir, fname)
        ttl_path = os.path.join(ontology_dir, module + ".ttl")
        try:
            mappings = parse_obda(obda_path)
        except Exception:
            continue
        annotations: dict = {"ontology_label": "", "ontology_comment": "", "terms": {}}
        if os.path.exists(ttl_path):
            try:
                annotations = parse_ttl_annotations(ttl_path)
            except Exception:
                pass

        for m in mappings:
            subject_class, dt_terms, ob_terms = _target_terms(m["target"])
            base_tables, time_phased = _source_sql_shape(m["source"])
            mapping_short = re.sub(r"^map-", "", m["mapping_id"])
            entries.append(
                {
                    "entry_key": f"{module}/{m['mapping_id']}",
                    "module": module,
                    "module_title": _module_title(module),
                    "mapping_id": m["mapping_id"],
                    "mapping_short": mapping_short,
                    "subject_class": subject_class,
                    "datatype_terms": dt_terms,
                    "object_terms": ob_terms,
                    "target": m["target"],
                    "source_sql": m["source"],
                    "base_tables": base_tables,
                    "time_phased": time_phased,
                    "ontology_label": annotations["ontology_label"],
                    "ontology_comment": annotations["ontology_comment"],
                    "terms": annotations["terms"],
                }
            )

    entries.sort(key=lambda e: (e["module"], e["mapping_id"]))
    return entries


def _source_sql_shape(source_sql: str) -> Tuple[List[str], Optional[bool]]:
    """(base_tables, time_phased) for a mapping's source SQL, via pure AST."""
    try:
        from view_ontology_extractor import extract_view_ontology

        vo = extract_view_ontology(source_sql, "ontop", "ONTOP", "obda")
        return list(vo.physical_tables), bool(vo.time_phased)
    except Exception:
        return _fallback_tables(source_sql), None


def _fallback_tables(source_sql: str) -> List[str]:
    """Regex fallback for base tables when AST extraction is unavailable."""
    found: List[str] = []
    for kw, name in re.findall(r"\b(FROM|JOIN)\s+([A-Za-z_][\w]*)", source_sql, re.IGNORECASE):
        if name.lower() not in (t.lower() for t in found):
            found.append(name)
    return found


def selector_choices(entries: List[dict]) -> List[Tuple[str, str]]:
    """(label, entry_key) pairs for a Gradio Dropdown master selector."""
    return [(slot_label(e), e["entry_key"]) for e in entries]


# ── category level (showcase ontology) ───────────────────────────────────────

def module_choices(entries: List[dict]) -> List[Tuple[str, str]]:
    """(display, module) per showcase ontology — the concrete category level.

    Display is the plain module title plus its mapping count, e.g.
    ``Customer Order  (4)`` — nothing abstract, exactly one choice per
    .obda showcase file.
    """
    out: List[Tuple[str, str]] = []
    for module in sorted({e["module"] for e in entries}):
        pool = [e for e in entries if e["module"] == module]
        out.append((f"{pool[0]['module_title']}  ({len(pool)})", module))
    return out


def selector_choices_for_module(
    entries: List[dict], module: Optional[str]
) -> List[Tuple[str, str]]:
    """Selector choices narrowed to one showcase module (None = all)."""
    if module is None:
        return selector_choices(entries)
    return selector_choices([e for e in entries if e["module"] == module])


# ── binding-key bridge (governed, explicit) ──────────────────────────────────

BRIDGE_FILENAME = "binding_bridge.json"


def load_binding_bridge(poc_dir: str = DEFAULT_POC_DIR) -> Dict[str, List[str]]:
    """Load the governed binding_key -> [showcase module] bridge.

    The bridge is a committed POC artifact (binding_bridge.json) linking
    reviewer-manifest binding keys to the showcase ontology modules that
    republish their governed story. EXPLICIT ONLY — no SQL-similarity
    inference: a missing/invalid file or an absent key means "unbound",
    which callers must surface visibly.
    """
    path = os.path.join(poc_dir, BRIDGE_FILENAME)
    if not os.path.exists(path):
        return {}
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("bindings") or {}
        out: Dict[str, List[str]] = {}
        for bk, modules in raw.items():
            if isinstance(modules, list):
                mods = [m for m in modules if isinstance(m, str) and m]
                if mods:
                    out[bk] = mods
        return out
    except Exception:
        return {}


def load_query_bindings(poc_dir: str = DEFAULT_POC_DIR) -> Dict[str, List[str]]:
    """Load the governed query-name -> [binding_key] section of the bridge.

    Supplies the query->key hop ONLY for governed palette queries that carry
    no '-- Binding:' marker (a marker, when present, always wins upstream).
    Same fail-closed contract as load_binding_bridge: missing/invalid file
    or absent query name means "unbound".
    """
    path = os.path.join(poc_dir, BRIDGE_FILENAME)
    if not os.path.exists(path):
        return {}
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("query_bindings") or {}
        out: Dict[str, List[str]] = {}
        for name, keys in raw.items():
            if isinstance(keys, list):
                bks = [k for k in keys if isinstance(k, str) and k]
                if bks:
                    out[name] = bks
        return out
    except Exception:
        return {}


def entries_for_binding(
    entries: List[dict],
    bridge: Dict[str, List[str]],
    binding_key: Optional[str],
) -> List[dict]:
    """All OBDA mapping entries bridged to one binding key (order kept).

    Returns [] when the key is unbound — the caller renders that as an
    explicit "no ontology mapping bound" message, never a fallback.
    """
    modules = bridge.get(binding_key or "") or []
    return [e for e in entries if e["module"] in modules]
