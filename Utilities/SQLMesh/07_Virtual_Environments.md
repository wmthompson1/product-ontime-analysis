# 07 - SQLMesh Virtual Environments

## The Problem

Traditional data development has a dilemma:
- **Clone data**: Expensive, slow, storage costs
- **Share tables**: Risk of breaking production

## The Solution: Virtual Environments

SQLMesh virtual environments provide:
- **Isolated development**: Each developer has their own space
- **Zero data duplication**: Uses views pointing to production
- **Instant promotion**: Swap pointers instead of rebuilding

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    Physical Layer                        │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ orders__v1    │  │ orders__v2    │  │ customers    │ │
│  │ (prod data)   │  │ (dev changes) │  │ (shared)     │ │
│  └───────────────┘  └───────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                    Virtual Layer                         │
│  ┌───────────────┐  ┌───────────────┐                   │
│  │ prod.orders   │  │ dev.orders    │                   │
│  │ (view → v1)   │  │ (view → v2)   │                   │
│  └───────────────┘  └───────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

## Creating Environments

### Development Environment

```bash
# Create/update dev environment
sqlmesh plan dev
```

### Staging Environment

```bash
# Create staging from prod
sqlmesh plan staging
```

### Production

```bash
# Production is the default
sqlmesh plan
```

## Environment Workflow

### 1. Make Changes

Edit your models in the `models/` directory.

### 2. Plan Dev Environment

```bash
sqlmesh plan dev
```

Output shows:
- Modified models
- Impact on downstream models
- Backfill requirements

### 3. Apply to Dev

Follow prompts to apply changes to dev environment.

### 4. Test in Dev

```bash
# Query dev environment
sqlmesh fetchdf --gateway dev "SELECT * FROM analytics.orders LIMIT 10"

# Run tests
sqlmesh test

# Run audits
sqlmesh audit
```

### 5. Compare to Production

```bash
# See differences
sqlmesh diff dev prod

# Compare table data
sqlmesh table_diff analytics.orders dev prod
```

### 6. Promote to Production

```bash
# Plan production changes
sqlmesh plan

# Review and apply
```

## Named Environments

Create team-specific environments:

```bash
# Feature branch environment
sqlmesh plan feature-user-analytics

# Personal environment
sqlmesh plan dev-alice

# Sprint environment
sqlmesh plan sprint-2024-q1
```

## Environment Isolation

Each environment sees its own version:

```sql
-- In dev: points to modified table
SELECT * FROM dev.analytics.orders;

-- In prod: points to production table
SELECT * FROM prod.analytics.orders;
```

## Cleanup

### Invalidate Environment

```bash
# Remove dev environment
sqlmesh invalidate dev

# Remove staging
sqlmesh invalidate staging
```

### Clean Old Snapshots

```bash
# Remove orphaned physical tables
sqlmesh clean
```

## Benefits Comparison

| Feature | Clone Approach | Virtual Environments |
|---------|---------------|---------------------|
| Storage | 2-10x production | ~0 (views only) |
| Setup time | Hours to days | Seconds |
| Promotion | Full rebuild | Pointer swap |
| Isolation | Complete | Complete |
| Freshness | Point-in-time | Real-time (views) |

## Schema Organization

How SQLMesh organizes schemas:

```
database/
├── sqlmesh__/                    # Physical tables
│   ├── orders__abc123           # Snapshot v1
│   ├── orders__def456           # Snapshot v2
│   └── customers__xyz789        # Shared snapshot
├── prod/                         # Production views
│   ├── orders → orders__abc123
│   └── customers → customers__xyz789
└── dev__alice/                   # Alice's dev views
    ├── orders → orders__def456  # Her changes
    └── customers → customers__xyz789  # Shares prod
```

## Best Practices

1. **Always develop in a named environment**
   ```bash
   sqlmesh plan dev  # Not just sqlmesh plan
   ```

2. **Test thoroughly before promoting**
   ```bash
   sqlmesh test
   sqlmesh audit
   sqlmesh diff dev prod
   ```

3. **Clean up after feature completion**
   ```bash
   sqlmesh invalidate feature-xyz
   ```

4. **Use consistent naming**
   - `dev-{username}` for personal
   - `feature-{name}` for features
   - `staging` for pre-prod

5. **Share staging for integration testing**
   - Multiple developers can validate together
   - Closer to production conditions

## Next Steps

Continue to [08_Column_Level_Lineage.md](08_Column_Level_Lineage.md) to understand lineage tracking.
