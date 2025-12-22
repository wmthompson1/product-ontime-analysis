# VS Code MCP Migration Guide

This guide documents how to use the Manufacturing SQL Semantic Layer from VS Code using the Hugging Face MCP server.

## Tested MCP Endpoints (All Working)

### 1. Discovery Endpoint
```bash
GET /mcp/discover
```
Returns MCP capability manifest with all available tools, resources, and prompts.

### 2. Schema & Tables

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/get_db_tables` | GET | List all 20 manufacturing tables |
| `/mcp/tools/get_table_ddl?table_name=<name>` | GET | Get CREATE TABLE for specific table |
| `/mcp/tools/get_all_ddl` | GET | Get DDL for all tables |
| `/mcp/tools/get_schema` | GET | Get inventory schema (legacy) |

**Example:**
```bash
curl http://localhost:5000/mcp/tools/get_db_tables
# Returns: {"tables":["daily_deliveries","equipment_metrics",...], "count":20}

curl "http://localhost:5000/mcp/tools/get_table_ddl?table_name=suppliers"
# Returns: {"table_name":"suppliers", "ddl":"CREATE TABLE suppliers (...)"}
```

### 3. Ground Truth SQL Queries

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/get_saved_categories` | GET | List query categories with counts |
| `/mcp/tools/get_saved_queries?category_id=<id>` | GET | Get queries by category |

**Categories Available:**
- `quality_control` - Defect tracking, NCM management (3 queries)
- `supplier_performance` - OTD metrics, supplier scorecards (2 queries)
- `equipment_reliability` - OEE, downtime, MTBF (3 queries)
- `production_analytics` - Schedule adherence, quality costs (3 queries)

**Example:**
```bash
curl http://localhost:5000/mcp/tools/get_saved_categories
curl "http://localhost:5000/mcp/tools/get_saved_queries?category_id=quality_control"
```

### 4. SQL Execution (Read-Only)

| Endpoint | Method | Content-Type | Description |
|----------|--------|--------------|-------------|
| `/mcp/tools/execute_sql` | POST | form-data | Execute SELECT queries |

**Example:**
```bash
curl -X POST "http://localhost:5000/mcp/tools/execute_sql" \
  -d "sql=SELECT supplier_name, performance_rating FROM suppliers LIMIT 5"
```

**Safety:** Only SELECT queries allowed. DROP, DELETE, UPDATE, INSERT blocked.

### 5. SQL Generation (AI-Powered)

| Endpoint | Method | Content-Type | Description |
|----------|--------|--------------|-------------|
| `/mcp/tools/generate_sql` | POST | JSON | Natural language to SQL |

**Example:**
```bash
curl -X POST "http://localhost:5000/mcp/tools/generate_sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me suppliers with low performance ratings"}'
```

### 6. SQL Templates

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/tools/get_sql_templates?template_name=<name>` | GET | Get pre-built SQL templates |

**Available Templates:**
- `low_stock` - Inventory below threshold
- `inventory_value` - Calculate inventory valuation
- `supplier_performance` - Supplier metrics
- `transaction_summary` - Transaction summaries

**Example:**
```bash
curl "http://localhost:5000/mcp/tools/get_sql_templates?template_name=low_stock"
```

### 7. CSV Analysis

| Endpoint | Method | Content-Type | Description |
|----------|--------|--------------|-------------|
| `/mcp/tools/analyze_csv` | POST | JSON | Analyze uploaded CSV to suggest schema and queries |

**Example:**
```bash
curl -X POST "http://localhost:5000/mcp/tools/analyze_csv" \
  -H "Content-Type: application/json" \
  -d '{"csv_content": "col1,col2\nval1,val2"}'
```

### 8. Save Query (Protected)

| Endpoint | Method | Content-Type | Auth Required | Description |
|----------|--------|--------------|---------------|-------------|
| `/mcp/tools/save_query` | POST | JSON | X-API-Key header | Save ground truth SQL queries |

**Note:** Requires `QUERY_API_KEY` environment variable set on server.

---

## VS Code Setup Options

### Option A: Hugging Face Spaces Deployment (Recommended for Work)

1. **Deploy to HF Spaces:**
   - Push `hf-space-inventory-sqlgen/` to a new Hugging Face Space
   - Select Gradio SDK
   - Space will run at: `https://<your-username>-<space-name>.hf.space`

