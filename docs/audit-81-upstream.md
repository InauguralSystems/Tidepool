# Draft upstream EigenScript issues recommended by audit #81

These are drafts for the orchestrator. Search before filing; #1216 already owns the gfx request and must not be duplicated.

## 1. Package: reusable gfx draw-list recorder

**Title:** `package: record/replay wrapper for gfx draw primitives`

**Repro:** Tidepool must maintain seven identical branches in `src/draw.eigs:51-91` and a matching dispatch ladder at `src/draw.eigs:96-112` merely to inspect a frame without SDL. Every gfx consumer that wants structural rendering tests must recreate the same operation schema.

**Why:** Headless-inspectable drawing is consumer infrastructure, not game logic. Ship a pure-`.eigs` package that records, counts, replays, and can be extended with future primitives; define a stable op representation so application tests survive backend changes. It should compose with, not replace, pixel tests.

## 2. Package: procedural SFX recipes and channel lifecycle

**Title:** `package: high-level procedural SFX and persistent-channel lifecycle over audio_*`

**Repro:** Tidepool's `src/audio.eigs:34-86` repeatedly composes sweep/noise, envelope, gain and play; application code must separately retain channel ids, stop them, and avoid restarting persistent loops.

**Why:** The mixer primitives are complete, but correct “start once / update volume / stop” behavior and common sweep-envelope recipes are duplicated consumer code. A pure-`.eigs` package should own lifecycle and recipes while games provide named parameters/assets. Coordinate with EigenScript#2170's shared UI/audio package edge.

## 3. JIT: quantify call/namespace overhead exposed by Tidepool

**Title:** `jit: module namespace access and small helper calls retain measurable Ir overhead in consumer hot loops`

**Repro:** Use the two 550-tick fixtures and exact cachegrind commands in `audit.md`; one differs only by spelling Tidepool's food distance inline versus calling `torus_dist_sq`. Report both `PROGRAM TOTALS` Ir values and architecture/runtime SHA. A second fixture should compare imported namespace constants to function-local hoists.

**Why:** v0.12 closed the original interpreter-dispatch gap, but consumer code remains manually expanded and the Stage 5 docs say namespace dict probes bail out. If the measured call form is materially worse, this is a current optimizer target; if parity holds, Tidepool can delete fragile duplication. Require cachegrind Ir, not wall time.

## 4. Graphics capability request — do not file; update EigenScript#1216

**Title:** Existing `gfx: no image blit, no additive blend, no polygon/gradient, no font API...`

**Repro:** v0.48.0 exposes point/line/rect/rrect/circle/text/framebuffer operations but no image load/draw/cache, additive blending, arbitrary filled polygon, gradient/soft circle, alpha line/point, or explicit font handle. Tidepool's target frame is `docs/concept-2026-09-20.png`; the structural requirements are `docs/ORACLE.md:49-78`.

**Why:** These are the missing runtime primitives behind #43, not invitations for local scanline/sprite workarounds. #1216 already specifies pixel tests, no new link dependency, and acceptance. Add current v0.48.0 confirmation and prioritize it; do not open six fragmented duplicates.
