# Coding Conventions

**Analysis Date:** 2026-02-22

## Naming Patterns

**Files:**
- `inky_photo_frame.py` - Main application file using snake_case
- `inky-photo-frame-cli` - CLI wrapper using kebab-case for shell scripts
- Convention: Snake_case for Python modules, kebab-case for shell scripts/binaries

**Functions:**
- Public methods: camelCase with lowercase start (e.g., `display_photo()`, `next_photo()`, `change_photo()`)
- Private/internal methods: underscore prefix with snake_case (e.g., `_on_button_a()`, `_apply_spectra_palette()`, `_apply_warmth_boost()`)
- Decorator functions: snake_case (e.g., `retry_on_error()`)

**Variables:**
- Module-level constants: UPPERCASE_WITH_UNDERSCORES (e.g., `PHOTOS_DIR`, `CHANGE_HOUR`, `COLOR_MODE`, `MAX_PHOTOS`, `VERSION`, `LOG_FILE`)
- Instance variables: snake_case with no prefix (e.g., `self.display`, `self.width`, `self.history`, `self.button_controller`)
- Local variables: snake_case (e.g., `photo_path`, `next_photo`, `is_recoverable`)
- Boolean prefixes: Generally no "is_" prefix in most cases, but used when appropriate (e.g., `BUTTONS_AVAILABLE`, `self.is_spectra`, `self.is_13inch`)

**Types/Classes:**
- Class names: PascalCase (e.g., `DisplayManager`, `ButtonController`, `PhotoHandler`, `InkyPhotoFrame`)
- Dictionary keys: snake_case (e.g., in `DISPLAY_CONFIGS`, `gpio_pins`, `button_a`, `detection`)
- Config dictionaries: Nested dicts with lowercase keys (e.g., `SPECTRA_PALETTE`, `WARMTH_BOOST_CONFIG`)

## Code Style

**Formatting:**
- No explicit formatter detected (no .prettierrc, .style.yapf, etc.)
- Indentation: 4 spaces (Python standard)
- Line length: Appears to follow ~100-110 character limit (most lines wrap appropriately)
- String quotes: Mix of single and double quotes, no strict convention
  - Double quotes for docstrings and longer strings
  - Single quotes for simple strings in some contexts
  - f-strings used extensively for logging (e.g., `f'🚀 Inky Photo Frame v{VERSION}'`)

**Linting:**
- No linting configuration files detected (.eslintrc, .flake8, .pylintrc, pyproject.toml)
- Code follows general PEP 8 conventions implicitly
- Some exceptions: bare `except:` clause used (line 548-552 in `display_welcome()`)

## Import Organization

**Order:**
1. Standard library imports (os, json, random, datetime, pathlib, PIL, time, logging, sys, etc.)
2. Third-party library imports (watchdog, gpiozero)
3. Optional imports in try/except blocks (pillow_heif, gpiozero)
4. Local/relative imports: None used (single-file application)

**Pattern from lines 30-56:**
```python
import os
# Set environment variable to skip GPIO check
os.environ['INKY_SKIP_GPIO_CHECK'] = '1'
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import time as time_module
import logging
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from threading import Timer
import socket
import subprocess
import atexit
import signal
from functools import wraps

# Optional GPIO button support
try:
    from gpiozero import Button
    BUTTONS_AVAILABLE = True
except ImportError:
    BUTTONS_AVAILABLE = False
```

**Path Aliases:**
- No path aliases used (`@` imports or similar)
- Absolute imports from installed packages only

## Error Handling

**Patterns:**
- Try/except with specific exception types preferred where possible (lines 423-425, 440-448)
- Broad exception catching used in GPIO initialization (lines 285-299, 441-445) due to hardware variability
- Bare `except:` only used in font loading fallback (line 548) - intentional graceful degradation
- Exceptions with optional logging on non-critical failures (lines 298-299: `logging.warning`)
- Critical exceptions logged as errors and re-raised (line 206-207: `logging.error`, then `raise`)

