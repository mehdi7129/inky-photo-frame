# Architecture Research

**Domain:** Python hardware application — monolith-to-package refactoring
**Researched:** 2026-02-22
**Confidence:** HIGH

## Standard Architecture

### System Overview

The current monolith already has implicit layers. The refactoring makes those layers explicit as Python modules within a package. This is not an architectural redesign — it is a boundary extraction.

```
┌─────────────────────────────────────────────────────────────────┐
│                   Entry Points                                  │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐  │
│  │   __main__.py        │  │   inky-photo-frame-cli (bash)   │  │
│  │  (python -m package) │  │   (systemd / CLI commands)      │  │
│  └──────────┬───────────┘  └─────────────────────────────────┘  │
├─────────────┼───────────────────────────────────────────────────┤
│             │         Application Layer                          │
│  ┌──────────▼───────────┐                                        │
│  │   app.py             │  InkyPhotoFrame — orchestrates all     │
│  │   (main coordinator) │  subsystems, owns main run() loop      │
│  └──┬──────┬──────┬─────┘                                        │
├────┼──────┼──────┼──────────────────────────────────────────────┤
│   │      │      │          Domain Layer                          │
│  ┌▼──────┐ ┌────▼──────┐ ┌▼──────────────┐ ┌────────────────┐  │
│  │photos │ │image_     │ │buttons.py     │ │schedule.py     │  │
│  │.py    │ │processor  │ │ButtonController│ │(time / cron    │  │
│  │Photo  │ │.py        │ │+ PhotoHandler │ │ logic)         │  │
│  │history│ │Color modes│ │               │ │                │  │
│  │Storage│ │Crop/resize│ │               │ │                │  │
│  └───────┘ └───────────┘ └───────────────┘ └────────────────┘  │
├────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                          │
│  ┌──────────────────────┐  ┌────────────────────────────────┐   │
│  │   display.py         │  │   config.py                    │   │
│  │   DisplayManager     │  │   DISPLAY_CONFIGS, constants,  │   │
│  │   retry_on_error     │  │   SPECTRA_PALETTE, file paths  │   │
│  │   (GPIO/SPI/Inky)    │  │                                │   │
│  └──────────────────────┘  └────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `__main__.py` | Entry point for `python -m inky_photo_frame` | `app.py` only |
| `app.py` (InkyPhotoFrame) | Orchestrates all subsystems; owns `run()` loop | all domain modules |
| `config.py` | All constants, file paths, display configs, palette data | imported by all modules |
| `display.py` (DisplayManager) | Singleton GPIO/SPI lifecycle; retry decorator | `inky.auto`, hardware |
| `image_processor.py` | Color mode transforms, crop, resize, dithering | `config.py`, PIL |
| `photos.py` | Photo discovery, history persistence, storage cleanup | `config.py`, file system |
| `buttons.py` (ButtonController + PhotoHandler) | GPIO button callbacks; watchdog file events | `app.py` via callbacks |
| `welcome.py` | Render welcome screen image with network/credential info | `config.py`, PIL |

## Recommended Project Structure

```
inky-photo-frame/               ← repo root (unchanged)
├── inky_photo_frame/           ← NEW: Python package directory
│   ├── __init__.py             ← exposes VERSION, main entry symbol
│   ├── __main__.py             ← python -m inky_photo_frame entry point
│   ├── app.py                  ← InkyPhotoFrame class + run()
│   ├── config.py               ← all constants, file paths, display configs
│   ├── display.py              ← DisplayManager singleton + retry_on_error
│   ├── image_processor.py      ← process_image(), color mode transforms
│   ├── photos.py               ← photo discovery, history, cleanup
│   ├── buttons.py              ← ButtonController + PhotoHandler
│   └── welcome.py              ← display_welcome() rendered image
├── tests/
│   ├── __init__.py
│   ├── conftest.py             ← pytest fixtures, GPIO mocks
│   ├── test_image_processor.py ← pure logic, no hardware
│   ├── test_photos.py          ← history/storage logic
│   └── test_app.py             ← integration tests with full mocks
├── inky_photo_frame.py         ← KEPT as thin shim for backward compat
├── inky-photo-frame-cli        ← unchanged bash script
├── install.sh                  ← updated to reference package dir
├── update.sh                   ← updated FILES_TO_UPDATE list
├── requirements.txt
└── README.md
```

### Structure Rationale

- **`inky_photo_frame/` package at root:** The Hitchhiker's Guide to Python and Real Python both recommend placing the package at the repository root level, not in a `src/` subdirectory, for non-pip-installable projects. This also matches how `inky-photo-frame-cli` and `update.sh` resolve the install directory.

- **`inky_photo_frame.py` kept as shim:** Existing installations reference `INSTALL_DIR/inky_photo_frame.py` in systemd service files, `update.sh` (line 46: `grep "^VERSION = " "$INSTALL_DIR/inky_photo_frame.py"`), and the CLI (line 48). The shim contains only: `from inky_photo_frame import app; app.main()` plus `VERSION = "2.0"`. This is the critical backward-compatibility contract.

- **`config.py` extracted first:** All modules depend on constants. Making this the first extraction eliminates circular import risk. Nothing in config imports from other modules.

- **`display.py` second:** Hardware abstraction extracted second because it depends only on `config.py` and external libraries. Once extracted, `image_processor.py` and `app.py` both depend on it cleanly.

- **`image_processor.py` is the priority for testability:** The image processing pipeline has no hardware dependencies beyond PIL. Pure logic tests can run in CI with no GPIO mocks. This is the highest-value extraction for test coverage.

- **`buttons.py` bundles ButtonController + PhotoHandler:** Both are input controllers that adapt external events (GPIO, file system) into `app.py` callbacks. They belong together and both require GPIO/watchdog mocks in tests.

- **`welcome.py` extracted last:** Low complexity, pure PIL, no dependencies on other new modules. Can be deferred to a late step.

## Architectural Patterns

### Pattern 1: Backward-Compatible Shim

**What:** Keep the original `inky_photo_frame.py` as a thin 3-line entry point that imports and calls the new package. Existing systemd services and `update.sh` continue to work without modification.

**When to use:** Any time a script has external callers (systemd unit files, update scripts, user documentation) that reference it by name.

**Trade-offs:** Adds one indirection layer. Small cost for zero breaking changes on active user installations.

**Example:**
```python
# inky_photo_frame.py (shim — replaces 1100-line file)
"""Backward-compatible entry point. Real code is in inky_photo_frame/ package."""
from inky_photo_frame import __version__ as VERSION  # noqa: F401 (update.sh greps this)
from inky_photo_frame.app import InkyPhotoFrame

