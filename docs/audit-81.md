# Tidepool modernization audit (#81)

Audit date: 2026-10-29. Scope: EigenScript v0.48.0; no game code changed. Rankings are **language stress × user-visible effect** (1 is highest). `file upstream` means use the draft in `docs/audit-81-upstream.md`; existing upstream reports are linked rather than duplicated.

## Track 1 — training works and is gated

1. **The optimizer is broken and CI cannot see it (very high × invisible model failure).** `train.eigs` stores transition observations in a numeric shaped buffer at lines 112–118; v0.48.0 rejects the first nested buffer store. The public repro from #80 is `eigenscript train.eigs --episodes 1 --seed 79 --ticks 31 --batch 8 --buffer 128`. CI only invokes the four tests named in `Makefile:44-47`; neither training nor evaluation runs. **Disposition: replace with numeric row copy after #80 identifies the compatibility boundary; add a deterministic few-step test asserting finite loss and changed weights, and run it in the headless CI job.**

2. **Training progress ignores the observer (high × training quality).** Manual 50-episode accumulators (`train.eigs:498-504`) and block logging (`train.eigs:620-665`) track exactly the loss/Q/tier dynamics for which v0.48.0 supplies `observe`, `improving`, `diverging`, and `converged`. **Disposition: replace the hand-coded trend decision (not the durable CSV telemetry) with current observer predicates sampled once per optimizer step; gate divergence/non-finite loss explicitly.**

3. **Untested behavior.** No test takes an optimizer step, resumes a checkpoint, round-trips a policy, checks finite/decreasing loss or weight mutation, compares inference before/after serialization, covers CLI argument boundaries, or runs `eval_policy.eigs`; #80 proves the consequence. Rendering tests cover structure but CI does not run `test_frametime.eigs`, `test_game_tick.eigs`, `test_gfx.eigs`, `pacing_harness.eigs`, `train.eigs`, or `eval_policy.eigs` (`Makefile:38-48`; `.github/workflows/tests.yml:25-41`). **Disposition: replace CI coverage with a fast optimizer-step regression in `make test`; keep slow baseline/eval/training on #79's off-box lane; add explicit jobs/issues for deterministic perf and CLI smoke checks.**

## Track 2 — ML moves to a package

1. **Local MLP/DQN/autograd duplicates the current ecosystem (very high × learned-brain differentiator).** `src/neural.eigs:38-179` owns initialization and buffer forward inference; `train.eigs:179-361` owns cached forward/backprop/SGD, while v0.48.0 ships `lib/autograd.eigs` (including clipped SGD). **Disposition: replace with the eigs-ml package planned by #79 / EigenScript#2170; use #79's move/stay inventory and baseline rather than repeating it here.**

2. **Game-specific observation/reward stays local.** The 433-feature temporal observation is assembled from Tidepool entities (`src/neural.eigs:191-458`) and action selection mutates game controls (`src/neural.eigs:460-527`). **Disposition: keep: these are Tidepool environment/adaptor semantics, not general ML.**

## Track 3 — graphics to the modern bar

1. **Runtime gfx lacks the concept-frame primitives (very high × largest visible effect).** Tidepool can record only clear/circle/line/text/rect/rrect/point (`src/draw.eigs:49-112`), while the required visual bar calls for a depth gradient, translucent parts, hazards and visible current (`docs/ORACLE.md:49-78`). v0.48.0 still has no image load/blit/cache, additive blend, filled polygon, gradient/radial-soft primitive, alpha on line/point, or explicit font load/handle. **Disposition: file upstream: do not emulate these in Tidepool; EigenScript#1216 already contains the complete open request, so update/execute that issue rather than filing a duplicate.**

2. **Theme/toolkit modernization is blocked only partly by gfx (medium × broad UI effect).** #43 requires a named palette/theme applied before widget construction, plus toolkit adoption; `src/editor.eigs:8-10` already imports `ui`, but renderer colors remain globals/literals (`src/renderer.eigs:19-21`). **Disposition: keep as Tidepool #43 work after gfx capabilities land; this is application design, not a runtime gap.**

3. **Draw-list recording is reusable infrastructure (medium × testability across apps).** The generic immediate/record/replay adapter and its seven nearly identical wrappers occupy `src/draw.eigs:1-112`. **Disposition: replace with an EigenScript package shared by gfx consumers; file upstream/package draft, retaining Tidepool's op-level assertions.**

