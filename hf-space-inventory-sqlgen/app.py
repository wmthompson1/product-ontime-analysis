"""
Manufacturing Inventory SQL Generator - Hugging Face Space
MCP-compliant FastAPI server for natural language to SQL conversion

This Space demonstrates:
1. MCP (Model Context Protocol) discovery pattern
2. Natural language to SQL generation for inventory management
3. Schema introspection and query validation
4. Manufacturing domain-specific SQL patterns
"""

import os
import json
import csv
import io
import re
import datetime
import tempfile
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import gradio as gr
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from solder_engine import SolderEngine
from production_dispatcher import ProductionDispatcher

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "app_schema")
QUERIES_DIR = os.path.join(SCHEMA_DIR, "queries")
QUERY_API_KEY = os.environ.get("QUERY_API_KEY", "")
SQLITE_DB_PATH = os.path.join(SCHEMA_DIR, "manufacturing.db")
db_engine = None

def get_db_engine():
    """Get or create SQLite database engine"""
    global db_engine
    if db_engine is None:
        db_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
        init_sqlite_db()
    return db_engine

def init_sqlite_db():
    """Initialize SQLite database from schema file.
    
    Executes both CREATE TABLE and INSERT statements to ensure
    seed data (concepts, perspectives, etc.) is loaded on first run.
    Uses sqlite3 module directly for proper multi-statement handling.
    """
    import sqlite3
    
    schema_file = os.path.join(SCHEMA_DIR, "schema_sqlite.sql")
    if not os.path.exists(schema_file):
        return
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Replace INSERT with INSERT OR IGNORE for idempotent seeding
    schema_sql = schema_sql.replace('INSERT INTO', 'INSERT OR IGNORE INTO')
    
    # Use sqlite3 directly for executescript (handles multi-line statements)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    except Exception as e:
        # Log but don't fail - some statements may already exist
        print(f"Database init warning: {e}")
    finally:
        conn.close()

def get_table_create_sql(table_name: str) -> str:
    """Generate CREATE TABLE SQL for a given table (SQLite version)"""
    engine = get_db_engine()
    if not engine:
        return "-- Database not connected"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=:table_name"), {"table_name": table_name})
            row = result.fetchone()
            if row and row[0]:
                return row[0]
            return f"-- Table '{table_name}' not found"
    except Exception as e:
        return f"-- Error: {str(e)}"

def get_table_create_sql_legacy(table_name: str) -> str:
    """Generate CREATE TABLE SQL for a given table (PostgreSQL version - deprecated)"""
    engine = get_db_engine()
    if not engine:
        return "-- Database not connected"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length, 
                       is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            columns = result.fetchall()
            
            if not columns:
                return f"-- Table '{table_name}' not found"
            
            col_defs = []
            for col in columns:
                col_name, data_type, max_len, nullable, default = col
                type_str = data_type.upper()
                if max_len:
                    type_str = f"{type_str}({max_len})"
                null_str = "" if nullable == "YES" else " NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                col_defs.append(f"    {col_name} {type_str}{null_str}{default_str}")
            
            pk_result = conn.execute(text("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name 
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY' 
                    AND tc.table_schema = 'public'
                    AND tc.table_name = :table_name
                ORDER BY kcu.ordinal_position
            """), {"table_name": table_name})
            pk_cols = [row[0] for row in pk_result.fetchall()]
            
            if pk_cols:
                col_defs.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")
            
            return f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"
    except Exception as e:
        return f"-- Error: {str(e)}"

def get_all_tables() -> List[str]:
    """Get list of all tables in the SQLite database"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        inspector = inspect(engine)
        inspector.clear_cache()
        return inspector.get_table_names()
    except Exception:
        return []

def execute_readonly_sql(sql: str) -> Dict[str, Any]:
    """Execute read-only SQL query (SELECT only)"""
    engine = get_db_engine()
    if not engine:
        return {"error": "Database not connected", "rows": [], "columns": []}
    
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed for safety", "rows": [], "columns": []}
    
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]
    for keyword in dangerous_keywords:
        if keyword in sql_stripped:
            return {"error": f"Query contains forbidden keyword: {keyword}", "rows": [], "columns": []}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(100)]
            return {"error": None, "columns": columns, "rows": rows}
    except SQLAlchemyError as e:
        return {"error": str(e), "rows": [], "columns": []}

def count_queries_in_file(sql_file_path: str) -> int:
    """Count the number of queries in a SQL file by counting '-- Query:' markers"""
    if not os.path.exists(sql_file_path):
        return 0
    try:
        with open(sql_file_path, 'r') as f:
            content = f.read()
        return content.count('-- Query:')
    except Exception:
        return 0

def get_query_categories() -> Dict[str, Any]:
    """Load query index from schema/queries/index.json with dynamic query counts"""
    index_path = os.path.join(QUERIES_DIR, "index.json")
    if not os.path.exists(index_path):
        return {"categories": [], "error": "Query index not found"}
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        for category in index.get("categories", []):
            sql_file = os.path.join(QUERIES_DIR, category["file"])
            category["query_count"] = count_queries_in_file(sql_file)
        
        return index
    except Exception as e:
        return {"categories": [], "error": str(e)}

def get_saved_queries(category_id: str) -> List[Dict[str, str]]:
    """Parse SQL file and extract individual queries with their comments"""
    index = get_query_categories()
    
    category = next((c for c in index.get("categories", []) if c["id"] == category_id), None)
    if not category:
        return []
    
    sql_file = os.path.join(QUERIES_DIR, category["file"])
    if not os.path.exists(sql_file):
        return []
    
    try:
        with open(sql_file, 'r') as f:
            content = f.read()
        
        queries = []
        current_query = {"name": "", "description": "", "sql": "", "binding_key": ""}
        lines = content.split('\n')
        
        for line in lines:
            if line.startswith('-- Query:'):
                if current_query["sql"].strip():
                    queries.append(current_query)
                current_query = {"name": line.replace('-- Query:', '').strip(), "description": "", "sql": "", "binding_key": ""}
            elif line.startswith('-- Description:'):
                current_query["description"] = line.replace('-- Description:', '').strip()
            elif line.startswith('-- Binding:'):
                current_query["binding_key"] = line.replace('-- Binding:', '').strip()
            elif not line.startswith('-- ') and line.strip():
                current_query["sql"] += line + "\n"
        
        if current_query["sql"].strip():
            queries.append(current_query)
        
        return queries
    except Exception:
        return []

def save_query_to_file(category_id: str, query_name: str, description: str, sql: str) -> Dict[str, Any]:
    """Append a new query to the appropriate category file"""
    index = get_query_categories()
    
    category = next((c for c in index.get("categories", []) if c["id"] == category_id), None)
    if not category:
        return {"success": False, "error": f"Category '{category_id}' not found"}
    
    sql_file = os.path.join(QUERIES_DIR, category["file"])
    
    try:
        new_query = f"\n-- Query: {query_name}\n-- Description: {description}\n{sql.strip()}\n"
        
        with open(sql_file, 'a') as f:
            f.write(new_query)
        
        return {"success": True, "message": f"Query '{query_name}' saved to {category['name']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

GROUND_TRUTH_DIR = os.path.join(SCHEMA_DIR, "ground_truth")
GROUND_TRUTH_SQL_DIR = os.path.join(GROUND_TRUTH_DIR, "sql_snippets")
MANIFEST_PATH = os.path.join(GROUND_TRUTH_DIR, "reviewer_manifest.json")


def get_ground_truth_tables() -> List[str]:
    """Extract unique table names referenced in APPROVED ground truth SQL files."""
    if not os.path.exists(MANIFEST_PATH):
        return []

    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)
    except Exception:
        return []

    approved = manifest.get("approved_snippets", {})
    all_tables = set()
    known_tables = set(get_all_tables())

    for entry in approved.values():
        if entry.get("validation_status") != "APPROVED":
            continue
        file_path = entry.get("file_path", "")
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        if not os.path.exists(file_path):
            alt = os.path.join(GROUND_TRUTH_DIR, os.path.basename(file_path))
            if os.path.exists(alt):
                file_path = alt
            else:
                continue
        try:
            with open(file_path, "r") as sf:
                sql_text = sf.read().upper()
            for m in re.finditer(r'\bFROM\s+(\w+)', sql_text):
                tbl = m.group(1).lower()
                if tbl in known_tables:
                    all_tables.add(tbl)
            for m in re.finditer(r'\bJOIN\s+(\w+)', sql_text):
                tbl = m.group(1).lower()
                if tbl in known_tables:
                    all_tables.add(tbl)
        except Exception:
            continue

    return sorted(all_tables)


def _sanitize_slug(value: str) -> str:
    slug = re.sub(r'[^a-z0-9_]', '_', value.lower().strip())
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug or "unknown"


def _auto_concept_from_sql(sql_text: str) -> str:
    """Auto-generate a concept name from SQL when user leaves Concept blank."""
    upper = sql_text.upper()
    from_match = re.search(r'\bFROM\s+(\w+)', upper)
    if from_match:
        table = from_match.group(1)
        select_cols = re.search(r'SELECT\s+(.*?)\s+FROM', upper, re.DOTALL)
        if select_cols:
            cols = select_cols.group(1).strip()
            if cols == "*":
                return f"{table}_OVERVIEW"
            col_parts = []
            for c in cols.split(','):
                part = c.strip().split('.')[-1].split(' ')[-1]
                part = re.sub(r'[^A-Z0-9_]', '', part)
                if part:
                    col_parts.append(part)
            if col_parts and len(col_parts) <= 3:
                return f"{table}_{'_'.join(col_parts)}"
            return f"{table}_QUERY"
        return f"{table}_QUERY"
    return "UNCLASSIFIED"


def save_sme_submission(sql_text: str, category: str, perspective: str, concept: str, justification: str) -> str:
    os.makedirs(GROUND_TRUTH_SQL_DIR, exist_ok=True)

    safe_perspective = _sanitize_slug(perspective)
    safe_concept = _sanitize_slug(concept)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    binding_key = f"{safe_perspective}_{safe_concept}_{timestamp}"
    filename = f"{binding_key}.sql"
    file_path = os.path.join(GROUND_TRUTH_SQL_DIR, filename)

    with open(file_path, "w") as f:
        f.write(sql_text)

    logic_type = "SPATIAL_ALIAS" if "User_Defined" in sql_text else "DIRECT"

    manifest_entry = {
        "concept_anchor": concept.upper(),
        "perspective": perspective,
        "category": category,
        "logic_type": logic_type,
        "file_path": file_path,
        "sme_justification": justification,
        "validation_status": "PENDING",
        "binding_key": binding_key,
        "created_at": datetime.datetime.now().isoformat()
    }

    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, Exception):
            manifest = {"approved_snippets": {}}
    else:
        manifest = {"approved_snippets": {}}

    if "approved_snippets" not in manifest:
        manifest["approved_snippets"] = {}

    manifest["approved_snippets"][binding_key] = manifest_entry
    manifest["last_updated"] = datetime.datetime.now().isoformat()

    tmp_fd, tmp_path = tempfile.mkstemp(dir=GROUND_TRUTH_DIR, suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(manifest, f, indent=4)
        os.replace(tmp_path, MANIFEST_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return f"Saved {filename} and updated Reviewer Manifest. Logic type: {logic_type}. Status: PENDING review."


def resolve_sql_bindings(sql_dir: str = None) -> List[Dict[str, Any]]:
    if sql_dir is None:
        sql_dir = GROUND_TRUTH_SQL_DIR

    bindings = []
    if not os.path.exists(sql_dir):
        return bindings

    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r") as f:
                manifest = json.load(f)
        except Exception:
            pass

    approved_snippets = manifest.get("approved_snippets", {})

    for filename in sorted(os.listdir(sql_dir)):
        if not filename.endswith(".sql"):
            continue

        binding_key = filename.replace(".sql", "")
        file_path = os.path.join(sql_dir, filename)

        entry = approved_snippets.get(binding_key, {})

        bindings.append({
            "filename": filename,
            "binding_key": binding_key,
            "perspective": entry.get("perspective", ""),
            "concept": entry.get("concept_anchor", ""),
            "category": entry.get("category", ""),
            "justification": entry.get("sme_justification", ""),
            "validation_status": entry.get("validation_status", "UNKNOWN"),
            "created_at": entry.get("created_at", ""),
            "path": file_path
        })

    return bindings


def get_manifest_summary() -> Dict[str, Any]:
    if not os.path.exists(MANIFEST_PATH):
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "bindings": []}

    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)
    except Exception:
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "bindings": []}

    snippets = manifest.get("approved_snippets", {})
    bindings_list = list(snippets.values())
    return {
        "total": len(bindings_list),
        "pending": sum(1 for b in bindings_list if b.get("validation_status") == "PENDING"),
        "approved": sum(1 for b in bindings_list if b.get("validation_status") == "APPROVED"),
        "rejected": sum(1 for b in bindings_list if b.get("validation_status") == "REJECTED"),
        "bindings": bindings_list
    }


CATEGORY_MAP = {
    "Quality": "quality_control",
    "Inventory": "production_analytics",
    "Delivery": "supplier_performance",
    "Financial": "production_analytics",
    "Production": "production_analytics",
}

REVERSE_CATEGORY_MAP = {v: k for k, v in CATEGORY_MAP.items()}


