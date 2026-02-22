# Architecture

**Analysis Date:** 2026-02-22

## Pattern Overview

**Overall:** Monolithic Photo Slideshow Engine with Singleton Display Management

**Key Characteristics:**
- Single Python file (`inky_photo_frame.py`, 1,211 lines) containing all application logic
- Singleton pattern for hardware display management (GPIO/SPI) via `DisplayManager`
- Event-driven architecture: file system events (watchdog) and GPIO button presses run in threads
- Main loop is single-threaded, sleeping 60 seconds between schedule checks
- State persisted entirely as JSON files on disk (no database)
- Scheduled for modularization into a Python package as part of v2.0 (Phase 3)

## Layers

**Hardware Abstraction Layer (HAL):**
- Purpose: Isolate Inky display hardware from application logic
- Location: `DisplayManager` class in `inky_photo_frame.py` (lines 166-228)
- Contains: GPIO/SPI initialization, display lifecycle management, signal cleanup
- Depends on: `inky.auto` library (auto-detection), `gpiozero` for button input
- Used by: All photo display operations

**Input Controller Layer:**
- Purpose: Handle user input from physical GPIO buttons and file system events
- Location: `ButtonController` class (lines 263-336), `PhotoHandler` class (lines 341-395)
- Contains: Button debouncing (20ms via gpiozero), upload detection with 3-second debounce timer, event routing
- Depends on: `gpiozero.Button`, `watchdog.observers`, `DisplayManager`
- Used by: `InkyPhotoFrame` main class

**Photo Management Layer:**
- Purpose: Photo discovery, history tracking, rotation logic, storage cleanup
- Location: Core methods in `InkyPhotoFrame` class:
  - `get_all_photos()` (lines 641-650)
  - `cleanup_old_photos()` (lines 652-716)
  - `refresh_pending_list()` (lines 718-751)
  - History persistence: `load_history()` / `save_history()` (lines 612-639)
- Contains: File scanning with glob, FIFO storage management, cycle-reset logic (when all shown, shuffle and restart)
- Depends on: File system, `HISTORY_FILE` JSON
- Used by: Photo change routines and the main loop

**Image Processing Pipeline:**
- Purpose: Transform images for e-ink display using multiple configurable color modes
- Location: `process_image()` method (lines 821-875) and color mode processors:
  - `_apply_spectra_palette()` (lines 753-792): Floyd-Steinberg dithering to 6-color palette
  - `_apply_warmth_boost()` (lines 794-819): Per-channel RGB brightness adjustments
- Contains: Smart crop (aspect-ratio preserving, portrait-biased), LANCZOS resize, RGBA→RGB conversion
- Depends on: Pillow (PIL), `SPECTRA_PALETTE` / `WARMTH_BOOST_CONFIG` constants
- Used by: `display_photo()` method

**Display Engine:**
- Purpose: Coordinate image processing and hardware display updates with resilience
- Location: `display_photo()` method (lines 877-906), decorated with `@retry_on_error`
- Contains: Retry with exponential backoff (up to 3 attempts), saturation parameter handling, display count tracking
- Depends on: Image processing pipeline, `DisplayManager` singleton
- Used by: All photo change operations and button actions

**Application State Manager:**
- Purpose: Track display state, history queues, color mode, photo metadata
- Location: `InkyPhotoFrame.__init__()` (lines 398-448) and JSON persistence methods
- Contains: Color mode persistence, photo queues (shown/pending/current), metadata per photo
- Depends on: File system — `/home/pi/.inky_history.json`, `/home/pi/.inky_color_mode.json`, `/home/pi/.inky_credentials`
- Used by: All state-dependent operations

**Schedule and Maintenance:**
- Purpose: Periodic tasks — photo changes, hourly welcome screen check, 6-hour storage cleanup
- Location: Main loop in `run()` method (lines 1144-1207)
- Contains: Time-based scheduling, observer health checks with auto-restart, 60-second polling
- Depends on: System time (`datetime`), file watcher (`watchdog.Observer`)
- Used by: Background operations only (no external callers)

## Data Flow

**Photo Display Flow:**

1. Button press (GPIO) or scheduled time (`should_change_photo()` returns True)
2. `next_photo()`, `change_photo()`, or `display_new_photo()` called
3. Photo path resolved from `self.history['pending']` queue
4. `process_image()` loads PIL Image, crops to display ratio, resizes to display resolution
5. Color mode applied: `pimoroni` (no-op), `spectra_palette` (quantize+dither), `warmth_boost` (channel adjust)
6. `display_photo()` with `@retry_on_error` sends processed image to `DisplayManager`
7. `display.set_image(img, saturation=self.saturation)` and `display.show()` called
8. History updated atomically under `self.lock`: photo moves pending→current, previous current→shown
9. JSON history persisted to `/home/pi/.inky_history.json`

