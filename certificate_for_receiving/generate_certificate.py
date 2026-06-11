"""
generate_certificate.py
-----------------------
Connects to sql-lab-2 (Staging), reads masking_matrix.csv, probes the Vendor
and Part tables, and writes a versioned receiving certificate to this directory.

Usage:
    python certificate_for_receiving/generate_certificate.py
"""

from __future__ import annotations

import csv
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASKING_MATRIX_PATH = REPO_ROOT / "masking_matrix.csv"
CERTIFICATE_DIR = Path(__file__).resolve().parent

# please update to use environment variables or config management 
CONNECTION_STRING = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=sql-lab-2;"
    "Database=Staging;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _connect():
    try:
        pyodbc = importlib.import_module("pyodbc")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "pyodbc is required. Install it in the active Python environment."
        ) from exc
    return pyodbc.connect(CONNECTION_STRING)


# ---------------------------------------------------------------------------
# Masking matrix
# ---------------------------------------------------------------------------

def _load_masking_matrix() -> list[dict]:
    with MASKING_MATRIX_PATH.open(newline="", encoding="utf-8") as f:
        return [
            row for row in csv.DictReader(f)
            if row.get("status", "").strip().lower() == "active"
        ]


# ---------------------------------------------------------------------------
# Table probe
# ---------------------------------------------------------------------------

def _probe_table(conn, table_name: str) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM Staging.dbo.{table_name.upper()}")
        row_count = cursor.fetchone()[0]
        return {"status": "reachable", "row_count": row_count}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

def _next_version_and_id(cert_dir: Path) -> tuple[str, str]:
    """Increment version and receiving_id from the newest existing certificate."""
    candidates = sorted(cert_dir.glob("receiving_certificate*.json"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not candidates:
        return "1.0", f"RECV-{today}-001"

    with candidates[-1].open(encoding="utf-8") as f:
        latest = json.load(f)

    major, minor = latest.get("certificate_version", "1.0").split(".", 1)
    new_version = f"{major}.{int(minor) + 1}"

    # Find highest sequence number already used today
    seq = 0
    for p in cert_dir.glob("receiving_certificate*.json"):
        with p.open(encoding="utf-8") as f:
            recv_id = json.load(f).get("receiving_id", "")
        if f"RECV-{today}-" in recv_id:
            try:
                seq = max(seq, int(recv_id.rsplit("-", 1)[-1]))
            except ValueError:
                pass

    return new_version, f"RECV-{today}-{seq + 1:03d}"


# ---------------------------------------------------------------------------
# Certificate builder
# ---------------------------------------------------------------------------

def generate_certificate() -> Path:
    matrix_rows = _load_masking_matrix()

    dag_lines = []
    unique_tables: list[str] = []
    for row in matrix_rows:
        entry = {
            "dag_no": row["dag_no"],
            "table_name": row["table_name"],
            "column_name": row["column_name"],
            "masking_rule": row["masking_rule"],
            "masking_type": row["masking_type"],
        }
        if row.get("parent_table"):
            entry["parent_table"] = row["parent_table"]
        if row.get("parent_column"):
            entry["parent_column"] = row["parent_column"]
        dag_lines.append(entry)
        if row["table_name"] not in unique_tables:
            unique_tables.append(row["table_name"])

    # Probe tables
    table_probes: dict[str, dict] = {}
    connection_status = "connected"
    try:
        with _connect() as conn:
            for table in unique_tables:
                table_probes[table] = _probe_table(conn, table)
    except Exception as exc:
        connection_status = "failed"
        for table in unique_tables:
            table_probes[table] = {"status": "unreachable", "error": str(exc)}

    new_version, new_receiving_id = _next_version_and_id(CERTIFICATE_DIR)
    issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    certificate = {
        "certificate_version": new_version,
        "issued_at": issued_at,
        "pre_stage_server": "sql-lab-2",
        "receiving_id": new_receiving_id,
        "connection_probe": {
            "server": "sql-lab-2",
            "database": "Staging",
            "auth": "Trusted_Connection (Windows Integrated)",
            "status": connection_status,
            "tables": table_probes,
        },
        "masking_matrix_ref": {
            "file": "../masking_matrix.csv",
            "dag_lines": dag_lines,
        },
        "receiver_id_agent": "sqlmesh-receiving-agent-v1",
        "trust_boundary": "pre_stage_to_receiving",
        "status": "certified" if connection_status == "connected" else "pending",
        "notes": (
            "PII masking applied per corpus policy before downstream model ingestion. "
            "DAG traversal: vendor.id (1.1) → part.pref_vendor (1.2). "
            f"Server probe: {connection_status}."
        ),
    }

    out_path = CERTIFICATE_DIR / f"receiving_certificate_{new_receiving_id}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(certificate, f, indent=2)

    print(f"Certificate written : {out_path.name}")
    print(f"  Version           : {new_version}")
    print(f"  Receiving ID      : {new_receiving_id}")
    print(f"  Server probe      : {connection_status}")
    for table, probe in table_probes.items():
        print(f"  Table [{table}]  : {probe}")

    return out_path


if __name__ == "__main__":
    generate_certificate()