def _ensure_manifest_entry(query_name: str, sql_text: str, description: str, category_id: str) -> str:
    """Reverse bridge: create a PENDING manifest entry for a Ground Truth query that has no binding key."""
    safe_name = _sanitize_slug(query_name)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    binding_key = f"gt_{safe_name}_{timestamp}"
    filename = f"{binding_key}.sql"
    file_path = os.path.join(GROUND_TRUTH_SQL_DIR, filename)

    os.makedirs(GROUND_TRUTH_SQL_DIR, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(sql_text.strip())

    category_label = REVERSE_CATEGORY_MAP.get(category_id, category_id)
    logic_type = "SPATIAL_ALIAS" if "User_Defined" in sql_text else "DIRECT"

    manifest_entry = {
        "concept_anchor": safe_name.upper(),
        "perspective": "Pending",
        "category": category_label,
        "logic_type": logic_type,
        "file_path": file_path,
        "sme_justification": f"Auto-created from Ground Truth: {query_name} — {description}",
        "validation_status": "PENDING",
        "binding_key": binding_key,
        "created_at": datetime.datetime.now().isoformat()
    }

    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, Exception):
            manifest = {"approved_snippets": {}}
    else:
        manifest = {"approved_snippets": {}}

    if "approved_snippets" not in manifest:
        manifest["approved_snippets"] = {}

    manifest["approved_snippets"][binding_key] = manifest_entry
    manifest["last_updated"] = datetime.datetime.now().isoformat()

    tmp_fd, tmp_path = tempfile.mkstemp(dir=GROUND_TRUTH_DIR, suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(manifest, f, indent=4)
        os.replace(tmp_path, MANIFEST_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    _inject_binding_tag(query_name, binding_key, category_id)

    return binding_key


def _inject_binding_tag(query_name: str, binding_key: str, category_id: str):
    """Inject a -- Binding: tag into the category .sql file so subsequent loads find it directly."""
    index = get_query_categories()
    category = next((c for c in index.get("categories", []) if c["id"] == category_id), None)
    if not category:
        return
    sql_file = os.path.join(QUERIES_DIR, category["file"])
    if not os.path.exists(sql_file):
        return
    with open(sql_file, "r") as f:
        content = f.read()
    marker = f"-- Query: {query_name}"
    if marker not in content:
        return
    if f"-- Binding: {binding_key}" in content:
        return
    patched = content.replace(marker, f"{marker}\n-- Binding: {binding_key}")
    with open(sql_file, "w") as f:
        f.write(patched)


def _append_to_category_file(entry: Dict[str, Any], binding_key: str) -> str:
    category_name = entry.get("category", "")
    category_id = CATEGORY_MAP.get(category_name, "")
    if not category_id:
        category_id = CATEGORY_MAP.get(category_name.title(), "")
    if not category_id:
        return f"No category mapping for '{category_name}'"

    index = get_query_categories()
    category = next((c for c in index.get("categories", []) if c["id"] == category_id), None)
    if not category:
        return f"Category '{category_id}' not found in index"

    sql_file = os.path.join(QUERIES_DIR, category["file"])

    concept = entry.get("concept_anchor", binding_key)
    perspective = entry.get("perspective", "")
    query_name = f"{concept} ({perspective})"
    justification = entry.get("sme_justification", "SME-approved query")

    if os.path.exists(sql_file):
        with open(sql_file, "r") as f:
            existing = f.read()
        if binding_key in existing or f"-- Query: {query_name}" in existing:
            return f"Already in {category['name']} (skipped duplicate)"

    file_path = entry.get("file_path", "")
    candidates = [
        file_path,
        os.path.join(GROUND_TRUTH_SQL_DIR, os.path.basename(file_path)),
        os.path.join(GROUND_TRUTH_SQL_DIR, f"{binding_key}.sql"),
        os.path.join(GROUND_TRUTH_DIR, os.path.basename(file_path)),
        os.path.join(GROUND_TRUTH_DIR, f"{binding_key}.sql"),
    ]

    sql_text = ""
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            with open(candidate, "r") as f:
                sql_text = f.read().strip()
            break

    if not sql_text:
        return f"Could not find SQL file for {binding_key}"

    new_entry = f"\n\n-- Query: {query_name}\n-- Description: {justification}\n-- Binding: {binding_key}\n{sql_text}\n"

    with open(sql_file, "a") as f:
        f.write(new_entry)

    return f"Added to {category['name']} category"


def update_binding_status(binding_key: str, new_status: str) -> str:
    if not os.path.exists(MANIFEST_PATH):
        return "Manifest file not found."

    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)
    except Exception as e:
        return f"Error reading manifest: {e}"

    snippets = manifest.get("approved_snippets", {})

    if binding_key not in snippets:
        return f"Binding key '{binding_key}' not found in manifest."

    snippets[binding_key]["validation_status"] = new_status
    snippets[binding_key]["reviewed_at"] = datetime.datetime.now().isoformat()
    manifest["last_updated"] = datetime.datetime.now().isoformat()

    tmp_fd, tmp_path = tempfile.mkstemp(dir=GROUND_TRUTH_DIR, suffix=".json")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(manifest, f, indent=4)
        os.replace(tmp_path, MANIFEST_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    category_msg = ""
    if new_status == "APPROVED":
        category_msg = _append_to_category_file(snippets[binding_key], binding_key)
        if category_msg:
            category_msg = f" | {category_msg}"

    return f"Updated '{binding_key}' to {new_status}.{category_msg}"


app = FastAPI(
    title="Manufacturing Inventory SQL Generator",
    description="MCP-compliant natural language to SQL for inventory management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_SCHEMA = {
    "tables": {
        "inventory": {
            "columns": {
                "part_id": {"type": "VARCHAR(50)", "primary_key": True, "description": "Unique part identifier"},
                "part_name": {"type": "VARCHAR(200)", "description": "Part name/description"},
                "category": {"type": "VARCHAR(100)", "description": "Part category (raw_material, component, finished_good)"},
                "quantity_on_hand": {"type": "INTEGER", "description": "Current stock quantity"},
                "reorder_point": {"type": "INTEGER", "description": "Minimum quantity before reorder"},
                "unit_cost": {"type": "DECIMAL(10,2)", "description": "Cost per unit in USD"},
                "supplier_id": {"type": "VARCHAR(50)", "description": "Primary supplier ID"},
                "warehouse_location": {"type": "VARCHAR(50)", "description": "Warehouse bin location"},
                "last_updated": {"type": "TIMESTAMP", "description": "Last inventory update timestamp"}
            }
        },
        "suppliers": {
            "columns": {
                "supplier_id": {"type": "VARCHAR(50)", "primary_key": True, "description": "Unique supplier identifier"},
                "supplier_name": {"type": "VARCHAR(200)", "description": "Supplier company name"},
                "lead_time_days": {"type": "INTEGER", "description": "Average lead time in days"},
                "quality_rating": {"type": "DECIMAL(3,2)", "description": "Quality score 0.00-5.00"},
                "on_time_delivery_rate": {"type": "DECIMAL(5,2)", "description": "On-time delivery percentage"}
            }
        },
        "transactions": {
            "columns": {
                "transaction_id": {"type": "SERIAL", "primary_key": True, "description": "Auto-increment transaction ID"},
                "part_id": {"type": "VARCHAR(50)", "foreign_key": "inventory.part_id", "description": "Part being transacted"},
                "transaction_type": {"type": "VARCHAR(20)", "description": "Type: receipt, issue, adjustment, transfer"},
                "quantity": {"type": "INTEGER", "description": "Quantity transacted (positive or negative)"},
                "transaction_date": {"type": "TIMESTAMP", "description": "When transaction occurred"},
                "reference_number": {"type": "VARCHAR(100)", "description": "PO number, work order, etc."}
            }
        }
    },
    "relationships": [
        {"from": "inventory.supplier_id", "to": "suppliers.supplier_id", "type": "many-to-one"},
        {"from": "transactions.part_id", "to": "inventory.part_id", "type": "many-to-one"}
    ]
}

SQL_TEMPLATES = {
    "low_stock": """SELECT part_id, part_name, quantity_on_hand, reorder_point,
       (reorder_point - quantity_on_hand) AS units_below_reorder
FROM inventory
WHERE quantity_on_hand < reorder_point
ORDER BY units_below_reorder DESC;""",
    
    "inventory_value": """SELECT category,
       COUNT(*) AS part_count,
       SUM(quantity_on_hand) AS total_units,
       SUM(quantity_on_hand * unit_cost) AS total_value
FROM inventory
GROUP BY category
ORDER BY total_value DESC;""",
    
    "supplier_performance": """SELECT s.supplier_name,
       s.quality_rating,
       s.on_time_delivery_rate,
       COUNT(DISTINCT i.part_id) AS parts_supplied
FROM suppliers s
LEFT JOIN inventory i ON s.supplier_id = i.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.quality_rating, s.on_time_delivery_rate
ORDER BY s.quality_rating DESC;""",
    
    "transaction_summary": """SELECT DATE(transaction_date) AS txn_date,
       transaction_type,
       COUNT(*) AS transaction_count,
       SUM(ABS(quantity)) AS total_units
FROM transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(transaction_date), transaction_type
ORDER BY txn_date DESC, transaction_type;"""
}

class MCPToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]

class MCPDiscoveryResponse(BaseModel):
    name: str
    version: str
    description: str
    tools: List[MCPToolDefinition]
    resources: List[Dict[str, Any]]
    prompts: List[Dict[str, Any]]

class SQLGenerationRequest(BaseModel):
    query: str = Field(..., description="Natural language query to convert to SQL")
    include_explanation: bool = Field(default=True, description="Include explanation of generated SQL")

class SQLGenerationResponse(BaseModel):
    sql: str
    explanation: Optional[str] = None
    tables_used: List[str]
    estimated_complexity: str

class SchemaUploadRequest(BaseModel):
    schema_definition: str = Field(..., description="JSON schema definition")

def analyze_query_intent(query: str) -> Dict[str, Any]:
    """Analyze natural language query to determine SQL intent"""
    query_lower = query.lower()
    
    intent = {
        "action": "select",
        "tables": [],
        "aggregation": False,
        "filtering": False,
        "sorting": False,
        "grouping": False,
        "keywords": []
    }
    
    if any(word in query_lower for word in ["count", "total", "sum", "average", "avg", "how many"]):
        intent["aggregation"] = True
        intent["keywords"].append("aggregation")
    
    if any(word in query_lower for word in ["low", "below", "under", "less than", "shortage", "reorder"]):
        intent["filtering"] = True
        intent["keywords"].append("threshold_filter")
    
    if any(word in query_lower for word in ["top", "highest", "lowest", "best", "worst", "rank"]):
        intent["sorting"] = True
        intent["keywords"].append("ranking")
    
    if any(word in query_lower for word in ["by category", "by supplier", "per warehouse", "group by", "breakdown"]):
        intent["grouping"] = True
        intent["keywords"].append("grouping")
    
    if any(word in query_lower for word in ["inventory", "stock", "part", "quantity", "warehouse"]):
        intent["tables"].append("inventory")
    if any(word in query_lower for word in ["supplier", "vendor", "lead time", "quality rating"]):
        intent["tables"].append("suppliers")
    if any(word in query_lower for word in ["transaction", "receipt", "issue", "transfer", "movement"]):
        intent["tables"].append("transactions")
    
    if not intent["tables"]:
        intent["tables"] = ["inventory"]
    
    return intent

def generate_sql_from_intent(query: str, intent: Dict[str, Any]) -> SQLGenerationResponse:
    """Generate SQL based on analyzed intent"""
    query_lower = query.lower()
    
    if "low stock" in query_lower or "below reorder" in query_lower or "need to reorder" in query_lower:
        return SQLGenerationResponse(
            sql=SQL_TEMPLATES["low_stock"],
            explanation="This query identifies parts where current stock is below the reorder point, "
                       "sorted by urgency (how far below reorder point).",
            tables_used=["inventory"],
            estimated_complexity="simple"
        )
    
    if "inventory value" in query_lower or "total value" in query_lower or "worth" in query_lower:
        return SQLGenerationResponse(
            sql=SQL_TEMPLATES["inventory_value"],
            explanation="Calculates total inventory value by category, showing part counts, "
                       "total units, and monetary value.",
            tables_used=["inventory"],
            estimated_complexity="moderate"
        )
    
    if "supplier" in query_lower and ("performance" in query_lower or "rating" in query_lower or "quality" in query_lower):
        return SQLGenerationResponse(
            sql=SQL_TEMPLATES["supplier_performance"],
            explanation="Shows supplier performance metrics including quality rating, "
                       "on-time delivery rate, and number of parts supplied.",
            tables_used=["suppliers", "inventory"],
            estimated_complexity="moderate"
        )
    
    if "transaction" in query_lower or "movement" in query_lower or "activity" in query_lower:
        return SQLGenerationResponse(
            sql=SQL_TEMPLATES["transaction_summary"],
            explanation="Summarizes inventory transactions over the last 30 days, "
                       "grouped by date and transaction type.",
            tables_used=["transactions"],
            estimated_complexity="moderate"
        )
    
    tables = intent["tables"]
    main_table = tables[0] if tables else "inventory"
    
    if intent["aggregation"] and intent["grouping"]:
        if main_table == "inventory":
            sql = """SELECT category,
       COUNT(*) AS part_count,
       SUM(quantity_on_hand) AS total_quantity,
       AVG(unit_cost) AS avg_unit_cost
FROM inventory
GROUP BY category
ORDER BY total_quantity DESC;"""
            explanation = "Aggregates inventory data by category with counts and totals."
        else:
            sql = f"SELECT * FROM {main_table} LIMIT 100;"
            explanation = f"Basic query on {main_table} table."
    
    elif intent["filtering"]:
        sql = """SELECT part_id, part_name, quantity_on_hand, reorder_point
FROM inventory
WHERE quantity_on_hand < reorder_point
ORDER BY quantity_on_hand ASC;"""
        explanation = "Filters inventory for items needing attention based on stock levels."
    
    elif intent["sorting"]:
        sql = """SELECT part_id, part_name, quantity_on_hand, unit_cost,
       (quantity_on_hand * unit_cost) AS total_value
FROM inventory
ORDER BY total_value DESC
LIMIT 20;"""
        explanation = "Returns top items sorted by total inventory value."
    
    else:
        sql = f"""SELECT *
FROM {main_table}
LIMIT 100;"""
        explanation = f"Basic select query on {main_table} table. Refine your question for more specific results."
    
    complexity = "simple"
    if len(tables) > 1 or intent["aggregation"]:
        complexity = "moderate"
    if len(tables) > 2 or (intent["aggregation"] and intent["grouping"]):
        complexity = "complex"
    
    return SQLGenerationResponse(
        sql=sql,
        explanation=explanation,
        tables_used=tables,
        estimated_complexity=complexity
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main Gradio interface"""
    return """
    <html>
        <head>
            <title>Manufacturing Inventory SQL Generator</title>
            <meta http-equiv="refresh" content="0; url=/gradio" />
        </head>
        <body>
            <p>Redirecting to <a href="/gradio">Gradio Interface</a>...</p>
        </body>
    </html>
    """


@app.get("/mcp/discover", response_model=MCPDiscoveryResponse)
async def mcp_discover():
    """MCP Discovery endpoint - returns available tools and capabilities"""
    return MCPDiscoveryResponse(
        name="manufacturing-inventory-sqlgen",
        version="1.0.0",
        description="Natural language to SQL generator for manufacturing inventory management",
        tools=[
            MCPToolDefinition(
                name="generate_sql",
                description="Convert natural language query to SQL for inventory database",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query about inventory"
                        },
                        "include_explanation": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include explanation of generated SQL"
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPToolDefinition(
                name="get_schema",
                description="Get the database schema for inventory tables",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            MCPToolDefinition(
                name="get_sql_templates",
                description="Get pre-built SQL templates for common inventory queries",
                input_schema={
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "enum": ["low_stock", "inventory_value", "supplier_performance", "transaction_summary"],
                            "description": "Name of the SQL template"
                        }
                    },
                    "required": []
                }
            ),
            MCPToolDefinition(
                name="analyze_csv",
                description="Analyze uploaded CSV to suggest schema and queries",
                input_schema={
                    "type": "object",
                    "properties": {
                        "csv_content": {
                            "type": "string",
                            "description": "CSV file content as string"
                        }
                    },
                    "required": ["csv_content"]
                }
            ),
            MCPToolDefinition(
                name="get_db_tables",
                description="Get list of all tables from connected PostgreSQL database",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            MCPToolDefinition(
                name="get_table_ddl",
                description="Get CREATE TABLE SQL for a specific table",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to get DDL for"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            MCPToolDefinition(
                name="get_all_ddl",
                description="Get CREATE TABLE SQL for all tables in the database",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            MCPToolDefinition(
                name="execute_sql",
                description="Execute read-only SQL query (SELECT only) against the database",
                input_schema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT query to execute"
                        }
                    },
                    "required": ["sql"]
                }
            )
        ],
        resources=[
            {
                "uri": "schema://inventory",
                "name": "Inventory Schema",
                "description": "Database schema for inventory management tables",
                "mimeType": "application/json"
            }
        ],
        prompts=[
            {
                "name": "inventory_query",
                "description": "Template for inventory-related queries",
                "arguments": [
                    {"name": "question", "description": "The inventory question to answer", "required": True}
                ]
            }
        ]
    )


@app.post("/mcp/tools/generate_sql", response_model=SQLGenerationResponse)
async def generate_sql(request: SQLGenerationRequest):
    """Generate SQL from natural language query"""
    intent = analyze_query_intent(request.query)
    response = generate_sql_from_intent(request.query, intent)
    
    if not request.include_explanation:
        response.explanation = None
    
    return response


@app.get("/mcp/tools/get_schema")
async def get_schema():
    """Return the database schema"""
    return {"schema": SAMPLE_SCHEMA}


@app.get("/mcp/tools/get_sql_templates")
async def get_sql_templates(template_name: Optional[str] = None):
    """Return SQL templates for common queries"""
    if template_name:
        if template_name not in SQL_TEMPLATES:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        return {"template_name": template_name, "sql": SQL_TEMPLATES[template_name]}
    return {"templates": SQL_TEMPLATES}


@app.post("/mcp/tools/analyze_csv")
async def analyze_csv(csv_content: str = Form(...)):
    """Analyze CSV content and suggest schema"""
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        if not rows:
            return {"error": "Empty CSV file"}
        
        columns = list(rows[0].keys())
        
        column_analysis = {}
        for col in columns:
            values = [row[col] for row in rows if row[col]]
            
            col_type = "VARCHAR(255)"
            if all(v.isdigit() for v in values[:10] if v):
                col_type = "INTEGER"
            elif all(v.replace(".", "").replace("-", "").isdigit() for v in values[:10] if v):
                col_type = "DECIMAL(10,2)"
            
            column_analysis[col] = {
                "suggested_type": col_type,
                "sample_values": values[:3],
                "non_null_count": len(values)
            }
        
        return {
            "row_count": len(rows),
            "columns": column_analysis,
            "suggested_queries": [
                f"SELECT * FROM uploaded_data LIMIT 10;",
                f"SELECT COUNT(*) FROM uploaded_data;",
                f"SELECT {columns[0]}, COUNT(*) FROM uploaded_data GROUP BY {columns[0]};" if columns else ""
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


@app.get("/mcp/tools/get_db_tables")
async def get_db_tables():
    """Get list of all tables from connected PostgreSQL database"""
    tables = get_all_tables()
    if not tables:
        return {"error": "Database not connected or no tables found", "tables": []}
    return {"tables": tables, "count": len(tables)}


@app.get("/mcp/tools/get_table_ddl")
async def get_table_ddl(table_name: str):
    """Get CREATE TABLE SQL for a specific table"""
    sql = get_table_create_sql(table_name)
    return {"table_name": table_name, "ddl": sql}


@app.get("/mcp/tools/get_all_ddl")
async def get_all_ddl():
    """Get CREATE TABLE SQL for all tables in the database"""
    tables = get_all_tables()
    if not tables:
        return {"error": "Database not connected or no tables found", "ddl": {}}
    
    ddl_statements = {}
    for table in tables:
        ddl_statements[table] = get_table_create_sql(table)
    
    return {"tables": tables, "ddl": ddl_statements}


@app.post("/mcp/tools/execute_sql")
async def execute_sql_endpoint(sql: str = Form(...)):
    """Execute read-only SQL query against the database"""
    result = execute_readonly_sql(sql)
    return result


@app.get("/mcp/tools/get_saved_categories")
async def get_saved_categories():
    """Get list of saved query categories"""
    return get_query_categories()


@app.get("/mcp/tools/get_saved_queries")
async def get_saved_queries_endpoint(category_id: str):
    """Get saved queries for a specific category"""
    queries = get_saved_queries(category_id)
    return {"category_id": category_id, "queries": queries, "count": len(queries)}


class SaveQueryRequest(BaseModel):
    category_id: str = Field(..., description="Category to save the query to")
    query_name: str = Field(..., description="Name of the query")
    description: str = Field(..., description="Description of what the query does")
    sql: str = Field(..., description="The SQL query")


@app.post("/mcp/tools/save_query")
async def save_query_endpoint(
    request: SaveQueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """Save a validated SQL query from the Flask app (ground truth).
    
    Requires X-API-Key header for authentication. Set QUERY_API_KEY env var.
    """
    if not QUERY_API_KEY:
        raise HTTPException(
            status_code=503, 
            detail="Query save endpoint not configured. Set QUERY_API_KEY environment variable."
        )
    
    if not x_api_key or x_api_key != QUERY_API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing API key. Include X-API-Key header."
        )
    
    result = save_query_to_file(
        request.category_id,
        request.query_name,
        request.description,
        request.sql
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# =============================================================================
# SEMANTIC LAYER: Concept, Perspective, and Intent Endpoints
# =============================================================================

@app.get("/mcp/tools/get_concepts")
async def get_concepts(domain: Optional[str] = None, concept_type: Optional[str] = None):
    """Get all schema concepts, optionally filtered by domain or type.
    
    Concepts represent multiple possible interpretations of ambiguous fields.
    Domains: quality, finance, operations, compliance, customer
    Types: state, metric, classification, outcome
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            query = "SELECT concept_id, concept_name, concept_type, description, domain FROM schema_concepts WHERE 1=1"
            params = {}
            if domain:
                query += " AND domain = :domain"
                params["domain"] = domain
            if concept_type:
                query += " AND concept_type = :concept_type"
                params["concept_type"] = concept_type
            query += " ORDER BY domain, concept_name"
            
            result = conn.execute(text(query), params)
            concepts = [
                {"concept_id": r[0], "concept_name": r[1], "concept_type": r[2], 
                 "description": r[3], "domain": r[4]}
                for r in result.fetchall()
            ]
            return {"concepts": concepts, "count": len(concepts)}
    except Exception as e:
        return {"error": str(e), "concepts": [], "count": 0}


@app.get("/mcp/tools/get_field_concepts")
async def get_field_concepts(table_name: Optional[str] = None, field_name: Optional[str] = None):
    """Get concept mappings for ambiguous fields (CAN_MEAN relationships).
    
    Shows how the same field can have multiple interpretations based on context.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            query = """
                SELECT cf.table_name, cf.field_name, cf.is_primary_meaning, cf.context_hint,
                       c.concept_id, c.concept_name, c.concept_type, c.description, c.domain
                FROM schema_concept_fields cf
                JOIN schema_concepts c ON cf.concept_id = c.concept_id
                WHERE 1=1
            """
            params = {}
            if table_name:
                query += " AND cf.table_name = :table_name"
                params["table_name"] = table_name
            if field_name:
                query += " AND cf.field_name = :field_name"
                params["field_name"] = field_name
            query += " ORDER BY cf.table_name, cf.field_name, cf.is_primary_meaning DESC"
            
            result = conn.execute(text(query), params)
            mappings = [
                {
                    "table_name": r[0], "field_name": r[1], 
                    "is_primary": bool(r[2]), "context_hint": r[3],
                    "concept": {
                        "concept_id": r[4], "concept_name": r[5],
                        "concept_type": r[6], "description": r[7], "domain": r[8]
                    }
                }
                for r in result.fetchall()
            ]
            return {"field_concepts": mappings, "count": len(mappings)}
    except Exception as e:
        return {"error": str(e), "field_concepts": [], "count": 0}


@app.get("/mcp/tools/get_ambiguous_fields")
async def get_ambiguous_fields():
    """Get list of fields that have multiple concept interpretations.
    
    These are the fields where perspective/intent matters for correct interpretation.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT cf.table_name, cf.field_name, COUNT(*) as concept_count,
                       GROUP_CONCAT(c.concept_name, ', ') as concepts,
                       GROUP_CONCAT(c.domain, ', ') as domains
                FROM schema_concept_fields cf
                JOIN schema_concepts c ON cf.concept_id = c.concept_id
                GROUP BY cf.table_name, cf.field_name
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
            """))
            fields = [
                {
                    "table_name": r[0], "field_name": r[1], 
                    "concept_count": r[2], "concepts": r[3], "domains": r[4]
                }
                for r in result.fetchall()
            ]
            return {"ambiguous_fields": fields, "count": len(fields)}
    except Exception as e:
        return {"error": str(e), "ambiguous_fields": [], "count": 0}


@app.get("/mcp/tools/get_perspectives")
async def get_perspectives():
    """Get all organizational perspectives.
    
    Perspectives are viewpoints that constrain which concept interpretations are valid.
    Each perspective represents a stakeholder group with specific priorities.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT perspective_id, perspective_name, description, 
                       stakeholder_role, priority_focus
                FROM schema_perspectives
                ORDER BY perspective_name
            """))
            perspectives = [
                {
                    "perspective_id": r[0], "perspective_name": r[1],
                    "description": r[2], "stakeholder_role": r[3],
                    "priority_focus": r[4]
                }
                for r in result.fetchall()
            ]
            return {"perspectives": perspectives, "count": len(perspectives)}
    except Exception as e:
        return {"error": str(e), "perspectives": [], "count": 0}


@app.get("/mcp/tools/get_perspective_concepts")
async def get_perspective_concepts(perspective_name: Optional[str] = None):
    """Get concepts used by each perspective (USES_DEFINITION relationships).
    
    Shows which concept interpretations are valid for each organizational perspective.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            query = """
                SELECT p.perspective_name, p.description, p.stakeholder_role,
                       pc.relationship_type, pc.priority_weight,
                       c.concept_id, c.concept_name, c.concept_type, c.description as concept_desc, c.domain
                FROM schema_perspectives p
                JOIN schema_perspective_concepts pc ON p.perspective_id = pc.perspective_id
                JOIN schema_concepts c ON pc.concept_id = c.concept_id
                WHERE 1=1
            """
            params = {}
            if perspective_name:
                query += " AND p.perspective_name = :perspective_name"
                params["perspective_name"] = perspective_name
            query += " ORDER BY p.perspective_name, pc.priority_weight DESC"
            
            result = conn.execute(text(query), params)
            mappings = [
                {
                    "perspective": r[0], "perspective_desc": r[1], 
                    "stakeholder_role": r[2], "relationship_type": r[3],
                    "priority_weight": r[4],
                    "concept": {
                        "concept_id": r[5], "concept_name": r[6],
                        "concept_type": r[7], "description": r[8], "domain": r[9]
                    }
                }
                for r in result.fetchall()
            ]
            return {"perspective_concepts": mappings, "count": len(mappings)}
    except Exception as e:
        return {"error": str(e), "perspective_concepts": [], "count": 0}


@app.get("/mcp/tools/resolve_field_for_perspective")
async def resolve_field_for_perspective(table_name: str, field_name: str, perspective_name: str):
    """Resolve which concept interpretation applies for a field given a perspective.
    
    This is the semantic disambiguation endpoint - given a perspective, it returns
    the correct interpretation of an ambiguous field.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT c.concept_id, c.concept_name, c.concept_type, c.description, c.domain,
                       cf.context_hint, pc.priority_weight
                FROM schema_concept_fields cf
                JOIN schema_concepts c ON cf.concept_id = c.concept_id
                JOIN schema_perspective_concepts pc ON c.concept_id = pc.concept_id
                JOIN schema_perspectives p ON pc.perspective_id = p.perspective_id
                WHERE cf.table_name = :table_name 
                  AND cf.field_name = :field_name
                  AND p.perspective_name = :perspective_name
                ORDER BY pc.priority_weight DESC
                LIMIT 1
            """), {"table_name": table_name, "field_name": field_name, "perspective_name": perspective_name})
            
            row = result.fetchone()
            if row:
                return {
                    "resolved": True,
                    "table_name": table_name,
                    "field_name": field_name,
                    "perspective": perspective_name,
                    "concept": {
                        "concept_id": row[0], "concept_name": row[1],
                        "concept_type": row[2], "description": row[3], 
                        "domain": row[4], "context_hint": row[5],
                        "priority_weight": row[6]
                    }
                }
            else:
                return {
                    "resolved": False,
                    "table_name": table_name,
                    "field_name": field_name,
                    "perspective": perspective_name,
                    "message": "No concept mapping found for this field/perspective combination"
                }
    except Exception as e:
        return {"error": str(e), "resolved": False}


