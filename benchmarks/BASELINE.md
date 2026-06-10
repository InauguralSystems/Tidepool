# Tidepool baseline

Machine: T3200 (Gateway-era laptop). Use as local trend numbers, not
universal performance claims.

## v0.12.0 baseline — 2026-06-10

EigenScript v0.12.0 (JIT Stage 5 inline matrix + temporal compile-gate),
binary built via `make gfx` (the gfx extension is required so
`test_frametime.eigs` can resolve `gfx_clear` and run all four
measurements).

Command:

```bash
/home/jon/EigenScript/src/eigenscript test_frametime.eigs
```

Wall-clock per measurement (ms), median/mean/min/max over 5 runs:

| measurement | n | median | mean | min | max |
|---|---|---|---|---|---|
| 100 game ticks | 5 | 171.67 | 170.50 | 163.91 | 175.82 |
| 10 renders (60x20) | 5 | 15.02 | 15.62 | 10.78 | 20.97 |
| 10x buffer init (1200 appends) | 5 | 12.60 | 14.38 | 10.92 | 22.65 |
| 100x join(2000 parts) | 5 | 30.74 | 31.38 | 30.32 | 32.78 |

Per-tick figure: ~1.7 ms/tick (game_tick alone, no render).

Raw run log: `frametime-v0.12.0-n5.log`.

### Notes / open questions

- The first run of this session, against an `./build.sh`-produced
  minimal binary, measured 100 game ticks at **381 ms** — over 2× the
  `make gfx` number. Same v0.12.0 source, but `./build.sh` and
  `make gfx` use different CFLAGS (`build.sh` skips
  `-D_FORTIFY_SOURCE=2 -fPIE` and the matching `-pie -Wl,-z,relro,-z,now`
  LDFLAGS). Not yet root-caused; should re-test cleanly with an
  in-repo `make` binary vs `./build.sh` binary on the same workload
  before next baseline. The release CI uses `./build.sh`, so if the
  delta is real it affects shipped binaries.
- `test_frametime.eigs` requires gfx (line 661 uses `gfx_clear`). For
  baselining, build with `make gfx` (and restore minimal with `make`
  after).

## v0.12.0 hoist sweep — 2026-06-10

Applied the iLambdaAi modernization pattern (hoist module globals
into function locals so v0.12.0's JIT inline ICs can fire) to
`game_tick` + its per-tick helpers in `src/game.eigs`. Gfx-free
bench harness `test_game_tick.eigs` (`new_game` + 50-tick warm-up,
then time 100-tick runs, n=5).

Edits:
- `game_tick`: removed redundant `pp_ww`/`pp_wh`, `pww`/`pwh`,
  `cpp_ww`/`cpp_wh`, `mp_ww`/`mp_wh` re-hoists — `ww`/`wh`/`hw`/`hh`
  already in scope from the food-collision pass. Hoisted `pred_n`,
  `food_n`, `meat_n` at the top so inner predator/food/meat loops
  don't recompute `len of ...` per outer iter.
- `npc_combat`: hoisted `ww`/`wh`/`species`/`species_n` at entry;
  hoisted attacker fields (`a_px`/`a_py`/`a_size`/`a_radius`/
  `a_species_id`) once per outer iter so the N² target loop reads
  locals.
- `player_auto_weapons`, `update_poison_clouds`, `update_epic_cells`,
  `update_part_drops`: hoisted `ww`/`wh`/`gpx`/`gpy` (+ length /
  predator-count locals) at entry.

| variant | n | mean ms | best ms |
|---|---|---|---|
| pre-hoist | 5 | 160.85 | 154.26 |
| post-hoist (5 reps × n=5, median) | 25 | 156.5 | 150.5 |

Net ~2–3% on T3200, within the per-run noise band (±10 ms). The
helpers I modernized (`update_epic_cells`, `update_poison_clouds`,
`update_part_drops`) iterate empty lists at game start since
epic/poison/part-drop entities only appear after tier-2 / kills,
so their hoist-pattern payoff isn't visible in this scenario. The
measurable gain came from `game_tick`'s main body (food collision
+ per-predator AI + `npc_combat` inner loops) where the inner
work actually fires every tick.

Matches the **proxy-vs-real bench** pattern: cleaning up obviously-
redundant global re-reads is the right hygiene, but downstream perf
only moves when the modernized path is actually hot in the chosen
benchmark.

Bench wrapper: `test_game_tick.eigs` (repo root).