if __name__ == '__main__':
    frame = InkyPhotoFrame()
    frame.run()
```

Note: `update.sh` line 46 greps `"^VERSION = "` from this file, so `VERSION` must remain a module-level name matching that pattern.

### Pattern 2: Config-First Extraction Order

**What:** Extract constants and configuration dictionaries into `config.py` as the very first module. All other modules import from `config.py`; `config.py` imports from nothing in the project.

**When to use:** Splitting any Python monolith. Circular import problems almost always originate from constants living in the same file as business logic.

**Trade-offs:** None. There is no reason to do this differently.

**Example:**
```python
# inky_photo_frame/config.py
from pathlib import Path

VERSION = "2.0"
PHOTOS_DIR = Path('/home/pi/Images')
HISTORY_FILE = Path('/home/pi/.inky_history.json')
COLOR_MODE_FILE = Path('/home/pi/.inky_color_mode.json')
LOG_FILE = '/home/pi/inky_photo_frame.log'
MAX_PHOTOS = 1000
CHANGE_HOUR = 5
CHANGE_INTERVAL_MINUTES = 0
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

DISPLAY_CONFIGS = { ... }  # moved verbatim
```

### Pattern 3: Dependency Injection for Hardware Abstractions

**What:** `app.py` receives `display_manager`, `button_controller`, and `photo_handler` as constructor arguments (or creates them internally but behind an interface). Tests inject mock objects. Production code uses real ones.

**When to use:** Any hardware-dependent class that needs CI testing. This is the standard pattern for Python hardware projects with GPIO mocking.

**Trade-offs:** Slightly more constructor arguments. Worth it: enables full test coverage without Raspberry Pi hardware.

**Example:**
```python
# inky_photo_frame/app.py
class InkyPhotoFrame:
    def __init__(self, display_manager=None):
        # Allow injection for testing; create real one for production
        self.display_manager = display_manager or DisplayManager()
        self.display = self.display_manager.initialize()
        ...
```

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_display():
    display = MagicMock()
    display.resolution = (800, 480)
    return display

@pytest.fixture
def mock_display_manager(mock_display):
    dm = MagicMock()
    dm.initialize.return_value = mock_display
    return dm
```

### Pattern 4: Module-Private vs Package-Public API