**File Upload Flow:**

1. `PhotoHandler.on_created()` triggered by watchdog observer thread
2. File extension validated against `{'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic'}`
3. Path added to `self.pending_photos` list
4. 3-second debounce timer started (cancels any previous timer)
5. `process_uploads()` fires after 3 seconds:
   - Last uploaded photo displayed immediately via `display_new_photo()`
   - All other photos added to pending queue via `add_to_queue()`
6. `self.pending_photos` cleared

**Color Mode Lifecycle:**

1. Startup: `load_color_mode()` reads `/home/pi/.inky_color_mode.json`, falls back to `COLOR_MODE` constant
2. Display detection: `detect_display_saturation()` returns saturation value per current mode
3. Processing: Corresponding filter in `process_image()` selected by `self.color_mode` string
4. Button C press: `cycle_color_mode()` rotates pimoroni → spectra_palette → warmth_boost → pimoroni
5. Save: `save_color_mode()` persists new mode to JSON
6. Re-render: Current photo redisplayed with new mode

**State Management:**

```
History state (persisted to /home/pi/.inky_history.json):
{
  'shown':        [str, ...],   # Photos already displayed (stack for prev button)
  'pending':      [str, ...],   # Photos queued for next changes (shuffled)
  'current':      str | None,   # Currently displayed photo path
  'last_change':  str | None,   # ISO-8601 timestamp of last change
  'photo_metadata': {           # Metadata per known photo
    path: {
      'added_at': str,          # ISO-8601 when photo was first seen
      'size_bytes': int,
      'displayed_count': int
    }
  }
}
```

**Scheduling Logic:**

```
CHANGE_INTERVAL_MINUTES == 0 (daily mode):
  → Change once per day at CHANGE_HOUR (5 AM)
  → Check: now.hour >= 5 AND last_change.date < today

CHANGE_INTERVAL_MINUTES > 0 (interval mode):
  → Change every N minutes
  → Check: (now - last_change).seconds / 60 >= CHANGE_INTERVAL_MINUTES
```

## Key Abstractions

**Display Configuration Dict:**
- Purpose: Auto-detect display model and provide hardware-specific parameters (GPIO pins, resolution, Spectra flag)
- Location: `DISPLAY_CONFIGS` constant (lines 103-150) in `inky_photo_frame.py`
- Keys: `spectra_7.3`, `classic_7.3`, `spectra_13.3`
- Each entry has: `name`, `resolution`, `is_spectra`, `is_13inch`, `gpio_pins`, `detection` (rules for matching)
- Used by: `detect_display_saturation()` and `ButtonController`

**Color Mode Profiles:**
- Purpose: Encapsulate different color transformation strategies as named constants
- `SPECTRA_PALETTE` (lines 81-88): 6 calibrated RGB tuples for Spectra e-ink
- `WARMTH_BOOST_CONFIG` (lines 91-97): Enhancement multipliers (red_boost, green_reduce, blue_reduce, brightness, saturation)
- Pattern: Config dicts selected at runtime by `self.color_mode` string

**Retry Decorator:**
- Purpose: Make display operations resilient to transient GPIO/SPI errors
- Location: `retry_on_error()` (lines 229-257) in `inky_photo_frame.py`
- Applied to: `display_photo()` with `max_attempts=3, delay=1, backoff=2`
- Pattern: Exponential backoff; only retries recoverable errors (GPIO, SPI, transport, endpoint, busy)

**Threading Lock:**
- Purpose: Protect shared `self.history` dict from concurrent modification by button/watchdog threads
- Location: `self.lock = threading.Lock()` (line 434)
- Acquired in: `change_photo()`, `next_photo()`, `previous_photo()`, `cleanup_old_photos()`, `display_new_photo()`, `add_to_queue()`

## Entry Points

**Main Process:**
- Location: `inky_photo_frame.py` (lines 1209-1211)
- Triggers: `python3 inky_photo_frame.py` or systemd service ExecStart
- Responsibilities: Instantiate `InkyPhotoFrame`, call `run()`

**Systemd Service:**
- Location: `/etc/systemd/system/inky-photo-frame.service` (installed by `install.sh`)
- Triggers: System boot (WantedBy=multi-user.target), auto-restart on crash (Restart=always, RestartSec=10)
- ExecStart: `/home/pi/.virtualenvs/pimoroni/bin/python /home/pi/inky-photo-frame/inky_photo_frame.py`

