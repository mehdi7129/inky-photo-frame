# Phase 1: Pre-flight Hygiene - Research

**Researched:** 2026-02-22
**Domain:** Git repository hygiene, PR merging, file cleanup
**Confidence:** HIGH

## Summary

Phase 1 is a pure housekeeping phase with no feature work or code refactoring. The goal is to get the repository into a clean state before any structural changes begin in later phases. There are three distinct workstreams: (1) merging PR #3 which fixes a GPIO pin conflict on 13.3" displays, (2) ensuring `__pycache__` is not tracked and `.gitignore` is comprehensive, and (3) removing two obsolete documentation files.

A critical discovery during research: the working tree version of `inky_photo_frame.py` already contains the PR #3 changes (DISPLAY_CONFIGS dict, GPIO 25 for 13.3" button C) as uncommitted local modifications, along with additional changes beyond the PR scope (CHANGE_INTERVAL_MINUTES feature, updated docstring). The PR itself remains OPEN on GitHub. The uncommitted local changes and the PR diff overlap but are not identical -- the local version has extra features and minor formatting differences, while the PR includes button press logging that the local version omits. This situation requires careful handling to avoid losing either set of changes.

**Primary recommendation:** Merge PR #3 via GitHub's squash merge (it's CLEAN and MERGEABLE), then reconcile the additional local changes on top of the merged result. Do not simply commit the local working tree changes -- that would leave PR #3 open and unattributed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Squash merge PR #3 into main -- single clean commit
- Resolve conflicts automatically, favoring the GPIO 25 fix
- Audit ALL GPIO pin assignments across all display sizes (not just 13.3") to catch similar conflicts
- Delete the feature branch after successful merge
- Working tree cleanup only -- remove __pycache__ from current tracked files, no history rewrite
- Add a full standard Python .gitignore (*.pyc, __pycache__/, .egg-info, dist/, build/, etc.), not just __pycache__
- Scan for other files that shouldn't be tracked (e.g., .env, IDE configs, *.pyc) and report findings before removing
- Force push is acceptable if needed (solo project)
- Scan codebase for any references/links to SUMMARY.md and COLOR_CALIBRATION.md before deleting -- fix broken references
- Flag any other potentially obsolete documentation files found during cleanup
- Use detailed commit messages explaining what was removed and why

### Claude's Discretion
- Order of operations (merge first vs cleanup first)
- Exact .gitignore template to use as baseline
- How to handle any unexpected tracked files found during scan

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HYGN-01 | PR #3 merged -- GPIO fix for 13.3" displays integrated into codebase | PR #3 is OPEN, MERGEABLE, no CI checks, mergeStateStatus=CLEAN. Only touches `inky_photo_frame.py`. Working tree already contains overlapping changes -- must merge PR first then reconcile. See "PR #3 Merge Strategy" section. |
| HYGN-02 | `__pycache__/` removed from repo history and added to .gitignore | No `__pycache__` files are currently tracked (`git ls-files | grep __pycache__` returns empty). `.gitignore` already has `__pycache__/` and `*.py[cod]`. Requirement is already partially satisfied. Need to expand `.gitignore` to full Python standard. |
| HYGN-03 | Obsolete documentation files removed (SUMMARY.md, COLOR_CALIBRATION.md) | Both files exist and are tracked. References found in 8 planning/codebase files (all are "remove these" references, not actual links). No references in README.md, CHANGELOG.md, or source code. Safe to delete. |
</phase_requirements>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| git | system | Version control, PR merge, file removal | Standard VCS |
| gh (GitHub CLI) | system | Squash merge PR #3 via API, branch cleanup | Official GitHub CLI for PR operations |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| git rm | built-in | Remove tracked files from index and working tree | Removing SUMMARY.md, COLOR_CALIBRATION.md |
| git ls-files | built-in | Verify no unwanted files are tracked | Post-cleanup verification |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `gh pr merge --squash` | Manual merge + commit | gh gives proper PR attribution, closes PR, deletes branch automatically |
| Expanding existing .gitignore | GitHub's Python template wholesale | Existing .gitignore is already decent; selective expansion avoids dropping project-specific entries |

## Architecture Patterns

### Recommended Order of Operations

The recommended execution order:

1. **Push local planning commits first** -- The local branch is 8 commits ahead of origin (all planning docs). Push these so origin/main is current before merging PR #3.
2. **Squash merge PR #3 via GitHub** -- Use `gh pr merge 3 --squash --delete-branch`. This creates a merge commit on the remote.
3. **Pull the merge commit** -- `git pull` to get PR #3's squash merge into local main.
4. **Reconcile local uncommitted changes** -- The working tree has additional changes to `inky_photo_frame.py` and `inky-photo-frame-cli` beyond PR #3. After pulling the merge, the local diff will show only the extra changes (CHANGE_INTERVAL_MINUTES, docstring update, reset-password CLI feature). Commit these as a separate commit.
5. **Expand .gitignore** -- Update to comprehensive Python .gitignore.
6. **Remove obsolete docs** -- `git rm SUMMARY.md COLOR_CALIBRATION.md` with descriptive commit message.
7. **Update planning references** -- Fix references in `.planning/` files that mention these deleted files.

**Rationale for merge-first order:**
- Merging PR #3 first gives proper attribution to the external contributor
- It closes the PR cleanly on GitHub with squash merge history
- It avoids creating a situation where local commits contain PR #3 content without attribution
- The reconciliation step after pull is straightforward since the working tree already has a superset of the PR changes

### Pattern: Squash Merge via GitHub CLI

```bash
# Push local commits first so origin/main is up to date
git push origin main

# Squash merge PR #3 (closes PR, deletes remote branch)
gh pr merge 3 --squash --delete-branch

# Pull the merge commit into local
git pull origin main
```

### Pattern: Safe File Removal from Git

```bash
# Remove file from git tracking AND working tree
git rm SUMMARY.md COLOR_CALIBRATION.md

# Commit with explanatory message
git commit -m "chore: remove obsolete SUMMARY.md and COLOR_CALIBRATION.md

SUMMARY.md was a v1.1.7 release summary in French, now superseded
by CHANGELOG.md which covers the same content more comprehensively.

COLOR_CALIBRATION.md was a v1.0.1 color tuning guide, now outdated
since v1.1.0 introduced the 3-mode color system (pimoroni,
spectra_palette, warmth_boost) with runtime button switching.
README.md covers current color configuration."
```

### Anti-Patterns to Avoid
- **Committing the working tree changes before merging PR #3**: This would incorporate PR #3's GPIO fix without proper attribution and leave the PR open. Always merge the PR first via GitHub.
- **Using `git merge` instead of `gh pr merge --squash`**: A regular merge would bring in the full gitgost-anonymous commit history. Squash merge creates a single clean commit.
- **History rewriting for __pycache__**: The user explicitly decided "no history rewrite." Do not use `git filter-branch` or `git filter-repo`. Only remove from current tracking (which turns out to be unnecessary since no `__pycache__` files are tracked).
- **Deleting planning files that reference SUMMARY.md/COLOR_CALIBRATION.md**: These planning files reference the deletions as planned actions. Update the references rather than deleting planning content.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PR merging | Manual cherry-pick of PR #3 changes | `gh pr merge --squash` | Proper attribution, closes PR, handles remote branch deletion |
| Python .gitignore | Write from scratch | GitHub's Python.gitignore template as a base, merged with existing entries | Covers edge cases (Cython, distribution, virtualenv variants) |
| Reference scanning | Manual file-by-file reading | `grep -r "SUMMARY.md\|COLOR_CALIBRATION.md"` | Catches all references including in deeply nested planning files |

**Key insight:** This phase has no custom code to write. Every action uses standard git operations. The complexity is in sequencing operations correctly given the state of uncommitted changes and an open PR.

## Common Pitfalls

### Pitfall 1: Losing Uncommitted Working Tree Changes During Merge
**What goes wrong:** `git pull` after the PR #3 merge could create conflicts with the uncommitted local changes to `inky_photo_frame.py`, causing git to abort or require manual resolution.
**Why it happens:** The working tree has uncommitted changes to `inky_photo_frame.py` that overlap with PR #3's changes. Git will refuse to pull if it would overwrite uncommitted changes.
**How to avoid:** Before pulling, stash the uncommitted changes: `git stash`, then `git pull`, then `git stash pop`. Resolve any conflicts in the stash pop. Alternatively, commit the local changes to a temporary branch first.
**Warning signs:** `git pull` says "Your local changes to the following files would be overwritten by merge."

### Pitfall 2: PR #3 Left Open After Incorporating Its Changes
**What goes wrong:** If the GPIO fix is committed directly from the working tree, PR #3 stays open on GitHub forever. Future contributors see a stale PR and get confused.
**Why it happens:** Git doesn't know about GitHub PRs. Only `gh pr merge` or the GitHub web UI properly closes a PR.
**How to avoid:** Always use `gh pr merge 3 --squash --delete-branch` to close PR #3. Never commit the same changes manually.
**Warning signs:** `gh pr list` still shows PR #3 as open after the GPIO fix is in main.

### Pitfall 3: .gitignore Entries Conflicting with Project Files
**What goes wrong:** The standard Python .gitignore includes patterns like `*.egg-info/`, `dist/`, `build/` which are fine, but also patterns like `*.cfg` which could match project files.
**Why it happens:** GitHub's template is generic and includes patterns for frameworks (Django, Flask) and tools the project doesn't use.
**How to avoid:** Review the template entries against actual project files. The current .gitignore already ignores `*.jpg`, `*.png` etc. which is intentional (photos directory). Keep project-specific patterns. Only add relevant Python patterns that are missing.
**Warning signs:** After updating .gitignore, `git status` shows tracked files becoming ignored.

### Pitfall 4: Broken References After Deleting Documentation
**What goes wrong:** Files in `.planning/` reference SUMMARY.md and COLOR_CALIBRATION.md. If deleted without updating references, future planning phases may reference nonexistent files.
**Why it happens:** The planning docs were written knowing these files would be deleted in Phase 1. References are descriptive ("to be removed") not links.
**How to avoid:** Grep for references, verify they're all "delete these" instructions rather than dependency links, then update them to past tense after deletion.
**Warning signs:** Any reference that says "see SUMMARY.md" or links to it as a dependency.

### Pitfall 5: inky-photo-frame-cli Uncommitted Changes
**What goes wrong:** The CLI file has a 56-line uncommitted diff (reset-password command) that is unrelated to Phase 1 scope. It could get accidentally committed during cleanup work.
**Why it happens:** Working tree has pre-existing modifications across multiple files.
**How to avoid:** Be explicit about which files to stage for each commit. Never use `git add -A` or `git add .` in this phase. Only add specific files relevant to each operation.
**Warning signs:** `git diff --cached` shows unexpected files staged.

## Code Examples

### Complete PR #3 Merge Workflow

```bash
# Step 0: Verify starting state
git status  # Should show modified: inky_photo_frame.py, inky-photo-frame-cli
gh pr view 3 --json state,mergeable  # Should show OPEN, MERGEABLE

# Step 1: Stash local uncommitted changes
git stash push -m "pre-PR3-merge local changes"

# Step 2: Push any local commits ahead of origin
git push origin main

# Step 3: Squash merge PR #3
gh pr merge 3 --squash --delete-branch

# Step 4: Pull the squash merge commit
git pull origin main

# Step 5: Restore stashed changes
git stash pop
# If conflicts arise, resolve them favoring the local changes
# since they're a superset of PR #3

# Step 6: Verify GPIO 25 is in the merged result
grep "button_c.*25" inky_photo_frame.py
# Expected: 'button_c': 25,

# Step 7: Audit all GPIO pin assignments
grep -n "gpio_pins\|button_[abcd]" inky_photo_frame.py
# Verify no conflicts: 7.3" uses GPIO 16 for button C, 13.3" uses GPIO 25
```

### GPIO Pin Audit Checklist

Current GPIO assignments in `inky_photo_frame.py` DISPLAY_CONFIGS (verified from working tree):

| Display | Button A | Button B | Button C | Button D | Conflict? |
|---------|----------|----------|----------|----------|-----------|
| spectra_7.3 | GPIO 5 | GPIO 6 | GPIO 16 | GPIO 24 | No |
| classic_7.3 | GPIO 5 | GPIO 6 | GPIO 16 | GPIO 24 | No |
| spectra_13.3 | GPIO 5 | GPIO 6 | **GPIO 25** | GPIO 24 | Fixed (was GPIO 16) |

GPIO 16 is used by the 13.3" display's CS1 (chip select 1) SPI pin. Using it for a button on 13.3" caused a hardware conflict. GPIO 25 is the correct alternative.

### .gitignore Expansion

The current .gitignore is already solid. Missing patterns to add from the standard Python template:

```gitignore
# Additional Python patterns (missing from current .gitignore)
*.egg-info/
*.egg
dist/
build/
*.manifest
*.spec
pip-log.txt
pip-delete-this-directory.txt

# Testing
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Environments (additional variants)
.env
.env.*

# Distribution / packaging
sdist/
develop-eggs/
eggs/
lib/
lib64/
parts/
var/
wheels/
```

**Note:** Do NOT add `*.cfg` (would match logrotate.conf if renamed), `local_settings.py` (Django-specific), or framework patterns not used by this project.

### Reference Scan Results

Files referencing SUMMARY.md or COLOR_CALIBRATION.md:

| File | Line | Reference Type | Action Needed |
|------|------|----------------|---------------|
| `.planning/PROJECT.md:38` | "Clean obsolete documentation files (SUMMARY.md, COLOR_CALIBRATION.md)" | Checklist item | Mark as done after deletion |
| `.planning/REQUIREMENTS.md:14` | "HYGN-03: Obsolete documentation files removed (SUMMARY.md, COLOR_CALIBRATION.md)" | Requirement definition | No change needed (stays as requirement text) |
| `.planning/ROADMAP.md:31` | Success criterion: "SUMMARY.md and COLOR_CALIBRATION.md are absent" | Success criterion | No change needed (describes target state) |
| `.planning/codebase/CONCERNS.md:219-220` | "Files: SUMMARY.md, COLOR_CALIBRATION.md... are obsolete and should be removed" | Concern description | Update to reflect removal is complete |
| `.planning/codebase/STRUCTURE.md:39,42,44,90` | Listed in directory tree | Structure documentation | Update tree to remove these entries |
| `.planning/research/FEATURES.md:38` | "SUMMARY.md and COLOR_CALIBRATION.md exist as orphaned files" | Research finding | No change needed (historical research) |
| `.planning/research/SUMMARY.md:42,98` | "Obsolete docs removed" | Research summary | No change needed (historical) |
| `SUMMARY.md:89` | Self-reference | Will be deleted | N/A |

**Result:** No source code references. No README links. All references are in planning docs describing the planned deletion. Only `.planning/codebase/STRUCTURE.md` and `.planning/codebase/CONCERNS.md` need updating post-deletion. Others are requirement/research docs that describe the action and don't need changing.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `git filter-branch` for history cleanup | `git filter-repo` | 2020+ | Not applicable -- user chose no history rewrite |
| Manual PR merge on GitHub web | `gh pr merge --squash` via CLI | gh CLI v1.0+ (2020) | Enables automated, scriptable PR merging |
| Custom .gitignore per project | GitHub's language templates | Ongoing | Standard patterns cover most edge cases |

**Deprecated/outdated:**
- `git filter-branch`: Replaced by `git filter-repo` for history rewriting. Neither is needed here since user chose working-tree-only cleanup.

## Open Questions

1. **What should happen with the uncommitted `inky-photo-frame-cli` changes (reset-password feature)?**
   - What we know: The CLI file has a 56-line diff adding a `reset-password` command. This is unrelated to Phase 1 scope.
   - What's unclear: Should it be committed as part of Phase 1 cleanup, or left for a later phase?
   - Recommendation: Leave it uncommitted for now. Phase 1 is about hygiene, not feature integration. The reset-password feature can be committed in Phase 2 (Release Preparation) or as a separate pre-Phase-2 commit. If the planner disagrees, it can be included as an optional cleanup task.

2. **Should the extra `inky_photo_frame.py` changes (CHANGE_INTERVAL_MINUTES, docstring) be committed in Phase 1?**
   - What we know: These are local working tree changes beyond PR #3 scope. They add a configurable change interval and update the module docstring.
   - What's unclear: Whether these are finished, tested features or work-in-progress.
   - Recommendation: After merging PR #3 and pulling, the stash pop will restore these changes. They should be committed as a separate "integrate local improvements" commit in Phase 1, since leaving uncommitted changes across phases creates risk. The planner should verify they're complete before committing.

3. **Should `.planning/codebase/STRUCTURE.md` and `.planning/codebase/CONCERNS.md` be updated in Phase 1 or later?**
   - What we know: Both files reference SUMMARY.md and COLOR_CALIBRATION.md in their content.
   - What's unclear: Whether updating planning docs is in Phase 1 scope or deferred to Phase 2.
   - Recommendation: Update them in the same commit that removes the obsolete docs. This keeps the repo internally consistent.

## Sources

### Primary (HIGH confidence)
- Local repository inspection via `git log`, `git status`, `git diff`, `git ls-files` -- all findings verified directly
- `gh pr view 3` -- PR state (OPEN, MERGEABLE, CLEAN), file list, additions/deletions
- Working tree `inky_photo_frame.py` lines 103-150 -- DISPLAY_CONFIGS with GPIO pin assignments verified
- Working tree `.gitignore` -- current content verified

### Secondary (MEDIUM confidence)
- GitHub Python.gitignore template (https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore) -- standard patterns verified via WebFetch

### Tertiary (LOW confidence)
- None. All findings verified from primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- only git and gh CLI needed, both verified present and functional
- Architecture: HIGH -- order of operations derived from direct inspection of repo state (uncommitted changes, PR state, local-vs-remote divergence)
- Pitfalls: HIGH -- all identified from direct observation of the actual repo state (uncommitted changes overlapping with PR, unrelated file modifications)

**Research date:** 2026-02-22
**Valid until:** Indefinite (git operations don't change; repo state is the variable)
