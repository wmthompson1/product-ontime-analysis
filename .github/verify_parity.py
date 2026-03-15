import sqlite3
import os
import re

def verify_parity(catalog_path, models_dir, docs_dir):
    """
    Checks if tables in catalog exist as .sql models and are mentioned in docs.
    """
    conn = sqlite3.connect(catalog_path)
    cursor = conn.cursor()
    
    # 1. Fetch authoritative table list from the catalog
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