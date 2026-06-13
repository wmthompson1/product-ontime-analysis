"""masking_helpers.py — shared masking helpers for the raw SQLMesh Python models.

Ported for Plan 8 (Multi-Agent Schema Traversal & Masking Orchestration). The
two raw Python models (``raw_user_def_fields``, ``raw_matrix_driven``) import
their masking primitives from here so there is a single, SME-approved source of
the deterministic transform — never an LLM.

These functions reuse this repo's canonical masking logic in
``hf-space-inventory-sqlgen/masking_matrix.py`` and ``masking_type.py`` (the
CSV<->SQLite mirror of the column-masking DAG). The masking salt stays in the
secret env flow (``GEMIN_SALT``); it is never stored here.

This module lives under ``Utilities/SQLMesh/models/raw`` (a namespace package) so
the two raw models can import it as ``models.raw.masking_helpers``. It puts the
hf-space app dir onto ``sys.path`` so the canonical ``masking_matrix`` /
``masking_type`` modules import cleanly.

It is not a SQLMesh model; ``config.yaml`` lists it under ``ignore_patterns`` so
the loader does not try to treat it as one. Because the two models import these
functions, SQLMesh serializes them (by source) into each model's snapshot and
walks every module-level global they reference — so the globals they touch are
kept serializable (plain strings / modules), never ``Path`` or compiled-regex
objects.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# --- path bootstrap so the canonical masking modules import everywhere --------
# models/raw/masking_helpers.py -> raw -> models -> SQLMesh -> Utilities -> repo
_REPO_ROOT = Path(__file__).resolve().parents[4]
# A plain-string copy: resolve_cert_dir() references this (not the Path) so
# SQLMesh can serialize it when it walks the model functions' globals.
_REPO_ROOT_STR = str(_REPO_ROOT)
_HF_DIR = _REPO_ROOT / "hf-space-inventory-sqlgen"
# Only the hf-space app dir needs to be importable (for masking_matrix /
# masking_type). Deliberately do NOT add the repo root to sys.path: it contains
# an unrelated models.py that would shadow SQLMesh's project-local `models`
# package when the loader imports `models.raw.<name>`.
if str(_HF_DIR) not in sys.path:
    sys.path.insert(0, str(_HF_DIR))

# Canonical, SME-approved masking logic (single source of truth).
import masking_matrix as _mm  # noqa: E402
import masking_type as _mt  # noqa: E402

# Repo-root CSVs are the SME-facing approval copies the models read.
MASKING_MATRIX_CSV = Path(_mm.DEFAULT_CSV_PATH)
MASKING_TYPE_CSV = Path(_mt.DEFAULT_CSV_PATH)

# A strict identifier guard: table / column names that flow into a SQL Server
# query must look like plain identifiers, so a tampered CSV can never become an
# injection path. The pattern is a module-level string (not a compiled object)
# because SQLMesh serializes the globals referenced by model functions, and a
# compiled ``re.Pattern`` is not serializable.
_IDENT_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"


def is_safe_identifier(name: str) -> bool:
    """True if *name* is a plain SQL identifier (letters, digits, underscore)."""
    return bool(re.match(_IDENT_PATTERN, str(name or "")))


def resolve_cert_dir() -> Path:
    """Return the receiving-certificate directory.

    Defaults to ``<repo>/certificate_for_receiving`` (where
    ``generate_certificate.py`` writes ``receiving_certificate_*.json``); the
    ``RECEIVING_CERT_DIR`` env var overrides it.
    """
    override = os.environ.get("RECEIVING_CERT_DIR")
    if override:
        return Path(override)
    return Path(_REPO_ROOT_STR) / "certificate_for_receiving"


def _load_active_cert(cert_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load the newest receiving certificate JSON; ``{}`` if none exists.

    "Newest" is the highest ``certificate_version`` (falling back to filename
    order). Returns the parsed certificate dict, or an empty dict when no
    certificate has been generated yet (the models tolerate that).
    """
    cert_dir = cert_dir or resolve_cert_dir()
    if not cert_dir.exists():
        return {}
    candidates = sorted(cert_dir.glob("receiving_certificate*.json"))
    if not candidates:
        return {}

    def _ver_key(p: Path):
        try:
            with p.open(encoding="utf-8") as fh:
                data = json.load(fh)
            major, _, minor = str(
                data.get("certificate_version", "0.0")
            ).partition(".")
            return (int(major or 0), int(minor or 0))
        except Exception:
            return (-1, -1)

    newest = max(candidates, key=_ver_key)
    try:
        with newest.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def load_masking_matrix(path: "Path | str | None" = None) -> pd.DataFrame:
    """Load + normalize the masking-matrix CSV into a DataFrame.

    Reuses ``masking_matrix.read_csv_rows`` so the row normalization matches the
    rest of the app. Defaults to the canonical repo-root CSV
    (``_mm.DEFAULT_CSV_PATH``); returns an empty (typed) frame if it is absent.
    """
    csv_path = str(path) if path is not None else str(_mm.DEFAULT_CSV_PATH)
    rows = _mm.read_csv_rows(csv_path)
    if not rows:
        return pd.DataFrame(columns=list(_mm.MATRIX_COLUMNS))
    return pd.DataFrame(rows)


