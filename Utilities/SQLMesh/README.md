# SQLMesh Configuration

This directory contains the SQLMesh project configuration for manufacturing analytics and product on-time analysis.

## Digital Twin - Part I

### Overview

The **Digital Twin** initiative creates a virtualized representation of the manufacturing production schema using SQLMesh. This enables:

- **Schema Virtualization**: Mirror production tables without data duplication
- **Safe Development**: Test transformations in isolated environments
- **Incremental Processing**: Efficient handling of time-series manufacturing data
- **Column-Level Lineage**: Track data flow through the analytics pipeline

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Schema (raw.*)                     │
│  corrective_actions, daily_deliveries, equipment_metrics, ...   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ DDL Parser (024_Entry_Point)
┌─────────────────────────────────────────────────────────────────┐
│                    Staging Layer (staging.stg_*)                 │
│  26 SQLMesh models with audits, column docs, incremental logic  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (Part II - Future)
┌─────────────────────────────────────────────────────────────────┐
│                    Marts Layer (marts.*)                         │
│  Aggregated metrics, KPIs, dimensional models                   │
└─────────────────────────────────────────────────────────────────┘
```

### Generated Models

| Category | Model Kind | Tables | Time Column |
|----------|------------|--------|-------------|
| **Delivery Performance** | INCREMENTAL | daily_deliveries | delivery_date |
| **Equipment Health** | INCREMENTAL | equipment_metrics, equipment_reliability | measurement_date |
| **Failure Analysis** | INCREMENTAL | failure_events, downtime_events | failure_date |
| **Quality Control** | INCREMENTAL | product_defects, production_quality | production_date |
| **Financial Impact** | INCREMENTAL | financial_impact, quality_costs | event_date |
| **Reference Data** | FULL | suppliers, products, production_lines | - |
| **Semantic Layer** | FULL | schema_concepts, schema_edges | - |

### Entry Point Script

The DDL-to-SQLMesh converter (`024_Entry_Point_DDL_to_SQLMesh.py`) automates model generation:

```bash
# Preview without writing files
python 024_Entry_Point_DDL_to_SQLMesh.py --preview

# Generate models from manufacturing DDL
python 024_Entry_Point_DDL_to_SQLMesh.py

# Custom DDL source
python 024_Entry_Point_DDL_to_SQLMesh.py --ddl schema/schema_sqlite.sql
```

### Model Features

Each generated model includes:

1. **Appropriate Kind Selection**
   - `INCREMENTAL_BY_TIME_RANGE` for time-series data
   - `FULL` for reference/dimension tables

2. **Data Quality Audits**
   ```sql
   audits (
     UNIQUE_VALUES(columns = (equipment_id)),
     NOT_NULL(columns = (equipment_id))
   )
   ```

3. **Manufacturing Domain Documentation**
   ```sql
   columns (
     oee_score 'Overall Equipment Effectiveness (0-100%)',
     mtbf_hours 'Mean Time Between Failures in hours',
     defect_rate 'Defect rate as percentage'
   )
   ```

4. **Incremental Time Filtering**
   ```sql
   WHERE measurement_date BETWEEN @start_ds AND @end_ds
   ```

### Directory Structure

```
Utilities/SQLMesh/
├── config.yaml                     # DuckDB gateway configuration
├── models/
│   ├── staging/                    # Digital Twin staging models
│   │   ├── stg_daily_deliveries.sql
│   │   ├── stg_equipment_metrics.sql
│   │   ├── stg_failure_events.sql
│   │   └── ... (26 models total)
│   ├── full_model.sql              # Example FULL model
│   ├── incremental_model.sql       # Example incremental model
│   └── seed_model.sql              # Example seed model
├── seeds/                          # Static reference data (CSV)
├── tests/                          # Unit tests
├── audits/                         # Custom data quality checks
└── docs/                           # Documentation (01-11 guides)
```

### Part II Roadmap

Future enhancements planned:

- **Marts Layer**: Aggregated KPIs and dimensional models
- **Semantic Integration**: Connect to LangChain semantic layer
- **Graph Traversal**: Intent/Perspective disambiguation in SQLMesh
- **ArangoDB Sync**: Bidirectional graph metadata synchronization

---

## Raw Masked Staging Models & Orchestrator Handshake

Two Python models in `models/raw/` pull ERP staging data through this repo's
SME-approved masking pipeline (the **Solder Pattern** — never LLM-generated SQL):

| Model | Source | What it returns |
|-------|--------|-----------------|
| `raw.raw_user_def_fields` | `Staging.dbo.USER_DEF_FIELDS` | One masked row per user-defined field, with the "Legacy Manufacturer Code" (`USER_DEF_1`) projection and the active receiving certificate's metadata. |
| `raw.raw_matrix_driven` | every active table in `masking_matrix.csv` | Long-format, one row per masked source value, annotated with the active receiving certificate. |

Both import their masking primitives from `models/raw/masking_helpers.py`, which
reuses the canonical logic in `hf-space-inventory-sqlgen/masking_matrix.py` and
`masking_type.py`. `masking_helpers.py` is listed under `ignore_patterns` in
`config.yaml` so the loader does not treat it as a model. SQLMesh serializes the
helper functions (by source) into each model's snapshot and walks the globals
they reference, so those globals are kept serializable (plain strings / modules,
never `Path` or compiled-regex objects).

### Orchestrator handshake

`orchestrator_handshake.py` (repo root) is a non-interactive validation script
that proves the environment is wired correctly end-to-end:

```bash
python orchestrator_handshake.py
```

- **Phase 1 (environment):** Python 3.13, SQLMesh + SQLGlot install, project
  structure, `app_schema/manufacturing.db`, and a successful SQLMesh context load.
- **Phase 2 (semantic):** resolves a natural-language intent
  (e.g. `"Legacy Manufacturer Code"`) to its physical column (`USER_DEF_1`) via
  this repo's schema metadata, then confirms `raw.raw_user_def_fields` exposes
  that column — i.e. the orchestrator routes semantic requests to masked staging
  data, never to generated SQL.

The script exits non-zero if any check fails, so it is safe to run in CI or a
pre-merge gate.

---

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

## Documentation Guides

Comprehensive SQLMesh documentation available in this directory:

| Guide | Topic |
|-------|-------|
| [01_Installation_Guide.md](01_Installation_Guide.md) | Install methods, database extras |
| [02_Project_Setup.md](02_Project_Setup.md) | Init templates, environment config |
| [03_Models_Basics.md](03_Models_Basics.md) | Model kinds, metadata, variables |
| [04_Commands_Reference.md](04_Commands_Reference.md) | CLI commands reference |
| [05_Testing_and_Audits.md](05_Testing_and_Audits.md) | Unit tests, audit types |
| [06_Incremental_Models.md](06_Incremental_Models.md) | Time-range, unique-key strategies |
| [07_Virtual_Environments.md](07_Virtual_Environments.md) | Dev/staging/prod isolation |
| [08_Column_Level_Lineage.md](08_Column_Level_Lineage.md) | Lineage tracking, impact analysis |
| [09_dbt_Migration.md](09_dbt_Migration.md) | dbt conversion guide |
| [10_Best_Practices.md](10_Best_Practices.md) | Project organization, CI/CD |
| [11_VSCode_Extension.md](11_VSCode_Extension.md) | IDE integration |
