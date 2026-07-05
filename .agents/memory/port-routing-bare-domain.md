---
name: Bare domain routing & port map
description: Why the bare Replit dev domain shows the mockup Vite server and how stray hits behave
---

# Bare domain routing

External port 80 (the bare dev domain, no port suffix) is owned by the mockup-sandbox Vite server — canvas mockup iframes depend on this, so do NOT remap it. The main FastAPI+Gradio app is external `:5000`.

**Why:** The Preview pane, canvas frames, or links that hit the bare domain expecting the app land on the Vite server instead (its base is `/__mockup/`, so off-base paths show Vite's "public base URL /__mockup/" hint page).

**How to apply:**
- Any URL meant for the app must carry the `:5000` suffix (canvas frames, docs, smoke tests).
- The root-redirect-to-:5000 middleware that used to live in the mockup vite config was REMOVED at the user's explicit request (July 2026) — do NOT reintroduce it. Bare-domain `/` now 302s to `/__mockup/` (Vite's native base redirect) and stays on the mockup server.
- Gradio "connection lost" toast after an app restart just needs a frame reload, not a config change.
