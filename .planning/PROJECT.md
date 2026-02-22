# Inky Photo Frame

## What This Is

A Raspberry Pi-powered photo frame application for Pimoroni Inky Impression e-ink displays (7.3" and 13.3"). It auto-detects the display model, manages photo slideshows with configurable intervals, supports GPIO button controls, and provides SMB file sharing for easy photo uploads from any device.

## Core Value

Photos display reliably on the e-ink screen with correct colors, and the system just works after installation -- no manual intervention needed.

## Current State

**Version:** v2.0.0 (shipped 2026-02-22)
**Codebase:** 1,277 LOC Python across 10 files (9-module package + shim)
**Platform:** Raspberry Pi OS Bookworm, Python 3.11+
**Users:** Active installs via install.sh/update.sh

### Architecture

```
inky_photo_frame.py (4-line shim) -> inky_photo_frame/app.py (orchestrator)
                                       -> config.py (constants)
                                       -> display.py (DisplayManager singleton)
                                       -> image_processor.py (color pipelines)
                                       -> photos.py (PhotoHandler, file watcher)
                                       -> buttons.py (GPIO controller)
                                       -> welcome.py (welcome screen)
```

## Requirements

### Validated

- Auto-detect Inky display models (7.3" Classic, 7.3" Spectra, 13.3" Spectra) -- v1.0
- Photo slideshow with configurable intervals -- v1.0, enhanced v2.0
- GPIO button controls (next, prev, color mode cycle, reset) -- v1.1.0
- SMB file sharing for photo uploads -- v1.0
- Multiple color modes (Pimoroni, Spectra palette, Warmth boost) -- v1.0
- File watcher for real-time new photo detection -- v1.0
- Welcome screen with connection info and credentials -- v1.0
- CLI wrapper (start, stop, status, logs, update, reset-password) -- v1.0, enhanced v2.0
- systemd service management with auto-restart -- v1.0
- Photo history tracking and rotation -- v1.0
- Storage cleanup with configurable limits -- v1.0
- HEIC (iPhone) image format support -- v1.0
- Modular package architecture (9-module package + backward-compatible shim) -- v2.0
- GPIO fix for 13.3" displays (button C on GPIO 25) -- v2.0
- CHANGELOG.md covering v1.0 through v2.0 -- v2.0
- GitHub Release v2.0 published -- v2.0
- install.sh and update.sh updated for modular package -- v2.0

### Active

(No active requirements -- next milestone not yet planned)

### Out of Scope

- pip-installable package (pyproject.toml, setup.py) -- install.sh is the distribution mechanism
- Web interface or remote management -- CLI + buttons is sufficient
- Additional display brands -- Pimoroni Inky only
- Cloud photo sync -- SMB is sufficient
- mypy strict mode -- no type stubs for inky/gpiozero hardware objects
- Multi-Python version CI matrix -- single target: Python 3.11 on RPi OS Bookworm

## Constraints

- **Retro-compatibility**: update.sh must migrate existing installations transparently
- **Package structure**: Simple package with modules, not pip-installable
- **Target platform**: Raspberry Pi OS only (no cross-platform support needed)
- **Hardware dependency**: Tests would need to mock GPIO/SPI/I2C for CI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Simple package, not pip-installable | install.sh is the distribution mechanism | Good -- keeps deployment simple |
| v2.0 as target version | Structural refactoring justifies major bump | Good -- clear break from monolith era |
| Backward-compatible shim | Active users have systemd pointing to inky_photo_frame.py | Good -- zero-change upgrade |
| Leaf modules never import app.py | Prevents circular imports | Good -- clean dependency graph |
| Constructor injection for ButtonController/PhotoHandler | Avoids importing orchestrator from leaf modules | Good -- testable design |
| Lazy hardware imports (inky.auto inside initialize()) | Allows importing config without triggering GPIO | Good -- enables future testing |
| Defer tests/CI to v2.1 | Core value is photo display, not CI badges | Pending -- revisit when adding features |
| CHANGELOG written before code | Enables release draft early | Revisit -- caused false claims that needed fixing |

---
*Last updated: 2026-02-22 after v2.0 milestone*
