# Codebase Concerns

**Analysis Date:** 2026-02-22

## Tech Debt

**Bare Exception Handling:**
- Issue: Multiple locations use bare `except:` clauses without exception type specification
- Files: `inky_photo_frame.py` (lines 518, 548)
- Impact: Masks unexpected errors, makes debugging difficult, can hide resource leaks
- Fix approach: Replace with specific exception types (`except Exception as e:`, `except OSError as e:`, etc.)

**Incomplete Error Message in IP Address Fallback:**
- Issue: `get_ip_address()` returns hardcoded fallback instead of handling actual connection failure
- Files: `inky_photo_frame.py` (line 519)
- Impact: Users will see incorrect IP if network connection fails
- Fix approach: Log the actual connection error and provide better fallback messaging

**Direct File Access Without Validation:**
- Issue: `get_credentials()` reads credentials file without validating file integrity
- Files: `inky_photo_frame.py` (lines 523-532)
- Impact: Malformed credentials file crashes welcome screen display; no graceful degradation
- Fix approach: Add JSON/format validation and return defaults on any parse error

**String-Based Error Detection in Retry Logic:**
- Issue: `retry_on_error` decorator checks error messages with string matching (line 243)
- Files: `inky_photo_frame.py` (lines 243-245)
- Impact: Fragile - new error types may not be recognized; maintenance burden as error messages change in libraries
- Fix approach: Catch specific exception types instead of parsing error strings

**Hard-Coded Paths and Configuration:**
- Issue: All paths are hard-coded to `/home/pi/` directories
- Files: `inky_photo_frame.py` (lines 59-66), `install.sh`, `update.sh`
- Impact: Non-portable; fails on non-standard Pi installations; incompatible with different users
- Fix approach: Use environment variables or configuration files for installation paths

**Missing Validation for Display Configuration:**
- Issue: `detect_display_saturation()` creates minimal fallback config without logging resolution properly
- Files: `inky_photo_frame.py` (lines 483-496)
- Impact: Unknown displays get wrong GPIO pin assignments silently; buttons may fail without diagnostic
- Fix approach: Log warning with actual resolution and suggest reporting issue

## Known Bugs

**File Watcher Observer Restart Without Event Handler Update:**
- Symptoms: File watcher restarts but continues using old event handler instance
- Files: `inky_photo_frame.py` (line 1195)
- Trigger: Observer dies (rare but happens after extended uptime or system events)
- Workaround: Service restart required; automatic restart by systemd applies temporary fix
- Root cause: `observer.start()` is called with old `event_handler` object that may have stale state

**History File Race Condition:**
- Symptoms: "displayed_count" metadata may not be synchronized on rapid photo changes
- Files: `inky_photo_frame.py` (lines 898-901)
- Trigger: Rapid button presses during display refresh cycle
- Workaround: Button busy flag prevents issue in practice
- Root cause: Lock only protects the history update, not the entire display operation

**Potential HEIF Import Silent Failure:**
- Symptoms: HEIF support claimed in logs but module import failure is logged only at INFO level
- Files: `inky_photo_frame.py` (lines 420-425)
- Trigger: pillow-heif not installed despite being in requirements
- Workaround: HEIF files still process via PIL fallback
- Root cause: ImportError on optional dependency not escalated; no fallback for HEIF-specific file types

## Security Considerations

**Credentials File Stored in Plain Text:**
- Risk: `/home/pi/.inky_credentials` stores SMB password in plain text with chmod 644 (world-readable)
- Files: `install.sh` (line 236), `inky_photo_frame.py` (lines 523-532), `inky-photo-frame-cli` (line 151)
- Current mitigation: File only readable by local filesystem; password displayed on e-ink only at setup
- Recommendations:
  - Store credentials with chmod 600 (owner-read-only)
  - Use SMB credential store/keyring instead of custom file
  - Rotate password automatically on first boot after installation

**Hardcoded GPIO Skip Environment Variable:**
- Risk: `INKY_SKIP_GPIO_CHECK = '1'` set at module load (line 32) to skip hardware validation
- Files: `inky_photo_frame.py` (line 32)
- Current mitigation: Only affects development mode; not ideal for production
- Recommendations: Make this configurable via environment or config file with explicit opt-in

