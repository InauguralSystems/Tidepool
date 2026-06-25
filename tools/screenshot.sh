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

command -v Xvfb >/dev/null || { echo "screenshot: need Xvfb (apt install xvfb)" >&2; exit 1; }
command -v xwd  >/dev/null || { echo "screenshot: need xwd (apt install x11-apps)" >&2; exit 1; }

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'kill ${GPID:-} ${XPID:-} 2>/dev/null || true; pkill -9 -f "Xvfb $DISP" 2>/dev/null || true; rm -rf "$tmp"' EXIT

pkill -9 -f "Xvfb $DISP" 2>/dev/null || true
sleep 1
Xvfb "$DISP" -screen 0 "${W}x${H}x24" >/dev/null 2>&1 &
XPID=$!
sleep 1
DISPLAY="$DISP" "$EIG" "$HARNESS" >/dev/null 2>&1 &
GPID=$!
sleep 2
DISPLAY="$DISP" xwd -root -out "$tmp/frame.xwd" 2>/dev/null
python3 "$here/xwd2png.py" "$tmp/frame.xwd" "$OUT"
echo "screenshot: wrote $OUT"
