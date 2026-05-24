# 🏭 Manufacturing Inventory SQL Generator

A **Hugging Face Space** that converts natural language questions to SQL queries for manufacturing inventory management. Built with the **Model Context Protocol (MCP)** pattern for seamless AI agent integration.

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Gradio](https://img.shields.io/badge/Gradio-4.0+-orange.svg)](https://gradio.app)

## 🎯 Features

- **Natural Language to SQL**: Convert plain English questions to optimized SQL queries
- **MCP-Compliant API**: Full Model Context Protocol support for AI agent integration
- **Manufacturing Focus**: Pre-built templates for inventory, suppliers, and transactions
- **Schema Introspection**: Automatic schema discovery and documentation
- **CSV Analysis**: Upload CSV files to auto-detect schema and generate queries

## 🚀 Quick Start

### Run Locally

```bash
# Clone the repository
git clone https://huggingface.co/spaces/YOUR-USERNAME/inventory-sqlgen
cd inventory-sqlgen

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Open http://localhost:7860 in your browser.

### Deploy to Hugging Face Spaces

1. Create a new Space at https://huggingface.co/new-space
2. Select **Gradio** as the SDK
3. Upload all files from this repository
4. Your Space will auto-deploy!

## ⚙️ Configuration

Set these environment variables before starting the server (copy `.env.example` to `.env` for local development; use Space Secrets on Hugging Face).

| Variable | Default | Description |
|----------|---------|-------------|
| `ERP_INSTANCE_NAME` | `ERP_Instance_1` | Display name for this ERP system. Shown as the group key in `/mcp/tools/list_schema_tables` and in the Gradio Schema tab. Set to your actual system name (e.g. `SAP_S4`, `Oracle_EBS`, `NetSuite`). |
| `QUERY_API_KEY` | _(none)_ | Optional bearer-token guard for write endpoints. Leave blank in development. |
| `OPENAI_API_KEY` | _(none)_ | Required for embedding-based semantic search and RAG features. |
| `TAVILY_API_KEY` | _(none)_ | Required for advanced RAG with live web retrieval. |
| `ARANGO_HOST` / `ARANGO_DB` | _(none)_ | Required for graph persistence to ArangoDB. |

### Verifying your configuration

After starting the server, hit the config endpoint to confirm the active values without reading logs:

```bash
curl http://localhost:7860/mcp/config
```

```json
{
  "erp_instance_name": "SAP_S4",
  "erp_instance_name_source": "env",
  "sqlite_db_path": "/path/to/manufacturing.db",
  "query_api_key_set": false
}
```

`erp_instance_name_source` is `"env"` when the variable was explicitly set, or `"default"` when the fallback value is in use.

## 📡 MCP API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/config` | GET | Returns active runtime configuration (ERP name, DB path, auth status) |
| `/mcp/discover` | GET | Discovery endpoint - lists all tools |
| `/mcp/tools/generate_sql` | POST | Convert natural language to SQL |
| `/mcp/tools/get_schema` | GET | Get database schema |
| `/mcp/tools/get_sql_templates` | GET | Get pre-built SQL templates |
| `/mcp/tools/analyze_csv` | POST | Analyze CSV for schema suggestions |

### Example: Generate SQL

```bash
curl -X POST "http://localhost:7860/mcp/tools/generate_sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me parts below reorder point", "include_explanation": true}'
```

Response:
```json
{
  "sql": "SELECT part_id, part_name, quantity_on_hand, reorder_point...",
  "explanation": "This query identifies parts where current stock is below the reorder point...",
  "tables_used": ["inventory"],
  "estimated_complexity": "simple"
}
```

## 🔧 SQL Templates

Pre-built templates for common manufacturing queries:

| Template | Description |
|----------|-------------|
| `low_stock` | Parts below reorder point |
| `inventory_value` | Total value by category |
| `supplier_performance` | Supplier quality ratings |
| `transaction_summary` | Recent transaction activity |

## 📊 Database Schema

The Space includes a sample manufacturing inventory schema:

### Tables

- **inventory**: Parts master data (part_id, quantity, cost, location)
- **suppliers**: Vendor information (lead time, quality rating)
- **transactions**: Inventory movements (receipts, issues, transfers)

### Relationships

```
suppliers ──1:N──► inventory ◄──N:1── transactions
```

## 🤖 AI Agent Integration

This Space follows the Model Context Protocol (MCP) pattern, making it easy to integrate with AI agents:

```python
import requests

# Discover available tools
discovery = requests.get("https://YOUR-SPACE.hf.space/mcp/discover").json()

# Use a tool
result = requests.post(
    "https://YOUR-SPACE.hf.space/mcp/tools/generate_sql",
    json={"query": "What's our total inventory value?"}
).json()

print(result["sql"])
```

## 🧪 Testing

Run the test client to verify all endpoints:

```bash
python test_client.py --base-url http://localhost:7860
```

## 📁 Project Structure

```
hf-space-inventory-sqlgen/
├── app.py                 # FastAPI + Gradio application
├── mcp_discovery.json     # MCP discovery response example
├── test_client.py         # Python test client
├── sample_inventory.csv   # Sample data for testing
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## 🏷️ Keywords

`text-to-sql` `manufacturing` `inventory-management` `mcp` `model-context-protocol` `natural-language-sql` `github-copilot` `ai-agent` `semantic-layer` `business-intelligence`

## 📝 License

MIT License - Feel free to use, modify, and distribute!

## 🙏 Acknowledgments

- Built for Berkeley Haas AI Strategy capstone project
- Inspired by LangChain semantic layer patterns
- MCP specification by Anthropic

---

**Made with ❤️ for manufacturing intelligence**
