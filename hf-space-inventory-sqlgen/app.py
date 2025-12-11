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
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import gradio as gr
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.environ.get("DATABASE_URL")
SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema")
QUERIES_DIR = os.path.join(SCHEMA_DIR, "queries")
QUERY_API_KEY = os.environ.get("QUERY_API_KEY", "")
db_engine = None

def get_db_engine():
    """Get or create database engine"""
    global db_engine
    if db_engine is None and DATABASE_URL:
        db_engine = create_engine(DATABASE_URL)
    return db_engine

def get_table_create_sql(table_name: str) -> str:
    """Generate CREATE TABLE SQL for a given table"""
    engine = get_db_engine()
    if not engine:
        return "-- Database not connected"
    try:
        dialect = engine.dialect.name
        # SQLite fallback: read CREATE statement from sqlite_master
        if dialect == 'sqlite':
            with engine.connect() as conn:
                res = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name = :t"), {"t": table_name})
                row = res.fetchone()
                if not row or not row[0]:
                    return f"-- Table '{table_name}' not found"
                return row[0]

        # Default: Postgres-style introspection (information_schema)
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
    """Get list of all tables in the database"""
    engine = get_db_engine()
    if not engine:
        return []
    
    try:
        inspector = inspect(engine)
        dialect = engine.dialect.name
        if dialect == 'sqlite':
            return inspector.get_table_names()
        return inspector.get_table_names(schema='public')
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
        current_query = {"name": "", "description": "", "sql": ""}
        lines = content.split('\n')
        
        for line in lines:
            if line.startswith('-- Query:'):
                if current_query["sql"].strip():
                    queries.append(current_query)
                current_query = {"name": line.replace('-- Query:', '').strip(), "description": "", "sql": ""}
            elif line.startswith('-- Description:'):
                current_query["description"] = line.replace('-- Description:', '').strip()
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
        
        def build_copilot_context(question: str, include_schema: bool, include_queries: bool, selected_category: str) -> str:
            """Build MCP context package for Copilot"""
            context_parts = []
            
            context_parts.append("# MCP Context for Manufacturing SQL Generation\n")
            
            if question.strip():
                context_parts.append("## Prompt")
                context_parts.append(f"User Question: {question}\n")
            
            if include_schema:
                context_parts.append("## Resources: Database Schema")
                tables = get_all_tables()
                if tables:
                    for table in sorted(tables)[:10]:
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
                    include_schema = gr.Checkbox(label="Include Database Schema (top 10 tables)", value=True)
                    include_queries = gr.Checkbox(label="Include Ground Truth SQL Examples", value=True)
                    query_category = gr.Dropdown(
                        choices=get_category_choices(),
                        label="Query Category",
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
                inputs=[question_input, include_schema, include_queries, query_category],
                outputs=context_output
            )
        
        with gr.Tab("📊 Schema"):
            gr.Markdown("### Database Schema Resources")
            
            with gr.Row():
                with gr.Column():
                    refresh_tables_btn = gr.Button("Refresh Table List", variant="secondary")
                    table_dropdown = gr.Dropdown(
                        choices=get_all_tables(),
                        label="Select Table",
                        interactive=True
                    )
                    get_ddl_btn = gr.Button("View DDL", variant="primary")
                    get_all_ddl_btn = gr.Button("View All Tables", variant="secondary")
                
                with gr.Column():
                    ddl_output = gr.Code(label="CREATE TABLE SQL", language="sql", lines=20)
            
            def refresh_table_list():
                        tables = get_all_tables()
                        # Return an update for the existing Dropdown component instead of
                        # creating a new Dropdown object (which breaks dynamic updates).
                        return gr.update(choices=tables, value=None)
            
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
                if not category_id:
                    return gr.update(choices=[], value=None), ""
                queries = get_saved_queries(category_id)
                choices = [(q['name'], i) for i, q in enumerate(queries)]
                return gr.update(choices=choices, value=None), ""
            
            def load_query_sql(category_id: str, query_idx):
                if category_id is None or query_idx is None:
                    return "", ""
                queries = get_saved_queries(category_id)
                if query_idx < len(queries):
                    q = queries[query_idx]
                    return q['sql'], q['description']
                return "", ""
            
            with gr.Row():
                with gr.Column():
                    saved_category = gr.Dropdown(
                        choices=get_category_choices(),
                        label="Query Category",
                        interactive=True
                    )
                    saved_query_dropdown = gr.Dropdown(
                        choices=[],
                        label="Select Query",
                        interactive=True
                    )
                    saved_description = gr.Textbox(label="Description", interactive=False)
                
                with gr.Column():
                    saved_sql_output = gr.Code(label="SQL Query", language="sql", lines=15, show_label=True)
            
            saved_category.change(
                fn=load_queries_for_category,
                inputs=saved_category,
                outputs=[saved_query_dropdown, saved_sql_output]
            )
            
            saved_query_dropdown.change(
                fn=load_query_sql,
                inputs=[saved_category, saved_query_dropdown],
                outputs=[saved_sql_output, saved_description]
            )
        
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


gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(app, gradio_app, path="/gradio")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
