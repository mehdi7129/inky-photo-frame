# Codebase Concerns

**Analysis Date:** 2026-02-22

## Tech Debt

**1100-Line Monolith with No Module Separation:**
- Issue: All application logic lives in a single file `inky_photo_frame.py`. Five distinct responsibilities (display management, button handling, image processing, photo management, scheduling) are deeply coupled.
- Files: `inky_photo_frame.py`
- Impact: Any change to image processing risks breaking button handling; the file is too large to reason about locally; testability is blocked by coupling.
- Fix approach: Extract into `inky_photo_frame/` package as planned in Phase 3 (STRC-01). Keep `inky_photo_frame.py` as a 3-line shim per STRC-02. Do NOT change the systemd `ExecStart` path.

**Module-Level Side Effects on Import:**
- Issue: `logging.basicConfig(...)` runs at import time (lines 153-160), not inside a function or `if __name__ == '__main__'`. `os.environ['INKY_SKIP_GPIO_CHECK'] = '1'` also fires on import (line 32).
- Files: `inky_photo_frame.py` (lines 32, 153-160)
- Impact: When modules are split into a package, every `import` fires these side effects. In CI, this can overwrite the test runner's logging config and pollute test output. If any module-level code eventually calls inky hardware drivers, CI will fail with `FileNotFoundError: /dev/i2c-1`.
- Fix approach: Move `logging.basicConfig(...)` into a `setup_logging()` function called only from the entry point. Leave the `os.environ` line at module level (it guards the import) but document this explicitly.

**DisplayManager Singleton Poisons Test Isolation:**
- Issue: `DisplayManager` uses a class-variable singleton (`_instance = None`). Once initialized in one test, `_instance` persists for the entire test process.
- Files: `inky_photo_frame.py` (lines 166-228)
- Impact: Tests pass individually but fail when run together; mocking `inky.auto.auto` in one test does not reset the singleton for the next test. Test order determines test outcomes.
- Fix approach: Add a `reset()` classmethod and call it in an `autouse` pytest fixture in `conftest.py` (per PITFALLS.md Pitfall 2). Or refactor to dependency injection.

**Bare Exception Handling:**
- Issue: Multiple locations use bare `except:` clauses without specifying an exception type.
- Files: `inky_photo_frame.py` (lines 518, 548)
- Impact: Masks unexpected errors including `KeyboardInterrupt` and `SystemExit`; makes debugging difficult; can hide resource leaks.
- Fix approach: Replace with `except Exception as e:` at minimum; use specific exception types (`OSError`, `IOError`) where the failure mode is known.

**String-Based Error Detection in Retry Decorator:**
- Issue: `retry_on_error` identifies recoverable errors by substring matching on error message strings (lines 242-245): `'gpio', 'spi', 'pins', 'transport', 'endpoint', 'busy'`.
- Files: `inky_photo_frame.py` (lines 229-257)
- Impact: Fragile — any change to upstream library error message text breaks retry detection. New error types are never retried until this list is manually updated.
- Fix approach: Catch specific exception types from `inky` and `gpiozero` instead of parsing string messages.

**Hard-Coded Paths Throughout All Scripts:**
- Issue: `/home/pi/`, `/home/pi/Images`, `/home/pi/.inky_history.json`, `/home/pi/inky-photo-frame`, `/home/pi/.virtualenvs/pimoroni` all hard-coded.
- Files: `inky_photo_frame.py` (lines 59-66), `install.sh` (throughout), `update.sh` (throughout), `inky-photo-frame-cli` (line 7), `uninstall.sh` (throughout)
- Impact: Fails on any non-standard Pi installation; incompatible if the running user is not `pi`; test code cannot avoid writing to `/home/pi/` unless paths are injectable.
- Fix approach: For tests, inject `HISTORY_FILE` and `PHOTOS_DIR` as constructor parameters (use pytest `tmp_path` fixture). For production, keep current approach but document the assumption.

**All Configuration Requires File Editing:**
- Issue: `CHANGE_HOUR`, `CHANGE_INTERVAL_MINUTES`, `MAX_PHOTOS`, `COLOR_MODE` are top-of-file constants. Changing them requires editing `inky_photo_frame.py` directly.
- Files: `inky_photo_frame.py` (lines 59-74)
- Impact: No configuration file system; users must edit Python source to change behavior; CHANGELOG.md even tells users which line to edit ("line ~703").
- Fix approach: Implement a `~/.inky_config.json` overlay loaded at startup (planned as future requirement FEAT-01 area). Out of scope for v2.0 but worth documenting.