def load_masking_types(path: "Path | str | None" = None) -> pd.DataFrame:
    """Load + normalize the masking-type lookup CSV into a DataFrame."""
    csv_path = str(path) if path is not None else str(_mt.DEFAULT_CSV_PATH)
    rows = _mt.read_csv_rows(csv_path)
    if not rows:
        return pd.DataFrame(columns=list(_mt.TYPE_COLUMNS))
    return pd.DataFrame(rows)


def get_masking_rules_for_table(
    table_name: str,
    mask_df: pd.DataFrame,
    types_df: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """Return the masking rules that apply to *table_name*.

    One rule per matrix row for the table that names a column; the row's
    ``masking_mode`` is used, falling back to the ``masking_type`` lookup when a
    row leaves it blank. Rows without a ``column_name`` (table-level markers) are
    skipped — there is no column to mask.
    """
    if mask_df is None or mask_df.empty:
        return []

    mode_by_type: Dict[str, int] = {}
    if types_df is not None and not types_df.empty:
        for _, t in types_df.iterrows():
            key = str(t.get("masking_type", "")).strip().lower()
            mode_by_type[key] = _mm._to_int(t.get("masking_mode"), 0)

    want = str(table_name or "").strip().lower()
    rules: List[Dict[str, Any]] = []
    for _, row in mask_df.iterrows():
        if str(row.get("table_name", "")).strip().lower() != want:
            continue
        column = str(row.get("column_name", "")).strip()
        if not column:
            continue
        mtype = str(row.get("masking_type", "")).strip()
        mode = _mm._to_int(
            row.get("masking_mode"), mode_by_type.get(mtype.lower(), 1)
        )
        rules.append(
            {
                "dag_no": str(row.get("dag_no", "")).strip(),
                "column_name": column,
                "masking_mode": mode,
                "field_length": _mm._to_int(row.get("field_length"), 0),
                "masking_type": mtype,
                "masking_rule": str(row.get("masking_rule", "")).strip(),
            }
        )
    return rules


def apply_masking_to_df(
    df: pd.DataFrame,
    rules: List[Dict[str, Any]],
    seed: Optional[str] = None,
) -> pd.DataFrame:
    """Apply the masking *rules* to *df* in place (and return it).

    Each rule masks its column with the canonical deterministic transform
    (``masking_matrix.mask_row_value``), sized to the row's ``field_length`` and
    sensitive to its ``masking_mode``. The salt comes from *seed* or the
    ``GEMIN_SALT`` secret; columns not present in the frame are skipped.
    """
    if df is None or df.empty or not rules:
        return df
    lower_cols = {c.lower(): c for c in df.columns}
    for rule in rules:
        col = lower_cols.get(str(rule["column_name"]).lower())
        if col is None:
            continue
        df[col] = df[col].map(
            lambda v, _r=rule: _mm.mask_row_value(_r, v, salt=seed)
        )
    return df


__all__ = [
    "MASKING_MATRIX_CSV",
    "MASKING_TYPE_CSV",
    "is_safe_identifier",
    "resolve_cert_dir",
    "_load_active_cert",
    "load_masking_matrix",
    "load_masking_types",
    "get_masking_rules_for_table",
    "apply_masking_to_df",
]
