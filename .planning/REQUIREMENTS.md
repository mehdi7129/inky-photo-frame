# Requirements: Inky Photo Frame v2.0

**Defined:** 2026-02-22
**Core Value:** Photos display reliably on the e-ink screen with correct colors, and the system just works after installation

## v1 Requirements

Requirements for v2.0 release. Each maps to roadmap phases.

### Repository Hygiene

- [x] **HYGN-01**: PR #3 merged -- GPIO fix for 13.3" displays integrated into codebase
- [x] **HYGN-02**: `__pycache__/` removed from repo history and added to .gitignore
- [x] **HYGN-03**: Obsolete documentation files removed (SUMMARY.md, COLOR_CALIBRATION.md)
- [ ] **HYGN-04**: CHANGELOG.md updated with all changes from v1.0 through v2.0

### Code Structure

- [ ] **STRC-01**: `inky_photo_frame.py` split into package with modules: config, display, image_processor, photos, buttons, welcome, app
- [ ] **STRC-02**: `inky_photo_frame.py` retained as backward-compatible 3-line shim launcher
- [ ] **STRC-03**: `update.sh` updated to download and deploy new package file structure
- [ ] **STRC-04**: systemd service continues working transparently after modularization (no ExecStart path change)

### Testing

- [ ] **TEST-01**: pytest test suite with `conftest.py` providing GPIO mocks (sys.modules injection + MockFactory) and DisplayManager singleton reset fixture
- [ ] **TEST-02**: Pure logic tests for image processing pipeline (cropping, resizing, color mode transformations)
- [ ] **TEST-03**: Pure logic tests for photo management (history rotation, pending queue, storage cleanup)
- [ ] **TEST-04**: Display logic tests with mocked hardware (welcome screen rendering, display retry, scheduling logic)
- [ ] **TEST-05**: Test coverage gate at 70%+ enforced via pytest-cov

### CI/CD

- [ ] **CICD-01**: GitHub Actions workflow running pytest + ruff check + ruff format on push and pull requests
- [ ] **CICD-02**: `pyproject.toml` configuring ruff rules, pytest options, and coverage thresholds
- [ ] **CICD-03**: pre-commit hooks configured for local ruff lint and format checks

### Release

- [ ] **RELS-01**: GitHub Release v2.0 published with comprehensive release notes
- [ ] **RELS-02**: Backward-compatible `update.sh` migration verified (existing install.sh users update transparently)

## v2 Requirements

Deferred to future releases. Tracked but not in current roadmap.

### Quality

- **QUAL-01**: Type annotations added progressively with mypy gradual checking
- **QUAL-02**: Integration tests running on actual Raspberry Pi hardware

### Features

- **FEAT-01**: Web-based configuration interface
- **FEAT-02**: Remote photo management API

## Out of Scope

| Feature | Reason |
|---------|--------|
| pip-installable package (pyproject.toml packaging) | Wrong delivery model -- install.sh is the distribution mechanism |
| mypy strict mode | No type stubs for inky/gpiozero hardware objects |
| Hardware-in-the-loop CI testing | Disproportionate infrastructure for single-developer project |
| Multi-Python version CI matrix | Single target: Python 3.11 on Raspberry Pi OS Bookworm |
| tox multi-environment testing | Only one Python version targeted |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HYGN-01 | Phase 1 | Complete |
| HYGN-02 | Phase 1 | Complete |
| HYGN-03 | Phase 1 | Complete |
| HYGN-04 | Phase 2 | Pending |
| STRC-01 | Phase 3 | Pending |
| STRC-02 | Phase 3 | Pending |
| STRC-03 | Phase 4 | Pending |
| STRC-04 | Phase 3 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 6 | Pending |
| TEST-03 | Phase 6 | Pending |
| TEST-04 | Phase 6 | Pending |
| TEST-05 | Phase 6 | Pending |
| CICD-01 | Phase 5 | Pending |
| CICD-02 | Phase 5 | Pending |
| CICD-03 | Phase 5 | Pending |
| RELS-01 | Phase 2 | Pending |
| RELS-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-02-22*
*Last updated: 2026-02-22 after roadmap creation — all 18 requirements mapped*