2. **Configure VS Code MCP Extension:**
   - Install the Hugging Face MCP extension for VS Code
   - Add your Space URL as the MCP server endpoint

3. **Files Needed for HF Spaces:**
   ```
   hf-space-inventory-sqlgen/
   ├── app.py              # Main Gradio + FastAPI app
   ├── requirements.txt    # Python dependencies
   └── schema/
       ├── manufacturing.db        # SQLite database
       ├── schema_sqlite.sql       # Schema DDL
       └── queries/                # Ground truth SQL files
           ├── quality_control.sql
           ├── supplier_performance.sql
           ├── equipment_reliability.sql
           └── production_analytics.sql
   ```

### Option B: Local Development (Your Machine)

1. **Clone the repo locally:**
   ```bash
   git clone <your-github-repo>
   cd hf-space-inventory-sqlgen
   ```

2. **Install dependencies:**
   ```bash
   pip install gradio fastapi uvicorn sqlalchemy pydantic
   ```

3. **Run the server:**
   ```bash
   python app.py
   # Runs on http://localhost:5000
   ```

4. **Configure VS Code:**
   - Point MCP client to `http://localhost:5000`

---

## GitHub Copilot Integration Workflow

The Gradio UI provides a "Copy to Copilot" button that bundles:

1. **System Prompt** - Manufacturing domain context
2. **Schema DDL** - Top 10 table definitions
3. **Ground Truth Examples** - Validated SQL patterns

**Workflow:**
1. Open the Gradio UI (`/` endpoint)
2. Enter your natural language question
3. Click "Copy to Copilot"
4. Paste into GitHub Copilot Chat
5. Copilot generates SQL with proper context

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `QUERY_API_KEY` | No | Only needed for `/mcp/tools/save_query` endpoint |
| `HUGGINGFACE_TOKEN` | No | Optional for HF Hub features |

**Note:** All read endpoints work without authentication.

---

## MCP Tool Definitions

The `/mcp/discover` endpoint returns this tool manifest for MCP clients:

```json
{
  "name": "manufacturing-inventory-sqlgen",
  "version": "1.0.0",
  "tools": [
    {"name": "generate_sql", "description": "Convert natural language to SQL"},
    {"name": "get_schema", "description": "Get database schema"},
    {"name": "get_sql_templates", "description": "Get SQL templates"},
    {"name": "analyze_csv", "description": "Analyze uploaded CSV"},
    {"name": "get_db_tables", "description": "Get list of all tables"},
    {"name": "get_table_ddl", "description": "Get DDL for specific table"},
    {"name": "get_all_ddl", "description": "Get DDL for all tables"},
    {"name": "execute_sql", "description": "Execute SELECT queries"}
  ]
}
```

---

## Database Schema Summary

**20 Manufacturing Tables:**

| Category | Tables |
|----------|--------|
| Quality | `product_defects`, `non_conformant_materials`, `production_quality`, `quality_costs` |
| Equipment | `equipment_metrics`, `equipment_reliability`, `downtime_events`, `failure_events`, `effectiveness_metrics` |
| Supply Chain | `suppliers`, `daily_deliveries` |
| Production | `production_schedule`, `product_lines` |
| Reference | `manufacturing_acronyms`, `industry_benchmarks`, `maintenance_targets` |
| Metadata | `schema_edges`, `schema_nodes` |
| System | `users`, `financial_impact` |

---

## Quick Test Commands

```bash
# Test discovery
curl http://localhost:5000/mcp/discover | jq

# List tables
curl http://localhost:5000/mcp/tools/get_db_tables

# Get DDL for a table
curl "http://localhost:5000/mcp/tools/get_table_ddl?table_name=product_defects"

# Get ground truth SQL examples
curl http://localhost:5000/mcp/tools/get_saved_categories
curl "http://localhost:5000/mcp/tools/get_saved_queries?category_id=quality_control"

# Execute a query
curl -X POST http://localhost:5000/mcp/tools/execute_sql \
  -d "sql=SELECT * FROM product_defects LIMIT 5"
```

---

## Migration Checklist

- [ ] Push code to GitHub (keys checked - safe)
- [ ] Create Hugging Face Space with Gradio SDK
- [ ] Upload `hf-space-inventory-sqlgen/` folder contents
- [ ] Verify Space is running at public URL
- [ ] Install VS Code MCP extension
- [ ] Configure MCP client with Space URL
- [ ] Test endpoints from VS Code
