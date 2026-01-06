# Utilities/SQLMesh

Minimal SQLMesh project scaffold for local development.

Quick start

1. Create and activate a Python virtualenv, then install dependencies:

```bash
# from repository root
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "sqlmesh[lsp]" sqlglot
```

2. Ensure the dev DuckDB exists at `Utilities/SQLMesh/dev.duckdb` (this repo may already contain a test DB).

3. Validate or apply the plan:

```bash
cd Utilities/SQLMesh
sqlmesh plan --auto-apply
```

Files:
- `config.yaml` — minimal project config (duckdb gateway pointing to `dev.duckdb`).
- `models/items_model.sql` — simple model with self-contained sample data using proper SQLMesh MODEL syntax.
- `gateways.yml` — example gateway configuration for in-memory testing.

Gateways and in-memory testing

You can run quick tests against an in-memory database using either SQLite or DuckDB.

- Using SQLite (in-memory):

	```bash
	export DATABASE_URL="sqlite:///:memory:"
	cd Utilities/SQLMesh
	sqlmesh render items_model
	sqlmesh run items_model
	```

- Using DuckDB (in-memory):

	```bash
	export DATABASE_URL="duckdb:///:memory:"
	cd Utilities/SQLMesh
	sqlmesh render items_model
	sqlmesh run items_model
	```

Alternatively, the repository contains `gateways.yml` which shows a local in-memory SQLite gateway configuration you can adapt.
