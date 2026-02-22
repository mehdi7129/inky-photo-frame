---
phase: 03-module-extraction
plan: 02
subsystem: infra
tags: [python-package, module-extraction, refactoring, dependency-injection, singleton]

# Dependency graph
requires:
  - phase: 03-module-extraction
    plan: 01
    provides: "config.py foundation with all constants, DISPLAY_CONFIGS, setup_logging()"
provides:
  - "display.py with DisplayManager singleton and retry_on_error decorator"
  - "image_processor.py with process_image(), _apply_spectra_palette(), _apply_warmth_boost()"
  - "photos.py with PhotoHandler, get_all_photos(), load_history()"
  - "buttons.py with BUTTONS_AVAILABLE flag and ButtonController"
  - "welcome.py with display_welcome(), get_ip_address(), get_credentials()"
affects: [03-module-extraction, 04-migration-validation, 06-test-suite]

# Tech tracking
tech-stack:
  added: []
  patterns: ["constructor injection for ButtonController and PhotoHandler", "explicit parameters replacing self.* access in module-level functions", "lazy hardware import inside DisplayManager.initialize()"]

key-files:
  created:
    - inky_photo_frame/display.py
    - inky_photo_frame/image_processor.py
    - inky_photo_frame/photos.py
    - inky_photo_frame/buttons.py
    - inky_photo_frame/welcome.py
  modified: []

key-decisions:
  - "process_image() takes explicit width/height/color_mode/is_spectra params instead of self.*"
  - "display_welcome() takes explicit display/width/height params instead of self.*"
  - "ButtonController and PhotoHandler use constructor injection, no import of app.py"
  - "ImageEnhance stays as local import inside color functions (matching monolith pattern)"

patterns-established:
  - "Constructor injection: ButtonController(photo_frame), PhotoHandler(slideshow) receive app instance without importing app module"
  - "Explicit parameters: Module-level functions take display dimensions and config as arguments, not from self"
  - "Lazy hardware import: from inky.auto import auto only inside DisplayManager.initialize(), never at module level"
  - "Guarded optional import: gpiozero import wrapped in try/except with BUTTONS_AVAILABLE flag"

requirements-completed: [STRC-01]

# Metrics
duration: 3min
completed: 2026-02-22
---

# Phase 03 Plan 02: Leaf Module Extraction Summary

**Five leaf modules extracted from monolith with constructor injection, explicit parameters, and zero circular dependencies**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-22T11:39:25Z
- **Completed:** 2026-02-22T11:42:05Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extracted DisplayManager singleton and retry_on_error decorator into display.py with lazy hardware import preserved
- Extracted image processing pipeline into image_processor.py as three module-level functions with explicit parameters replacing self.* access
- Extracted PhotoHandler, get_all_photos(), and load_history() into photos.py with config.py constants
- Extracted ButtonController into buttons.py with guarded gpiozero import and constructor injection
- Extracted welcome screen rendering into welcome.py with explicit display/width/height parameters
- Verified all 5 modules import cleanly without hardware dependencies and with no circular imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract display.py and image_processor.py** - `493e461` (feat)
2. **Task 2: Extract photos.py, buttons.py, and welcome.py** - `be0250b` (feat)

## Files Created/Modified
- `inky_photo_frame/display.py` - DisplayManager singleton with lazy inky.auto import, retry_on_error decorator
- `inky_photo_frame/image_processor.py` - process_image(), _apply_spectra_palette(), _apply_warmth_boost() as module-level functions
- `inky_photo_frame/photos.py` - PhotoHandler (watchdog FileSystemEventHandler), get_all_photos(), load_history()
- `inky_photo_frame/buttons.py` - BUTTONS_AVAILABLE flag, ButtonController with constructor injection
- `inky_photo_frame/welcome.py` - display_welcome(), get_ip_address(), get_credentials() as module-level functions

## Decisions Made
- process_image() takes explicit width, height, color_mode, is_spectra parameters instead of reading from self -- enables calling from app.py without tight coupling
- display_welcome() takes explicit display, width, height parameters for the same reason
- ButtonController and PhotoHandler use constructor injection (receive app instance via __init__), never import from app.py -- prevents circular imports
- ImageEnhance stays as a local import inside _apply_spectra_palette() and _apply_warmth_boost(), matching the monolith pattern for lazy loading
- ImageOps omitted from image_processor.py imports since it was not used in the extracted functions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing watchdog dependency**
- **Found during:** Task 2 (photos.py verification)
- **Issue:** watchdog package not installed on dev machine, causing ImportError when verifying photos.py
- **Fix:** Installed watchdog via pip3 (already listed in project requirements.txt, just not on dev machine)
- **Files modified:** None (system package only)
- **Verification:** `from inky_photo_frame.photos import PhotoHandler` succeeds after install
- **Committed in:** N/A (no code change, dev environment setup)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal -- dev environment missing a dependency that is already in requirements.txt. No scope creep.

## Issues Encountered
None beyond the watchdog installation noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 leaf modules extracted and importable without hardware
- Monolith `inky_photo_frame.py` remains unmodified and still runs as-is
- Ready for 03-03: app.py orchestrator extraction (depends on all leaf modules being available)
- Import direction is strictly one-way: leaf modules depend only on config.py, never on app.py or each other

## Self-Check: PASSED

- FOUND: inky_photo_frame/display.py
- FOUND: inky_photo_frame/image_processor.py
- FOUND: inky_photo_frame/photos.py
- FOUND: inky_photo_frame/buttons.py
- FOUND: inky_photo_frame/welcome.py
- FOUND: 03-02-SUMMARY.md
- FOUND: commit 493e461 (Task 1)
- FOUND: commit be0250b (Task 2)

---
*Phase: 03-module-extraction*
*Completed: 2026-02-22*
