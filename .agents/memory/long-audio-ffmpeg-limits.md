---
name: Long-audio ffmpeg under bash-tool limits
description: How to loudness-normalize ~1h stitched audio when commands cap at 120s and detached processes get reaped
---

**Rule:** For long stitched audio (> ~30 min), never run a single `concat + loudnorm` re-encode pass, and never rely on `nohup`/backgrounded ffmpeg surviving the bash tool session — background processes are reaped when the call returns.

**Why:** A ~55-min loudnorm re-encode exceeds the 120s bash-tool timeout, and a detached nohup ffmpeg was silently killed mid-write (file stalled, no exit marker).

**How to apply:**
1. Lossless concat all segments first (`-f concat -c copy`) — seconds, no timeout risk.
2. Split the program into ~10–15-min chunks at silence boundaries (between-episode gaps), loudnorm each chunk to the same target (I=-16:TP=-1.5:LRA=11) in separate ≤120s commands.
3. Join normalized chunks with `-c copy`. Seams in silence make per-chunk normalization inaudible.

Also: keep gap/silence files in the exact TTS output format (44.1 kHz mono mp3) or concat copy glitches.