## Track 4 — shared audio/draw/math code becomes packages

1. **Three live audio workarounds are obsolete (high × audible behavior/allocation).** Ambient polling/requeue remains at `src/audio.eigs:129-135` although `audio_play_loop(samples, -1)` exists; danger allocates a scaled list every update at `src/audio.eigs:136-155` although channel ids plus `audio_volume`/`audio_stop` exist; startup catches missing pre-v0.18 builtins at `src/audio.eigs:21-32,40-55` despite the v0.48.0 pin. **Disposition: replace with one infinite ambient channel and one persistent danger channel with live volume; remove version-probe catches and retain handling only for real device/asset failure.**

2. **Procedural SFX construction is package-worthy, not a language gap (medium × reuse).** Eleven effects repeat `audio_sweep` + envelopes at `src/audio.eigs:34-86`; music already uses the runtime stream API. **Disposition: replace with a small reusable audio/SFX package (or contribute to the planned shared package in EigenScript#2170); keep only Tidepool's sound palette/asset mapping.**

3. **Math utility overlap (low × maintainability).** `clamp` and `signum` at `src/math_utils.eigs:9-21` duplicate current math facilities, while torus coordinate/distance and body-zone projection at lines 33-109 are domain geometry. **Disposition: replace `clamp`/`signum` with `import math` equivalents after module migration; keep torus/body helpers in Tidepool or a geometry package because they encode wrapping/world semantics.**

## Track 5 — stale workarounds and performance

### Every GAPS.md entry

1. **GAP-004 function-call/JIT workaround (high × tick rate): closed upstream by the v0.12 bytecode/JIT and nearest-query builtins, but the local workaround needs measured removal.** Five call sites remain visibly inlined (`src/game.eigs:399-424,467-486,589-632,708-727`) and `torus_dist_sq` itself manually inlines `torus_delta` (`src/math_utils.eigs:52-66`); neural hoists world/player fields before its scans (`src/neural.eigs:191-207`). The representative food-collision comparison below is the decision evidence. **Disposition: replace this representative inline site with `torus_dist_sq`: the plain call used 63,798 fewer Ir (0.242%); measure the other four game sites and neural hoists independently before removing them.**

2. **GAP-005 nonblocking receive: closed by commit `082f833` (`try_recv`, `recv_timeout`).** No channel or file-poll training UI remains in the current tree (derived with `git grep -nE 'try_recv|recv_timeout|file_exists|spawn|channel' -- '*.eigs'`; only checkpoint/file uses remain). **Disposition: remove the stale GAPS entry; no Tidepool workaround remains.**

3. **GAP-006 spawn arguments: closed by commit `5a857d0`.** The current tree contains no `spawn` call. **Disposition: remove the stale GAPS entry; use `spawn of [fn, args…]` if an interactive trainer returns.**

4. **GAP-002 infinite audio loop: closed by EigenScript PR #375.** Poll/requeue still exists (`src/audio.eigs:129-135`). **Disposition: replace with `audio_play_loop of [samples, -1]` and retain the channel id.**

5. **GAP-003 per-channel volume: closed by EigenScript PR #375.** Per-frame `audio_gain` remains (`src/audio.eigs:136-155`). **Disposition: replace with `audio_volume` on a persistent channel, stopping it when danger clears.**

6. **GAP-008 question-word lint: closed by EigenScript#583 on 2026-07-13; v0.48.0 documents W019/E004.** Tidepool already renamed the binding to `reason` (`src/audio.eigs:50-55`), and the full lint found no W019. **Disposition: remove the house-rule gap note; keep `reason` as clear naming.**

7. **GAP-001 frequency sweep: closed and already adopted.** `generate_sweep` is now only an envelope wrapper over `audio_sweep` (`src/audio.eigs:34-38`). **Disposition: remove the stale GAP comments at `src/audio.eigs:7-8`; keep the wrapper because it adds Tidepool's decay envelope.**

8. **GAP-007 streamed music: closed and already adopted.** `audio_music_play`/volume are used at `src/audio.eigs:21-30`. **Disposition: remove the resolved ledger entry from active gaps (or archive it as history); keep the runtime calls and asset-specific wrapper.**

### Deterministic representative inlining measurement

One site only was changed in a scratch copy: the food loop's inline torus delta (`src/game.eigs:411-424`) versus `torus_dist_sq of [gpx,gpy,f.px,f.py,ww,wh]`, with the same seed and **550 ticks** (50 warm-up-equivalent + 500 measured workload). Commands:

```sh
apt-get update -qq && apt-get install -y -qq valgrind
(cd /tmp/tp-inline && valgrind --tool=cachegrind --cachegrind-out-file=/tmp/cg-inline /workspace/EigenScript/src/eigenscript bench.eigs)
(cd /tmp/tp-call && valgrind --tool=cachegrind --cachegrind-out-file=/tmp/cg-call /workspace/EigenScript/src/eigenscript bench.eigs)
cg_annotate /tmp/cg-inline | grep 'PROGRAM TOTALS'
cg_annotate /tmp/cg-call   | grep 'PROGRAM TOTALS'
```

Results and percentage are recorded in `docs/audit-81-evidence.md`. Cachegrind's `Ir` is deterministic instruction count; this deliberately avoids #79's 32–46% wall-time spread. **Disposition: use the measured winner; do not generalize one site to all hoists.** Module-global hoists (`src/game.eigs:399-410`, `src/neural.eigs:196-207`) should each be removed only behind equivalent Ir fixtures because imported namespace member access still bails out of the JIT dict-probe fast path in v0.48.0.

## Track 6 — old idioms, lint, errors and observer use

1. **`load_file` composition prevents module isolation (high × package migration).** A source-derived search finds 29 `load_file` sites and only three `import ui` sites; modules rely on shared globals and five files suppress E003 at line 1. Current `import` executes once into a namespace and is the package path. **Disposition: replace with `import` namespaces incrementally, beginning constants/math/entities; do not mechanically convert because every member access/call site must be qualified and benchmarked.**

2. **Globals that should be local (medium × correctness).** Entry-point scratch/state is globally bound (`eval_policy.eigs:141-157`, `train.eigs:478-504`, `pacing_harness.eigs:9-26`, `tidepool.eigs:143-189`) although it is not an exported module API. Mutable module holders `_draw`, `_sounds`, editor and renderer state intentionally need module lifetime (`src/draw.eigs:18-26`; `src/audio.eigs:16-19`). **Disposition: replace entry-point scratch with `local` or a `main` function during import migration; keep module-private state but encapsulate it behind imported namespaces.**

3. **Error handling is overbroad (medium × silent missing audio/render failures).** Audio catches every exception and returns silence (`src/audio.eigs:25-32,45-55`); the frame loop catches every render error, prints, and continues (`tidepool.eigs:1059-1069`). **Disposition: replace with kind-specific expected IO/capability handling and rethrow programmer/type errors; remove compatibility catches made impossible by the pin.**

4. **Lint results (low × hygiene).** Running v0.48.0 `eigenscript --lint` on the `git ls-files '*.eigs'` population (22 files) produced **99 warnings: W001 96, W002 3, errors 0**. W001 is dominated by 91 constants falsely appearing unused because `load_file` cross-file use is invisible (`src/constants.eigs:6-150`); the actionable W001s are three neural offset constants (`src/neural.eigs:17-19`), `test_frametime.eigs:44`, and `tidepool.eigs:160`. W002 identifies unused `tier`/`mass` parameters (`src/entities.eigs:190,206`). **Disposition: replace `load_file` so lint sees namespace use, then remove real dead bindings/parameters; make CI fail on warnings after the false-positive source is gone.**

## Track 7 — CI and release discipline

1. **CI's green signal excludes the product's defining feature (very high × silent user failure).** See Track 1 and #80. **Disposition: add the optimizer-step gate first.**
2. **CI lint discards warnings (medium × maintainability).** `Makefile:53-58` greps only “error”, despite 99 warnings. **Disposition: replace with structured lint output/rule budgets temporarily, then zero-warning enforcement after imports.**
3. **Performance is wall-time-only/manual (medium × regression risk).** `test_game_tick.eigs:5-27` prints time but has no assertion and CI never runs it. **Disposition: replace/add a fixed-tick cachegrind Ir job with a stated budget only after banking a reviewed baseline; do not put valgrind in the portable suite.**
4. **Release CI is packaging-only.** `.github/workflows/release.yml` archives HEAD without depending on tests. **Disposition: keep source-archive behavior, but require protected-tag/test workflow success through GitHub environment/branch policy rather than duplicating the suite.**
