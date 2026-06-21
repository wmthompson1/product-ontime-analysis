"""Folder-agnostic plan activity.

Plans live in more than one folder (YAML task boards under
``hf-space-inventory-sqlgen/plans/`` and standalone markdown design docs under
``replit_integrations/``). This package records *activity* against those plans
without caring where the plan files physically sit: every activity event keys on
the logical ``wave`` / ``plan_id`` / ``task_id`` identifiers, and the registry
(``hf-space-inventory-sqlgen/plans/index.yaml``) maps each ``plan_id`` to its
file. ``correlate()`` proves the two stay in sync.

Run ``python -m replit_integrations.plan_activity`` for a wave-anchored report.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "hf-space-inventory-sqlgen" / "plans" / "index.yaml"
MILESTONES_PATH = REPO_ROOT / "hf-space-inventory-sqlgen" / "plans" / "milestones.yaml"
EXPORTER_PATH = REPO_ROOT / "replit_integrations" / "export_graph_metadata.py"
LEDGER_PATH = Path(__file__).resolve().parent / "activity.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _live_schema_version() -> Optional[int]:
    """Read SCHEMA_VERSION from the exporter without importing the heavy module."""
    if not EXPORTER_PATH.exists():
        return None
    for line in EXPORTER_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*SCHEMA_VERSION\s*=\s*(\d+)", line)
        if match:
            return int(match.group(1))
    return None


def _live_milestone_name() -> Optional[str]:
    """Read MILESTONE_NAME from the exporter without importing the heavy module."""
    if not EXPORTER_PATH.exists():
        return None
    for line in EXPORTER_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r'\s*MILESTONE_NAME\s*=\s*["\']([^"\']+)["\']', line)
        if match:
            return match.group(1)
    return None


def load_registry() -> dict[str, Any]:
    """Return the parsed plan registry (index.yaml)."""
    return _load_yaml(REGISTRY_PATH)


def load_milestones() -> dict[str, Any]:
    """Return the parsed milestone benchmark catalog (milestones.yaml)."""
    return _load_yaml(MILESTONES_PATH)


def load_ledger() -> dict[str, Any]:
    """Return the parsed activity ledger (activity.yaml)."""
    return _load_yaml(LEDGER_PATH)


def resolve_plan(plan_id: str, registry: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    """Look up a plan by its logical id, regardless of which folder it lives in."""
    registry = registry if registry is not None else load_registry()
    for plan in registry.get("plans", []):
        if plan.get("plan_id") == plan_id:
            return plan
    return None


def task_ids_for(plan_id: str, registry: Optional[dict[str, Any]] = None) -> set[str]:
    """Return the set of task_ids declared by a plan's tasks file (empty if none)."""
    plan = resolve_plan(plan_id, registry)
    if not plan or not plan.get("tasks"):
        return set()
    tasks_doc = _load_yaml(REPO_ROOT / plan["tasks"])
    return {t.get("task_id") for t in tasks_doc.get("tasks", []) if t.get("task_id")}


