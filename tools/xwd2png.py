#!/usr/bin/env python3
"""Convert an X window dump (xwd) to PNG.

PIL and ImageMagick can't read XWD, and we don't want to pull in a heavy
dependency just to screenshot, so parse the XWD v7 header directly. Assumes a
32-bpp TrueColor visual (what `Xvfb -screen 0 WxHx24` produces).

Usage: xwd2png.py <in.xwd> <out.png>
"""
import struct
import sys

from PIL import Image


def main(src: str, dst: str) -> None:
    data = open(src, "rb").read()
    # XWDFileHeader: 25 big-endian uint32s, then the window-name string padded
    # out to header_size, then ncolors colormap entries (12 bytes each), then
    # the pixmap (height * bytes_per_line).
    h = struct.unpack(">25I", data[:100])
    header_size, _ver, _fmt, _depth, w, ht = h[0], h[1], h[2], h[3], h[4], h[5]
    byte_order = h[7]
    bytes_per_line = h[12]
    rmask, gmask, bmask = h[14], h[15], h[16]
    ncolors = h[19]

    off = header_size + ncolors * 12
    pix = data[off:off + ht * bytes_per_line]

    def shift(m: int) -> int:
        s = 0
        while m and not (m & 1):
            m >>= 1
            s += 1
        return s

    rs, gs, bs = shift(rmask), shift(gmask), shift(bmask)
    endian = ">I" if byte_order == 1 else "<I"

    img = Image.new("RGB", (w, ht))
    px = img.load()
    for y in range(ht):
        row = pix[y * bytes_per_line:(y + 1) * bytes_per_line]
        for x in range(w):
            v = struct.unpack(endian, row[x * 4:x * 4 + 4])[0]
            px[x, y] = ((v & rmask) >> rs, (v & gmask) >> gs, (v & bmask) >> bs)
    img.save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
