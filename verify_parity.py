"""
verify_parity.py — Code-Documentation Parity Auditor (MCP Skill: parity_verifier_001)

Audits alignment across three layers:
  1. Schema Catalog (SQLite) — authoritative source of truth
  2. SQLMesh Staging Models (.sql files) — code layer
  3. Documentation/models (Markdown) — narrative layer

Usage:
    python verify_parity.py
    python verify_parity.py --catalog <path> --models <dir> --docs <dir>
"""

import sqlite3
import os
import json
import argparse
import sys


def verify_parity(catalog_path: str, models_dir: str, docs_dir: str) -> dict:
    """
    Checks if tables in the schema catalog exist as .sql models and are
    mentioned in Markdown documentation.

    Args:
        catalog_path: Path to schema_catalog.db (SQLite).
        models_dir:   Directory containing SQLMesh .sql staging models.
        docs_dir:     Directory containing Markdown documentation files.

    Returns:
        dict with keys: status, verified_count, missing_models,
                        missing_docs, discrepancies, catalog_count
    """
    # --- 1. Load authoritative table list from schema_catalog.db ---
    if not os.path.exists(catalog_path):
        return {
            "status": "error",
            "message": f"Catalog not found: {catalog_path}",
            "verified_count": 0,
            "discrepancies": []
        }

    conn = sqlite3.connect(catalog_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT table_name FROM schema_catalog")
        catalog_tables = {row[0].lower() for row in cursor.fetchall()}
    except sqlite3.OperationalError as exc:
        conn.close()
        return {
            "status": "error",
            "message": f"Could not query schema_catalog.db: {exc}",
            "verified_count": 0,
            "discrepancies": []
        }
    finally:
        conn.close()

    # --- 2. Check SQLMesh Staging Models ---
    model_files: set[str] = set()
    if os.path.exists(models_dir):
        model_files = {
            f.replace(".sql", "").lower()
            for f in os.listdir(models_dir)
            if f.endswith(".sql")
        }

    # --- 3. Check Documentation Narrative ---
    doc_content = ""
    if os.path.exists(docs_dir):
        for doc in os.listdir(docs_dir):
            if doc.endswith(".md"):
                with open(os.path.join(docs_dir, doc), "r", encoding="utf-8") as fh:
                    doc_content += fh.read().lower()

    # --- 4. Build discrepancy report ---
    missing_models = []
    missing_docs = []

    for table in sorted(catalog_tables):
        # SQLMesh staging models are prefixed stg_; strip prefix for match
        model_name = f"stg_{table}" if f"stg_{table}" in model_files else table
        if model_name not in model_files and table not in model_files:
            missing_models.append(f"Missing SQLMesh Model: {table}")
        if table not in doc_content:
            missing_docs.append(f"Missing in Documentation: {table}")

    discrepancies = missing_models + missing_docs
    verified_count = len(catalog_tables) - len(set(missing_models))

    return {
        "status": "success" if not discrepancies else "warning",
        "catalog_count": len(catalog_tables),
        "verified_count": verified_count,
        "missing_models": missing_models,
        "missing_docs": missing_docs,
        "discrepancies": discrepancies
    }


def _print_report(result: dict) -> None:
    """Print a human-readable audit report to stdout."""
    icon = "✔" if result["status"] == "success" else ("✘" if result["status"] == "error" else "⚠")
    print(f"\n{icon}  Parity Audit — Status: {result['status'].upper()}")

    if result["status"] == "error":
        print(f"   {result.get('message', 'Unknown error')}")
        return

    print(f"   Catalog tables : {result['catalog_count']}")
    print(f"   Verified        : {result['verified_count']}")
    print(f"   Discrepancies   : {len(result['discrepancies'])}")

    if result["missing_models"]:
        print("\n  Missing SQLMesh Models:")
        for item in result["missing_models"]:
            print(f"    • {item}")

    if result["missing_docs"]:
        print("\n  Missing in Documentation:")
        for item in result["missing_docs"]:
            print(f"    • {item}")

    if not result["discrepancies"]:
        print("   All catalog tables have matching models and documentation. ✓")


def main() -> int:
    parser = argparse.ArgumentParser(description="Code-Documentation Parity Auditor")
    parser.add_argument(
        "--catalog",
        default="Utilities/SQLMesh/analysis/impact/output/schema_catalog.db",
        help="Path to schema_catalog.db"
    )
    parser.add_argument(
        "--models",
        default="Utilities/SQLMesh/models/staging",
        help="Directory containing SQLMesh staging .sql models"
    )
    parser.add_argument(
        "--docs",
        default="Documentation/models",
        help="Directory containing Markdown documentation"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON instead of human-readable report"
    )
    args = parser.parse_args()

    result = verify_parity(args.catalog, args.models, args.docs)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_report(result)

    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
