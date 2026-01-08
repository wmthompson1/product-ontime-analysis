"""
Generate Markdown documentation of SQL schema.

Usage:
  export DATABASE_URL=postgresql://user:pass@host/dbname
  python schema_to_markdown.py > schema.md

This script uses SQLAlchemy to reflect the database and prints tables,
primary keys and foreign keys in Markdown format.
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, inspect

def require_env(key):
    try:
        return os.environ[key]
    except KeyError:
        print(f"Required environment variable '{key}' not set.", file=sys.stderr)
        sys.exit(2)

DATABASE_URL = require_env("DATABASE_URL")

def main():
    engine = create_engine(DATABASE_URL)
    insp = inspect(engine)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    print("# Database schema (generated)\n")
    for table_name in sorted(metadata.tables.keys()):
        table = metadata.tables[table_name]
        print(f"## Table: {table_name}")
        # Columns
        print("- Columns:")
        for col in table.columns:
            colline = f"  - {col.name} : {col.type}"
            if col.primary_key:
                colline += " (PK)"
            if not col.nullable:
                colline += " (NOT NULL)"
            if col.default is not None:
                colline += f" (default={col.default})"
            print(colline)
        # Primary key
        pk = insp.get_pk_constraint(table_name)
        pkcols = pk.get("constrained_columns", [])
        print(f"- Primary key: {', '.join(pkcols) if pkcols else '(none)'}")
        # Foreign keys
        fks = insp.get_foreign_keys(table_name)
        if fks:
            print("- Foreign keys:")
            for fk in fks:
                cols = fk.get("constrained_columns", [])
                ref = fk.get("referred_table")
                refcols = fk.get("referred_columns", [])
                print(f"  - {', '.join(cols)} -> {ref}({', '.join(refcols)})")
        else:
            print("- Foreign keys: (none)")
        print("\n")

if __name__ == "__main__":
    main()