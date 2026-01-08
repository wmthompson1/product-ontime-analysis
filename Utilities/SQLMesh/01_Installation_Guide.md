# 01 - SQLMesh Installation Guide

## Overview

SQLMesh is a next-generation data transformation framework that provides:
- **SQL Transpilation**: Write once, run on 10+ data warehouses
- **Column-Level Lineage**: Track data flow at the column level
- **Virtual Environments**: Develop without duplicating data
- **Built-in Testing**: Fast, deterministic unit tests
- **Incremental Processing**: Efficient handling of large datasets

## Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) Virtual environment

## Installation Methods

### Method 1: Basic Installation

```bash
pip install sqlmesh
```

### Method 2: With Virtual Environment (Recommended)

```bash
# Create project directory
mkdir my-sqlmesh-project
cd my-sqlmesh-project

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install SQLMesh
pip install sqlmesh

# Verify installation
sqlmesh --version
```

### Method 3: With Poetry

```bash
poetry add sqlmesh
```

### Method 4: With uv (Fast Python Package Manager)

```bash
uv pip install sqlmesh
```

## Database-Specific Extras

SQLMesh uses extras to add database connectors:

| Extra | Command | Use Case |
|-------|---------|----------|
| DuckDB | `pip install "sqlmesh[duckdb]"` | Local development (default) |
| PostgreSQL | `pip install "sqlmesh[postgres]"` | PostgreSQL databases |
| Snowflake | `pip install "sqlmesh[snowflake]"` | Snowflake data warehouse |
| BigQuery | `pip install "sqlmesh[bigquery]"` | Google BigQuery |
| Databricks | `pip install "sqlmesh[databricks]"` | Databricks lakehouse |
| Redshift | `pip install "sqlmesh[redshift]"` | Amazon Redshift |
| MySQL | `pip install "sqlmesh[mysql]"` | MySQL databases |
| Trino | `pip install "sqlmesh[trino]"` | Trino distributed SQL |
| Spark | `pip install "sqlmesh[spark]"` | Apache Spark |

### Multiple Extras

```bash
pip install "sqlmesh[snowflake,github,slack]"
```

## IDE Support

### VS Code Extension

```bash
# Install with Language Server Protocol support
pip install "sqlmesh[lsp]"
```

Then install the "SQLMesh" extension from VS Code Marketplace.

### JupyterLab

```bash
pip install "sqlmesh[jupyter]"
```

## Integration Extras

| Extra | Purpose |
|-------|---------|
| `github` | GitHub CI/CD bot integration |
| `slack` | Slack notifications |
| `web` | Web UI (deprecated, use VS Code) |
| `llm` | LLM-powered features |

## Verify Installation

```bash
# Check version
sqlmesh --version

# View help
sqlmesh --help

# List available commands
sqlmesh
```

## Troubleshooting

### Common Issues

**1. "command not found: sqlmesh"**
- Ensure your virtual environment is activated
- Try: `python -m sqlmesh --version`

**2. Database connection errors**
- Install the appropriate database extra
- Verify credentials in config.yaml

**3. Python version mismatch**
- SQLMesh requires Python 3.8+
- Check: `python --version`

## Resources

| Resource | URL |
|----------|-----|
| Official Docs | https://sqlmesh.readthedocs.io/ |
| PyPI | https://pypi.org/project/sqlmesh/ |
| GitHub | https://github.com/TobikoData/sqlmesh |
| Slack Community | https://tobikodata.com/slack |

## Next Steps

Continue to [02_Project_Setup.md](02_Project_Setup.md) to initialize your first SQLMesh project.
