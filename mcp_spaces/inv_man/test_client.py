# test_client.py
import requests
import json

BASE = "http://localhost:8000"  # change to 7860 if using HF Space local Gradio, or HF URL when deployed

def discover():
    r = requests.get(f"{BASE}/mcp")
    r.raise_for_status()
    return r.json()

def invoke_generate_sql():
    payload = {
        "options": {
            "dialect": "postgres",
            "target_table": "public.inventory",
            "staging_table": "staging.inventory_staging",
            "key_columns": ["sku", "location"],
            "update_columns": ["quantity_on_hand", "reserved_qty", "last_seen"],
            "business_intent": "preserve reserved"
        },
        "context": {
            "note": "This request is for replenishing shortages and preserving reserved quantities."
        }
    }
    r = requests.post(f"{BASE}/generate_sql", json=payload)
    print("status:", r.status_code)
    print(r.json())

if __name__ == "__main__":
    print("Discovery:", json.dumps(discover(), indent=2))
    print("\nInvoke generate_sql:")
    invoke_generate_sql()
