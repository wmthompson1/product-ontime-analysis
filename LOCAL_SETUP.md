# Local Development Setup (No Docker)

## Prerequisites
- Homebrew PostgreSQL (not Docker)
- Node.js / npm

## Database Setup

### 1. Start PostgreSQL (Homebrew)
```bash
brew services start postgresql@14
```

### 2. Create Database
```bash
createdb manufacturing_analytics
```

### 3. Load Schema
```bash
psql manufacturing_analytics < schema/schema.sql
```

This creates all 24 tables from the Replit production schema.

## Environment Variables

Create `.env` file:
```
DATABASE_URL=postgresql://your_username@localhost:5432/manufacturing_analytics
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
