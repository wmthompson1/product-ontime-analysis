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

| Category | Model Kind | Tables | Data Source |
|----------|------------|--------|-------------|
| **Delivery Performance** | SEED | daily_deliveries | seeds/daily_deliveries.csv |
| **Equipment Health** | SEED | equipment_metrics, equipment_reliability | seeds/*.csv |
| **Failure Analysis** | SEED | failure_events, downtime_events | seeds/*.csv |
| **Quality Control** | SEED | product_defects, production_quality | seeds/*.csv |
| **Financial Impact** | SEED | financial_impact, quality_costs | seeds/*.csv |
| **Reference Data** | SEED | suppliers, products, production_lines | seeds/*.csv |
| **Semantic Layer** | SEED | schema_concepts, schema_edges | seeds/*.csv |

**Note**: The current implementation uses SEED models to stage data from CSV files. This approach supports both raw and staging schemas for digital twin development.

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
   - `SEED` for staging data loaded from CSV files in the seeds directory
   - `INCREMENTAL_BY_TIME_RANGE` for time-series data (future marts layer)
   - `FULL` for reference/dimension tables

2. **Data Quality Audits**
   ```sql
   audits (
     UNIQUE_VALUES(columns = (equipment_id)),
     NOT_NULL(columns = (equipment_id))
   )
   ```
   
   **Note**: Audits are executed automatically during `sqlmesh plan` and `sqlmesh run`. No separate audit step is needed as they are part of the validation and execution phases.

3. **Manufacturing Domain Documentation**
   ```sql
   columns (
     equipment_id TEXT,
     oee_score DOUBLE 'Overall Equipment Effectiveness (0-100%)',
     mtbf_hours DOUBLE 'Mean Time Between Failures in hours',
     defect_rate DOUBLE 'Defect rate as percentage'
   )
   ```

4. **Seed-Based Data Loading** (Current Implementation)
   ```sql
   MODEL (
     name staging.stg_equipment_metrics,
     kind SEED (
       path '$root/seeds/equipment_metrics.csv'
     ),
     grain (equipment_id),
     audits (
       NOT_NULL(columns = (equipment_id))
     )
   );
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
   sqlmesh plan  # Creates execution plan and runs audits
   sqlmesh run   # Executes models and validates with audits
   ```
   
   **Note**: Audits are automatically executed as part of `plan` and `run` commands. No separate audit command is required.

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
