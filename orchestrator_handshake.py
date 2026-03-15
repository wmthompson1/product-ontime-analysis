"""
orchestrator_handshake.py — Herald Orchestrator Handshake

Demonstrates the Herald -> Agent -> Skill execution chain using
the local MCP registry defined in copilot-config.yaml.

Instead of a fictional copilot_sdk, this implementation reads
copilot-config.yaml and invokes skills directly via subprocess,
matching the contract defined in each skill's skill.json.

Usage:
    python orchestrator_handshake.py
    python orchestrator_handshake.py --perspective finance
    python orchestrator_handshake.py --skip-parity
"""

import json
import os
import subprocess
import sys
import argparse
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "copilot-config.yaml"


def load_config() -> dict:
    """Load the MCP registry from copilot-config.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_skill_contract(skill_name: str, config: dict) -> dict:
    """Resolve a skill name to its skill.json contract."""
    for skill in config.get("skills", []):
        if skill["name"] == skill_name:
            skill_path = PROJECT_ROOT / skill["path"]
            with open(skill_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise ValueError(f"Skill '{skill_name}' not found in copilot-config.yaml")


def run_parity_audit(config: dict) -> dict:
    """
    Execute the parity_verifier_001 skill as the pre-execution safety gate.

    Returns:
        dict with keys: status, verified_count, discrepancies
    """
    paths = config.get("paths", {})
    cmd = [
        str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
        str(PROJECT_ROOT / "verify_parity.py"),
        "--catalog", str(PROJECT_ROOT / paths.get("schema_catalog", "")),
        "--models",  str(PROJECT_ROOT / paths.get("models_staging", "")),
        "--docs",    str(PROJECT_ROOT / paths.get("docs_models", "Documentation/models")),
        "--json"
    ]

    print("🔍 Safety Gate: Running parity_verifier_001 ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()

    try:
        audit_result = json.loads(output)
    except json.JSONDecodeError:
        audit_result = {"status": "error", "message": output or result.stderr}

    status_icon = "✔" if audit_result["status"] == "success" else "⚠"
    print(f"   {status_icon}  Parity status: {audit_result['status'].upper()} "
          f"({audit_result.get('verified_count', '?')} verified, "
          f"{len(audit_result.get('discrepancies', []))} discrepancy/-ies)")

    return audit_result


def execute_masking_intent(perspective: str = "manufacturing",
                           gemin_salt: str = "",
                           skip_parity: bool = False) -> None:
    """
    Orchestrates the Herald -> Intent Mapping Agent -> Skill handshake.

    Steps:
      1. Load MCP registry from copilot-config.yaml
      2. (Optional) Run parity_verifier_001 as safety gate
      3. Validate mission parameters against masking_engine_001 skill contract
      4. Report readiness (mask_pii.py invocation deferred — requires salt)

    Args:
        perspective:  Semantic overlay — 'manufacturing' or 'finance'.
        gemin_salt:   Cryptographic salt for PII pseudonymization.
        skip_parity:  If True, bypass the pre-execution parity audit.
    """
    print(f"\n{'═'*58}")
    print(f"  Herald Orchestrator — Handshake Initiated")
    print(f"{'═'*58}")
    print(f"  Agent    : intent-mapping-agent")
    print(f"  Skill    : masking_engine_001")
    print(f"  Persp.   : {perspective}")
    print(f"{'─'*58}\n")

    config = load_config()
    contract = load_skill_contract("masking_engine_001", config)

    # --- Safety Gate ---
    if not skip_parity:
        audit = run_parity_audit(config)
        if audit["status"] == "warning":
            print("\n⚠  Parity discrepancies detected. Halting masking execution.")
            print("   → Herald is alerting the Documentation Writer agent.")
            print("   → Resolve discrepancies in Documentation/models, then re-run.\n")
            for d in audit.get("discrepancies", [])[:10]:
                print(f"     • {d}")
            sys.exit(1)
        elif audit["status"] == "error":
            print(f"\n✘  Parity audit failed: {audit.get('message', 'unknown error')}")
            sys.exit(2)
    else:
        print("   ⚡ Parity audit skipped (--skip-parity flag).")

    # --- Validate mission parameters against skill contract ---
    required_params = contract["parameters"].get("required", [])
    mission = {
        "perspective": perspective,
        "gemin_salt": gemin_salt,
        "db_path": str(PROJECT_ROOT / config["paths"]["schema_catalog"].replace(
            "analysis/impact/output/schema_catalog.db", "db.db"
        ))
    }

    missing = [p for p in required_params if not mission.get(p)]
    if missing:
        print(f"\n✘  Contract validation failed. Missing required parameters: {missing}")
        print("   Provide --salt <value> to supply gemin_salt.\n")
        sys.exit(3)

    print(f"\n✔  Contract validated — all required parameters present.")
    print(f"   Skill    : {contract['skill_id']}")
    print(f"   Params   : perspective={perspective}, db_path set")

    # --- Invoke mask_pii.py ---
    python_path = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    paths = config.get("paths", {})
    db_path = str(PROJECT_ROOT / "Utilities/SQLMesh/db.db")
    bfs_path = str(PROJECT_ROOT / paths.get("bfs_hierarchy",
                   "Utilities/SQLMesh/analysis/impact/output/foreign_key_hierarchy.json"))

    mask_cmd = [
        str(python_path),
        str(PROJECT_ROOT / "mask_pii.py"),
        "--salt",        gemin_salt,
        "--perspective", perspective,
        "--db-path",     db_path,
        "--bfs-path",    bfs_path,
    ]

    print(f"\n🚀 Invoking masking_engine_001 ...\n")
    mask_result = subprocess.run(mask_cmd, capture_output=False, text=True)

    if mask_result.returncode != 0:
        print(f"\n✘  mask_pii.py exited with code {mask_result.returncode}")
        sys.exit(mask_result.returncode)

    print(f"\n✔  masking_engine_001 completed successfully (exit 0).")
    print(f"{'═'*58}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Herald Orchestrator Handshake")
    parser.add_argument("--perspective", default="manufacturing",
                        choices=["manufacturing", "finance"],
                        help="Semantic overlay perspective")
    parser.add_argument("--salt", default="",
                        help="Cryptographic salt for masking_engine_001 (gemin_salt)")
    parser.add_argument("--skip-parity", action="store_true",
                        help="Bypass the parity_verifier_001 safety gate")
    args = parser.parse_args()

    execute_masking_intent(
        perspective=args.perspective,
        gemin_salt=args.salt,
        skip_parity=args.skip_parity
    )


if __name__ == "__main__":
    main()
