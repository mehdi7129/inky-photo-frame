# Roadmap: Inky Photo Frame v2.0

## Overview

Inky Photo Frame v2.0 transforms a working 1100-line monolith into a maintainable, testable Python package while keeping every existing user installation intact. The journey moves from repo cleanup and merge of an outstanding hardware fix, through a structured module extraction, to a validated migration script and a CI-enforced test suite — ending with a tagged GitHub Release that closes the gap between the last published tag (v1.0) and the current codebase (v1.1.7+).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Pre-flight Hygiene** - Merge the GPIO hardware fix and clean the repository before any restructuring
- [ ] **Phase 2: Release Preparation** - Write CHANGELOG.md and draft GitHub Release notes independently of the code refactor
- [ ] **Phase 3: Module Extraction** - Split the monolith into a clean Python package with a backward-compatible shim
- [ ] **Phase 4: Migration Validation** - Update and hardware-verify update.sh so existing users upgrade transparently
- [ ] **Phase 5: CI Foundation** - Wire up GitHub Actions, ruff, pyproject.toml, and hardware-mock conftest.py
- [ ] **Phase 6: Test Suite** - Write pure-logic tests for image processing and photo management with a 70% coverage gate

## Phase Details

### Phase 1: Pre-flight Hygiene
**Goal**: The repository is clean, conflict-free, and the GPIO hardware fix is integrated before any structural change
**Depends on**: Nothing (first phase)
**Requirements**: HYGN-01, HYGN-02, HYGN-03
**Success Criteria** (what must be TRUE):
  1. PR #3 is merged and the 13.3" display button C reads from GPIO 25 instead of the conflicting GPIO 16
  2. `git ls-files | grep __pycache__` returns no results and `.gitignore` contains the `__pycache__/` entry
  3. `SUMMARY.md` and `COLOR_CALIBRATION.md` are absent from the repository and no broken links reference them
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Squash merge PR #3 and reconcile local improvements (HYGN-01)
- [ ] 01-02-PLAN.md — Expand .gitignore, remove __pycache__ tracking, delete obsolete docs (HYGN-02, HYGN-03)

