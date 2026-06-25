# Security Policy

Tidepool is a single-player game that runs locally on the EigenScript
interpreter. It opens no network sockets and stores only local files
(`models/`, `saves/`). The realistic attack surface is small, but reports are
welcome.

## Reporting a vulnerability

Please report security issues privately rather than in a public issue —
e.g. via [GitHub private vulnerability reporting](https://github.com/InauguralSystems/Tidepool/security/advisories/new)
or by contacting the maintainer at the address on the
[InauguralSystems](https://github.com/InauguralSystems) profile. Include steps
to reproduce and the affected EigenScript version.

## Scope

- Issues in the EigenScript interpreter or its extensions (graphics, etc.)
  belong in the [EigenScript](https://github.com/InauguralSystems/EigenScript)
  repository, which has its own security process.
- Tidepool's own scope is the `.eigs` game/trainer code: e.g. unsafe handling
  of save files (`saves/`) or model files (`models/`) loaded from disk.

## Supported versions

The latest release on `main` is supported. Tidepool tracks a pinned EigenScript
version (currently v0.17.2); run against that or newer.
