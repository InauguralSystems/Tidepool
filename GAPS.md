# EigenScript Language Gaps Found During Tidepool Port

Discovered while porting sporelike-c to EigenScript. Active gaps belong in
**Open**; shipped upstream capabilities are retained under **Resolved** as a
historical adoption ledger.

## Open

None. Performance work that remains in Tidepool is application optimization,
not a missing EigenScript capability.

## Resolved

### GAP-001: Frequency sweep

Resolved by EigenScript's `audio_sweep` builtin (shipped by 2026-06-11).
Tidepool's `generate_sweep` now adds only its game-specific decay envelope.

### GAP-002: Infinite audio loop

Resolved by [EigenScript PR #375](https://github.com/InauguralSystems/EigenScript/pull/375)
(2026-07-03). Tidepool uses `audio_play_loop of [samples, -1]` and retains the
returned channel id.

### GAP-003: Per-channel volume control

Resolved by [EigenScript PR #375](https://github.com/InauguralSystems/EigenScript/pull/375)
(2026-07-03). Tidepool retains a danger-loop channel, adjusts it with
`audio_volume`, and stops it with `audio_stop` when danger clears.

### GAP-004: Inner-loop function-call performance

Resolved upstream by the bytecode/copy-and-patch JIT in EigenScript v0.12.0
and the `nearest_in_range` / `nearest_in_range_all` builtins. The modernization
audit measured one representative `torus_dist_sq` call as 63,798 fewer
Cachegrind instructions than its manual inline form. Remaining inline sites
are Tidepool performance choices to measure independently, not language gaps.

### GAP-005: Non-blocking channel receive

Resolved by EigenScript commit `082f833`, which added `try_recv` and
`recv_timeout`. Tidepool has no remaining channel or file-poll training UI
workaround.

### GAP-006: Spawn arguments

Resolved by EigenScript commit `5a857d0`. `spawn of [fn, args...]` passes
positional arguments; Tidepool has no remaining `spawn` workaround.

### GAP-007: Streamed music playback

Resolved in EigenScript v0.18.0 by `audio_music_play`,
`audio_music_volume`, and `audio_music_stop`. Tidepool uses these builtins for
`assets/music/tidepool_background.mp3`.

### GAP-008: Question-word assignment lint

Resolved by [EigenScript issue #583](https://github.com/InauguralSystems/EigenScript/issues/583)
(2026-07-13), which documents W019/E004. Tidepool keeps the clear `reason`
naming but no longer needs a local house-rule workaround.
