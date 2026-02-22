# Phase 3: Module Extraction - Research

**Researched:** 2026-02-22
**Domain:** Python monolith-to-package refactoring with backward-compatible entry point
**Confidence:** HIGH

## Summary

Phase 3 splits the 1,216-line `inky_photo_frame.py` monolith into a Python package (`inky_photo_frame/`) with 9 modules while preserving the existing systemd `ExecStart` path unchanged. The core technical challenge is a **name collision**: when both `inky_photo_frame.py` and `inky_photo_frame/` (with `__init__.py`) exist in the same directory, Python's import system gives precedence to the **package directory** over the `.py` file. This means the shim file `inky_photo_frame.py` can safely `from inky_photo_frame.app import main; main()` -- it will import from the package, not from itself, because direct script execution (`python inky_photo_frame.py`) does not go through the import system for the script itself.

The module dependency graph must be strictly one-directional: `config.py` depends on nothing; `display.py` depends on `config`; `image_processor.py` depends on `config`; `photos.py` depends on `config`; `buttons.py` depends on nothing from the package (receives the app instance via constructor injection); `welcome.py` depends on `config`; `app.py` depends on all other modules. Circular imports are the highest-risk failure mode and are preventable by maintaining constructor-injection patterns already present in the codebase (`ButtonController(photo_frame)`, `PhotoHandler(slideshow)`).

**Primary recommendation:** Extract modules bottom-up starting with `config.py` (zero dependencies), then leaf modules (`display.py`, `image_processor.py`, `photos.py`, `buttons.py`, `welcome.py`), then the orchestrator (`app.py`). The shim and `__main__.py` are written last. Move `logging.basicConfig()` out of module-level scope into a `setup_logging()` function called only from entry points.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STRC-01 | `inky_photo_frame.py` split into package with modules: config, display, image_processor, photos, buttons, welcome, app | Module dependency graph and extraction order documented below; line ranges for each module identified in codebase analysis |
| STRC-02 | `inky_photo_frame.py` retained as backward-compatible 3-line shim launcher | Name collision analysis confirms package takes import precedence; shim pattern documented with exact code |
| STRC-04 | systemd service continues working transparently after modularization (no ExecStart path change) | ExecStart path is `python /home/pi/inky-photo-frame/inky_photo_frame.py` -- shim preserves this exact invocation; WorkingDirectory is `$INSTALL_DIR` which means Python resolves the package from the same directory |
</phase_requirements>

## Standard Stack

### Core

No new libraries are introduced. This phase is a pure refactoring of existing code.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11 | Target runtime (Raspberry Pi OS Bookworm) | Single target platform |
| Pillow (PIL) | >=10.0.0 | Image processing pipeline | Already in use |
| watchdog | >=3.0.0 | File system event monitoring | Already in use |
| gpiozero | >=2.0.0 | GPIO button handling | Already in use (optional import) |

### Supporting

No new supporting libraries needed.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 3-line shim at repo root | `python -m inky_photo_frame` invocation in systemd | Would require editing every user's systemd service file -- unacceptable per STRC-04 |
| Package `__init__.py` re-exporting all names | Minimal `__init__.py` with version only | Re-exporting everything defeats the purpose of modularization; import specific modules instead |
| Moving `InkyPhotoFrame` to `__init__.py` | Dedicated `app.py` module | `__init__.py` should be thin; app logic belongs in its own module |

**Installation:**
No new packages needed. Existing `requirements.txt` unchanged.

## Architecture Patterns

### Recommended Package Structure

```
inky_photo_frame/           # New package directory
  __init__.py               # Package marker + VERSION export
  __main__.py               # python -m inky_photo_frame support
  config.py                 # Constants, paths, DISPLAY_CONFIGS, color palettes
  display.py                # DisplayManager singleton + retry_on_error decorator
  image_processor.py        # process_image(), _apply_spectra_palette(), _apply_warmth_boost()
  photos.py                 # PhotoHandler (watchdog), get_all_photos(), history/cleanup logic
  buttons.py                # ButtonController (GPIO)
  welcome.py                # display_welcome() screen rendering
  app.py                    # InkyPhotoFrame orchestrator class + run() main loop

inky_photo_frame.py         # 3-line backward-compatible shim (repo root)
```

### Pattern 1: Name Collision Resolution (Shim + Package Coexistence)

