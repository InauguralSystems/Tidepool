# Contributing to Tidepool

Thanks for your interest. Tidepool is a Spore-style cell-stage game written
entirely in [EigenScript](https://github.com/InauguralSystems/EigenScript),
and it doubles as a real-world stress test for that language.

## Good first issues

Looking for a place to start? Issues labelled
[**good first issue**](https://github.com/InauguralSystems/Tidepool/labels/good%20first%20issue)
(also collected on the [contribute page](https://github.com/InauguralSystems/Tidepool/contribute))
are small and self-contained, each with the exact file and line, the change to
make, and acceptance criteria. Comment on one to claim it before opening a PR.

## Setup

EigenScript is not vendored here. Check it out alongside this repo and the
Makefile finds it automatically (override with `EIGS_DIR=`):

```
your-workspace/
├── EigenScript/      # the language toolchain (build with `make install-gfx`)
└── Tidepool/         # this repo
```

```bash
make build    # build the headless EigenScript binary
make test     # run the headless test suite
make lint     # parse-check every source
make run      # play the game (needs the graphical binary + a display)
```

All targets work from any directory and require EigenScript **v0.19.0+** (the
neural policy's flat buffers; CI pins the version in `.devcontainer/Dockerfile`'s
`EIGS_REF`).

## Before you open a PR

- `make lint` is clean and `make test` passes (CI enforces both).
- Add or update a test in `test_regressions.eigs` for any game-logic change —
  the renderer is headless-testable via the draw-list layer, so visual changes
  can be asserted too (see the "headless render" section there).
- Keep the prevailing style: `snake_case`, 4-space indent, `UPPER_CASE`
  constants in `src/constants.eigs`, sectioned files with header comments.
- Read [CLAUDE.md](CLAUDE.md) — it documents the architecture, the design
  priority order (AI > physics > gameplay > graphics), performance rules for
  the `game_tick` hot path, and known gotchas.

## Gameplay vs. the AI

Physics and gameplay changes alter the environment the neural policy learned
in, so they invalidate a trained model. Sequence such work as **land the change
→ retrain → evaluate**, so each step has a clean before/after. Don't bundle an
unrelated environment change into an AI PR.

## Found a language limitation?

If something can't be expressed cleanly in EigenScript, that's usually a signal
to improve the language rather than work around it. Record it in
[GAPS.md](GAPS.md); these gaps get driven upstream into EigenScript.

## Reporting bugs

Open an issue with the steps to reproduce, the seed if relevant, and whether
it's headless or graphical. For security concerns see [SECURITY.md](SECURITY.md).
