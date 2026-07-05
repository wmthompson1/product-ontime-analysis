---
name: Gradio chained programmatic .change events
description: Multi-input handlers break when a .change is triggered programmatically by another handler's gr.update
---

# Gradio chained programmatic `.change` events

**Rule:** In a cascading-dropdown chain, every `.change` handler must take exactly ONE input — the trigger component itself. If a handler needs more context (e.g. the parent filter's value), pack it into the trigger dropdown's *value* string (e.g. `f"{parent}\x1f{child}"`) and unpack server-side.

**Why:** When handler A returns `gr.update(value=...)` for dropdown B, Gradio fires B's `.change` programmatically but delivers only B's own value — a handler declared with `inputs=[other, B]` fails at runtime with *"didn't receive enough input values (needed: 2, got: 1)"*. User-initiated changes work fine, so the bug only surfaces mid-cascade.

**How to apply:** Any Gradio cascade (category → anchor → item): keep all `.change` handlers single-input; encode ancestor selections into composite choice values with a non-printing separator like `\x1f`; verify via `gradio_client` predict calls against the auto-named `/_handler_name` endpoints.
