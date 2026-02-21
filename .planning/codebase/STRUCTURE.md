# Codebase Structure

**Analysis Date:** 2026-02-22

## Directory Layout

```
/Users/mehdiguiard/Desktop/INKY_V2/
├── inky_photo_frame.py         # Main application (1,211 lines)
├── inky-photo-frame-cli        # CLI wrapper script for systemd management
├── install.sh                  # Installation and system setup script
├── update.sh                   # GitHub-based update script
├── uninstall.sh                # Cleanup script
├── diagnostic_report.sh        # System diagnostic tool
├── requirements.txt            # Python dependencies
├── logrotate.conf              # Log rotation configuration
├── .planning/
│   └── codebase/               # Analysis documents (this location)
├── README.md                   # User documentation
├── INSTALLATION_GUIDE.md       # Setup instructions
├── SUMMARY.md                  # Project overview
├── CHANGELOG.md                # Version history
├── COLOR_CALIBRATION.md        # Color tuning reference
└── LICENSE                     # MIT license
```

## Directory Purposes

**Root Directory:**
- Purpose: Single-file monolithic Python application with bash utilities
- Contains: Executable scripts, documentation, configuration
- Key files: `inky_photo_frame.py` (application core), `inky-photo-frame-cli` (user commands)

**`.planning/codebase/`:**
- Purpose: GSD analysis documents (auto-generated)
- Contains: Architecture, structure, testing patterns, concerns
- Key files: This is where ARCHITECTURE.md and STRUCTURE.md live

## Key File Locations

**Entry Points:**

- `inky_photo_frame.py` (lines 1209-1211): Python application entry point
  ```python
  if __name__ == '__main__':
      frame = InkyPhotoFrame()
      frame.run()
  ```

- `inky-photo-frame-cli` (lines 1-185): Command-line interface for user operations
  - Delegates to systemd service: `sudo systemctl [start|stop|restart]`
  - Displays logs: `journalctl -u inky-photo-frame -f`
  - Updates from GitHub: Executes `update.sh`

- `install.sh`: Raspberry Pi system configuration
  - Enables I2C/SPI interfaces
  - Installs Python dependencies
  - Configures systemd service
  - Sets up SMB share

**Configuration:**

- `/home/pi/.inky_history.json`: Photo display history (JSON)
  - Structure: shown[], pending[], current, last_change, photo_metadata
  - Created by: `InkyPhotoFrame.__init__()` via `load_history()`

- `/home/pi/.inky_color_mode.json`: Saved color mode preference (JSON)
  - Structure: { "color_mode": "pimoroni|spectra_palette|warmth_boost" }
  - Created by: `cycle_color_mode()` or `reset_color_mode()`

- `/home/pi/.inky_credentials`: SMB share credentials (plain text)
  - Structure: Line 1 = username, Line 2 = password
  - Created by: `install.sh` or `inky-photo-frame reset-password`
  - Read by: `get_credentials()` (lines 521-532)

- `/home/pi/inky_photo_frame.log`: Application log file
  - Written by: Python logging (configured line 153-160)
  - Rotated by: `/etc/logrotate.d/inky-photo-frame` (installed by install.sh)

**Core Logic:**

- `inky_photo_frame.py` - All application code is in this single file:
  - **DisplayManager** (lines 166-228): Singleton for hardware init/cleanup
  - **ButtonController** (lines 263-336): GPIO button event routing
  - **PhotoHandler** (lines 341-395): File system watcher events
  - **InkyPhotoFrame** (lines 397-1211): Main application class with all methods

**Display Rendering:**

- `process_image()` (lines 821-875): Image loading, cropping, resizing
- `_apply_spectra_palette()` (lines 753-792): 6-color palette quantization with dithering
- `_apply_warmth_boost()` (lines 794-819): RGB channel adjustments for warmth
- `display_photo()` (lines 877-906): Render to hardware with retry logic

**Testing:**

- No test files present in repository
- See TESTING.md (if generated) for testing approach

## Naming Conventions

**Files:**

- Python: `inky_photo_frame.py` (snake_case, descriptive)
- Shell scripts: No extension (executable), descriptive names
- Config files: Dot-prefixed for hidden status (`.inky_*`)
- Logs: `inky_photo_frame.log` (matches application name)

**Directories:**

- System paths: Lowercase, absolute `/home/pi/` for Raspberry Pi
- Hidden configs: Dot-prefixed (`.inky_*`, `.inky_backups`)
- Planning: `.planning/codebase/` (hidden, organized)

**Classes:**

- Pascal case: `DisplayManager`, `InkyPhotoFrame`, `ButtonController`, `PhotoHandler`
- Purpose in name: Manager, Controller, Handler suffixes clear responsibility

**Functions:**

- Snake case: `initialize()`, `cleanup()`, `display_photo()`, `process_image()`
- Underscore prefix for internal: `_apply_spectra_palette()`, `_on_button_a()`
- Decorators: `@retry_on_error()`, `@wraps()`

**Variables:**

- Configuration constants: ALL_CAPS
  - `PHOTOS_DIR`, `HISTORY_FILE`, `COLOR_MODE_FILE`, `CHANGE_HOUR`, `MAX_PHOTOS`
