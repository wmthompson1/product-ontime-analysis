#!/usr/bin/env python
"""
orchestrator_handshake.py
=========================

Comprehensive validation script for Plan 8: Multi-Agent Schema Traversal &
Masking Orchestration.

Phase 1: Environment Validation
- Python version (3.13 for sqlglot ast.Str compatibility; NOT 3.14, which drops
  ast.Str)
- SQLMesh installed and functional
- sqlglot available and AST parsing works
- Local SQLite catalog accessible
- Utilities/SQLMesh project structure intact + SQLMesh context loads

Phase 2: Semantic Validation (Plan 8 Core)
- Resolve a semantic intent to its physical column using THIS repo's schema
  metadata (api_field_descriptions, the SME/DAB overlay) — deterministic, never
  an LLM (Solder Pattern).
- Use sqlglot to programmatically build the AST query for that column.
- Load the SQLMesh context and confirm the masked staging model for the resolved
  table (``raw.raw_<table>``) exposes the resolved column — i.e. the intent maps
  through its own table's model, not merely to any model that happens to declare
  a same-named column.

Returns exit code 0 on success, 1 on any validation failure.
Usage: python orchestrator_handshake.py

This file lives at the repo root: it derives repo_root from its own location and
expects ``Utilities/SQLMesh`` and ``hf-space-inventory-sqlgen`` as siblings.
"""
from __future__ import annotations

import ast
import logging
import os
import sqlite3
import sys
from pathlib import Path

# SQLMesh must never drop into an interactive prompt during the handshake.
os.environ.setdefault("SQLMESH_NO_INTERACTIVE", "1")
os.environ.setdefault("CI", "1")

REPO_ROOT = Path(__file__).resolve().parent
# Python puts this script's directory (the repo root) on sys.path. The repo root
# contains an unrelated models.py (a Flask SQLAlchemy helper), which would shadow
# SQLMesh's project-local `models` package when it loads the Python models
# (import models.raw.<name>). Drop the repo root from sys.path so SQLMesh
# resolves its own models/ package.
sys.path[:] = [
    p for p in sys.path if p not in ("", ".") and Path(p).resolve() != REPO_ROOT
]

DB_PATH = REPO_ROOT / "hf-space-inventory-sqlgen" / "app_schema" / "manufacturing.db"
SQLMESH_DIR = REPO_ROOT / "Utilities" / "SQLMesh"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def validate_python_version() -> bool:
    """Check Python 3.13 for sqlglot AST compatibility (3.14 drops ast.Str)."""
    v = sys.version_info
    logger.info(f"Python version: {sys.version}")
    if v.major == 3 and v.minor == 13:
        logger.info("\u2713 Python 3.13 (sqlglot ast.Str compatible)")
        return True
    if v.major == 3 and v.minor > 13:
        logger.error(
            f"\u2717 Python {v.major}.{v.minor}: SQLGlot/SQLMesh AST handling "
            "depends on ast.Str, removed after 3.13. Pin to 3.13."
        )
        return False
    logger.error(f"\u2717 Python {v.major}.{v.minor} too old. Required: 3.13")
    return False


def validate_sqlmesh_installed() -> bool:
    """Verify SQLMesh is importable."""
    try:
        import sqlmesh
        logger.info(f"\u2713 SQLMesh {sqlmesh.__version__} imported successfully")
        return True
    except ImportError as e:
        logger.error(f"\u2717 SQLMesh import failed: {e}")
        return False


def validate_sqlglot_available() -> bool:
    """Verify sqlglot is importable, has ast.Str (3.13), and parses."""
    try:
        import sqlglot
    except ImportError as e:
        logger.error(f"\u2717 SQLGlot import failed: {e}")
        return False

    logger.info(f"\u2713 SQLGlot {sqlglot.__version__} imported successfully")
    if hasattr(ast, "Str"):
        logger.info("\u2713 ast.Str available (Python 3.13 compatible)")
    else:
        logger.warning("\u26a0 ast.Str not available (expected only on 3.14+)")

    try:
        sqlglot.parse_one("SELECT * FROM test_table", read="duckdb")
        logger.info("\u2713 SQLGlot AST parsing functional")
        return True
    except Exception as e:
        logger.error(f"\u2717 SQLGlot AST parsing failed: {e}")
        return False


