# Testing Patterns

**Analysis Date:** 2026-02-22

## Test Framework

**Status:** No formal test framework exists.

**What is absent:**
- No pytest, unittest, or nose configuration files
- No test files matching `test_*.py`, `*_test.py`, or `*.test.py` patterns
- No `tests/` or `spec/` directory
- No CI/CD pipeline (no `.github/workflows/`, `.gitlab-ci.yml`, etc.)
- No test runner commands in `requirements.txt`
- No `requirements-dev.txt` or `setup.cfg` with test extras

**Run Commands:**
```bash
# No test commands defined — these are recommended if tests are added:
pytest tests/                  # Run all tests
pytest tests/ -v               # Verbose output
pytest tests/ --cov=inky_photo_frame  # Coverage report
```

## Current Testing Approach

This is a hardware-dependent embedded application (Raspberry Pi + e-ink display). All testing is manual, conducted on actual hardware. The codebase compensates for the lack of automated testing through extensive graceful degradation patterns.

**Hardware abstraction strategy:** Conditional imports with fallback flags allow the application to import on non-Pi systems (enabling future unit test authoring) without crashing.

**Pattern — optional hardware import (`inky_photo_frame.py` lines 52-56):**
```python
try:
    from gpiozero import Button
    BUTTONS_AVAILABLE = True
except ImportError:
    BUTTONS_AVAILABLE = False
```

**Pattern — optional library inside method (`inky_photo_frame.py` lines 419-425):**
```python
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    logging.info('📱 HEIF support enabled for iPhone photos')
except ImportError:
    logging.info('📱 HEIF support not available')
```

**Pattern — critical display initialization (lines 190-207):**
```python
try:
    from inky.auto import auto
    self._display = auto()
    self._initialized = True
except Exception as e:
    logging.error(f'❌ Failed to initialize display: {e}')
    raise
```

## Embedded Error Recovery Patterns

The application implements error handling that acts as a form of runtime validation, ensuring failures are caught, logged, and handled without crashing.

**Retry logic with exponential backoff (`inky_photo_frame.py` lines 229-257):**
```python
is_recoverable = any(x in error_msg for x in [
    'gpio', 'spi', 'pins', 'transport', 'endpoint', 'busy'
])

if is_recoverable and attempt < max_attempts:
    wait_time = delay * (backoff ** (attempt - 1))
    logging.warning(f'⚠️ Attempt {attempt}/{max_attempts} failed: {e}')
    time_module.sleep(wait_time)
else:
    logging.error(f'❌ Operation failed after {attempt} attempts: {e}')
    raise
```

**Graceful button controller degradation (`inky_photo_frame.py` lines 285-299):**
```python
try:
    self.button_a = Button(gpio_a, bounce_time=0.02)
    # ...
    logging.info(f'✅ Button controller initialized...')
except Exception as e:
    logging.warning(f'⚠️ Could not initialize buttons: {e}')
    # Application continues without buttons
```

**Per-file batch operation isolation (`inky_photo_frame.py` lines 700-713):**
```python
for photo_path, added_at in photos_with_dates[:to_delete]:
    try:
        Path(photo_path).unlink()
        logging.info(f'Deleted: {Path(photo_path).name}...')
    except Exception as e:
        logging.error(f'Error deleting {photo_path}: {e}')
        # Loop continues — single failure does not abort batch
```

## State Persistence (Implicit Contract Testing)

**History JSON serialization with schema migration (`inky_photo_frame.py` lines 612-632):**
The `load_history()` method performs schema migration and validates format on every load:

```python
def load_history(self):
    """Load history from file or create new"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)

            # Migrate old format to new format with metadata
            if 'photo_metadata' not in data:
                data['photo_metadata'] = {}
                logging.info('Migrated history to new format with metadata')

            return data
    else:
        return {
            'shown': [],
            'pending': [],
            'current': None,
            'last_change': None,
            'photo_metadata': {}
        }
```

**Thread-safe history writes (`inky_photo_frame.py` lines 634-639):**
```python
def save_history(self):
    with self.lock:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)
```

## Service-Level Testing (Current Approach)

The application is deployed as a systemd service. Regression testing is performed by restarting the service and observing behavior via logs:

```bash
# Check service health
sudo systemctl status inky-photo-frame --no-pager

# Watch live application logs
sudo journalctl -u inky-photo-frame -f

# Restart for regression testing
sudo systemctl restart inky-photo-frame

# Run diagnostic report (captures system state)
bash /home/pi/inky-photo-frame/diagnostic_report.sh
```

The `diagnostic_report.sh` script collects: system info, hardware interface status, service status, photo counts, Python environment packages, SMB configuration, recent logs, and history file contents.

## Testable Units (When Adding Tests)

The following functions have no hardware dependencies and are candidates for isolated unit tests:

**Color processing (`inky_photo_frame.py` lines 753-819):**
- `_apply_spectra_palette(img)` — PIL image quantization using calibrated palette
- `_apply_warmth_boost(img)` — RGB channel adjustments via `ImageEnhance`

