#!/usr/bin/env python3
"""Reject a blank/near-blank real gfx capture with named diagnostics."""

import sys
from collections import Counter

from PIL import Image


def main(path: str) -> int:
    # tobytes() exists in every Pillow; get_flattened_data() is only in recent
    # releases and failed in the devcontainer's older Pillow (Tidepool#76 CI).
    raw = Image.open(path).convert("RGB").tobytes()
    pixels = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    colours = Counter(pixels)
    dominant, dominant_count = colours.most_common(1)[0]
    ink = len(pixels) - dominant_count

    # Deliberately broad runner-robust features, not a cross-platform golden:
    # a correct 800x600 frame has hundreds of colours and extensive non-ocean
    # ink. These floors still catch a window that opened but drew nothing.
    if len(colours) < 32:
        print(f"GFX ORACLE MISMATCH: pixel frame has only {len(colours)} colours", file=sys.stderr)
        return 1
    if ink < 10_000:
        print(f"GFX ORACLE MISMATCH: pixel frame has only {ink} non-background pixels", file=sys.stderr)
        return 1
    print(
        f"GFX ORACLE PASS: pixel frame colours={len(colours)} "
        f"non-background={ink} dominant={dominant}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