@app.get("/mcp/tools/get_intents")
async def get_intents(category: Optional[str] = None):
    """Get all analytical intents, optionally filtered by category.
    
    Intents are analytical goals that binary-switch concept weights.
    Each intent elevates one field interpretation to 1.0 while suppressing alternatives to 0.0.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            query = """
                SELECT intent_id, intent_name, intent_category, description, typical_question
                FROM schema_intents
                WHERE 1=1
            """
            params = {}
            if category:
                query += " AND intent_category = :category"
                params["category"] = category
            query += " ORDER BY intent_category, intent_name"
            
            result = conn.execute(text(query), params)
            intents = [
                {
                    "intent_id": r[0], "intent_name": r[1],
                    "intent_category": r[2], "description": r[3],
                    "typical_question": r[4]
                }
                for r in result.fetchall()
            ]
            return {"intents": intents, "count": len(intents)}
    except Exception as e:
        return {"error": str(e), "intents": [], "count": 0}


@app.get("/mcp/tools/get_intent_weights")
async def get_intent_weights(intent_name: str):
    """Get concept weights for a specific intent (the binary elevation/suppression).
    
    Returns which concepts are elevated (1.0) vs suppressed (0.0) for this intent.
    This is the core disambiguation mechanism - intent determines which interpretation wins.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT i.intent_name, i.description, i.typical_question,
                       ic.intent_factor_weight, ic.explanation,
                       c.concept_id, c.concept_name, c.concept_type, c.description as concept_desc, c.domain
                FROM schema_intents i
                JOIN schema_intent_concepts ic ON i.intent_id = ic.intent_id
                JOIN schema_concepts c ON ic.concept_id = c.concept_id
                WHERE i.intent_name = :intent_name
                ORDER BY ic.intent_factor_weight DESC, c.concept_name
            """), {"intent_name": intent_name})
            
            rows = result.fetchall()
            if not rows:
                return {"error": f"Intent '{intent_name}' not found", "weights": []}
            
            weights = [
                {
                    "intent_factor_weight": r[3],
                    "status": "ELEVATED" if r[3] == 1.0 else "SUPPRESSED",
                    "explanation": r[4],
                    "concept": {
                        "concept_id": r[5], "concept_name": r[6],
                        "concept_type": r[7], "description": r[8], "domain": r[9]
                    }
                }
                for r in rows
            ]
            
            return {
                "intent_name": rows[0][0],
                "description": rows[0][1],
                "typical_question": rows[0][2],
                "weights": weights,
                "elevated_count": sum(1 for w in weights if w["intent_factor_weight"] == 1.0),
                "suppressed_count": sum(1 for w in weights if w["intent_factor_weight"] == 0.0)
            }
    except Exception as e:
        return {"error": str(e), "weights": []}


@app.get("/mcp/tools/get_intent_queries")
async def get_intent_queries(intent_name: Optional[str] = None):
    """Get ground truth SQL queries linked to intents.
    
    Maps intents to validated SQL examples that demonstrate the correct interpretation.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            query = """
                SELECT i.intent_name, i.intent_category, i.description,
                       iq.query_category, iq.query_file, iq.query_index, iq.query_name
                FROM schema_intents i
                JOIN schema_intent_queries iq ON i.intent_id = iq.intent_id
                WHERE 1=1
            """
            params = {}
            if intent_name:
                query += " AND i.intent_name = :intent_name"
                params["intent_name"] = intent_name
            query += " ORDER BY i.intent_category, i.intent_name"
            
            result = conn.execute(text(query), params)
            queries = [
                {
                    "intent_name": r[0], "intent_category": r[1], "intent_description": r[2],
                    "query_category": r[3], "query_file": r[4], 
                    "query_index": r[5], "query_name": r[6]
                }
                for r in result.fetchall()
            ]
            return {"intent_queries": queries, "count": len(queries)}
    except Exception as e:
        return {"error": str(e), "intent_queries": [], "count": 0}


