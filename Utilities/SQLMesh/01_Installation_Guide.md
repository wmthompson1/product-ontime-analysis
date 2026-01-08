# SQLMesh Installation Guide

## Overview
SQLMesh is a next-generation data transformation framework for shipping data quickly and efficiently. It supports SQL/Python transformations with SQL transpilation, column-level lineage, unit testing, and virtual environments.

## Prerequisites
- Python 3.8+ installed
- pip package manager

## Basic Installation

```bash
pip install sqlmesh
```

## Database-Specific Extras

SQLMesh uses extras to add optional dependencies:

```bash
pip install "sqlmesh[duckdb]"      # Local dev environment (default)
pip install "sqlmesh[snowflake]"   # Snowflake connector
pip install "sqlmesh[bigquery]"    # BigQuery support
pip install "sqlmesh[postgres]"    # PostgreSQL
pip install "sqlmesh[mysql]"       # MySQL
pip install "sqlmesh[redshift]"    # Amazon Redshift
pip install "sqlmesh[databricks]"  # Databricks
```

## Multiple Extras

```bash
pip install "sqlmesh[snowflake,github,slack]"
```

Common extras:
- `lsp` - VSCode language server support
- `github` - GitHub CI/CD bot integration
- `slack` - Slack notifications

## VSCode Support

```bash
pip install "sqlmesh[lsp]"
```

## Verify Installation

```bash
sqlmesh --version
sqlmesh --help
```

## Resources
- Official Docs: https://sqlmesh.readthedocs.io/
- PyPI: https://pypi.org/project/sqlmesh/
- GitHub: https://github.com/TobikoData/sqlmesh
