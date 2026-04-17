# EigenScript requests from Tidepool

Things the game has surfaced that the language or stdlib doesn't
currently handle well. Not bugs — gaps that show up once you try to
do real-time work on constrained hardware.

## 1. High-resolution monotonic timer builtin

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

## 2. (placeholder)

Add further gaps here as they're hit.
