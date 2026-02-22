# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-22

### Added

- Modular package structure: monolith split into `inky_photo_frame/` package with dedicated modules for config, display, image processing, photo management, buttons, welcome screen, and app orchestration
- Pytest test suite with 70% coverage gate enforced in CI
- GitHub Actions CI pipeline running ruff lint, ruff format, and pytest on every push and pull request
- `conftest.py` with GPIO hardware mocks enabling test execution without physical Raspberry Pi hardware
- Configurable photo rotation interval via `CHANGE_INTERVAL_MINUTES` environment variable, replacing the hardcoded 5 AM daily rotation

### Changed

- Entry point moved from direct `inky_photo_frame.py` script execution to package-based invocation; a backward-compatible shim preserves existing `systemctl` and cron configurations

### Fixed

- GPIO button C on 13.3-inch Inky Impression displays now reads from GPIO 25 instead of the conflicting GPIO 16, which is active-low on that hardware revision ([#3](https://github.com/mehdi7129/inky-photo-frame/pull/3))

## [1.1.7] - 2025-10-24

### Fixed

- ACT LED disable made reliable via a dedicated systemd service (`disable-leds.service`) that writes directly to sysfs at boot, replacing the previous `/boot/config.txt` method which could be overridden by kernel updates
  - Service uses `Type=oneshot` with `RemainAfterExit=yes` and runs after `multi-user.target`
  - Both `install.sh` and `update.sh` create, enable, and start the service automatically

## [1.1.6] - 2025-10-24

### Fixed

- Auto-install system-level dependencies (`swig`, `python3-dev`, `liblgpio-dev`) required for lgpio compilation
  - `install.sh` includes these packages in the initial `apt-get install` step
  - `update.sh` checks and installs system dependencies before running pip
  - Resolves the `command 'swig' failed` and `cannot find -llgpio` build errors introduced by v1.1.5's lgpio requirement

## [1.1.5] - 2025-10-24

### Added

- lgpio GPIO backend support for Raspberry Pi OS Bookworm (Python 3.13), where the kernel requires lgpio instead of RPi.GPIO
  - `update.sh` installs lgpio first, with RPi.GPIO as fallback
  - gpiozero pin factory hierarchy: lgpio, then RPi.GPIO, then NativeFactory

### Fixed

- GPIO group membership check added to `update.sh`; user is automatically added to the `gpio` group if missing, preventing `PinFactoryFallback` errors on modern Raspberry Pi OS

## [1.1.4] - 2025-10-24

### Fixed

- Added `RPi.GPIO>=0.7.0` as an explicit dependency in `requirements.txt`, `update.sh`, and `install.sh`
  - gpiozero requires RPi.GPIO to access GPIO pins; without it, gpiozero falls back to the experimental NativeFactory which fails with `[Errno 22] Invalid argument`

## [1.1.3] - 2025-10-24

### Changed

- Improved dependency installation error handling in `update.sh`
  - Verifies virtualenv activation before running pip install
  - Uses `--quiet` flag instead of suppressing all output, so errors remain visible
  - Reports clear success or failure messages after each installation step

## [1.1.2] - 2025-10-24

### Added

- Auto-install Python dependencies (`gpiozero`, `pillow-heif`, `watchdog`) during `update.sh` execution
  - Activates the pimoroni virtualenv and runs `pip install --upgrade` after downloading new files
  - Ensures button support activates immediately after update without manual pip commands

## [1.1.1] - 2025-10-24

### Fixed

- Made `gpiozero` import optional with try/except at module level so the service starts even when gpiozero is not installed
  - `BUTTONS_AVAILABLE` flag gates button controller initialization
  - Added `gpiozero` to `install.sh` dependencies for new installations
  - Prevents service crash on systems where gpiozero was not yet installed

## [1.1.0] - 2025-10-24

### Added

- Physical button controls via GPIO for interactive photo browsing
  - Button A (GPIO 5): next photo
  - Button B (GPIO 6): previous photo
  - Button C (GPIO 16): cycle color mode (pimoroni, spectra_palette, warmth_boost)
  - Button D (GPIO 24): reset to default pimoroni mode
- Dynamic color mode switching at runtime with persistent preference saved to `/home/pi/.inky_color_mode.json`
- `ButtonController` class with 20 ms debounce using gpiozero, thread-safe busy-flag lock to prevent presses during e-ink refresh

## [1.0.2] - 2025-10-24

### Removed

- Deprecated Bluetooth WiFi configuration feature and `bluetooth_wifi_smart.py` test file
- All Bluetooth references from documentation and setup scripts

### Changed

- Documentation updated with `inky-photo-frame update` command usage in README

## [1.0.1] - 2025-10-24

### Fixed

- ACT LED disable logic corrected using `act_led_activelow=on` for proper LED shutdown behavior
- WiFi configuration integrated with web-based setup and hotspot fallback
- GPIO/SPI singleton pattern stabilized to prevent resource contention

### Changed

- All version references updated from beta numbering (v2.x) to stable v1.0.1 across documentation and scripts

## [1.0.0] - 2025-10-24

### Added

- Auto-detection of Inky display models (Impression 5.7-inch, 7.3-inch, 13.3-inch) at startup
- Multiple color palette modes: `pimoroni` (default), `spectra_palette`, and `warmth_boost`
- SMB/CIFS network share support for receiving photos from any device on the local network
- HEIC image format support via `pillow-heif`, enabling direct display of iPhone photos
- Daily photo rotation at 5 AM via cron-triggered service restart
- `update.sh` CLI for one-command updates from GitHub (`inky-photo-frame update`)
- `install.sh` setup script for automated first-time installation on Raspberry Pi
- Storage management with FIFO cleanup policy at 1000 photos (`MAX_PHOTOS` configurable)
- `DisplayManager` singleton ensuring single SPI initialization with proper cleanup via `atexit` and signal handlers
- Retry logic with exponential backoff (3 attempts, 1s/2s/4s delays) for transient GPIO/SPI errors
- Log rotation via logrotate with 7-day retention

[2.0.0]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.4...v2.0.0
[1.1.7]: https://github.com/mehdi7129/inky-photo-frame/compare/5fde38c...e5ce52b
[1.1.6]: https://github.com/mehdi7129/inky-photo-frame/compare/4231b71...5fde38c
[1.1.5]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.4...4231b71
[1.1.4]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/mehdi7129/inky-photo-frame/compare/1f21ab6...v1.0.2
[1.0.1]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.0...1f21ab6
[1.0.0]: https://github.com/mehdi7129/inky-photo-frame/releases/tag/v1.0
