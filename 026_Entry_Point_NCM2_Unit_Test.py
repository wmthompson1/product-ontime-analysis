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