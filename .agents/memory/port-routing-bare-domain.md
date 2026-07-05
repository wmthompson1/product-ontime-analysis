---
name: Bare domain routing & port map
description: Why the bare Replit dev domain shows the mockup Vite server and how the root redirect fixes it
---

# Bare domain routing

External port 80 (the bare dev domain, no port suffix) is owned by the mockup-sandbox Vite server — canvas mockup iframes depend on this, so do NOT remap it. The main FastAPI+Gradio app is external `:5000`.

**Why:** Repeated user-facing failures ("public base URL /__mockup/" hint page) happened whenever the Preview pane, canvas frames, or links hit the bare domain expecting the app.

**How to apply:**
- Any URL meant for the app must carry the `:5000` suffix (canvas frames, docs, smoke tests).
- The mockup Vite config has a dev middleware plugin that 302-redirects `/` and `/index.html` (query strings included) to `https://<host>:5000/`, so stray bare-domain hits land on the app automatically. Keep that plugin if the vite config is regenerated.
- Gradio "connection lost" toast after an app restart just needs a frame reload, not a config change.
