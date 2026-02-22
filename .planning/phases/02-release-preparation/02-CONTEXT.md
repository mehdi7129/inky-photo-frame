# Phase 2: Release Preparation - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Write CHANGELOG.md and draft GitHub Release v2.0 notes so the release can be published immediately once the code refactor passes validation. This phase is documentation-only — no code changes.

</domain>

<decisions>
## Implementation Decisions

### Version history reconstruction
- One entry per git-tagged version from v1.0 through v2.0
- Untagged changes go into an [Unreleased] section until absorbed by v2.0
- v2.0.0 entry is written directly as [2.0.0] (not [Unreleased]), with today's date — date updated at publication if needed

### CHANGELOG format & depth
- Keep a Changelog format with all standard categories: Added, Changed, Deprecated, Removed, Fixed, Security
- Detailed entries: description + context (why, impact, PR/issue reference where applicable)
- Audience is both end-users (Raspberry Pi + Inky display owners) and developers/contributors
- Readable summaries at top level, technical details in sub-points
- Language: English

### Release notes content
- Tone: technical and factual (not marketing/narrative)
- Structure: Highlights + Breaking Changes + Full Changelog (3 main sections)
- Dedicated "Upgrade" section with instructions for going from v1.x to v2.0 (update.sh workflow)
- No breaking changes — everything is backward-compatible via the entry-point shim
- Release notes reference the GPIO fix (PR #3), module refactor, and test suite as key changes

### Timing & forward references
- Draft the complete release notes now as if everything is done — validate/adjust in final phase
- Create the GitHub Release as a Draft immediately (not a local file)
- No git tag yet — tag v2.0.0 only at final publication
- CHANGELOG date for v2.0.0 is today's date, updated at publication if needed

### Claude's Discretion
- Exact wording and prose style of release notes
- How to organize the Highlights section
- Level of detail for intermediate version entries
- Upgrade section formatting

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-release-preparation*
*Context gathered: 2026-02-22*
