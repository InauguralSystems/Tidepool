#!/usr/bin/env bash
# Capture a Tidepool frame headless — no display required.
#
# Runs the graphical EigenScript binary under a virtual X server (Xvfb),
# dumps the root window with xwd, and converts it to PNG. Used to generate
# the README screenshot and to iterate on the renderer without a monitor.
#
# Usage: tools/screenshot.sh <eigenscript-gfx-binary> <harness.eigs> <out.png>
#   env: W, H  window size (default 800x600)
#
# Deps: Xvfb (apt install xvfb), xwd (apt install x11-apps), python3 + PIL.
set -euo pipefail

EIG="${1:?eigenscript binary}"
HARNESS="${2:?harness .eigs}"
OUT="${3:?output .png}"
W="${W:-800}"
H="${H:-600}"
DISP=":99"

command -v Xvfb >/dev/null || { echo "PREREQ MISSING: display tooling (Xvfb)" >&2; exit 2; }
command -v xwd  >/dev/null || { echo "PREREQ MISSING: display tooling (xwd)" >&2; exit 2; }

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'kill ${GPID:-} ${XPID:-} 2>/dev/null || true; pkill -9 -f "Xvfb $DISP" 2>/dev/null || true; rm -rf "$tmp"' EXIT

pkill -9 -f "Xvfb $DISP" 2>/dev/null || true
sleep 1
Xvfb "$DISP" -screen 0 "${W}x${H}x24" >/dev/null 2>&1 &
XPID=$!
sleep 1
DISPLAY="$DISP" "$EIG" "$HARNESS" >"$tmp/game.log" 2>&1 &
GPID=$!
sleep 2
if ! kill -0 "$GPID" 2>/dev/null; then
    wait "$GPID" || rc=$?
    if grep -qE "unavailable in this build|undefined variable 'gfx_" "$tmp/game.log"; then
        echo "PREREQ MISSING: gfx build (gfx builtins unavailable)" >&2
        exit 2
    fi
    echo "GFX INFRASTRUCTURE FAILURE: renderer exited before capture (status ${rc:-0})" >&2
    cat "$tmp/game.log" >&2
    exit 1
fi
DISPLAY="$DISP" xwd -root -out "$tmp/frame.xwd" 2>/dev/null
python3 "$here/xwd2png.py" "$tmp/frame.xwd" "$OUT"
echo "screenshot: wrote $OUT"
