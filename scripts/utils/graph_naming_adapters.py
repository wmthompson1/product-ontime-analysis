# Path: scripts/utils/graph_naming_adapters.py

def tokenize_agent_canonical_id(table_name: str, column_name: str = None) -> dict:
    """
    Enforces the public agent's exact naming pattern.
    Uses double colons and literal periods to keep keys safe for ArangoDB
    while preserving strict structural prefixes.
    """
    # Force names to upper or exact casing to match your physical ERP catalog
    tbl = table_name.strip().upper()
    
    if column_name:
        col = column_name.strip().upper()
        # Generates: column::EMPLOYEE.ID
        safe_key = f"column::{tbl}.{col}"
        collection = "columns"
    else:
        # Generates: table::EMPLOYEE
        safe_key = f"table::{tbl}"
        collection = "tables"
        
    return {
        "_key": safe_key,
        "_id": f"{collection}/{safe_key}"
    }

# --- QUICK SANITY PASS ---
node_meta = tokenize_agent_canonical_id("EMPLOYEE", "ID")
print(f"Target Key: {node_meta['_key']}") # Output: column::EMPLOYEE.ID
print(f"Target ID:  {node_meta['_id']}")  # Output: columns/column::EMPLOYEE.ID