# CLAUDE.md

Guidance for working in this repository.

## What this is

Tidepool is a Spore-style cell-stage evolution game written **entirely in
[EigenScript](https://github.com/InauguralSystems/EigenScript)** (`.eigs`
files), a custom interpreted language with a JIT. You play a single cell:
eat food, avoid predators, spend DNA on mutations, grow through five scale
tiers. The repo doubles as a real-world stress test for EigenScript — see
`GAPS.md` and `docs/EIGENSCRIPT_REQUESTS.md`.

There is no Python/JS/native code here. The game, renderer, and a
from-scratch DQN trainer are all EigenScript.

## Design intent & priorities

Tidepool is a faithful homage to **Spore's cell stage** (Maxis): diet
choice (herbivore/carnivore/omnivore), eat food and meat, spend DNA in
the editor on parts (filter/jaw/proboscis mouths; fin/claw/cilia/poison/
electric/jet appendages), grow through scale tiers via a deliberate evolve
action (mate-calling is optional flavor — see the progression rework below),
dodge giant "epic" cells. The systems are ported faithfully — it is not a
loose tribute.

**The differentiator vs. Spore: the cells actually learn.** Spore's
creatures ran on scripted AI. Tidepool has a neural policy that perceives
the world the same way a player does (the 107-feature observation) and
learns to survive. "Spore cell stage where you watch the cells evolve
their brains, written from scratch in a homemade language" is the pitch.

Current priority order (set by the maintainer):

1. **AI** — make the learned policy genuinely good (it's the unique asset).
2. **Physics** — deepen the movement/energy/combat simulation.
3. **Gameplay** — tighten the eat → grow → evolve loop and progression.
4. **Graphics** — explicitly deferred as polish. Don't spend effort here
   until the above are solid.

When physics/gameplay change, the AI must be retrained — those edits alter
the environment the policy learned in. Sequence work as: land a
physics/gameplay change → retrain → eval, so each step has a clean
before/after.

## Toolchain

EigenScript is **not** vendored in this repo; it lives in the sibling
`../EigenScript` repo (override with `EIGS_DIR=`). **Minimum version
v0.19.0** — the neural policy stores its weights/obs as flat shaped buffers
(`buffer of [r, c]`, shaped `VAL_BUFFER` #275), which land there. (Background
music needs `audio_music_*` from v0.18.0.) **CI and the devcontainer pin
v0.35.1** via `.devcontainer/Dockerfile`'s `EIGS_REF` — build that ref for
parity.

The **Makefile** wraps the toolchain so you don't hand-manage the binary
path. These work from any directory:

```bash
make build   # build the headless EigenScript binary (no SDL2 needed)
make test    # headless suite (test_regressions, test_obs_stack, test_game, test_pacing)
make lint    # parse-check every .eigs source
make gfx     # build the graphical (SDL2) binary
make run     # play the game (needs gfx + a display)
make shot    # headless screenshot -> docs/screenshot.png (needs xvfb + python3-PIL)
```

Headless is enough for every `test_*.eigs`, `train.eigs`, and
`eval_policy.eigs`. The graphical binary is required for `tidepool.eigs`
itself and `test_frametime.eigs`. Training/eval are run directly since they
take args — see the neural rule (`.claude/rules/neural-training.md`).

Always run `test_regressions.eigs` before committing game-logic changes.

## Layout — the non-obvious parts

(`ls src/` for the rest; the file names say what they hold.)

- `src/math_utils.eigs` is hot path — its torus helpers are inlined at
  per-tick call sites (see Performance).
- The renderer never calls `gfx_*` directly; it goes through `src/draw.eigs`
  so frames are headless-inspectable. Details:
  `.claude/rules/rendering.md`.

Load order matters: `game.eigs` loads `constants`, `math_utils`,
`entities`. Load `game.eigs` **before** `neural.eigs`.

## Architecture notes

- **World is a torus.** All distance/direction math must wrap. Use
  `torus_delta` / `torus_dist` (or the inlined dx/dy wrap pattern you'll
  see in hot loops). Never use raw Euclidean deltas on world coordinates.
- **The `game` dict is the single source of truth.** `new_game(w, h, seed)`
  builds it; `game_tick(game)` advances one step reading
  `game.thrusting` / `game.braking` / `game.turning`. Discrete actions go
  through `game_action(game, ACTION_*)`.
- **Five scale tiers**, creature specs (body shape, pattern, sockets,
  appendages, spines), mutations bought with DNA, combat via appendages
  (poison clouds, electric bolts, jets) and spikes.
- **Combat is survivable** (`game_tick` predator-collision branch): a
  collision you lose deals an energy bite (scaled by the power gap, capped
  at 60) plus knockback and ~0.75s invulnerability (`invuln_timer`), not
  an instant kill. You die only when energy hits 0. Epic-cell collisions
  are still meant to be lethal hazards.
- The neural policy, DQN trainer, checkpointing, and eval methodology live
  in `.claude/rules/neural-training.md` (loads when you touch
  `neural.eigs`/`train.eigs`/`eval_policy.eigs`).

## EigenScript conventions

Writing `.eigs` here? → the **`write-eigenscript`** skill (call syntax, the
single-element-list spread trap, the outward-mutable scope model and when to
use `local`). v0.13.0+ niceties are available: destructuring, slicing,
negative indexing, default params.

## Physics & gameplay roadmap (known gaps)

Concrete, code-grounded opportunities, roughly ranked by impact-per-effort.
These are the substance behind the "physics" and "gameplay" priorities.

1. ~~**Two progression systems conflict**~~ — **RESOLVED 2026-06-25.**
   Unified on one canonical gate: eating `FOOD_PER_TIER*(tier+1)` cumulative
   food sets `game.evolve_ready`; a deliberate `ACTION_EVOLVE` (player key E
   or policy action 5) runs `evolve_tier_up` (the rich species/predator
   refresh) to advance one tier. No DNA cost, no mate requirement — the
   cost is the harsher world it summons, so *when* to evolve is the
   decision. `call_mate`/`update_mate` are now optional flavor.
   `evolve_tier_up`'s dead epic-spawn was removed (`update_epic_cells`
   handles it). Chosen over a pure mate-ritual gate because the policy is
   the priority and a movement+evolve action space keeps the one off-box
   training run tractable while letting the cell *learn* when to evolve.
