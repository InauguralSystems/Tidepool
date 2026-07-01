## What does this PR do?

<!-- Brief description of the change -->

## Checklist

- [ ] `make lint` is clean and `make test` passes locally
- [ ] Added/updated a test in `test_regressions.eigs` for any game-logic change
- [ ] Followed the design priority order (AI > physics > gameplay > graphics) and the `game_tick` performance rules in [CLAUDE.md](../CLAUDE.md)
- [ ] CHANGELOG.md updated (if user-facing)
- [ ] For a physics/gameplay change: noted that the neural policy needs retraining (land change → retrain → eval)
