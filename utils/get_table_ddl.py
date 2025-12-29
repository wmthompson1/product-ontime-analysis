"""Utility to fetch a table's DDL from a PostgreSQL database.

Usage:
    from utils.get_table_ddl import get_table_ddl
    ddl = get_table_ddl('my_table')

This tries to run `pg_dump --schema-only --table=...` first (if `pg_dump` is available).
If `pg_dump` isn't available or fails, it falls back to querying
`information_schema` and building a minimal CREATE TABLE statement
including columns and primary key.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from typing import Optional

try:
    import psycopg2
except Exception:  # pragma: no cover - psycopg2 may not be installed in some environments
    psycopg2 = None


def _run_pg_dump(dsn: str, schema: str, table: str) -> Optional[str]:
    pg_dump_path = shutil.which("pg_dump")
    if not pg_dump_path:
        return None

    # Use --schema-only and target the single table
    tbl = f"{schema}.{table}" if schema else table
    cmd = [pg_dump_path, "--schema-only", "--no-owner", "--no-privileges", "--table", tbl, "--dbname", dsn]
    try:
        out = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return out.stdout
    except subprocess.CalledProcessError:
        return None


def _build_minimal_ddl(conn, schema: str, table: str) -> Optional[str]:
    cur = conn.cursor()

    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default, character_maximum_length,
               numeric_precision, numeric_scale, udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )
    rows = cur.fetchall()
    if not rows:
        return None

    cols = []
    for (column_name, data_type, is_nullable, column_default, char_max_len, num_prec, num_scale, udt_name) in rows:
        # Prefer udt_name for more precise type in some cases
        typ = data_type
        if data_type in ("character varying", "character", "numeric") and char_max_len:
            if data_type.startswith("character") and char_max_len:
                typ = f"{data_type}({char_max_len})"
            elif data_type == "numeric" and num_prec:
                if num_scale:
                    typ = f"numeric({num_prec},{num_scale})"
                else:
                    typ = f"numeric({num_prec})"

        # fallback to udt_name for custom types
        if not typ or typ == "USER-DEFINED":
            typ = udt_name

        parts = [f"\"{column_name}\" {typ}"]
        if column_default is not None:
            parts.append(f"DEFAULT {column_default}")
        if is_nullable == "NO":
            parts.append("NOT NULL")
        cols.append(" ".join(parts))

    # find primary key columns
    cur.execute(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = %s
          AND tc.table_name = %s
        ORDER BY kcu.ordinal_position
        """,
        (schema, table),
    )
    pk_cols = [r[0] for r in cur.fetchall()]

    ddl = []
    full_name = f"\"{schema}\".\"{table}\"" if schema else f"\"{table}\""
    ddl.append(f"CREATE TABLE {full_name} (")
    ddl.append(
        ",\n".join("    " + c for c in cols)
    )
    if pk_cols:
        ddl.append(",\n    PRIMARY KEY (" + ", ".join(f'\"{c}\"' for c in pk_cols) + ")")
    ddl.append("\n);")
    cur.close()
    return "\n".join(ddl)


def get_table_ddl(table: str, dsn: Optional[str] = None, schema: str = "public", try_pg_dump: bool = True) -> str:
    """Return DDL for `schema.table`.

    Parameters
    - table: table name (no schema) or schema.table (if you include a dot it will override schema argument)
    - dsn: optional database URL/DSN (if None, `DATABASE_URL` env var is used)
    - schema: schema name (defaults to `public`)
    - try_pg_dump: if True, try using `pg_dump` first

    Returns the DDL string or raises RuntimeError if the table does not exist or connection fails.
    """
    if "." in table:
        s, t = table.split(".", 1)
        schema, table = s, t

    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("No DSN provided and DATABASE_URL not set in environment")

    if try_pg_dump:
        out = _run_pg_dump(dsn, schema, table)
        if out:
            return out

    if psycopg2 is None:
        raise RuntimeError("psycopg2 not installed and pg_dump not available, cannot retrieve DDL")

    # connect and build a minimal DDL
    conn = psycopg2.connect(dsn)
    try:
        ddl = _build_minimal_ddl(conn, schema, table)
        if ddl:
            return ddl
        raise RuntimeError(f"Table {schema}.{table} not found or has no columns")
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Print table DDL for a Postgres table")
    p.add_argument("table", help="Table name or schema.table")
    p.add_argument("--dsn", help="Database URL/DSN (fallback to $DATABASE_URL)")
    p.add_argument("--no-pgdump", dest="pgdump", action="store_false", help="Don't try pg_dump")
    args = p.parse_args()
    try:
        print(get_table_ddl(args.table, dsn=args.dsn, try_pg_dump=args.pgdump))
    except Exception as e:
        print(f"Error: {e}")
        raise
