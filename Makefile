# Tidepool — build / test / run via the EigenScript toolchain.
#
# EigenScript is NOT vendored in this repo. Point EIGS_DIR at its checkout
# (defaults to the sibling repo). Every target builds and runs against the
# right binary regardless of the current directory — no manual EIG=… paths.
#
#   make build   build the headless EigenScript binary (tests/lint)
#   make gfx      build the graphical (SDL2) binary (play/screenshot)
#   make test     run the headless test suite (marker-gated, like CI)
#   make lint     parse-check every .eigs source
#   make run      play the game (needs the gfx binary + a display)
#   make shot     capture a screenshot headless (needs xvfb + python3-PIL)
#   make clean    remove generated models/, saves/, *.log

EIGS_DIR ?= ../EigenScript
EIG      := $(EIGS_DIR)/src/eigenscript

# Overridable for `make shot`. Defaults regenerate the README screenshot.
HARNESS ?= tools/gameplay_shot.eigs
OUT     ?= docs/screenshot.png

.PHONY: all build gfx test lint run shot clean help
.DEFAULT_GOAL := help

# Always (re)build the headless EigenScript binary.
build:
	$(MAKE) -C $(EIGS_DIR) build

# Always (re)build the graphical EigenScript binary.
gfx:
	$(MAKE) -C $(EIGS_DIR) gfx

# Build the binary on first use if it is missing (so test/lint work out of
# the box). Either build flavour lives at the same path and runs headless.
$(EIG):
	$(MAKE) -C $(EIGS_DIR) build

# Headless test suite — exit non-zero if any test misses its success marker.
test: | $(EIG)
	@fail=0; \
	check() { out=$$("$(EIG)" "$$1" </dev/null 2>&1); \
	  if printf '%s' "$$out" | grep -q "$$2"; then echo "  ok: $$1"; \
	  else echo "  FAIL: $$1"; printf '%s\n' "$$out" | tail -3; fail=1; fi; }; \
	check test_regressions.eigs "All regressions passed"; \
	check test_obs_stack.eigs   "All observation stacking tests passed"; \
	check test_game.eigs        "Test complete"; \
	if [ $$fail -eq 0 ]; then echo "all headless tests passed"; else exit 1; fi

# Parse-check every source.
lint: | $(EIG)
	@fail=0; \
	for f in *.eigs src/*.eigs; do \
	  if "$(EIG)" --lint "$$f" 2>&1 | grep -iqE "error"; then \
	    echo "  LINT FAIL: $$f"; "$(EIG)" --lint "$$f" 2>&1 | grep -iE "error"; fail=1; \
	  fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "lint clean"; else exit 1; fi

# Play the game (graphical; needs a display).
run: gfx
	"$(EIG)" tidepool.eigs

# Headless screenshot via Xvfb + xwd + PIL. Override HARNESS=… OUT=… .
shot: gfx
	tools/screenshot.sh "$(EIG)" "$(HARNESS)" "$(OUT)"

clean:
	rm -f *.log
	rm -rf models saves

help:
	@echo "Tidepool targets (EIGS_DIR=$(EIGS_DIR)):"
	@echo "  make build   build the headless EigenScript binary"
	@echo "  make gfx     build the graphical (SDL2) binary"
	@echo "  make test    run the headless test suite"
	@echo "  make lint    parse-check every source"
	@echo "  make run     play the game (needs gfx + a display)"
	@echo "  make shot    headless screenshot (needs xvfb + python3-PIL); HARNESS=, OUT="
	@echo "  make clean   remove generated models/, saves/, *.log"
