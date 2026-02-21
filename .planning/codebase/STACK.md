# Technology Stack

**Analysis Date:** 2026-02-22

## Languages

**Primary:**
- Python 3 - Core application and display logic

**Secondary:**
- Bash - Installation, update, and CLI management scripts

## Runtime

**Environment:**
- Python 3.x (Raspberry Pi OS default)
- Raspberry Pi OS (Bookworm or later)

**Package Manager:**
- pip (Python Package Installer)
- Lockfile: `requirements.txt`

## Frameworks

**Core:**
- inky[rpi,example-depends] 1.5.0+ - Pimoroni Inky Impression display library with auto-detection (`inky.auto`)
- Pillow (PIL) 10.0.0+ - Image processing and rendering
- pillow-heif 0.13.0+ - iPhone HEIC image format support
- watchdog 3.0.0+ - File system monitoring for new photo detection

**System Integration:**
- gpiozero 2.0.0+ - GPIO button interface abstraction
- lgpio 0.2.0+ - Modern GPIO backend (Raspberry Pi OS Bookworm recommended)
- RPi.GPIO 0.7.0+ - Legacy GPIO backend (fallback for older systems)

**Optional but Recommended:**
- numpy 1.24.0+ - Enhanced image processing capabilities
- requests 2.31.0+ - HTTP client for future web feature extensibility

## Key Dependencies

**Critical:**
- inky[rpi,example-depends] - Provides the official Pimoroni Inky display driver with auto-detection via `inky.auto.auto()`
- Pillow - Image processing engine for cropping, resizing, color conversion
- watchdog - Real-time file system event monitoring (NEW_PHOTOS detection)

**Infrastructure:**
- python3-pip - Package management
- python3-venv - Virtual environment isolation
- samba / samba-common-bin - SMB file sharing for photo uploads
- git - Version control and updates
- fonts-dejavu / fonts-dejavu-core - System font rendering for welcome screen

**Hardware Interface:**
- liblgpio-dev - GPIO hardware support (system package)
- swig - C extension building support
- python3-dev - Python C extension compilation

## Configuration

**Environment:**
- Virtual environment: `~/.virtualenvs/pimoroni/`
  - Isolated Python environment per `install.sh` line 143
  - Activated automatically by systemd service
- GPIO check disabled: `INKY_SKIP_GPIO_CHECK=1` env var set at line 32 of `inky_photo_frame.py`

**Build:**
- `requirements.txt` - Single source of truth for all Python dependencies
- `install.sh` - Automated installation with I2C/SPI setup
- `update.sh` - In-place version updates via GitHub

## Platform Requirements

**Development:**
- Raspberry Pi (all models with GPIO support)
- I2C interface enabled (`raspi-config nonint do_i2c 0`)
- SPI interface enabled (`raspi-config nonint do_spi 0`)
- GPIO device tree overlay: `dtoverlay=spi0-1cs,cs0_pin=7` in `/boot/config.txt` or `/boot/firmware/config.txt`

**Production:**
- Deployment target: Raspberry Pi running Raspberry Pi OS (Bookworm or Bullseye)
- Systemd service management at `/etc/systemd/system/inky-photo-frame.service`
- Log rotation via `/etc/logrotate.d/inky-photo-frame`
- SMB share for photo upload at `/home/pi/Images`

## Display Support

**Compatible Hardware:**
- Inky Impression 7.3" Classic (7 colors, 800×480px) - detected via `resolution` match
- Inky Impression 7.3" Spectra 2025 (6 colors, 800×480px) - detected via `e673` module class
- Inky Impression 13.3" Spectra 2025 (6 colors, 1600×1200px) - detected via resolution match

**Auto-Detection Mechanism:**
- `inky.auto.auto()` called at line 191 of `inky_photo_frame.py`
- Manual detection fallback at lines 462-483 matches against `DISPLAY_CONFIGS` dictionary

---

*Stack analysis: 2026-02-22*
