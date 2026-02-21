# Pitfalls Research

**Domain:** Python monolith refactoring + hardware-dependent CI/CD (Raspberry Pi e-ink photo frame)
**Researched:** 2026-02-22
**Confidence:** HIGH (code inspected directly, hardware patterns verified via gpiozero docs and community)

---

## Critical Pitfalls

### Pitfall 1: Breaking update.sh for Existing Users

**What goes wrong:**
The refactored code changes the entry point from `inky_photo_frame.py` (a single runnable script) to a package (e.g., `inky_photo_frame/main.py` or `inky_photo_frame/__main__.py`). The existing systemd service file hard-codes the old path:

```
ExecStart=/home/pi/.virtualenvs/pimoroni/bin/python /home/pi/inky-photo-frame/inky_photo_frame.py
```

When `update.sh` downloads the new code, the service still points to the old path. Existing users who run `inky-photo-frame update` get a broken service with no photo output and no obvious error — it just silently fails to start or starts the wrong file.

**Why it happens:**
The update script only downloads files — it does not update the systemd unit. Since the service was installed during the original install, it is not touched again by update.sh. Moving from a flat file to a package changes the invocation method invisibly.

**How to avoid:**
- Keep `inky_photo_frame.py` as the runnable entry point for the systemd service. It becomes a thin launcher that imports and runs the package: `from inky_photo_frame import main; main.run()`. The service ExecStart path never changes.
- OR: update.sh must explicitly update the systemd unit file with `sudo tee /etc/systemd/system/inky-photo-frame.service` and run `sudo systemctl daemon-reload` after every update. This is fragile and error-prone.
- The thin-launcher approach is strongly preferred: zero changes to install.sh, update.sh, or any installed service files.

**Warning signs:**
- The plan includes renaming or removing `inky_photo_frame.py`
- The plan creates a package at `inky_photo_frame/` without a flat entry-point shim
- update.sh does not call `systemctl daemon-reload`

**Phase to address:**
Module decomposition phase — decide entry-point strategy before splitting anything.

---

### Pitfall 2: The DisplayManager Singleton Poisons Test Isolation

**What goes wrong:**
`DisplayManager` is a module-level singleton (`_instance = None` class variable). Once initialized in one test, `_instance` persists across all subsequent tests in the same process. Tests that expect a fresh display object get the already-initialized one, including any state from previous tests. Mocking `inky.auto.auto` in one test does not reset the singleton, so the next test gets the real (or previously mocked) display object.

**Why it happens:**
Module-level class variables in Python are cached for the lifetime of the process. `_instance` is never reset between tests unless explicitly cleared. This is a known anti-pattern: "singletons carry state between tests and you can't easily mock a singleton" (multiple sources confirm).

**How to avoid:**
Add a `reset()` classmethod to `DisplayManager` and call it in a pytest `autouse` fixture:
```python
@pytest.fixture(autouse=True)
def reset_display_manager():
    DisplayManager._instance = None
    DisplayManager._display = None
    DisplayManager._initialized = False
    yield
    DisplayManager._instance = None
    DisplayManager._display = None
    DisplayManager._initialized = False
```
Alternatively, refactor `DisplayManager` out of the singleton pattern and inject it as a dependency into `InkyPhotoFrame.__init__`. Dependency injection eliminates hidden state and gives each test a fresh, isolated instance.

**Warning signs:**
- Tests pass individually but fail when the full suite runs
- `DisplayManager.get_display()` returns an unexpected type in later tests
- Test order matters for test outcomes

**Phase to address:**
Test scaffolding phase — this must be solved before writing any tests for `InkyPhotoFrame`.

---

### Pitfall 3: Module-Level Side Effects Fire on Import

**What goes wrong:**
`inky_photo_frame.py` runs `logging.basicConfig(...)` at import time (module level, not inside a function or `if __name__ == '__main__'`). It also sets `os.environ['INKY_SKIP_GPIO_CHECK'] = '1'` at the top. When tests import anything from the refactored package, these side effects fire immediately — potentially overwriting the test's own logging configuration or polluting the environment for unrelated tests.

More critically: if `from inky.auto import auto` triggers any hardware probe (I2C/SPI scan), even an `import` statement will fail in CI where the hardware devices do not exist.

