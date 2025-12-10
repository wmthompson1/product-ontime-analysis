# Local Development Setup (No Docker)

## Prerequisites
- PostgreSQL (via apt or Homebrew)
- Node.js / npm
- Python with gradio, sqlalchemy

## Database Setup

### Option A: Linux / Codespaces (apt)
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

sudo service postgresql start

sudo -u postgres createuser -s $(whoami)
createdb manufacturing_analytics

psql manufacturing_analytics < schema/schema_local.sql
```

### Option B: macOS (Homebrew)
```bash
brew services start postgresql@14
createdb manufacturing_analytics
psql manufacturing_analytics < schema/schema_local.sql
```

This creates all 24 tables from the Replit production schema.

**Note:** Use `schema_local.sql` (not `schema.sql`) - it removes the pgvector extension which isn't available on standard PostgreSQL.

## Environment Variables

Create `.env` file:
```
DATABASE_URL=postgresql://$(whoami)@localhost:5432/manufacturing_analytics
```

Or for Codespaces with default postgres user:
```
DATABASE_URL=postgresql://postgres@localhost:5432/manufacturing_analytics
```

## Ground Truth SQL

Validated queries are in `schema/queries/` organized by category:
- `quality_control/` - Defect rates, SPC analysis
- `supplier_performance/` - On-time delivery, ratings
- `equipment_reliability/` - MTBF, maintenance
- `production_analytics/` - Throughput, scheduling

## Testing the Schema

```bash
psql manufacturing_analytics -c "\dt"
```

Expected: 24 tables including users, products, suppliers, daily_deliveries, etc.

## No Docker Required

This project uses:
- Homebrew PostgreSQL for local database
- npm for package management
- schema/schema.sql as the ground truth DDL
