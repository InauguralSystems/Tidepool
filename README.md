# Tidepool

A Spore-inspired cell-stage evolution game written in
[EigenScript](https://github.com/InauguralSystems/EigenScript).

Eat, evolve, survive. Start as a single cell in the primordial pool.
Consume food, avoid predators, spend DNA on mutations, and grow through
five scale tiers.

## Requirements

EigenScript v0.17.2 or later (with SDL2 graphics):

```bash
git clone https://github.com/InauguralSystems/EigenScript.git
cd EigenScript && make install-gfx
```

## Run

```bash
eigenscript tidepool.eigs
```

Run headless tests without SDL2:

```bash
eigenscript test_game.eigs
eigenscript test_regressions.eigs
```

## Status

Game core ported from C — physics, entities, collisions, progression.
Playable with an SDL2 renderer, HUD, and keyboard input.