**CLI Wrapper:**
- Location: `inky-photo-frame-cli` (source), `/usr/local/bin/inky-photo-frame` (installed)
- Triggers: User command `inky-photo-frame [command]`
- Responsibilities: Delegate to systemd (start/stop/restart/status/logs), trigger `update.sh`, reset SMB password

**Welcome Screen:**
- Location: `display_welcome()` method (lines 534-610) in `inky_photo_frame.py`
- Triggers: Startup with no photos, or hourly maintenance when photo directory is empty
- Responsibilities: Render SMB IP address, credentials, device-specific connection instructions

## Error Handling

**Strategy:** Graceful degradation with logging — failures in optional components (buttons, HEIC) never stop the core display loop.

**Patterns:**

1. **Display Initialization Errors** (lines 205-207):
   - Caught in `DisplayManager.initialize()`
   - Logged and re-raised — fail fast if hardware unconfigured

2. **GPIO Button Errors** (lines 298-299):
   - Caught in `ButtonController.__init__()`
   - Logged as warning, `button_controller` set to None
   - Application runs without buttons if GPIO unavailable

3. **Photo Processing Errors** (lines 904-906):
   - `display_photo()` returns False on failure
   - `@retry_on_error` retries GPIO/SPI errors up to 3 times with exponential backoff

4. **File System Event Errors** (lines 382-392):
   - Caught in `PhotoHandler.process_uploads()`
   - Error logged, photo processing continues
   - File watcher self-heals in main loop (lines 1193-1198) if observer dies

5. **Config/Credential Errors** (lines 531-532, line 1082):
   - `get_credentials()` falls back to hardcoded defaults
   - `load_color_mode()` falls back to `COLOR_MODE` constant

6. **History Format Migration** (line 619):
   - `load_history()` auto-migrates old format (missing `photo_metadata` key) on load

## Cross-Cutting Concerns

**Logging:**
- Framework: Python standard `logging` module
- Config: `basicConfig()` (lines 153-160) — dual handler: `FileHandler` (`/home/pi/inky_photo_frame.log`) + `StreamHandler` (stdout)
- Pattern: Emoji prefixes for readability (✅ ❌ ⚠️ 🎨 📺 ⏰ 📸)
- Rotation: `/etc/logrotate.d/inky-photo-frame` (daily, 7-day retention, compress)

**Validation:**
- File extensions: Whitelist in `PhotoHandler.image_extensions` (line 345): `{'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.heic'}`
- Display model: Auto-detection in `detect_display_saturation()` with fallback unknown config

**Authentication:**
- SMB credentials stored in `/home/pi/.inky_credentials` (plain text, line 1 = username, line 2 = password)
- Reset via: `inky-photo-frame reset-password` generates 10-char random alphanumeric password
- Welcome screen reads and displays credentials via `get_credentials()`

**Thread Safety:**
- `self.lock` (threading.Lock) guards all writes to `self.history`
- File watcher (`watchdog.Observer`) runs in daemon thread
- Button handlers run in gpiozero event threads
- Timer in `PhotoHandler` uses `threading.Timer` (daemon)

**Scheduling:**
- Main loop polls every 60 seconds via `time_module.sleep(60)`
- Hourly: `refresh_pending_list()` and optional welcome screen check (line 1177)
- Every 6 hours: `cleanup_old_photos()` with FIFO deletion (line 1187)
- Daily at `CHANGE_HOUR` (or every `CHANGE_INTERVAL_MINUTES` if >0): photo change

## Planned v2.0 Package Structure

Per `ROADMAP.md` Phase 3 (Module Extraction), the monolith will be split into:

```
inky_photo_frame/       # New package directory
├── __init__.py
├── __main__.py         # python -m inky_photo_frame
├── config.py           # All constants and DISPLAY_CONFIGS
├── display.py          # DisplayManager singleton
├── image_processor.py  # process_image(), _apply_spectra_palette(), _apply_warmth_boost()
├── photos.py           # InkyPhotoFrame photo management methods
├── buttons.py          # ButtonController
├── welcome.py          # display_welcome()
└── app.py              # InkyPhotoFrame orchestrator (run loop)

inky_photo_frame.py     # 3-line shim (backward compat for systemd ExecStart)
```

The systemd service's `ExecStart` path (`inky_photo_frame.py`) does not change — the shim preserves it.

---

*Architecture analysis: 2026-02-22*