@app.get("/mcp/tools/resolve_field_for_intent")
async def resolve_field_for_intent(table_name: str, field_name: str, intent_name: str):
    """Resolve which concept interpretation applies for a field given an intent.
    
    This is the intent-based semantic disambiguation endpoint.
    Unlike perspective (which uses priority weights), intent uses binary elevation:
    - 1.0 = this interpretation is THE correct one for this intent
    - 0.0 = this interpretation should be ignored for this intent
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT c.concept_id, c.concept_name, c.concept_type, c.description, c.domain,
                       cf.context_hint, ic.intent_factor_weight, ic.explanation,
                       i.typical_question
                FROM schema_concept_fields cf
                JOIN schema_concepts c ON cf.concept_id = c.concept_id
                JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
                JOIN schema_intents i ON ic.intent_id = i.intent_id
                WHERE cf.table_name = :table_name 
                  AND cf.field_name = :field_name
                  AND i.intent_name = :intent_name
                  AND ic.intent_factor_weight = 1.0
                LIMIT 1
            """), {"table_name": table_name, "field_name": field_name, "intent_name": intent_name})
            
            row = result.fetchone()
            if row:
                return {
                    "resolved": True,
                    "table_name": table_name,
                    "field_name": field_name,
                    "intent": intent_name,
                    "typical_question": row[8],
                    "concept": {
                        "concept_id": row[0], "concept_name": row[1],
                        "concept_type": row[2], "description": row[3], 
                        "domain": row[4], "context_hint": row[5],
                        "intent_factor_weight": row[6], 
                        "explanation": row[7]
                    }
                }
            else:
                return {
                    "resolved": False,
                    "table_name": table_name,
                    "field_name": field_name,
                    "intent": intent_name,
                    "message": "No elevated concept found for this field/intent combination"
                }
    except Exception as e:
        return {"error": str(e), "resolved": False}


@app.get("/mcp/tools/get_intent_perspectives")
async def get_intent_perspectives(intent_name: Optional[str] = None):
    """Get OPERATES_WITHIN relationships (Intent → Perspective).
    
    Shows which perspective(s) each intent operates within.
    This is the intermediate constraint layer in the graph traversal:
    Intent -[OPERATES_WITHIN]-> Perspective -[USES_DEFINITION]-> Concept
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            query = """
                SELECT i.intent_name, i.intent_category, i.description as intent_desc,
                       ip.intent_factor_weight, ip.explanation,
                       p.perspective_id, p.perspective_name, p.description as perspective_desc,
                       p.stakeholder_role
                FROM schema_intents i
                JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id
                JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
                WHERE ip.intent_factor_weight = 1.0
            """
            params = {}
            if intent_name:
                query += " AND i.intent_name = :intent_name"
                params["intent_name"] = intent_name
            query += " ORDER BY i.intent_category, i.intent_name"
            
            result = conn.execute(text(query), params)
            mappings = [
                {
                    "intent_name": r[0], "intent_category": r[1], 
                    "intent_description": r[2],
                    "relationship": "OPERATES_WITHIN",
                    "intent_factor_weight": r[3], "explanation": r[4],
                    "perspective": {
                        "perspective_id": r[5], "perspective_name": r[6],
                        "description": r[7], "stakeholder_role": r[8]
                    }
                }
                for r in result.fetchall()
            ]
            return {"intent_perspectives": mappings, "count": len(mappings)}
    except Exception as e:
        return {"error": str(e), "intent_perspectives": [], "count": 0}


@app.get("/mcp/tools/resolve_semantic_path")
async def resolve_semantic_path(table_name: str, field_name: str, intent_name: str):
    """Full graph traversal: Intent → Perspective → Concept ← Field.
    
    This is the complete semantic disambiguation endpoint that follows the graph path:
    1. Start from Intent
    2. Traverse OPERATES_WITHIN to get constraining Perspective
    3. Traverse USES_DEFINITION to get valid Concepts for that Perspective
    4. Match against Field's CAN_MEAN concepts
    5. Apply intent_factor_weight to select the elevated concept
    
    Returns the deterministically resolved concept for the field given the intent.
    """
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    -- Intent info
                    i.intent_name, i.intent_category, i.typical_question,
                    -- Perspective info (via OPERATES_WITHIN)
                    p.perspective_name, p.stakeholder_role,
                    -- Concept info (via USES_DEFINITION and CAN_MEAN)
                    c.concept_id, c.concept_name, c.concept_type, c.description, c.domain,
                    -- Edge weights
                    ip.intent_factor_weight as operates_within_weight,
                    pc.priority_weight as uses_definition_weight,
                    cf.context_hint,
                    ic.intent_factor_weight as concept_elevation_weight,
                    ic.explanation
                FROM schema_concept_fields cf
                JOIN schema_concepts c ON cf.concept_id = c.concept_id
                JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
                JOIN schema_intents i ON ic.intent_id = i.intent_id
                JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id
                JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
                JOIN schema_perspective_concepts pc ON p.perspective_id = pc.perspective_id 
                    AND c.concept_id = pc.concept_id
                WHERE cf.table_name = :table_name 
                  AND cf.field_name = :field_name
                  AND i.intent_name = :intent_name
                  AND ip.intent_factor_weight = 1.0  -- Active OPERATES_WITHIN path
                  AND ic.intent_factor_weight = 1.0  -- Elevated concept
                LIMIT 1
            """), {"table_name": table_name, "field_name": field_name, "intent_name": intent_name})
            
            row = result.fetchone()
            if row:
                return {
                    "resolved": True,
                    "field": {"table_name": table_name, "field_name": field_name},
                    "traversal_path": {
                        "intent": {
                            "name": row[0], "category": row[1], 
                            "typical_question": row[2]
                        },
                        "operates_within": {
                            "perspective": row[3], "stakeholder_role": row[4],
                            "weight": row[10]
                        },
                        "uses_definition": {
                            "priority_weight": row[11]
                        },
                        "can_mean": {
                            "context_hint": row[12]
                        }
                    },
                    "resolved_concept": {
                        "concept_id": row[5], "concept_name": row[6],
                        "concept_type": row[7], "description": row[8], 
                        "domain": row[9],
                        "elevation_weight": row[13], "explanation": row[14]
                    }
                }
            else:
                return {
                    "resolved": False,
                    "field": {"table_name": table_name, "field_name": field_name},
                    "intent": intent_name,
                    "message": "No valid path found. Check that Intent operates within a Perspective that uses a Concept the Field can mean."
                }
    except Exception as e:
        return {"error": str(e), "resolved": False}


from semantic_reasoning import (
    compare_query_plans, resolve_intent_probabilistic, 
    infer_intent_from_sql, get_graph_syntax_examples,
    resolve_field_meaning, validate_semantic_model, ResolutionResult
)

@app.get("/mcp/tools/compare_query_plans")
async def api_compare_query_plans(table_name: str, field_name: str):
    """Feature 1: Show how different intents produce different query plans for the same field"""
    engine = get_db_engine()
    plans = compare_query_plans(engine, table_name, field_name)
    return {"field": f"{table_name}.{field_name}", "query_plans": plans, "count": len(plans)}


class SQLInput(BaseModel):
    sql: str

@app.post("/mcp/tools/infer_intent")
async def api_infer_intent(body: SQLInput):
    """Feature 3: Automatically infer intent from SQL shape"""
    engine = get_db_engine()
    scores = infer_intent_from_sql(engine, body.sql)
    return {
        "sql_analyzed": body.sql[:200] + "..." if len(body.sql) > 200 else body.sql,
        "inferred_intents": [
            {
                "intent": s.intent_name,
                "confidence": s.confidence,
                "matched_fields": s.matched_fields,
                "matched_concepts": s.matched_concepts,
                "explanation": s.explanation
            } for s in scores[:5]
        ]
    }


@app.get("/mcp/tools/graph_syntax")
async def api_graph_syntax(intent_name: str, table_name: str, field_name: str):
    """Feature 4: Get Cypher and AQL syntax for semantic path traversal"""
    engine = get_db_engine()
    return get_graph_syntax_examples(engine, intent_name, table_name, field_name)


@app.get("/mcp/tools/resolve_field")
async def api_resolve_field(intent_name: str, table_name: str, field_name: str):
    """
    FORMAL RESOLUTION ALGORITHM
    
    For a given (Intent I, Field F), resolve to exactly one Concept C.
    
    Algorithm per treatise:
    1. Find perspectives where Intent operates (weight ≠ -1)
    2. Find concepts that perspectives use/emphasize
    3. Filter to concepts the field CAN_MEAN
    4. Apply intent elevation/suppression
    5. Assert exactly one result
    
    Returns resolution status: 'resolved', 'ambiguous', or 'no_path'
    """
    engine = get_db_engine()
    result = resolve_field_meaning(engine, intent_name, table_name, field_name)
    return {
        "intent": result.intent,
        "field": result.field_name,
        "status": result.status,
        "is_valid": result.is_valid,
        "resolved_concept": result.resolved_concept,
        "perspective": result.perspective,
        "candidate_concepts": result.candidate_concepts,
        "explanation": result.explanation
    }


