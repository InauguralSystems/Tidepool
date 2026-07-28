---
paths:
  - "src/renderer.eigs"
  - "src/draw.eigs"
  - "src/editor.eigs"
  - "tidepool.eigs"
  - "test_frametime.eigs"
---

# Rendering and the draw layer

- `src/renderer.eigs` draws via the **`draw_*` layer, never `gfx_*`
  directly**, so frames are headless-inspectable.
- `src/draw.eigs` is that layer. Play mode: `draw_*` calls `gfx_*` directly.
  Record mode (`draw_record_begin`): captures each draw as `{op,a}` for
  headless inspection (`draw_ops`/`draw_op_count`/`draw_count_of`) — no SDL
  needed, like DMG's `--render-probe`. Only drawing primitives are wrapped;
  `gfx_present`/`gfx_poll`/window control stay direct.
- Graphics are **explicitly deferred as polish** (priority 4 of 4). Don't
  spend effort here until AI, physics, and gameplay are solid.

## Seeing a frame without a monitor

`make shot` runs the gfx binary under Xvfb and converts the frame with
`tools/xwd2png.py` → `docs/screenshot.png`. That's how the README screenshot
is generated and how to iterate on the renderer headless. `make gfx` builds
the graphical binary (dlopens SDL2 at run time — needs `libsdl2-2.0-0`
installed, but NO `-dev` headers to build); `test_frametime.eigs` needs it too.
