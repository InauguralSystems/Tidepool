---
paths:
  - "src/neural.eigs"
  - "train.eigs"
  - "eval_policy.eigs"
  - "test_obs_stack.eigs"
  - "models/**"
---

# Neural policy, DQN trainer, and evaluation

- **Neural policy** (`src/neural.eigs`): obs is 107 features (player
  state, nearest food/threat/meat, a 9×9 egocentric grid, global
  summary), stacked over 4 frames + 5 aux = **433 inputs** →
  MLP(64→32→**6 actions**). Actions: 0=none,1=thrust,2=left,3=right,
  4=brake,**5=evolve**. The 5th aux feature is the evolve-eligibility flag
  (`game.evolve_ready`), so the policy can perceive when evolving is
  available and learn to time it. Movement + the evolve decision are
  learned; **mutation-buying stays auto-piloted** (`autopilot_buy_mutation`
  is still called for the policy each step). **Weights/obs are shaped flat
  buffers** (`buffer of [r, c]`), so matmul/add/relu run on the flat `double[]`
  with no per-call nested-list flatten (requires EigenScript #275); the forward
  source is unchanged, byte-identical to the old nested-list form.
- **DQN trainer** (`train.eigs`): epsilon-greedy with an *adaptive*
  schedule (anneals start→end over ~60% of the run so the greedy policy
  is actually exploited), target network, circular replay buffer, manual
  backprop with gradient clipping. Reward in `compute_reward`: +10 per
  food, **+5 per tier advanced (evolve)**, −20 on death, +0.01 survival,
  plus **dense shaping** (±0.5 for closing/opening distance to the nearest
  food) — without the shaping the signal is too sparse to learn from. The
  death penalty for the harsher world a new tier summons is the
  counter-pressure that makes *when* to evolve a real decision. Trains on a
  denser 40×20 world (`tick_limit` 1000 so an episode can contain
  eat→evolve→harder-world cycles).
- **Checkpointing / resume (hardened for off-box runs):** `save_policy`
  writes atomically (tmp + `rename`) so a crash can never corrupt
  `models/policy.txt`, and serializes in O(n) via `join` (~0.2s vs the old
  O(n²) ~36s). The saved policy is the *best* avg-score checkpoint, not the
  final (DQN degrades late). `--resume` reloads the best weights **and**
  `models/train_state.txt` (global episode + best-score bar), continues the
  episode numbering, and **appends** to the learning curve instead of
  clobbering it — so a chained multi-run effort reads as one curve. (The
  replay buffer is not checkpointed; it refills. Pre-6-action policies are
  incompatible — retrain from scratch.)
- **Learning curve:** `models/train_log.csv` logs per 50-ep block
  `ep,avg_score,avg_len,mean_tier,loss,mean_q,epsilon`. **`mean_tier` is the
  headline signal** — tier only rises (one step per evolve), so mean tier ==
  mean evolves/episode; watch it to see whether the policy is actually
  learning to use the evolve action.
- **Eval:** `eval_policy.eigs` reports score as **mean ± 95% CI** (over
  `--seeds` seeds) for trained vs the autopilot (a strong baseline that
  evolves eagerly when eligible) vs random, on the 40×20 world, so a gap can
  be read as real or within noise. Also reports survival rate and avg tier.

## Commands (flags aren't guessable from the Makefile)

```bash
EIG=/path/to/EigenScript/src/eigenscript   # or: make build, then ../EigenScript/src/eigenscript

# Train the DQN policy (writes models/policy.txt):
$EIG train.eigs --episodes 800 --seed 42

# Continue from the saved policy (chain toward convergence — real
# convergence needs many thousands of episodes, not hundreds):
$EIG train.eigs --episodes 800 --resume --eps-start 0.4

# Evaluate trained vs hand-coded autopilot vs random (same 40x20 world the
# trainer uses, so the comparison is apples-to-apples):
$EIG eval_policy.eigs --seeds 20 --ticks 1000
```

## Gotchas

- **Judge policies on the 40×20 world, not the default game world.** Score
  density depends on world size: on the big 60×30 world even the autopilot
  eats <1 food per episode and deaths are rare, so it's a poor training/eval
  signal. On 40×20 autopilot (~3.8) clearly beats random (~1.3) and deaths
  happen — that's the signal the AI learns from.
- DQN training is noisy and slow on interpreted EigenScript (~3 s/episode on
  this host). 800 episodes is a proof-of-life snapshot, not convergence;
  expect to chain `--resume` runs across many thousands.
- **Ephemeral container**: anything not committed (including trained
  `models/policy.txt`) is lost when it's reclaimed. To persist a long
  training effort, commit milestone policies with `git add -f`.
- When physics/gameplay change, the policy must be retrained — those edits
  alter the environment it learned in.
