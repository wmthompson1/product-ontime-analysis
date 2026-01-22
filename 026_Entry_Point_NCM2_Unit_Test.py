"""
# 026 Entry Point: NCM Elevation Unit Tests (Solder Pattern)

## Overview
This module validates the **Solder Pattern** for perspective-driven SQL generation
in the Manufacturing Semantic Layer. It tests that different business perspectives
(Quality, Finance) receive appropriately shaped data from the same underlying
Non-Conformant Materials (NCM) concept.

## Architecture
```
(:Intent) → [:OPERATES_WITHIN] → (:Perspective) → [:ELEVATES] → (:Concept) → [:CAN_MEAN] → (:Field)
```

## Prerequisites

### Option 1: Mock Mode (Default)
No external dependencies required - uses MockMCPService for offline testing.

### Option 2: Live ArangoDB Mode
1. **Start ArangoDB via Docker:**
   ```bash
   docker run -d --name arangodb -p 8529:8529 \\
       -e ARANGO_ROOT_PASSWORD=password \\
       arangodb/arangodb:latest
   ```

2. **Set environment variables:**
   ```bash
   export ARANGO_HOST=http://localhost:8529
   export ARANGO_DB=manufacturing_semantics
   export ARANGO_USER=root
   export ARANGO_PASSWORD=password
   ```

3. **Populate the semantic graph:**
   ```bash
   python 026_Entry_Point_NCM_Elevation_ArangoDB.py
   ```

## Running Tests
```bash
python 026_Entry_Point_NCM2_Unit_Test.py
```

## Expected Output
```
✅ Finance Solder Validated:
SELECT SUM(ncm.cost_impact) AS total_liability, ncm.severity FROM erp_virtual.stg_non_conformant_materials AS ncm WHERE ncm.product_line_hash = 'ee3c6e8ed9' GROUP BY ncm.severity

✅ Quality Solder Validated:
SELECT ncm.ncm_id, ncm.defect_description, ncm.severity FROM erp_virtual.stg_non_conformant_materials AS ncm WHERE ncm.product_line_hash = 'ee3c6e8ed9'

Ran 2 tests in 0.001s
OK
```

## Test Cases
| Test | Perspective | Validates |
|------|-------------|-----------|
| test_finance_perspective_elevation | Finance | Aggregated cost data (SUM, GROUP BY) |
| test_quality_perspective_elevation | Quality | Detail-level NCM records (no aggregation) |

## Related Files
- `026_Entry_Point_NCM_Elevation_ArangoDB.py` - ArangoDB graph population
- `arangodb_persistence.py` - Shared graph persistence utilities
- `Utilities/SQLMesh/models/staging/stg_non_conformant_materials.sql` - Target staging model
"""

import unittest
import hashlib

# 1. The Mock MCP Service (Simulating the ArangoDB AQL Resolution)
class MockMCPService:
    @staticmethod
    def resolve_semantic_path(intent, perspective, params):
        """
        Simulates (:Intent) -[:OPERATES_WITHIN]-> (:Perspective) -[:USES_DEFINITION]-> (:Concept)
        """
        # Common parameters for the NCM table
        base_manifest = {
            "target_schema": "erp_virtual",
            "model": "stg_non_conformant_materials",
            "alias": "ncm"
        }

        if perspective == "Quality":
            return {
                "status": "success",
                "build_order": {
                    **base_manifest,
                    "concept": "MATERIAL_NON_CONFORMANCE",
                    "projections": ["ncm.ncm_id", "ncm.defect_description", "ncm.severity"],
                    "parameters": params
                }
            }
        elif perspective == "Finance":
            return {
                "status": "success",
                "build_order": {
                    **base_manifest,
                    "concept": "FINANCIAL_LIABILITY_NCM",
                    "projections": ["SUM(ncm.cost_impact) AS total_liability", "ncm.severity"],
                    "parameters": params
                }
            }
        return {"status": "error", "message": "Access Denied"}

# 2. The Solder (Logic to assemble the SQL from the MCP manifest)
class DeterministicSolder:
    def assemble_sql(self, manifest):
        order = manifest["build_order"]
        table = f"{order['target_schema']}.{order['model']}"
        cols = ", ".join(order["projections"])

        # Deterministic Hashing for the Software Firewall
        raw_val = order["parameters"].get("product_line", "")
        hashed_val = hashlib.md5(raw_val.encode()).hexdigest()[:10]

        sql = f"SELECT {cols} FROM {table} AS {order['alias']} "
        sql += f"WHERE {order['alias']}.product_line_hash = '{hashed_val}'"

        if "SUM" in cols:
            sql += f" GROUP BY {order['alias']}.severity"

        return sql

# 3. The Unit Test
class TestSemanticElevations(unittest.TestCase):
    def setUp(self):
        self.mcp = MockMCPService()
        self.solder = DeterministicSolder()

    def test_quality_perspective_elevation(self):
        """Tests that Quality perspective receives detail-level NCM data."""
        resp = self.mcp.resolve_semantic_path("audit", "Quality", {"product_line": "Electronics"})
        sql = self.solder.assemble_sql(resp)

        # Assertion: Ensure specific NCM ID and Description are present
        self.assertIn("ncm.ncm_id", sql)
        self.assertIn("ncm.defect_description", sql)
        # Assertion: Ensure no aggregation (unless explicitly requested)
        self.assertNotIn("SUM(", sql)
        print(f"✅ Quality Solder Validated:\n{sql}\n")

    def test_finance_perspective_elevation(self):
        """Tests that Finance perspective receives aggregated cost data."""
        resp = self.mcp.resolve_semantic_path("audit", "Finance", {"product_line": "Electronics"})
        sql = self.solder.assemble_sql(resp)

        # Assertion: Ensure Cost Impact is summed as 'total_liability'
        self.assertIn("SUM(ncm.cost_impact) AS total_liability", sql)
        # Assertion: Ensure Group By is added for the sum
        self.assertIn("GROUP BY", sql)
        print(f"✅ Finance Solder Validated:\n{sql}\n")

if __name__ == '__main__':
    unittest.main()