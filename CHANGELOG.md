# Changelog

All notable changes to Tidepool are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Removed
- **The in-game "background trainer" (`src/training.eigs`), which never
  trained.** Its worker saved a demo log and reported `"done"` without any
  gradient step, so watch mode showed a "training done / policy promoted" toast
  while the policy was unchanged. Real training is the standalone `train.eigs`
  (an off-box job); watch mode (Tab) still runs the loaded policy. Also drops
  the orphaned demo-logging (nothing read `models/demo_log.txt`). Closes #12.

### Added
- **Looping background music** (`assets/music/tidepool_background.mp3`), played
  via EigenScript 0.18.0's new `audio_music_*` builtins on startup. Degrades
  gracefully (no music, no crash) on older runtimes or if the asset is missing.
  Requires EigenScript **v0.18.0+** and `libsdl2-mixer-2.0-0`. Closes GAP-007.

### Fixed
- **Sim speed no longer tracks display refresh.** The main loop paced with a
  fixed 1 ms delay while `game_tick` advances a fixed `SIM_DT` (1/60 s), so with
  vsync the game ran at the monitor's refresh rate — too fast on a high-refresh
  panel (or with vsync off). It now sleeps the remainder of each frame's
  1/60 s budget via `gfx_ticks`, so the sim runs at wall-clock 60 Hz. (A
  full fixed-timestep catch-up accumulator, for machines that can't hit 60 fps,
  remains a follow-up — it needs on-SDL testing.)
- **A stunned predator no longer bites the player.** The predator-player bite
  was gated only on recent-hit invulnerability; a predator stunned by the
  electric part still chewed through your energy while sitting on you. It now
  also checks `stunned_timer`, so the stun is actually defensive. Guarded by a
  regression test.
- **DQN loss telemetry now matches the objective it descends.** The logged
  Huber loss used the half-scale convention while the gradient used the
  un-halved one, so `train_log.csv`'s loss column read at half the true scale
  (and `--lr` looked half as effective as it was). The logged value now matches
  the gradient; training trajectories are unchanged.
- Hardened two latent scope-clobber sites (`_hit_test_btn`'s `result`,
  `draw_creature_body`'s `mx`/`my`) with `local` so a render/hit-test can never
  overwrite the module-global mouse/return state on a future refactor.

### Performance
- **DQN `train_step`: `next_obs` is stacked once, not twice.** Double-DQN
  forwards the next state through both the target and online nets; each forward
  rebuilt the `[batch × 433]` stacked buffer, so it ran twice on identical data
  (plus discarded two backprop caches). A cache-free `forward_stacked` now
  shares one stacked buffer — byte-identical output.
- **Inference: no redundant obs copy per frame.** `policy_decide` copied its
  already-buffer observation into a fresh 433-element buffer every step;
  `build_stacked_observation` already returns a buffer, so it's passed straight
  through.

- `spawn_meat` now always produces meat: when the fixed meat pool is full
  (a burst of kills faster than meat expires) it recycles the
  soonest-to-expire slot instead of silently dropping the chunk. Removes an
  ignored success/fail return that five call sites discarded.

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
