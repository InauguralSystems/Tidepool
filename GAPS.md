# EigenScript Language Gaps Found During Tidepool Port

Discovered while porting sporelike-c to EigenScript. Each gap represents
a real limitation hit during non-trivial game development.

---

## GAP-001: No frequency sweep in audio builtins ✅ RESOLVED
- Found during: Audio Synthesis (Phase 1)
- Severity: Medium
- Workaround: Chain 8 short sine/saw tones at linearly interpolated frequencies via `generate_sweep()` in audio.eigs
- Proper fix: Add `audio_sweep of [freq_start, freq_end, duration, amplitude, waveform]` builtin that generates a continuous frequency sweep with phase continuity
- **Resolved (2026-06-11):** `audio_sweep` ships in EigenScript (`src/ext_gfx.c`), exact signature as requested, phase-continuous (`waveform`: 0=sine, 1=sawtooth). Predates this gap-sweep round — it was already shipped when GAPS.md was written. Done: the `generate_sweep()` helper in `audio.eigs` now wraps `audio_sweep` directly.

## GAP-002: No loop playback for audio ✅ RESOLVED (infinite included — EigenScript PR #375)
- Found during: Audio Synthesis (Phase 1)
- Severity: Medium
- Workaround: Poll `audio_queue_size` each frame and re-queue ambient samples when buffer runs low
- Proper fix: Add `audio_loop of samples` that continuously re-queues, or `audio_play of [samples, loops]` with loop count (-1 for infinite)
- **Resolved finite form (EigenScript 0.13.0 commit `16ca2b2`):** `audio_play_loop of [samples, loops]` queues the samples `loops` times in one call (finite, `loops >= 1`). Returns total samples queued (`len of samples * loops`), or `0` on bad args / closed device. Drops the per-frame poll-and-refill for any finite repetition (game ambient that plays N times, sound cue repeated, music loop that ends with the level).
- **Resolved infinite form (EigenScript PR #375, 2026-07-03):** the audio device is now a 16-channel callback mixer; `audio_play_loop of [samples, -1]` loops forever (the mixer rewinds one owned copy — loop count no longer multiplies memory) and returns a channel id. The runtime pin now carries PR #375 (v0.24.0+; Tidepool is on v0.26.0), but `src/audio.eigs` still runs the poll-and-refill (`audio_queue_size` at lines 113/134) — dropping it for `audio_play_loop[-1]` is still pending. Note the return-value change: play/play_loop now return a channel id, not a sample count.

## GAP-003: No per-channel volume control ✅ RESOLVED (EigenScript PR #375)
- Found during: Audio Synthesis (Phase 1)
- Severity: Low
- Workaround (still in place; see below): Pre-scale danger sound with `audio_gain` each frame based on threat proximity (allocates new sample list each time)
- **Resolved (EigenScript PR #375, 2026-07-03):** exactly the proposed shape — `audio_play` returns a channel id and `audio_volume of [channel, vol]` adjusts a playing channel live (0.0–4.0); `audio_stop of channel` stops one channel. The runtime pin now carries PR #375 (Tidepool is on v0.26.0), but `src/audio.eigs` still runs the per-frame `audio_gain` re-render (line 132) — replacing it with one `audio_volume` call is still pending.

## GAP-004: Inner loop performance with function calls ✅ LARGELY DELIVERED UPSTREAM (ledger refresh 2026-07-03: both proper-fix asks shipped — the bytecode VM + copy-and-patch JIT landed in v0.12.0, and `nearest_in_range` / `nearest_in_range_all` exist as builtins; the manual inlining below remains good practice per the hot-loop playbook, and re-measuring against a current pin would quantify what's left of the gap)
- Found during: NPC AI (Phase 2)
- Severity: High
- Workaround: Run expensive searches (food-seeking, NPC hunting, boid flocking) only on retarget ticks (~every 30-90 frames) instead of every tick. Use distance-squared comparisons to avoid `sqrt`. Still 4x slower than simple wander AI (50ms vs 12ms per tick with 8 predators + 52 food).
- Note: Also blocks expanding observation from 20 to 107 features (9x9 spatial grid) which would add more entity iteration loops.
- Proper fix: Bytecode compilation or JIT for hot loops. Each `torus_delta`/`torus_dist_sq` call inside a nested loop goes through full interpreter dispatch. With 8 predators × 52 food items, that's ~400 function calls per retarget tick. The `unobserved` block helps with observer overhead but not dispatch cost. A batch distance builtin (e.g., `nearest_in_range of [entities, x, y, range, world_w, world_h]`) returning index+distance would also help.
- **Partial mitigation (2026-06-08, application-level):** Applied DMG hot-loop playbook (rule 1: inline 1 call/iter before anything else). Inlined `torus_delta` into `torus_dist_sq` in math_utils.eigs, then inlined `torus_dist_sq` at the five per-tick call sites in game.eigs (player×food, predator×food filter-eat, predator-player delta, predator-player collision, player-meat collision), hoisting world constants out of the inner loops. Benchmark scenario (60×20, seed 42, 6 filter + 2 proboscis predators, 52 food): **n=10 median 236.5 → 166.4 ms per 100 game_ticks, 29.6% reduction**, regressions pass. Per-tick call count dropped by ~1100 (most from the 6×52 predator×food eat loop). Confirms the underlying gap is still real — the manual inlining is what bytecode compilation + slot inference would do automatically — but unblocks the 9×9 spatial grid expansion at current EigenScript.

## GAP-005: No non-blocking channel receive ✅ RESOLVED
- Found during: Interactive Training UI (Phase 7)
- Severity: High
- Workaround: Training thread writes result to a file. Main thread polls `file_exists` + `read_text` (non-blocking) instead of `recv`. Clunky but avoids blocking the game loop.
- Proper fix: Add `try_recv of channel` that returns null immediately if empty (non-blocking), or `recv_timeout of [channel, ms]`. This is essential for any real-time application (game loops, UI threads) that needs to check for messages without stalling.
- **Resolved (EigenScript 0.13.0 commit `082f833`):** Both forms ship. `try_recv of channel` returns the value immediately if buffered, `null` if empty (no wait, ever). `recv_timeout of [channel, ms]` returns the value if one arrives — or is already buffered — before the deadline, else `null`; also returns `null` on close-while-waiting. Fractional `ms` honored (ns precision via `pthread_cond_timedwait`); negative `ms` degenerates to `try_recv`. Drop the file-polling workaround — main loop should `try_recv` per frame, or `recv_timeout` per frame with a small `ms` budget if it wants to yield the main thread briefly.

## GAP-006: spawn takes no arguments ✅ RESOLVED
- Found during: Interactive Training UI (Phase 7)
- Severity: Medium
- Workaround: Save training data to file before spawning. Training thread reads from file instead of receiving data as arguments.
- Proper fix: `spawn of [fn, arg1, arg2, ...]` that deep-copies arguments and passes them to the function. Or support closures that capture local variables by value.
- **Resolved (EigenScript 0.13.0 commit `5a857d0`):** `spawn of [fn, arg1, arg2, ...]` now passes N positional arguments. Bare `spawn of fn` (zero args) and the original `spawn of [fn, arg]` (one arg) keep working verbatim. Missing trailing params bind to `null`; extra args are ignored. **Args are shared by reference, not deep-copied** — matches the channel model already in place (see EigenScript `docs/BUILTINS.md` thread-safety note). Drop the save-to-file workaround. For the training-data case specifically: pass the training data and channel(s) as positional args to the spawned function directly.

## GAP-007: No audio file / music playback ✅ RESOLVED
- Found during: Background music (post-1.0 polish)
- Severity: Medium
- Workaround: None viable — EigenScript audio was sample-queue only
  (`audio_open` + `audio_play` of synthesized PCM). A multi-minute MP3 can't be
  loaded as an EigenScript sample list, and there was no file decode/stream.
- Proper fix: A streaming file-playback builtin (decode + stream + loop a
  music file), separate from the SFX sample queue.
- **Resolved (EigenScript 0.18.0):** `audio_music_play of [path, loops]`
  (loops `-1` = forever), `audio_music_volume of v` (0–128), and
  `audio_music_stop of null` stream an mp3/ogg/wav via SDL_mixer on the mixer's
  own audio device, alongside the SFX queue (two SDL devices, OS-mixed). MP3
  decode via libmpg123. SDL_mixer is `dlopen`ed lazily; requires
  `libsdl2-mixer-2.0-0` at runtime. Tidepool now plays a looping background
  track (`assets/music/tidepool_background.mp3`).

## GAP-008: Silent question-word "assignment" — no lint warning (filed: EigenScript#583)
- Found during: Audio-init hardening (issue #23, 2026-07-12)
- Severity: Medium (silent-wrong output, zero diagnostics)
- What happened: in a catch handler, `local why is "init failed"` followed by
  `why is "no audio builtins in this build"` inside an `if` silently kept the
  stale value — `why` is a question word, so the bare statement is the
  interrogative form (an expression evaluated and discarded), never an
  assignment. The game printed the wrong fallback message; nothing failed.
- Workaround: renamed the variable (`why` → `reason`). House rule: never bind
  question words (`what who when where why how`) with plain `is`.
- Proper fix: a lint W-rule flagging an interrogative used as a bare
  statement (its result is always discarded — dead code at best, a mistaken
  assignment at worst, especially when a same-named binding is in scope).
  Filed upstream as [EigenScript#583](https://github.com/InauguralSystems/EigenScript/issues/583).
