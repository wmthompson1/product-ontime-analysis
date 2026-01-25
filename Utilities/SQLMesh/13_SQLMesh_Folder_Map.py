#!/usr/bin/env python3
"""Utility to show how SQLMesh seed paths are resolved.

This script demonstrates resolution of a seed path like
  $root/seeds/equipment_metrics.csv
and shows how the same resource would be resolved when a model
file is located in `models/` or `models/staging/` using a relative
reference (e.g. `../seeds/equipment_metrics.csv`).

Run from repo root:
  python Utilities/SQLMesh/13_SQLMesh_Folder_Map.py
"""
from pathlib import Path
import os


def resolve_root_seed(project_root: Path, seed_ref: str) -> Path:
    """Resolve a seed reference that uses $root/..."""
    if seed_ref.startswith("$root/"):
        rel = seed_ref[len("$root/"):]
        return (project_root / rel).resolve()
    return Path(seed_ref).resolve()


def resolve_relative_from_model(model_path: Path, relative_ref: str) -> Path:
    """Resolve a relative seed path from the model file location."""
    return (model_path.parent / relative_ref).resolve()


def main():
    project_root = Path(__file__).parent.resolve()  # Utilities/SQLMesh
    print(f"Project root: {project_root}")
    print("\n")

    seed_ref = "$root/seeds/equipment_metrics.csv"
    print(f"Seed reference: {seed_ref}")
    print("\n")

    # 1) $root replacement
    resolved_root = resolve_root_seed(project_root, seed_ref)
    print(f"Resolved ($root replacement): {resolved_root}")
    print("\n")

    # 2) Example model in models/
    model_in_models = project_root / "models" / "example_model.sql"
    rel_ref = "../seeds/equipment_metrics.csv"  # typical relative from models/
    resolved_from_models = resolve_relative_from_model(model_in_models, rel_ref)
    print(f"If model is under models/ and uses '{rel_ref}': {resolved_from_models}")
    print("\n")

    # 3) Example staging model in models/staging/
    model_in_staging = project_root / "models" / "staging" / "stg_equipment_metrics.sql"
    resolved_from_staging = resolve_relative_from_model(model_in_staging, rel_ref)
    print(f"If model is under models/staging/ and uses '{rel_ref}': {resolved_from_staging}")
    print("\n")


    # Existence checks
    print("\nExistence checks:")
    print(f"  seed file exists: {resolved_root.exists()}")
    print(f"  models-level resolved exists: {resolved_from_models.exists()}")
    print(f"  staging-level resolved exists: {resolved_from_staging.exists()}")
    print("\n")


if __name__ == "__main__":
    main()
