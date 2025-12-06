# Product On-Time Analysis

NPM-first development setup with embedded Postgres (pg-embed), graphology graph building, and optional Python NetworkX exporter for aerospace manufacturing supply chain analysis.

## Features

- **Embedded Postgres**: Uses `pg-embed` to run Postgres locally without external dependencies
- **Aerospace Manufacturing Schema**: Comprehensive schema covering suppliers, parts, assemblies, products, orders, production, and quality
- **Sample Data**: Pre-populated test data for quick validation
- **Graph Analysis**: Build supply chain graphs using graphology (Node.js) or NetworkX (Python)
- **SQL Validation Scripts**: Numbered validation queries for quick data verification

## Prerequisites

- Node.js 16+ and npm
- Python 3.8+ (optional, for NetworkX analysis)

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Initialize Database

Run embedded Postgres, create schema, and load sample data:

```bash
npm run init-db
```

This will:
- Start an embedded Postgres instance
- Create the `pta_dev` database
- Apply the schema from `sql/schema.sql`
- Insert sample data from `sql/sample_data.sql`
- Stop Postgres automatically

**To keep Postgres running** for further queries:

```bash
npm run init-db-keep
```

Connection string when Postgres is running:
```
postgresql://postgres:postgres@localhost:5432/pta_dev
```

### 3. Build Supply Chain Graph

Build a directed graph of suppliers → parts → assemblies → products:

```bash
npm run build-graph-node
```

This creates:
- `graph_nodes.csv` - All nodes with metadata
- `graph_edges.csv` - All edges with relationships

### 4. Optional: NetworkX Analysis (Python)

If you want to use Python's NetworkX for advanced graph analysis and visualization:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run NetworkX builder
python scripts/networkx_build.py
```

This generates:
- `supply_chain_graph.png` - Visual representation of the supply chain
- Graph analytics (DAG check, connectivity, node types)

## SQL Validation Scripts

Two numbered validation scripts are provided in `sql/validation/`:

1. **01_assemblies_part_counts.sql** - Lists assemblies with distinct part counts and total quantities
2. **02_supplier_exposure.sql** - Calculates supplier cost exposure per assembly

To run them (when Postgres is running):

```bash
psql postgresql://postgres:postgres@localhost:5432/pta_dev -f sql/validation/01_assemblies_part_counts.sql
psql postgresql://postgres:postgres@localhost:5432/pta_dev -f sql/validation/02_supplier_exposure.sql
```

## Project Structure

```
.
├── package.json              # NPM dependencies and scripts
├── sql/
│   ├── schema.sql           # Aerospace manufacturing schema
│   ├── sample_data.sql      # Sample test data
│   └── validation/          # Numbered SQL validation scripts
│       ├── 01_assemblies_part_counts.sql
│       └── 02_supplier_exposure.sql
├── scripts/
│   ├── init_db.js           # Database initialization script
│   ├── build_graph_node.js  # Node.js graph builder (graphology)
│   └── networkx_build.py    # Python NetworkX exporter
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Schema Overview

The schema (`pta` schema in Postgres) includes:

- **suppliers** - Supplier information
- **parts** - Individual parts with costs and supplier links
- **assemblies** - Assembly definitions
- **assembly_parts** - Many-to-many: assemblies ↔ parts with quantities
- **products** - Final products linked to assemblies
- **customers** - Customer information
- **orders** - Customer orders
- **order_items** - Order line items
- **machines** - Production machines
- **production_runs** - Manufacturing runs
- **maintenance_records** - Machine maintenance logs
- **quality_checks** - Quality control results
- **shipments** - Shipping information

## Environment Variables

Create a `.env` file (see `.env.example`) to customize:

```
DB_NAME=pta_dev
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

## Development Workflow

1. **Schema changes**: Edit `sql/schema.sql` and re-run `npm run init-db`
2. **Data changes**: Edit `sql/sample_data.sql` and re-run `npm run init-db`
3. **Graph updates**: After data changes, run `npm run build-graph-node`
4. **Validation**: Run SQL validation scripts to verify data integrity

## Troubleshooting

### Postgres port already in use

If port 5432 is already taken, either stop the existing Postgres instance or modify the port in scripts.

### Permission issues

Ensure the `.pgdata` directory is writable. This is where pg-embed stores the Postgres data.

### Graph build fails

Make sure Postgres is running (use `npm run init-db-keep`) before running `npm run build-graph-node`.

## License

MIT
