# Review plan file

Each review skill writes one plan file to the project root, and
julia-review-implement consumes it. Review plan and session files
(`*_REVIEW_PLAN.md`, `*_REVIEW_SESSION.md`) are excluded via `.git/info/exclude`,
not committed.

| Skill                 | Plan file                    | Title                     | Metadata `Kind` |
|-----------------------|------------------------------|---------------------------|-----------------|
| a design review      | `DESIGN_REVIEW_PLAN.md`      | `# Design Review Plan`      | `design`        |
| julia-review-api     | `API_REVIEW_PLAN.md`         | `# API Review Plan`         | `api`           |
| an integration review | `INTEGRATION_REVIEW_PLAN.md` | `# Integration Review Plan` | `integration`   |

## Chunk fields

The chunk schema is intentionally slim: only `Kind`, `Description`, `Status`,
and `Notes` are required. Add `Breaking: yes`, `Depends on: ...`, or
`Cluster: ...` only when non-default. Reference the originating finding inline
in the description (a phrase, not a separate field); the review skill says what
that reference should contain. Findings the user declined become chunks with
`Status: dropped` and a one-line reason in `Notes`.

## Chunk sizing

Merge small related findings into chunks large enough to justify a CI cycle and
a focused review. A merged chunk takes the strictest `Breaking` flag of its
parts. Put a breaking change and its deprecation shim in one chunk when `Stated
values` accepts breaking changes readily. Findings that stay in separate chunks
but belong together share a `Cluster` label, so the implementer can flag a cluster left
half-finished; a cluster may mix breaking and non-breaking chunks.

## Schema

Substitute the title, skill name, and `Kind` from the table above.

```markdown
# [Design|API|Integration] Review Plan
<!-- Written by a review (design, API or integration). Edit freely, but preserve chunk IDs and status values. -->

## Metadata
- **Kind**: `design` | `api` | `integration`
- **Package**: [name]
- **Source review date**: [YYYY-MM-DD]
- **Current version**: [from Project.toml]
- **Issue**: #NNN | n/a

## Stated values
[author's interview reply, verbatim]

## Release strategy
- **Pre-breaking-release**: `yes` | `no` | `decide-later` | `n/a (no breaking changes planned)`
- **Inter-cluster releases**: `yes` | `no` | `decide-later` | `n/a`

## Decisions
<!-- Answers to `decide` chunks land here, with the chunk ID. -->

## Chunks

### CHUNK-001: preflight
- **Kind**: `preflight`
- **Description**: Establish baseline — tests pass, `Test.detect_ambiguities` count, clean tree, current version. Record results in this chunk's Notes.
- **Status**: `not-started`
- **Notes**:

### CHUNK-002: [verb-phrase-name]
- **Kind**: `implement` | `decide` | `investigate`
- **Description**: [what the chunk does, fixes, or asks; reference the originating finding inline]
- **Status**: `not-started`
- **Notes**:

# Add only when non-default:
# - **Breaking**: yes
# - **Depends on**: CHUNK-XXX, ...
# - **Cluster**: [label]

[... additional chunks ...]

### CHUNK-NNN: version-bump
- **Kind**: `version-bump`
- **Breaking**: yes
- **Depends on**: [every Breaking: yes chunk, plus any release-breaking chunks]
- **Description**: Bump version per breaking changes (0.x → minor; ≥1.x → major). Update CHANGELOG.
- **Status**: `not-started`
- **Notes**:

## Session ledger
<!-- The implementer appends one line after each session: `- YYYY-MM-DD CHUNK-XXX (name) → next: CHUNK-YYY` -->

## Open Questions
```

## Release chunks

- Include the terminal `version-bump` chunk only if at least one chunk is
  `Breaking: yes`. It depends on every breaking chunk, and on any
  `release-breaking` chunks if `Inter-cluster releases` is `yes`.
- If `Release strategy` says `yes` for pre-breaking, also include a
  `release-baseline` chunk before the first breaking chunk.
- If `Inter-cluster releases` is `yes`, insert `release-breaking` chunks at
  cluster boundaries.

## Briefing the user

Afterwards, summarize the chunk counts by kind (and tier), the recorded release
strategy, and that julia-review-implement starts the work.
