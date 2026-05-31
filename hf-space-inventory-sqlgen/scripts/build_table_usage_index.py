"""
build_table_usage_index.py — entry point only.

All logic lives in SolderEngine.build_table_usage_index().
Run:
    python scripts/build_table_usage_index.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from solder_engine import SolderEngine

if __name__ == "__main__":
    engine = SolderEngine()
    summary = engine.build_table_usage_index(verbose=True)
    global_counts = summary.get("_global", {})
    print(f"\nGlobal table reference counts (most used first):")
    for table, count in global_counts.items():
        print(f"  {table:<35} {count}")
    total_refs = sum(global_counts.values())
    print(f"\nDone — {total_refs} total references across {len(global_counts)} distinct tables.")
