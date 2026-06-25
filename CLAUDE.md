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
electric/jet appendages), call a mate to evolve, grow through scale tiers,
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

EigenScript is **not** vendored in this repo. You need its interpreter
binary. To build it from source:

```bash
git clone --branch v0.17.2 https://github.com/InauguralSystems/EigenScript.git
cd EigenScript
make build      # headless binary -> src/eigenscript  (no SDL2 needed)
make gfx        # graphical binary (requires libsdl2-dev) for the playable game
```

- **Headless** (`make build`) is enough for all `test_*.eigs`,
  `train.eigs`, and `eval_policy.eigs`.
- **Graphical** (`make gfx` / `make install-gfx`) is required for
  `tidepool.eigs` itself and `test_frametime.eigs` (they call `gfx_*`).
- Minimum language version for current features is **v0.13.0** (uses
  multi-arg `spawn`, `recv_timeout`, `audio_play_loop`); **v0.17.2 is the
  current tested release** (validated headless: regressions, obs-stacking,
  game_tick, and the train pipeline all pass; `game_tick` ~86 ms vs ~100 ms
  on 0.16.3).

Run a script:

```bash
/path/to/EigenScript/src/eigenscript test_game.eigs
```

## Run / test / train / evaluate

```bash
EIG=/path/to/EigenScript/src/eigenscript

# Headless tests (fast, no SDL2):
$EIG test_game.eigs          # 300-tick smoke sim
$EIG test_regressions.eigs   # tier progression, torus wrap, collision, meat pool
$EIG test_game_tick.eigs     # game_tick microbenchmark (n=5)
$EIG test_obs_stack.eigs     # neural observation-stacking unit tests

# Train the DQN policy (writes models/policy.txt):
$EIG train.eigs --episodes 800 --seed 42

# Continue training from the saved policy (chain toward convergence —
# real convergence needs many thousands of episodes, not hundreds):
$EIG train.eigs --episodes 800 --resume --eps-start 0.4

# Evaluate trained vs hand-coded autopilot vs random (same world the
# trainer uses, 40x20, so the comparison is apples-to-apples):
$EIG eval_policy.eigs --seeds 20 --ticks 600

# Play (needs gfx binary + SDL2):
$EIG tidepool.eigs
```

Always run `test_regressions.eigs` before committing game-logic changes.

## Layout

| Path | Role |
|---|---|
| `tidepool.eigs` | Game entry point: menus, HUD, input, main loop (gfx) |
| `train.eigs` | Standalone DQN trainer (replay buffer, target net, backprop) |
| `eval_policy.eigs` | Policy evaluation harness (trained/autopilot/random) |
| `src/game.eigs` | Core: physics, entities, collisions, combat, progression, autopilot, save/load. Largest file. |
| `src/constants.eigs` | All tunable constants (world, physics, combat, action enums) |
| `src/math_utils.eigs` | Torus distance/delta, angle helpers (hot path — inlined elsewhere) |
| `src/entities.eigs` | Entity + creature-spec constructors, palettes, derived stats |
| `src/neural.eigs` | MLP policy: forward pass, observation builder, frame stacking, save/load |
| `src/training.eigs` | In-game background-thread training UI glue |
| `src/renderer.eigs` | SDL2 renderer: creatures, particles, caustics, HUD, camera |
| `src/editor.eigs` | In-game creature editor UI |
| `src/audio.eigs` | Procedural audio synthesis |
| `docs/`, `benchmarks/`, `GAPS.md` | Language requests, perf baselines, documented language gaps |

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
- **Neural policy** (`src/neural.eigs`): obs is 107 features (player
  state, nearest food/threat/meat, a 9×9 egocentric grid, global
  summary), stacked over 4 frames + 4 aux = **432 inputs** →
  MLP(64→32→5 actions). Actions: 0=none,1=thrust,2=left,3=right,4=brake.
- **DQN trainer** (`train.eigs`): epsilon-greedy with an *adaptive*
  schedule (anneals start→end over ~60% of the run so the greedy policy
  is actually exploited), target network, circular replay buffer, manual
  backprop with gradient clipping. Reward in `compute_reward`: +10 per
  food, −20 on death, +0.01 survival, plus **dense shaping** (±0.5 for
  closing/opening distance to the nearest food) — without the shaping the
  signal is too sparse to learn from. Trains on a denser 40×20 world.
  `--resume` continues from `models/policy.txt`. Evaluate with
  `eval_policy.eigs` against the autopilot (a strong baseline) and random.
- **Combat is survivable** (`game_tick` predator-collision branch): a
  collision you lose deals an energy bite (scaled by the power gap, capped
  at 60) plus knockback and ~0.75s invulnerability (`invuln_timer`), not
  an instant kill. You die only when energy hits 0. Epic-cell collisions
  are still meant to be lethal hazards.

## EigenScript conventions (quick reference)

- Define: `define f(a, b) as:` — body is indented.
- Call: single arg `f of x`; multiple args `f of [a, b, c]`;
  zero args `f of null` (e.g. `new_policy of null`).
- Assign: `x is expr`. Dict access: `d.key` or `d["key"]`.
- Lists: `append of [list, val]`, `len of list`, `range of n`.
- Control: `if/elif/else:`, `loop while cond:`, `for x in range of n:`,
  `match expr:` / `case val:`, `continue`, `break`.
- f-strings: `f"text {expr}"`.
- v0.13.0+ niceties available: destructuring `[a, b] is rhs`, slicing
  `a[start:end]`, negative indexing `a[-1]`, default params.

## Physics & gameplay roadmap (known gaps)

Concrete, code-grounded opportunities, roughly ranked by impact-per-effort.
These are the substance behind the "physics" and "gameplay" priorities.

1. **Two progression systems conflict** — tiers auto-advance every 10 food
   eaten (`game_tick`, the scale-tier block), *and* there's the full
   Spore-style mate gate (`call_mate` → `update_mate` → `evolve_tier_up`,
   which costs DNA and does the rich work: respawns species, spawns epic
   cells). The free food-based auto-tier short-circuits the mate ritual, so
   the interesting evolve path rarely fires. Pick one canonical gate
   (the mate path is the faithful, richer one).
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
- Score density depends on world size: on the big 60×30 world even the
  autopilot eats <1 food per episode and deaths are rare, so it's a poor
  training/eval signal. The trainer and `eval_policy.eigs` use a denser
  40×20 world where autopilot (~3.8) clearly beats random (~1.3) and
  deaths happen — that's the signal the AI learns from. Judge policies on
  that world, not the default game world.
- DQN training is noisy and slow on interpreted EigenScript (~3 s/episode
  on this host). 800 episodes is a proof-of-life snapshot, not
  convergence; expect to chain `--resume` runs across many thousands.
- This is an **ephemeral container**: anything not committed (including
  trained `models/policy.txt`) is lost when it's reclaimed. To persist a
  long training effort, commit milestone policies with `git add -f`.
