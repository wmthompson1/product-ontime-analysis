# SQLMesh Virtual Environments

## Overview

SQLMesh's virtual environments allow isolated development without duplicating data. They use virtual tables/views that point to production or dev-specific tables.

## How It Works

1. Production tables store actual data
2. Dev/staging environments use views pointing to production
3. Only modified models get new physical tables
4. Promotes efficiently by swapping view pointers

## Creating Environments

```bash
# Create/update dev environment
sqlmesh plan dev

# Create staging environment  
sqlmesh plan staging

# Production (default)
sqlmesh plan
```

## Environment Workflow

### Development
```bash
# 1. Make model changes
# 2. Plan dev environment
sqlmesh plan dev

# 3. Review changes and apply
# 4. Test in dev
sqlmesh fetchdf --gateway dev "SELECT * FROM analytics.my_model LIMIT 10"

# 5. Run tests
sqlmesh test
```

### Promotion to Production
```bash
# Plan production (compares to current prod state)
sqlmesh plan

# Review impact analysis
# Apply changes
```

## Environment Comparison

```bash
# Compare dev to prod
sqlmesh diff dev prod

# See what's different
sqlmesh table_diff analytics.customers dev prod
```

## Invalidating Environments

```bash
# Remove dev environment
sqlmesh invalidate dev

# Force recreation
sqlmesh plan dev --create-from prod
```

## Benefits

| Feature | Traditional | SQLMesh |
|---------|-------------|---------|
| Dev data | Full copy | Virtual pointers |
| Storage cost | 2x-10x | Minimal |
| Promote speed | Full rebuild | Pointer swap |
| Isolation | Complete | Complete |

## Schema Organization

```
database/
├── prod/                    # Production schema
│   ├── customers (table)
│   └── orders (table)
├── dev__alice/              # Alice's dev environment
│   ├── customers (view → prod)
│   └── orders (modified table)
└── dev__bob/                # Bob's dev environment
    ├── customers (view → prod)
    └── orders (view → prod)
```

## Best Practices

1. Always test in dev before prod
2. Use meaningful environment names
3. Clean up unused environments
4. Share staging for integration testing
