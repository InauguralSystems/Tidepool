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
