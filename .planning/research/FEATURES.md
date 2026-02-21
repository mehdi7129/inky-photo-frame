# Feature Research

**Domain:** Python hardware project quality improvement (Raspberry Pi e-ink photo frame)
**Researched:** 2026-02-22
**Confidence:** HIGH

## Context

This is not a new product feature set — it is a code quality improvement milestone for an existing,
functioning application. The framing of "table stakes / differentiators / anti-features" maps to:

- **Table stakes**: What a well-maintained open-source Python hardware project must have to be taken
  seriously by contributors and users.
- **Differentiators**: Quality investments that distinguish a hobbyist script from a production-grade
  OSS project for a specific hardware ecosystem.
- **Anti-features**: Practices that seem useful but add complexity without proportional benefit, or
  are explicitly out of scope.

The project has active users (install.sh-based), an external contributor (PR #3), and aims for a
v2.0 release. These three facts define the minimum quality bar.

---

## Feature Landscape

### Table Stakes (Quality Practices Every Serious Python OSS Project Must Have)

Features/practices that serious OSS maintainers and contributors expect. Missing these signals an
unmaintained or prototype-grade project.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Module package structure | A 1210-line single file is unmaintainable. Modules allow isolated changes and isolated testing. Every serious OSS Python project splits concerns into modules. | MEDIUM | Four logical modules emerge from the code: `display`, `buttons`, `photo_handler`, `config`. `InkyPhotoFrame` becomes the orchestrator. |
| `tests/` directory with at least basic pytest coverage | Active contributors (PR #3) cannot validate changes without tests. CI gates on tests. The project explicitly listed this as an active requirement. | MEDIUM | Must mock `inky.auto`, `gpiozero.Button`, `RPi.GPIO`, and `pillow_heif`. Pure logic tests (color mode selection, display config detection, history rotation) require zero mocking. |
| `.github/workflows/` CI with pytest | Without CI, every PR is a gamble. GitHub contributors expect a green check before merging. GPIO Zero itself uses this pattern. | LOW | Run on `ubuntu-latest`, Python 3.11. Skip hardware tests. Mock GPIO at import time via `sys.modules` patching or `unittest.mock.patch`. |
| `__pycache__/` excluded from repo | Already in `.gitignore` but the directory is committed. This is a hygiene smell visible on first `git clone`. | LOW | One-time cleanup: `git rm -r --cached __pycache__/` and verify `.gitignore` applies. |
| `CHANGELOG.md` current through v2.0 | The project has a `CHANGELOG.md` that stopped tracking after v1.0 despite 7 patch releases. Active users need to know what changed before running `update.sh`. | LOW | Follow Keep a Changelog format. Add entries for v1.1.1 through v1.1.7, then v2.0. |
| Obsolete documentation removed | `SUMMARY.md` and `COLOR_CALIBRATION.md` exist as orphaned files. They mislead users and contributors about what is current. | LOW | Delete both. Verify content is either irrelevant or absorbed into `README.md`. |
| GitHub Release for v2.0 | Releases stopped at v1.0. Users checking GitHub for the latest stable version see stale information. The release is the public contract with users. | LOW | Tag v2.0, publish release notes from CHANGELOG, attach no artifacts (install.sh is the delivery mechanism). |
| GPIO fix merged (PR #3) | An external contributor fixed a real hardware conflict (Button C on GPIO 25 vs 16 for 13.3" displays). Leaving PRs open signals poor maintenance hygiene. | LOW | Merge before starting modularization to avoid conflict; the fix touches the GPIO pin config dict which will be moved to a module. |

### Differentiators (What Makes This Project Stand Out in the Pimoroni/RPi OSS Ecosystem)

Practices beyond the minimum that signal a well-engineered hardware project, not just a working script.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hardware-mocked test suite with `conftest.py` fixtures | Most RPi OSS projects skip testing entirely because "you need the hardware." A proper mock suite (following the GPIO Zero pattern) proves the logic is correct in CI and enables external contributors to validate PRs without a physical device. | MEDIUM | Use `unittest.mock.patch` at the module level for `inky.auto`, `gpiozero`, `RPi.GPIO`. Create `conftest.py` with a `mock_display` fixture returning a fake display with `.resolution = (800, 480)`. GPIO Zero's own test suite is the reference implementation. |
| Pure-logic unit tests for image processing pipeline | The color mode selection, palette quantization, and HEIC conversion are pure Python with Pillow — no hardware dependency at all. These are the highest-value tests: they catch regressions in the most complex logic. | MEDIUM | Use `PIL.Image.new()` to create synthetic test images. Test `apply_color_mode()`, `detect_display_saturation()` with mocked display class names, and history rotation logic. |
| `ruff` for linting and formatting (replaces flake8 + black) | The 2025 Python standard is `ruff` — it replaces flake8, isort, and black in one tool, written in Rust, runs in milliseconds. For a project this size it adds essentially zero CI overhead. | LOW | Add `ruff` to `requirements-dev.txt`. Configure in `pyproject.toml` (even if not pip-installable, `pyproject.toml` is still the right place for tool config). Run `ruff check` and `ruff format --check` in CI. |
| `pyproject.toml` for tool configuration | `pyproject.toml` is the modern Python standard for configuring pytest, ruff, mypy, and coverage — even for non-pip-installable projects. It signals current practices to contributors. | LOW | No `setup.py` or `setup.cfg` needed. Just `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.coverage.run]` sections. |
| Coverage gate in CI (>=70%) | A coverage threshold prevents the test suite from growing stale. 70% is achievable given the pure-logic surface area (color modes, display detection, history). Hardware-dependent paths are excluded via `# pragma: no cover`. | LOW | `pytest-cov` with `--cov-fail-under=70`. Cover image processing and config logic first. |
| Retro-compatible `update.sh` migration | The project has active users who ran `install.sh`. If `update.sh` breaks their installation when pulling v2.0, they will open issues and lose trust. A migration that transparently moves files from flat layout to package layout is a genuine differentiator. | HIGH | This is the highest-risk feature. `update.sh` must handle: moving `inky_photo_frame.py` to package, updating the systemd service `ExecStart`, updating the CLI wrapper path. Must be idempotent. |

### Anti-Features (Practices to Deliberately NOT Build)

Practices that seem like quality improvements but add complexity without proportional benefit for this project's scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| pip-installable package (pyproject.toml build system, PyPI) | Seems like the "professional" Python way. | The project is deployed via `install.sh` on a specific Raspberry Pi. PyPI packaging adds `src/` layout, build backend config, versioning automation, and release CI — all overhead with no benefit since users don't `pip install` it. Explicitly out of scope in PROJECT.md. | Keep flat package layout (modules alongside `install.sh`). Use `pyproject.toml` for tool config only, not as a build manifest. |
| mypy strict type checking | Type checking is a quality signal. | The codebase uses `inky.auto` which returns dynamically typed hardware objects with no stubs. Achieving strict mypy compliance would require writing type stubs for third-party hardware libraries or littering the code with `# type: ignore`. The ROI is negative for a 1-developer hardware project. | Add type hints to new modules where trivial. Do not enforce via CI. |
| Pre-commit hooks | Consistent code formatting at commit time is a quality practice. | Adds a developer setup step (`pre-commit install`) that RPi hardware hackers are unlikely to run. The CI ruff check catches the same issues. | Run ruff in CI only. Document `ruff format .` in CONTRIBUTING.md. |
| Hardware-in-the-loop (HIL) tests with a real Raspberry Pi | Real hardware validation catches integration issues mocks miss. | Requires a self-hosted GitHub Actions runner connected to physical hardware. This is a significant infrastructure investment appropriate for commercial products (e.g., Golioth's HIL setup) but disproportionate for this project. | Document manual hardware test checklist. Run mock-based CI for regression detection. |
| Automated CHANGELOG generation (commitizen/git-changelog) | Automates keeping the changelog current. | Requires commit message discipline (Conventional Commits). Retrofitting this onto 7 patch releases of organic commits is more work than manually writing the entries once. The project has one maintainer. | Write CHANGELOG.md entries by hand for historical versions. Consider commitizen for future releases only after v2.0. |
| Web interface for remote management | Would make the project more accessible. | Explicitly out of scope in PROJECT.md. Adds a web server, authentication, and attack surface to a device on a home network. The CLI + buttons interaction model is sufficient. | Keep CLI (`inky-photo-frame` command) as the management interface. |
| Multi-display brand support | Broadens the user base. | Pimoroni Inky's API is specific. Other e-ink brands (Waveshare, Papirus) have different Python libraries, different color models, different GPIO interfaces. Abstraction would require major architecture changes. Explicitly out of scope. | Add display detection documentation for the three supported Inky models. |

---

## Feature Dependencies

```
[GPIO fix merged (PR #3)]
    └──must precede──> [Module package structure]
                           (fix touches gpio_pins config dict that will move to display module)

[Module package structure]
    └──enables──> [Hardware-mocked test suite]
    └──enables──> [Coverage gate in CI]
    └──requires──> [Retro-compatible update.sh migration]

[Hardware-mocked test suite]
    └──enables──> [CI with pytest]
    └──enhances──> [Coverage gate in CI]

[pyproject.toml]
    └──enables──> [ruff linting in CI]
    └──enables──> [Coverage gate in CI]
    └──enables──> [CI with pytest configuration]

[CHANGELOG.md current]
    └──required for──> [GitHub Release v2.0]

[Obsolete docs removed]
    └──enhances──> [GitHub Release v2.0] (clean repo on release day)
```

### Dependency Notes

- **GPIO fix must precede modularization**: PR #3 changes the `gpio_pins` dict inside `DISPLAY_CONFIGS`. Once modularization splits this into a `display` module, the merge conflict surface grows. Merge first, modularize second.
- **Module structure enables testing**: You cannot effectively mock and test `InkyPhotoFrame` while it is a 1210-line monolith. Separation into modules with clear boundaries is the prerequisite for any meaningful test coverage.
- **update.sh migration is the riskiest dependency**: It is the only feature that can break existing users. It must be validated manually on a real Raspberry Pi before tagging v2.0.
- **pyproject.toml is a low-effort enabler**: Even without pip packaging, `pyproject.toml` is where `[tool.ruff]`, `[tool.pytest.ini_options]`, and `[tool.coverage.run]` live. Create it early; all CI jobs depend on it.

---

## MVP Definition

### Launch With (v2.0 Release)

The minimum needed to justify a major version bump and restore trust with existing users.

- [x] **GPIO fix merged (PR #3)** — unblocks 13.3" display users, must happen first
- [ ] **Module package structure** — the structural reason for calling this v2.0
- [ ] **`__pycache__/` removed from repo** — hygiene, one-time fix
- [ ] **CHANGELOG.md current (v1.1.1 to v2.0)** — users need to know what changed
- [ ] **Obsolete docs removed** — clean slate for release
- [ ] **GitHub Release published** — public announcement, gives users a stable reference point
- [ ] **Retro-compatible `update.sh`** — non-negotiable, existing users cannot break

### Add After v2.0 is Stable (v2.x)

- [ ] **Basic pytest suite (pure-logic tests)** — adds CI gate, enables confident future changes
- [ ] **GitHub Actions CI workflow** — green check on PRs
- [ ] **`pyproject.toml` with ruff** — standardizes tooling for contributors
- [ ] **Coverage gate (>=70%)** — prevents test suite from growing stale

**Rationale for split**: The structural refactor and release are independently valuable. Testing and CI can follow once the package structure is stable, reducing the scope of v2.0 and the risk of the release being blocked by CI configuration issues.

### Future Consideration (Post v2.x)

- [ ] **Hardware-mocked tests for ButtonController** — requires deeper gpiozero mock setup, lower ROI than pure-logic tests
- [ ] **Manual HIL test checklist document** — useful for contributors with hardware access
- [ ] **Conventional Commits for future changelog automation** — consider after v2.0 when commit hygiene can be established going forward

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| GPIO fix (PR #3) merge | HIGH (fixes hardware bug) | LOW (already written) | P1 |
| Module package structure | HIGH (maintainability) | MEDIUM | P1 |
| `__pycache__` removal | MEDIUM (repo hygiene) | LOW | P1 |
| CHANGELOG.md update | HIGH (user trust) | LOW | P1 |
| Obsolete docs removal | MEDIUM (clarity) | LOW | P1 |
| GitHub Release v2.0 | HIGH (public milestone) | LOW | P1 |
| Retro-compatible update.sh | HIGH (user safety) | HIGH | P1 |
| Basic pytest suite | HIGH (contributor enablement) | MEDIUM | P2 |
| GitHub Actions CI | HIGH (PR quality gate) | LOW | P2 |
| `pyproject.toml` + ruff | MEDIUM (contributor experience) | LOW | P2 |
| Coverage gate (70%) | MEDIUM (regression prevention) | LOW | P2 |
| mypy type checking | LOW (high cost, stubs missing) | HIGH | P3 |
| Pre-commit hooks | LOW (setup friction) | LOW | P3 |

**Priority key:**
- P1: Must have for v2.0 release
- P2: Target for v2.x, adds CI and testing discipline
- P3: Future consideration, low ROI for this project profile

---

## Comparable Project Analysis

Well-maintained Python hardware projects in the RPi/Pimoroni ecosystem and what they do:

| Quality Practice | GPIO Zero (pimoroni) | Home Assistant (ha) | This Project (target) |
|------------------|---------------------|---------------------|----------------------|
| Module structure | Full package with submodules | Extensive package | Single package, 4-5 modules |
| Test suite | pytest + MockFactory fixtures | pytest + extensive mocks | pytest + sys.modules mocking |
| CI (GitHub Actions) | Yes, multi-Python matrix | Yes, extensive | Yes, single Python version |
| Hardware mocking | MockFactory (built-in) | Extensive mock framework | unittest.mock.patch on inky/gpiozero |
| Linting | ruff | ruff | ruff (target) |
| CHANGELOG | Yes, maintained | Yes, automated | Manual, needs update |
| PyPI package | Yes (pip install gpiozero) | No (install script) | No (install.sh, by design) |
| Release process | Git tags + PyPI | Docker + release notes | GitHub Releases only |

**Key insight**: This project's delivery mechanism (install.sh) is intentionally simpler than GPIO Zero (PyPI). The target quality bar is closer to "serious single-developer OSS hardware project" than "community-maintained library." That means: good module structure, a working test suite, CI on PRs, and a reliable release process — not multi-version test matrices or type stub maintenance.

---

## Sources

- [GPIO Zero Testing documentation (DeepWiki)](https://deepwiki.com/gpiozero/gpiozero/6.1-testing) — MEDIUM confidence, describes mock_factory pattern
- [Pimoroni inky GitHub repository](https://github.com/pimoroni/inky) — HIGH confidence, reference for CI patterns
- [Testing Python applications on Raspberry Pi with pytest (woteq)](https://woteq.com/how-to-test-python-applications-running-on-raspberry-pi-with-pytest/) — MEDIUM confidence, concrete mocking examples
- [GitHub Actions Python CI in 2025 (ber2.github.io)](https://ber2.github.io/posts/2025_github_actions_python/) — HIGH confidence, current workflow patterns (ruff, ty, bandit, pytest)
- [Python Code Quality (testdriven.io)](https://testdriven.io/blog/python-code-quality/) — MEDIUM confidence, tool landscape
- [src layout vs flat layout (Python Packaging User Guide)](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) — HIGH confidence, official guidance on flat layout for non-pip projects
- [Keep a Changelog](https://keepachangelog.com/en/0.3.0/) — HIGH confidence, CHANGELOG format standard
- [Python project maturity checklist (michal.karzynski.pl)](https://michal.karzynski.pl/blog/2019/05/26/python-project-maturity-checklist/) — LOW confidence (2019, partially outdated)
- [Building and testing Python — GitHub Docs](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) — HIGH confidence, official GitHub Actions documentation

---
*Feature research for: Python hardware project quality improvement (Inky Photo Frame v2.0)*
*Researched: 2026-02-22*
