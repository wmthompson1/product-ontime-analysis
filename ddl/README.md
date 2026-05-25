# ERP DDL Files — Canonical Location

All ERP schema DDL files (CREATE TABLE scripts) extracted from `sql-lab-1 / LIVE` live here.

## What's here

- **1,109+ `.sql` files** — one per table, named `dbo.<TABLE_NAME>.sql`
- **`TABLE_INDEX.md`** — auto-generated index mapping table name → file
- **`generate_table_index.ps1`** — script to regenerate `TABLE_INDEX.md`

## Moved here on 4/2/2026

Files were consolidated here from two previous locations:

| Old location | Status |
|---|---|
| `Documentation\Schema\Tables\` | Superseded — files still present for reference |
| `Documentation\Schema\ddl-extract\schema-extract\output\LIVE\` | Superseded — files still present for reference |

## Regenerate the table index

Run from repo root:

```powershell
pwsh Utilities\SQLMesh\ddl\generate_table_index.ps1
```

## Extract fresh DDL from sql-lab-1

```powershell
.\Documentation\Schema\ddl-extract\extract-schema.ps1 `
  -ServerInstance 'sql-lab-1' `
  -Databases 'LIVE' `
  -OutputDir '.\Utilities\SQLMesh\ddl' `
  -UseIntegratedAuth -TrustServerCertificate
```
