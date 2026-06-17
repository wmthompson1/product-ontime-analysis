---
name: OpenAI key auth state & deterministic-first drafting
description: The repl's OPENAI_API_KEY fails auth; AI drafting paths must fall back to deterministic, which also matches the user's cost preference.
---

The `OPENAI_API_KEY` present in this repl currently fails with an
`AuthenticationError` (invalid/revoked). Any feature that "optionally" calls
OpenAI (e.g. field-description AI drafting via `--ai` / `ai_draft` /
`use_kb`+`kb_context`) will error out if it actually hits the API.

**Why:** Discovered while authoring the 223 graph-column field descriptions
(overlay `api_field_descriptions` + root `field_descriptions.csv`). The plan
called for gpt-4o-mini drafts; the key auth-failed, so the committed CSV was
generated with the deterministic pattern-based drafter instead. This also
aligns with the standing user preference: cost-conscious, deterministic before
live AI.

**How to apply:** Before relying on OpenAI here, re-verify the key actually
authenticates (it may have been rotated since this note). Default to the
deterministic path and only invoke AI when explicitly asked and after
confirming a working key. Build AI calls so a missing/invalid key degrades
gracefully to deterministic rather than crashing.