**What:** When both `inky_photo_frame.py` and `inky_photo_frame/` exist in the same directory, Python's import system gives the package directory precedence for `import inky_photo_frame`. But `python inky_photo_frame.py` executes the file directly (no import resolution for the script itself).

**When to use:** Always -- this is the foundation of the backward-compatible shim strategy.

**Example -- the 3-line shim (`inky_photo_frame.py` at repo root):**
```python
#!/usr/bin/env python3
from inky_photo_frame.app import InkyPhotoFrame
InkyPhotoFrame().run()
```

When systemd runs `python /home/pi/inky-photo-frame/inky_photo_frame.py`, Python executes this file directly. The `from inky_photo_frame.app import InkyPhotoFrame` statement triggers the import system, which finds the `inky_photo_frame/` package directory (which takes precedence). The shim never imports itself.

**Confidence:** HIGH -- verified via Python official import documentation and multiple authoritative sources confirming package directory precedence over same-named `.py` files.

### Pattern 2: Bottom-Up Extraction with Dependency Injection

**What:** Extract modules starting from those with zero intra-package dependencies (config), then leaf modules, then the orchestrator. Maintain the existing constructor-injection pattern to avoid circular imports.

**When to use:** For every module extraction step.

**Dependency graph (arrows mean "depends on"):**
```
config.py        <-- depends on: nothing (stdlib only)
display.py       <-- depends on: config (VERSION, imports inky.auto lazily)
image_processor.py <-- depends on: config (SPECTRA_PALETTE, WARMTH_BOOST_CONFIG)
photos.py        <-- depends on: config (PHOTOS_DIR, HISTORY_FILE, MAX_PHOTOS)
buttons.py       <-- depends on: nothing from package (receives app via constructor)
welcome.py       <-- depends on: config (paths, credentials)
app.py           <-- depends on: config, display, image_processor, photos, buttons, welcome
__main__.py      <-- depends on: app
```

**Key rule:** `buttons.py` and `photos.py` (PhotoHandler) receive the `InkyPhotoFrame` instance via constructor injection, never via module-level import of `app.py`. This prevents circular imports.

### Pattern 3: Side-Effect-Free Module Imports

**What:** No module in the package should produce side effects on import. All initialization happens in explicit function calls from the entry point.

**When to use:** During extraction of every module.

**Current side effects that must be relocated:**
1. `logging.basicConfig(...)` (lines 153-160) -- move to `setup_logging()` function in `config.py`, called from entry points only
2. `os.environ['INKY_SKIP_GPIO_CHECK'] = '1'` (line 32) -- keep at top of `config.py` (required before any `inky` import), but document explicitly
3. `from gpiozero import Button` + `BUTTONS_AVAILABLE` flag (lines 52-56) -- keep in `buttons.py` as a guarded import, not at package level

### Pattern 4: Minimal `__init__.py`

**What:** The package `__init__.py` should expose only the version string and optionally a convenience import. It must NOT import hardware drivers.

**Example:**
```python
"""Inky Photo Frame - Universal E-Ink Photo Frame for Inky Impression"""

from inky_photo_frame.config import VERSION

__version__ = VERSION
```

**Verification criterion:** `python -c "from inky_photo_frame import config"` must succeed without importing `inky`, `gpiozero`, or any hardware driver. This is success criterion 4 in the phase definition.

### Pattern 5: `__main__.py` for `python -m` support

**What:** A minimal `__main__.py` enables running the package as a module: `python -m inky_photo_frame`.

**Example:**
```python
from inky_photo_frame.app import InkyPhotoFrame

InkyPhotoFrame().run()
```

Per Python official documentation, `__main__.py` should be short and not contain an `if __name__ == '__main__'` guard.

### Anti-Patterns to Avoid

- **Circular imports between modules:** Never `from inky_photo_frame.app import InkyPhotoFrame` inside `buttons.py` or `photos.py`. Use constructor injection instead.
- **Re-exporting everything from `__init__.py`:** Do NOT write `from inky_photo_frame.config import *` in `__init__.py`. This defeats modularization and causes import side effects.
- **Module-level `logging.basicConfig()`:** This overwrites any previously configured logging (including test runner logging). Must be in a callable function.
- **Importing hardware drivers at package level:** `from inky.auto import auto` must only happen inside `DisplayManager.initialize()`, never at module scope.
- **Moving `os.environ['INKY_SKIP_GPIO_CHECK']` into display.py only:** This env var must be set BEFORE any `import inky` anywhere. It belongs at the top of `config.py` which is imported first by all modules that might transitively trigger an inky import.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Module dependency resolution | Custom import ordering or lazy-import framework | Python's standard import system with explicit imports | The dependency graph is simple (7 modules); no framework needed |
| Backward-compatible entry point | Complex `sys.path` manipulation or importlib hacks | Simple 3-line shim file that imports and calls the package | The name collision behavior is well-defined and reliable |
| Singleton management across modules | Custom registry or service locator | Keep existing `DisplayManager` singleton pattern as-is | It already works; refactoring it is out of scope for this phase |

