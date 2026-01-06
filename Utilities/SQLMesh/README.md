# SQLMesh Configuration

This directory contains the SQLMesh project configuration for product on-time analysis.

## Configuration

The project is configured to use **DuckDB** as the database engine with persistent file-based storage.

### Files

- `sqlmesh.toml` - Main configuration file with DuckDB gateway setup
- `models/` - Directory for SQLMesh model definitions
- `requirements.txt` - Python dependencies for SQLMesh

### Database Connection

- **Type**: DuckDB (file-based)
- **Database file**: `dev.duckdb` (automatically created, not tracked in Git)
- **Dialect**: DuckDB SQL

### Usage

To use SQLMesh in this project:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Initialize the project (if needed):
   ```bash
   cd Utilities/SQLMesh
   sqlmesh init
   ```

3. Create and test models:
   ```bash
   sqlmesh plan
   sqlmesh run
   ```

### Configuration Details

- **Project name**: `product_ontime_sqlmesh`
- **Gateway**: `local` (DuckDB connection)
- **Environment**: `default` (uses local gateway)
- **Models directory**: `models/`

The configuration provides:
- Single source of truth (TOML format)
- Persistent database for testing consistency
- Fast analytics performance with DuckDB
- Clear gateway-to-environment mapping