**SMB Share Allows Anonymous-Like Access:**
- Risk: `valid users` and `write list` include both `inky` and `pi` users; `force user = pi` applies blanket permissions
- Files: `install.sh` (lines 199-201)
- Current mitigation: Network-only access; firewall should restrict LAN access
- Recommendations:
  - Document requirement for trusted network only
  - Add per-share authentication instead of force_user
  - Consider restricting SMB to local network only

**No Input Validation on Photo Files:**
- Risk: `get_all_photos()` trusts all files with image extensions; no format/signature validation
- Files: `inky_photo_frame.py` (lines 641-650)
- Current mitigation: PIL will fail gracefully on corrupt files; exception caught in display_photo
- Recommendations:
  - Add file magic number validation
  - Quarantine corrupt images instead of skipping silently
  - Log suspicious file types

## Performance Bottlenecks

**Blocking Image Processing in Main Loop:**
- Problem: `process_image()` runs synchronously in display_photo; blocks event loop during color processing
- Files: `inky_photo_frame.py` (lines 821-875, 878-906)
- Cause: PIL operations (color mapping, dithering, resizing) are CPU-intensive (100-300ms on Pi Zero)
- Current impact: E-ink refresh ~30-40s dominant; processing ~100-300ms is secondary
- Improvement path:
  - Pre-process images in background thread when added to queue
  - Cache processed images with versioning by color mode
  - Defer color processing until display time only for current photo

**History File Rewritten on Every Photo Change:**
- Problem: `save_history()` dumps entire history JSON to disk on every photo change
- Files: `inky_photo_frame.py` (lines 634-639)
- Cause: No incremental update; full write with indent=2 for readability
- Current impact: ~10-50ms disk I/O per change; negligible on modern SD cards
- Improvement path:
  - Track changes and write only diffs
  - Use binary format for large histories (>10k photos)
  - Batch writes to reduce I/O frequency

**Linear Search in Cleanup and Refresh:**
- Problem: `cleanup_old_photos()` and `refresh_pending_list()` scan all photos on every operation
- Files: `inky_photo_frame.py` (lines 652-716, 718-751)
- Cause: File system glob and metadata lookups are O(n)
- Current impact: Negligible for <1000 photos; would be slow at MAX_PHOTOS limit
- Improvement path:
  - Cache pending/shown lists in memory
  - Index metadata by path for O(1) lookups
  - Lazy load metadata on demand

**Display Saturation Recalculated on Every Photo:**
- Problem: `detect_display_saturation()` runs during `__init__` but logic could be cached
- Files: `inky_photo_frame.py` (lines 450-508)
- Cause: Saturation varies by color_mode which can change at runtime
- Current impact: Negligible; called only at startup and color mode change
- Improvement path: Cache per color_mode; invalidate only on mode change

## Fragile Areas

**Button Controller GPIO Initialization:**
- Files: `inky_photo_frame.py` (lines 263-299)
- Why fragile:
  - GPIO pins are hardware-specific and detected at runtime
  - `gpiozero.Button` initialization can fail silently (line 298 catches all exceptions)
  - No per-button error handling; single failed pin initialization prevents all buttons
  - Dependencies (lgpio, RPi.GPIO) may not be installed despite being in requirements
- Safe modification:
  - Add per-button try/except with individual error logging
  - Fall back to minimal GPIO support (buttons not available) instead of all-or-nothing
  - Test each GPIO pin before assigning to button
- Test coverage: Basic import test exists; no integration test for actual button presses

**Display Detection and Configuration:**
- Files: `inky_photo_frame.py` (lines 450-508)
- Why fragile:
  - Multi-level detection logic (module → class → resolution) with fallback
  - Unknown displays silently get wrong GPIO pin assignments (line 485)
  - Resolution tuple comparison may fail if dimensions don't exactly match
  - No validation that detected pins are actually connected to buttons
- Safe modification:
  - Add explicit error logging when falling back to default config
  - Validate pin detection against actual gpiozero initialization
  - Document the detection logic explicitly
- Test coverage: Only implicit through button tests

**File System Event Handler Timing:**
- Files: `inky_photo_frame.py` (lines 341-395)
- Why fragile:
  - 3-second timer (line 366) is arbitrary; uploads faster than 3s will show only last file
  - No verification that file is fully written before processing
  - Duplicate uploads within 3s window discarded (line 373-374)
  - Timer cancellation (line 363) happens before new file arrives - race condition possible
- Safe modification:
  - Implement file lock detection (check if file is still being written)
  - Increase timer or use file size stability check
  - Queue all uploads with metadata, display immediately only if timer expires
