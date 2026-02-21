# Stack Research

**Domain:** Python quality tooling — testing, CI/CD, code quality for hardware-dependent Raspberry Pi project
**Researched:** 2026-02-22
**Confidence:** HIGH (all versions verified against PyPI/official docs as of 2026-02-22)

---

## Recommended Stack

### Core Testing Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest | 9.0.2 | Test runner and framework | Industry standard Python test runner. Plain function syntax, powerful fixture system, rich plugin ecosystem. Supports `conftest.py` for shared fixtures — critical for centralizing GPIO mock setup. Expressive failure messages and excellent IDE integration. |
| pytest-mock | 3.15.1 | Thin wrapper around `unittest.mock` | Provides `mocker` fixture making mock/patch ergonomics pytest-native (auto-teardown, no decorator boilerplate). Also provides `spy` for wrapping real functions. Cleaner than raw `@patch` decorators for hardware stubs. |
| pytest-cov | 7.0.0 | Test coverage measurement and reporting | De facto coverage plugin for pytest. Integrates with `coverage.py`, outputs GitHub-compatible XML for CI annotations, supports LCOV format. Tells us which image processing paths are untested. |

### Hardware Mocking Strategy

| Library/Technique | Purpose | Why Recommended |
|-------------------|---------|-----------------|
| `unittest.mock` (stdlib) | Mock GPIO calls, Inky SPI calls, file system calls | Ships with Python 3 — no extra dependency. `MagicMock` covers attribute access, method calls, and return values. Used to mock `gpiozero.Button`, `inky` display objects, and `spidev`. |
| `sys.modules` injection in `conftest.py` | Prevent `ImportError` for hardware-only packages | The standard pattern for CI: insert `MagicMock()` objects into `sys.modules` before imports run (see pi-top SDK example). Handles `RPi`, `RPi.GPIO`, `spidev`, `smbus2`, `inky` so CI never needs actual hardware. |
| `GPIOZERO_PIN_FACTORY=mock` env var | Enable gpiozero's built-in MockFactory | gpiozero ships `MockFactory` (pins from `gpiozero.pins.mock`). Setting this env var at test time makes all `Button()` objects use fake pins that can be driven programmatically with `pin.drive_low()`. No external library needed. |

### Linter and Formatter

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| ruff | 0.15.2 | Linting AND formatting (replaces black + flake8 + isort) | Written in Rust, 10-100x faster than flake8/black. Single tool replaces: flake8, black, isort, pydocstyle, pyupgrade. Has official GitHub Action (`astral-sh/ruff-action@v3`). Configurable in `pyproject.toml`. Industry consensus as of 2025 is to use ruff instead of the older separate-tools approach. |

### Type Checking

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| mypy | 1.19.1 | Static type analysis | Catches bugs at analysis time rather than runtime. Gradual typing — start with just the pure logic modules (image processing, history rotation). Does not require hardware. Provides long-term maintenance confidence as the codebase grows. |

### CI/CD Pipeline

| Technology | Purpose | Why Recommended |
|------------|---------|-----------------|
| GitHub Actions | CI/CD orchestration | Already on GitHub. Free for public repos. Native to the platform — no external CI server to manage. `ubuntu-latest` runner is the standard environment. |
| `actions/setup-python@v5` | Python environment setup | Official GitHub action. Caches pip installs automatically. Supports any Python version including 3.11 (Raspberry Pi OS Bookworm ships 3.11). |
| `astral-sh/ruff-action@v3` | Ruff linting and format check | Official action maintained by Astral. No Python setup needed — downloads binary directly. Used with `args: --output-format=github` for inline PR annotations. |

### Development Workflow

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pre-commit | 4.5.1 | Git hook manager | Runs ruff (lint + format) before every commit locally. Catches issues before they reach CI. One-time setup per developer. Hooks defined in `.pre-commit-config.yaml`. Uses the same ruff version as CI — no drift. |
| pyproject.toml | N/A | Unified project configuration | Single config file for pytest, ruff, mypy, and coverage. Supported by all modern Python tools. Avoids proliferation of `setup.cfg`, `tox.ini`, `.flake8`, `mypy.ini` files. |

---

## Installation

```bash
# Dev dependencies only — not installed on the Pi
pip install pytest==9.0.2 pytest-mock==3.15.1 pytest-cov==7.0.0

# Code quality tools
pip install ruff==0.15.2 mypy==1.19.1

# Git hook manager (installed globally or in venv)
pip install pre-commit==4.5.1
pre-commit install
```

