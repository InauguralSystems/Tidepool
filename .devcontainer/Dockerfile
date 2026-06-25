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

# Full EigenScript source at the pinned tag; build the gfx variant. SDL2 is
# dlopen'd at runtime, so building gfx needs no -dev headers — only libsdl2 to
# *run* it. eigenscript resolves its stdlib relative to the binary (../lib).
ARG EIGS_REF=v0.18.0
RUN git clone --depth 1 --branch "${EIGS_REF}" \
        https://github.com/InauguralSystems/EigenScript.git /opt/eigenscript \
 && make -C /opt/eigenscript gfx CC=gcc

ENV EIGS_DIR=/opt/eigenscript
ENV PATH="/opt/eigenscript/src:${PATH}"
WORKDIR /workspaces/Tidepool