**Uninstall Script References Stale Directory:**
- Issue: `uninstall.sh` refers to `/home/pi/InkyPhotos` (old directory name) instead of `/home/pi/Images` (current name used in `install.sh`).
- Files: `uninstall.sh` (lines 25, 68, 72)
- Impact: Uninstall silently fails to remove the photos directory; leaves orphaned data on disk.
- Fix approach: Update `uninstall.sh` to use `/home/pi/Images` consistently. Also, `uninstall.sh` tries to remove `[InkyPhotos]` SMB share section but the actual section is `[Images]`.

**Version Version Numbering Confusion in CHANGELOG:**
- Issue: `CHANGELOG.md` lists "Version 2.0.0 (2025-01-02) - Beta" at the bottom but the current codebase is `VERSION = "1.1.7"`. The current project goal is to reach v2.0 as a planned milestone, not a past release.
- Files: `CHANGELOG.md` (line 255), `inky_photo_frame.py` (line 66)
- Impact: Confusing history; update mechanism parses version from grep, so inconsistency may surface in future tooling.
- Fix approach: Archive the "Beta v2.0" CHANGELOG section or rename it clearly. Per HYGN-04, CHANGELOG.md must be rewritten in Keep a Changelog format.

**`update.sh` Fetches from `main` Branch (Always Latest):**
- Issue: `update.sh` downloads from `https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/$file` — always the tip of `main`.
- Files: `update.sh` (line 10)
- Impact: A broken commit on `main` immediately breaks all new installs and updates for all users. No ability to roll back to the last known-good state without manual intervention.
- Fix approach: Tag releases; download from a tagged release URL. Noted in PITFALLS.md security section. Low priority for MVP but critical for production stability.

**No Validation of Downloaded Files in `update.sh`:**
- Issue: `update.sh` does not verify integrity of downloaded files (no SHA-256 checksum, no signature).
- Files: `update.sh` (lines 75-91)
- Impact: A corrupted or MITM-modified download could silently replace working code. The rollback logic partially mitigates (service start failure triggers rollback), but silent data corruption is not caught.
- Fix approach: Add `sha256sum` verification against a known-good manifest. Low priority for this network-trust model but noted for future.

## Known Bugs

**File Watcher Observer Restart Reuses Stale Event Handler:**
- Symptoms: After the observer is restarted (line 1195), the old `event_handler` instance is reused. If `event_handler` holds state (e.g., `pending_photos` list, active timer), that state is not reset.
- Files: `inky_photo_frame.py` (lines 1192-1198)
- Trigger: Observer dies after extended uptime or OS-level inotify errors.
- Workaround: Service restart via systemd creates fresh state. The observer restart in the main loop is not a full fix.
- Root cause: New `Observer()` is created but not a new `PhotoHandler()`.

**History Race Condition on Rapid Button Presses:**
- Symptoms: `displayed_count` metadata may not synchronize if two button presses fire during display refresh.
- Files: `inky_photo_frame.py` (lines 898-901)
- Trigger: User presses Button A multiple times within the e-ink 15-30 second refresh window.
- Workaround: `ButtonController.busy` flag prevents the second press from calling `next_photo()` during refresh.
- Root cause: `busy` flag only prevents concurrent invocations of `next_photo()`; it doesn't prevent metadata updates racing with the ongoing display operation.

**HEIF Files Detected but Not Processed If `pillow-heif` Not Installed:**
- Symptoms: `.heic` files appear in `get_all_photos()` results (extension in list), but `Image.open()` fails silently if `pillow_heif.register_heif_opener()` was not called (i.e., `pillow-heif` import failed).
- Files: `inky_photo_frame.py` (lines 345, 419-425, 641-650)
- Trigger: `pillow-heif` not installed despite being in `requirements.txt`.
- Workaround: Error caught in `display_photo()` and logged; photo skipped.
- Root cause: `.heic` extension left in `image_extensions` set even when HEIF support is unavailable.

**Observer Health Check Only Tests `is_alive()` — Does Not Detect Hangs:**
- Symptoms: Observer thread may be alive but not processing events (hung on inotify syscall); `is_alive()` returns `True`, no restart triggered.
- Files: `inky_photo_frame.py` (lines 1192-1198)
- Trigger: OS-level inotify failure without thread death; rare but possible under high filesystem load.
- Workaround: Daily 5AM photo change still triggers from scheduler even without file watch events.
- Root cause: No heartbeat or watchdog mechanism beyond thread liveness check.

