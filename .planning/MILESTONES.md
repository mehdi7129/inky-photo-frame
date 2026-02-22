# Milestones

## v2.0 Package Refactor (Shipped: 2026-02-22)

**Phases completed:** 3 phases, 7 plans
**Python LOC:** 1,277 lines across 10 files
**Git range:** 9c7d251..5c27203 (43 files changed, +4986/-2070)
**Timeline:** 1 day (2026-02-22)

**Key accomplishments:**
- Merged PR #3 GPIO fix for 13.3" displays (button C GPIO 25 instead of conflicting GPIO 16)
- Split 1,216-line monolith into 9-module Python package with backward-compatible 4-line shim
- Published CHANGELOG.md (v1.0.0 through v2.0.0) and GitHub Release v2.0.0
- Updated install.sh and update.sh for modular package deployment
- Hardware-verified: fresh install, welcome screen, SMB upload, GPIO buttons, CLI commands

**Known gaps (deferred to v2.1):**
- TEST-01-05: pytest test suite with hardware mocks and 70% coverage gate
- CICD-01-03: GitHub Actions CI, pyproject.toml, pre-commit hooks
- RELS-02: update.sh migration from v1.x never formally tested

---