**Photo queue management (`inky_photo_frame.py` lines 718-751, 908-1033):**
- `refresh_pending_list()` — list deduplication and shuffle logic
- `next_photo()` — queue pop and history update
- `previous_photo()` — history stack pop and pending prepend
- `add_to_queue()` — deduplication before append

**Display configuration detection (`inky_photo_frame.py` lines 450-508):**
- `detect_display_saturation()` — config matching against `DISPLAY_CONFIGS` dict

**Timing logic (`inky_photo_frame.py` lines 1095-1120):**
- `should_change_photo()` — datetime comparison in daily vs. interval modes

**History management (`inky_photo_frame.py` lines 612-716):**
- `load_history()` — JSON parsing and schema migration
- `cleanup_old_photos()` — FIFO deletion with metadata tracking

## Recommended Mocking Patterns

**Mock Inky display:**
```python
from unittest.mock import MagicMock, patch

@patch('inky.auto.auto')
def test_display_manager_initialize(mock_auto):
    mock_display = MagicMock()
    mock_display.resolution = (800, 480)
    mock_auto.return_value = mock_display

    manager = DisplayManager()
    display = manager.initialize()
    assert display == mock_display
```

**Mock file system events (watchdog):**
```python
from watchdog.events import FileCreatedEvent

def test_photo_handler_queues_image():
    frame = MagicMock()
    handler = PhotoHandler(frame)

    event = FileCreatedEvent('/home/pi/Images/test.jpg')
    handler.on_created(event)

    assert '/home/pi/Images/test.jpg' in handler.pending_photos
```

**Mock JSON history file:**
```python
import json
from unittest.mock import mock_open, patch

def test_load_history_migration():
    old_format = {'shown': [], 'pending': [], 'current': None, 'last_change': None}

    with patch('builtins.open', mock_open(read_data=json.dumps(old_format))):
        with patch('pathlib.Path.exists', return_value=True):
            # load_history() should add missing 'photo_metadata' key
            result = frame.load_history()
            assert 'photo_metadata' in result
```

**Mock PIL image for color processing:**
```python
from PIL import Image
from unittest.mock import MagicMock, patch

def test_apply_warmth_boost():
    frame = MagicMock()
    frame._apply_warmth_boost = InkyPhotoFrame._apply_warmth_boost.__get__(frame)

    img = Image.new('RGB', (800, 480), color=(128, 128, 128))
    result = frame._apply_warmth_boost(img)

    assert result.size == (800, 480)
    assert result.mode == 'RGB'
```

## Coverage Gaps

| Untested Area | Files | Risk | Priority |
|---|---|---|---|
| `DisplayManager.cleanup()` SPI teardown | `inky_photo_frame.py` lines 215-227 | Hardware resource leak on shutdown | High |
| `@retry_on_error` exponential backoff logic | `inky_photo_frame.py` lines 229-257 | Silent retry failures | High |
| `ButtonController` GPIO callbacks | `inky_photo_frame.py` lines 301-335 | Unresponsive UI buttons | High |
| Concurrent photo uploads (race condition in `PhotoHandler`) | `inky_photo_frame.py` lines 341-396 | State corruption under load | Medium |
| `cycle_color_mode()` visual output | `inky_photo_frame.py` lines 1035-1055 | Wrong colors after mode switch | Medium |
| `should_change_photo()` edge cases at midnight/CHANGE_HOUR boundary | `inky_photo_frame.py` lines 1095-1120 | Photos not rotating at expected time | Medium |
| `cleanup_old_photos()` at `MAX_PHOTOS` limit | `inky_photo_frame.py` lines 652-716 | Oldest photo deleted while currently displayed | Low |
| SMB credentials file parsing in `get_credentials()` | `inky_photo_frame.py` lines 521-532 | Wrong credentials on welcome screen | Low |

## Recommended Testing Roadmap

**Phase 1 — Unit tests (no hardware required):**
- Add `pytest` and `pytest-cov` to a new `requirements-dev.txt`
- Create `tests/test_image_processing.py` — `_apply_spectra_palette()`, `_apply_warmth_boost()`, `process_image()` crop logic
- Create `tests/test_photo_queue.py` — `next_photo()`, `previous_photo()`, `refresh_pending_list()`, `add_to_queue()`
- Create `tests/test_history.py` — `load_history()` migration, `save_history()` serialization, `cleanup_old_photos()` FIFO logic
- Create `tests/test_timing.py` — `should_change_photo()` in daily and interval modes

**Phase 2 — Integration tests with mocks:**
- Create `tests/test_file_watcher.py` — mock `watchdog` events, test `PhotoHandler.on_created()` and `process_uploads()`
- Create `tests/test_display_manager.py` — mock `inky.auto`, verify singleton pattern and cleanup registration
- Create `tests/test_button_controller.py` — mock `gpiozero.Button`, test callback sequences with `busy` flag

**Phase 3 — CI/CD:**
- Add `.github/workflows/test.yml` running unit and integration tests on push
- Gate pull requests on test passage

---

*Testing analysis: 2026-02-22*
