# Coding Conventions

**Analysis Date:** 2026-02-22

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` — `inky_photo_frame.py`
- Shell scripts/binaries: `kebab-case` — `inky-photo-frame-cli`, `install.sh`, `update.sh`, `uninstall.sh`, `diagnostic_report.sh`

**Functions:**
- Public methods: `snake_case` — `display_photo()`, `next_photo()`, `change_photo()`, `load_history()`, `save_history()`
- Private/internal methods: `_snake_case` with leading underscore — `_on_button_a()`, `_apply_spectra_palette()`, `_apply_warmth_boost()`
- Module-level utility functions: `snake_case` — `retry_on_error()`

**Variables:**
- Module-level constants: `UPPER_SNAKE_CASE` — `PHOTOS_DIR`, `CHANGE_HOUR`, `COLOR_MODE`, `MAX_PHOTOS`, `VERSION`, `LOG_FILE`, `SPECTRA_PALETTE`, `WARMTH_BOOST_CONFIG`, `DISPLAY_CONFIGS`
- Instance variables: `snake_case` without prefix — `self.display`, `self.width`, `self.history`, `self.button_controller`, `self.color_mode`, `self.saturation`
- Local variables: `snake_case` — `photo_path`, `next_photo`, `is_recoverable`, `wait_time`
- Boolean module flags: `UPPER_SNAKE_CASE` — `BUTTONS_AVAILABLE`
- Boolean instance attributes: `snake_case` with `is_` prefix for display properties — `self.is_spectra`, `self.is_13inch`

**Types/Classes:**
- Class names: `PascalCase` — `DisplayManager`, `ButtonController`, `PhotoHandler`, `InkyPhotoFrame`
- Dictionary keys: lowercase `snake_case` — `gpio_pins`, `button_a`, `detection`, `is_spectra`, `module_contains`
- Module-level config dictionaries: `UPPER_SNAKE_CASE` dict names with lowercase keys — `SPECTRA_PALETTE`, `WARMTH_BOOST_CONFIG`, `DISPLAY_CONFIGS`

## Code Style

**Formatting:**
- No explicit formatter configured (no `.style.yapf`, `pyproject.toml`, `.black`, or similar)
- Indentation: 4 spaces (Python standard PEP 8)
- Line length: Approximately 100-110 characters; no enforced limit
- String quotes: Mix of single and double quotes
  - f-strings used extensively throughout logging calls: `f'🚀 Inky Photo Frame v{VERSION}'`
  - Single quotes preferred for simple string literals: `'pimoroni'`, `'spectra_palette'`
  - Double quotes used for longer docstrings and some constants

**Linting:**
- No linting configuration detected (`.flake8`, `.pylintrc`, `pyproject.toml [tool.flake8]` absent)
- Code implicitly follows PEP 8 conventions
- Known exception: bare `except:` clause used intentionally in font loading fallback (`inky_photo_frame.py` line 548) for graceful degradation

## Import Organization

**Order:**
1. Standard library imports (grouped together at top)
2. Third-party library imports (PIL, watchdog)
3. Optional hardware imports in `try/except` blocks

**Pattern from `inky_photo_frame.py` lines 30-56:**
```python
import os
os.environ['INKY_SKIP_GPIO_CHECK'] = '1'  # env var set immediately after os import
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import time as time_module  # aliased to avoid shadowing
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

**Note:** Standard library imports are NOT strictly grouped by stdlib/third-party boundaries (PIL is mixed in). Optional/hardware-dependent imports are consistently wrapped in `try/except ImportError`.

**Path Aliases:**
- Not used. All imports are absolute from installed packages.

## Error Handling

**Strategy:**
Tiered exception handling by severity, with graceful degradation for non-critical hardware failures and re-raise for critical initialization failures.

**Patterns by context:**

- **Critical initialization** (`inky_photo_frame.py` lines 190-207): Catch all exceptions, log as error, then re-raise. Application cannot continue without display.
  ```python
  try:
      from inky.auto import auto
      self._display = auto()
      self._initialized = True
  except Exception as e:
      logging.error(f'❌ Failed to initialize display: {e}')
      raise
  ```

- **Non-critical hardware** (`inky_photo_frame.py` lines 285-299): Catch all exceptions, log as warning, continue without feature.
  ```python
  try:
      self.button_a = Button(gpio_a, bounce_time=0.02)
      # ...
  except Exception as e:
      logging.warning(f'⚠️ Could not initialize buttons: {e}')
      # graceful degradation: no buttons but service continues
  ```

- **API compatibility** (`inky_photo_frame.py` lines 606-610, 887-891): Catch `TypeError` only when handling optional method parameters across library versions.
  ```python
  try:
      self.display.set_image(img, saturation=self.saturation)
  except TypeError:
      self.display.set_image(img)
  ```

- **Per-item batch operations** (`inky_photo_frame.py` lines 700-713): Catch all exceptions per item, log error, continue loop. Never abort a batch on a single failure.
  ```python
  try:
      Path(photo_path).unlink()
  except Exception as e:
      logging.error(f'Error deleting {photo_path}: {e}')
      # continue to next file
  ```

- **Bare `except:` blocks** (`inky_photo_frame.py` line 548): Used only for font loading fallback — intentional and documented pattern for graceful degradation on non-Pi systems.

- **Recoverable error detection** (`inky_photo_frame.py` lines 243-245): String matching on error messages to classify GPIO/SPI errors as recoverable:
  ```python
  is_recoverable = any(x in error_msg for x in [
      'gpio', 'spi', 'pins', 'transport', 'endpoint', 'busy'
  ])
  ```

## Logging

**Framework:** Python's built-in `logging` module

**Configuration (`inky_photo_frame.py` lines 152-160):**
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

