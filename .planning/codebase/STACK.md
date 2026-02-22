# Technology Stack

**Analysis Date:** 2026-02-22

## Languages

**Primary:**
- Python 3.11 - All application logic (`inky_photo_frame.py`)
  - Target runtime: Python 3.11 (Raspberry Pi OS Bookworm ships this version)
  - Dev environment: Python 3.13 (macOS)
  - Single-file monolith currently; architecture research targets refactor into package

**Secondary:**
- Bash - Installation, update, and CLI management (`install.sh`, `update.sh`, `inky-photo-frame-cli`)

## Runtime

**Environment:**
- Raspberry Pi OS Bookworm (Debian 12) — production target
- macOS / Linux — development only

**Package Manager:**
- pip, inside a virtualenv
- Virtualenv location: `~/.virtualenvs/pimoroni/` (created by `install.sh` line 143)
- Lockfile: None — only `requirements.txt` with minimum version pins (`>=`)

## Frameworks

**Core display:**
- `inky[rpi,example-depends]` >= 1.5.0 — Pimoroni e-ink display driver
  - Auto-detection: `from inky.auto import auto` called in `DisplayManager.initialize()`
  - Supports: Inky Impression 7.3" Classic (7-color), 7.3" Spectra (6-color), 13.3" Spectra
  - SPI + I2C hardware interface; requires both enabled via `raspi-config`

**Image processing:**
- `Pillow` >= 10.0.0 — Image open, resize, crop, RGBA compositing, palette quantization, drawing
  - Floyd-Steinberg dithering via `Image.Dither.FLOYDSTEINBERG` (Pillow 10+ API)
  - Font rendering via `ImageFont.truetype()` — uses DejaVu system fonts on Pi
- `pillow-heif` >= 0.13.0 — HEIC/HEIF support for iPhone photos
  - Optional: registered via `pillow_heif.register_heif_opener()` in `InkyPhotoFrame.__init__`
  - Guarded by `try/except ImportError` — app runs without it

**File system monitoring:**
- `watchdog` >= 3.0.0 — Real-time detection of photo uploads to `/home/pi/Images`
  - `Observer` + `FileSystemEventHandler` subclass (`PhotoHandler`)
  - 3-second debounce timer to coalesce batch uploads
  - Observer auto-restart loop in `run()` if it dies

**GPIO / Buttons:**
- `gpiozero` >= 2.0.0 — High-level `Button` abstraction with 20ms debounce
  - Optional: guarded by `BUTTONS_AVAILABLE = True/False` at module level
  - `GPIOZERO_PIN_FACTORY=mock` env var enables MockFactory for CI/testing
- `lgpio` >= 0.2.0 — Modern GPIO backend, recommended for Bookworm
- `RPi.GPIO` >= 0.7.0 — Legacy GPIO backend (fallback)

**Standard library used heavily:**
- `threading` — `Lock`, `Timer` for debounce and history concurrency
- `logging` — dual handler (file + stdout), `%(asctime)s` format
- `json` — history and color mode persistence
- `pathlib.Path` — all file system operations
- `socket` — local IP detection (UDP trick to determine outbound interface)
- `signal`, `atexit` — graceful shutdown / SPI cleanup
- `subprocess` — available but not actively called in current code
- `functools.wraps` — used in `retry_on_error` decorator

**Optional / future:**
- `numpy` >= 1.24.0 — Listed in `requirements.txt`; not directly imported in current code
- `requests` >= 2.31.0 — Listed as "for future web features"; not used

## Key Dependencies

**Cannot run without:**
- `inky[rpi,example-depends]` — the entire app displays to this library's API
- `Pillow` — all image processing; no display possible without it
- `watchdog` — file monitoring for instant upload detection

**Gracefully optional:**
- `gpiozero` / `lgpio` / `RPi.GPIO` — buttons disabled if unavailable (`BUTTONS_AVAILABLE` guard)
- `pillow-heif` — HEIC support disabled if unavailable (try/except)
- `numpy` — not yet actively used; listed for future enhancement

