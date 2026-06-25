# Changelog

All notable changes to Tidepool are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-06-25

First tagged release: a complete, playable Spore-style cell-stage game with a
learnable neural policy, written entirely in EigenScript. The AI training
pipeline is in place; training a policy to convergence is ongoing.

### Game
- Cell-stage loop: diet choice, eat food/meat, spend DNA on speed/sense/spikes
  mutations and on unlockable parts (mouths, fins, claws, poison/electric/jet),
  call a mate, grow through five scale tiers, dodge epic cells.
- **Deliberate evolution**: eating `FOOD_PER_TIER` food unlocks the next tier,
  but evolving is an explicit action (`ACTION_EVOLVE`); each tier scales up the
  predator count and strength, making *when* to evolve a real decision.
- Survivable, zone-aware combat (energy bites + knockback + i-frames, not
  instant kills); torus world; rotating water current.
- Creature editor with a part-drop → unlock → equip progression loop.

### AI
- 433-feature observation (player state, nearest food/threat/meat, a 9×9
  egocentric grid, global summary; 4-frame stack + 5 aux including evolve
  eligibility) → MLP(64→32→6 actions; movement + evolve).
- From-scratch DQN trainer (`train.eigs`): epsilon-greedy with an adaptive
  schedule, target network, circular replay buffer, manual backprop with
  gradient clipping, dense reward shaping, and a +tier-up evolve reward.
- Crash-safe, resumable checkpointing; per-block learning-curve CSV with
  `mean_tier` telemetry; `eval_policy.eigs` reports score as mean ±95% CI vs a
  hand-coded autopilot and random.
- In-game watch mode (Tab) runs the loaded policy.

### Graphics
- Bioluminescent renderer: translucent lit-from-within cells, a depth-graded
  pool, shimmering caustics, drifting plankton, glowing food, a styled HUD.
- A draw-list layer (`src/draw.eigs`) makes the renderer headless-inspectable,
  so frames are testable and screenshottable without a display.

### Tooling
- Makefile (`make build/gfx/test/lint/run/shot`) so the toolchain isn't manual.
- Headless CI (GitHub Actions) that builds the pinned EigenScript and runs the
  test suite on push/PR.
- Headless screenshot pipeline (`make shot`).

### Requires
- EigenScript v0.17.2 or later.
