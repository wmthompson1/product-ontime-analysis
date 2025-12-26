# Product On-Time Analysis

A comprehensive manufacturing analytics platform for tracking supplier performance, product quality, and on-time delivery metrics. Features an NPM-first embedded PostgreSQL setup, graph-based supply chain analysis, and AI-powered semantic layer for natural language queries.

## Features

- **Supply Chain Tracking**: Monitor suppliers, parts, assemblies, and products
- **Delivery Performance**: Track on-time delivery rates and late shipments
- **Quality Metrics**: Analyze production runs and defect rates
- **Graph Analytics**: Visualize supply chain relationships using Graphology (Node.js) and NetworkX (Python)
- **SQL Validation**: Pre-built queries for assemblies part counts and supplier exposure analysis
- **Semantic Layer**: Natural language to SQL conversion using LangChain

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- PostgreSQL 14+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/wmthompson1/product-ontime-analysis.git
   cd product-ontime-analysis
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and API keys
   ```

5. **Initialize the database**
   ```bash
   # Create schema only
   npm run db:init
   
   # Or create schema with sample data
   npm run db:init:sample
   ```

## Database Management

### Initialize Database
```bash
# Create schema
npm run db:init

# Create schema with sample data
npm run db:init:sample

# Reset database (drop and recreate with sample data)
npm run db:reset
```

### Manual Database Operations
```bash
# Run schema creation directly
psql -U postgres -d product_ontime -f sql/schema.sql

# Load sample data
psql -U postgres -d product_ontime -f sql/sample_data.sql

# Run validation queries
psql -U postgres -d product_ontime -f sql/validation/01_assemblies_part_counts.sql
psql -U postgres -d product_ontime -f sql/validation/02_supplier_exposure.sql
```

## Graph Analysis

### Build Supply Chain Graph (Node.js with Graphology)
```bash
# Build and analyze graph
npm run graph:build

# Custom output
node scripts/build_graph_node.js --output supply_chain.json --analyze
```

### Build Supply Chain Graph (Python with NetworkX)
```bash
# Build and analyze graph
npm run graph:build:python

# Or run directly with Python
python scripts/networkx_build.py --analyze --visualize
```

## Database Schema

### Core Tables

- **suppliers**: Supplier information and contact details
- **parts**: Part catalog with costs and lead times
- **products**: Product definitions and families
- **assemblies**: Bill of materials (BOM) linking parts to products
- **deliveries**: Delivery records with on-time tracking
- **production_runs**: Production history with quality metrics
- **quality_metrics**: Detailed quality measurements

### Views

- **supplier_performance**: Aggregated supplier on-time delivery rates
- **product_quality**: Product-level defect rates
- **daily_delivery_summary**: Daily delivery statistics

## SQL Validation Queries

### 01: Assemblies Part Counts
Analyzes bill of materials complexity:
- Unique parts per product
- Total parts required
- Supplier exposure per product

```bash
psql -U postgres -d product_ontime -f sql/validation/01_assemblies_part_counts.sql
```

### 02: Supplier Exposure Analysis
Identifies supply chain risks:
- Parts supplied per supplier
- Products affected by supplier issues
- On-time delivery performance
- Single-source dependencies

```bash
psql -U postgres -d product_ontime -f sql/validation/02_supplier_exposure.sql
```

## Development

### Project Structure
```
product-ontime-analysis/
├── sql/
│   ├── schema.sql              # Database schema
│   ├── sample_data.sql         # Sample data
│   └── validation/
│       ├── 01_assemblies_part_counts.sql
│       └── 02_supplier_exposure.sql
├── scripts/
│   ├── init_db.js              # Database initialization (Node.js)
│   ├── build_graph_node.js     # Graph builder (Graphology)
│   └── networkx_build.py       # Graph builder (NetworkX)
├── app/                        # Flask application
├── templates/                  # HTML templates
├── package.json                # Node.js dependencies
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`: Database connection
- `FLASK_SECRET_KEY`: Flask session secret
- `OPENAI_API_KEY`: OpenAI API key for semantic layer
- `TAVILY_API_KEY`: Tavily API key for research capabilities

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

ISC

## Version

API 2.1.1
