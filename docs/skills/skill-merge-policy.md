# Skill Merge Policy

[Back to README](../README.md)

This policy governs future merges inside `skills/`. It is a guardrail document only: Phase 0 does not delete, rename, merge, or shim any skill.

## Definitions

- **Canonical skill**: the maintained target skill after a merge. It owns the current instructions, references, scripts, templates, and assets for the merged workflow.
- **Shim skill**: a compatibility skill kept at an old identifier after that skill is absorbed. It exists so old direct skill calls remain loadable while users and agents migrate to the canonical skill.
- **Absorbed skill**: an old skill whose unique guidance, references, scripts, templates, or assets have moved into a canonical skill.
- **Merge manifest**: the required checklist for one merge. It records the canonical target, absorbed skills, moved resources, compatibility shims, tests, docs, and rollout notes.
- **Deprecation criteria**: the conditions that must be true before a shim skill can be removed.

## Merge Manifest

Every future merge must document:

- canonical target skill name
- absorbed skill identifiers
- reason for merging, including overlapping triggers or duplicated workflow content
- unique guidance moved into the canonical skill
- references, scripts, templates, and assets moved or linked
- old identifiers that remain as shim skills
- docs and hub routes updated
- tests proving old identifiers remain loadable and point to the canonical successor

## Standard Shim Body

Use this exact body for compatibility shims unless a phase plan explicitly requires more detail:

```markdown
# Deprecated: use `<canonical-skill>`

This skill identifier is kept for compatibility. Load `<canonical-skill>` for the maintained workflow.
```

## Deprecation Criteria

A shim skill can be removed only after all of these are true:

- It has existed for at least one release cycle after the canonical skill landed.
- Hub skills and docs no longer recommend the old identifier.
- Tests prove the canonical skill is indexed and recommended for the old trigger patterns.
- Any bundled references, scripts, templates, or assets from the absorbed skill were moved, linked, or explicitly declared obsolete.
- The removal is called out in the relevant merge phase plan.

## Non-Goals

- Do not merge hub skills into specialized skills.
- Do not delete direct identifiers in the same change that creates a canonical skill.
- Do not flatten framework-specific or regulated-domain expertise into generic prose.
- Do not move bundled scripts or assets without preserving their execution path or documenting the replacement.