**What:** Functions intended only for internal module use are named with a leading underscore (`_apply_spectra_palette`, `_apply_warmth_boost`). Only the top-level `process_image()` function is exported without underscore. `__init__.py` only re-exports the public surface.

**When to use:** All modules in the package. Prevents tests from coupling to internal implementation details.

**Trade-offs:** None. This is standard Python convention and guides test design toward public interfaces.

## Data Flow

### Photo Display Flow

```
User button press or scheduled time trigger
    |
    v
app.py: InkyPhotoFrame.next_photo() / change_photo()
    |
    v
photos.py: resolve photo path from pending queue
    |
    v
image_processor.py: process_image(path, color_mode, width, height)
    - crop + resize to display resolution
    - apply color transform (pimoroni / spectra_palette / warmth_boost)
    |
    v
display.py: DisplayManager.get_display().set_image(image, saturation)
    - @retry_on_error decorator (3 attempts, exponential backoff)
    |
    v
photos.py: update_history(current → shown, new → current)
    - persist to HISTORY_FILE
```

### File Upload Flow

```
SMB upload to /home/pi/Images/photo.jpg
    |
    v (watchdog event)
buttons.py: PhotoHandler.on_created()
    - validate image extension
    - set 3-second debounce timer
    |
    v (timer fires)
buttons.py: PhotoHandler.process_uploads()
    - last photo → display immediately via app callback
    - others → add to pending queue via app callback
    |
    v
app.py: display_new_photo(path) → image_processor → display
```

### Color Mode Lifecycle

```
Startup: config.py COLOR_MODE default
    |
    v (override from disk)
photos.py / app.py: load_color_mode() reads COLOR_MODE_FILE
    |
    v
Button C press → app.py: cycle_color_mode()
    - rotate: pimoroni → spectra_palette → warmth_boost → pimoroni
    - persist new mode to COLOR_MODE_FILE
    - re-display current photo with new mode
    |
Button D press → app.py: reset_color_mode()
    - force pimoroni mode
    - persist, re-display
```

### Module Import Graph

```
config.py           (no project imports)
    ^
    |── display.py        (imports config)
    |── image_processor.py (imports config)
    |── photos.py          (imports config)
    |── welcome.py         (imports config)
    |── buttons.py         (imports config)
    |
    └── app.py             (imports all of above)
           ^
           |
    __main__.py             (imports app only)
    inky_photo_frame.py     (shim, imports app)
```

No circular dependencies. `app.py` is the only module that imports from multiple siblings.

## Suggested Build Order

Refactoring must be done in dependency order. Each step leaves the system runnable.

**Step 1 — Extract `config.py`:**
Move all module-level constants, `DISPLAY_CONFIGS`, `SPECTRA_PALETTE`, `WARMTH_BOOST_CONFIG`. Update imports in `inky_photo_frame.py`. Run app to verify. No logic changed.

**Step 2 — Extract `display.py`:**
Move `DisplayManager` class and `retry_on_error` decorator. Dependencies: only `config.py` + stdlib + `inky.auto`. Run app to verify.

**Step 3 — Extract `image_processor.py`:**
Move `process_image()`, `_apply_spectra_palette()`, `_apply_warmth_boost()`. Dependencies: `config.py`, PIL. This enables the first real unit tests in CI (no GPIO needed).

**Step 4 — Extract `photos.py`:**
Move photo discovery, history load/save, storage cleanup, `refresh_pending_list()`. Dependencies: `config.py`. Enables history/storage unit tests.

**Step 5 — Extract `buttons.py`:**
Move `ButtonController` and `PhotoHandler`. These reference `app` via callback — use a protocol/interface or pass the frame reference. Enables GPIO-mocked tests.

**Step 6 — Extract `welcome.py`:**
Move `display_welcome()`, `get_ip_address()`, `get_credentials()`. Pure PIL, no hardware. Easy to test.

**Step 7 — Finalize `app.py`:**
`InkyPhotoFrame` class now contains only orchestration: `__init__`, `run()`, scheduling logic, and the coordination methods that call into other modules. Write `__main__.py`. Convert `inky_photo_frame.py` to shim.

**Step 8 — Update `update.sh`:**
Add the new module files to `FILES_TO_UPDATE` array. The shim `inky_photo_frame.py` stays in the list so version grepping continues to work.

## Anti-Patterns

### Anti-Pattern 1: Big-Bang Extraction

**What people do:** Extract all modules in one commit and fix the resulting import errors.

**Why it's wrong:** At 1100 lines, this produces dozens of simultaneous import errors, broken references, and makes it impossible to isolate which extraction broke which behavior. Rollback requires reverting everything.

