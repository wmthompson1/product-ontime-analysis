# Core-Framework Knowledge-Loop Podcast

## What & Why
Turn the four enterprise knowledge-loop docs in `docs/my-mrp-kb/01-core-framework/` into a two-host podcast (same ALEX/SAM style the user approved for the planning-doc series) for hands-free personal listening. Personal study use only — no resale; open the audio with a short spoken disclaimer stating it is a personal study aid summarizing internal knowledge-loop documents.

Source material (~17k words total):
- Knowledge Loop Framework — Aerospace MRP (~1.5k words)
- Manufacturing and MRP Terminology in Semantic Models (~15k words — the big one; must be split into themed chapter episodes, not one giant episode)
- My MRP 501.001 Outline — Core — Parts (~285 words)
- My MRP — Deterministic Semantic Architecture (~304 words)

## Done looks like
- One continuous, loudness-normalized MP3 in `attached_assets/generated_audio/` covering all four docs as conversational episodes (framework first, then terminology chapters, then outline + architecture), presented to the user
- A ~10-second spoken disclaimer at the top ("personal study aid, summarizes internal knowledge-loop documents, not for redistribution")
- Episode scripts saved in an `episodes.json` (same format as the planning-doc series) so episodes can be re-stitched or extended without re-rendering
- Before any TTS spend: user sees the episode plan (episode list + estimated runtime + rough cost) and confirms — the user is cost-conscious and the terminology doc could balloon the line count

## Out of scope
- Verbatim read-throughs of the docs (episodes are conversational digests, like the approved planning-doc series)
- Podcast for other my-mrp-kb topic folders (02–06) — only 01-core-framework
- Any changes to the librarian MCP, ingestion runner, or the KB folder layout
- Publishing/distribution of any kind

## Steps
1. **Brief the docs** — Read all four docs; split the Terminology doc into coherent themed chapters (by its section structure) so each episode stays digestible.
2. **Propose the episode plan** — Present the episode list with estimated total runtime and TTS cost; get user confirmation before rendering.
3. **Author scripts** — Write two-host episodes in the approved style (ALEX explains, SAM peer-reviews; one "let me play that back" recap and one "the headline is" line per episode), plus the disclaimer intro; apply the established pronunciation guide (SQL→sequel, SQLite→Sequel-Light, ArangoDB→Arango D-B, MRP/ERP spelled out, etc.).
4. **Render with cache** — TTS the lines in chunks with retry/backoff, using the content-hash cache so nothing renders twice (same voices/settings as the planning-doc series).
5. **Stitch & normalize** — Concatenate with the existing gap files, loudness-normalize in ~10–15-min chunks at silence boundaries then losslessly join (long single-pass loudnorm exceeds the shell time limit), and present the final MP3.

## Relevant files
- `docs/my-mrp-kb/01-core-framework/Knowledge Loop Framework - Aerospace MRP.md`
- `docs/my-mrp-kb/01-core-framework/Manufacturing and MRP Terminology in Semantic Models.md`
- `docs/my-mrp-kb/01-core-framework/My MRP 501.001 Outline - Core - Parts.md`
- `docs/my-mrp-kb/01-core-framework/My MRP - Deterministic Semantic Architecture.md`
- `attached_assets/generated_audio/task241/episodes.json`
- `attached_assets/generated_audio/task241/_gap.mp3`
- `attached_assets/generated_audio/task241/_gap_big.mp3`
- `.agents/memory/long-audio-ffmpeg-limits.md`