**Key insight:** This phase is a pure structural refactoring. No new abstractions, patterns, or libraries are needed. The existing code organization within the monolith already has clear responsibility boundaries -- the extraction follows those boundaries.

## Common Pitfalls

### Pitfall 1: Circular Imports After Splitting

**What goes wrong:** `buttons.py` imports from `app.py` to get the `InkyPhotoFrame` type, and `app.py` imports from `buttons.py` to create the `ButtonController`. Python raises `ImportError: cannot import name X from partially initialized module`.

**Why it happens:** The current code uses constructor injection (`ButtonController(self)`) which works in a single file but looks like it needs a type import when split into modules.

**How to avoid:**
- `buttons.py` does NOT import `app.py` -- it receives the app instance via `__init__(self, photo_frame)` with no type annotation or with `TYPE_CHECKING`-guarded annotation
- `photos.py` (PhotoHandler) does NOT import `app.py` -- it receives `slideshow` via `__init__(self, slideshow)` the same way
- Import direction is strictly: `app.py` -> `buttons.py`, `app.py` -> `photos.py`, never the reverse

**Warning signs:** Any `.py` file in the package that imports from `app.py`

### Pitfall 2: Module-Level Side Effects Break CI and Tests

**What goes wrong:** `import inky_photo_frame.display` triggers `logging.basicConfig()` which overwrites test logging, or triggers hardware probes.

**Why it happens:** The current monolith runs `logging.basicConfig()` at import time (line 153-160). When split into modules, every import path triggers this.

**How to avoid:**
- Create a `setup_logging()` function in `config.py`
- Call it only from the shim (`inky_photo_frame.py`), `__main__.py`, and `app.py`'s `run()` method
- Never call it at module level

**Warning signs:** `python -c "from inky_photo_frame import config"` produces log output or fails

### Pitfall 3: Shim Imports Itself Instead of Package

**What goes wrong:** The shim `inky_photo_frame.py` at the repo root tries `from inky_photo_frame.app import ...` but Python resolves `inky_photo_frame` to the `.py` file itself instead of the package directory.

**Why it happens:** This would only happen if `inky_photo_frame/` did not have an `__init__.py`, or if `sys.path` is manipulated incorrectly.

**How to avoid:**
- Ensure `inky_photo_frame/__init__.py` exists (even if nearly empty)
- Do NOT add the package directory itself to `sys.path`
- Do NOT use `sys.path.insert()` in the shim
- The shim works because direct script execution (`python file.py`) adds the script's directory to `sys.path[0]`, and the import system finds the package directory first

**Warning signs:** `ImportError: cannot import name 'app' from 'inky_photo_frame'` with a traceback pointing to `inky_photo_frame.py` (the shim) instead of `inky_photo_frame/__init__.py`

### Pitfall 4: `VERSION` Grep Breaks in update.sh

**What goes wrong:** `update.sh` detects the version via `grep "^VERSION = " "$INSTALL_DIR/inky_photo_frame.py"`. After refactoring, `VERSION` moves to `config.py` inside the package, but the grep still targets the shim file.

**Why it happens:** `update.sh` is not updated in this phase (that is Phase 4, STRC-03).

**How to avoid:**
- Keep a `VERSION` reference accessible from the shim file, OR
- Accept that version detection will be fixed in Phase 4 when `update.sh` is updated
- Document this as a known interim issue between Phase 3 and Phase 4

**Warning signs:** `update.sh` reports "unknown" version after Phase 3 deployment

### Pitfall 5: Hard-Coded Paths Prevent Testing

**What goes wrong:** `PHOTOS_DIR`, `HISTORY_FILE`, `COLOR_MODE_FILE`, `LOG_FILE` are module-level constants in `config.py`. Tests that import `config` get production paths pointing to `/home/pi/`.

