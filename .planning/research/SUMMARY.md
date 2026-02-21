# Project Research Summary

**Project:** Inky Photo Frame v2
**Domain:** Python hardware project — monolith refactoring + CI/CD for Raspberry Pi e-ink display
**Researched:** 2026-02-22
**Confidence:** HIGH

## Executive Summary

Inky Photo Frame v2 is not a new product — it is a quality improvement milestone for a working, actively-used Raspberry Pi e-ink photo slideshow application. The project currently ships as a 1100-line single-file Python script deployed via `install.sh` with active users and at least one external contributor (PR #3). The research consensus is that v2.0's primary deliverable is a structured Python package split from the monolith, followed by a test suite with GitHub Actions CI. These two things transform the project from a "working script" into a maintainable OSS hardware project that external contributors can trust.

The recommended approach is a dependency-ordered module extraction (config → display → image_processor → photos → buttons → welcome → app), with a critical backward-compatibility constraint: `inky_photo_frame.py` must remain runnable as a thin shim so that existing systemd service installations and `update.sh` work without modification. The package structure follows the flat-layout convention (package at repo root, not `src/`), appropriate for a non-pip-installable project. Testing uses pytest with `sys.modules` hardware mocking in `conftest.py` and the `GPIOZERO_PIN_FACTORY=mock` env var for button testing. Tooling converges on `ruff` for linting/formatting, `pyproject.toml` for configuration, and GitHub Actions on `ubuntu-latest` for CI.

The primary risk is breaking existing user installations during the refactor. Merging PR #3 before any restructuring, maintaining the `inky_photo_frame.py` shim, and thoroughly testing `update.sh` migration on real hardware before tagging v2.0 are non-negotiable safeguards. Secondary risks are the `DisplayManager` singleton polluting test isolation and module-level side effects (logging setup, env var setting) firing unexpectedly on import — both of which must be resolved before any test is written.

---

## Key Findings

### Recommended Stack

The testing stack centers on pytest 9.0.2 + pytest-mock 3.15.1 + pytest-cov 7.0.0 as the standard Python hardware project configuration. Hardware mocking is handled without extra dependencies: `sys.modules` injection in `conftest.py` blocks `ImportError` for `inky`, `RPi.GPIO`, `spidev`, and `smbus2`; the official `GPIOZERO_PIN_FACTORY=mock` env var enables gpiozero's built-in `MockFactory` for `Button` objects. Code quality uses a single tool — ruff 0.15.2 — replacing flake8, isort, and black. All tool configuration centralizes in `pyproject.toml` (used for tool config only, not as a build manifest). CI runs on GitHub Actions with `ubuntu-latest` and `actions/setup-python@v5`.

**Core technologies:**
- pytest 9.0.2: Test runner — industry standard, powerful fixture system, `conftest.py` for shared GPIO mocks
- pytest-mock 3.15.1: Mocker fixture — auto-teardown mock ergonomics, cleaner than raw `@patch`
- pytest-cov 7.0.0: Coverage measurement — integrates with CI for XML/HTML output
- ruff 0.15.2: Linting and formatting — replaces flake8 + black + isort, 10-100x faster, one tool
- mypy 1.19.1: Optional type checking — gradual typing on pure modules only (not enforced in CI)
- pre-commit 4.5.0: Git hooks — documented in CONTRIBUTING but not required (too much friction for hardware hackers)
- GitHub Actions + astral-sh/ruff-action@v3: CI pipeline — free, native to the platform, standard runner

### Expected Features

Research distinguishes between features for the v2.0 release (structural milestone) and features for v2.x (quality discipline). This split is intentional: shipping the structural refactor and release without being blocked by CI configuration issues is the right prioritization.

**Must have — v2.0 release (table stakes):**
- GPIO fix (PR #3) merged — fixes real hardware bug for 13.3" display users; must precede modularization
- Module package structure — the structural reason v2.0 is a major version bump
- `__pycache__` removal from repo — one-time hygiene fix, signals active maintenance
- CHANGELOG.md current through v2.0 — users running `update.sh` need to know what changed
- Obsolete docs removed (`SUMMARY.md`, `COLOR_CALIBRATION.md`) — clean slate for release
- Retro-compatible `update.sh` migration — non-negotiable; cannot break existing installations
- GitHub Release v2.0 published — tags the stable public milestone

**Should have — v2.x (differentiators that grow contributor confidence):**
- Hardware-mocked pytest suite with `conftest.py` — enables contributor validation without physical hardware
- Pure-logic unit tests for image processing pipeline — highest-value tests, zero hardware dependency
- GitHub Actions CI with ruff + pytest — green check on PRs
- `pyproject.toml` with ruff configuration — signals current tooling practices
- Coverage gate (>=70%) — prevents test suite from growing stale

**Defer — future consideration:**
- mypy strict enforcement in CI — too high cost (no stubs for `inky.auto`, `gpiozero`); add type hints incrementally
- Pre-commit hooks — too much setup friction for the target hardware-hacker audience
- Hardware-in-the-loop tests with real Pi — significant infrastructure overhead for a single-developer project
- Automated CHANGELOG generation (commitizen) — overhead not justified; consider after v2.0
- pip-installable PyPI package — explicitly out of scope; `install.sh` is the delivery mechanism

### Architecture Approach

The refactoring is a boundary extraction, not an architectural redesign. The monolith already has implicit layers; the task is to make them explicit as Python modules within a package at the repository root. The import graph is strictly one-directional: `config.py` has no project imports, all domain modules import from `config.py` only, and `app.py` is the sole module that imports from multiple siblings. The entry-point shim (`inky_photo_frame.py`) and the CLI wrapper (`inky-photo-frame-cli`) are unchanged from the user's perspective.

**Major components:**
1. `config.py` — all constants, file paths, display configs, palette data; no project imports; extracted first
2. `display.py` (DisplayManager) — GPIO/SPI/Inky lifecycle, retry decorator; imported by `app.py` only
3. `image_processor.py` — color mode transforms, crop, resize, dithering; pure PIL logic, highest testability value
4. `photos.py` — photo discovery, history persistence, storage cleanup; pure file system logic
5. `buttons.py` (ButtonController + PhotoHandler) — GPIO button callbacks and watchdog file events; both thin input adapters bundled together
6. `welcome.py` — welcome screen rendering; pure PIL, lowest priority extraction
7. `app.py` (InkyPhotoFrame) — orchestrator only, owns `run()` loop; extracted last
8. `inky_photo_frame.py` (shim) — 3-line backward-compatible entry point; kept for systemd and `update.sh`

### Critical Pitfalls

1. **Breaking update.sh for existing users** — Keep `inky_photo_frame.py` as a runnable thin shim that imports the package. Never rename or remove it. The systemd `ExecStart` path must never need editing. Validate `update.sh` on real hardware before tagging v2.0.

2. **DisplayManager singleton poisoning test isolation** — Add an `autouse` pytest fixture in `conftest.py` that resets `DisplayManager._instance = None` before and after every test. Alternatively, refactor to dependency injection in `app.py`'s constructor (preferred long-term).

3. **Module-level side effects on import** — Move `logging.basicConfig(...)` into a `setup_logging()` function called only from the entry point. Never import `inky.auto` at module level in `display.py` — it must live inside `DisplayManager.initialize()` only.

4. **Circular imports after package restructuring** — Draw the dependency graph before writing any `import` statements. `buttons.py` must never import from `app.py`; pass the frame object as a constructor argument. Dependency direction: `main` → `app` → domain modules → `config`.

5. **gpiozero MockFactory not reset between tests** — Create an `autouse` conftest fixture that saves and restores `Device.pin_factory` around every test. Run `pytest --randomly-seed=random` to verify test order independence before every CI push.

6. **`process_image()` coupling I/O to logic** — Split into `load_image(path) -> PIL.Image` (I/O only) and `process_image(img, width, height, mode) -> PIL.Image` (pure function). Tests use `Image.new('RGB', ...)` synthetic images with zero filesystem operations.

---

## Implications for Roadmap

Based on combined research, the following phase structure is recommended. The split between "release" phases and "quality" phases reflects the FEATURES.md finding that CI configuration issues should not block the v2.0 release.

### Phase 1: Pre-flight and Repository Hygiene

**Rationale:** Two actions are blockers for everything else and have zero architectural risk. Merging PR #3 before any file restructuring avoids merge conflict growth. Cleaning `__pycache__` from git history is a one-time operation that gets harder the longer it waits.
**Delivers:** A clean repository baseline and the GPIO hardware fix that unblocks 13.3" display users.
**Addresses:** GPIO fix (PR #3), `__pycache__` removal, obsolete docs removal (`SUMMARY.md`, `COLOR_CALIBRATION.md`)
**Avoids:** The PR #3 merge conflict pitfall (config dict that will move to `display.py`)

### Phase 2: CHANGELOG and Release Preparation

**Rationale:** Release artifacts (CHANGELOG, GitHub Release) are independent of the code refactor and can be drafted in parallel. Completing them early means v2.0 can be tagged immediately after the module refactor passes manual hardware testing.
**Delivers:** CHANGELOG.md covering v1.1.1 through v2.0, GitHub Release notes draft, `install.sh` tagged-release URL update.
**Addresses:** CHANGELOG.md current, GitHub Release v2.0, install.sh fetching from tag not `main`
**Avoids:** Release being blocked by documentation debt after a complex refactor

### Phase 3: Module Extraction (Config-First, Dependency Order)

**Rationale:** This is the core structural work and the primary reason v2.0 is a major version bump. The extraction order is strictly defined by the dependency graph: config first (no dependencies), then display, image_processor, photos, buttons, welcome, and finally app. Each step must leave the application runnable before proceeding to the next. The shim strategy (keeping `inky_photo_frame.py`) must be decided and implemented before the first extraction commit.
**Delivers:** `inky_photo_frame/` Python package with 7 modules + shim entry point, `__main__.py`, package `__init__.py`
**Uses:** Dependency injection pattern (ARCHITECTURE.md), backward-compatible shim pattern (ARCHITECTURE.md)
**Implements:** All 8 architecture components
**Addresses:** Module package structure (table stakes), retro-compatible entry point
**Avoids:** Breaking update.sh (Pitfall 1), circular imports (Pitfall 4), module-level side effects (Pitfall 3)

### Phase 4: update.sh Migration and Hardware Validation

**Rationale:** The retro-compatible `update.sh` migration is the highest-risk feature and must be validated on real Raspberry Pi hardware before tagging v2.0. This is a dedicated phase because a broken migration is a v2.0 release-blocker — it cannot be discovered or fixed after the tag is published.
**Delivers:** Updated `update.sh` with new package module files in `FILES_TO_UPDATE`, `VERSION` grep compatibility confirmed, manual hardware test sign-off.
**Addresses:** Retro-compatible update.sh migration (highest-risk table stake)
**Avoids:** Breaking existing user installations (Pitfall 1), history format incompatibility

### Phase 5: Test Scaffolding and CI Foundation

**Rationale:** Testing requires the package structure to exist first (Phase 3). The scaffolding phase — `conftest.py`, `pyproject.toml`, GitHub Actions workflow — must be completed before any test is written, because the pitfalls (singleton pollution, MockFactory not reset) are infrastructure problems that corrupt every test if not addressed upfront.
**Delivers:** `tests/conftest.py` with hardware mocks and autouse fixtures, `pyproject.toml` with pytest/ruff/coverage config, `.github/workflows/ci.yml` running ruff check + pytest on push/PR.
**Uses:** pytest 9.0.2, pytest-mock 3.15.1, pytest-cov 7.0.0, ruff 0.15.2, GitHub Actions (STACK.md)
**Addresses:** `pyproject.toml` configuration, CI workflow, ruff linting gate
**Avoids:** DisplayManager singleton test pollution (Pitfall 2), gpiozero MockFactory state leakage (Pitfall 5)

### Phase 6: Test Suite — Pure Logic Coverage

**Rationale:** After scaffolding is in place, pure-logic tests for `image_processor.py` and `photos.py` are the highest-value tests to write — they need zero hardware mocks and cover the most complex application logic. The image processing pipeline refactor (separating I/O from pure transform logic) must happen in this phase, before writing tests.
**Delivers:** `test_image_processor.py` with synthetic image tests, `test_photos.py` with history/storage tests, coverage gate at 70%+.
**Addresses:** Hardware-mocked test suite, pure-logic unit tests, coverage gate (v2.x differentiators)
**Avoids:** `process_image()` I/O coupling (Pitfall 6), hardcoded history file path in tests

### Phase Ordering Rationale

- **PR #3 merge first** because the GPIO config dict it touches will move into a module in Phase 3; merge conflict surface grows with each passing day.
- **CHANGELOG and release prep before code refactor** because release artifacts are independent, parallelizable work; having them ready means no delay between "refactor complete" and "v2.0 tagged."
- **Module extraction before tests** because tests require importable, isolated modules; testing a monolith is possible but yields brittle tests that must be rewritten after the split.
- **update.sh validation as its own phase** because it is the highest-risk deliverable and requires physical hardware — it cannot be embedded in another phase without creating an awkward validation dependency.
- **Scaffolding before tests** because all known test pitfalls (singleton pollution, MockFactory state) are infrastructure problems; writing tests before the fixture infrastructure exists produces unreliable results.
- **Pure-logic tests last** because they depend on the image_processor.py I/O/logic split being done correctly in Phase 3; once the refactor is clean, the tests themselves are straightforward.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (update.sh migration):** The migration script behavior with existing v1.x installations has edge cases that are hard to predict without inspecting real user environments. Plan for a "migration dry-run" flag or a rollback mechanism.
- **Phase 5 (CI Foundation):** The exact `sys.modules` injection list for `conftest.py` may need adjustment once the real import chain is visible post-extraction; run `python -c "import inky_photo_frame"` in CI to surface hidden imports.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Pre-flight):** git operations and file cleanup — no research needed.
- **Phase 2 (CHANGELOG):** Keep a Changelog format is well-documented and established.
- **Phase 3 (Module extraction):** Config-first extraction order and backward-compatible shim are well-documented patterns; ARCHITECTURE.md provides the complete build order with code examples.
- **Phase 6 (Tests):** pytest patterns and `Image.new()` synthetic image testing are standard; PITFALLS.md provides the conftest.py fixtures verbatim.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI as of 2026-02-22. Official docs confirm GitHub Actions patterns. gpiozero MockFactory is documented and stable since v1.6. |
| Features | HIGH | Grounded in direct code inspection of the 1100-line monolith, PR #3, and explicit PROJECT.md scope constraints. Feature prioritization is unambiguous given the active-user and single-developer context. |
| Architecture | HIGH | Import graph and module boundaries derived from primary sources (current codebase + update.sh + install.sh). Shim constraint is a hard requirement backed by real `update.sh` grep patterns. |
| Pitfalls | HIGH | Pitfalls 1-4 are derived from direct code inspection. Pitfalls 5-6 are verified against gpiozero official documentation. All pitfalls have concrete prevention strategies with code examples. |

**Overall confidence: HIGH**

### Gaps to Address

- **update.sh edge cases on existing installations:** The research identifies the general migration strategy but cannot enumerate all edge cases (e.g., users with custom `INSTALL_DIR`, users on non-standard Pi OS versions). Address by running `update.sh` on a fresh v1.x clone before tagging v2.0, not just on the development machine.
- **mypy stubs for inky and gpiozero:** If gradual type hinting is adopted, the absence of official stubs for `inky.auto` and `gpiozero` means `ignore_missing_imports = true` is required in `mypy.ini`. This limits mypy's value for the hardware-integration modules; pure logic modules (`image_processor`, `config`, `photos`) benefit most.
- **Coverage gate achievability:** 70% coverage is stated as the target, but the actual achievable coverage depends on how many hardware-dependent paths can be excluded with `# pragma: no cover`. Validate the coverage number after the first test run before enforcing it as a CI gate.

---

## Sources

### Primary (HIGH confidence)
- Current codebase: `/Users/mehdiguiard/Desktop/INKY_V2/inky_photo_frame.py` (1100 lines, read in full, 2026-02-22)
- `update.sh`, `install.sh`, `inky-photo-frame-cli` — backward-compat constraints (direct inspection)
- [pytest 9.0.2 — PyPI](https://pypi.org/project/pytest/) — version verified 2026-02-22
- [ruff 0.15.2 — PyPI](https://pypi.org/project/ruff/) — version verified 2026-02-22
- [gpiozero MockFactory API — official docs](https://gpiozero.readthedocs.io/en/stable/api_pins.html) — MockFactory and testing patterns confirmed
- [Ruff integrations — astral.sh official docs](https://docs.astral.sh/ruff/integrations/) — ruff-action@v3 confirmed
- [GitHub Actions Python — official docs](https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python) — setup-python@v5 confirmed
- [Hitchhiker's Guide to Python — Structuring Your Project](https://docs.python-guide.org/writing/structure/) — flat layout for non-pip projects
- [Real Python — Python Application Layouts](https://realpython.com/python-application-layouts/) — package-at-root pattern
- [src layout vs flat layout — Python Packaging User Guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) — official guidance
- [Keep a Changelog](https://keepachangelog.com/en/0.3.0/) — CHANGELOG format standard

### Secondary (MEDIUM confidence)
- [pi-top Python SDK conftest.py](https://github.com/pi-top/pi-top-Python-SDK/blob/master/conftest.py) — sys.modules injection pattern for hardware mocks
- [GitHub Actions Python 2025 — Alberto Cámara](https://ber2.github.io/posts/2025_github_actions_python/) — 2025 workflow patterns
- [GPIO Zero Testing documentation — DeepWiki](https://deepwiki.com/gpiozero/gpiozero/6.1-testing) — MockFactory pattern
- [Testing Python applications on Raspberry Pi (woteq)](https://woteq.com/how-to-test-python-applications-running-on-raspberry-pi-with-pytest/) — concrete mocking examples
- [Breadcrumbs Collector — Modular Monolith in Python](https://breadcrumbscollector.tech/modular-monolith-in-python/) — extraction patterns
- [Python circular import patterns — Builtin](https://builtin.com/articles/python-circular-import) — import direction principles
- [Singleton anti-pattern and testability — The New Stack](https://thenewstack.io/unmasking-the-singleton-anti-pattern/) — singleton reset strategies
- [Pimoroni inky GitHub repository](https://github.com/pimoroni/inky) — CI pattern reference

### Tertiary (LOW confidence)
- [Python project maturity checklist (michal.karzynski.pl, 2019)](https://michal.karzynski.pl/blog/2019/05/26/python-project-maturity-checklist/) — partially outdated, used only for checklist framing

---

*Research completed: 2026-02-22*
*Ready for roadmap: yes*