@app.get("/mcp/tools/validate_model")
async def api_validate_model():
    """
    Validate entire semantic model for resolution completeness.
    
    Checks all (Intent, Field) combinations and reports:
    - Resolved: Valid single-concept resolution
    - Ambiguous: Multiple concepts (modeling error)
    - No Path: Missing edges (incomplete model)
    
    Use this to detect modeling errors before deploying.
    """
    engine = get_db_engine()
    validation = validate_semantic_model(engine)
    return {
        "summary": validation['summary'],
        "ambiguous_combinations": validation['ambiguous'][:10],
        "no_path_combinations": validation['no_path'][:10],
        "total_resolved": validation['summary']['resolved_count'],
        "total_errors": validation['summary']['ambiguous_count'] + validation['summary']['no_path_count']
    }


def create_gradio_interface():
    """Create the Gradio interface for the Space"""
    
    def process_query(query: str, include_explanation: bool) -> tuple:
        intent = analyze_query_intent(query)
        response = generate_sql_from_intent(query, intent)
        
        explanation = response.explanation if include_explanation else "Explanation disabled"
        tables = ", ".join(response.tables_used)
        
        return response.sql, explanation, tables, response.estimated_complexity
    
    def get_template(template_name: str) -> str:
        return SQL_TEMPLATES.get(template_name, "Template not found")
    
    def show_schema() -> str:
        return json.dumps(SAMPLE_SCHEMA, indent=2)
    
    def get_live_tables() -> List[str]:
        """Get list of tables from live database"""
        return get_all_tables()
    
    def get_perspectives_list() -> List[str]:
        """Get list of perspectives for dropdown"""
        engine = get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT perspective_name FROM schema_perspectives ORDER BY perspective_name"))
                return [r[0] for r in result.fetchall()]
        except:
            return []
    
    def get_intents_list() -> List[tuple]:
        """Get list of intents for dropdown, marking which have ground truth SQL"""
        engine = get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT intent_name, intent_category, primary_binding_key 
                    FROM schema_intents ORDER BY intent_category, intent_name
                """))
                choices = []
                for r in result.fetchall():
                    has_binding = r[2] is not None
                    label = f"{r[0]} ({r[1]})" if has_binding else f"{r[0]} ({r[1]}) [no SQL]"
                    choices.append((label, r[0]))
                return choices
        except:
            return []
    
    def get_ambiguous_fields_list() -> List[tuple]:
        """Get list of ambiguous fields for dropdown"""
        engine = get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT cf.table_name, cf.field_name
                    FROM schema_concept_fields cf
                    GROUP BY cf.table_name, cf.field_name
                    HAVING COUNT(*) > 1
                    ORDER BY cf.table_name, cf.field_name
                """))
                return [(f"{r[0]}.{r[1]}", f"{r[0]}|{r[1]}") for r in result.fetchall()]
        except:
            return []
    
    def resolve_field_gradio(field_choice: str, intent_choice: str) -> str:
        """Resolve a field using the full graph traversal"""
        if not field_choice or not intent_choice:
            return "Select both a field and an intent to resolve."
        
        table_name, field_name = field_choice.split("|")
        engine = get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        i.intent_name, i.intent_category, i.typical_question,
                        p.perspective_name, p.stakeholder_role,
                        c.concept_id, c.concept_name, c.concept_type, c.description, c.domain,
                        ip.intent_factor_weight, pc.priority_weight, cf.context_hint,
                        ic.intent_factor_weight, ic.explanation
                    FROM schema_concept_fields cf
                    JOIN schema_concepts c ON cf.concept_id = c.concept_id
                    JOIN schema_intent_concepts ic ON c.concept_id = ic.concept_id
                    JOIN schema_intents i ON ic.intent_id = i.intent_id
                    JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id
                    JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
                    JOIN schema_perspective_concepts pc ON p.perspective_id = pc.perspective_id 
                        AND c.concept_id = pc.concept_id
                    WHERE cf.table_name = :table_name 
                      AND cf.field_name = :field_name
                      AND i.intent_name = :intent_name
                      AND ip.intent_factor_weight = 1.0
                      AND ic.intent_factor_weight = 1.0
                    LIMIT 1
                """), {"table_name": table_name, "field_name": field_name, "intent_name": intent_choice})
                
                row = result.fetchone()
                if row:
                    return f"""## Graph Traversal Result

### Field
`{table_name}.{field_name}`

### Intent
**{row[0]}** ({row[1]})
*"{row[2]}"*

### OPERATES_WITHIN → Perspective
**{row[3]}**
Stakeholder: {row[4]}

### USES_DEFINITION → Concept
**{row[6]}** (type: {row[7]})
Domain: {row[9]}

### Resolution
> {row[8]}

**Explanation:** {row[14]}
"""
                else:
                    valid_intents_result = conn.execute(text("""
                        SELECT DISTINCT i.intent_name, c.concept_name
                        FROM schema_intents i
                        JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id AND ip.intent_factor_weight = 1.0
                        JOIN schema_perspective_concepts pc ON ip.perspective_id = pc.perspective_id
                        JOIN schema_concepts c ON pc.concept_id = c.concept_id
                        JOIN schema_concept_fields cf ON c.concept_id = cf.concept_id
                        JOIN schema_intent_concepts ic ON i.intent_id = ic.intent_id AND c.concept_id = ic.concept_id AND ic.intent_factor_weight = 1.0
                        WHERE cf.table_name = :table_name AND cf.field_name = :field_name
                    """), {"table_name": table_name, "field_name": field_name})
                    valid_rows = valid_intents_result.fetchall()
                    
                    if valid_rows:
                        suggestions = "\n".join([f"- **{r[0]}** → resolves to `{r[1]}`" for r in valid_rows])
                        return f"""## No Valid Path Found

Field: `{table_name}.{field_name}`
Intent: `{intent_choice}`

The selected intent does not have a valid semantic path to this field.

### Try these intents instead:
{suggestions}
"""
                    else:
                        return f"""## No Valid Path Found

Field: `{table_name}.{field_name}`
Intent: `{intent_choice}`

