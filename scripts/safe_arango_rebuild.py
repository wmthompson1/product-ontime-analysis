#!/usr/bin/env python3
"""
Safe ArangoDB Graph Rebuild
============================
Rebuilds the semantic_graph with backup and confirmation safeguards.

Usage:
    python scripts/safe_arango_rebuild.py --dry-run  # Preview only
    python scripts/safe_arango_rebuild.py --force    # Execute rebuild

Safety Features:
- Creates timestamped backup before any destructive operation
- Requires --force flag for actual execution
- Validates backup succeeded before proceeding
- Reports detailed sync results

Prerequisites:
- ARANGO_HOST, ARANGO_USER, ARANGO_ROOT_PASSWORD, ARANGO_DB in .env
- hf-space-inventory-sqlgen/graph_sync.py module available
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from arango import ArangoClient
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Add parent directory to path for graph_sync import
sys.path.insert(0, str(Path(__file__).parent.parent / "hf-space-inventory-sqlgen"))

from graph_sync import sync_graph, get_arango_client, get_arango_db, GRAPH_NAME


BACKUP_DIR = Path(__file__).parent.parent / "arango_backups"
BACKUP_DIR.mkdir(exist_ok=True)


def backup_graph(db, graph_name: str) -> Path:
    """
    Export graph data to timestamped JSON backup.
    Returns path to backup file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{graph_name}_backup_{timestamp}.json"
    
    if not db.has_graph(graph_name):
        print(f"⚠️  Graph '{graph_name}' does not exist - nothing to backup")
        return None
    
    graph = db.graph(graph_name)
    backup_data = {
        "graph_name": graph_name,
        "timestamp": timestamp,
        "vertex_collections": {},
        "edge_collections": {},
    }
    
    # Backup vertices
    for v_coll_name in graph.vertex_collections():
        collection = db.collection(v_coll_name)
        docs = [doc for doc in collection.all()]
        backup_data["vertex_collections"][v_coll_name] = docs
        print(f"  ✓ Backed up {len(docs)} vertices from '{v_coll_name}'")
    
    # Backup edges
    for e_def in graph.edge_definitions():
        e_coll_name = e_def["edge_collection"]
        collection = db.collection(e_coll_name)
        docs = [doc for doc in collection.all()]
        backup_data["edge_collections"][e_coll_name] = docs
        print(f"  ✓ Backed up {len(docs)} edges from '{e_coll_name}'")
    
    with open(backup_path, "w") as f:
        json.dump(backup_data, f, indent=2, default=str)
    
    print(f"✅ Backup saved: {backup_path}")
    return backup_path


def delete_graph_with_collections(db, graph_name: str):
    """
    Delete named graph and all its collections.
    THIS IS DESTRUCTIVE - only call after backup.
    """
    if not db.has_graph(graph_name):
        print(f"⚠️  Graph '{graph_name}' does not exist - nothing to delete")
        return
    
    graph = db.graph(graph_name)
    
    # Collect collection names before deletion
    vertex_colls = graph.vertex_collections()
    edge_colls = [ed["edge_collection"] for ed in graph.edge_definitions()]
    
    # Delete graph (keeps collections by default)
    db.delete_graph(graph_name, drop_collections=False)
    print(f"  ✓ Deleted graph '{graph_name}'")
    
    # Delete collections
    for coll_name in vertex_colls + edge_colls:
        if db.has_collection(coll_name):
            db.delete_collection(coll_name)
            print(f"  ✓ Deleted collection '{coll_name}'")


def rebuild_graph(dry_run: bool = True):
    """
    Complete rebuild: backup → delete → sync from SQLite.
    """
    print("=" * 60)
    print(f"ArangoDB Graph Rebuild - {'DRY RUN' if dry_run else 'LIVE MODE'}")
    print("=" * 60)
    print()
    
    # Test connection
    try:
        client = get_arango_client()
        db = get_arango_db(client)
        print(f"✅ Connected to ArangoDB (database: {os.getenv('ARANGO_DB', 'manufacturing_semantic_layer')})")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    print()
    
    # Backup existing graph
    print("Step 1: Backup existing graph")
    print("-" * 60)
    backup_path = backup_graph(db, GRAPH_NAME)
    print()
    
    if dry_run:
        print("Step 2: Delete graph and collections (SKIPPED - dry run)")
        print("-" * 60)
        print(f"  Would delete graph '{GRAPH_NAME}' and all collections")
        print()
        
        print("Step 3: Sync from SQLite (DRY RUN)")
        print("-" * 60)
        report = sync_graph(dry_run=True)
        print(report.summary())
        print()
        print("=" * 60)
        print("DRY RUN COMPLETE - No changes made")
        print("=" * 60)
        return True
    
    # DESTRUCTIVE: Delete existing graph
    print("Step 2: Delete graph and collections")
    print("-" * 60)
    if backup_path:
        print(f"⚠️  Backup created: {backup_path.name}")
    user_confirm = input("  🚨 This will PERMANENTLY delete existing data. Continue? (type 'yes'): ")
    if user_confirm.lower() != "yes":
        print("❌ Rebuild aborted - no changes made")
        return False
    
    delete_graph_with_collections(db, GRAPH_NAME)
    print()
    
    # Rebuild from SQLite
    print("Step 3: Sync from SQLite")
    print("-" * 60)
    report = sync_graph(dry_run=False)
    print(report.summary())
    print()
    
    if report.success:
        print("=" * 60)
        print("✅ REBUILD SUCCESSFUL")
        print("=" * 60)
        print(f"Backup available: {backup_path}")
        return True
    else:
        print("=" * 60)
        print("❌ REBUILD FAILED")
        print("=" * 60)
        print(f"Restore from backup if needed: {backup_path}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Safely rebuild ArangoDB semantic_graph with backup protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview rebuild without changes
  python scripts/safe_arango_rebuild.py --dry-run
  
  # Execute rebuild with confirmation
  python scripts/safe_arango_rebuild.py --force
  
Environment variables required:
  ARANGO_HOST, ARANGO_USER, ARANGO_ROOT_PASSWORD, ARANGO_DB
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rebuild without making changes"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Execute rebuild (requires confirmation)"
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.force:
        parser.print_help()
        print("\n⚠️  Must specify --dry-run or --force")
        sys.exit(1)
    
    success = rebuild_graph(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
