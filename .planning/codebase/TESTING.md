# Testing Patterns

**Analysis Date:** 2026-02-22

## Test Framework

**Status:** No formal testing framework detected

**What's Missing:**
- No pytest, unittest, or vitest configuration files
- No test files (*.test.py, *_test.py, test_*.py patterns)
- No CI/CD pipeline for automated testing (.github/workflows, .gitlab-ci.yml, etc.)
- No test runner commands in requirements.txt or setup files

**Assessment:** This is a hardware-dependent application (Raspberry Pi with e-ink display). Testing is implicitly conducted through:
1. Manual testing on actual hardware (DisplayManager initialization)
2. Graceful fallback for missing hardware (try/except blocks for GPIO, display)
3. Integration testing via systemd service

## Current Testing Approach

**Hardware Abstraction Strategy:**
The codebase uses conditional imports and graceful degradation to support testing on non-hardware systems:

**Pattern from lines 52-56:**
```python
# Optional GPIO button support
try:
    from gpiozero import Button
    BUTTONS_AVAILABLE = True
except ImportError:
    BUTTONS_AVAILABLE = False
```

**Pattern from lines 190-207 (DisplayManager):**
```python
try:
    from inky.auto import auto
    self._display = auto()
    self._initialized = True
    # ... success logging
except Exception as e:
    logging.error(f'❌ Failed to initialize display: {e}')
    raise
```

**Pattern from lines 543-552 (Font Loading):**
```python
try:
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
    # ... more fonts
except:
    title_font = ImageFont.load_default()
    ip_font = title_font
    # ... fallback fonts
```

## Error Testing Patterns

**Mock/Simulation via Exception Handling:**

The application tests error conditions using try/except simulation:

**GPIO Error Recovery (lines 243-254):**
```python
is_recoverable = any(x in error_msg for x in [
    'gpio', 'spi', 'pins', 'transport', 'endpoint', 'busy'
])

if is_recoverable and attempt < max_attempts:
    wait_time = delay * (backoff ** (attempt - 1))
    logging.warning(f'⚠️ Attempt {attempt}/{max_attempts} failed: {e}')
    logging.info(f'Retrying in {wait_time}s...')
    time_module.sleep(wait_time)
else:
    logging.error(f'❌ Operation failed after {attempt} attempts: {e}')
    raise
```

**Button Controller Error Handling (lines 285-299):**
```python
try:
    self.button_a = Button(gpio_a, bounce_time=0.02)
    # ... setup more buttons
    logging.info(f'✅ Button controller initialized...')
except Exception as e:
    logging.warning(f'⚠️ Could not initialize buttons: {e}')
    # Continue without buttons - graceful degradation
```

**File Operation Error Recovery (lines 700-713):**
```python
for photo_path, added_at in photos_with_dates[:to_delete]:
    # Don't delete the currently displayed photo
    if photo_path == self.history['current']:
        continue

    try:
        Path(photo_path).unlink()
        logging.info(f'Deleted: {Path(photo_path).name}...')
        # ... update history
    except Exception as e:
        logging.error(f'Error deleting {photo_path}: {e}')
        # Continue with next file - don't abort batch operation
```

## State Management Testing

**History Serialization (lines 612-632):**
The application tests state persistence through JSON serialization:

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

            logging.info(f'📚 Loaded history: {len(data["shown"])} shown, {len(data["pending"])} pending')
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

**Thread Safety Verification (lines 636-639, 657):**
```python
def save_history(self):
    """Save history to file"""
    with self.lock:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)
        logging.info('History saved')
```

## Recommended Testing Strategy

### Unit Tests (If Implemented)

**Test candidates using unittest/pytest:**

1. **Color processing functions** (testable without hardware)
   - `_apply_spectra_palette()` - Image quantization logic
   - `_apply_warmth_boost()` - RGB channel adjustments
   - Location: `inky_photo_frame.py` lines 753-819

2. **Photo navigation logic** (can mock history)
   - `next_photo()` - Queue management
   - `previous_photo()` - History stack operations
   - `change_photo()` - Time-based rotation
   - Location: `inky_photo_frame.py` lines 953-1033

3. **Display configuration detection**
   - `detect_display_saturation()` - Config matching logic
   - Location: `inky_photo_frame.py` lines 450-508