- Test coverage: No automated tests for file watcher behavior

**Color Mode Persistence and Compatibility:**
- Files: `inky_photo_frame.py` (lines 1071-1093)
- Why fragile:
  - Color mode stored as plain text JSON in /home/pi/.inky_color_mode.json
  - No validation that stored mode is valid (corrupt file crashes on load)
  - Mode switching calls `display_photo()` with retry decorator but doesn't catch display errors
  - Spectra-only modes used on non-Spectra displays cause silent no-op
- Safe modification:
  - Validate color_mode against known modes before applying
  - Handle display errors in color mode switching
  - Check `self.is_spectra` before allowing Spectra-specific modes
- Test coverage: Manual testing only; no automated mode switching tests

**Observer Restart Without Guarantee:**
- Files: `inky_photo_frame.py` (lines 1192-1198)
- Why fragile:
  - Check `observer.is_alive()` is not guaranteed to detect hangs
  - Restart happens every 60 seconds but timing is coupled to main loop
  - No exponential backoff if observer repeatedly fails to start
  - Old event handler instance reused with new observer (state pollution)
- Safe modification:
  - Create new PhotoHandler instance on observer restart
  - Track consecutive restart failures and increase checks
  - Add health check beyond just `is_alive()` (e.g., periodic file creation test)
- Test coverage: No automated tests for observer lifecycle

## Scaling Limits

**Photo History Lists Unbounded Growth:**
- Current capacity: Starts at 0, grows with every photo change
- Limit: 'shown' list could grow to 1000+ photos; no pruning
- Impact: History file grows ~500 bytes per photo; at 1000 photos = 500KB
- Scaling path:
  - Prune shown list when it exceeds MAX_PHOTOS
  - Archive old history entries separately
  - Implement rolling window (keep last N days only)

**Metadata Dictionary Growth:**
- Current capacity: One entry per photo; currently unbounded
- Limit: ~200 bytes metadata per photo × 1000 photos = 200KB
- Impact: Memory usage grows; history file grows
- Scaling path:
  - Implement metadata pruning when photos are deleted
  - Consider database (SQLite) for >10,000 photos
  - Archive old metadata to separate file

**File System Watching at Single Directory Level:**
- Current capacity: Watches /home/pi/Images only (not recursive)
- Limit: inotify can handle ~1000s of files; observer efficiency depends on FS
- Impact: First scan of 1000 photos is slow; incremental adds are fast
- Scaling path:
  - Profile file watcher performance at high photo counts
  - Consider pagination or directory sharding for >5000 photos

**Pending Queue Processing:**
- Current capacity: All photos in pending list loaded and shuffled in memory
- Limit: Max 1000 photos (MAX_PHOTOS); all shuffled at startup
- Impact: ~1000 shuffles × 100 bytes = negligible
- Scaling path: If unlimited photos allowed, implement lazy shuffle or queue

## Dependencies at Risk

**Pimoroni Inky Library Major Version Dependency:**
- Risk: `inky[rpi,example-depends]>=1.5.0` allows major version bumps; API could change
- Impact: New versions might change display initialization or color handling
- Current mitigation: Version constraint prevents pre-1.5.0
- Migration plan:
  - Pin to specific minor version: `inky>=1.5.0,<2.0.0`
  - Monitor GitHub releases for breaking changes
  - Test major version upgrades in staging before deploying

**gpiozero 2.x Pin Factory Fallback Chain:**
- Risk: gpiozero tries lgpio → RPi.GPIO → NativeFactory; fallback is unreliable
- Impact: On systems without lgpio/RPi.GPIO, buttons fail silently
- Current mitigation: Both libraries installed; NativeFactory not used
- Migration plan:
  - Explicitly test pin factory availability before button init
  - Document required system dependencies
  - Consider alternative GPIO library if gpiozero proves unreliable

**Watchdog File Observer Lifecycle:**
- Risk: Observer can hang or become unresponsive; no built-in health checks
- Impact: New photos won't be detected until service restart
- Current mitigation: Manual restart check in main loop (line 1193)
- Migration plan:
  - Implement observer health check with test file
  - Consider alternative: polling instead of inotify (slower but more reliable)
  - Add timeout to observer operations

**Python 3.11+ Deprecated String Formatting:**
- Risk: Code uses older style `f-strings`; no deprecation visible now
- Impact: Future Python versions may deprecate string format methods
- Current mitigation: f-strings are modern Python 3.6+ standard
- Migration plan: Already using modern f-strings; no action needed

