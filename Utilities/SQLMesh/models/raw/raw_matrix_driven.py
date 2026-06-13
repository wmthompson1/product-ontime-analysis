"""SQLMesh raw model: ``raw.raw_matrix_driven``

Ported for Plan 8 (Multi-Agent Schema Traversal & Masking). Walks the active
column-masking DAG (``masking_matrix.csv``), loads the named pre-stage SQL
Server tables (``Staging.dbo.<table>``), masks the flagged columns
deterministically, and emits a single normalized long-format frame:

    (cert metadata) + dag_no + source_table + source_column + masked_value

The narrow, statically-typed shape (instead of an arbitrary ``SELECT *`` union)
keeps SQLMesh render/plan stable. The masking transform comes from
``masking_helpers`` — the single SME-approved source — never an LLM.

Note: ``pyodbc`` + the SQL Server source are only needed to *execute* this
model. SQLMesh renders/plans it from the static ``columns`` schema without them;
when ``pyodbc`` or Staging is unavailable the model returns an empty (typed)
frame rather than failing.
"""
from __future__ import annotations

import importlib
import logging
import os
import typing as t

import pandas as pd
from sqlmesh import ExecutionContext, model

# SQLMesh loads this file as `models.raw.raw_matrix_driven`, so the masking
# helper is importable as a sibling under the same project-local `models`
# package. (masking_helpers itself puts the hf-space app dir on sys.path for the
# canonical masking_matrix / masking_type modules.)
from models.raw.masking_helpers import (
    _load_active_cert,
    load_masking_matrix,
    load_masking_types,
    get_masking_rules_for_table,
    apply_masking_to_df,
    is_safe_identifier,
)

_CONNECTION_STRING = os.environ.get(
    "STAGING_ODBC",
    "Driver={ODBC Driver 18 for SQL Server};Server=sql-lab-2;Database=Staging;"
    "Trusted_Connection=yes;TrustServerCertificate=yes;",
)

_OUT_COLUMNS = [
    "receiving_id",
    "receiver_id",
    "cert_status",
    "cert_version",
    "dag_no",
    "source_table",
    "source_column",
    "masking_rule",
    "masking_type",
    "masked_value",
]


@model(
    "raw.raw_matrix_driven",
    kind="FULL",
    columns={c: "text" for c in _OUT_COLUMNS},
    grain=[],
    description=(
        "Normalized long-format masked sample of every active column-masking DAG "
        "line in masking_matrix.csv, annotated with the active receiving "
        "certificate. One row per masked source value."
    ),
)
def execute(context: ExecutionContext, **kwargs: t.Any) -> pd.DataFrame:
    def _empty() -> pd.DataFrame:
        return pd.DataFrame(columns=_OUT_COLUMNS).astype(str)

    mask_df = load_masking_matrix()
    types_df = load_masking_types()
    if mask_df is None or mask_df.empty:
        logging.info("masking_matrix.csv is empty; nothing to load")
        return _empty()

    cert = _load_active_cert()
    r_id = str(cert.get("receiving_id", "")) if cert else ""
    rec_id = r_id.replace("RECV-", "RECR-", 1) if r_id else ""
    c_status = str(cert.get("status", "")) if cert else ""
    c_ver = str(cert.get("certificate_version", "")) if cert else ""

    # Prefer the certificate's active DAG; otherwise take every table named in
    # the matrix (active rows only are masked by the rule lookup downstream).
    dag_lines = (cert.get("masking_matrix_ref") or {}).get("dag_lines", []) if cert else []
    active_tables = {
        str(line.get("table_name", "")).strip().lower()
        for line in dag_lines
        if line.get("table_name")
    }
    table_names = sorted({
        str(x).strip() for x in mask_df.get("table_name", []) if str(x).strip()
    })
    if active_tables:
        table_names = [t for t in table_names if t.lower() in active_tables]
    if not table_names:
        logging.info("no active tables to load from the masking matrix")
        return _empty()

    try:
        pyodbc = importlib.import_module("pyodbc")
    except Exception:
        logging.warning(
            "pyodbc unavailable; SQL Server staging not loaded — "
            "returning empty matrix-driven frame"
        )
        return _empty()

    seed = os.environ.get("RECEIVING_PSEED")
    rows: t.List[t.Dict[str, t.Any]] = []
    conn = None
    try:
        conn = pyodbc.connect(_CONNECTION_STRING)
        for tbl in table_names:
            if not is_safe_identifier(tbl):
                logging.warning("skipping unsafe table identifier: %r", tbl)
                continue
            rules = get_masking_rules_for_table(tbl, mask_df, types_df)
            if not rules:
                continue
            try:
                df = pd.read_sql(
                    f"SELECT * FROM Staging.dbo.{tbl.upper()} WITH (NOLOCK)", conn
                )
            except Exception:
                logging.exception("failed reading %s; skipping", tbl)
                continue
            df.columns = [c.lower() for c in df.columns]
            apply_masking_to_df(df, rules, seed)
            for rule in rules:
                col = str(rule["column_name"]).lower()
                if col not in df.columns:
                    continue
                for val in df[col].tolist():
                    rows.append({
                        "receiving_id": r_id,
                        "receiver_id": rec_id,
                        "cert_status": c_status,
                        "cert_version": c_ver,
                        "dag_no": str(rule.get("dag_no", "")),
                        "source_table": tbl,
                        "source_column": col,
                        "masking_rule": str(rule.get("masking_rule", "")),
                        "masking_type": str(rule.get("masking_type", "")),
                        "masked_value": "" if val is None else str(val),
                    })
    finally:
        if conn is not None:
            conn.close()

    if not rows:
        return _empty()
    return pd.DataFrame(rows, columns=_OUT_COLUMNS).astype(str)
