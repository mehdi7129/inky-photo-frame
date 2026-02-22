# Inky Photo Frame - Project Guidelines

## Overview

Universal e-ink photo frame for Raspberry Pi with Inky Impression displays (7.3" and 13.3"). Photos are uploaded via SMB network share and displayed automatically.

## Architecture

Modular Python package (`inky_photo_frame/`) with a backward-compatible shim at the repo root:

```
inky_photo_frame.py          -> 4-line shim (systemd entry point)
inky_photo_frame/
  config.py                  -> Constants, DISPLAY_CONFIGS, setup_logging()
  display.py                 -> DisplayManager singleton, retry_on_error decorator
  image_processor.py         -> process_image() with explicit params
  photos.py                  -> PhotoHandler (watchdog), get_all_photos(), load_history()
  buttons.py                 -> ButtonController (guarded GPIO import)
  welcome.py                 -> Welcome screen rendering
  app.py                     -> InkyPhotoFrame orchestrator (imports all modules)
  __init__.py                -> Exports __version__ only
  __main__.py                -> python -m entry point
```

## Key Design Decisions

- **No circular imports**: Leaf modules import only from `config.py`, never from `app.py`. ButtonController and PhotoHandler use constructor injection.
- **Lazy hardware imports**: `from inky.auto import auto` is inside `DisplayManager.initialize()`, never at module level.
- **setup_logging() is a function**: Called in `InkyPhotoFrame.__init__()`, not at import time.
- **os.environ['INKY_SKIP_GPIO_CHECK']**: Must be set at top of `config.py` before any other import.
- **Shim compatibility**: `inky_photo_frame.py` at repo root preserves `systemd ExecStart` path unchanged.

## Development

- Python 3.11+ on Raspberry Pi OS Bookworm
- Dependencies managed via virtualenv at `~/.virtualenvs/pimoroni/`
- Hardware: Inky Impression 7.3" (800x480, 7 colors) and 13.3" (1600x1200, 6 colors)
- SPI + I2C required, plus `dtoverlay=spi0-1cs,cs0_pin=7` in boot config

## Deployment

- **Install**: `curl -sSL https://raw.githubusercontent.com/mehdi7129/inky-photo-frame/main/install.sh | bash`
- **Update**: `inky-photo-frame update` (CLI) or `bash ~/inky-photo-frame/update.sh`
- **Service**: `systemd` unit `inky-photo-frame.service`, auto-starts at boot
- **SMB**: Samba share `Images` at `/home/pi/Images`, credentials in `/home/pi/.inky_credentials`

## Conventions

- Commit messages: `type(scope): description` (feat, fix, docs, refactor)
- No tests on hardware-dependent code paths without mocks
- Preserve all emoji log prefixes in app.py
- Keep shim at exactly 4 lines (shebang + docstring + import + call)
