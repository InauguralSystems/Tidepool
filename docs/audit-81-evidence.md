# Issue 81 audit evidence

Started from `1fe875412cd41a3c25f419af9d698567c7b4e85a` on 2026-10-29 UTC.

This file records the commands and primary observations used by `audit.md`. It is intentionally written before analysis so partial work survives.

## Inputs read

Read Tidepool issues #81, #43, #79 and #80 through the GitHub API, and read `GAPS.md`, `CLAUDE.md`, and `README.md` in full. Source populations were derived with `git ls-files`, not handwritten.

## Runtime and lint

Built the pinned v0.48.0 checkout at `/workspace/EigenScript` (`make -C /workspace/EigenScript build -j2`). Then ran:

```sh
for f in $(git ls-files '*.eigs'); do
  /workspace/EigenScript/src/eigenscript --lint "$f"
done
```

Population: 22 tracked `.eigs` files. Result: 0 errors; 99 warnings: W001=96 and W002=3. Of W001, 91 are `src/constants.eigs` cross-file constants, three are `src/neural.eigs` offsets, one is `test_frametime.eigs`'s `result`, and one is `tidepool.eigs`'s `tutorial_shown`. W002 is unused `tier` and `mass` at `src/entities.eigs:190` and unused `mass` at line 206.

Composition census command:

```sh
git grep -nE '\b(load_file|import)\b' -- '*.eigs'
```

Result: 29 `load_file` call sites and 3 `import ui` call sites. Five source fragments suppress E003 at line 1.

## Cachegrind inlining experiment

Installed valgrind, copied the tracked source to two scratch directories, and changed exactly the food-loop block at `src/game.eigs:414-424`: inline `dx`/`dy` wrapping versus `torus_dist_sq of [gpx, gpy, f.px, f.py, ww, wh]`. Both fixtures used `new_game(60,20,42)` and exactly 550 `game_tick` calls. Commands:

```sh
(cd /tmp/tp-inline && valgrind --tool=cachegrind --cachegrind-out-file=/tmp/cg-inline /workspace/EigenScript/src/eigenscript bench.eigs)
(cd /tmp/tp-call && valgrind --tool=cachegrind --cachegrind-out-file=/tmp/cg-call /workspace/EigenScript/src/eigenscript bench.eigs)
cg_annotate /tmp/cg-inline | grep 'PROGRAM TOTALS'
cg_annotate /tmp/cg-call   | grep 'PROGRAM TOTALS'
```

Output:

```text
INLINE 26,322,922 Ir
CALL   26,259,124 Ir
```

The plain helper call is **63,798 Ir / 0.242% lower** than the manual inline form on this representative workload. Conclusion: the current JIT makes the plain spelling at least as fast here; replace this site. This is not evidence for every hoist: the other sites have different loop frequency and imported-module namespace access remains a documented JIT bailout, so each family needs its own fixture.

## Upstream verification

- EigenScript `docs/BUILTINS.md` v0.48.0 documents `nearest_in_range`/`nearest_in_range_all`, `audio_play_loop(...,-1)`, `audio_volume`, proportional TTF text, and the gfx primitive table.
- EigenScript#583 is closed (2026-07-13); v0.48.0 `docs/DIAGNOSTICS.md` documents W019/E004.
- EigenScript#1216 remains open and already enumerates image blit/cache, additive blend, alpha line/point, filled polygons/gradients/soft circles, and explicit font handles. The audit therefore recommends updating it, not filing duplicates.

## CI-equivalent validation

After installing the brief's prerequisites (`python3 -m pip install PyYAML` and `apt-get install -y libsdl2-dev libsdl2-mixer-2.0-0`), copied `.github/workflows/tests.yml`'s headless commands exactly:

```sh
make lint
make test
```

Output: `lint clean`; all four enrolled tests reported `ok`; `all headless tests passed`.
