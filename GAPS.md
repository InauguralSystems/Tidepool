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