**System packages (installed by `install.sh`):**
- `samba`, `samba-common-bin` — SMB file sharing for photo uploads
- `fonts-dejavu`, `fonts-dejavu-core` — system fonts for welcome screen text rendering
- `liblgpio-dev`, `swig`, `python3-dev` — build dependencies for lgpio C extension
- `git` — used by install/update flow

## Configuration

**Inline constants in `inky_photo_frame.py` (lines 59–97):**
- `PHOTOS_DIR = Path('/home/pi/Images')` — photo storage and SMB share root
- `HISTORY_FILE = Path('/home/pi/.inky_history.json')` — JSON display history
- `COLOR_MODE_FILE = Path('/home/pi/.inky_color_mode.json')` — persisted color mode
- `LOG_FILE = '/home/pi/inky_photo_frame.log'` — application log
- `MAX_PHOTOS = 1000` — FIFO auto-cleanup threshold
- `CHANGE_HOUR = 5` — daily rotation hour (5 AM)
- `CHANGE_INTERVAL_MINUTES = 0` — 0 = daily mode; >0 = interval mode
- `COLOR_MODE = 'spectra_palette'` — default; options: `pimoroni`, `spectra_palette`, `warmth_boost`
- `SATURATION = 0.5` — Pimoroni default saturation passed to `display.set_image()`

**Environment variables:**
- `INKY_SKIP_GPIO_CHECK=1` — set at line 32 of `inky_photo_frame.py` before imports, prevents Inky from failing on non-Pi
- `GPIOZERO_PIN_FACTORY=mock` — not set in production; needed for CI testing

**Credentials file:**
- `/home/pi/.inky_credentials` — plain text, line 1 = username, line 2 = password
- Read at runtime by `get_credentials()` to display SMB credentials on welcome screen
- Written by `install.sh` step 12 and `inky-photo-frame-cli reset-password`

**Build configuration:**
- No `pyproject.toml` yet (planned; research recommends adding for tool config only)
- No `setup.py` / `setup.cfg` — application is not pip-installable
- Deployed by `install.sh` downloading raw files from GitHub
- Updated by `update.sh` with backup/rollback

## System Services

**Systemd unit (`inky-photo-frame.service`):**
- Installed to: `/etc/systemd/system/inky-photo-frame.service`
- Runs as user: `pi`
- Working directory: `/home/pi/inky-photo-frame`
- Interpreter: `/home/pi/.virtualenvs/pimoroni/bin/python`
- Restart: `always`, 10-second delay
- Logging: systemd journal (`journalctl -u inky-photo-frame -f`)

**Samba:**
- Share name: `Images`, path: `/home/pi/Images`
- iOS compatibility: `vfs objects = fruit streams_xattr` (Apple SMB extensions)
- Service: `smbd` managed by systemd

**Log rotation (`logrotate.conf`):**
- Installed to: `/etc/logrotate.d/inky-photo-frame`
- Retention: 7 days, daily, compressed

**LED disable service:**
- Installed to: `/etc/systemd/system/disable-leds.service`
- Disables Raspberry Pi ACT LED to prevent light pollution in dark rooms

## Platform Requirements

**Development:**
- Python 3.9+ (for future test tooling)
- No hardware required when using `INKY_SKIP_GPIO_CHECK=1` + `GPIOZERO_PIN_FACTORY=mock`

**Production:**
- Raspberry Pi with 40-pin GPIO (any model)
- Raspberry Pi OS Bookworm
- I2C + SPI interfaces enabled
- GPIO overlay: `dtoverlay=spi0-1cs,cs0_pin=7` in `/boot/firmware/config.txt`
- Inky Impression display (7.3" 800x480 or 13.3" 1600x1200) on SPI/GPIO

---

*Stack analysis: 2026-02-22*