## Security Considerations

**Credentials File Stored as Plain Text, World-Readable:**
- Risk: `/home/pi/.inky_credentials` stores the SMB password as plain text with `chmod 644` (world-readable to all local users and processes running as any user).
- Files: `install.sh` (lines 233-237), `inky-photo-frame-cli` (line 151), `inky_photo_frame.py` (lines 521-532)
- Current mitigation: File accessible only on local filesystem; password is displayed on e-ink screen at setup (intentional for UX).
- Recommendations:
  - Change to `chmod 600` so only the `pi` user can read it
  - Document the local-network-only trust assumption explicitly
  - Consider using the SMB credential store or system keyring

**SMB Share Uses `force user = pi` — Blanket Privilege Escalation:**
- Risk: All SMB connections, regardless of authenticated user (`inky` or `pi`), write files as `pi`. This conflates authentication identity with filesystem ownership.
- Files: `install.sh` (lines 190-213)
- Current mitigation: Restricted to local network; authenticated users only.
- Recommendations: Document the assumption that this is a trusted home network device. Add firewall rules restricting SMB to LAN only if deploying beyond home use.

**`install.sh` Fetches and Executes Remote Code Over Curl:**
- Risk: The recommended install command `curl -sSL ... | bash` provides no integrity verification. Anyone with access to the GitHub repo (or capable of MITM) can execute arbitrary code as the `pi` user.
- Files: `install.sh` (lines 172-179), README user-facing install instructions
- Current mitigation: GitHub HTTPS provides transport security. No supply chain attack mitigation.
- Recommendations: Provide a checksum for the install script; document this as a trust decision.

**`INKY_SKIP_GPIO_CHECK = '1'` Set at Module Level Unconditionally:**
- Risk: This environment variable skips hardware validation, set unconditionally at import time (line 32). In a production deployment, hardware should be validated.
- Files: `inky_photo_frame.py` (line 32)
- Current mitigation: Required for the `inky` library to initialize without crashing at import when GPIO is not yet fully configured.
- Recommendations: Make configurable; document why it is required and what it bypasses.

**No Input Validation on Uploaded Photo Files:**
- Risk: `get_all_photos()` trusts all files matching image extensions. A crafted file with a `.jpg` extension but malformed content could trigger a PIL parsing vulnerability.
- Files: `inky_photo_frame.py` (lines 641-650)
- Current mitigation: `Image.open()` exceptions caught in `display_photo()`, file skipped on error.
- Recommendations: Add file magic number validation before calling `Image.open()`; quarantine corrupt files with a log entry rather than silently skipping.

## Performance Bottlenecks

**`get_all_photos()` Calls `glob()` Across All Extensions Separately:**
- Problem: Twelve separate `PHOTOS_DIR.glob(ext)` calls in `get_all_photos()` (lines 643-650). Called by `cleanup_old_photos()`, `refresh_pending_list()`, `display_current_or_change()`, and the hourly maintenance check.
- Files: `inky_photo_frame.py` (lines 641-650)
- Cause: Extension list uses both lower and upper variants (`.jpg`, `.JPG`, `.jpeg`, `.JPEG`, etc.) requiring separate glob calls per variant.
- Improvement path: Use `rglob` with a case-insensitive filter, or use `os.scandir()` with a single set membership check on `path.suffix.lower()`. Cache the result for 60 seconds.

**`cleanup_old_photos()` Uses O(n²) `list.remove()` Operations:**
- Problem: `self.history['shown'].remove(photo_path)` and `self.history['pending'].remove(photo_path)` inside cleanup loop (lines 705-706, 708). Python `list.remove()` is O(n); called once per deleted photo.
- Files: `inky_photo_frame.py` (lines 652-716)
- Cause: `shown` and `pending` are stored as lists, not sets. PITFALLS.md confirms this pattern.
- Improvement path: Convert `shown` and `pending` to sets in the history format. Requires history format migration on upgrade. Noted in PITFALLS.md performance traps.

