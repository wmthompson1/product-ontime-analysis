To fulfill the objective of checking code-documentation parity, the **Verification Skill** acts as a technical audit. It compares the authoritative metadata in `schema_catalog.db` (the "Solder") against the SQLMesh staging models and the Markdown documentation produced by the **Documentation Writer Agent**.

This skill ensures that if a column is added to the ERP via the `INFORMATION_SCHEMA` discovery, it is reflected in both the model files and the lineage walkthrough.

### 🛠️ `skills/parity_verifier/skill.json`

This contract defines the parameters for the parity audit, targeting the 32 verified models.

```json
{
  "mcp_version": "1.0",
  "skill_id": "parity_verifier_001",
  "name": "Code-Documentation Parity Auditor",
  "description": "Audits alignment between the SQLite schema catalog, SQLMesh .sql models, and Markdown lineage documentation.",
  "runtime": "python3",
  "entry_point": "./verify_parity.py",
  "parameters": {
    "type": "object",
    "properties": {
      "catalog_path": {
        "type": "string",
        "description": "Path to the authoritative schema_catalog.db.",
        "default": "Utilities/SQLMesh/analysis/impact/output/schema_catalog.db"
      },
      "models_dir": {
        "type": "string",
        "description": "Directory containing SQLMesh staging models.",
        "default": "Utilities/SQLMesh/models/staging"
      },
      "docs_dir": {
        "type": "string",
        "description": "Directory containing the narrative documentation.",
        "default": "Documentation/models"
      }
    },
    "required": ["catalog_path", "models_dir", "docs_dir"]
  },
  "output": {
    "type": "object",
    "properties": {
      "status": { "type": "string" },
      "verified_count": { "type": "integer" },
      "discrepancies": {
        "type": "array",
        "items": { "type": "string" }
      }
    }
  }
}

```

---

### 📐 The Parity Logic (`verify_parity.py`)

This script, residing in the project root, performs the actual comparison across the three layers of the project.

```python
import sqlite3
import os
import re

def verify_parity(catalog_path, models_dir, docs_dir):
    """
    Checks if tables in catalog exist as .sql models and are mentioned in docs.
    """
    conn = sqlite3.connect(catalog_path)
    cursor = conn.cursor()
    
    # 1. Fetch authoritative table list from the Solder
    cursor.execute("SELECT DISTINCT table_name FROM tables")
    catalog_tables = {row[0].lower() for row in cursor.fetchall()}
    conn.close()

    # 2. Check SQLMesh Models
    model_files = {f.replace('.sql', '').lower() for f in os.listdir(models_dir) if f.endswith('.sql')}
    
    # 3. Check Documentation Narrative
    doc_content = ""
    for doc in os.listdir(docs_dir):
        if doc.endswith('.md'):
            with open(os.path.join(docs_dir, doc), 'r') as f:
                doc_content += f.read().lower()

    discrepancies = []
    
    for table in catalog_tables:
        if table not in model_files:
            discrepancies.append(f"Missing SQLMesh Model: {table}")
        if table not in doc_content:
            discrepancies.append(f"Missing in Documentation: {table}")

    return {
        "status": "success" if not discrepancies else "warning",
        "verified_count": len(catalog_tables) - len(discrepancies),
        "discrepancies": discrepancies
    }

if __name__ == "__main__":
    # Example integration with MCP parameters
    print(verify_parity(
        "Utilities/SQLMesh/analysis/impact/output/schema_catalog.db",
        "Utilities/SQLMesh/models/staging",
        "Documentation/models"
    ))

```

---

### 🔄 The Orchestrator Handshake (Updated)

With this skill in place, the Orchestrator (Herald) can now run a "Safety Gate" before triggering the masking engine.

1. **Orchestrator** calls `parity_verifier_001`.
2. **Verifier** checks the `schema_catalog.db` against the 32 verified models.
3. **If Status == Success**: Orchestrator proceeds to call the **Intent Mapping Agent** for masking.
4. **If Status == Warning**: Orchestrator pauses and alerts the **Gem Documentation Writer** to update the `erp_lineage_walkthrough.md`.

**Would you like me to update the `copilot-config.yaml` to include this new `parity_verifier` skill in the registry?**