---
name: Canvas artifact-frame 3s reload loop (Gradio app)
description: Why the HF Space Gradio app appears to "refresh every 3 seconds" in the Replit canvas preview, and why it is NOT an app bug.
---

# Symptom
User reports the app preview (canvas iframe on port 5000) "internally refreshing every ~3 seconds." Browser console logs an empty-object error (`[{}]`, i.e. an Event/EventSource-style error that serializes to `{}`) every ~3-5s. Server access log shows repeating `GET /gradio/gradio_api/app_id` + `GET /gradio/` + `GET /gradio/theme.css?v=...` in near-equal counts.

# This is a preview-layer probe, NOT the app
The looping requests come from the Replit proxy IPs (`10.48.x.x`) and fetch ONLY the page shell: `app_id` + index HTML + `theme.css`. They never fetch `/gradio/config`, JS bundles, `queue/join`, or `heartbeat`. A real browser session (seen as `127.0.0.1` from a screenshot load) DOES fetch config/JS/queue/heartbeat. So the loop is a non-JS-executing shell probe reloading, characteristic of the embedded canvas artifact preview frame, not a browsing session and not the application.

# Interventions that DID NOT fix it (all disproven)
- Backend was already healthy: single stable uvicorn process, exactly one startup, growing uptime (not restarting).
- `app_id` is identical across localhost / `:5000` / bare-domain, AND identical between the endpoint and the value inlined in the served HTML — so Gradio's app_id-mismatch reload is ruled out.
- Pointing the canvas iframe URL from root `/` (which `<meta refresh>`-redirects to `/gradio/`) directly at `/gradio/` (returns 200, no redirect) did nothing.
- `ssr_mode=False` on `mount_gradio_app` + restart did nothing (reverted afterward — Gradio always inlines `gradio_config` into HTML regardless of SSR, so "config inlined" is not an SSR tell).
- No Vite HMR client is injected into the served pages; `theme.css` returns valid CSS; no 404s reach uvicorn (the one browser 404 is served by the proxy layer, never reaches the app).

**Why:** three separate app-side changes changed nothing, and the loop only ever pulls the static shell via the proxy — the reload originates above the app.

**How to apply:** if a Gradio (or similar SSE-driven) app "refreshes every few seconds" only inside the Replit canvas artifact frame, do NOT chase app code. Confirm backend health + stable app_id, then tell the user to view it in the standard Preview tab / a dedicated browser tab. Ask whether the refresh also happens in a plain browser tab to distinguish canvas-frame behavior from a universal issue. Avoid repeated workflow restarts — each one invalidates the user's live Gradio session.
