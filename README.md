# Tidepool

A Spore-inspired cell-stage evolution game written in
[EigenScript](https://github.com/InauguralSystems/EigenScript).

Eat, evolve, survive. Start as a single cell in the primordial pool.
Consume food, avoid predators, spend DNA on mutations, and grow through
five scale tiers.

![Tidepool gameplay](docs/screenshot.png)

## Requirements

EigenScript v0.17.2 or later (with SDL2 graphics):

```bash
git clone https://github.com/InauguralSystems/EigenScript.git
cd EigenScript && make install-gfx
```

## Run

With EigenScript checked out alongside this repo (`../EigenScript`), the
Makefile handles building the right binary:

```bash
make run     # build the graphical binary and play
make test    # build the headless binary and run the test suite
make lint    # parse-check every source
```

Point `EIGS_DIR=` at EigenScript if it's elsewhere. Or run directly:

```bash
/path/to/EigenScript/src/eigenscript tidepool.eigs
```

## Status

Game core ported from C — physics, entities, collisions, progression.
Playable with an SDL2 renderer, HUD, and keyboard input.