**Log levels:**
- `logging.info()` — major state changes, startup, success confirmations
- `logging.debug()` — detailed processing (color mode details, saturation values)
- `logging.warning()` — recoverable issues, degraded functionality (missing GPIO, retry attempts)
- `logging.error()` — failures that affect functionality, exception messages

**Emoji prefix convention (visual parsing in logs):**
- `🚀` startup sequence
- `✅` success
- `❌` error/failure
- `📺` display operations
- `🎨` color/visual processing
- `🧹` cleanup operations
- `📁` file/directory operations
- `📸` photo detection/watcher
- `⏰` timing/scheduling
- `🆕` new photo immediate display
- `👋` shutdown/stop
- `📱` HEIF/iPhone photo support
- `📚` history loading
- `🗑️` storage cleanup/deletion
- `🔥` warmth boost color mode
- `✨` spectra palette application

**Log destinations:**
- File: `/home/pi/inky_photo_frame.log` (set via `LOG_FILE` constant at line 64)
- Console: `sys.stdout` (duplicated to both handlers simultaneously)

## Comments

**Docstrings:**
- All classes have module-level docstrings describing purpose and key behaviors
- Most public methods have single-line or multi-line docstrings
- Private helper methods (`_apply_spectra_palette`, `_apply_warmth_boost`) have multi-line docstrings explaining algorithm steps

**Example pattern:**
```python
def process_image(self, image_path):
    """Process image for e-ink display with smart cropping and color correction"""
```

**Section separators:**
- Large banners used to separate major code sections:
  ```python
  # ============================================================================
  # DISPLAY MANAGER - Singleton pattern for robust GPIO/SPI management
  # ============================================================================
  ```

**Inline comments:**
- Used to explain non-obvious logic: hardware quirks, algorithm steps, configuration reasons
- File-level module docstring (lines 2-28) documents color mode options with visual alignment

**Type hints:**
- Not used. No type annotations in the codebase.

## Function Design

**Size:**
- Utility methods: 2-15 lines (e.g., `get_display()`, `save_color_mode()`, `add_to_queue()`)
- Business logic methods: 20-50 lines (e.g., `change_photo()`, `refresh_pending_list()`, `process_image()`)
- Complex operations: 50-90 lines with justified complexity (e.g., `cleanup_old_photos()`, `display_welcome()`)

**Parameters:**
- Methods take 0-3 parameters (always including `self`)
- Decorator factory pattern for configuration: `retry_on_error(max_attempts=3, delay=1, backoff=2)`
- Private helpers minimize parameters by relying on `self` state

**Return values:**
- `bool` for success/failure: `display_photo()`, `next_photo()`, `previous_photo()`, `change_photo()`
- `dict` for state data: `load_history()`
- `str` for computed values: `get_ip_address()`
- `None` for void operations: `save_history()`, `cleanup()`, `display_welcome()`

## Module Design

**Architecture:**
- Single-file application (`inky_photo_frame.py`) — no package structure
- Entry point guard at bottom of file (`inky_photo_frame.py` lines 1209-1211):
  ```python
  if __name__ == '__main__':
      frame = InkyPhotoFrame()
      frame.run()
  ```

**Classes:**
- `DisplayManager` (lines 166-227): Singleton pattern via `__new__` override for GPIO/SPI lifecycle management
- `ButtonController` (lines 263-336): Composition-based, receives `photo_frame` instance in constructor
- `PhotoHandler` (lines 341-396): Extends `watchdog.FileSystemEventHandler`, uses timer debouncing
- `InkyPhotoFrame` (lines 397-1207): Main controller (~800 lines), owns all business logic

**Module-level constants (lines 58-150):**
- Grouped semantically: paths, timing, color configuration, display configurations
- `DISPLAY_CONFIGS` dict provides structured display type definitions with nested config:
  ```python
  DISPLAY_CONFIGS = {
      'spectra_7.3': {
          'name': '...',
          'resolution': (800, 480),
          'is_spectra': True,
          'gpio_pins': {'button_a': 5, ...},
          'detection': {'module_contains': 'e673'},
      },
      ...
  }
  ```

## Decorator Usage

**Custom `@retry_on_error` decorator (`inky_photo_frame.py` lines 229-257):**
- Implements exponential backoff for GPIO/SPI resilience
- Applied to `display_photo()` via `@retry_on_error(max_attempts=3, delay=1, backoff=2)` at line 877
- Uses `@wraps(func)` to preserve function metadata

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
- `threading.Lock()` instance: `self.lock = threading.Lock()` (`inky_photo_frame.py` line 434)
- All history mutations wrapped in `with self.lock:` context manager
- Timer-based debouncing for file system events: `threading.Timer(3.0, self.process_uploads)` (line 366)
- Button handlers use local `self.busy` boolean flag to prevent re-entrant presses during display refresh
- `DisplayManager` uses its own `self._lock = threading.Lock()` for singleton initialization safety

## Shell Script Conventions

**Files:** `install.sh`, `update.sh`, `uninstall.sh`, `diagnostic_report.sh`, `inky-photo-frame-cli`

**Style:**
- `set -e` at top of critical scripts (`install.sh`, `update.sh`) — exit on any error
- ANSI color variables defined at top: `RED`, `GREEN`, `YELLOW`, `BLUE`, `NC`
- Helper print functions: `print_status()`, `print_error()`, `print_info()` (consistent across all scripts)
- Heredoc syntax used for multi-line content and systemd unit file generation
- Variables in `UPPER_SNAKE_CASE`: `INSTALL_DIR`, `SERVICE_NAME`, `GITHUB_RAW`
- Arrays for file lists: `FILES_TO_UPDATE=("file1" "file2")`
- Case statement for CLI dispatch in `inky-photo-frame-cli`

---

*Convention analysis: 2026-02-22*
