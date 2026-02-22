# External Integrations

**Analysis Date:** 2026-02-22

## APIs & External Services

**GitHub (update distribution):**
- Used as a raw file host — NOT a git workflow on-device
- Base URL: `https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/`
- Used by: `install.sh` (lines 171-179) and `update.sh` (lines 75-91)
- Files fetched: `inky_photo_frame.py`, `update.sh`, `inky-photo-frame-cli`, `logrotate.conf`
- Tool: `curl -sSL` — no auth, public repo assumed
- No API key required; no GitHub API calls; no webhooks

**No other external APIs are used.** The application is entirely self-contained on the local network.

## Hardware Interfaces

**Pimoroni Inky display (SPI/I2C):**
- SDK/Client: `inky` Python package (`inky[rpi,example-depends]` >= 1.5.0)
- Connection: SPI bus (requires `dtoverlay=spi0-1cs,cs0_pin=7`) + I2C (display detection)
- Entry point: `from inky.auto import auto` → `auto()` in `DisplayManager.initialize()` (`inky_photo_frame.py` line 191)
- API used: `display.set_image(img, saturation=float)` and `display.show()`
- Retry wrapper: `@retry_on_error(max_attempts=3, delay=1, backoff=2)` on `display_photo()`
- Cleanup: `display._spi.close()` in `DisplayManager.cleanup()` on exit signals

**GPIO buttons (gpiozero via lgpio):**
- SDK/Client: `gpiozero` >= 2.0.0, backend: `lgpio` >= 0.2.0 (or `RPi.GPIO` fallback)
- Pins vary by display model (from `DISPLAY_CONFIGS` in `inky_photo_frame.py` lines 103-150):
  - 7.3" displays: Button A=GPIO5, B=GPIO6, C=GPIO16, D=GPIO24
  - 13.3" display: Button A=GPIO5, B=GPIO6, C=GPIO25, D=GPIO24 (C shifted due to CS1 conflict)
- API used: `Button(pin, bounce_time=0.02)` + `.when_pressed` callback
- Optional: guarded by `BUTTONS_AVAILABLE` boolean; app runs without buttons

## Data Storage

**Databases:** None.

**File Storage (local filesystem only):**
- Photo directory: `/home/pi/Images` — primary storage, SMB-writable, watchdog-monitored
- History file: `/home/pi/.inky_history.json` — JSON object with keys: `shown`, `pending`, `current`, `last_change`, `photo_metadata`
- Color mode file: `/home/pi/.inky_color_mode.json` — JSON: `{"color_mode": "spectra_palette"}`
- Log file: `/home/pi/inky_photo_frame.log` — plain text, rotated by logrotate
- Credentials file: `/home/pi/.inky_credentials` — plain text, 2 lines (username, password)
- Backups: `/home/pi/.inky-backups/` — created by `update.sh` (last 5 kept)

**Caching:** None external. Photo rotation state is in-memory (`InkyPhotoFrame.history` dict) with periodic JSON flush.

## Authentication & Identity

**Auth Provider:** Local Samba (no external identity provider)
- Implementation: Linux system users + `smbpasswd` (lines 225-230 of `install.sh`)
- Default SMB user: `inky` (+ `pi` as secondary user)
- Password: auto-generated 10-character alphanumeric via `/dev/urandom` at install time
- Credentials storage: `/home/pi/.inky_credentials` (plaintext, chmod 644)
- Password reset: `inky-photo-frame reset-password` command in `inky-photo-frame-cli`
- Credentials displayed on Inky welcome screen for user convenience (read via `get_credentials()`)

## File Sharing (SMB/Samba)

**Incoming photo uploads:**
- Protocol: SMB/CIFS (Samba)
- Share name: `Images`
- Path: `/home/pi/Images`
- Users: `inky` and `pi` (both have write access)
- iOS compatibility: `vfs objects = fruit streams_xattr`, `fruit:model = MacSamba`
- No authentication beyond local Samba user — no LDAP, no AD, no Kerberos
- Upload detection: `watchdog` `Observer` watches `/home/pi/Images` non-recursively

**Network addressing:**
- IP displayed on welcome screen; detected at runtime by `get_ip_address()` using UDP socket trick:
  `socket.connect(("8.8.8.8", 80))` then `getsockname()` — does NOT actually make network call
- No DNS or mDNS registration; users connect by IP address directly

## Monitoring & Observability

**Error Tracking:** None external. All errors logged locally.

**Logging:**
- Library: Python `logging` module (stdlib)
- Level: `INFO` (default)
- Format: `%(asctime)s - %(message)s`
- Handlers: dual — `FileHandler('/home/pi/inky_photo_frame.log')` + `StreamHandler(stdout)`
- Systemd journal: `StandardOutput=journal` in service unit (aggregates stdout)
- View live: `journalctl -u inky-photo-frame -f` or `inky-photo-frame logs`
- Log rotation: `/etc/logrotate.d/inky-photo-frame` — daily, 7 days, compressed

## CI/CD & Deployment

**Hosting:** Raspberry Pi bare metal — no cloud hosting.

**CI Pipeline:** None currently in place. Research documents (`/Users/mehdiguiard/Desktop/INKY_V2/.planning/research/STACK.md`) recommend GitHub Actions for future CI.

**Deployment process:**
1. `curl -sSL .../install.sh | bash` — one-shot bootstrap on new Pi
2. `inky-photo-frame update` (or `update.sh`) — pulls raw files from GitHub, stops service, replaces files, restarts
3. Rollback: `update.sh` creates timestamped backup in `/home/pi/.inky-backups/`; restores on failure

**Installed binary files:**
- `/home/pi/inky-photo-frame/inky_photo_frame.py` — main application
- `/home/pi/inky-photo-frame/update.sh` — update script
- `/home/pi/inky-photo-frame/inky-photo-frame-cli` — CLI tool source
- `/usr/local/bin/inky-photo-frame` — CLI command (symlinked from above)
- `/etc/systemd/system/inky-photo-frame.service` — systemd unit
- `/etc/logrotate.d/inky-photo-frame` — log rotation config
- `/etc/systemd/system/disable-leds.service` — LED suppression service

## Environment Configuration

**Required env vars (set by the application itself):**
- `INKY_SKIP_GPIO_CHECK=1` — set in `inky_photo_frame.py` line 32 before any imports; prevents Inky library GPIO check from failing on non-Pi machines

**Required for CI/testing (not set in production):**
- `GPIOZERO_PIN_FACTORY=mock` — enables gpiozero's built-in MockFactory for unit tests

**Secrets location:**
- `/home/pi/.inky_credentials` — local SMB username + password (not a secret manager)
- No cloud secrets, no API tokens, no .env file

## Webhooks & Callbacks

**Incoming webhooks:** None.

**Outgoing webhooks:** None.

**Internal event callbacks (not webhooks):**
- `watchdog` `FileSystemEventHandler.on_created()` → fires on new file in `/home/pi/Images`
- `gpiozero` `Button.when_pressed` → fires on GPIO pin state change
- `threading.Timer` (3-second debounce) → coalesces rapid upload events before display

---

*Integration audit: 2026-02-22*
