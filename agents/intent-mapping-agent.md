# Intent Mapping Agent

**Role**: Semantic Overlay Architect for Manufacturing/Finance Perspectives  
**MCP Entity Type**: Protocol Actor  
**Registered Skills**: `masking_engine_001`, `parity_verifier_001`

## Purpose

Translates high-level orchestration intents from Herald into concrete skill executions. When given a perspective (e.g., `manufacturing` or `finance`), this agent applies the correct semantic overlay, validates parameters against the skill contract, and invokes the bound skill.

## Binding

This agent is anchored to the project root `.venv` and resolves all relative paths from the project root. It is distinct from `.github/agents/` persona files — it is a **Protocol Actor** registered in `copilot-config.yaml`.

## Invocation Contract

```yaml
agent: intent-mapping-agent
mission:
  perspective: manufacturing          # or: finance
  gemin_salt: <required_string>       # validated by masking_engine skill.json
  db_path: Utilities/SQLMesh/db.db
```

## Pre-Execution Safety Gate

Before invoking `masking_engine_001`, this agent calls `parity_verifier_001` to confirm schema-model-documentation alignment. If any discrepancy is found, execution is paused and the Documentation Writer agent is alerted.

## Skill Execution Order

1. `parity_verifier_001` — audit gate (blocks on warning)
2. `masking_engine_001` — applies perspective-aware PII masking