- Instance variables: snake_case with self prefix
  - `self.display`, `self.history`, `self.button_controller`
- Module-level dicts: ALL_CAPS for config, camelCase for content
  - `DISPLAY_CONFIGS`, `SPECTRA_PALETTE`, `WARMTH_BOOST_CONFIG`

**Methods:**

- Public APIs: `change_photo()`, `display_photo()`, `cycle_color_mode()`
- Event handlers: `on_created()`, `when_pressed` callbacks
- Getters/Loaders: `get_all_photos()`, `load_history()`, `load_color_mode()`

## Where to Add New Code

**New Feature - Photo Processing:**
- Primary code: Add method to `InkyPhotoFrame` class (around lines 821-875)
- Color mode: Add dict to top-level config section (lines 68-97)
- Entry point: Add button handler or update `process_image()` logic

**New Feature - Hardware Control:**
- GPIO buttons: Update `ButtonController.__init__()` and add `_on_button_x()` method (lines 272-335)
- Display detection: Add to `DISPLAY_CONFIGS` dict (lines 103-150), update `detect_display_saturation()` (lines 450-508)
- Error recovery: Update `retry_on_error()` decorator (lines 229-257)

**New Feature - File Management:**
- Upload handling: Modify `PhotoHandler` class (lines 341-395)
- Photo discovery: Update `get_all_photos()` (lines 641-650) or `refresh_pending_list()` (lines 718-751)
- Storage cleanup: Enhance `cleanup_old_photos()` (lines 652-716)

**New Feature - User Commands:**
- CLI commands: Add case statement to `inky-photo-frame-cli` (lines 91-184)
- Help text: Update `show_usage()` function in CLI script

**New Utilities:**
- Helper functions: Add to top of `InkyPhotoFrame` class before `__init__`
- Decorators: Add near `retry_on_error()` (lines 229-257)
- Module-level: Add to configuration section (lines 58-150)

## Special Directories

**`__pycache__/`:**
- Purpose: Python bytecode cache (auto-generated by interpreter)
- Generated: Yes (Python creates on import)
- Committed: No (in .gitignore)
- Safe to delete: Yes, will regenerate

**`.planning/codebase/`:**
- Purpose: GSD analysis documents
- Generated: Yes (by /gsd:map-codebase command)
- Committed: Yes (part of planning workflow)
- Manual edits: Not recommended (auto-generated)

**`.claude/`:**
- Purpose: Claude IDE workspace metadata
- Generated: Yes (Claude Code creates)
- Committed: No (in .gitignore)
- Safe to delete: Yes

**`.git/`:**
- Purpose: Git version control metadata
- Generated: Yes (git init)
- Committed: No (always ignored)
- Safe to delete: No (loses history)

## Configuration Constants Reference

**Key Configuration Lines:**

- `PHOTOS_DIR` (line 59): `/home/pi/Images` - Photo source location
- `HISTORY_FILE` (line 60): `/home/pi/.inky_history.json` - State persistence
- `COLOR_MODE_FILE` (line 61): `/home/pi/.inky_color_mode.json` - Mode preference
- `CHANGE_HOUR` (line 62): `5` - Daily change time (5 AM)
- `CHANGE_INTERVAL_MINUTES` (line 63): `0` - 0=daily, >0=every N minutes
- `LOG_FILE` (line 64): `/home/pi/inky_photo_frame.log`
- `MAX_PHOTOS` (line 65): `1000` - Storage limit before cleanup
- `VERSION` (line 66): `"1.1.7"` - Current version string
- `COLOR_MODE` (line 74): `'spectra_palette'` - Default color mode
- `SATURATION` (line 77): `0.5` - Pimoroni default saturation

**Display Configuration Constants:**

- `DISPLAY_CONFIGS` (lines 103-150): Dict of display models
  - Keys: `spectra_7.3`, `classic_7.3`, `spectra_13.3`
  - Each contains: `name`, `resolution`, `is_spectra`, `is_13inch`, `gpio_pins`, `detection`

**Color Profiles:**

- `SPECTRA_PALETTE` (lines 81-88): RGB tuples for 6-color e-ink display
- `WARMTH_BOOST_CONFIG` (lines 91-97): Enhancement multipliers for warmth mode

## Organization Summary

**Monolithic Structure (Single Python File):**
- `inky_photo_frame.py` contains all classes, functions, and logic
- No package structure (not needed for single-purpose application)
- All dependencies imported at top (lines 30-48)

**Script Utilities (Bash):**
- `install.sh`: One-time setup (450+ lines)
- `update.sh`: Version management
- `uninstall.sh`: Cleanup
- `diagnostic_report.sh`: Troubleshooting
- `inky-photo-frame-cli`: User interface

**Data Persistence (JSON Files):**
- History and preferences stored in `/home/pi/.inky_*` files
- No database (JSON sufficient for single-device use)
- SMB credentials in plain text (Raspberry Pi local-only)

**Documentation:**
- User guides: README.md, INSTALLATION_GUIDE.md
- Technical: COLOR_CALIBRATION.md, SUMMARY.md
- Version tracking: CHANGELOG.md

---

*Structure analysis: 2026-02-22*