def validate_project_structure() -> bool:
    """Verify critical directories exist."""
    checks = {
        "Utilities/SQLMesh": SQLMESH_DIR,
        "Utilities/SQLMesh/models": SQLMESH_DIR / "models",
        "Utilities/SQLMesh/analysis": SQLMESH_DIR / "analysis",
        "hf-space-inventory-sqlgen": REPO_ROOT / "hf-space-inventory-sqlgen",
    }
    all_valid = True
    for name, path in checks.items():
        if path.exists() and path.is_dir():
            logger.info(f"\u2713 {name} exists")
        else:
            logger.error(f"\u2717 {name} missing or not a directory: {path}")
            all_valid = False
    return all_valid


def _load_context():
    """Load a SQLMesh Context from Utilities/SQLMesh (non-interactive)."""
    from sqlmesh.core.context import Context

    original_cwd = os.getcwd()
    os.chdir(SQLMESH_DIR)
    try:
        return Context(), original_cwd
    except Exception:
        os.chdir(original_cwd)
        raise


def validate_sqlmesh_context() -> bool:
    """Attempt to load the SQLMesh context from Utilities/SQLMesh."""
    try:
        ctx, original_cwd = _load_context()
    except Exception as e:
        logger.error(f"\u2717 SQLMesh context load failed: {e}")
        return False
    try:
        logger.info(
            f"\u2713 SQLMesh context loaded successfully ({len(ctx.models)} models)"
        )
        return True
    finally:
        os.chdir(original_cwd)


