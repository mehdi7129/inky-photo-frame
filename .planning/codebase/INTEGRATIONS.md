# External Integrations

**Analysis Date:** 2026-02-22

## APIs & External Services

**Display Hardware:**
- Pimoroni Inky Impression - E-ink display control via GPIO/SPI
  - SDK/Client: `inky` Python package
  - Connection: SPI (hardware interface)
  - Auto-detection: `inky.auto.auto()` at line 191 of `inky_photo_frame.py`

**System IP Detection:**
- Local network socket query (no external API)
  - Method: UDP socket to get local IP at line 513 of `inky_photo_frame.py`
  - No external dependency - uses Python `socket` module

## Data Storage

**File Storage:**
- Local filesystem only
  - Photo directory: `/home/pi/Images` (SMB-accessible network location)
  - History file: `/home/pi/.inky_history.json` (JSON state persistence)
  - Color mode file: `/home/pi/.inky_color_mode.json` (Runtime settings)
  - Log file: `/home/pi/inky_photo_frame.log` (Activity logging)
  - Credentials file: `/home/pi/.inky_credentials` (SMB user credentials)

**Databases:**
- None - Application uses file-based JSON state management

**Caching:**
- Photo rotation history: In-memory + JSON persistence
- Color mode preference: Single JSON config file

## Authentication & Identity

**Auth Provider:**
- Local SMB (Samba) authentication
  - Implementation: Linux user account via `smbpasswd` at line 225-230 of `install.sh`
  - Default user: `inky` (configurable via `USER_NAME` variable at line 18 of `install.sh`)
  - Fallback user: `pi` (also enabled for SMB access at line 229)
  - Password: Auto-generated 10-character alphanumeric at line 20 of `install.sh`
  - Persistence: Stored in `/home/pi/.inky_credentials` (username on line 1, password on line 2)

**Credential Management:**
- No external auth service required
- Single-user local Samba share
- Credentials displayed on welcome screen for user access

## File Sharing & Network Access

**SMB/CIFS Protocol:**
- Samba server configuration added at line 190 of `install.sh`
- Share name: `Images` (maps to `/home/pi/Images`)
- Access: Network file sharing for photo uploads from phones/computers
- Restart: `systemctl restart smbd` at line 241 of `install.sh`

**Network Services:**
- SMB share: `smb://[ip-address]`
- Hostname discovery: Local network only (no central registry)
- No DNS integration required

## Monitoring & Observability

**Error Tracking:**
- Local application logging (no external service)
  - Handler: Python `logging` module
  - Configuration: Line 39 of `inky_photo_frame.py`
  - Log file: `/home/pi/inky_photo_frame.log`

**Logs:**
- Systemd journal integration:
  - `StandardOutput=journal` and `StandardError=journal` in service file at line 259-260 of `install.sh`
  - View: `journalctl -u inky-photo-frame -f`
- Logrotate rotation:
  - Config: `/etc/logrotate.d/inky-photo-frame` (7-day retention)
  - Installed at line 268-270 of `install.sh`

## CI/CD & Deployment

**Hosting:**
- Raspberry Pi (bare metal deployment)
- Auto-start: systemd service `inky-photo-frame.service` at `/etc/systemd/system/inky-photo-frame.service`

**Updates:**
- GitHub repository updates:
  - Download script: `update.sh` downloads latest files from `https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/`
  - CLI command: `inky-photo-frame update` triggers update process
  - In-place update: No downtime required

**CI Pipeline:**
- Not detected - Manual updates via GitHub releases

## Environment Configuration

**Required env vars:**
- `INKY_SKIP_GPIO_CHECK=1` - Set at line 32 of `inky_photo_frame.py` to suppress GPIO check warnings

**Optional env vars:**
- None detected - Configuration via Python constants in `inky_photo_frame.py`

**Secrets location:**
- `.inky_credentials` file at `/home/pi/.inky_credentials` (local SMB credentials)
- No external secret manager required

## System Services

**Service Management:**
- systemd service: `inky-photo-frame` at `/etc/systemd/system/inky-photo-frame.service`
- User context: Runs as `pi` user (line 253 of `install.sh`)
- Working directory: `/home/pi/inky-photo-frame`
- Python interpreter: `/home/pi/.virtualenvs/pimoroni/bin/python`
- Restart policy: Always restart with 10-second delay (line 257-258 of `install.sh`)

**GPIO & Hardware:**
- GPIO pin configuration: Device tree overlay `dtoverlay=spi0-1cs,cs0_pin=7` (line 87, 97 of `install.sh`)
- Button pins: Configured per display type in `DISPLAY_CONFIGS` at lines 103-150 of `inky_photo_frame.py`
  - 7.3" displays: GPIO 5, 6, 16, 24
  - 13.3" display: GPIO 5, 6, 25, 24 (different C pin due to CS1 conflict)

## Webhooks & Callbacks

**Incoming:**
- None - Application is display-only with no incoming webhook support

**Outgoing:**
- None - No external API calls or webhook delivery

## File System Events

**Watched Directory:**
- Path: `/home/pi/Images`
- Monitored by: `watchdog.observers.Observer` (line 41-42 of `inky_photo_frame.py`)
- Trigger: `FileSystemEventHandler` for `on_created` events (new photo detection)
- Supported formats: JPG, PNG, HEIC (iPhone support via pillow-heif)

---

*Integration audit: 2026-02-22*