**Blocking Image Processing Runs Synchronously in Main Thread:**
- Problem: `process_image()` including Floyd-Steinberg dithering on 800x480 or 1600x1200 images runs synchronously before `display.show()`.
- Files: `inky_photo_frame.py` (lines 821-875)
- Cause: No pre-processing cache; no background thread for image prep.
- Current impact: 100-300ms on Pi Zero for 800x480; 10-30s for 1600x1200 with spectra_palette mode. E-ink refresh dominates at 15-30s so this is currently acceptable.
- Improvement path: Pre-process next queued image in a background thread while current e-ink refresh is underway. Cache processed image by `(path, color_mode)` key.

**`save_history()` Writes Full JSON on Every Single Photo Change:**
- Problem: Every call to `change_photo()`, `next_photo()`, `previous_photo()`, `display_new_photo()`, and `add_to_queue()` calls `save_history()`, which dumps the entire JSON with `indent=2`.
- Files: `inky_photo_frame.py` (lines 634-639)
- Cause: No dirty-flag or batching mechanism.
- Current impact: ~10-50ms I/O per change. SD card write endurance concern over years of operation.
- Improvement path: Mark history as dirty; flush on a 5-second debounce or on shutdown signal.

## Fragile Areas

**Button Controller GPIO Initialization — All or Nothing:**
- Files: `inky_photo_frame.py` (lines 263-299)
- Why fragile: A single exception in `ButtonController.__init__()` (line 298) prevents ALL buttons from initializing. No per-button isolation. GPIO pins detected from `display_config` without pre-validation. Dependencies (`lgpio`, `RPi.GPIO`) have historically been missing on fresh installs (documented in CHANGELOG v1.1.4 through v1.1.6).
- Safe modification:
  - Add individual `try/except` per button initialization
  - Fall back to available buttons rather than all-or-nothing
  - Validate GPIO pin availability before calling `gpiozero.Button()`
- Test coverage: No automated tests; only manual hardware validation

**Display Auto-Detection Logic — Fallback Assigns Wrong GPIO Pins:**
- Files: `inky_photo_frame.py` (lines 450-508)
- Why fragile: Unknown display models fall through to a default config with GPIO pins 5, 6, 16, 24 (lines 485-495). On a 13.3" display, GPIO 16 is used by the display's CS1 line — assigning button C to GPIO 16 creates a hardware conflict. This is the exact bug fixed by PR #3 (HYGN-01, not yet merged per ROADMAP.md).
- Safe modification:
  - Do not provide a GPIO fallback for unknown displays; log error and disable buttons
  - Add explicit detection test before declaring unknown display
  - Merge PR #3 before any other changes
- Test coverage: No tests for display detection logic

**File System Event Handler — 3-Second Timer is Arbitrary:**
- Files: `inky_photo_frame.py` (lines 341-395)
- Why fragile: The 3-second debounce timer (line 366) assumes all photo uploads complete within 3 seconds. Large HEIC files over slow SMB connections may still be writing at 3 seconds. No file-write-completion check before calling `Image.open()`.
- Safe modification:
  - Use `on_modified` event with file size stability check (read size twice with 1s gap; display only when stable)
  - Or: defer with longer timeout (10 seconds) for large files
- Test coverage: No automated tests for `PhotoHandler` timing behavior

**`load_history()` — No Error Recovery on Corrupt JSON:**
- Files: `inky_photo_frame.py` (lines 612-632)
- Why fragile: `json.load()` called without `try/except` on lines 615-616. A corrupted or truncated `HISTORY_FILE` raises `json.JSONDecodeError` which propagates up through `__init__()` and crashes the service at startup.
- Safe modification:
  - Wrap `json.load()` in `try/except (json.JSONDecodeError, OSError)`
  - Back up the corrupt file and return a fresh empty history
- Test coverage: No test for corrupt history file recovery

**Color Mode Persistence — Invalid Stored Mode Not Validated:**
- Files: `inky_photo_frame.py` (lines 1071-1093)
- Why fragile: `load_color_mode()` reads the stored mode string without validating it against the known modes list (`['pimoroni', 'spectra_palette', 'warmth_boost']`). A corrupt or manually edited `.inky_color_mode.json` can set `self.color_mode` to an invalid value, causing silent no-op in `process_image()`.
- Safe modification:
  - Validate against known modes after loading; fall back to `COLOR_MODE` constant if invalid
  - Add a schema version to the color mode file for future migration
- Test coverage: No automated mode switching tests