def validate_manufacturing_db() -> bool:
    """Check that manufacturing.db is accessible."""
    if not DB_PATH.exists():
        logger.error(f"\u2717 manufacturing.db not found at {DB_PATH}")
        return False
    logger.info(f"\u2713 manufacturing.db accessible at {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
        finally:
            conn.close()
        logger.info(f"\u2713 manufacturing.db contains {count} tables")
        return True
    except Exception as e:
        logger.error(f"\u2717 manufacturing.db read failed: {e}")
        return False


def resolve_semantic_intent(intent: str, db_path: Path) -> "tuple[str, str] | None":
    """Resolve a semantic intent to its ``(table_name, column_name)`` from metadata.

    Deterministic lookup (Solder Pattern — never an LLM):
      1. ``api_field_descriptions.display_name`` (the SME/DAB human-label
         overlay) -> ``(table_name, column_name)``.
      2. Fallback: ``column_bindings.intent_name`` -> ``(table_name, column_name)``.

    The table is carried alongside the column so the caller can assert the intent
    maps through *that table's* model, not just to any model exposing the column.

    Example: 'Legacy Manufacturer Code' -> ('user_def_fields', 'USER_DEF_1').
    """
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        logger.error(f"\u2717 Semantic resolution failed to open DB: {e}")
        return None
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT table_name, column_name
            FROM api_field_descriptions
            WHERE LOWER(TRIM(display_name)) = LOWER(TRIM(?))
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (intent,),
        ).fetchone()
        if row is None:
            row = conn.execute(
                """
                SELECT table_name, column_name
                FROM column_bindings
                WHERE LOWER(TRIM(intent_name)) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (intent,),
            ).fetchone()
        if row is None:
            logger.warning(f"\u26a0 No physical column mapping for intent '{intent}'")
            return None
        table = str(row["table_name"] or "").strip()
        column = str(row["column_name"] or "").strip()
        if not table or not column:
            logger.warning(
                f"\u26a0 Incomplete mapping for intent '{intent}' "
                f"(table={table!r}, column={column!r})"
            )
            return None
        logger.info(
            f"\u2713 Semantic intent '{intent}' resolved to '{table}.{column}'"
        )
        return table, column
    except Exception as e:
        logger.error(f"\u2717 Semantic resolution failed: {e}")
        return None
    finally:
        conn.close()


def _find_model(ctx, leaf_name: str):
    """Find a model by its leaf name, robust to SQLMesh's fully-qualified keys."""
    for m in ctx.models.values():
        name = str(getattr(m, "name", ""))
        if name.split(".")[-1].strip('"').lower() == leaf_name.lower():
            return m
    return None


def build_and_execute_ast_query(table_name: str, column_name: str) -> bool:
    """Confirm the resolved table's model exposes *column_name*.

    1. Derive the masked staging model from the resolved table (``raw.raw_<table>``)
       — so a same-named column on a *different* table cannot produce a false pass.
    2. Build a SELECT against that model with sqlglot (exercises the AST path on 3.13).
    3. Load the SQLMesh context (non-interactive) and confirm that specific model
       exists and declares the resolved column.
    """
    try:
        import sqlglot
    except Exception as e:
        logger.error(f"\u2717 AST query build failed (sqlglot import): {e}")
        return False

    model_leaf = f"raw_{table_name.strip().lower()}"
    model_fqn = f"raw.{model_leaf}"
    sql = f"SELECT {column_name} FROM {model_fqn} LIMIT 1"
    logger.info(f"Building AST query for {table_name}.{column_name} via {model_fqn}")
    logger.info(f"  Generated SQL: {sql}")
    try:
        sqlglot.parse_one(sql, read="duckdb")
    except Exception as e:
        logger.error(f"\u2717 SQLGlot failed to parse the generated SQL: {e}")
        return False
    logger.info(f"\u2713 AST parsed successfully using sqlglot {sqlglot.__version__}")
    logger.info(f"  Python 3.13 compatibility: ast.Str available = {hasattr(ast, 'Str')}")

    try:
        ctx, original_cwd = _load_context()
    except Exception as e:
        logger.error(f"\u2717 SQLMesh context load failed: {e}")
        return False
    try:
        logger.info(f"\u2713 SQLMesh context loaded ({len(ctx.models)} models)")
        model = _find_model(ctx, model_leaf)
        if model is None:
            logger.error(
                f"\u2717 Model '{model_leaf}' for resolved table '{table_name}' "
                "not found in context"
            )
            logger.info(f"  Available models: {list(ctx.models.keys())[:5]} ...")
            return False
        logger.info(f"\u2713 Model '{model_leaf}' found in SQLMesh context")

        cols = {c.lower() for c in (getattr(model, "columns_to_types", {}) or {})}
        if column_name.lower() not in cols:
            logger.error(
                f"\u2717 Column '{column_name}' not declared by "
                f"'{model_leaf}' (has {sorted(cols)})"
            )
            return False
        logger.info(
            f"\u2713 Column '{column_name}' exposed by '{model_leaf}' "
            "(masked staging surface)"
        )
        logger.info(
            "\u2713 Semantic validation passed: Intent -> Table -> Column -> Model"
        )
        return True
    except Exception as e:
        logger.error(f"\u2717 AST query execution failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False
    finally:
        os.chdir(original_cwd)


def validate_semantic_intent_translation() -> bool:
    """Phase 2: resolve the sample intent and confirm the masked model surface."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("PHASE 2: SEMANTIC VALIDATION (Plan 8 Core)")
    logger.info("=" * 70)

    semantic_intent = "Legacy Manufacturer Code"
    logger.info(f"Step 1: Resolving semantic intent '{semantic_intent}'...")
    resolution = resolve_semantic_intent(semantic_intent, DB_PATH)
    if not resolution:
        return False
    table_name, physical_column = resolution

    logger.info(
        f"Step 2: Building/loading model surface for "
        f"'{table_name}.{physical_column}'..."
    )
    if not build_and_execute_ast_query(table_name, physical_column):
        return False

    logger.info(
        "\u2713 Semantic validation passed: Orchestrator routes semantic "
        "requests to masked staging data"
    )
    return True


def main() -> int:
    """Run all validations and report results."""
    logger.info("=" * 70)
    logger.info("ORCHESTRATOR HANDSHAKE: Environment Validation for Plan 8")
    logger.info("=" * 70)

    logger.info("")
    logger.info("PHASE 1: ENVIRONMENT VALIDATION")
    logger.info("-" * 70)

    checks = [
        ("Python Version", validate_python_version),
        ("SQLMesh Installation", validate_sqlmesh_installed),
        ("SQLGlot Availability", validate_sqlglot_available),
        ("Project Structure", validate_project_structure),
        ("Manufacturing DB", validate_manufacturing_db),
        ("SQLMesh Context", validate_sqlmesh_context),
    ]

    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
            logger.info("")
        except Exception as e:
            logger.exception(f"\u2717 {name} check raised exception: {e}")
            results[name] = False

    logger.info("=" * 70)
    logger.info("PHASE 1 SUMMARY")
    logger.info("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, result in results.items():
        logger.info(f"{'\u2713 PASS' if result else '\u2717 FAIL'}: {name}")

    logger.info("")
    logger.info(f"Phase 1 Result: {passed}/{total} checks passed")

    if passed != total:
        logger.error("=" * 70)
        logger.error("\u2717 PHASE 1 FAILED: Fix the above issues before proceeding")
        logger.error("=" * 70)
        return 1

    if not validate_semantic_intent_translation():
        logger.error("=" * 70)
        logger.error("\u2717 PHASE 2 FAILED: Semantic validation did not pass")
        logger.error("=" * 70)
        return 1

    logger.info("")
    logger.info("=" * 70)
    logger.info("\u2713 HANDSHAKE SUCCESSFUL: All phases passed")
    logger.info("Environment ready for Plan 8 (Schema Traversal & Masking)")
    logger.info("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
