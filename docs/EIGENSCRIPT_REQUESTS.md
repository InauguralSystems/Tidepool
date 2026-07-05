# EigenScript requests from Tidepool

Things the game has surfaced that the language or stdlib doesn't
currently handle well. Not bugs — gaps that show up once you try to
do real-time work on constrained hardware.

## 1. High-resolution monotonic timer builtin ✅ RESOLVED

**Resolved**: `monotonic_ns of null` ships in EigenScript and is used by
`test_game_tick.eigs`. (`test_frametime.eigs` still uses the old `date`
shell-out below and could be migrated to it.)

**Want**: `monotonic_ns of null` → integer nanoseconds from a
monotonic source. Optionally `monotonic_ms`, `monotonic_us`.

**Why**: per-frame performance instrumentation needs sub-millisecond
precision. At 60fps a frame budget is 16.67 ms, and tick/render/idle
are each on the order of 1–5 ms.

**Current state**: `timer_start` / `timer_elapsed` are documented as
second-granularity in the stdlib, which is coarser than a single
frame. `test_frametime.eigs` currently works around this with:

```eigs
define now as:
    r is exec_capture of ["date", "+%s%N"]
    return num of (trim of r[1])
```

That shells out to `/bin/date` and parses its stdout once per
measurement. On a 2007 Pentium the fork+exec alone dominates the
thing being measured, so the benchmark reports noise.

**Blocks**: a per-frame perf overlay (tick-ms, render-ms, idle-ms) —
exactly the kind of HUD that catches regressions at the moment they
happen on slow hardware, rather than three commits later when the
game visibly stutters.

**Implementation sketch**: `clock_gettime(CLOCK_MONOTONIC, ...)` on
Linux, `mach_absolute_time` on macOS, `QueryPerformanceCounter` on
Windows. Return i64 nanoseconds. No allocation per call.

## 2. Stdlib module resolution for external projects ✅ RESOLVED

**Resolved**: `load_file` now also resolves exe-dir-relative and system paths —
it tries `<exe_dir>/../<path>`, `<exe_dir>/../lib/eigenscript/<path>`, and
`~/.local/lib/eigenscript/<path>`, so a script run from any directory finds the
stdlib alongside the binary (shipped from the "possible fixes" below). Empirically
`load_file of "lib/test.eigs"` resolves when running a script from Tidepool, so
`test_regressions.eigs` could now use `lib/test.eigs` instead of the bare `assert`.

**Want**: `load_file of "lib/test.eigs"` (or `import test`) should find
EigenScript's stdlib modules regardless of the caller's working directory.

**Why**: `test_regressions.eigs` in Tidepool uses the bare `assert` builtin
instead of `lib/test.eigs` because the load path only searches relative to
the script file and CWD — neither of which is the EigenScript install
directory when running a game.

**Current state**: `load_file` resolution order is:
1. Relative to CWD
2. Relative to the script file's directory
3. Relative to the script file's parent directory

None of these find `~/EigenScript/lib/` when running `~/Tidepool/test.eigs`.

**Impact**: any project outside the EigenScript tree can't use the stdlib
test framework, format utilities, or any library module without copying
files or symlinking.

**Possible fixes**:
- `EIGENSCRIPT_LIB` env var pointing to the stdlib directory
- Bake the install prefix into the binary at compile time
- `import` searches a known system path (e.g. `~/.local/lib/eigenscript/`)
- Ship stdlib modules alongside the binary on `make install`

## 3. (placeholder)

Add further gaps here as they're hit.
