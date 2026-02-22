## Highlights

- **GPIO fix for 13.3" displays** -- Button C now reads GPIO 25 instead of the conflicting GPIO 16, which is active-low on the 13.3" Inky Impression hardware revision ([#3](https://github.com/mehdi7129/inky-photo-frame/pull/3))
- **Modular package architecture** -- The monolithic `inky_photo_frame.py` (1100 lines) is split into 7 focused modules: `config`, `display`, `image_processor`, `photos`, `buttons`, `welcome`, and `app`. A backward-compatible shim at the original entry point preserves existing systemd service and cron configurations.
- **Automated test suite** -- pytest with hardware mocks (GPIO, SPI, I2C) enables testing without physical Raspberry Pi hardware. A 70% coverage gate is enforced in CI.
- **CI pipeline** -- GitHub Actions runs ruff lint, ruff format, and pytest on every push and pull request
- **Configurable photo rotation interval** -- The `CHANGE_INTERVAL_MINUTES` environment variable replaces the hardcoded daily 5 AM rotation, allowing any interval from minutes to hours

## Breaking Changes

None. v2.0 is fully backward-compatible with v1.x installations:

- The entry-point shim (`inky_photo_frame.py`) continues to work identically -- existing systemd services and cron jobs require no path changes
- `update.sh` handles the migration to the new package structure transparently
- Photos, configuration, and color mode preferences are preserved across the upgrade

## Upgrade

**For users with the CLI installed:**

```
inky-photo-frame update
```

**For users without the CLI:**

```
bash /home/pi/inky-photo-frame/update.sh
```

`update.sh` automatically downloads the new modular package structure alongside the existing entry point. No manual steps are required. Photos stored in `/home/pi/Pictures/` and the color mode preference in `/home/pi/.inky_color_mode.json` are preserved.

## Full Changelog

### Added

- Modular package structure (`inky_photo_frame/` directory) with dedicated modules for config, display, image processing, photo management, buttons, welcome screen, and app orchestration
- Pytest test suite with hardware mocks (`conftest.py`) enabling CI execution without physical GPIO/SPI/I2C hardware
- GitHub Actions CI pipeline running ruff lint, ruff format, and pytest on every push and pull request
- 70% test coverage gate enforced in CI
- `CHANGE_INTERVAL_MINUTES` environment variable for configurable photo rotation intervals

### Changed

- Entry point refactored from direct script execution to package-based invocation; a backward-compatible shim at `inky_photo_frame.py` preserves existing installations

### Fixed

- GPIO button C on 13.3-inch Inky Impression displays reads from GPIO 25 instead of the conflicting GPIO 16 ([#3](https://github.com/mehdi7129/inky-photo-frame/pull/3))

See [CHANGELOG.md](https://github.com/mehdi7129/inky-photo-frame/blob/main/CHANGELOG.md) for the complete version history from v1.0.0 through v2.0.0.