**Why it happens:**
In a single-file script, module-level code runs once when the script starts, and that is expected. When the same code is split into modules that are imported by other modules and by tests, every import triggers those side effects again.

**How to avoid:**
- Move `logging.basicConfig(...)` into a `setup_logging()` function called only from the entry point (`if __name__ == '__main__'` or the thin launcher).
- Wrap `from inky.auto import auto` inside `DisplayManager.initialize()` (it already is — keep it there and do not add any top-level inky imports).
- The `os.environ` line is acceptable at module level since it guards the inky import, but document it explicitly.
- Use `pytest`'s `importmode=importlib` (in `pytest.ini`) to avoid unexpected import side effects from module caching.

**Warning signs:**
- Tests produce unexpected log output mixed with test output
- `import inky_photo_frame.display` fails in CI with `FileNotFoundError: /dev/i2c-1`
- CI log shows "Initializing display..." during test collection

**Phase to address:**
Module decomposition phase — before writing tests, audit every module-level statement.

---

### Pitfall 4: Circular Imports After Package Restructuring

**What goes wrong:**
When splitting the 1100-line file into modules (e.g., `display.py`, `buttons.py`, `slideshow.py`, `photo_handler.py`), it is tempting to use a shared `config.py` or to import from `__init__.py`. If `slideshow.py` imports from `buttons.py` and `buttons.py` imports from `slideshow.py` (e.g., via a back-reference to `InkyPhotoFrame`), Python raises `ImportError: cannot import name X from partially initialized module`.

The current code has this risk: `ButtonController.__init__` takes `photo_frame` as a parameter (direct object reference), and `PhotoHandler` takes `slideshow` as a parameter. These circular references in the object graph do not cause circular imports, but if they are expressed as module-level imports, they will.

**Why it happens:**
The natural boundary appears to be "each class = one file," but the classes have direct back-references. Developers then add `from inky_photo_frame.slideshow import InkyPhotoFrame` inside `buttons.py`, creating a cycle. This is the most common mistake when converting a single-file class hierarchy into a package.

**How to avoid:**
- Keep the dependency injection pattern already used: pass objects as constructor arguments, never import the other class's module.
- Use a `types.py` or `interfaces.py` module for any shared type hints. Use `from __future__ import annotations` and `TYPE_CHECKING` for type-hint-only imports.
- Module dependency direction must be one-way: `main` → `slideshow` → `display`; `main` → `buttons` → nothing from `slideshow`; `main` → `photo_handler` → nothing from `buttons`.
- Draw the dependency graph before writing any import statements.

**Warning signs:**
- `ImportError: cannot import name X from partially initialized module Y`
- Any file that imports from two other package files at the same level
- `__init__.py` that imports from multiple submodules simultaneously

**Phase to address:**
Module decomposition phase — define import direction before writing any new files.

---

### Pitfall 5: gpiozero MockFactory Not Reset Between Tests

**What goes wrong:**
`gpiozero` uses a global pin factory (`Device.pin_factory`). If a test sets `Device.pin_factory = MockFactory()` and does not reset it afterwards, subsequent tests may use the wrong factory — or, more dangerously, the real hardware factory if a test accidentally resets to the default. Symptoms: tests that pass alone fail when run in sequence; `PinInvalidPin` errors appear in unrelated tests.

**Why it happens:**
`Device.pin_factory` is a class-level attribute on `gpiozero.Device`. It persists for the life of the process. `MockFactory.reset()` clears pin reservations but does not restore the original factory.

**How to avoid:**
Use a pytest fixture in `conftest.py` (HIGH confidence, verified against gpiozero official docs):
```python
import pytest
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

@pytest.fixture(autouse=True)
def mock_gpio():
    original_factory = Device.pin_factory
    Device.pin_factory = MockFactory()
    yield Device.pin_factory
    Device.pin_factory.reset()
    Device.pin_factory = original_factory
```
This fixture must be in `conftest.py` at the test root, not in individual test files, so it applies to all tests automatically.

**Warning signs:**
- `gpiozero.exc.PinInvalidPin` in tests that do not use GPIO directly
- Tests pass with `pytest tests/test_buttons.py` but fail with `pytest tests/`
- `ButtonController` tests leave mock pins in a "reserved" state

**Phase to address:**
Test scaffolding phase — conftest.py must be the first test file created.

---

