## Highlights

- **GPIO fix for 13.3" displays** -- Button C now reads GPIO 25 instead of the conflicting GPIO 16, which is active-low on the 13.3" Inky Impression hardware revision ([#3](https://github.com/mehdi7129/inky-photo-frame/pull/3))
- **Modular package architecture** -- The monolithic `inky_photo_frame.py` (1100 lines) is split into 7 focused modules: `config`, `display`, `image_processor`, `photos`, `buttons`, `welcome`, and `app`. A backward-compatible shim at the original entry point preserves existing systemd service and cron configurations.
- **Configurable photo rotation interval** -- The `CHANGE_INTERVAL_MINUTES` constant in `config.py` replaces the hardcoded daily 5 AM rotation, allowing any interval from minutes to hours
- **SMB password management** -- New `inky-photo-frame reset-password` CLI command for credential rotation

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

`update.sh` automatically downloads the new modular package structure alongside the existing entry point. No manual steps are required. Photos stored in `/home/pi/Images/` and the color mode preference in `/home/pi/.inky_color_mode.json` are preserved.

## Full Changelog

### Added

- Modular package structure (`inky_photo_frame/` directory) with dedicated modules for config, display, image processing, photo management, buttons, welcome screen, and app orchestration
- `CHANGE_INTERVAL_MINUTES` constant in `config.py` for configurable photo rotation intervals
- `update.sh` and `install.sh` updated to deploy the new package structure transparently
- `inky-photo-frame reset-password` CLI command for SMB credential rotation

### Changed

- Entry point refactored from direct script execution to package-based invocation; a backward-compatible shim at `inky_photo_frame.py` preserves existing installations

### Fixed

- GPIO button C on 13.3-inch Inky Impression displays reads from GPIO 25 instead of the conflicting GPIO 16 ([#3](https://github.com/mehdi7129/inky-photo-frame/pull/3))

See [CHANGELOG.md](https://github.com/mehdi7129/inky-photo-frame/blob/main/CHANGELOG.md) for the complete version history from v1.0.0 through v2.0.0.
