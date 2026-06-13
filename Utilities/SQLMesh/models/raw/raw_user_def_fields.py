"""SQLMesh raw model: ``raw.raw_user_def_fields``

Ported for Plan 8 (Multi-Agent Schema Traversal & Masking). Loads the ERP
user-defined-field records from the pre-stage SQL Server (``Staging.dbo.
USER_DEF_FIELDS``), masks them deterministically per ``masking_matrix.csv``, and
annotates each row with the active receiving certificate's metadata. The masking
transform comes from ``masking_helpers`` — the single SME-approved source —
never an LLM.

``user_def_1`` is exposed as the resolved physical column for the "Legacy
Manufacturer Code" semantic intent (see ``orchestrator_handshake.py``); it is a
deterministically masked projection of the record's string value.

Note: ``pyodbc`` + the SQL Server source are only needed to *execute* this
model. SQLMesh renders/plans it from the static ``columns`` schema without them;
in this repo execution is skipped (no ``pyodbc`` / no Staging server).
"""
from __future__ import annotations

import importlib
import logging
import os
import typing as t

import pandas as pd
from sqlmesh import ExecutionContext, model

# SQLMesh loads this file as `models.raw.raw_user_def_fields`, so the masking
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

_TABLE = "USER_DEF_FIELDS"
_CONNECTION_STRING = os.environ.get(
    "STAGING_ODBC",
    "Driver={ODBC Driver 18 for SQL Server};Server=sql-lab-2;Database=Staging;"
    "Trusted_Connection=yes;TrustServerCertificate=yes;",
)

_SELECT_SQL = """
SELECT
    ROWID          AS rowid,
    PROGRAM_ID     AS program_id,
    ID             AS id,
    DOCUMENT_ID    AS document_id,
    LINE_NO        AS line_no,
    DEL_LINE_NO    AS del_line_no,
    LABEL          AS label,
    DATA_TYPE      AS data_type,
    DISPLAY_FORMAT AS display_format,
    TAB_OR_TABLE   AS tab_or_table,
    TAB_ID         AS tab_id,
    TABLE_ID       AS table_id,
    SEQUENCE_NO    AS sequence_no,
    UDF_REQUIRED   AS udf_required,
    STRING_VAL     AS string_val,
    NUMBER_VAL     AS number_val,
    BOOL_VAL       AS bool_val,
    DATE_VAL       AS date_val
FROM Staging.dbo.USER_DEF_FIELDS WITH (NOLOCK)
"""


@model(
    "raw.raw_user_def_fields",
    kind="FULL",
    columns={
        "rowid": "int",
        "program_id": "text",
        "id": "text",
        "document_id": "text",
        "line_no": "int",
        "del_line_no": "int",
        "label": "text",
        "data_type": "int",
        "display_format": "text",
        "tab_or_table": "int",
        "tab_id": "text",
        "table_id": "text",
        "sequence_no": "int",
        "udf_required": "int",
        "string_val": "text",
        "number_val": "double",
        "bool_val": "int",
        "date_val": "timestamp",
        "user_def_1": "text",
        "receiving_id": "text",
        "receiver_id": "text",
        "cert_status": "text",
        "cert_version": "text",
    },
    grain=["rowid"],
    description=(
        "ERP user-defined fields from Staging.dbo.USER_DEF_FIELDS, masked per "
        "masking_matrix.csv and annotated with the active receiving certificate."
    ),
)
def execute(context: ExecutionContext, **kwargs: t.Any) -> pd.DataFrame:
    if not is_safe_identifier(_TABLE):
        raise ValueError(f"unsafe table identifier: {_TABLE!r}")
    try:
        pyodbc = importlib.import_module("pyodbc")
    except Exception:
        logging.exception("pyodbc import failed (SQL Server source unavailable)")
        raise

    conn = pyodbc.connect(_CONNECTION_STRING)
    try:
        df = pd.read_sql(_SELECT_SQL, conn)
    finally:
        conn.close()

    # Normalize column names, then mask per the matrix rules for this table.
    df.columns = [c.lower() for c in df.columns]
    seed = os.environ.get("RECEIVING_PSEED")
    mask_df = load_masking_matrix()
    types_df = load_masking_types()
    rules = get_masking_rules_for_table("user_def_fields", mask_df, types_df)
    if rules:
        apply_masking_to_df(df, rules, seed)

    # Resolve the "Legacy Manufacturer Code" physical column (USER_DEF_1) as a
    # deterministically masked projection of the record's string value.
    df = df.assign(user_def_1=df.get("string_val", ""))
    apply_masking_to_df(
        df,
        [{
            "column_name": "user_def_1",
            "masking_mode": 1,
            "field_length": 30,
            "masking_type": "deterministic_hash",
            "masking_rule": "hash_sha256(column_name,length)",
        }],
        seed,
    )

    # Annotate with the active receiving certificate's metadata.
    cert = _load_active_cert()
    r_id = str(cert.get("receiving_id", "")) if cert else ""
    rec_id = r_id.replace("RECV-", "RECR-", 1) if r_id else None
    c_status = str(cert.get("status", "")) if cert else ""
    c_ver = str(cert.get("certificate_version", "")) if cert else ""

    df = df.assign(
        receiving_id=r_id,
        receiver_id=rec_id,
        cert_status=c_status,
        cert_version=c_ver,
    )
    return df
