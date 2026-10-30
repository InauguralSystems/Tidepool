# Tidepool#79 baseline (ML-package migration, EigenScript#1410)

This directory will hold the trained DQN policy that the move to the pure-`.eigs`
ML package (EigenScript#1410) is graded against. The baseline exists so that
"no regression" is measured, not asserted.

**Status:** the training run is in progress off-box. The checkpoint has not
been collected yet, so this directory holds only this README.

## How the checkpoint is produced

The 4 GB dev box does not run full training (Tidepool#79, comment of
2026-10-29). Training runs as a Hugging Face Space worker lane, with the source
in `tools/hf_lane/`:

| file | role |
|---|---|
| `app.py` | Gradio wrapper. It runs `job.py` in a subprocess, not a thread, and exposes the log tail as `/status`. |
| `job.py` | The lane: toolchain, preflight, train, eval, bank. |
| `lane.env` | The config. `deploy.py` sets each line as a Space variable. |
| `deploy.py` | Creates or updates the private Space and restarts it. `--status` prints the stage, the log tail and the banked files. |
| `requirements.txt`, `packages.txt`, `SPACE_README.md` | The Space build: pip deps, apt deps, and the card with frontmatter. |

### Pinned inputs

- **Runtime:** EigenScript **v0.48.0**, cloned at the tag and built with `make build`.
- **Game:** Tidepool `53410e7a84c61659a4a322847be24b71e7db2555` (main at
  launch). The lane changes nothing in the game.
- **Seed:** `42`. `train.eigs` seeds its RNG once, and every episode's world
  seed is drawn from that stream.
- **Config:** `--episodes 1000 --seed 42`. Everything else is a `train.eigs`
  default: lr 0.001, gamma 0.99, epsilon 1.0 to 0.05 on a geometric anneal
  over 60% of the episodes, batch 32, replay buffer 5000, target update every
  100 steps, 1000 ticks per episode, 40x20 world, Double-DQN with a Huber loss.
- **Hardware:** HF `cpu-basic` (2 vCPU, free). The CPU model, gcc version and
  cgroup CPU quota are recorded in `summary.json`.

### What the lane does (each phase's wall time is recorded)

1. **toolchain:** build EigenScript v0.48.0 and clone Tidepool at the pinned commit.
2. **preflight:** run the CI training smoke
   (`train.eigs --training-check --episodes 1 --seed 80 --ticks 31 --batch 8 --buffer 128`)
   twice, each in a fresh directory. Both runs must pass, and they must
   produce a byte-identical `models/policy.txt`. This shows that the build
   trains and that same-seed training is deterministic on that host.
3. **train:** `eigenscript train.eigs --episodes 1000 --seed 42`. The
   checkpoint and the curve are re-uploaded every 15 minutes under `partial/`.
4. **eval:** `eigenscript eval_policy.eigs --seeds 20 --ticks 1000`, which
   compares the trained policy against the autopilot and a random policy on a
   fixed seed list.
5. **bank:** upload the raw files first and `summary.json` last. Then the
   Space pauses itself.

To reproduce, run `python3 tools/hf_lane/deploy.py` with an HF login. To
replicate with another seed, change `SEED` **and** `TAG` in `lane.env` first.

## Where the results land

Private dataset `InauguralSystems/tidepool-baseline`, under `baseline-79/seed42-ep1000/`:

| path | content |
|---|---|
| `policy.txt` | The best-average-score checkpoint (`save_policy` format). |
| `train_state.txt` | The global episode count and the best-score bar. |
| `train_log.csv` | The loss curve, one row per 50-episode block: `ep,avg_score,avg_len,mean_tier,loss,mean_q,epsilon`. |
| `logs/` | Logs for the preflight, training and eval runs. |
| `summary.json` | The EigenScript version and commit, the Tidepool commit, the seed, the config, the platform, wall time per phase, the curve with a wall-clock time per block, the eval output and the policy sha256. |
| `partial/` | The in-flight copies from the periodic uploads. |

The training run does not finish this issue. Two steps remain:

- Copy `policy.txt`, `train_log.csv`, `train_state.txt` and `summary.json`
  into this directory. `models/` is gitignored, so they go here and not there.
- Measure #79's estimators against that checkpoint, with N=3 runs each,
  recorded as a median plus the spread:
  - frame-time Ir, using callgrind or cachegrind over a fixed tick count;
  - policy-eval output on a fixed seed, which must match exactly;
  - training-speed Ir for a fixed number of steps.

  Wall time is recorded for information only. Comment 1 on #79 measured it
  varying 32–46% between runs.
