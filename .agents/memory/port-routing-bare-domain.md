---
name: Bare domain routing & port map
description: How the bare Replit dev domain reaches the app while the mockup Vite server owns external port 80
---

# Bare domain routing

External port 80 (the bare dev domain, no port suffix) is owned by the mockup-sandbox Vite server — canvas mockup iframes depend on path routing under it (`/__mockup/...`), so do NOT remap it. The main FastAPI+Gradio app is local port 5000 (also external `:5000`).

**Why:** The preview pane defaults to the bare domain; users repeatedly landed on Vite's "public base URL /__mockup/" hint page instead of the app. A visible 302-redirect-to-`:5000` middleware was tried first but the user asked for it to be removed (it bounced canvas frames to "external page" banners).

**Current mechanism (July 2026):** the mockup vite config has an `app-pass-through` middleware that transparently proxies every request outside `/__mockup/` (and Vite internals `/@*`, `/node_modules/`) to `http://localhost:5000` — same-origin, no redirect. So the bare domain serves the app; `/__mockup/*` still serves canvas previews. Keep this plugin if the vite config is regenerated; do NOT reintroduce the 302 redirect variant.

**How to apply:**
- `.replit` ports: local 23636 → external 80; local 5000 → external 5000. Direct `.replit` edits are blocked — port maps come from workflow tooling.
- Gradio "connection lost" toast after an app restart just needs a frame reload, not a config change.
- The pass-through requires the app workflow to be up, else non-mockup paths return 502.