### Phase 2: Release Preparation
**Goal**: CHANGELOG.md is current and GitHub Release v2.0 notes are drafted, so release can be published immediately once the code refactor passes validation
**Depends on**: Phase 1
**Requirements**: HYGN-04, RELS-01
**Success Criteria** (what must be TRUE):
  1. CHANGELOG.md contains entries for every version from v1.0 through v2.0 in Keep a Changelog format
  2. A GitHub Release v2.0 draft exists with release notes that accurately describe what changed since v1.0
  3. The release notes reference the GPIO fix (PR #3), the module refactor, and the new test suite as key changes
**Plans**: TBD

Plans:
- [ ] 02-01: Write CHANGELOG.md entries from v1.0 through v2.0
- [ ] 02-02: Draft and publish GitHub Release v2.0

### Phase 3: Module Extraction
**Goal**: The monolith is split into an importable Python package while the entry-point shim and systemd service require zero changes from users
**Depends on**: Phase 1
**Requirements**: STRC-01, STRC-02, STRC-04
**Success Criteria** (what must be TRUE):
  1. An `inky_photo_frame/` package directory exists with modules: `config.py`, `display.py`, `image_processor.py`, `photos.py`, `buttons.py`, `welcome.py`, `app.py`, `__init__.py`, `__main__.py`
  2. `inky_photo_frame.py` at the repo root is a 3-line shim that imports and runs the package — it still executes correctly when invoked directly
  3. The running systemd service requires no `ExecStart` path change and restarts successfully after the package is deployed
  4. `python -c "from inky_photo_frame import config"` succeeds without importing hardware drivers
**Plans**: TBD

Plans:
- [ ] 03-01: Extract config.py (no-dependency module, extracted first)
- [ ] 03-02: Extract display.py, image_processor.py, photos.py, buttons.py, welcome.py
- [ ] 03-03: Extract app.py (orchestrator, extracted last) and write shim + __main__.py

### Phase 4: Migration Validation
**Goal**: Existing users running `update.sh` from a v1.x installation arrive at the v2.0 package structure without any manual steps
**Depends on**: Phase 3
**Requirements**: STRC-03, RELS-02
**Success Criteria** (what must be TRUE):
  1. `update.sh` downloads and deploys the new `inky_photo_frame/` package directory in addition to `inky_photo_frame.py`
  2. Running `update.sh` on a fresh v1.x clone produces a working v2.0 installation with the systemd service running and photos displaying
  3. `inky-photo-frame status` reports the service as active after `update.sh` completes on a v1.x installation
**Plans**: TBD

Plans:
- [ ] 04-01: Update update.sh to handle new package file structure
- [ ] 04-02: Hardware validation — run update.sh on a v1.x installation and verify end-to-end

### Phase 5: CI Foundation
**Goal**: Every push and pull request runs automated lint and test checks, with local pre-commit hooks available for contributors
**Depends on**: Phase 3
**Requirements**: CICD-01, CICD-02, CICD-03, TEST-01
**Success Criteria** (what must be TRUE):
  1. A green CI badge appears on the repository after a passing push — the GitHub Actions workflow runs ruff check, ruff format, and pytest
  2. `pyproject.toml` exists with ruff rules, pytest options, and coverage thresholds configured — `ruff check .` and `pytest` run from the repo root without extra flags
  3. Pre-commit hooks run ruff lint and format on `git commit` when the developer has run `pre-commit install`
  4. `pytest tests/` passes with an empty test file (zero tests, no collection errors) — confirming the hardware mocks in `conftest.py` do not raise ImportError
**Plans**: TBD

Plans:
- [ ] 05-01: Write pyproject.toml (ruff, pytest, coverage configuration)
- [ ] 05-02: Write tests/conftest.py (sys.modules hardware mocks, DisplayManager reset fixture, gpiozero MockFactory fixture)
- [ ] 05-03: Write .github/workflows/ci.yml and .pre-commit-config.yaml

### Phase 6: Test Suite
**Goal**: The package has a pytest suite covering image processing and photo management pure logic, enforced at 70% coverage in CI
**Depends on**: Phase 5
**Requirements**: TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. `pytest tests/ --cov=inky_photo_frame --cov-report=term-missing` reports coverage >= 70% and exits 0
  2. `test_image_processor.py` contains tests for crop, resize, and at least two color mode transformations using `Image.new()` synthetic images — no filesystem I/O
  3. `test_photos.py` contains tests for history rotation, pending queue behavior, and storage cleanup using temp directories — no real photo files required
  4. `test_display.py` contains tests for welcome screen rendering and display retry logic with mocked hardware — no Inky driver import at test time
  5. CI reports a green check on a push that includes all test files, confirming the 70% gate is enforced automatically
**Plans**: TBD

Plans:
- [ ] 06-01: Refactor image_processor.py to separate I/O from pure transform logic, then write test_image_processor.py
- [ ] 06-02: Write test_photos.py (history rotation, pending queue, storage cleanup)
- [ ] 06-03: Write test_display.py (welcome screen, display retry, scheduling logic with mocked hardware)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

Note: Phase 2 (Release Preparation) can be worked in parallel with Phase 3 (Module Extraction) once Phase 1 is complete, since they are independent. Phase 4 depends on Phase 3. Phase 5 depends on Phase 3. Phase 6 depends on Phase 5.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pre-flight Hygiene | 0/2 | Not started | - |
| 2. Release Preparation | 0/2 | Not started | - |
| 3. Module Extraction | 0/3 | Not started | - |
| 4. Migration Validation | 0/2 | Not started | - |
| 5. CI Foundation | 0/3 | Not started | - |
| 6. Test Suite | 0/3 | Not started | - |