### Pitfall 6: Testing `process_image()` Requires Real Image Files

**What goes wrong:**
`InkyPhotoFrame.process_image()` calls `Image.open(image_path)` with a real file path. Tests that mock the path or pass a non-existent path get `FileNotFoundError`. Tests that pass a minimal 1x1 PNG get unexpected results because the aspect-ratio crop math depends on image dimensions. The image processing pipeline is the most critical code to test (per PROJECT.md constraints), but the tests become fragile if they depend on specific test fixture images.

**Why it happens:**
`process_image` is written as a method that takes a file path, not an image object. Pure image-processing logic (crop math, color mode application) is tightly coupled to file I/O. Splitting them apart requires refactoring the method signature, which is a change that must not alter behavior.

**How to avoid:**
Refactor `process_image` into two layers during the decomposition phase:
1. `load_image(path) -> PIL.Image` — handles file I/O and HEIC registration (easy to mock)
2. `process_image(img: PIL.Image, width, height, color_mode, is_spectra) -> PIL.Image` — pure function, no I/O

The pure function can be tested with `Image.new('RGB', (1200, 900))` (synthetic images), making tests deterministic and fast. The file-I/O layer can be tested with a real 2x2 PNG fixture in `tests/fixtures/`.

**Warning signs:**
- Tests import `os` or `pathlib.Path` to create temp image files
- Test files grow to > 50 lines of setup before the first assertion
- `process_image` tests are skipped in CI because they are "too slow"