2. **Food is static and teleport-respawns** (`game_tick`, food-collision
   block sets a new random position). Letting food drift with the rotating
   water current would make the current matter and the pool feel alive.
3. **Thin endgame** — progression caps at tier 5 (`SCALE_TIER_COUNT`) with
   no graduation payoff. A real win state + escalating threat curve gives
   runs a point.

## Performance

This project targets slow hardware; `game_tick` is the hot path.
- Hoist module globals into function locals so the JIT's inline caches
  fire (see `benchmarks/BASELINE.md` "hoist sweep").
- Inline `torus_*` math at per-tick call sites; compare on
  distance-squared to avoid `sqrt`; run expensive target searches only
  on retarget ticks. See `GAPS.md` GAP-004.
- Benchmark with `test_game_tick.eigs` (headless) or
  `test_frametime.eigs` (gfx). Baseline numbers in `benchmarks/` are
  from a specific slow laptop — only compare runs on the same machine.

## Gotchas

- Don't compare benchmark numbers across machines; record the host.
- `models/` (trained weights) is generated; `saves/` and `*.log` are
  gitignored.
- macOS Intel has the JIT live since EigenScript v0.15.2; Apple Silicon
  (arm64) is interpreter-only until the ARM64 JIT exists — performance work
  won't reproduce on Apple Silicon.

## Versioning & releasing

SemVer; `VERSION` is the single source of truth. Cutting a release → the
**`release`** skill (`.claude/skills/release/`).