**`__pycache__/` No Longer Tracked:**
- Files: `__pycache__/` directory
- Status: Verified not tracked in git as of Phase 1 (plan 01-02). `.gitignore` covers `__pycache__/` and `*.py[cod]`. No cached Python files found in `git ls-files`.

**Obsolete Documentation Files Removed:**
- Files: `SUMMARY.md`, `COLOR_CALIBRATION.md` (removed in Phase 1, plan 01-02)
- Status: Both files were removed from the repository. `SUMMARY.md` was a v1.1.7 release summary in French, superseded by CHANGELOG.md. `COLOR_CALIBRATION.md` was a v1.0.1 color tuning guide, outdated since v1.1.0 introduced the 3-mode color system.
- Note: `INSTALLATION_GUIDE.md` remains and is flagged as a candidate for removal (content may overlap with README.md).

## Scaling Limits

**`shown` History List Grows Without Pruning:**
- Current capacity: Grows indefinitely; one entry per photo display event.
- Limit: At 1000 photos × average 1 display/day = 1000 entries max per cycle; negligible.
- Impact: If `CHANGE_INTERVAL_MINUTES > 0` with short intervals, `shown` can grow unboundedly within a day.
- Scaling path: Prune `shown` to a rolling window of `MAX_PHOTOS` entries.

**Metadata Dictionary Grows With Photo Count:**
- Current capacity: One entry (~200 bytes) per photo path. At `MAX_PHOTOS = 1000`, peak is ~200KB.
- Limit: Acceptable for current limits. Problematic if `MAX_PHOTOS` raised to 10,000+.
- Scaling path: Consider SQLite for metadata storage if scaling beyond current limits.

**File System Watching Not Recursive:**
- Current capacity: Only watches `PHOTOS_DIR` (not recursive), file count limit is OS inotify default.
- Limit: `inotify` can handle thousands of file events; no practical limit at current scale.
- Scaling path: No action needed for current use case.

## Dependencies at Risk

**`inky[rpi,example-depends]>=1.5.0` — Unbounded Upper Version:**
- Risk: No upper version pin. Breaking API changes in Inky 2.x would silently apply on next install or `pip upgrade`.
- Impact: Display initialization, color handling, or `set_image()` signature could change.
- Current mitigation: Version constraint prevents pre-1.5.0 only.
- Migration plan: Pin to `inky>=1.5.0,<2.0.0` in `requirements.txt`. Monitor Pimoroni GitHub for releases.

**`gpiozero>=2.0.0` — Pin Factory Fallback Chain is Unreliable:**
- Risk: gpiozero silently falls back from `lgpio` → `RPi.GPIO` → `NativeFactory`. `NativeFactory` is experimental and unreliable (documented in CHANGELOG v1.1.4).
- Impact: Buttons may appear to initialize but fail at press time.
- Migration plan: In test environment, explicitly set `Device.pin_factory = MockFactory()` before any `Button` construction (PITFALLS.md Pitfall 5 pattern).

**`watchdog>=3.0.0` — Observer Can Hang Without Death:**
- Risk: Observer thread can become unresponsive without raising an exception. `is_alive()` returns `True` but no events are processed.
- Impact: New photos not detected until service restart.
- Migration plan: Implement a heartbeat file creation test; restart observer on heartbeat failure (not just on `is_alive()` failure).

**`requests>=2.31.0` — Listed in requirements.txt but Unused:**
- Risk: `requests` appears in `requirements.txt` as "for future web features" but is not imported in `inky_photo_frame.py`.
- Files: `requirements.txt` (line 22)
- Impact: Unnecessary dependency increases install time and attack surface.
- Migration plan: Remove from `requirements.txt` until actually needed.

**`numpy>=1.24.0` — Listed as Recommended but Not Imported:**
- Risk: `numpy` appears in `requirements.txt` as "Optional but recommended" for "Better image processing" but is not imported anywhere in `inky_photo_frame.py`.
- Files: `requirements.txt` (line 20)
- Impact: Unused optional dependency; misleads users about what is actually required.
- Migration plan: Remove until actually used, or document exactly which operation would use it.

## Missing Critical Features

**No Test Suite (Zero Tests Exist):**
- Problem: No `tests/` directory, no `conftest.py`, no `pytest.ini` or `pyproject.toml`.
- Blocks: CI cannot enforce correctness; refactoring is unsafe without regression tests.
- Impact: Any code change risks breaking working behavior silently.
- Priority: High — addressed in Phase 5 (CI Foundation) and Phase 6 (Test Suite).

