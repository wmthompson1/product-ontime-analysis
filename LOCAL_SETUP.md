# Local Development Setup (SQLite - No External Database)

## Prerequisites
- Python 3.10+
- Node.js / npm
- Git

## Quick Start

### 1. Clone and Setup Python
```bash
git clone <your-repo>
cd 20241019-Python

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

pip install gradio sqlalchemy
```

### 2. Database is Automatic
The app uses SQLite - no database installation needed!

Schema is automatically loaded from `schema/schema_sqlite.sql` on first run.

Database file: `schema/manufacturing.db`

### 3. Run the HF Space
```bash
cd hf-space-inventory-sqlgen
python app.py
```

Open: http://localhost:5000/gradio

## Verify Tables
```bash
python -c "
from hf_space_inventory_sqlgen.app import get_all_tables
print(f'Tables: {len(get_all_tables())}')
print(get_all_tables()[:5])
"
```

Expected: 24 tables including corrective_actions, daily_deliveries, etc.

## Ground Truth SQL

Validated queries are in `schema/queries/` organized by category:
- `quality_control/` - Defect rates, SPC analysis
- `supplier_performance/` - On-time delivery, ratings
- `equipment_reliability/` - MTBF, maintenance
- `production_analytics/` - Throughput, scheduling

## Environment Variables (Optional)

Create `.env` file only if needed for API keys:
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

## No External Database Required

This project uses:
- SQLite for local database (no installation)
- schema/schema_sqlite.sql as the DDL source
- npm for package management (frontend only)