def activity_for(
    wave: Optional[int] = None,
    plan_id: Optional[str] = None,
    ledger: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Filter ledger events by wave and/or plan_id."""
    ledger = ledger if ledger is not None else load_ledger()
    events = ledger.get("events", [])
    if wave is not None:
        events = [e for e in events if e.get("wave") == wave]
    if plan_id is not None:
        events = [e for e in events if e.get("plan_id") == plan_id]
    return events


def record_event(event: dict[str, Any]) -> None:
    """Append one event to the ledger (folder-agnostic; keyed by wave/plan_id/task_id)."""
    if "plan_id" not in event or "wave" not in event:
        raise ValueError("an activity event must carry at least 'wave' and 'plan_id'")
    ledger = load_ledger() or {"ledger_version": 1, "events": []}
    ledger.setdefault("events", []).append(event)
    with LEDGER_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(ledger, handle, sort_keys=False, default_flow_style=False)


def correlate() -> list[str]:
    """Verify every activity event maps to a real plan/task/wave. Returns problems."""
    registry = load_registry()
    ledger = load_ledger()
    problems: list[str] = []

    for plan in registry.get("plans", []):
        for key in ("spec", "tasks"):
            rel = plan.get(key)
            if rel and not (REPO_ROOT / rel).exists():
                problems.append(f"registry plan {plan.get('plan_id')}: missing {key} file {rel}")

    for idx, event in enumerate(ledger.get("events", [])):
        plan_id = event.get("plan_id")
        plan = resolve_plan(plan_id, registry)
        if plan is None:
            problems.append(f"event[{idx}]: plan_id '{plan_id}' not found in registry")
            continue
        wave = event.get("wave")
        if wave is not None and wave not in (plan.get("waves") or []):
            problems.append(
                f"event[{idx}]: wave {wave} not declared for plan '{plan_id}' (waves={plan.get('waves')})"
            )
        task_id = event.get("task_id")
        if task_id:
            known = task_ids_for(plan_id, registry)
            if known and task_id not in known:
                problems.append(f"event[{idx}]: task_id '{task_id}' not found in plan '{plan_id}'")

    catalog = load_milestones()
    milestones = catalog.get("milestones", [])
    if milestones:
        versions = [m.get("version") for m in milestones]
        int_versions = [v for v in versions if isinstance(v, int)]
        if len(int_versions) != len(set(int_versions)):
            problems.append("milestones: duplicate version numbers")
        declared = catalog.get("current_schema_version")
        newest = max(int_versions) if int_versions else None
        if declared is not None and newest is not None and declared != newest:
            problems.append(
                f"milestones: current_schema_version {declared} != newest catalog milestone {newest}"
            )
        live_version = _live_schema_version()
        if live_version is not None and declared is not None and live_version != declared:
            problems.append(
                f"milestones: current_schema_version {declared} != live SCHEMA_VERSION {live_version} (planning drifted from code)"
            )
        # The newest catalog milestone NAME must match the live exporter constant,
        # so a same-version rename can't silently pass the number-only check.
        live_name = _live_milestone_name()
        if live_name is not None and newest is not None:
            newest_named = next(
                (m.get("milestone_name") for m in milestones if m.get("version") == newest), None
            )
            if newest_named is not None and newest_named != live_name:
                problems.append(
                    f"milestones: newest catalog milestone_name '{newest_named}' != live MILESTONE_NAME '{live_name}'"
                )
        # The declared benchmarks span (e.g. "11-17") must be present once each,
        # with no gaps and nothing outside the range.
        span = str(catalog.get("benchmarks", "")).strip()
        span_match = re.fullmatch(r"(\d+)-(\d+)", span)
        if span_match:
            low, high = int(span_match.group(1)), int(span_match.group(2))
            expected = set(range(low, high + 1))
            present = set(int_versions)
            missing = sorted(expected - present)
            extra = sorted(present - expected)
            if missing:
                problems.append(f"milestones: benchmarks span {span} missing version(s) {missing}")
            if extra:
                problems.append(f"milestones: version(s) {extra} outside declared benchmarks span {span}")
        for milestone in milestones:
            version = milestone.get("version")
            for field in ("version", "milestone_name", "snapshot"):
                if not milestone.get(field):
                    problems.append(f"milestone v{version}: missing required field '{field}'")
            snapshot = milestone.get("snapshot") or ""
            if isinstance(version, int) and not snapshot.endswith(f"graph_metadata.v{version}.json"):
                problems.append(
                    f"milestone v{version}: snapshot filename does not match version ({snapshot})"
                )
    return problems


def main() -> int:
    registry = load_registry()
    ledger = load_ledger()
    start_wave = ledger.get("activity_start_wave")

    print(f"Plan activity ledger — tracking started at wave {start_wave}")
    print(f"Registry: {REGISTRY_PATH.relative_to(REPO_ROOT)} ({len(registry.get('plans', []))} plans)")
    print(f"Ledger:   {LEDGER_PATH.relative_to(REPO_ROOT)} ({len(ledger.get('events', []))} events)")
    print()

    for wave_def in registry.get("waves", []):
        wave = wave_def.get("wave")
        if start_wave is not None and wave < start_wave:
            continue
        events = activity_for(wave=wave, ledger=ledger)
        marker = "  <- activity_start" if wave_def.get("activity_start") else ""
        print(f"Wave {wave}: {wave_def.get('theme')}{marker}")
        for plan_id in wave_def.get("plan_ids", []):
            plan = resolve_plan(plan_id, registry)
            folder = (plan.get("spec", "").split("/")[0]) if plan else "?"
            print(f"  - {plan_id}  [{folder}]  status={plan.get('status') if plan else 'UNKNOWN'}")
        for event in events:
            print(f"    * {event.get('ts')} {event.get('event')} ({event.get('task_id') or 'plan-level'})")
        print()

    catalog = load_milestones()
    milestones = catalog.get("milestones", [])
    if milestones:
        print(
            f"Milestone benchmarks ({catalog.get('benchmarks', '?')}) — "
            f"live SCHEMA_VERSION={_live_schema_version()}"
        )
        for milestone in milestones:
            series = f" [{milestone['series']}]" if milestone.get("series") else ""
            print(
                f"  v{milestone.get('version')} {milestone.get('milestone_name')}{series}"
                f"  ({milestone.get('date')})"
            )
        print()

    problems = correlate()
    if problems:
        print(f"CORRELATION FAILED ({len(problems)} problem(s)):")
        for problem in problems:
            print(f"  ! {problem}")
        return 1
    print("CORRELATION OK — every event maps to a real plan / task / wave.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