## Missing Critical Features

**No Configuration File System:**
- Problem: All settings are hard-coded at top of inky_photo_frame.py
- Blocks: Can't change settings without editing code; can't manage multiple installations
- Files: `inky_photo_frame.py` (lines 58-74)
- Fix approach:
  - Create /home/pi/.inky_config.json for user-overridable settings
  - Load defaults from code, override with JSON config
  - Add CLI command to edit config: `inky-photo-frame config set CHANGE_HOUR 6`

**No Automated Backup of History:**
- Problem: History lost if .inky_history.json corrupted or deleted
- Blocks: Can't recover photo rotation state if file corrupted
- Impact: Users lose photo viewing history; rotation restarts from scratch
- Fix approach:
  - Create daily backups of history file
  - Keep rolling window of last 7 backups
  - Add restore command: `inky-photo-frame restore-history [backup-date]`

**No Photo Metadata Display on E-Ink:**
- Problem: E-ink display only shows photos, no metadata
- Blocks: Users can't see file info, upload time, or storage status
- Impact: Limited information; users don't know if frame is working if display doesn't change
- Fix approach:
  - Add optional metadata overlay (filename, upload date, remaining storage)
  - Make configurable with COLOR_MODE analogy: `DISPLAY_MODE` = metadata_overlay, minimal, full
  - Use smaller fonts to preserve image area

**No Scheduled Photo Deletion or Archiving:**
- Problem: Photos keep accumulating; manual deletion required at MAX_PHOTOS limit
- Blocks: Can't implement time-based rotation (e.g., "keep only photos from last 30 days")
- Impact: Photo collection grows indefinitely until cleanup triggered
- Fix approach:
  - Add photo retention policy: `RETENTION_DAYS = 30`
  - Archive old photos to USB drive or cloud
  - Add command: `inky-photo-frame archive --older-than 30d`

**No Multi-User Support:**
- Problem: All photos stored in single /home/pi/Images directory
- Blocks: Can't support multiple families/users with separate photo collections
- Impact: Family photos mixed together; no privacy
- Fix approach:
  - Support user-scoped photo directories
  - Dynamic SMB share per user
  - Separate history per user

## Test Coverage Gaps

**No Unit Tests for Core Photo Logic:**
- What's not tested: `process_image()`, `change_photo()`, `next_photo()`, `previous_photo()`
- Files: `inky_photo_frame.py` (lines 821-1033)
- Risk: Color processing bugs, history corruption, photo ordering failures go undetected
- Priority: High - these are core features

**No Integration Tests for Button Input:**
- What's not tested: `ButtonController` initialization, button press handling, state updates
- Files: `inky_photo_frame.py` (lines 263-335)
- Risk: GPIO pin assignment errors, button mapping failures silent until user tests
- Priority: High - hardware integration point

**No Tests for File Watcher:**
- What's not tested: `PhotoHandler` file creation detection, timer behavior, upload batching
- Files: `inky_photo_frame.py` (lines 341-395)
- Risk: New files not detected, duplicate processing, race conditions
- Priority: Medium - critical UX feature but covered by manual testing

**No Tests for Display Configuration Detection:**
- What's not tested: `detect_display_saturation()` fallback logic, GPIO pin assignment
- Files: `inky_photo_frame.py` (lines 450-508)
- Risk: Unknown displays silently configured with wrong pins
- Priority: Medium - only affects edge cases

**No Tests for Error Handling and Retry Logic:**
- What's not tested: `@retry_on_error` decorator, exception handling in display_photo
- Files: `inky_photo_frame.py` (lines 229-257, 877-906)
- Risk: Retry logic doesn't work as intended; errors not properly escalated
- Priority: Medium - resilience feature

**No Tests for Storage Cleanup:**
- What's not tested: `cleanup_old_photos()` FIFO deletion, metadata pruning
- Files: `inky_photo_frame.py` (lines 652-716)
- Risk: Photos deleted in wrong order, current photo deleted, metadata corruption
- Priority: Low - covered by manual long-term testing

**No Tests for History File Format Migration:**
- What's not tested: `load_history()` old format to new format conversion
- Files: `inky_photo_frame.py` (lines 612-632)
- Risk: Upgrades from old version lose metadata or crash
- Priority: Low - only affects one-time upgrade path

---

*Concerns audit: 2026-02-22*
