# Self-contained dev/CI image for Tidepool (a graphical EigenScript game).
#
# Unlike the pure-language consumers, Tidepool builds EigenScript's *gfx*
# variant from a source checkout (its Makefile drives `make -C $EIGS_DIR ...`).
# So this image carries a full EigenScript source tree at a pinned tag, builds
# the gfx binary (a strict superset of headless — runs the headless suite fine),
# and ships SDL2 + Xvfb so a Codespace can actually render and screenshot the
# game. CI uses the same image for the headless suite; the tag IS the version
# pin (bump EIGS_REF to move the runtime).
FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        libsdl2-2.0-0 \
        xvfb \
        python3 \
        python3-pil \
 && rm -rf /var/lib/apt/lists/*

# Full EigenScript source at a pinned ref; build the gfx variant. SDL2 is
# dlopen'd at runtime, so building gfx needs no -dev headers — only libsdl2 to
# *run* it. eigenscript resolves its stdlib relative to the binary (../lib).
# EIGS_REF is a tag/SHA (fetched directly, so it stays reproducible). Pinned to
# v0.19.0 — the release that ships the flat-buffer tensors (shaped VAL_BUFFER,
# #275) the neural policy's buffer path requires.
ARG EIGS_REF=v0.36.0
RUN mkdir -p /opt/eigenscript && cd /opt/eigenscript && git init -q \
 && git remote add origin https://github.com/InauguralSystems/EigenScript.git \
 && git fetch -q --depth 1 origin "${EIGS_REF}" && git checkout -q FETCH_HEAD \
 && make -C /opt/eigenscript gfx CC=gcc

ENV EIGS_DIR=/opt/eigenscript
ENV PATH="/opt/eigenscript/src:${PATH}"
WORKDIR /workspaces/Tidepool