4. **History management**
   - `load_history()` - JSON parsing and migration
   - `cleanup_old_photos()` - FIFO deletion logic
   - Location: `inky_photo_frame.py` lines 612-716

### Integration Tests (If Implemented)

**Hardware-adjacent testing:**

1. **File watcher integration**
   - Mock filesystem events with watchdog
   - Test `PhotoHandler.on_created()` and `process_uploads()`
   - Location: `inky_photo_frame.py` lines 341-396

2. **Button controller**
   - Mock gpiozero Button inputs
   - Test button callback sequences
   - Location: `inky_photo_frame.py` lines 263-336

3. **Display initialization sequence**
   - Verify singleton pattern enforcement
   - Test cleanup handlers registration
   - Location: `inky_photo_frame.py` lines 166-227

### Manual Testing (Current Approach)

**Hardware testing checklist (implicit in design):**
- Display initialization on actual Raspberry Pi
- GPIO button functionality (when hardware available)
- SMB share mounting and photo access
- Photo display with color modes
- Service restart and persistence

## Mocking Patterns (If Tests Were Added)

**Recommended approach based on code structure:**

```python
# Mock Display
from unittest.mock import MagicMock, patch

@patch('inky.auto.auto')
def test_display_manager(mock_auto):
    mock_display = MagicMock()
    mock_display.resolution = (800, 480)
    mock_auto.return_value = mock_display

    manager = DisplayManager()
    display = manager.initialize()
    assert display == mock_display
```

```python
# Mock File System Events
from watchdog.events import FileCreatedEvent
from pathlib import Path

def test_photo_handler():
    frame = InkyPhotoFrame()
    handler = PhotoHandler(frame)

    event = FileCreatedEvent('/home/pi/Images/test.jpg')
    handler.on_created(event)
    assert '/home/pi/Images/test.jpg' in handler.pending_photos
```

```python
# Mock History/JSON
import json
from unittest.mock import mock_open, patch

def test_load_history_migration():
    old_format = {'shown': [], 'pending': []}

    with patch('builtins.open', mock_open(read_data=json.dumps(old_format))):
        with patch('pathlib.Path.exists', return_value=True):
            frame = InkyPhotoFrame()
            assert 'photo_metadata' in frame.history
```

## Coverage Gaps (Current Assessment)

**Untested areas:**

| Area | Risk | Why Untested | Priority |
|------|------|-------------|----------|
| `DisplayManager.cleanup()` | Hardware resource leak | Requires SPI/GPIO context | High |
| `ButtonController` callbacks | UI response issues | Requires GPIO hardware | High |
| `display_photo()` with @retry_on_error | Error recovery | Requires SPI failures to simulate | High |
| `cycle_color_mode()` visual output | Display correctness | Requires visual inspection | Medium |
| Multi-photo concurrent uploads | Race conditions | Requires rapid file creation | Medium |
| Storage cleanup at MAX_PHOTOS limit | Data loss risk | Requires 1000+ test images | Low |
| SMB credential file parsing | Auth failures | Depends on file permissions | Low |

## Service-Based Testing (Systemd Integration)

The application is deployed as a systemd service and tested via:

```bash
# Check service status
sudo systemctl status inky-photo-frame

# View live logs
sudo journalctl -u inky-photo-frame -f

# Restart for regression testing
sudo systemctl restart inky-photo-frame
```

This approach validates:
- Startup behavior and initialization
- Crash recovery
- Signal handling (SIGTERM, SIGINT)
- Log output accuracy

## Recommendations for Future Testing

**Phase 1 - Unit Tests:**
1. Add pytest to requirements-dev.txt
2. Create `tests/test_image_processing.py` for color transformation functions
3. Create `tests/test_photo_queue.py` for history and navigation logic

**Phase 2 - Integration Tests:**
1. Mock hardware with `unittest.mock`
2. Create `tests/test_file_watcher.py` for photo detection
3. Create `tests/test_button_controller.py` for GPIO simulation

**Phase 3 - E2E Tests:**
1. Containerized Raspberry Pi environment
2. Actual SMB share and photo uploads
3. Display state verification

**Phase 4 - CI/CD:**
1. GitHub Actions workflow
2. Run unit/integration tests on push
3. Build Docker image for ARM64

---

*Testing analysis: 2026-02-22*
