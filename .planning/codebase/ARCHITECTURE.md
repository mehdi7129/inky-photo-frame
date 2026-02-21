# Architecture

**Analysis Date:** 2026-02-22

## Pattern Overview

**Overall:** Monolithic Photo Slideshow Engine with Singleton Display Management

**Key Characteristics:**
- Single-threaded main loop with asynchronous file system monitoring
- Singleton pattern for hardware display management (GPIO/SPI)
- Event-driven architecture for file system changes and button presses
- Layered color management with multiple processing pipelines
- State persistence via JSON history files

## Layers

**Hardware Abstraction Layer (HAL):**
- Purpose: Isolate Inky display hardware from application logic
- Location: `DisplayManager` class in `inky_photo_frame.py` (lines 166-228)
- Contains: GPIO/SPI initialization, display lifecycle management
- Depends on: `inky.auto` library (auto-detection), `gpiozero` for button input
- Used by: All photo display operations

**Input Controller Layer:**
- Purpose: Handle user input from physical GPIO buttons and file system events
- Location: `ButtonController` class (lines 263-336), `PhotoHandler` class (lines 341-395)
- Contains: Button debouncing logic, upload detection, event routing
- Depends on: `gpiozero.Button`, `watchdog.observers`, display manager
- Used by: Main loop's event queue

**Photo Management Layer:**
- Purpose: Photo discovery, caching, history tracking, storage cleanup
- Location: Core methods in `InkyPhotoFrame` class:
  - `get_all_photos()` (lines 641-650)
  - `cleanup_old_photos()` (lines 652-716)
  - `refresh_pending_list()` (lines 718-751)
  - History persistence (lines 612-639)
- Contains: File scanning, storage management, rotation logic
- Depends on: File system, JSON history file
- Used by: Photo change routines

**Image Processing Pipeline:**
- Purpose: Transform images for e-ink display with multiple color modes
- Location: `process_image()` method (lines 821-875) and color processors:
  - `_apply_spectra_palette()` (lines 753-792)
  - `_apply_warmth_boost()` (lines 794-819)
- Contains: Cropping, resizing, color space transformations, dithering
- Depends on: Pillow (PIL), color configuration
- Used by: Display photo operations

**Display Engine:**
- Purpose: Coordinate photo processing and hardware display updates
- Location: `display_photo()` method (lines 877-906) decorated with retry logic
- Contains: Retry mechanisms, saturation management, error handling
- Depends on: Image processing pipeline, DisplayManager singleton
- Used by: Photo change operations, button actions

**Application State Manager:**
- Purpose: Track display state, history, current/pending/shown photos
- Location: `InkyPhotoFrame.__init__()` (lines 398-448) and history methods
- Contains: Color mode persistence, photo queues, metadata tracking
- Depends on: File system (`.inky_history.json`, `.inky_color_mode.json`, `.inky_credentials`)
- Used by: All state-dependent operations

**Schedule & Maintenance:**
- Purpose: Periodic tasks - photo changes, welcome screens, storage cleanup
- Location: Main loop in `run()` method (lines 1144-1207)
- Contains: Time-based scheduling, observer health checks, cleanup triggers
- Depends on: System time, file watcher
- Used by: Background operations

## Data Flow

**Photo Display Flow:**

1. User action (button press) or scheduled time triggers
2. `next_photo()`, `change_photo()`, or `display_new_photo()` called
3. Photo path resolved from pending queue
4. `process_image()` applies cropping + color processing
5. `display_photo()` with retry decorator sends to DisplayManager
6. `display.set_image()` applies saturation and renders
7. History updated: photo moved from pending→current or current→shown
8. JSON history persisted to disk

**File Upload Flow:**

1. `PhotoHandler.on_created()` triggered by watchdog
2. File validated as image extension
3. Timer set for 3-second debounce (handles multi-file uploads)
4. `process_uploads()` executes:
   - Last uploaded photo displayed immediately
   - Other photos added to pending queue for daily rotation

**Color Mode Lifecycle:**

1. Startup: `load_color_mode()` reads saved preference from `.inky_color_mode.json`
2. Display detection: `detect_display_saturation()` selects saturation per mode
3. Processing: Corresponding filter applied based on mode (pimoroni/spectra_palette/warmth_boost)
4. Button C: `cycle_color_mode()` rotates modes, updates file, re-displays current
5. Button D: `reset_color_mode()` forces pimoroni, updates file, re-displays

**State Management:**

```
History state: {
  'shown': [...],         # Photos already displayed (for prev button)
  'pending': [...],       # Photos queued for next changes
  'current': path,        # Currently displayed photo
  'last_change': ISO8601, # Timestamp of last photo change
  'photo_metadata': {     # New: when photo added, size, display count
    path: { added_at, size_bytes, displayed_count }
  }
}
```