**Why it happens:** These are currently top-of-file constants. Moving them into `config.py` doesn't change the fact that they're hard-coded.

**How to avoid:**
- For this phase: keep them as module-level constants in `config.py` (same as current behavior)
- Phase 5/6 will address testability by injecting paths via constructor parameters or environment variables
- Do NOT try to solve the testing problem in this phase -- it adds scope and risk

**Warning signs:** Attempting to add path-injection logic during module extraction

### Pitfall 6: Forgetting to Move `BUTTONS_AVAILABLE` Flag

**What goes wrong:** The `BUTTONS_AVAILABLE` flag (set by the guarded `gpiozero` import, lines 52-56) is needed by `app.py` to decide whether to create a `ButtonController`. If it stays in `buttons.py`, `app.py` must import it from there.

**Why it happens:** The flag is a side effect of the import guard pattern.

**How to avoid:**
- Keep `BUTTONS_AVAILABLE` in `buttons.py` where the guarded import lives
- `app.py` imports it: `from inky_photo_frame.buttons import BUTTONS_AVAILABLE, ButtonController`
- This is safe because `app.py` -> `buttons.py` is the correct dependency direction

## Code Examples

### Example 1: config.py (the foundation module)

```python
"""Configuration constants for Inky Photo Frame."""

import os

# Must be set before any inky import anywhere in the package
os.environ['INKY_SKIP_GPIO_CHECK'] = '1'

from pathlib import Path

# Application metadata
VERSION = "2.0.0"

# Paths
PHOTOS_DIR = Path('/home/pi/Images')
HISTORY_FILE = Path('/home/pi/.inky_history.json')
COLOR_MODE_FILE = Path('/home/pi/.inky_color_mode.json')
LOG_FILE = '/home/pi/inky_photo_frame.log'

# Timing
CHANGE_HOUR = 5
CHANGE_INTERVAL_MINUTES = 0
MAX_PHOTOS = 1000

# Color settings
COLOR_MODE = 'spectra_palette'
SATURATION = 0.5

SPECTRA_PALETTE = {
    'black':  (0x00, 0x00, 0x00),
    'white':  (0xff, 0xff, 0xff),
    'red':    (0xa0, 0x20, 0x20),
    'yellow': (0xf0, 0xe0, 0x50),
    'green':  (0x60, 0x80, 0x50),
    'blue':   (0x50, 0x80, 0xb8),
}

WARMTH_BOOST_CONFIG = {
    'red_boost': 1.15,
    'green_reduce': 0.92,
    'blue_reduce': 0.75,
    'brightness': 1.12,
    'saturation': 0.3,
}

DISPLAY_CONFIGS = {
    # ... (full dict from lines 103-150)
}


def setup_logging():
    """Configure logging. Call only from entry points, never at import time."""
    import logging
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
```

### Example 2: The 3-line shim (inky_photo_frame.py at repo root)

```python
#!/usr/bin/env python3
"""Inky Photo Frame - backward-compatible entry point for systemd service."""
from inky_photo_frame.app import InkyPhotoFrame
InkyPhotoFrame().run()
```

Note: `setup_logging()` should be called inside `InkyPhotoFrame.__init__()` or at the top of `InkyPhotoFrame.run()`, not in the shim. This keeps the shim minimal and avoids duplicating the logging call between the shim and `__main__.py`.

### Example 3: __init__.py (minimal)

```python
"""Inky Photo Frame - Universal E-Ink Photo Frame for Inky Impression."""

from inky_photo_frame.config import VERSION

__version__ = VERSION
```

### Example 4: __main__.py (minimal)

```python
"""Entry point for python -m inky_photo_frame."""

from inky_photo_frame.app import InkyPhotoFrame

InkyPhotoFrame().run()
```

### Example 5: display.py (lazy hardware import)

```python
"""Display management singleton with GPIO/SPI lifecycle handling."""

import logging
import threading
import atexit
import signal
import time as time_module
from functools import wraps

from inky_photo_frame.config import VERSION


class DisplayManager:
    """Singleton to manage Inky display with robust GPIO/SPI handling."""
    _instance = None
    _display = None
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize display once at startup."""
        with self._lock:
            if self._initialized:
                return self._display

            logging.info(f'Inky Photo Frame v{VERSION}')
            logging.info('Initializing display...')

            try:
                # Hardware import happens HERE, not at module level
                from inky.auto import auto
                self._display = auto()
                self._initialized = True
                # ... rest of init
```

