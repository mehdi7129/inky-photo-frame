# Phase 1: Pre-flight Hygiene - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up the repository before any structural work begins. Merge the GPIO hardware fix (PR #3), purge cached/compiled files from tracking, and remove obsolete documentation. This is pure housekeeping — no feature work, no refactoring.

</domain>

<decisions>
## Implementation Decisions

### PR #3 merge strategy
- Squash merge PR #3 into main — single clean commit
- Resolve conflicts automatically, favoring the GPIO 25 fix
- Audit ALL GPIO pin assignments across all display sizes (not just 13.3") to catch similar conflicts
- Delete the feature branch after successful merge

### Git history cleanup
- Working tree cleanup only — remove __pycache__ from current tracked files, no history rewrite
- Add a full standard Python .gitignore (*.pyc, __pycache__/, .egg-info, dist/, build/, etc.), not just __pycache__
- Scan for other files that shouldn't be tracked (e.g., .env, IDE configs, *.pyc) and report findings before removing
- Force push is acceptable if needed (solo project)

### Obsolete docs handling
- Scan codebase for any references/links to SUMMARY.md and COLOR_CALIBRATION.md before deleting — fix broken references
- Flag any other potentially obsolete documentation files found during cleanup
- Use detailed commit messages explaining what was removed and why

### Claude's Discretion
- Order of operations (merge first vs cleanup first)
- Exact .gitignore template to use as baseline
- How to handle any unexpected tracked files found during scan

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for repository cleanup.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-pre-flight-hygiene*
*Context gathered: 2026-02-22*
