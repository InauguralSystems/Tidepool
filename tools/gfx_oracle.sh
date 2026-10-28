#!/usr/bin/env bash
# Structural renderer + real-pixel acceptance oracle. Reuses screenshot.sh's
# Xvfb lifecycle; this wrapper owns only capability and verdict policy.
set -euo pipefail

EIG="${1:?gfx EigenScript binary}"

if [ ! -x "$EIG" ]; then
    echo "PREREQ MISSING: gfx build ($EIG is not executable)" >&2
    exit 2
fi
for command in Xvfb xwd python3; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "PREREQ MISSING: display tooling ($command)" >&2
        exit 2
    fi
done
if ! python3 -c 'from PIL import Image' 2>/dev/null; then
    echo "PREREQ MISSING: pixel inspector (python3-PIL)" >&2
    exit 2
fi

structural="$($EIG tools/gfx_oracle.eigs 2>&1)" || {
    printf '%s\n' "$structural" >&2
    exit 1
}
printf '%s\n' "$structural"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tools/screenshot.sh "$EIG" tools/gameplay_shot.eigs "$tmp/frame.png"
python3 tools/check_frame.py "$tmp/frame.png"
