# Local PostgreSQL Setup Guide

This guide helps you set up PostgreSQL locally on Intel Mac for development, independent of Replit's Neon-backed PostgreSQL.

## PostgreSQL Installation Options

### Option 1: Homebrew (Recommended - Docker-free)

```bash
# Install PostgreSQL 16
brew install postgresql@16

# Start PostgreSQL service
brew services start postgresql@16

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/usr/local/opt/postgresql@16/bin:$PATH"

# Verify installation
psql --version
```

### Option 2: Postgres.app (GUI-friendly)

1. Download from https://postgresapp.com/
2. Move to Applications folder
3. Open and click "Initialize" to create a server
4. Add CLI tools to PATH:
```bash
sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp
```

### Option 3: Supabase Free Tier (Cloud alternative)

1. Sign up at https://supabase.com/
2. Create a new project
3. Copy the connection string from Settings > Database

## Database Creation

After installing PostgreSQL locally:

```bash
# Create the database
createdb manufacturing_analytics

# Verify it exists
psql -l | grep manufacturing_analytics

# Connect to the database
psql manufacturing_analytics
```

## Environment Configuration

### .env File Structure

Create a `.env` file in the project root:

```bash
# PostgreSQL Connection
# Format: postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME

# Local Development (no SSL required)
DATABASE_URL=postgresql+psycopg2://your_username@localhost:5432/manufacturing_analytics

# Or with explicit parameters:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=manufacturing_analytics
DB_USER=your_username
DB_PASSWORD=
DB_SSLMODE=disable

# For Replit/Neon (SSL required) - DO NOT USE LOCALLY
# DATABASE_URL=postgresql+psycopg2://user:pass@host.neon.tech:5432/dbname?sslmode=require

# API Keys (placeholders)
# Set these locally in a private `.env` file or CI/repo secrets; do NOT commit real keys.
OPENAI_API_KEY=<OPENAI_API_KEY_PLACEHOLDER>
TAVILY_API_KEY=<TAVILY_API_KEY_PLACEHOLDER>
HUGGINGFACE_TOKEN=<HUGGINGFACE_TOKEN_PLACEHOLDER>
```

### Connection String Formats

| Environment | Format | SSL |
|-------------|--------|-----|
| Local (Homebrew) | `postgresql+psycopg2://user@localhost:5432/dbname` | No |
| Local (with password) | `postgresql+psycopg2://user:pass@localhost:5432/dbname` | No |
| Neon/Replit | `postgresql+psycopg2://user:pass@host.neon.tech:5432/dbname?sslmode=require` | Yes |
| Supabase | `postgresql+psycopg2://postgres:pass@host.supabase.co:5432/postgres` | Yes |

## Schema Setup

### Option A: Import from Replit (Recommended for existing data)

Export schema from Replit's Neon database:

```bash
# On Replit, run:
pg_dump --schema-only $DATABASE_URL > schema.sql

# Download schema.sql to local machine
# Then apply locally:
psql manufacturing_analytics < schema.sql
```

### Option B: Create from SQLAlchemy Models

```bash
# With Flask app running:
python -c "from main import app, db; app.app_context().push(); db.create_all()"
```

### Option C: Use Alembic Migrations

Initialize Alembic (if not already):

```bash
# Install Flask-Migrate (already in requirements.txt)
pip install flask-migrate

# Initialize migrations folder
flask db init

# Generate migration from models
flask db migrate -m "Initial schema"

# Apply migration
flask db upgrade
```

## Schema Reference

### Main Application Tables

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schema nodes (for graph-based schema)
CREATE TABLE schema_nodes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    node_type VARCHAR(50),
    metadata JSONB
);

-- Schema edges (relationships)
CREATE TABLE schema_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES schema_nodes(id),
    target_id INTEGER REFERENCES schema_nodes(id),
    edge_type VARCHAR(50),
    metadata JSONB
);
```

### HF Space Inventory Schema

```sql
-- Inventory items
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    quantity INTEGER DEFAULT 0,
    unit_price DECIMAL(10,2),
    category VARCHAR(100),
    location VARCHAR(100),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Suppliers
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT
);

-- Transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    transaction_type VARCHAR(20),
    quantity INTEGER,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Testing the Connection

### Python Test Script

```python
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Get connection string
database_url = os.getenv('DATABASE_URL')

# Create engine
engine = create_engine(database_url)

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(f"Connected to: {result.fetchone()[0]}")
    
    # List tables
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """))
    print("Tables:", [row[0] for row in result])
```

### Quick Connection Test

```bash
# Test with psql
psql $DATABASE_URL -c "SELECT version();"

# Or with Python
python -c "
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('Connected successfully!')
"
```

## npm Scripts for Database

Add to `package.json`:

```json
{
  "scripts": {
    "db:create": "createdb manufacturing_analytics",
    "db:drop": "dropdb manufacturing_analytics",
    "db:reset": "npm run db:drop && npm run db:create",
    "db:migrate": "flask db upgrade",
    "db:schema": "psql manufacturing_analytics < schema.sql"
  }
}
```

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Start if not running
brew services start postgresql@16
```

### Authentication Failed

```bash
# Check your username
whoami

# PostgreSQL typically uses your system username
psql -U $(whoami) -d manufacturing_analytics
```

### Database Does Not Exist

```bash
# Create the database
createdb manufacturing_analytics
```

### SSL Issues (when using cloud databases)

```bash
# For Neon/Supabase, ensure sslmode=require in URL
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db?sslmode=require
```

## GitHub Copilot Prompts

Use these prompts with GitHub Copilot to set up your database:

### Initial Setup
> "Help me install PostgreSQL 16 on Intel Mac using Homebrew and create a database called manufacturing_analytics"

### Schema Creation
> "Create SQLAlchemy models for inventory management with tables for inventory items, suppliers, and transactions"

### Migration
> "Set up Flask-Migrate and create an initial migration for my SQLAlchemy models"

### Connection Testing
> "Write a Python script to test my PostgreSQL connection and list all tables"
