# SQLMesh Configuration

This directory contains the SQLMesh project configuration for product on-time analysis.

## Configuration

The project is configured to use **DuckDB** as the database engine with persistent file-based storage.

### Files

- `config.yaml` - Main configuration file with DuckDB gateway setup (single source of truth)
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

2. Navigate to the SQLMesh directory:
   ```bash
   cd Utilities/SQLMesh
   ```

3. View project info:
   ```bash
   sqlmesh info
   ```

4. Create and test models:
   ```bash
   sqlmesh plan
   sqlmesh run
   ```

### Configuration Details

- **Gateway**: `local` (DuckDB connection)
- **Default gateway**: `local`
- **Models directory**: `models/`
- **Database dialect**: DuckDB

The configuration provides:
- **Single source of truth**: One YAML configuration file
- **Persistent database**: File-based storage for testing consistency
- **Fast analytics performance**: DuckDB optimized for OLAP workloads
- **Clear gateway mapping**: Explicit connection configuration

## Rationale

- **DuckDB advantages**: Better analytics capabilities and faster performance than SQLite
- **No conflicting configs**: Single `config.yaml` instead of multiple configuration files
- **Standard format**: YAML is SQLMesh's native configuration format
