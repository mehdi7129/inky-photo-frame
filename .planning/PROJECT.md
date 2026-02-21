# Inky Photo Frame v2.0

## What This Is

A Raspberry Pi-powered photo frame application for Pimoroni Inky Impression e-ink displays (7.3" and 13.3"). It auto-detects the display model, manages photo slideshows with configurable intervals, supports GPIO button controls, and provides SMB file sharing for easy photo uploads from any device.

## Core Value

Photos display reliably on the e-ink screen with correct colors, and the system just works after installation -- no manual intervention needed.

## Requirements

### Validated

- Auto-detect Inky display models (7.3" Classic, 7.3" Spectra, 13.3" Spectra) -- existing
- Photo slideshow with configurable intervals (daily or minutes-based) -- existing
- GPIO button controls (next, prev, color mode cycle, reset) -- existing
- SMB file sharing for photo uploads -- existing
- Multiple color modes (Pimoroni, Spectra palette, Warmth boost) -- existing
- File watcher for real-time new photo detection -- existing
- Welcome screen with connection info and credentials -- existing
- CLI wrapper (inky-photo-frame command with start, stop, status, logs, update, reset-password) -- existing
- systemd service management with auto-restart -- existing
- Photo history tracking and rotation -- existing
- Storage cleanup with configurable limits -- existing
- HEIC (iPhone) image format support -- existing
- Password reset command -- existing (v1.1.7)
- Configurable change interval in minutes -- existing (v1.1.7)
- LED disable via systemd service -- existing (v1.1.7)

### Active

- [ ] Merge PR #3: GPIO fix for 13.3" displays (button C on GPIO 25 instead of conflicting GPIO 16)
- [ ] Modularize inky_photo_frame.py (1100 lines) into a clean multi-module package
- [ ] Add unit tests with GPIO mocking and pure logic tests
- [ ] Add CI/CD pipeline via GitHub Actions
- [ ] Clean __pycache__ from repo and add to .gitignore
- [ ] Clean obsolete documentation files (SUMMARY.md, COLOR_CALIBRATION.md)
- [ ] Update CHANGELOG.md to reflect all changes since v1.0
- [ ] Release v2.0 on GitHub

### Out of Scope

- pip-installable package (pyproject.toml, setup.py) -- keep it simple, direct module imports
- Web interface or remote management -- not needed, CLI + buttons is enough
- Additional display brands -- Pimoroni Inky only
- Cloud photo sync -- SMB is sufficient

## Context

- The project has active users who installed via install.sh on Raspberry Pi
- PR #3 from an external contributor fixes a real hardware conflict on 13.3" displays
- The codebase grew organically to 1100 lines in a single file -- functional but hard to maintain
- No tests exist -- changes are manually tested on hardware
- GitHub releases stopped at v1.0 while code progressed to v1.1.7 via commits
- The project runs on Raspberry Pi OS (Bookworm) with Python 3, GPIO, SPI, I2C

## Constraints

- **Retro-compatibility**: update.sh must migrate existing installations transparently -- no breaking changes
- **Package structure**: Simple package with modules, not pip-installable
- **Hardware dependency**: Tests must mock GPIO/SPI/I2C for CI -- no Raspberry Pi needed in GitHub Actions
- **Test priority**: Image processing pipeline and display logic are the most critical to cover
- **Target platform**: Raspberry Pi OS only (no cross-platform support needed)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Package simple, pas pip-installable | L'install se fait via install.sh, pas besoin de complexifier | -- Pending |
| Mock GPIO pour les tests CI | Le hardware n'est pas disponible dans GitHub Actions | -- Pending |
| Garder CHANGELOG.md dans le repo | Source de verite pour l'historique, en complement des release notes | -- Pending |
| v2.0 comme version cible | Le refactoring structurel justifie un bump majeur | -- Pending |
| Retro-compatible obligatoire | Des utilisateurs ont deja installe via install.sh | -- Pending |

---
*Last updated: 2026-02-22 after initialization*