**Phase to address:**
Test writing phase — but the refactoring of `process_image` must happen in the decomposition phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep module-level `logging.basicConfig` | No refactoring needed | Log output bleeds into test output; reconfiguration silently ignored | Never — move to entry point |
| Mock `inky.auto` at the class level in tests | Simple patch | Patch must be replicated in every test file; breaks on refactor | Only in integration tests |
| Skip testing `display_welcome()` | Avoids font file dependency in CI | Welcome screen bugs only discovered manually on device | Acceptable for MVP test phase |
| Use `unittest.mock.patch` instead of dependency injection | Faster to write | Brittle — sensitive to import path of the mock target | Acceptable short-term, refactor later |
| Keep `HISTORY_FILE`, `PHOTOS_DIR` as module globals | No change needed | Tests that write history interfere with each other | Never — inject as parameters or use `tmp_path` fixture |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `inky.auto.auto()` | Import at module level in `display.py` | Import inside `DisplayManager.initialize()` only — never at module level |
| `gpiozero.Button` | Instantiate `Button` in `ButtonController.__init__` with no factory set | Set `Device.pin_factory = MockFactory()` before any `Button()` is constructed |
| `pillow_heif.register_heif_opener()` | Called unconditionally in `__init__` | Already guarded by `try/except ImportError` — keep this pattern in the refactored version |
| `watchdog.observers.Observer` | Started in `run()` — not mockable unless extracted | Extract observer creation to a method; pass `observer_class` as a parameter for testing |
| History JSON file | Tests write to `/home/pi/.inky_history.json` (hardcoded path) | Replace `HISTORY_FILE` global with a constructor parameter; use `pytest`'s `tmp_path` fixture |
| `socket.connect("8.8.8.8", 80)` | Hangs or raises in CI (no network) | Wrap in `try/except` with timeout (already done); ensure mock replaces `socket.socket` in tests |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `get_all_photos()` called on every `should_change_photo()` check | 60s × number of photos = disk thrash | Cache the photo list, invalidate on watchdog event | >200 photos in `/home/pi/Images` |
| `cleanup_old_photos()` iterates all photos AND all history | O(n²) membership checks via `list.remove()` | Use `set` for `shown` and `pending` in history (requires history format migration) | >500 photos |
| Floyd-Steinberg dithering on 1600×1200 images (13.3" display) | `_apply_spectra_palette()` takes 10-30s | No change needed for production (e-ink refresh is 15s anyway) | Not a performance trap — acceptable |
| `save_history()` called after every photo operation | Frequent disk writes on SD card | Already has `with self.lock:` — acceptable; SD card wear is minimal | Not a concern at current scale |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Credentials stored in `/home/pi/.inky_credentials` as plain text | Any process running as `pi` can read SMB password | Acceptable for this use case — no sensitive data, local network only; document the assumption |
| `install.sh` fetches from `raw.githubusercontent.com/main` (always latest) | A broken commit on `main` immediately breaks all new installs | Tag releases; install.sh should fetch from a tagged release, not `main` branch — note this as a v2.0 release task |
| No validation of downloaded files in `update.sh` | Corrupted download silently replaces working code | The existing rollback logic partially mitigates; add `sha256sum` check for critical files (low priority) |

---

## "Looks Done But Isn't" Checklist

- [ ] **Module split complete:** Verify `inky_photo_frame.py` (entry point shim) still runs `python inky_photo_frame.py` identically to before — the systemd service must not need editing
- [ ] **Tests pass in CI:** Ensure the GitHub Actions workflow runs on `ubuntu-latest` (not ARM), which means GPIO and inky must be fully mocked — verify with `GPIOZERO_PIN_FACTORY=mock` environment variable set in the workflow
- [ ] **History file migration:** The refactored code must handle existing `/home/pi/.inky_history.json` files from v1.x — test `load_history()` with a v1 format file missing `photo_metadata`
- [ ] **Color mode persistence:** `/home/pi/.inky_color_mode.json` must survive the update — test that `load_color_mode()` works after a cold start
- [ ] **gpiozero pin factory reset:** Confirm `Device.pin_factory` is restored after every test — run `pytest --randomly-seed=12345` to verify test order does not affect results
- [ ] **`__pycache__` excluded:** `.gitignore` must cover `**/__pycache__/` and `**/*.pyc` before committing the new package structure
- [ ] **Version bump visible:** `VERSION` string must be updated to `2.0.0` and the `update.sh` version-detection grep (`grep "^VERSION = "`) must still work in the refactored code

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Broke existing installs via update.sh | HIGH | Release a hotfix tag; update install.sh to point to hotfix; post issue on GitHub; add rollback note to README |
| Singleton state leaks between tests | LOW | Add `autouse` fixture to conftest.py; re-run test suite |
| Circular import at package level | MEDIUM | Remove the circular import; use TYPE_CHECKING guard; add an `interfaces.py` for shared types |
| CI fails because inky import hits hardware | MEDIUM | Set `GPIOZERO_PIN_FACTORY=mock` and mock `inky.auto` in the CI workflow env vars; add `sys.modules` patching in conftest.py |
| History format incompatible after refactor | HIGH | Restore `load_history()` migration shim; deploy a patch; existing users may lose history state |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Breaking update.sh for existing users | Module decomposition — decide entry-point strategy first | `python inky_photo_frame.py` works without editing systemd service |
| DisplayManager singleton test pollution | Test scaffolding — write conftest.py before any tests | All tests pass with `pytest --randomly-seed=random` (order-independent) |
| Module-level side effects on import | Module decomposition — audit before splitting | `python -c "import inky_photo_frame.display"` exits with code 0 in CI |
| Circular imports | Module decomposition — draw dependency graph before coding | `python -m py_compile inky_photo_frame/*.py` passes in CI |
| gpiozero MockFactory not reset | Test scaffolding — conftest.py autouse fixture | `pytest -x tests/` passes without hardware on any OS |
| `process_image()` couples I/O and logic | Module decomposition — split into load + process | `test_process_image.py` contains zero filesystem operations |
| History file hardcoded path | Test writing — use `tmp_path` fixture | No test writes to `/home/pi/` |

---

## Sources

- gpiozero official documentation — MockFactory and testing patterns: https://gpiozero.readthedocs.io/en/stable/api_pins.html#mock-pins
- gpiozero development guide (CI testing patterns): https://gpiozero.readthedocs.io/en/stable/development.html
- Python circular import patterns: https://builtin.com/articles/python-circular-import
- Python import traps (official Python notes): https://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html
- Singleton anti-pattern and testability: https://thenewstack.io/unmasking-the-singleton-anti-pattern/
- Refactoring monolithic code: https://understandlegacycode.com/blog/another-way-of-refactoring-untested-code/
- Direct code inspection: `/Users/mehdiguiard/Desktop/INKY_V2/inky_photo_frame.py` (1100 lines, read in full)
- Direct infrastructure inspection: `install.sh`, `update.sh`, `requirements.txt`

---

*Pitfalls research for: Python monolith refactoring + hardware-dependent CI/CD on Raspberry Pi*
*Researched: 2026-02-22*
