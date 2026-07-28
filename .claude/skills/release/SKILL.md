---
name: release
description: Cut a Tidepool release — the VERSION/CHANGELOG steps, the workflow_dispatch path this environment requires (the git proxy can't push tags), and how to verify a published archive's checksums and Sigstore attestation. Use when tagging a version or publishing a release.
disable-model-invocation: true
---

# Releasing Tidepool

Tidepool follows [SemVer](https://semver.org/); `VERSION` is the single source
of truth (the game reports it via `eigenscript tidepool.eigs --version`, and the
release workflow refuses to release a tag that disagrees with it).

To cut a release:

1. Move the `## [Unreleased]` block in `CHANGELOG.md` to `## [x.y.z] — YYYY-MM-DD`
   (leave a fresh empty `[Unreleased]` above it).
2. Bump `VERSION` to `x.y.z`.
3. Commit (`release: vx.y.z`) and merge to `main`.
4. **Actions ▸ Release ▸ Run workflow** (the `workflow_dispatch` path). It tags
   `vx.y.z` from `VERSION`, builds a deterministic source archive
   (`tidepool-vx.y.z.tar.gz` via `git archive`), writes `CHECKSUMS`, attaches a
   Sigstore build-provenance attestation, and publishes a GitHub release whose
   notes are the matching `CHANGELOG` section.

Use the dispatch path rather than pushing a tag by hand: this environment's git
proxy can't push tags, and a `GITHUB_TOKEN`-pushed tag wouldn't retrigger the
workflow (same gotcha as EigenScript). Pushing a `v*` tag through a normal
remote also works and triggers the same build. Verify a downloaded archive with
`sha256sum -c CHECKSUMS` and
`gh attestation verify tidepool-vx.y.z.tar.gz --repo InauguralSystems/Tidepool`.