### Example 6: buttons.py (guarded import, constructor injection)

```python
"""GPIO button controller for photo frame navigation."""

import logging

# Optional GPIO button support
try:
    from gpiozero import Button
    BUTTONS_AVAILABLE = True
except ImportError:
    BUTTONS_AVAILABLE = False


class ButtonController:
    """Handles 4 GPIO buttons for photo frame control."""

    def __init__(self, photo_frame):
        """
        Args:
            photo_frame: InkyPhotoFrame instance (injected, not imported).
        """
        self.photo_frame = photo_frame
        self.busy = False
        # ... rest of init using Button() from gpiozero
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-file Python scripts | Package with `__init__.py` | Python standard since 1.5 | Well-established, no version concerns |
| `if __name__ == '__main__'` in `__main__.py` | Minimal `__main__.py` without guard | Python 3.x best practice | Cleaner, consistent with official docs |
| Re-export everything from `__init__.py` | Minimal `__init__.py`, import from submodules | Modern Python convention | Better tree-shaking, clearer dependencies |

**Deprecated/outdated:**
- Namespace packages (implicit, no `__init__.py`): Not applicable here -- we need an explicit package with `__init__.py` for proper import precedence over the shim file

## Module Extraction Map

Detailed line-by-line mapping from the monolith to target modules:

| Target Module | Source Lines | Contents | Dependencies |
|---------------|-------------|----------|--------------|
| `config.py` | 30-32, 58-150, 152-160 | `os.environ` guard, all constants, `DISPLAY_CONFIGS`, `setup_logging()` | `os`, `pathlib`, `logging`, `sys` (stdlib only) |
| `display.py` | 166-257 | `DisplayManager` class, `retry_on_error` decorator | `config.VERSION` |
| `image_processor.py` | 758-880 | `_apply_spectra_palette()`, `_apply_warmth_boost()`, `process_image()` | `config.SPECTRA_PALETTE`, `config.WARMTH_BOOST_CONFIG` |
| `photos.py` | 346-401, 646-756 | `PhotoHandler` class, `get_all_photos()`, `cleanup_old_photos()`, `refresh_pending_list()`, history load/save | `config.PHOTOS_DIR`, `config.HISTORY_FILE`, `config.MAX_PHOTOS` |
| `buttons.py` | 52-56, 263-340 | `BUTTONS_AVAILABLE` flag, `ButtonController` class | `gpiozero` (optional, guarded) |
| `welcome.py` | 515-615 | `get_ip_address()`, `get_credentials()`, `display_welcome()` | `config` paths |
| `app.py` | 402-454, 882-1216 | `InkyPhotoFrame` class (orchestrator), `run()` loop, `__init__()`, photo navigation methods, color mode methods, scheduling | All other modules |
| `__init__.py` | N/A (new) | Version export only | `config.VERSION` |
| `__main__.py` | 1214-1216 | Entry point for `python -m` | `app.InkyPhotoFrame` |

### Methods That Move to `app.py` (InkyPhotoFrame orchestrator)

These methods stay on the `InkyPhotoFrame` class but call extracted module functions:

- `__init__()` -- orchestrates initialization of display, buttons, history
- `detect_display_saturation()` -- uses `config.DISPLAY_CONFIGS`
- `display_photo()` -- calls `image_processor.process_image()` then display
- `add_to_queue()`, `display_new_photo()`, `change_photo()`, `next_photo()`, `previous_photo()` -- photo navigation
- `cycle_color_mode()`, `reset_color_mode()`, `load_color_mode()`, `save_color_mode()` -- color mode management
- `should_change_photo()` -- scheduling
- `display_current_or_change()` -- startup logic
- `run()` -- main loop

### Methods That Move to Extracted Modules

| Method | Current Location | Target Module | Notes |
|--------|-----------------|---------------|-------|
| `_apply_spectra_palette(img)` | InkyPhotoFrame method | `image_processor.py` (module-level function) | No longer needs `self` |
| `_apply_warmth_boost(img)` | InkyPhotoFrame method | `image_processor.py` (module-level function) | No longer needs `self` |
| `process_image(image_path)` | InkyPhotoFrame method | `image_processor.py` (module-level function) | Takes explicit params instead of `self` |
| `get_all_photos()` | InkyPhotoFrame method | `photos.py` (module-level function) | Uses `config.PHOTOS_DIR` directly |
| `cleanup_old_photos()` | InkyPhotoFrame method | stays on `app.py` InkyPhotoFrame | Uses `self.history` and `self.lock` |
| `refresh_pending_list()` | InkyPhotoFrame method | stays on `app.py` InkyPhotoFrame | Uses `self.history` and `self.lock` |
| `load_history()` | InkyPhotoFrame method | `photos.py` (module-level function) | Takes optional path param |
| `save_history()` | InkyPhotoFrame method | stays on `app.py` InkyPhotoFrame | Uses `self.lock` |
| `get_ip_address()` | InkyPhotoFrame method | `welcome.py` (module-level function) | No `self` needed |
| `get_credentials()` | InkyPhotoFrame method | `welcome.py` (module-level function) | No `self` needed |
| `display_welcome()` | InkyPhotoFrame method | `welcome.py` (module-level function) | Takes display dimensions + display object |

## Open Questions

1. **Where should `setup_logging()` be called?**
   - What we know: It must be called once before any logging happens, but NOT at import time
   - What's unclear: Should it be in `InkyPhotoFrame.__init__()`, in `InkyPhotoFrame.run()`, or in both the shim and `__main__.py`?
   - Recommendation: Call it at the start of `InkyPhotoFrame.run()`. This centralizes the call and ensures it runs regardless of entry point (shim or `python -m`). Both entry points call `InkyPhotoFrame().run()`, so one call site covers both paths.

2. **Should `process_image()` be refactored to separate I/O from logic?**
   - What we know: PITFALLS.md Pitfall 6 recommends splitting into `load_image(path)` + `process_image(img, ...)` for testability
   - What's unclear: Should this refactoring happen in Phase 3 or Phase 6 (test suite)?
   - Recommendation: Do the split in Phase 3 since it is the natural boundary when extracting to `image_processor.py`. The function already has clear I/O (line 829: `Image.open()`) and pure logic (lines 834-880: crop/resize/color). Splitting them during extraction costs nothing extra.

3. **How does `update.sh` version detection survive Phase 3?**
   - What we know: `update.sh` greps `VERSION = ` from `inky_photo_frame.py`. After Phase 3, the shim no longer contains `VERSION`.
   - What's unclear: Whether to add a VERSION comment to the shim for compatibility, or accept the breakage until Phase 4.
   - Recommendation: Accept the interim breakage. Phase 4 (STRC-03) explicitly updates `update.sh`. Adding a VERSION hack to the shim creates technical debt.

## Sources

### Primary (HIGH confidence)
- Python official import system documentation: https://docs.python.org/3/reference/import.html -- package vs module precedence
- Python official `__main__` documentation: https://docs.python.org/3/library/__main__.html -- `__main__.py` patterns
- Direct code inspection: `/Users/mehdiguiard/Desktop/INKY_V2/inky_photo_frame.py` (1,216 lines, read in full)
- Direct infrastructure inspection: `install.sh` (ExecStart path, line 256), `update.sh` (VERSION grep, lines 46/96)
- GSD codebase analysis: `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONCERNS.md`, `CONVENTIONS.md`
- GSD pitfalls research: `.planning/research/PITFALLS.md` (7 pitfalls documented, all relevant)

### Secondary (MEDIUM confidence)
- itsdangerous single-module-to-package refactoring PR: https://github.com/pallets/itsdangerous/pull/107 -- real-world example of backward-compatible package extraction
- Python import system precedence analysis: https://trstringer.com/python-module-import-precedence/ -- module import resolution order
- Python import traps: https://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html -- same-name collision documentation
- Python discuss.python.org thread on `__init__.py` search order: https://discuss.python.org/t/how-exactly-does-init-py-influence-module-search-order/24759

### Tertiary (LOW confidence)
- None -- all findings verified against primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure refactoring of existing code
- Architecture: HIGH -- module boundaries clearly defined by existing class/function groupings in the monolith; dependency graph verified by code inspection
- Pitfalls: HIGH -- all 6 pitfalls identified via direct code analysis and verified against existing `.planning/research/PITFALLS.md`; the name collision behavior verified against Python official docs
- Entry point strategy: HIGH -- systemd ExecStart path confirmed in `install.sh` line 256; shim pattern verified against Python import precedence rules

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain, no version-sensitive findings)