**Exception handling strategy by context:**
- Display initialization (line 190-207): Try/catch with logging and re-raise on critical errors
- Button controller (line 285-299): Try/catch with warning log (non-critical, graceful fallback)
- File operations (line 525-530): Try/catch with warning, fallback to defaults
- Display updates (line 606-610): Try/except TypeError to handle API compatibility
- Photo deletion (line 700-713): Try/catch per-file with error logging (don't stop batch process)

## Logging

**Framework:** Python's built-in `logging` module

**Configuration (lines 152-160):**
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
```

**Patterns:**
- INFO level for major state changes (lines 187, 196, 297, etc.)
- DEBUG level for detailed processing info (lines 859, 873, 889)
- WARNING level for recoverable issues (lines 249-250, 299, 484)
- ERROR level for failures affecting functionality (lines 206, 253, 390, 905)
- Emoji prefixes used extensively for quick visual parsing:
  - `🚀` for startup
  - `✅` for success
  - `❌` for errors
  - `📺` for display operations
  - `🎨` for color/visual operations
  - `🧹` for cleanup
  - `📁` for file operations
  - `📸` for photo operations
  - `⏰` for timing operations
  - `🆕` for new items
  - `👋` for shutdown

**Log locations:**
- File: `/home/pi/inky_photo_frame.log` (set in `LOG_FILE` constant)
- Console: stdout (duplicated to both file and console)

## Comments

**When to Comment:**
- Block-level docstrings on all classes (e.g., lines 167-170, 263-271, 341-342, 397-398)
- Method-level docstrings on most public methods (e.g., lines 181-182, 534-535, 612-613)
- Inline comments used sparingly for non-obvious logic:
  - Configuration sections clearly marked with `# ` headers (lines 99-101, 162-164)
  - Explain "why" in complex sections (lines 243-245, 849-850)

**JSDoc/TSDoc:**
- Not applicable (Python codebase, no type hints)
- Docstrings use simple summary format without formal tags
- Example from line 821-822:
```python
def process_image(self, image_path):
    """Process image for e-ink display with smart cropping and color correction"""
```

## Function Design

**Size:**
- Methods range from 2-3 lines (e.g., `get_display()`) to 80+ lines (e.g., `cleanup_old_photos()`)
- Most utility methods 10-40 lines
- Longer methods justified by data processing requirements (image processing, cleanup logic)

**Parameters:**
- Most methods 0-3 parameters (self + up to 2 args)
- Some utility functions take configuration dicts (e.g., `retry_on_error()` with max_attempts, delay, backoff)
- Private helper methods: Minimal parameters, often state-dependent through `self`

**Return Values:**
- Boolean returns for success/failure (e.g., `display_photo()` returns True/False)
- Photo path strings for navigation (e.g., `next_photo()` picks from list)
- Dictionary returns for state/history (e.g., `load_history()` returns dict)
- None returns acceptable for void operations (e.g., `save_history()`, `cleanup()`)

## Module Design

**Exports:**
- Single-file application, no explicit module structure
- Entry point: `if __name__ == '__main__':` at end (lines 1209-1211)
- Main execution: Creates instance and calls `frame.run()`

**Classes:**
- Class-based architecture with singleton pattern for `DisplayManager` (lines 166-227)
- Event handler class extending watchdog's `FileSystemEventHandler` (lines 341-396)
- Main controller class `InkyPhotoFrame` (lines 397-1207) - ~800 lines

**Constants grouped at module level (lines 58-97):**
- Path configurations
- Timing configurations
- Logging configurations
- Color mode mappings
- Display configurations (DISPLAY_CONFIGS dict structure)

## Decorator Usage

**Custom decorators:**
- `@retry_on_error(max_attempts=3, delay=1, backoff=2)` decorator (lines 229-257)
  - Implements exponential backoff
  - Used on `display_photo()` for hardware reliability (line 877)
  - Detects recoverable errors (GPIO, SPI, transport, endpoint, busy)

**Pattern (lines 234-257):**
```python
def retry_on_error(max_attempts=3, delay=1, backoff=2):
    """Decorator to retry operations on GPIO/SPI errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Recoverable error detection and retry logic
                    if is_recoverable and attempt < max_attempts:
                        wait_time = delay * (backoff ** (attempt - 1))
                        time_module.sleep(wait_time)
                    else:
                        raise
            return None
        return wrapper
    return decorator
```

## Threading

**Pattern:**
- Uses `threading.Lock()` for safe history updates (line 434: `self.lock = threading.Lock()`)
- Lock acquired in critical sections: `with self.lock:` (lines 636-638, 657, 720-751, 898-900, 924-944, 961-971, 991-1001, 1012-1025)
- Timer threads used for debounced file processing (line 366: `threading.Timer(3.0, self.process_uploads)`)
- Button press handlers use local `busy` flag for synchronization (lines 274, 303-308)

---

*Convention analysis: 2026-02-22*
