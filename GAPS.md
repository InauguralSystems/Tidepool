# EigenScript Language Gaps Found During Tidepool Port

Discovered while porting sporelike-c to EigenScript. Each gap represents
a real limitation hit during non-trivial game development.

---

## GAP-001: No frequency sweep in audio builtins
- Found during: Audio Synthesis (Phase 1)
- Severity: Medium
- Workaround: Chain 8 short sine/saw tones at linearly interpolated frequencies via `generate_sweep()` in audio.eigs
- Proper fix: Add `audio_sweep of [freq_start, freq_end, duration, amplitude, waveform]` builtin that generates a continuous frequency sweep with phase continuity

## GAP-002: No loop playback for audio
- Found during: Audio Synthesis (Phase 1)
- Severity: Medium
- Workaround: Poll `audio_queue_size` each frame and re-queue ambient samples when buffer runs low
- Proper fix: Add `audio_loop of samples` that continuously re-queues, or `audio_play of [samples, loops]` with loop count (-1 for infinite)

## GAP-003: No per-channel volume control
- Found during: Audio Synthesis (Phase 1)
- Severity: Low
- Workaround: Pre-scale danger sound with `audio_gain` each frame based on threat proximity (allocates new sample list each time)
- Proper fix: Add multi-channel support: `audio_play` returns channel ID, `audio_volume of [channel, vol]` adjusts live

## GAP-004: Inner loop performance with function calls
- Found during: NPC AI (Phase 2)
- Severity: High
- Workaround: Run expensive searches (food-seeking, NPC hunting, boid flocking) only on retarget ticks (~every 30-90 frames) instead of every tick. Use distance-squared comparisons to avoid `sqrt`. Still 4x slower than simple wander AI (50ms vs 12ms per tick with 8 predators + 52 food).
- Note: Also blocks expanding observation from 20 to 107 features (9x9 spatial grid) which would add more entity iteration loops.
- Proper fix: Bytecode compilation or JIT for hot loops. Each `torus_delta`/`torus_dist_sq` call inside a nested loop goes through full interpreter dispatch. With 8 predators × 52 food items, that's ~400 function calls per retarget tick. The `unobserved` block helps with observer overhead but not dispatch cost. A batch distance builtin (e.g., `nearest_in_range of [entities, x, y, range, world_w, world_h]`) returning index+distance would also help.
- **Partial mitigation (2026-06-08, application-level):** Applied DMG hot-loop playbook (rule 1: inline 1 call/iter before anything else). Inlined `torus_delta` into `torus_dist_sq` in math_utils.eigs, then inlined `torus_dist_sq` at the five per-tick call sites in game.eigs (player×food, predator×food filter-eat, predator-player delta, predator-player collision, player-meat collision), hoisting world constants out of the inner loops. Benchmark scenario (60×20, seed 42, 6 filter + 2 proboscis predators, 52 food): **n=10 median 236.5 → 166.4 ms per 100 game_ticks, 29.6% reduction**, regressions pass. Per-tick call count dropped by ~1100 (most from the 6×52 predator×food eat loop). Confirms the underlying gap is still real — the manual inlining is what bytecode compilation + slot inference would do automatically — but unblocks the 9×9 spatial grid expansion at current EigenScript.

## GAP-005: No non-blocking channel receive
- Found during: Interactive Training UI (Phase 7)
- Severity: High
- Workaround: Training thread writes result to a file. Main thread polls `file_exists` + `read_text` (non-blocking) instead of `recv`. Clunky but avoids blocking the game loop.
- Proper fix: Add `try_recv of channel` that returns null immediately if empty (non-blocking), or `recv_timeout of [channel, ms]`. This is essential for any real-time application (game loops, UI threads) that needs to check for messages without stalling.

## GAP-006: spawn takes no arguments
- Found during: Interactive Training UI (Phase 7)
- Severity: Medium
- Workaround: Save training data to file before spawning. Training thread reads from file instead of receiving data as arguments.
- Proper fix: `spawn of [fn, arg1, arg2, ...]` that deep-copies arguments and passes them to the function. Or support closures that capture local variables by value.
