# Phase 2: Release Preparation - Research

**Researched:** 2026-02-22
**Domain:** Changelog authoring + GitHub Release drafting
**Confidence:** HIGH

## Summary

Phase 2 is a documentation-only phase: rewrite `CHANGELOG.md` in Keep a Changelog format and create a GitHub Release v2.0 draft. The existing CHANGELOG.md contains detailed version entries from v1.0.1 through v1.1.7 but uses a non-standard format (emoji headings, French prose for the beta "v2.0.0" entry, verbose technical details, no comparison links). It must be completely rewritten into proper Keep a Changelog format with English entries covering v1.0 through v2.0.0.

The GitHub Release v2.0 must be created as a draft (no git tag yet) using `gh release create`. The release notes are written now "as if everything is done" per user decision, referencing the GPIO fix (PR #3), module refactor, and test suite. The notes will be validated and adjusted in the final phase before publication.

**Primary recommendation:** Rewrite CHANGELOG.md from scratch using git history as the source of truth, then use `gh release create v2.0.0 --draft --notes-file` to create the release draft.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- One entry per git-tagged version from v1.0 through v2.0
- Untagged changes go into an [Unreleased] section until absorbed by v2.0
- v2.0.0 entry is written directly as [2.0.0] (not [Unreleased]), with today's date -- date updated at publication if needed
- Keep a Changelog format with all standard categories: Added, Changed, Deprecated, Removed, Fixed, Security
- Detailed entries: description + context (why, impact, PR/issue reference where applicable)
- Audience is both end-users (Raspberry Pi + Inky display owners) and developers/contributors
- Readable summaries at top level, technical details in sub-points
- Language: English
- Tone: technical and factual (not marketing/narrative)
- Structure: Highlights + Breaking Changes + Full Changelog (3 main sections)
- Dedicated "Upgrade" section with instructions for going from v1.x to v2.0 (update.sh workflow)
- No breaking changes -- everything is backward-compatible via the entry-point shim
- Release notes reference the GPIO fix (PR #3), module refactor, and test suite as key changes
- Draft the complete release notes now as if everything is done -- validate/adjust in final phase
- Create the GitHub Release as a Draft immediately (not a local file)
- No git tag yet -- tag v2.0.0 only at final publication
- CHANGELOG date for v2.0.0 is today's date, updated at publication if needed

### Claude's Discretion
- Exact wording and prose style of release notes
- How to organize the Highlights section
- Level of detail for intermediate version entries
- Upgrade section formatting

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HYGN-04 | CHANGELOG.md updated with all changes from v1.0 through v2.0 | Version history reconstructed from git tags and commit messages; Keep a Changelog format verified; all 10 versions identified with dates and changes |
| RELS-01 | GitHub Release v2.0 published with comprehensive release notes | `gh release create` command researched with --draft flag; release notes structure defined (Highlights + Breaking Changes + Full Changelog + Upgrade); existing v1.0 release analyzed as baseline |
</phase_requirements>

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Keep a Changelog | 1.1.0 (spec) | CHANGELOG.md format | Industry standard for human-readable changelogs; referenced in semver ecosystem |
| `gh` CLI | installed | Create GitHub Release draft | Already authenticated in this environment; supports `--draft` flag |
| Git tags | existing | Source of truth for version boundaries | 7 tagged versions exist (v1.0 through v1.1.4); 3 untagged versions identifiable from commit messages |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `git log` | Reconstruct version history from tags | Building each version entry from actual commits |
| `gh release create` | Create draft release on GitHub | Publishing v2.0 draft with `--draft` and `--notes-file` flags |

### Alternatives Considered

None -- this is a documentation task with a locked format (Keep a Changelog) and a locked tool (gh CLI).

## Architecture Patterns

### CHANGELOG.md Structure (Keep a Changelog 1.1.0)

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-22

### Added
- ...

### Changed
- ...

### Fixed
- ...

## [1.1.4] - 2025-10-24

### Fixed
- ...

<!-- ... more versions ... -->

## [1.0.0] - 2025-10-24

### Added
- ...

[2.0.0]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.4...v2.0.0
[1.1.4]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.3...v1.1.4
<!-- ... more links ... -->
[1.0.0]: https://github.com/mehdi7129/inky-photo-frame/releases/tag/v1.0
```

**Key format rules:**
- Reverse chronological order (newest first)
- Heading format: `## [VERSION] - YYYY-MM-DD`
- Categories: Added, Changed, Deprecated, Removed, Fixed, Security (only include categories that have entries)
- Comparison links at bottom as footnote-style references
- `# Changelog` as the document title (no emoji)

### GitHub Release Notes Structure (per user decisions)

```markdown
# Inky Photo Frame v2.0.0

## Highlights
- [key change 1]
- [key change 2]
- [key change 3]

## Breaking Changes
None -- v2.0 is fully backward-compatible. [explanation of shim]

## Upgrade
[instructions for v1.x to v2.0 migration via update.sh]

## Full Changelog
[detailed changes organized by category]
```

### Anti-Patterns to Avoid
- **Emoji in CHANGELOG headings:** Keep a Changelog format does not use emoji. The existing CHANGELOG.md uses emoji extensively -- all must be removed.
- **Mixing languages:** Existing CHANGELOG.md has French text in the "v2.0.0 (Beta)" section. All content must be English per user decision.
- **Verbose code examples in CHANGELOG:** The existing file includes full code blocks and error output. Keep a Changelog entries should be concise summaries with optional sub-points, not full documentation.
- **Marketing/narrative tone in release notes:** User explicitly requested technical and factual tone.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Version comparison links | Manual URL construction | Pattern: `https://github.com/mehdi7129/inky-photo-frame/compare/vA...vB` | Consistent, GitHub-native format |
| Release draft creation | Manual GitHub web UI | `gh release create v2.0.0 --draft --title "..." --notes-file release-notes.md --target main` | Scriptable, reproducible, keeps draft in version control pipeline |

**Key insight:** The CHANGELOG content must be reconstructed from git history (tags + commit messages), not by reformatting the existing CHANGELOG.md. The existing file has inaccurate version numbering (a "v2.0.0 Beta" that predates v1.0) and mixed-language content.

## Common Pitfalls

### Pitfall 1: Confusing the old "v2.0.0 (Beta)" with the new v2.0.0
**What goes wrong:** The existing CHANGELOG.md has a "Version 2.0.0 (2025-01-02) - Beta" entry that documents the original pre-v1.0 development. This is NOT the same as the v2.0.0 being released now.
**Why it happens:** The original project started at "v2.3.1" (initial commit message says "Inky Photo Frame v2.3.1"), then was re-versioned to v1.0. The beta "v2.0.0" changelog entry is from this pre-release era.
**How to avoid:** The new CHANGELOG starts at v1.0.0 (first tagged release). Everything before v1.0 is pre-release history and does not get a versioned entry. The features described in the old "v2.0.0 Beta" entry (storage management, DisplayManager singleton, update.sh CLI, retry logic) were actually part of the initial v1.0 release.
**Warning signs:** Any version entry dated before 2025-10-24 (the v1.0 tag date) is suspect.

### Pitfall 2: Missing untagged versions (v1.0.1, v1.1.5, v1.1.6, v1.1.7)
**What goes wrong:** Git has 7 tags (v1.0 through v1.1.4) but the commit history shows 3 additional versions (v1.1.5, v1.1.6, v1.1.7) and one more (v1.0.1) that were committed but never tagged.
**Why it happens:** The developer released rapidly (all on 2025-10-24) and stopped creating tags after v1.1.4.
**How to avoid:** The user decided "one entry per git-tagged version" -- but also said "untagged changes go into [Unreleased] until absorbed by v2.0". Since v2.0.0 is being written directly (not as [Unreleased]), the untagged version changes (v1.0.1, v1.1.5-v1.1.7) should be included as their own version entries in the CHANGELOG for completeness. The commit messages clearly identify them as releases. Include them but note they were not git-tagged.
**Warning signs:** A CHANGELOG that jumps from v1.1.4 to v2.0.0 would miss significant changes (lgpio support, system dependency auto-install, LED systemd service).

### Pitfall 3: Creating a git tag when creating the release draft
**What goes wrong:** `gh release create v2.0.0 --draft` will auto-create a `v2.0.0` tag if one does not exist, unless `--target` is used carefully.
**Why it happens:** GitHub's default behavior creates tags for releases.
**How to avoid:** Use `--target main` to specify the branch but the tag will still be created as a lightweight tag pointing to HEAD of main. The user explicitly said "No git tag yet -- tag v2.0.0 only at final publication." This is a conflict: GitHub draft releases still create a tag. Two options: (1) Accept the tag exists as part of the draft and delete/move it at publication, or (2) Use a placeholder approach. **Recommendation:** Check if `gh release create --draft` with a non-existent tag can be prevented. If not, document this behavior and plan to update the tag at final publication.
**Warning signs:** A v2.0.0 tag appearing in `git tag -l` before the code refactor is complete.

### Pitfall 4: Comparison links for untagged versions
**What goes wrong:** Keep a Changelog comparison links use tag names (`compare/v1.1.4...v1.1.5`), but v1.0.1 and v1.1.5-v1.1.7 have no tags.
**Why it happens:** Comparison links require git refs (tags, branches, or commit SHAs).
**How to avoid:** Use commit SHAs for untagged versions in comparison links. Example: `[1.1.5]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.4...4231b71`. Alternatively, create the missing tags first (but this is outside phase scope). **Recommendation:** Use commit SHAs for untagged versions.

### Pitfall 5: Release notes referencing future work as if complete
**What goes wrong:** The release notes must reference "the module refactor" and "the new test suite" per success criteria, but these do not exist yet (Phases 3-6).
**Why it happens:** User decided to "draft the complete release notes now as if everything is done."
**How to avoid:** Write the release notes describing these features in present tense. Add a comment or note in the plan that these sections must be validated in the final phase when the work is actually complete. The planner should include a validation step.

## Code Examples

### Creating a GitHub Release Draft

```bash
# Source: gh release create --help (verified locally)
gh release create v2.0.0 \
  --draft \
  --title "Inky Photo Frame v2.0.0" \
  --notes-file /path/to/release-notes.md \
  --target main
```

**Note on tag behavior:** `gh release create` will create a lightweight tag at the target ref if the tag does not exist. Per user constraint, we do NOT want a tag yet. Two approaches:

1. **Accept the auto-tag** -- it will point to HEAD of main at draft creation time. The tag can be moved to the correct commit at final publication with `git tag -f v2.0.0 <commit> && git push origin v2.0.0 --force`.
2. **Create release without a tag match** -- not supported by GitHub; releases require a tag reference.

**Recommendation:** Accept the auto-tag. Document that the tag must be updated at final publication (Phase 6 or a final validation phase). This is the standard GitHub workflow for draft releases.

### Editing an Existing Release Draft

```bash
# Source: gh release edit --help
gh release edit v2.0.0 \
  --notes-file /path/to/updated-release-notes.md \
  --title "Inky Photo Frame v2.0.0"
```

### Version History Reconstruction

Verified git history for all versions:

| Version | Tag | Commit | Date | Summary |
|---------|-----|--------|------|---------|
| 1.0.0 | v1.0 | 1567030 | 2025-10-24 | Initial release: auto-detection, color modes, SMB, HEIC, photo rotation, update.sh CLI |
| 1.0.1 | (none) | 1f21ab6 | 2025-10-24 | LED control fix, WiFi config integration, GPIO/SPI stability |
| 1.0.2 | v1.0.2 | 24aaad3 | 2025-10-24 | Bluetooth removal cleanup |
| 1.1.0 | v1.1.0 | 47fe46b | 2025-10-24 | Physical button controls (GPIO 5,6,16,24), dynamic color mode switching |
| 1.1.1 | v1.1.1 | a198260 | 2025-10-24 | Optional button import (graceful degradation if gpiozero unavailable) |
| 1.1.2 | v1.1.2 | 1b840da | 2025-10-24 | Auto-install dependencies in update.sh |
| 1.1.3 | v1.1.3 | 954de6e | 2025-10-24 | Better dependency installation error handling |
| 1.1.4 | v1.1.4 | 87e8f39 | 2025-10-24 | RPi.GPIO dependency added for gpiozero |
| 1.1.5 | (none) | 4231b71 | 2025-10-24 | lgpio support for Raspberry Pi OS Bookworm |
| 1.1.6 | (none) | 5fde38c | 2025-10-24 | Auto-install system dependencies (swig, python3-dev, liblgpio-dev) |
| 1.1.7 | (none) | e5ce52b | 2025-10-24 | Reliable LED disable via systemd service |
| 2.0.0 | (draft) | HEAD | 2026-02-22 | Module refactor, test suite, CI pipeline, GPIO fix for 13.3" (PR #3) |

### Comparison Link References

```markdown
[2.0.0]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.4...v2.0.0
[1.1.7]: https://github.com/mehdi7129/inky-photo-frame/compare/5fde38c...e5ce52b
[1.1.6]: https://github.com/mehdi7129/inky-photo-frame/compare/4231b71...5fde38c
[1.1.5]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.4...4231b71
[1.1.4]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/mehdi7129/inky-photo-frame/compare/1f21ab6...v1.0.2
[1.0.1]: https://github.com/mehdi7129/inky-photo-frame/compare/v1.0...1f21ab6
[1.0.0]: https://github.com/mehdi7129/inky-photo-frame/releases/tag/v1.0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Emoji-heavy changelog with code blocks | Keep a Changelog 1.1.0 format | This phase | Clean, scannable, standard format |
| French/English mixed documentation | English-only per user decision | This phase | Consistent language for broader audience |
| Single GitHub Release (v1.0 only) | Full release history in CHANGELOG + v2.0 draft | This phase | Complete project history documented |

**Deprecated/outdated:**
- The existing CHANGELOG.md "v2.0.0 (2025-01-02) - Beta" entry: This was a pre-v1.0 development note, not an actual release. It must not be carried into the new changelog.

## Open Questions

1. **Tag creation behavior with `gh release create --draft`**
   - What we know: GitHub requires a tag reference for releases. `gh release create` auto-creates a tag if it does not exist.
   - What's unclear: Whether there is a way to create a draft release that defers tag creation.
   - Recommendation: Accept the auto-tag behavior. The v2.0.0 tag will point to current HEAD (which is post-Phase-1). It can be moved with `git tag -f` and force-pushed at final publication. This is a known, standard workflow. **Confidence: HIGH** -- verified via `gh release create --help` output.

2. **Whether untagged versions (v1.0.1, v1.1.5-v1.1.7) should get their own CHANGELOG entries or be folded into adjacent versions**
   - What we know: User said "one entry per git-tagged version" and "untagged changes go into [Unreleased]"
   - What's unclear: The untagged versions are clearly distinct releases with their own commit messages (e.g., "v1.1.5 - Fix GPIO buttons with lgpio support"). They are not truly "unreleased" -- they were deployed.
   - Recommendation: Include all versions (including untagged) as separate CHANGELOG entries. They represent real releases even if the tags were not pushed. The v2.0.0 entry absorbs only the post-v1.1.7 changes (Phase 1 hygiene + Phases 2-6 work). This serves the dual audience (end-users and developers) better than hiding 4 versions of changes.

## Sources

### Primary (HIGH confidence)
- Keep a Changelog 1.1.0 specification: https://keepachangelog.com/en/1.1.0/ -- format rules, heading structure, link format
- `gh release create --help` -- verified locally, confirmed `--draft`, `--notes-file`, `--target` flags
- `gh release list --json` -- confirmed only one existing release (v1.0)
- `git tag -l` -- verified 7 tags exist: v1.0, v1.0.2, v1.1.0-v1.1.4
- `git log` between all tag boundaries -- verified commit contents for every version
- PR #3 body via `gh pr view 3` -- confirmed GPIO fix details and merge date

### Secondary (MEDIUM confidence)
- Existing CHANGELOG.md content -- useful as content reference but format is non-standard
- Existing v1.0 release notes via `gh release view v1.0` -- baseline for release note style

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Keep a Changelog spec verified via official site; gh CLI verified locally
- Architecture: HIGH -- CHANGELOG structure is a well-defined specification; git history fully reconstructed
- Pitfalls: HIGH -- All pitfalls identified from direct investigation of existing repo state

**Research date:** 2026-02-22
**Valid until:** No expiration -- changelog format is a stable specification, git history is immutable
