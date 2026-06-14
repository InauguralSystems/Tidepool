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

## Toolchain

EigenScript is **not** vendored in this repo. You need its interpreter
binary. To build it from source:

```bash
git clone --branch v0.14.2 https://github.com/InauguralSystems/EigenScript.git
cd EigenScript
make build      # headless binary -> src/eigenscript  (no SDL2 needed)
make gfx        # graphical binary (requires libsdl2-dev) for the playable game
```

- **Headless** (`make build`) is enough for all `test_*.eigs`,
  `train.eigs`, and `eval_policy.eigs`.
- **Graphical** (`make gfx` / `make install-gfx`) is required for
  `tidepool.eigs` itself and `test_frametime.eigs` (they call `gfx_*`).
- Minimum language version for current features is **v0.13.0** (uses
  multi-arg `spawn`, `recv_timeout`, `audio_play_loop`); v0.14.2 is the
  current tested release.

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

# Evaluate trained vs hand-coded autopilot vs random:
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
- **DQN trainer** (`train.eigs`): epsilon-greedy, target network,
  circular replay buffer, manual backprop with gradient clipping. Reward
  in `compute_reward`: +10 per food, −0.1 on energy loss, −20 on death,
  +0.01 survival.

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
- macOS Intel ships EigenScript v0.14.2 with the JIT disabled, and Apple
  Silicon is interpreter-only — performance work won't reproduce there.
- Scores are sparse: even the hand-coded autopilot eats <1 food per
  ~400-tick episode at tier 0, and deaths are rare on short episodes.
  Keep this in mind when judging whether a policy "learns" — survival
  rate alone is not discriminating on short episodes.