**No CI/CD Pipeline:**
- Problem: No `.github/workflows/` directory; no automated lint or test execution on push.
- Blocks: Contributors cannot verify correctness; broken code can merge to `main` without detection.
- Impact: The `update.sh` pull-from-main pattern means any broken `main` commit immediately harms all users running `update`.
- Priority: High — addressed in Phase 5 (CICD-01, CICD-02, CICD-03).

**No Automated Backup of History File:**
- Problem: `HISTORY_FILE` (`/home/pi/.inky_history.json`) is the sole source of truth for photo rotation state. No backup mechanism.
- Blocks: SD card corruption or accidental deletion loses all history.
- Impact: Photo rotation restarts from scratch; previously shown photos re-shown immediately.
- Priority: Medium — implement daily backup with 7-file rolling window.

**No Configuration Override File:**
- Problem: `CHANGE_HOUR`, `CHANGE_INTERVAL_MINUTES`, `MAX_PHOTOS` require editing Python source.
- Blocks: Multiple installation customization; updates via `update.sh` overwrite any edits.
- Impact: User changes to constants are lost every update.
- Priority: Low for v2.0 (out of scope per REQUIREMENTS.md); noted for v2+ planning.

## Test Coverage Gaps

**Image Processing Pipeline — No Tests:**
- What's not tested: `process_image()`, `_apply_spectra_palette()`, `_apply_warmth_boost()`, crop math, resize behavior
- Files: `inky_photo_frame.py` (lines 753-875)
- Risk: Color processing bugs only caught visually on hardware; crop math errors produce wrong framing silently
- Priority: High — PITFALLS.md Pitfall 6 documents the refactoring needed to make these testable
- Note: `process_image()` must be split into `load_image(path)` (I/O) and `process_image(img, ...)` (pure function) before tests can be written without filesystem I/O

**Photo History Logic — No Tests:**
- What's not tested: `change_photo()`, `next_photo()`, `previous_photo()`, `refresh_pending_list()`, `cleanup_old_photos()`, history format migration in `load_history()`
- Files: `inky_photo_frame.py` (lines 612-981)
- Risk: History corruption, duplicate displays, wrong deletion order go undetected
- Priority: High — addressed in Phase 6 (TEST-03)
- Note: Tests require `HISTORY_FILE` and `PHOTOS_DIR` to be injectable; currently hard-coded globals

**DisplayManager Singleton — No Tests:**
- What's not tested: Initialization, cleanup, singleton behavior, retry decorator
- Files: `inky_photo_frame.py` (lines 166-257)
- Risk: GPIO/SPI retry logic may not work as designed; cleanup may leave hardware in bad state
- Priority: High — PITFALLS.md Pitfall 2 documents the `autouse` fixture required before any test is possible
- Blocker: Singleton must be resettable between tests via `reset()` classmethod

**Button Controller — No Tests:**
- What's not tested: GPIO pin assignment, button press handling, busy flag behavior, color mode cycling
- Files: `inky_photo_frame.py` (lines 263-335)
- Risk: GPIO pin conflicts (e.g., 13.3" display CS1 vs button C) only caught on hardware
- Priority: High — requires `gpiozero` `MockFactory` fixture per PITFALLS.md Pitfall 5

**File Watcher — No Tests:**
- What's not tested: `PhotoHandler.on_created()`, 3-second debounce timer, multi-upload batching, process_uploads ordering
- Files: `inky_photo_frame.py` (lines 341-395)
- Risk: Race conditions in upload batching; only last photo shown behavior could break silently
- Priority: Medium — addressed in Phase 6 (TEST-04)

**Display Configuration Detection — No Tests:**
- What's not tested: `detect_display_saturation()` for each known display type, fallback to unknown config
- Files: `inky_photo_frame.py` (lines 450-508)
- Risk: New display models silently assigned wrong GPIO pins
- Priority: Medium

**Error Handling and Retry Logic — No Tests:**
- What's not tested: `@retry_on_error` decorator behavior, exponential backoff timing, recoverable vs non-recoverable error classification
- Files: `inky_photo_frame.py` (lines 229-257)
- Risk: Retry logic may not actually retry on real GPIO errors; may retry indefinitely on non-recoverable errors
- Priority: Medium

---

*Concerns audit: 2026-02-22*