No intents currently have complete semantic paths to this field.
Check that perspective-concept and intent-concept relationships are seeded.
"""
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_graph_visualization() -> str:
        """Generate text-based graph visualization"""
        engine = get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT i.intent_name, p.perspective_name
                    FROM schema_intent_perspectives ip
                    JOIN schema_intents i ON ip.intent_id = i.intent_id
                    JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
                    WHERE ip.intent_factor_weight = 1.0
                    ORDER BY p.perspective_name, i.intent_name
                """))
                
                graph = "## Intent → Perspective Graph\n\n"
                current_perspective = None
                for row in result.fetchall():
                    if row[1] != current_perspective:
                        current_perspective = row[1]
                        graph += f"\n### {row[1]}\n"
                    graph += f"  - {row[0]} → **{row[1]}**\n"
                
                return graph
        except Exception as e:
            return f"Error loading graph: {str(e)}"
    
    def get_table_ddl_gradio(table_name: str) -> str:
        """Get CREATE TABLE SQL for selected table"""
        if not table_name:
            return "-- Select a table to view its schema"
        return get_table_create_sql(table_name)
    
    def get_all_ddl_gradio() -> str:
        """Get all CREATE TABLE statements"""
        tables = get_all_tables()
        if not tables:
            return "-- Database not connected or no tables found"
        
        all_ddl = []
        for table in sorted(tables):
            all_ddl.append(f"-- Table: {table}")
            all_ddl.append(get_table_create_sql(table))
            all_ddl.append("")
        
        return "\n".join(all_ddl)
    
    def execute_sql_gradio(sql: str) -> tuple:
        """Execute SQL and return results as formatted output"""
        if not sql.strip():
            return "-- Enter a SQL query", ""
        
        result = execute_readonly_sql(sql)
        
        if result["error"]:
            return f"-- Error: {result['error']}", ""
        
        if not result["rows"]:
            return "-- Query executed successfully. No rows returned.", ""
        
        header = " | ".join(str(c) for c in result["columns"])
        separator = "-" * len(header)
        rows_str = "\n".join(" | ".join(str(v) for v in row) for row in result["rows"])
        
        table_output = f"{header}\n{separator}\n{rows_str}"
        stats = f"Returned {len(result['rows'])} rows, {len(result['columns'])} columns"
        
        return table_output, stats
    
    with gr.Blocks() as demo:
        gr.Markdown("""
        # 🏭 Manufacturing SQL Semantic Layer
        
        **MCP Context Builder** for GitHub Copilot integration.
        Select resources below and click **Copy to Copilot** to bundle context.
        
        | MCP Component | Purpose |
        |---------------|---------|
        | **Prompts** | Natural language question templates |
        | **Resources** | Schema DDL, ground truth SQL queries |
        | **Tools** | API endpoints for validation |
        """)
        
        def build_copilot_context(question: str, include_schema: bool, include_queries: bool, 
                                   selected_category: str, include_semantic: bool, selected_intent: str) -> str:
            """Build MCP context package for Copilot"""
            context_parts = []
            
            context_parts.append("# MCP Context for Manufacturing SQL Generation\n")
            
            if question.strip():
                context_parts.append("## Prompt")
                context_parts.append(f"User Question: {question}\n")
            
            if include_semantic and selected_intent:
                context_parts.append("## Semantic Context")
                context_parts.append(f"**Intent:** {selected_intent}")
                engine = get_db_engine()
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text("""
                            SELECT i.intent_name, i.description, i.typical_question,
                                   p.perspective_name, p.stakeholder_role
                            FROM schema_intents i
                            JOIN schema_intent_perspectives ip ON i.intent_id = ip.intent_id
                            JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
                            WHERE i.intent_name = :intent_name AND ip.intent_factor_weight = 1.0
                        """), {"intent_name": selected_intent})
                        row = result.fetchone()
                        if row:
                            context_parts.append(f"*{row[1]}*")
                            context_parts.append(f"\n**Perspective:** {row[3]} ({row[4]})")
                            context_parts.append(f"**Typical Question:** {row[2]}\n")
                        
                        result2 = conn.execute(text("""
                            SELECT c.concept_name, c.description, ic.explanation
                            FROM schema_intent_concepts ic
                            JOIN schema_concepts c ON ic.concept_id = c.concept_id
                            WHERE ic.intent_id = (SELECT intent_id FROM schema_intents WHERE intent_name = :intent_name)
                              AND ic.intent_factor_weight = 1.0
                        """), {"intent_name": selected_intent})
                        elevated = result2.fetchall()
                        if elevated:
                            context_parts.append("**Elevated Concepts:**")
                            for c in elevated:
                                context_parts.append(f"- {c[0]}: {c[1]}")
                            context_parts.append("")
                except:
                    pass
            
            if include_schema:
                gt_tables = get_ground_truth_tables()
                context_parts.append(f"## Resources: Database Schema ({len(gt_tables)} tables from Ground Truth)")
                if gt_tables:
                    for table in gt_tables:
                        ddl = get_table_create_sql(table)
                        context_parts.append(f"```sql\n-- {table}\n{ddl}\n```")
                context_parts.append("")
            
            if include_queries and selected_category:
                context_parts.append("## Resources: Ground Truth SQL Examples")
                queries = get_saved_queries(selected_category)
                for q in queries[:5]:
                    context_parts.append(f"### {q['name']}")
                    context_parts.append(f"*{q['description']}*")
                    context_parts.append(f"```sql\n{q['sql']}```\n")
            
            context_parts.append("## Tools Available")
            context_parts.append("- `generate_sql`: Convert natural language to SQL")
            context_parts.append("- `get_table_ddl`: Get schema for specific table")
            context_parts.append("- `validate_sql`: Check SQL syntax against schema")
            context_parts.append("- `resolve_semantic_path`: Disambiguate field meanings via graph traversal")
            
            return "\n".join(context_parts)
        
        def get_category_choices():
            index = get_query_categories()
            return [(f"{c['name']} ({c['query_count']} queries)", c['id']) 
                    for c in index.get("categories", [])]
        
        with gr.Tab("🚀 Copilot Context"):
            gr.Markdown("### Build MCP Context Package")
            
            with gr.Row():
                with gr.Column():
                    question_input = gr.Textbox(
                        label="Your Question (Prompt)",
                        placeholder="e.g., Show me supplier on-time delivery rates for Q4",
                        lines=2
                    )
                    
                    gr.Markdown("#### Select Resources")
                    include_schema = gr.Checkbox(label="Include Database Schema (tables in Ground Truth)", value=True)
                    include_queries = gr.Checkbox(label="Include Ground Truth SQL Examples", value=True)
                    query_category = gr.Dropdown(
                        choices=get_category_choices(),
                        label="Query Category",
                        interactive=True
                    )
                    
                    gr.Markdown("#### Semantic Context")
                    include_semantic = gr.Checkbox(label="Include Semantic Layer Context", value=True)
                    semantic_intent = gr.Dropdown(
                        choices=get_intents_list(),
                        label="Analytical Intent",
                        info="Intent constrains field interpretations via graph traversal",
                        interactive=True
                    )
                    
                    copy_btn = gr.Button("📋 Copy to Copilot", variant="primary", size="lg")
                
                with gr.Column():
                    context_output = gr.Textbox(
                        label="MCP Context (copy this to Copilot Chat)",
                        lines=20,
                        max_lines=40
                    )
            
            copy_btn.click(
                fn=build_copilot_context,
                inputs=[question_input, include_schema, include_queries, query_category, include_semantic, semantic_intent],
                outputs=context_output
            )
        
        with gr.Tab("📊 Schema"):
            gr.Markdown("### Database Schema Resources")
            
            initial_table_list = get_all_tables()
            gr.Markdown(f"**{len(initial_table_list)} tables available**")
            
            with gr.Row():
                with gr.Column():
                    refresh_tables_btn = gr.Button("Refresh Table List", variant="secondary")
                    table_dropdown = gr.Dropdown(
                        choices=initial_table_list,
                        value=initial_table_list[0] if initial_table_list else None,
                        label="Select Table",
                        interactive=True
                    )
                    get_ddl_btn = gr.Button("View DDL", variant="primary")
                    get_all_ddl_btn = gr.Button("View All Tables", variant="secondary")
                
                with gr.Column():
                    ddl_output = gr.Code(label="CREATE TABLE SQL", language="sql", lines=20)
            
            def refresh_table_list():
                tables = get_all_tables()
                return gr.update(choices=tables, value=tables[0] if tables else None)
            
            refresh_tables_btn.click(fn=refresh_table_list, outputs=table_dropdown)
            get_ddl_btn.click(fn=get_table_ddl_gradio, inputs=table_dropdown, outputs=ddl_output)
            get_all_ddl_btn.click(fn=get_all_ddl_gradio, outputs=ddl_output)
        
        with gr.Tab("📁 Ground Truth SQL"):
            gr.Markdown("""
            ### Validated SQL Query Resources
            
            Browse ground truth SQL queries organized by category.
            These serve as few-shot examples for Copilot context.
            """)
            
            def load_queries_for_category(category_id: str):
                print(f"[DEBUG] load_queries_for_category called with: {repr(category_id)}")
                if not category_id:
                    print("[DEBUG] category_id is empty, returning empty choices")
                    return gr.Dropdown(choices=[], value=None), ""
                queries = get_saved_queries(category_id)
                print(f"[DEBUG] Found {len(queries)} queries")
                choices = [q['name'] for q in queries]
                print(f"[DEBUG] Returning choices: {choices}")
                return gr.Dropdown(choices=choices, value=None), ""
            
            def _find_binding_key_for_sql(sql_text: str) -> str:
                """Look up binding key from manifest by matching SQL content"""
                if not sql_text or not sql_text.strip():
                    return ""
                manifest_path = os.path.join(GROUND_TRUTH_DIR, "reviewer_manifest.json")
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)

                    def normalize_sql(s: str) -> str:
                        if not s:
                            return ""
                        # Remove block comments /* ... */
                        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
                        # Remove line comments -- ...\n
                        s = re.sub(r"--.*?\n", "\n", s)
                        # Remove any remaining SQL comments starting at line end
                        s = re.sub(r"--.*$", "", s, flags=re.M)
                        # Strip trailing semicolons and whitespace
                        s = s.replace(';', ' ')
                        # Collapse whitespace
                        s = " ".join(s.split())
                        return s.lower().strip()

                    sql_normalized = normalize_sql(sql_text)
                    for binding_key, entry in manifest.get("approved_snippets", {}).items():
                        file_path = entry.get("file_path", "")
                        candidates = []
                        # Raw path as provided
                        if file_path:
                            candidates.append(file_path)
                        # If manifest entry used a repo-relative path (e.g., app_schema/...), resolve relative to this package
                        candidates.append(os.path.join(os.path.dirname(__file__), file_path))
                        # Try resolving as basename inside ground truth directory
                        candidates.append(os.path.join(GROUND_TRUTH_DIR, os.path.basename(file_path)))
                        # Try resolving inside sql_snippets
                        candidates.append(os.path.join(GROUND_TRUTH_SQL_DIR, os.path.basename(file_path)))
                        # Try canonical binding_key filename inside sql_snippets
                        candidates.append(os.path.join(GROUND_TRUTH_SQL_DIR, f"{binding_key}.sql"))

                        resolved = None
                        for candidate in candidates:
                            try:
                                if candidate and os.path.exists(candidate):
                                    resolved = candidate
                                    break
                            except Exception:
                                continue

                        if not resolved:
                            print(f"[DEBUG] No snippet file found for binding {binding_key}; tried candidates: {candidates}")
                            continue

                        try:
                            with open(resolved, 'r') as sf:
                                snippet_sql = sf.read()
                        except Exception as e:
                            print(f"[DEBUG] error reading snippet file {resolved}: {e}")
                            continue

                        if normalize_sql(snippet_sql) == sql_normalized:
                            print(f"[DEBUG] Found binding for query -> {binding_key} (file: {resolved})")
                            return binding_key
                except Exception as e:
                    print(f"[DEBUG] Binding key lookup error: {e}")
                return ""

            def _find_binding_key_by_name(query_name: str) -> str:
                """Look up binding key from manifest by matching query name against concept/perspective"""
                try:
                    with open(MANIFEST_PATH, 'r') as f:
                        manifest = json.load(f)
                    query_lower = query_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                    for key, entry in manifest.get("approved_snippets", {}).items():
                        concept = entry.get("concept_anchor", "").lower().replace('_', '')
                        perspective = entry.get("perspective", "")
                        sme_just = entry.get("sme_justification", "").lower()
                        entry_name = f"{concept} ({perspective.lower()})".replace(' ', '').replace('_', '')
                        if query_lower == entry_name:
                            return key
                        if query_name.lower() in sme_just:
                            return key
                except Exception:
                    pass
                return ""

            def load_query_sql(category_id: str, query_name: str):
                if category_id is None or query_name is None:
                    return "", "", ""
                queries = get_saved_queries(category_id)
                for q in queries:
                    if q['name'] == query_name:
                        binding_key = q.get('binding_key', '')
                        if not binding_key:
                            raw = _find_binding_key_for_sql(q['sql'])
                            if raw:
                                binding_key = raw
                        if not binding_key:
                            binding_key = _find_binding_key_by_name(query_name)
                        if not binding_key:
                            binding_key = _ensure_manifest_entry(
                                query_name, q['sql'], q.get('description', ''), category_id
                            )
                        return q['sql'], q['description'], binding_key
                return "", "", ""
            
            with gr.Row():
                with gr.Column():
                    saved_category = gr.Dropdown(
                        choices=get_category_choices(),
                        label="Query Category",
                        interactive=True
                    )
                    load_queries_btn = gr.Button("Load Queries", variant="secondary")
                    saved_query_dropdown = gr.Dropdown(
                        choices=[],
                        label="Select Query",
                        interactive=True
                    )
                    saved_description = gr.Textbox(label="Description", interactive=True)
                    saved_binding_key = gr.Textbox(label="Binding Key (empty = not yet in manifest)", interactive=False)
                
                with gr.Column():
                    saved_sql_output = gr.Code(label="SQL Query", language="sql", lines=15, show_label=True, interactive=True)
            
            with gr.Row():
                save_query_btn = gr.Button("Save Changes", variant="primary", elem_id="gt_save_btn")
                save_query_status = gr.Textbox(label="Save Status", interactive=False)

            def save_query_edits(category_id, query_name, new_sql, new_description):
                if not category_id or not query_name:
                    return "Select a category and query first."
                index = get_query_categories()
                category = next((c for c in index.get("categories", []) if c["id"] == category_id), None)
                if not category:
                    return f"Category '{category_id}' not found."
                sql_file = os.path.join(QUERIES_DIR, category["file"])
                if not os.path.exists(sql_file):
                    return f"File not found: {category['file']}"
                with open(sql_file, "r") as f:
                    content = f.read()
                queries = get_saved_queries(category_id)
                match = next((q for q in queries if q["name"] == query_name), None)
                if not match:
                    return f"Query '{query_name}' not found in {category['file']}."
                old_sql_block = match["sql"].strip()
                old_desc_line = f"-- Description: {match['description']}"
                new_desc_line = f"-- Description: {new_description.strip()}"
                new_sql_clean = new_sql.strip() if new_sql else old_sql_block
                updated = content.replace(old_desc_line, new_desc_line)
                updated = updated.replace(old_sql_block, new_sql_clean)
                with open(sql_file, "w") as f:
                    f.write(updated)
                return f"Saved changes to '{query_name}' in {category['name']}."

            load_queries_btn.click(
                fn=load_queries_for_category,
                inputs=saved_category,
                outputs=[saved_query_dropdown, saved_sql_output]
            )
            
            saved_query_dropdown.change(
                fn=load_query_sql,
                inputs=[saved_category, saved_query_dropdown],
                outputs=[saved_sql_output, saved_description, saved_binding_key]
            )

            save_query_btn.click(
                fn=save_query_edits,
                inputs=[saved_category, saved_query_dropdown, saved_sql_output, saved_description],
                outputs=[save_query_status],
                api_name="save_ground_truth_edits"
            )
        
        with gr.Tab("🔗 Semantic Graph"):
            gr.Markdown("""
            ### Semantic Disambiguation via Graph Traversal
            
            Resolve ambiguous field meanings using the graph path:
            
            ```
            (:Intent) -[:OPERATES_WITHIN]-> (:Perspective) -[:USES_DEFINITION]-> (:Concept) <-[:CAN_MEAN]- (:Field)
            ```
            
            Select an **Intent** (analytical goal) and an **Ambiguous Field** to see how the graph resolves the field's meaning.
            """)
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 1. Select Intent")
                    intent_dropdown = gr.Dropdown(
                        choices=get_intents_list(),
                        label="Analytical Intent",
                        info="Intent determines which perspective and concept to use",
                        interactive=True
                    )
                    
                    gr.Markdown("#### 2. Select Ambiguous Field")
                    field_dropdown = gr.Dropdown(
                        choices=get_ambiguous_fields_list(),
                        label="Field (table.column)",
                        info="Fields with multiple possible interpretations",
                        interactive=True
                    )
                    
                    resolve_btn = gr.Button("🔍 Resolve Field Meaning", variant="primary", size="lg")
                
                with gr.Column():
                    resolution_output = gr.Markdown(
                        value="Select an intent and field, then click **Resolve Field Meaning**.",
                        label="Graph Traversal Result"
                    )
            
            resolve_btn.click(
                fn=resolve_field_gradio,
                inputs=[field_dropdown, intent_dropdown],
                outputs=resolution_output,
                api_name="resolve_semantic_field"
            )
            
            gr.Markdown("---")
            
            with gr.Accordion("View Intent → Perspective Graph", open=False):
                graph_output = gr.Markdown(value=get_graph_visualization())
            
            gr.Markdown("""
            #### Semantic MCP Endpoints
            
            | Endpoint | Purpose |
            |----------|---------|
            | `GET /mcp/tools/get_perspectives` | List organizational perspectives |
            | `GET /mcp/tools/get_intents` | List analytical intents |
            | `GET /mcp/tools/get_intent_perspectives` | View OPERATES_WITHIN edges |
            | `GET /mcp/tools/resolve_semantic_path` | Full graph traversal |
            """)
        
        with gr.Tab("🧠 Advanced Reasoning"):
            gr.Markdown("""
            ### Advanced Semantic Reasoning
            
            Demonstrates 4 advanced patterns for semantic graph traversal:
            1. **Query Plan Comparison** - How different intents interpret the same field
            2. **Intent Resolution** - Rank intents by confidence score
            3. **SQL Intent Inference** - Automatically detect intent from SQL shape
            4. **Graph Syntax Mapping** - Cypher and AQL traversal examples
            """)
            
            with gr.Accordion("1. Intent Factor Weight → Query Plan Changes", open=True):
                gr.Markdown("See how the same field resolves differently under different intents:")
                
                with gr.Row():
                    qp_field = gr.Dropdown(
                        choices=get_ambiguous_fields_list(),
                        label="Select Ambiguous Field",
                        interactive=True
                    )
                    qp_btn = gr.Button("Compare Query Plans", variant="primary")
                
                qp_output = gr.Markdown()
                
                def compare_plans_gradio(field_choice: str) -> str:
                    if not field_choice:
                        return "Select a field to compare query plans."
                    table_name, field_name = field_choice.split("|")
                    engine = get_db_engine()
                    plans = compare_query_plans(engine, table_name, field_name)
                    if not plans:
                        return f"No query plans found for `{table_name}.{field_name}`"
                    
                    output = f"## Query Plans for `{table_name}.{field_name}`\n\n"
                    for p in plans:
                        output += f"### Intent: {p['intent']}\n"
                        output += f"- **Perspective**: {p['perspective']}\n"
                        output += f"- **Resolves to**: `{p['resolves_to']}`\n"
                        output += f"- **Elevated concepts**: {', '.join(p['elevated']) or 'None'}\n"
                        output += f"- **Suggested joins**: {', '.join(p['suggested_joins']) or 'None'}\n\n"
                    return output
                
                qp_btn.click(fn=compare_plans_gradio, inputs=[qp_field], outputs=qp_output)
            
            with gr.Accordion("2. Intent Resolution", open=False):
                gr.Markdown("Given multiple fields, compute confidence scores for each intent:")
                
                fields_input = gr.Textbox(
                    label="Fields (comma-separated: table.field, table.field)",
                    placeholder="daily_deliveries.ontime_rate, product_defects.severity",
                    lines=1
                )
                prob_btn = gr.Button("Resolve Intents", variant="secondary")
                prob_output = gr.Markdown()
                
                def probabilistic_resolve_gradio(fields_str: str) -> str:
                    if not fields_str.strip():
                        return "Enter fields to analyze."
                    
                    fields = []
                    for f in fields_str.split(","):
                        parts = f.strip().split(".")
                        if len(parts) == 2:
                            fields.append((parts[0], parts[1]))
                    
                    if not fields:
                        return "Invalid field format. Use: table.field, table.field"
                    
                    engine = get_db_engine()
                    scores = resolve_intent_probabilistic(engine, fields)
                    
                    if not scores:
                        return "No intents found for the given fields."
                    
                    output = "## Intent Confidence Scores\n\n"
                    output += "| Intent | Confidence | Matched Fields | Matched Concepts |\n"
                    output += "|--------|------------|----------------|------------------|\n"
                    for s in scores[:5]:
                        output += f"| {s.intent_name} | {s.confidence:.1%} | {len(s.matched_fields)} | {', '.join(s.matched_concepts)} |\n"
                    
                    return output
                
                prob_btn.click(fn=probabilistic_resolve_gradio, inputs=[fields_input], outputs=prob_output)
            
            with gr.Accordion("3. Automatic Intent Inference from SQL Shape", open=False):
                gr.Markdown("Parse SQL to detect likely intent based on tables, columns, and patterns:")
                
                sql_input = gr.Textbox(
                    label="SQL Query",
                    placeholder="SELECT supplier_id, AVG(ontime_rate) FROM daily_deliveries GROUP BY supplier_id",
                    lines=3
                )
                infer_btn = gr.Button("Infer Intent", variant="secondary")
                infer_output = gr.Markdown()
                
                def infer_intent_gradio(sql: str) -> str:
                    if not sql.strip():
                        return "Enter a SQL query to analyze."
                    
                    engine = get_db_engine()
                    scores = infer_intent_from_sql(engine, sql)
                    
                    if not scores:
                        return "Could not infer intent from SQL. Check that tables/columns exist in schema."
                    
                    output = "## Inferred Intents\n\n"
                    for i, s in enumerate(scores[:3]):
                        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
                        output += f"### {medal} {s.intent_name} ({s.confidence:.1%})\n"
                        output += f"- **Matched fields**: {', '.join(s.matched_fields)}\n"
                        output += f"- **Concepts**: {', '.join(s.matched_concepts)}\n"
                        output += f"- *{s.explanation}*\n\n"
                    
                    return output
                
                infer_btn.click(fn=infer_intent_gradio, inputs=[sql_input], outputs=infer_output)
            
            with gr.Accordion("4. ArangoDB / Neo4j Traversal Syntax", open=False):
                gr.Markdown("Generate explicit graph database syntax for the semantic path:")
                
                with gr.Row():
                    syntax_intent = gr.Dropdown(
                        choices=get_intents_list(),
                        label="Intent",
                        interactive=True
                    )
                    syntax_field = gr.Dropdown(
                        choices=get_ambiguous_fields_list(),
                        label="Field",
                        interactive=True
                    )
                
                syntax_btn = gr.Button("Generate Graph Syntax", variant="secondary")
                
                with gr.Tabs():
                    with gr.Tab("Cypher (Neo4j)"):
                        cypher_output = gr.Code(language="sql", label="Cypher Query")
                    with gr.Tab("AQL (ArangoDB)"):
                        aql_output = gr.Code(language="sql", label="AQL Query")
                    with gr.Tab("SQL Equivalent"):
                        sql_equiv_output = gr.Code(language="sql", label="SQL Query")
                
                def generate_syntax_gradio(intent: str, field_choice: str):
                    if not intent or not field_choice:
                        return "-- Select intent and field", "-- Select intent and field", "-- Select intent and field"
                    
                    table_name, field_name = field_choice.split("|")
                    engine = get_db_engine()
                    syntax = get_graph_syntax_examples(engine, intent, table_name, field_name)
                    
                    return syntax["cypher"], syntax["aql"], syntax["sql_equivalent"]
                
                syntax_btn.click(
                    fn=generate_syntax_gradio,
                    inputs=[syntax_intent, syntax_field],
                    outputs=[cypher_output, aql_output, sql_equiv_output]
                )
        
        with gr.Tab("📝 SME SQL Entry"):
            gr.Markdown("""
            ### SME Semantic SQL Submission
            
            Submit SQL snippets with semantic metadata for review. Each submission generates:
            - A **deterministic filename** binding SQL to its semantic context
            - A **Reviewer Manifest** entry for approval workflow
            
            ```
            Flow: SME Submit → Binding Key → Manifest → Approver Review → ArangoDB Solder
            ```
            """)
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 1. Semantic Context")
                    sme_perspective = gr.Dropdown(
                        choices=get_perspectives_list(),
                        label="Perspective",
                        info="The organizational lens for this SQL",
                        interactive=True
                    )
                    sme_concept = gr.Textbox(
                        label="Concept (e.g., LOT, NCM_COST, DELIVERY_RATE)",
                        placeholder="Enter the concept this SQL defines"
                    )
                    sme_category = gr.Dropdown(
                        choices=["Inventory", "Quality", "Delivery", "Financial", "Production"],
                        label="Category",
                        value="Inventory",
                        interactive=True
                    )
                    
                    gr.Markdown("#### 2. SQL Statement")
                    sme_sql = gr.Code(
                        label="SQL Statement",
                        language="sql",
                        lines=8,
                        value="-- Enter your SQL here\nSELECT "
                    )
                    
                    sme_justification = gr.Textbox(
                        label="SME Justification / Notes",
                        placeholder="Why does this SQL represent the concept from this perspective?",
                        lines=3
                    )
                    
                    sme_submit_btn = gr.Button("Submit for Review", variant="primary", size="lg")
                    sme_status = gr.Textbox(label="Submission Status", interactive=False, value="")
                
                with gr.Column():
                    gr.Markdown("#### Reviewer's Decision Table")
                    
                    def _friendly_name(binding_key: str, concept: str, perspective: str) -> str:
                        """Convert binding key to human-readable name for reviewer."""
                        if concept and concept != "UNKNOWN":
                            label = concept.replace("_", " ").title()
                            if perspective:
                                return f"{label} ({perspective})"
                            return label
                        parts = binding_key.replace("gt_", "").rsplit("_", 2)
                        if len(parts) >= 2:
                            return parts[0].replace("_", " ").title()
                        return binding_key

                    def load_reviewer_table() -> str:
                        bindings = resolve_sql_bindings()
                        if not bindings:
                            return "No submissions yet. Use the form on the left to submit SQL."
                        
                        output = "| Name | Perspective | Concept | Status |\n"
                        output += "|------|-------------|---------|--------|\n"
                        
                        status_icons = {
                            "PENDING": "⏳",
                            "APPROVED": "✅",
                            "REJECTED": "❌",
                            "UNKNOWN": "❓"
                        }
                        
                        for b in bindings:
                            icon = status_icons.get(b["validation_status"], "❓")
                            name = _friendly_name(b["binding_key"], b.get("concept", ""), b.get("perspective", ""))
                            output += f"| {name} | {b['perspective']} | {b['concept']} | {icon} {b['validation_status']} |\n"
                        
                        summary = get_manifest_summary()
                        output += f"\n**Total: {summary['total']}** | "
                        output += f"Pending: {summary['pending']} | "
                        output += f"Approved: {summary['approved']} | "
                        output += f"Rejected: {summary['rejected']}"
                        
                        return output
                    
                    reviewer_table = gr.Markdown(value=load_reviewer_table())
                    refresh_reviewer_btn = gr.Button("Refresh Table", variant="secondary")
                    
                    gr.Markdown("#### Review Actions")
                    
                    def get_pending_binding_keys():
                        bindings = resolve_sql_bindings()
                        result = []
                        for b in bindings:
                            friendly = _friendly_name(b["binding_key"], b.get("concept", ""), b.get("perspective", ""))
                            status = b.get("validation_status", "UNKNOWN")
                            label = f"{friendly} [{status}]"
                            result.append((label, b["binding_key"]))
                        return result
                    
                    with gr.Row():
                        review_binding_key = gr.Dropdown(
                            choices=get_pending_binding_keys(),
                            label="Binding Key",
                            interactive=True,
                            allow_custom_value=False
                        )
                        review_action = gr.Dropdown(
                            choices=["APPROVED", "REJECTED", "PENDING"],
                            label="Decision",
                            interactive=True
                        )
                    review_btn = gr.Button("Update Status", variant="secondary")
                    review_status = gr.Textbox(label="Review Status", interactive=False)
            
            def submit_sme(sql, category, perspective, concept, justification):
                if not sql or not sql.strip():
                    return "Please enter a SQL statement.", load_reviewer_table(), gr.update()
                cleaned_sql = sql.strip()
                if cleaned_sql in ("-- Enter your SQL here\nSELECT", "-- Enter your SQL here", "SELECT"):
                    return "Please enter a SQL statement.", load_reviewer_table(), gr.update()
                if not perspective:
                    return "Please select a perspective.", load_reviewer_table(), gr.update()
                if not concept or not concept.strip():
                    concept = _auto_concept_from_sql(cleaned_sql)
                
                result = save_sme_submission(cleaned_sql, category or "Inventory", perspective, concept.strip(), justification or "")
                keys = get_pending_binding_keys()
                return result, load_reviewer_table(), gr.update(choices=keys, value=keys[0] if keys else None)
            
            sme_submit_btn.click(
                fn=submit_sme,
                inputs=[sme_sql, sme_category, sme_perspective, sme_concept, sme_justification],
                outputs=[sme_status, reviewer_table, review_binding_key]
            )
            
            def refresh_reviewer_and_keys():
                keys = get_pending_binding_keys()
                return load_reviewer_table(), gr.update(choices=keys, value=keys[0] if keys else None)
            
            refresh_reviewer_btn.click(fn=refresh_reviewer_and_keys, outputs=[reviewer_table, review_binding_key])
            
            def do_review(binding_key, action):
                if not binding_key:
                    return "Select a binding key.", load_reviewer_table(), gr.update()
                if not action:
                    return "Select a decision.", load_reviewer_table(), gr.update()
                result = update_binding_status(binding_key.strip(), action)
                keys = get_pending_binding_keys()
                return result, load_reviewer_table(), gr.update(choices=keys, value=keys[0] if keys else None)
            
            review_btn.click(
                fn=do_review,
                inputs=[review_binding_key, review_action],
                outputs=[review_status, reviewer_table, review_binding_key]
            )
        
        solder = SolderEngine()
        
        with gr.Tab("💬 Ask a Question"):
            gr.Markdown("""
            ### Production Dispatcher — Hybrid RAG
            
            Ask a **natural language question** about your manufacturing data. The system:
            1. Routes your question to the correct **Intent** and **Concepts** (closed vocabulary)
            2. Passes those to the **SolderEngine** to assemble governed SQL
            3. Returns perspective-aware SQL built entirely from **SME-approved snippets**
            
            The LLM acts as a **Semantic Router**, not a SQL generator. All SQL is governed.
            """)
            
            dispatcher = ProductionDispatcher(solder_engine=solder, use_live_api=True)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### Your Question")
                    nl_input = gr.Textbox(
                        label="Natural Language Query",
                        placeholder="e.g., What are our top defect costs this quarter?",
                        lines=3,
                        info="Ask about defects, costs, suppliers, OEE, scheduling, maintenance..."
                    )
                    
                    with gr.Row():
                        perspective_override = gr.Dropdown(
                            choices=[("Auto-detect", "")] + [(p, p) for p in dispatcher.perspectives],
                            value="",
                            label="Perspective Override",
                            info="Leave as Auto-detect to let the router choose",
                            interactive=True
                        )
                        dispatch_dialect = gr.Dropdown(
                            choices=[
                                ("SQLite", "sqlite"),
                                ("T-SQL (SQL Server)", "tsql"),
                                ("PostgreSQL", "postgres"),
                                ("MySQL", "mysql"),
                                ("BigQuery", "bigquery"),
                            ],
                            value="sqlite",
                            label="Target Dialect",
                            interactive=True
                        )
                    
                    with gr.Row():
                        dispatch_mode = gr.Radio(
                            choices=[("Live API (HuggingFace)", "live"), ("Demo Mode (Mock)", "mock")],
                            value="mock",
                            label="Routing Mode",
                            info="Demo mode uses keyword matching; Live uses HF Inference API"
                        )
                    
                    dispatch_btn = gr.Button("Ask", variant="primary", size="lg")
                    
                    gr.Markdown("#### Example Questions")
                    gr.Markdown("""
                    - *"Show me the cost of defects on the East Wall"*
                    - *"What is our supplier delivery performance?"*
                    - *"How is OEE trending for the assembly line?"*
                    - *"What are the top NCM costs this quarter?"*
                    - *"Which defects have customer impact?"*
                    - *"What's the maintenance schedule for critical equipment?"*
                    """)
                
                with gr.Column(scale=1):
                    gr.Markdown("#### Governed SQL Output")
                    dispatch_sql = gr.Code(label="Assembled SQL", language="sql", lines=14)
                    
                    dispatch_metadata = gr.Markdown(label="Routing Metadata")
                    
                    dispatch_warnings = gr.Markdown(label="Warnings")
            
            def run_dispatch(question, perspective, dialect, mode):
                if not question or not question.strip():
                    return (
                        "-- Enter a question above",
                        "Enter a natural language question to begin.",
                        ""
                    )
                
                force_mock = (mode == "mock")
                persp = perspective if perspective else None
                
                result = dispatcher.dispatch(
                    user_query=question.strip(),
                    perspective_override=persp,
                    force_mock=force_mock,
                    target_dialect=dialect or "sqlite"
                )
                
                meta = f"## Routing Result\n\n"
                meta += f"**Mode:** {result.routing_mode}\n\n"
                meta += f"**Confidence:** {result.routing_confidence}\n\n"
                meta += f"**Intent:** `{result.intent}`\n\n"
                meta += f"**Binding Key:** `{result.binding_key}`\n\n" if result.binding_key else ""
                meta += f"**Concepts:** {', '.join(f'`{c}`' for c in result.concepts) if result.concepts else 'None'}\n\n"
                meta += f"**Perspective:** {result.perspective or 'N/A'}\n\n"
                
                if result.assembly_report:
                    meta += "### Assembly Report\n"
                    for line in result.assembly_report:
                        meta += f"{line}\n"
                    meta += "\n"
                
                warn_md = ""
                if result.warnings:
                    warn_md = "### Warnings\n"
                    for w in result.warnings:
                        warn_md += f"- {w}\n"
                
                if result.out_of_scope:
                    warn_md += "\n**This question is outside the manufacturing domain.** Try asking about defects, costs, suppliers, OEE, scheduling, or maintenance.\n"
                
                return result.assembled_sql, meta, warn_md
            
            dispatch_btn.click(
                fn=run_dispatch,
                inputs=[nl_input, perspective_override, dispatch_dialect, dispatch_mode],
                outputs=[dispatch_sql, dispatch_metadata, dispatch_warnings]
            )
        
        with gr.Tab("🔧 Solder Engine"):
            gr.Markdown("""
            ### Semantic Transpilation Engine
            
            The **Solder Pattern** assembles final executable SQL by combining:
            - **Elevation Weights** from the semantic graph (which concepts are relevant)
            - **Approved SQL Snippets** from SME submissions (governed ground truth)
            - **SQLGlot AST Manipulation** for alias renaming, table qualification, and dialect transpilation
            
            ```
            Intent → ELEVATES → Concept → Approved Snippet → SQLGlot AST → Final SQL
            ```
            """)
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("#### 1. Select Intent")
                    available_intents = solder.get_available_intents()
                    intent_choices = [(f"{i['intent_name']} ({i['intent_category']})", i['intent_name']) for i in available_intents]
                    
                    solder_intent = gr.Dropdown(
                        choices=intent_choices,
                        label="Analytical Intent",
                        info="Determines which concepts are ELEVATED vs SUPPRESSED",
                        interactive=True
                    )
                    
                    gr.Markdown("#### 2. Target Concept (optional)")
                    solder_concept = gr.Textbox(
                        label="Target Concept",
                        placeholder="Leave blank to use primary elevated concept",
                        info="e.g., DefectSeverityCost, NCM_COST"
                    )
                    
                    gr.Markdown("#### 3. Output Dialect")
                    solder_dialect = gr.Dropdown(
                        choices=[
                            ("SQLite", "sqlite"),
                            ("T-SQL (SQL Server)", "tsql"),
                            ("PostgreSQL", "postgres"),
                            ("MySQL", "mysql"),
                            ("BigQuery", "bigquery"),
                        ],
                        value="sqlite",
                        label="Target SQL Dialect",
                        interactive=True
                    )
                    
                    with gr.Accordion("Alias Overrides (Advanced)", open=False):
                        gr.Markdown("Rename table aliases in the soldered SQL:")
                        alias_old = gr.Textbox(label="Old Alias", placeholder="e.g., t1")
                        alias_new = gr.Textbox(label="New Alias", placeholder="e.g., defects")
                    
                    solder_btn = gr.Button("Solder Query", variant="primary", size="lg")
                    report_btn = gr.Button("View Elevation Report", variant="secondary")
                
                with gr.Column():
                    gr.Markdown("#### Soldered Output")
                    soldered_sql_output = gr.Code(label="Final SQL", language="sql", lines=10)
                    
                    solder_details = gr.Markdown(label="Solder Details")
                    
                    solder_report_output = gr.Markdown(label="Elevation Report")
            
            def run_solder(intent, concept, dialect, old_alias, new_alias):
                if not intent:
                    return "-- Select an intent to solder", "Select an intent above."
                
                overrides = {}
                if old_alias and old_alias.strip() and new_alias and new_alias.strip():
                    overrides[old_alias.strip()] = new_alias.strip()
                
                result = solder.solder(
                    intent_name=intent,
                    target_concept=concept.strip() if concept and concept.strip() else None,
                    target_dialect=dialect or "sqlite",
                    context_overrides=overrides if overrides else None
                )
                
                details = f"## Solder Result\n\n"
                details += f"**Binding Key:** `{result.binding_key}`\n\n"
                details += f"**Perspective:** {result.perspective}\n\n"
                details += f"**Concept:** {result.concept}\n\n"
                details += f"**Logic Type:** {result.logic_type}\n\n"
                details += f"**Elevation Weight:** {result.elevation_weight}\n\n"
                details += f"**Dialect:** {result.dialect}\n\n"
                
                if result.ast_operations:
                    details += "### AST Operations\n"
                    for op in result.ast_operations:
                        details += f"- {op}\n"
                    details += "\n"
                
                if result.warnings:
                    details += "### Warnings\n"
                    for w in result.warnings:
                        details += f"- {w}\n"
                
                return result.soldered_sql, details
            
            def run_report(intent):
                if not intent:
                    return "Select an intent to view the elevation report."
                return solder.get_solder_report(intent)
            
            solder_btn.click(
                fn=run_solder,
                inputs=[solder_intent, solder_concept, solder_dialect, alias_old, alias_new],
                outputs=[soldered_sql_output, solder_details]
            )
            
            report_btn.click(
                fn=run_report,
                inputs=[solder_intent],
                outputs=solder_report_output
            )
            
            gr.Markdown("---")
            gr.Markdown("""
            ### Preview Solder (Multi-Concept Assembly)
            
            Combine **multiple concepts** into a single cohesive query. The engine resolves 
            each concept's approved snippet, applies elevation weights, and assembles them 
            as projections from a base table. Suppressed concepts become `NULL`.
            """)
            
            with gr.Row():
                with gr.Column():
                    assemble_intent = gr.Dropdown(
                        choices=intent_choices,
                        label="Intent",
                        info="Controls which concepts are elevated vs suppressed",
                        interactive=True
                    )
                    
                    perspective_choices = ["Finance", "Quality", "Operations", "Customer", "Compliance"]
                    assemble_perspective = gr.Dropdown(
                        choices=perspective_choices,
                        label="Perspective",
                        info="SME perspective for snippet resolution",
                        interactive=True
                    )
                    
                    assemble_concepts = gr.Textbox(
                        label="Concepts (comma-separated)",
                        placeholder="e.g., DefectSeverityCost, DefectSeverityQuality, DefectSeverityCustomer",
                        info="List the concepts to include as projections"
                    )
                    
                    assemble_base_table = gr.Textbox(
                        label="Base Table",
                        value="stg_manufacturing_flat",
                        info="FROM clause table name"
                    )
                    
                    assemble_dialect = gr.Dropdown(
                        choices=[
                            ("SQLite", "sqlite"),
                            ("T-SQL (SQL Server)", "tsql"),
                            ("PostgreSQL", "postgres"),
                            ("MySQL", "mysql"),
                            ("BigQuery", "bigquery"),
                        ],
                        value="sqlite",
                        label="Target Dialect",
                        interactive=True
                    )
                    
                    assemble_btn = gr.Button("Assemble Query", variant="primary", size="lg")
                
                with gr.Column():
                    gr.Markdown("#### Assembled Output")
                    assembled_sql_output = gr.Code(label="Assembled SQL", language="sql", lines=12)
                    assembled_report = gr.Markdown(label="Assembly Report")
            
            def run_assemble(intent, perspective, concepts_str, base_table, dialect):
                if not intent:
                    return "-- Select an intent", "Select an intent above."
                if not concepts_str or not concepts_str.strip():
                    return "-- Enter concepts", "Enter comma-separated concept names."
                
                concepts = [c.strip() for c in concepts_str.split(",") if c.strip()]
                result = solder.assemble_query(
                    intent=intent,
                    perspective=perspective or "",
                    concepts=concepts,
                    base_table=base_table or "stg_manufacturing_flat",
                    target_dialect=dialect or "sqlite"
                )
                
                report_md = f"## Assembly Report\n\n"
                report_md += f"**Intent:** {result.get('intent', '')}\n\n"
                report_md += f"**Perspective:** {result.get('perspective', '')}\n\n"
                report_md += f"**Base Table:** `{result.get('base_table', '')}`\n\n"
                report_md += f"**Concepts Resolved:** {result.get('concept_count', 0)} / {len(concepts)}\n\n"
                report_md += f"**Dialect:** {result.get('dialect', 'sqlite')}\n\n"
                
                if result.get("report"):
                    report_md += "### Concept Resolution\n"
                    for line in result["report"]:
                        report_md += f"{line}\n"
                    report_md += "\n"
                
                if result.get("warnings"):
                    report_md += "### Warnings\n"
                    for w in result["warnings"]:
                        report_md += f"- {w}\n"
                
                return result.get("sql", ""), report_md
            
            assemble_btn.click(
                fn=run_assemble,
                inputs=[assemble_intent, assemble_perspective, assemble_concepts, assemble_base_table, assemble_dialect],
                outputs=[assembled_sql_output, assembled_report]
            )
        
        with gr.Tab("🔄 Graph Sync"):
            gr.Markdown("""
            ### ArangoDB Graph Sync
            
            Push the semantic layer from SQLite into ArangoDB as a named graph (`semantic_graph`).
            This keeps your cloud graph database in sync with local changes to intents, perspectives,
            concepts, elevation weights, and SME-approved bindings.
            
            **Graph structure:**
            
            | Edge | From | To | Purpose |
            |------|------|----|---------|
            | `OPERATES_WITHIN` | Intent | Perspective | Which lens an intent uses |
            | `ELEVATES` | Intent | Concept | Elevation weight (1.0 = primary, 0.0 = neutral) |
            | `USES_DEFINITION` | Perspective | Concept | Which concepts a perspective defines |
            | `BOUND_TO` | Intent | Binding | Links intent to its approved SQL snippet |
            
            **How to use:**
            1. Click **Dry Run** to preview what will be synced (reads SQLite only, no ArangoDB connection)
            2. Click **Sync to ArangoDB** to push changes (creates new documents or updates existing ones)
            """)
            
            with gr.Row():
                with gr.Column():
                    sync_dry_run_btn = gr.Button("Dry Run (Preview)", variant="secondary")
                    sync_live_btn = gr.Button("Sync to ArangoDB", variant="primary")
                with gr.Column():
                    sync_status = gr.Textbox(label="Status", interactive=False, value="Ready — click Dry Run or Sync")
            
            sync_report_output = gr.Code(label="Sync Report", language=None, lines=22)
            
            def run_graph_sync(dry_run: bool):
                try:
                    from graph_sync import sync_graph
                    report = sync_graph(dry_run=dry_run)
                    if dry_run:
                        status = f"DRY RUN — {report.total_vertices} vertices, {report.total_edges} edges ready to sync"
                    elif report.success:
                        status = f"SUCCESS — {report.total_vertices} vertices, {report.total_edges} edges synced to ArangoDB"
                    else:
                        status = f"FAILED — see errors in report below"
                    return status, report.summary()
                except Exception as e:
                    return f"ERROR: {e}", str(e)
            
            sync_dry_run_btn.click(
                fn=lambda: run_graph_sync(dry_run=True),
                outputs=[sync_status, sync_report_output]
            )
            sync_live_btn.click(
                fn=lambda: run_graph_sync(dry_run=False),
                outputs=[sync_status, sync_report_output]
            )
        
        with gr.Tab("🎨 Query Palette"):
            gr.Markdown("### SQLMesh Query Palette\nRun SQL against the SQLMesh virtual layer. Queries resolve through masked/hashed physical tables automatically.")

            def get_sqlmesh_models():
                try:
                    from sqlmesh import Context as SMContext
                    sqlmesh_path = os.path.join(os.path.dirname(__file__), '..', 'Utilities', 'SQLMesh')
                    ctx = SMContext(paths=sqlmesh_path)
                    return sorted(m for m in ctx.models)
                except Exception:
                    return []

            palette_models = get_sqlmesh_models()
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("**Virtual Layer Explorer**")
                    model_dropdown = gr.Dropdown(
                        choices=palette_models,
                        label="Quick Select Model",
                        interactive=True,
                    )
                    generate_btn = gr.Button("Generate SELECT *")
                with gr.Column(scale=3):
                    palette_query = gr.Textbox(
                        label="SQL Query",
                        value="SELECT * FROM staging.stg_suppliers LIMIT 10",
                        lines=6,
                        interactive=True,
                    )
                    run_palette_btn = gr.Button("Run Query", variant="primary")

            palette_status = gr.Markdown("")
            palette_results = gr.Dataframe(label="Query Results", wrap=True)
            palette_dim_check = gr.Markdown("")

            def gen_select(model_name):
                if not model_name:
                    return "SELECT * FROM staging.stg_suppliers LIMIT 10"
                return f"SELECT * FROM {model_name} LIMIT 100"

            def run_palette_query(query):
                if not query or not query.strip():
                    return "Enter a query above.", None, ""
                try:
                    from sqlmesh import Context as SMContext
                    import pandas as pd
                    sqlmesh_path = os.path.join(os.path.dirname(__file__), '..', 'Utilities', 'SQLMesh')
                    ctx = SMContext(paths=sqlmesh_path)
                    df = ctx.fetchdf(query)
                    dim_msg = ""
                    if 'vendor_id' in df.columns:
                        unique_vendors = df['vendor_id'].unique()
                        dim_msg = f"**Dimensionality Check:** Detected `vendor_id` — {len(unique_vendors)} unique masked vendors: {', '.join(map(str, unique_vendors[:20]))}"
                    return f"Returned **{len(df)}** rows, **{len(df.columns)}** columns.", df, dim_msg
                except Exception as e:
                    return f"**Error:** {e}", None, ""

            generate_btn.click(fn=gen_select, inputs=[model_dropdown], outputs=[palette_query])
            run_palette_btn.click(fn=run_palette_query, inputs=[palette_query], outputs=[palette_status, palette_results, palette_dim_check])

        with gr.Tab("🔌 MCP Endpoints"):
            gr.Markdown("""
            ### Model Context Protocol API
            
            These endpoints enable AI agent integration:
            
            | Endpoint | MCP Component | Description |
            |----------|---------------|-------------|
            | `GET /mcp/discover` | Discovery | Lists all available tools |
            | `GET /mcp/tools/get_schema` | Resource | Sample schema definition |
            | `GET /mcp/tools/get_all_ddl` | Resource | Full database DDL |
            | `GET /mcp/tools/get_saved_categories` | Resource | Query category index |
            | `GET /mcp/tools/get_saved_queries?category_id=X` | Resource | Ground truth SQL |
            | `POST /mcp/tools/generate_sql` | Tool | NL to SQL conversion |
            | `GET /mcp/tools/get_table_ddl?table_name=X` | Tool | Single table DDL |
            
            ### Usage with VS Code + Copilot
            
            1. Go to **Copilot Context** tab
            2. Click the **Copy to Copilot** button to build context
            3. Paste context into Copilot Chat
            4. Ask follow-up questions about your manufacturing data
            """)
    
    return demo


get_db_engine()
initial_tables = get_all_tables()
print(f"SQLite database initialized with {len(initial_tables)} tables")

gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(app, gradio_app, path="/gradio")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