## Key Abstractions

**Display Configuration:**
- Purpose: Auto-detect display model and provide hardware-specific parameters
- Examples: `DISPLAY_CONFIGS` (lines 103-150) - Spectra 7.3", Classic 7.3", Spectra 13.3"
- Pattern: Config dict with detection rules (module/class/resolution), GPIO pins, color handling

**Color Mode Profiles:**
- Purpose: Encapsulate different color transformation strategies
- Examples: `SPECTRA_PALETTE` (lines 81-88), `WARMTH_BOOST_CONFIG` (lines 91-97)
- Pattern: Named tuples of RGB values or enhancement factors

**Retry Decorator:**
- Purpose: Make display operations resilient to transient GPIO/SPI errors
- Examples: `@retry_on_error(max_attempts=3, delay=1, backoff=2)` (lines 877)
- Pattern: Exponential backoff on recoverable errors (GPIO, SPI, transport)

**Threading Primitives:**
- Purpose: Protect shared state from concurrent modification
- Examples: `self.lock = threading.Lock()` (line 434)
- Pattern: Acquire lock in methods that modify `self.history` or `self.display_config`

## Entry Points

**Main Process:**
- Location: `inky_photo_frame.py` (lines 1209-1211)
- Triggers: `python3 inky_photo_frame.py` or systemd service
- Responsibilities: Create `InkyPhotoFrame` instance, call `run()`

**CLI Wrapper:**
- Location: `/usr/local/bin/inky-photo-frame` script
- Triggers: User command `inky-photo-frame [command]`
- Responsibilities: Delegate to systemd service (restart, stop, status), show logs, update

**Display Welcome Screen:**
- Location: `display_welcome()` method (lines 534-610)
- Triggers: Startup when no photos, or hourly if pending becomes empty
- Responsibilities: Render connection info, SMB credentials, file access instructions

**Boot Integration:**
- Location: systemd service (installed via `install.sh`)
- Triggers: System startup (configured by install script)
- Responsibilities: Run as daemon, auto-restart on crash

## Error Handling

**Strategy:** Graceful degradation with logging

**Patterns:**

1. **Display Initialization Errors:**
   - Caught in `DisplayManager.initialize()` (lines 205-207)
   - Logged and re-raised to prevent start
   - Ensures fail-fast if hardware unconfigured

2. **GPIO Button Errors:**
   - Caught in `ButtonController.__init__()` (lines 298-299)
   - Logged as warning but don't stop application
   - Allows operation without buttons if GPIO unavailable

3. **Photo Processing Errors:**
   - Caught in `display_photo()` (lines 904-906)
   - Returns False to indicate failure
   - Retried up to 3 times with exponential backoff (decorator)

4. **File System Errors:**
   - Caught in `process_uploads()` (lines 382-392)
   - Photo added to queue on error, doesn't stop watcher
   - File watcher restarts if crashes (line 1193-1198)

5. **Credentials/Config Errors:**
   - Caught with fallback defaults
   - `get_credentials()` falls back to hardcoded defaults (lines 531-532)
   - `load_color_mode()` falls back to COLOR_MODE constant (line 1082)

6. **History Corruption:**
   - Caught in `load_history()` (line 619)
   - Auto-migrates to new format with metadata if old format detected

## Cross-Cutting Concerns

**Logging:**
- Framework: Python standard `logging` module
- Config: `basicConfig()` (lines 153-160) writes to both file and stdout
- Pattern: Contextual prefixes for status (✅ ❌ ⚠️ 🎨 📺 ⏰) for readability

**Validation:**
- File extensions: Whitelist in `PhotoHandler.image_extensions` (line 345)
- GPIO pins: Validated in `ButtonController` constructor
- Config auto-detection: Fallback unknown display config (lines 483-496)

**Authentication:**
- SMB credentials: Read from `.inky_credentials` file
- Dynamic: Can be reset via `inky-photo-frame reset-password` command
- Welcome screen displays credentials for first-time setup

**Thread Safety:**
- Lock usage: `self.lock = threading.Lock()` guards history modifications
- Acquainted in: `change_photo()`, `next_photo()`, `cleanup_old_photos()`, `display_new_photo()`
- Observer threads: File watcher runs in separate thread, uses queue mechanism via `PhotoHandler`

**Scheduling:**
- Daily mode: Check `should_change_photo()` (lines 1095-1120) every 60 seconds
- Interval mode: Same check but with configurable CHANGE_INTERVAL_MINUTES
- Maintenance: Cleanup every 6 hours (line 1187), refresh every hour (line 1177)

---

*Architecture analysis: 2026-02-22*