**Note:** All of these are dev dependencies. The Pi only runs `requirements.txt` (inky, Pillow, watchdog, gpiozero, etc.). Create a separate `requirements-dev.txt` for tooling.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| ruff | black + flake8 + isort separately | Never for new setup — ruff is strictly faster and has full feature parity with the three-tool combo. |
| ruff | pylint | If you need deep semantic analysis or team prefers pylint's verbose output. For this project, ruff's speed and zero-config approach wins. |
| pytest-mock | `@patch` decorators directly | `@patch` is fine for simple one-off tests, but `mocker` fixture scales better across a test suite with many GPIO stubs. Either is acceptable. |
| `sys.modules` injection | `mock-gpio` / `Mock.GPIO` PyPI packages | `Mock.GPIO` is a separate package targeting RPi.GPIO specifically. The `sys.modules` approach is more general and covers `inky`, `spidev`, `smbus2` too — not just GPIO. No extra dependency. |
| `GPIOZERO_PIN_FACTORY=mock` | patching gpiozero internals manually | The env var is the officially documented approach by the gpiozero team. Always prefer documented mechanisms over internal patching. |
| mypy | pyright / pyright-strict | pyright is faster and more accurate for newer Python features. For an existing codebase starting from no types at all, mypy's gradual typing story is well-documented and easier to begin with. |
| GitHub Actions hosted runner | Self-hosted Pi runner | A self-hosted Pi runner enables hardware-in-the-loop integration tests but adds significant operational overhead (runner maintenance, Pi uptime, networking). Not worth it for unit tests that mock hardware. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `tox` | Adds a matrix-testing layer (multiple Python versions) that is unnecessary for a single-target (Raspberry Pi OS Bookworm / Python 3.11) project. Obscures what's happening, complicates CI setup. | Run pytest directly in GitHub Actions. |
| `unittest` as the test runner | verbose class-based boilerplate, inferior fixture system compared to pytest. | pytest (which still runs unittest-style tests if needed). |
| `nose` / `nose2` | Deprecated, not maintained | pytest |
| `black` standalone | Ruff's formatter is compatible with black's style and runs in the same tool. No reason to install both. | `ruff format` |
| `isort` standalone | Ruff handles import sorting with `I` ruleset enabled. | `ruff check --select I` |
| `flake8` + plugins | Ruff's `E`, `W`, `F` rules cover the same checks. Ruff is 10-100x faster. | `ruff check` |
| `bandit` (security) | Useful for larger applications — adds complexity not justified at this project scale. | Skip for v2.0; reconsider if the project grows a web interface. |
| `coverage.py` CLI directly | pytest-cov integrates coverage into the pytest run with better defaults for HTML/XML output. | `pytest --cov` via pytest-cov. |

---

## Stack Patterns by Variant

**For CI runs (GitHub Actions, no hardware):**
- Set `GPIOZERO_PIN_FACTORY=mock` as an env var in the workflow
- Set `INKY_SKIP_GPIO_CHECK=1` (already set in the existing code)
- Inject `sys.modules` mocks in `conftest.py` for `inky`, `RPi`, `RPi.GPIO`, `spidev`, `smbus2`
- Run: `pytest tests/ --cov=inky_photo_frame --cov-report=xml --cov-report=term`

**For local development on a Mac/Linux machine (no Pi):**
- Same `conftest.py` approach works identically
- `pre-commit` catches lint/format issues before push

**For testing on actual Raspberry Pi hardware (optional integration tests):**
- Mark tests `@pytest.mark.hardware` and skip by default
- Run with `pytest -m hardware` manually on device
- Do NOT run these in GitHub Actions

---

## Version Compatibility

| Package | Compatible Python | Notes |
|---------|-------------------|-------|
| pytest 9.0.2 | >=3.9 | Raspberry Pi OS Bookworm ships Python 3.11 — fully compatible |
| pytest-mock 3.15.1 | >=3.9 | No constraints |
| pytest-cov 7.0.0 | >=3.9 | Dropped subprocess `.pth` approach — simpler setup |
| ruff 0.15.2 | >=3.7 (target) | Ruff itself runs on any OS; formats code targeting any Python |
| mypy 1.19.1 | >=3.9 | No constraints |
| pre-commit 4.5.1 | >=3.9 | No constraints |
| gpiozero MockFactory | >=2.0.0 | Already in requirements.txt at `>=2.0.0` — MockFactory is stable since 1.6 |

---

## Key Architecture Decision: No pyproject.toml for Packaging

Per `PROJECT.md`, this project is explicitly **not pip-installable** — it stays as a simple module installed via `install.sh`. Therefore `pyproject.toml` is used **only for tool configuration** (pytest, ruff, mypy), not for `[build-system]` or `[project]` metadata. This keeps things simple while still centralizing tool config.

```toml
# pyproject.toml — tool config only, no build-system section
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --cov=. --cov-report=term-missing"
env = ["GPIOZERO_PIN_FACTORY=mock", "INKY_SKIP_GPIO_CHECK=1"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true  # needed for inky, gpiozero stubs
```

---

## Sources

- [pytest 9.0.2 — PyPI](https://pypi.org/project/pytest/) — version verified 2026-02-22
- [pytest-mock 3.15.1 — PyPI](https://pypi.org/project/pytest-mock/) — version verified 2026-02-22
- [pytest-cov 7.0.0 — PyPI](https://pypi.org/project/pytest-cov/) — version verified 2026-02-22
- [ruff 0.15.2 — PyPI](https://pypi.org/project/ruff/) — version verified 2026-02-22
- [mypy 1.19.1 — PyPI](https://pypi.org/project/mypy/) — version verified 2026-02-22
- [pre-commit 4.5.1 — PyPI](https://pypi.org/project/pre-commit/) — version verified 2026-02-22
- [gpiozero MockFactory API — official docs](https://gpiozero.readthedocs.io/en/stable/api_pins.html) — GPIOZERO_PIN_FACTORY=mock pattern confirmed
- [Ruff integrations — astral.sh official docs](https://docs.astral.sh/ruff/integrations/) — ruff-action@v3 confirmed
- [GitHub Actions Python — official docs](https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python) — setup-python@v5 confirmed
- [pi-top Python SDK conftest.py](https://github.com/pi-top/pi-top-Python-SDK/blob/master/conftest.py) — sys.modules injection pattern for hardware mocks (MEDIUM confidence — real-world usage verified)
- [GitHub Actions Python 2025 — Alberto Cámara](https://ber2.github.io/posts/2025_github_actions_python/) — 2025 workflow patterns (MEDIUM confidence)

---

*Stack research for: Python quality tooling — testing, CI/CD, code quality for Raspberry Pi e-ink photo frame*
*Researched: 2026-02-22*
