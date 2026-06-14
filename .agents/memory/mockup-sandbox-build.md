---
name: mockup-sandbox build vs dev typecheck
description: Why a broken import passes the mockup-sandbox dev server but fails CI; entry files must use named imports.
---

# mockup-sandbox: dev server does NOT type-check; CI does

The Vite dev server (`artifacts/mockup-sandbox`, workflow "Component Preview
Server") transpiles per-module and **does not run a type check**, so a wrong
import (e.g. a default import of a named export) renders fine in the preview
yet fails the CI `tsc` step with errors like `TS2613: Module '…' has no
default export`.

**Rule:** the standalone/entry files (`standalone.tsx`,
`define-relationship-main.tsx`, etc.) must import mockup components the way
they are exported. The mockup components are **named** exports
(`export function DefineRelationship()`), so use
`import { DefineRelationship } from "…"`, not a default import.

**Why:** a green dev preview is not proof the build passes. Only CI / a real
`tsc` catches export/type mismatches.

**How to apply:** after touching mockup entry files or component exports,
don't trust the running preview alone — reason about the export shape, or run
the project's own `npm run typecheck` (note: `typescript` may not be installed
in this workspace's node_modules, and `vite build` needs `PORT`/`BASE_PATH`
env vars the workflow/CI set, so a bare local build can fail for unrelated
environment reasons).
