# Tidepool

A Spore-inspired cell-stage evolution game written in
[EigenScript](https://github.com/InauguralSystems/EigenScript).

Eat, evolve, survive. Start as a single cell in the primordial pool.
Consume food, avoid predators, spend DNA on mutations, and grow through
five scale tiers.

## Requirements

EigenScript v0.7.1 or later:

```bash
git clone https://github.com/InauguralSystems/EigenScript.git
cd EigenScript && make install
```

## Run

```bash
eigenscript test_game.eigs
```

## Status

Game core ported from C — physics, entities, collisions, progression.
Playable with an SDL2 renderer, HUD, and keyboard input.
