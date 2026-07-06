---
name: Proxy Host header & mount redirects
description: Why the bare-domain preview broke with localhost redirects, and the rule for the Vite pass-through proxy
---

# Proxy Host header & trailing-slash mount redirects

Starlette/FastAPI mounts (e.g. Gradio at `/gradio`) answer `/gradio` (no
trailing slash) with an absolute 307 to `/gradio/` built from the request's
`Host` header. Any proxy in front that rewrites `Host` to its upstream
(`localhost:5000`) makes real browsers follow a redirect to localhost —
symptom: "refused connection" / "took too long" on the public dev URL, while
curl from inside the repl looks fine.

**Why:** the mockup-sandbox Vite pass-through proxy (bare domain, ext 80)
originally forwarded `host: target.host`; the app's root page also
meta-refreshed to `/gradio` (slashless), guaranteeing the poisoned hop.

**How to apply:**
- The pass-through proxy must preserve the original `Host`
  (`req.headers.host || target.host`) and default `x-forwarded-proto` to
  `https`.
- Internal links/redirects to mounted sub-apps should always include the
  trailing slash (`/gradio/`) to skip the canonicalization redirect entirely.
- Diagnose with `curl -w '%{redirect_url}'` on the slashless path through
  every route (bare domain AND direct `:5000`) — inside-the-repl 200s do not
  prove browsers are fine.