**Do this instead:** One module per commit. Run the app (or tests) after each extraction to verify the system still works before proceeding.

### Anti-Pattern 2: Circular Imports via Bidirectional Module References

**What people do:** `buttons.py` imports from `app.py` to access `InkyPhotoFrame` methods; `app.py` imports from `buttons.py` to create the `ButtonController`.

**Why it's wrong:** Python cannot resolve circular imports. The import system will raise `ImportError: cannot import name 'X'` at startup.

**Do this instead:** `ButtonController` receives a callback dict or the frame reference as a constructor argument. It does not import `app.py`. Data flows one way: `buttons.py` calls into `app.py` callbacks; `app.py` creates `ButtonController(self)`.

### Anti-Pattern 3: Moving Constants Into `__init__.py`

**What people do:** Put `VERSION`, `PHOTOS_DIR`, and other constants in `__init__.py` for "convenience."

**Why it's wrong:** `__init__.py` gets imported first when any submodule is imported. Putting non-trivial code there (file path resolutions, dict definitions) creates ordering problems and makes the package harder to test in isolation.

**Do this instead:** `__init__.py` contains only re-exports and the docstring. All constants live in `config.py`.

```python
# inky_photo_frame/__init__.py — correct
"""Inky Photo Frame — e-ink photo slideshow for Raspberry Pi."""
from .config import VERSION

__version__ = VERSION
__all__ = ['VERSION']
```

### Anti-Pattern 4: Splitting `ButtonController` and `PhotoHandler` Into Separate Modules

**What people do:** Separate every class into its own file for "cleanliness."

**Why it's wrong:** `ButtonController` and `PhotoHandler` are both thin input adapters with similar responsibilities. Splitting them adds two files with ~100 lines each, more imports, and no architectural benefit. The complexity is not high enough to warrant it.

**Do this instead:** Both classes live in `buttons.py` as they serve the same role — adapting external events into application callbacks.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Inky display library (`inky.auto`) | Imported in `display.py` only | Mocked in tests via `unittest.mock.patch` |
| gpiozero / lgpio | Imported in `buttons.py` only | `BUTTONS_AVAILABLE` guard for non-Pi CI |
| watchdog | Used in `buttons.py` (PhotoHandler) | Mock `Observer` in tests |
| PIL / Pillow | Imported in `image_processor.py` and `welcome.py` | Testable without hardware |
| pillow-heif | Registered in `app.py` `__init__` | Optional, guarded by try/except |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `buttons.py` → `app.py` | Constructor callback reference | ButtonController(photo_frame) — keeps circular import clean |
| `app.py` → `image_processor.py` | Direct function call | `process_image(path, mode, w, h)` returns PIL Image |
| `app.py` → `photos.py` | Direct method calls | History state lives in app; photos.py provides pure functions |
| `app.py` → `display.py` | DisplayManager singleton | Singleton pattern preserved across extraction |
| `update.sh` → repo files | Raw file download per filename | FILES_TO_UPDATE must include all new module files |

## Scaling Considerations

This is an embedded single-user application. "Scaling" means hardware variants and maintainability, not users.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 Raspberry Pi | Current target — all modules in one package, single process |
| New display models | Add entries to `DISPLAY_CONFIGS` in `config.py` only |
| New color modes | Add processing function in `image_processor.py` + mode name in `config.py` |
| Multiple units managed remotely | Would require web layer (explicitly out of scope in PROJECT.md) |

### Scaling Priorities

1. **First maintainability concern:** Single large `InkyPhotoFrame` class — resolved by splitting into focused modules per the build order above.
2. **Second maintainability concern:** No tests — resolved by enabling testability of `image_processor.py` and `photos.py` in CI after extraction.

## Sources

- Hitchhiker's Guide to Python — Structuring Your Project: https://docs.python-guide.org/writing/structure/ (HIGH confidence — authoritative)
- Real Python — Python Application Layouts: https://realpython.com/python-application-layouts/ (HIGH confidence — authoritative)
- Breadcrumbs Collector — Modular Monolith in Python: https://breadcrumbscollector.tech/modular-monolith-in-python/ (MEDIUM confidence — community, verified against Python docs)
- Current codebase analysis (`inky_photo_frame.py`, 1100 lines, 2026-02-22) (HIGH confidence — primary source)
- `update.sh` and `inky-photo-frame-cli` — backward compat constraints (HIGH confidence — primary source)

---
*Architecture research for: Inky Photo Frame v2 — Python package modularization*
*Researched: 2026-02-22*
