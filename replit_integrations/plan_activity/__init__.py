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

import json
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
    """Append one event to the ledger (folder-agnostic).

    An event keys on ONE of two logical spines: a plan (``wave`` + ``plan_id``)
    or a milestone (``version`` and/or ``milestone`` M-series). Neither spine
    refers to a file path, so the link survives a plan or snapshot being moved.
    """
    has_plan_field = event.get("plan_id") is not None or event.get("wave") is not None
    has_milestone_field = event.get("version") is not None or event.get("milestone") is not None
    plan_keyed = event.get("plan_id") is not None and event.get("wave") is not None
    milestone_keyed = event.get("version") is not None  # 'milestone' series is optional metadata
    if has_plan_field and has_milestone_field:
        raise ValueError(
            "an activity event must use a single spine — plan ('wave' + 'plan_id') "
            "OR milestone ('version'), not both"
        )
    if not (plan_keyed or milestone_keyed):
        raise ValueError(
            "an activity event must key on either ('wave' + 'plan_id') "
            "or a milestone ('version', with optional 'milestone' series)"
        )
    ledger = load_ledger() or {"ledger_version": 1, "events": []}
    ledger.setdefault("events", []).append(event)
    with LEDGER_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(ledger, handle, sort_keys=False, default_flow_style=False)


def _correlate_milestone_event(
    idx: int, event: dict[str, Any], by_version: dict[Any, dict[str, Any]]
) -> list[str]:
    """Validate one milestone-keyed event against the milestone catalog.

    A milestone event maps canonical artifacts to a frozen schema version. It must
    name a real catalog version, agree with that version's M-series, list only
    artifacts that exist on disk, and include the milestone's own snapshot.
    """
    problems: list[str] = []
    version = event.get("version")
    series = event.get("milestone")
    if version is None:
        problems.append(
            f"event[{idx}]: milestone event missing required 'version' (series={series!r})"
        )
        return problems
    entry = by_version.get(version)
    if entry is None:
        problems.append(f"event[{idx}]: milestone version {version} not found in milestones.yaml")
        return problems
    if series is not None and entry.get("series") != series:
        problems.append(
            f"event[{idx}]: milestone '{series}' != catalog series '{entry.get('series')}' for v{version}"
        )
    artifacts = event.get("artifact") or []
    for art in artifacts:
        if not (REPO_ROOT / art).exists():
            problems.append(f"event[{idx}]: artifact '{art}' does not exist")
    snapshot = entry.get("snapshot")
    if snapshot and snapshot not in artifacts:
        problems.append(
            f"event[{idx}]: milestone v{version} snapshot '{snapshot}' not among mapped artifacts"
        )
    return problems


def _correlate_snapshot_counts(milestone: dict[str, Any], snapshot: str) -> list[str]:
    """Prove a milestone's declared node/edge counts match its frozen snapshot.

    Skips silently when the snapshot is absent (e.g. a private mirror that does
    not ship the .vN.json files) so the check degrades instead of failing closed.
    """
    problems: list[str] = []
    version = milestone.get("version")
    declared_n = milestone.get("node_count")
    declared_e = milestone.get("edge_count")
    if (declared_n is None and declared_e is None) or not snapshot:
        return problems
    snap_path = REPO_ROOT / snapshot
    if not snap_path.exists():
        return problems
    try:
        data = json.loads(snap_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        problems.append(f"milestone v{version}: cannot read snapshot counts ({exc})")
        return problems
    actual_n = len(data.get("nodes", []))
    actual_e = len(data.get("edges", []))
    if declared_n is not None and declared_n != actual_n:
        problems.append(f"milestone v{version}: node_count {declared_n} != snapshot {actual_n}")
    if declared_e is not None and declared_e != actual_e:
        problems.append(f"milestone v{version}: edge_count {declared_e} != snapshot {actual_e}")
    return problems


def _correlate_milestone_catalog(
    catalog: dict[str, Any], milestones: list[dict[str, Any]]
) -> list[str]:
    """Validate the milestone catalog itself (versions, parity with live code, counts)."""
    problems: list[str] = []
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
        problems.extend(_correlate_snapshot_counts(milestone, snapshot))
    return problems


def correlate() -> list[str]:
    """Verify every activity event maps to a real plan/task/wave or milestone. Returns problems."""
    registry = load_registry()
    ledger = load_ledger()
    catalog = load_milestones()
    milestones = catalog.get("milestones", [])
    by_version = {m.get("version"): m for m in milestones}
    problems: list[str] = []

    for plan in registry.get("plans", []):
        for key in ("spec", "tasks"):
            rel = plan.get(key)
            if rel and not (REPO_ROOT / rel).exists():
                problems.append(f"registry plan {plan.get('plan_id')}: missing {key} file {rel}")

    for idx, event in enumerate(ledger.get("events", [])):
        has_milestone = event.get("version") is not None or event.get("milestone") is not None
        has_plan = event.get("plan_id") is not None or event.get("wave") is not None
        if has_milestone and has_plan:
            problems.append(
                f"event[{idx}]: mixes plan (wave/plan_id) and milestone (version/milestone) "
                "spines — an event must use exactly one"
            )
            continue
        if has_milestone:
            problems.extend(_correlate_milestone_event(idx, event, by_version))
            continue
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

    if milestones:
        problems.extend(_correlate_milestone_catalog(catalog, milestones))
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

    mapped = [
        e for e in ledger.get("events", [])
        if e.get("version") is not None or e.get("milestone") is not None
    ]
    if mapped:
        print("Canonical artifact mappings:")
        for event in mapped:
            label = event.get("milestone") or f"v{event.get('version')}"
            count = len(event.get("artifact") or [])
            print(f"  {label} ({event.get('event')}): {count} artifact(s)")
        print()

    problems = correlate()
    if problems:
        print(f"CORRELATION FAILED ({len(problems)} problem(s)):")
        for problem in problems:
            print(f"  ! {problem}")
        return 1
    print("CORRELATION OK — every event maps to a real plan / task / wave or milestone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
