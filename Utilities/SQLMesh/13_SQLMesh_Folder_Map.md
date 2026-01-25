Companion script
---------------

We've added a simple companion script: `13_SQLMesh_Folder_Map.py`.
- Purpose: Demonstrates how the `$root` substitution and relative paths (e.g., `../seeds/<file>.csv`) resolve
	when a model file is located in `models/` or `models/staging/`.
- Usage: From the repo root run:

	python Utilities/SQLMesh/13_SQLMesh_Folder_Map.py

The script prints resolved absolute paths and whether the referenced files exist on disk. Use it to verify seed references
before running `sqlmesh plan` or updating CI workflows.

# SQLMesh Folder Map

This file documents how SQLMesh resolves model and seed locations inside the project. Use it to verify where your seed CSVs should live and how a `path` or `$root` reference in a MODEL block resolves to an OS path.

Project layout (relevant):

- `Utilities/SQLMesh/` — project root for the SQLMesh project
- `Utilities/SQLMesh/models/` — model files (MODEL blocks and SELECTs)
- `Utilities/SQLMesh/models/staging/` — staging models
- `Utilities/SQLMesh/seeds/` — seed CSVs referenced by SEED models or consumed by staging models

Path resolution rules

- `$root` in a MODEL `path` is replaced with the SQLMesh project root (the folder that contains `config.yaml`).
- Relative paths in a MODEL `path` are resolved from the model file location. For example, a staging model under `models/staging/` that references `../seeds/foo.csv` will resolve to `Utilities/SQLMesh/seeds/foo.csv`.

Companion script

There is a small companion Python script that demonstrates these resolution rules and prints resolved paths for the seed reference `$root/seeds/equipment_metrics.csv` as well as how the same seed would be resolved when a model file sits under `models/` or `models/staging/`.

Run the script from the repository root:

```bash
python Utilities/SQLMesh/13_SQLMesh_Folder_Map.py
```

The script prints the project root, the `$root`-resolved absolute seed path, and two resolved paths for the same seed if referenced relatively from a `models`-level model and a `models/staging`-level model.

Why this helps

- Quickly validate that your `path` values in SEED models or `$root` references point to files that actually exist on disk.
- Avoid subtle errors where a model in `models/staging/` references `../seeds/...` but the relative resolution is incorrect.


**Q: how do I determine the default schema?**
Quick check: inspect the project config, ask SQLMesh, or query the DuckDB warehouse.
*Inspect config.yaml for schema/default settings:*
```
grep -nE "schema|default" Utilities/SQLMesh/config.yaml || truesed -n '1,200p' Utilities/SQLMesh/config.yaml
```
## schema nesting
cd "/Users/williamthompson/bbb/20241019 Python/Utilities/SQLMesh"
../../.venv/bin/sqlmesh info -p . --verbose
SQLMesh requires all model names and references to have the same level of nesting.
Error: Failed to update model schemas

Table "seed_model" must match the schema's nesting level: 3.
 - seed csv:
 color,time_added
Yellow,2024-09-07 20:12:48 

MODEL (
  name seed_model,
  kind SEED (
    path '$root/seeds/colors.csv'
  ),
  grain (color),
  audits (
    UNIQUE_VALUES(columns = (color)),
    NOT_NULL(columns = (color))
  )
);

**To Resolve, patch seed_model.sql to the matching three-part name.**

I'll search the models for example three-part name values to match the project's nesting, then patch seed_model.sql to use the same pattern.