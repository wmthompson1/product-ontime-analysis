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
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import gradio as gr
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.environ.get("DATABASE_URL")
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
            rows = [list(row) for row in result.fetchall()]
            return {"error": None, "columns": columns, "rows": rows[:100]}
    except SQLAlchemyError as e:
        return {"error": str(e), "rows": [], "columns": []}

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
        # 🏭 Manufacturing Inventory SQL Generator
        
        Convert natural language questions to SQL queries for inventory management.
        This tool follows the **Model Context Protocol (MCP)** pattern for AI tool integration.
        
        ### Example Questions:
        - "Show me parts that are low on stock"
        - "What's the total inventory value by category?"
        - "Which suppliers have the best quality ratings?"
        - "Show transaction activity for the last 30 days"
        """)
        
        with gr.Tab("🔍 Query Generator"):
            with gr.Row():
                with gr.Column():
                    query_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., Show me all parts below reorder point",
                        lines=2
                    )
                    include_explanation = gr.Checkbox(label="Include Explanation", value=True)
                    generate_btn = gr.Button("Generate SQL", variant="primary")
                
                with gr.Column():
                    sql_output = gr.Code(label="Generated SQL", language="sql")
                    explanation_output = gr.Textbox(label="Explanation", lines=3)
                    with gr.Row():
                        tables_output = gr.Textbox(label="Tables Used")
                        complexity_output = gr.Textbox(label="Complexity")
            
            generate_btn.click(
                fn=process_query,
                inputs=[query_input, include_explanation],
                outputs=[sql_output, explanation_output, tables_output, complexity_output]
            )
        
        with gr.Tab("📋 SQL Templates"):
            gr.Markdown("### Pre-built SQL templates for common inventory queries")
            template_dropdown = gr.Dropdown(
                choices=list(SQL_TEMPLATES.keys()),
                label="Select Template"
            )
            template_output = gr.Code(label="SQL Template", language="sql")
            template_dropdown.change(fn=get_template, inputs=template_dropdown, outputs=template_output)
        
        with gr.Tab("📊 Sample Schema"):
            gr.Markdown("### Sample Schema for Inventory Management (Static)")
            schema_btn = gr.Button("Show Sample Schema")
            schema_output = gr.Code(label="Schema Definition", language="json")
            schema_btn.click(fn=show_schema, outputs=schema_output)
        
        with gr.Tab("🗄️ Live Database"):
            gr.Markdown("""
            ### PostgreSQL Database Schema
            
            Pull CREATE TABLE statements directly from the connected PostgreSQL database.
            This shows the actual table structures for your manufacturing analytics system.
            """)
            
            with gr.Row():
                with gr.Column():
                    refresh_tables_btn = gr.Button("Refresh Table List", variant="secondary")
                    table_dropdown = gr.Dropdown(
                        choices=get_all_tables(),
                        label="Select Table",
                        interactive=True
                    )
                    get_ddl_btn = gr.Button("Get Table DDL", variant="primary")
                    get_all_ddl_btn = gr.Button("Get All Tables DDL", variant="secondary")
                
                with gr.Column():
                    ddl_output = gr.Code(label="CREATE TABLE SQL", language="sql", lines=20)
            
            def refresh_table_list():
                tables = get_all_tables()
                return gr.Dropdown(choices=tables, value=None)
            
            refresh_tables_btn.click(fn=refresh_table_list, outputs=table_dropdown)
            get_ddl_btn.click(fn=get_table_ddl_gradio, inputs=table_dropdown, outputs=ddl_output)
            get_all_ddl_btn.click(fn=get_all_ddl_gradio, outputs=ddl_output)
        
        with gr.Tab("⚡ SQL Workbench"):
            gr.Markdown("""
            ### Execute SQL Queries
            
            Enter and execute SELECT queries against the live PostgreSQL database.
            
            **Safety Features:**
            - Only SELECT queries are allowed
            - Results limited to 100 rows
            - Dangerous keywords (DROP, DELETE, UPDATE, etc.) are blocked
            """)
            
            with gr.Row():
                with gr.Column():
                    sql_input = gr.Code(
                        label="Enter SQL Query",
                        language="sql",
                        lines=8,
                        value="SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 10;"
                    )
                    with gr.Row():
                        execute_btn = gr.Button("Execute Query", variant="primary")
                        clear_btn = gr.Button("Clear", variant="secondary")
                    
                    gr.Markdown("#### Quick Queries")
                    with gr.Row():
                        gr.Button("List Tables").click(
                            fn=lambda: "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;",
                            outputs=sql_input
                        )
                        gr.Button("Schema Nodes").click(
                            fn=lambda: "SELECT * FROM schema_nodes LIMIT 20;",
                            outputs=sql_input
                        )
                        gr.Button("Schema Edges").click(
                            fn=lambda: "SELECT * FROM schema_edges LIMIT 20;",
                            outputs=sql_input
                        )
                
                with gr.Column():
                    results_output = gr.Textbox(label="Query Results", lines=15, max_lines=30)
                    stats_output = gr.Textbox(label="Statistics")
            
            execute_btn.click(fn=execute_sql_gradio, inputs=sql_input, outputs=[results_output, stats_output])
            clear_btn.click(fn=lambda: ("", ""), outputs=[results_output, stats_output])
        
        with gr.Tab("🔌 MCP Integration"):
            gr.Markdown("""
            ### Model Context Protocol (MCP) Integration
            
            This Space exposes MCP-compliant endpoints for AI agent integration:
            
            | Endpoint | Description |
            |----------|-------------|
            | `GET /mcp/discover` | Discovery endpoint - lists all available tools |
            | `POST /mcp/tools/generate_sql` | Convert natural language to SQL |
            | `GET /mcp/tools/get_schema` | Get sample database schema |
            | `GET /mcp/tools/get_sql_templates` | Get SQL templates |
            | `POST /mcp/tools/analyze_csv` | Analyze CSV for schema suggestions |
            | `GET /mcp/tools/get_db_tables` | **NEW** - List all PostgreSQL tables |
            | `GET /mcp/tools/get_table_ddl?table_name=X` | **NEW** - Get CREATE TABLE for specific table |
            | `GET /mcp/tools/get_all_ddl` | **NEW** - Get CREATE TABLE for all tables |
            | `POST /mcp/tools/execute_sql` | **NEW** - Execute read-only SQL query |
            
            ### Database Connection
            
            The app connects to PostgreSQL via `DATABASE_URL` environment variable.
            This enables live schema introspection and query execution against your
            manufacturing analytics database with 24 tables including:
            - `schema_nodes` and `schema_edges` for graph-based SQL generation
            - `production_quality`, `suppliers`, `equipment_metrics`
            - `corrective_actions`, `non_conformant_materials`, and more
            
            ### Example: Get All Table DDL
            ```bash
            curl http://localhost:8000/mcp/tools/get_all_ddl
            ```
            """)
    
    return demo


gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(app, gradio_app, path="/gradio")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
