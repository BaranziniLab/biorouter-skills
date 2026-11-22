<!-- Adapted for Biorouter from Aperivue/medsci-skills skills/verify-refs/references/manual_checkpoint_guide.md (MIT, commit 7e9d133; licence in LICENSE-UPSTREAM). Changes: cross-references to other medsci-skills commands replaced with Biorouter equivalents; `${CLAUDE_SKILL_DIR}` replaced with `$SKILL_DIR`. -->

# Manual Reference Verification Checkpoint Guide

Set `SKILL_DIR` to the skill directory Biorouter lists when `claim-evidence-integrity` loads (for example `SKILL_DIR=~/.config/biorouter/skills/claim-evidence-integrity`), then run the commands below from the project root through the Developer shell.

**Audience**: Project owner before journal submission or before circulating a near-final draft to co-authors.

This guide documents the **manual strict-mode run** the owner should perform
immediately before submitting or before the manuscript leaves the project
workspace.

## When to run manually

Run `verify-refs --strict` manually at every one of these checkpoints:

1. **Before first circulation to co-authors.** Catches hallucinations that
   slipped into earlier drafts.
2. **Before cover-letter + manuscript package freeze.**
3. **Before each revision resubmission** (R1, R2, ...). Revisions are a common
   site of new citation drift because reviewer responses introduce new
   references.
4. **Before preprint posting** (medRxiv / arXiv). Preprints are public and hard
   to correct.
5. **After any external edit** (co-author returns a `.docx` with tracked
   changes, or an external editor touches references).

## Command

From the project root:

```bash
python3 "$SKILL_DIR/scripts/verify_refs.py" \
  manuscript/index.qmd \
  --project-root . \
  --strict
```

Or via the wrapper:

```bash
"$SKILL_DIR/scripts/verify_cli.sh" manuscript/index.qmd --strict
```

Docx input is also accepted:

```bash
"$SKILL_DIR/scripts/verify_cli.sh" \
  submission/radiology_ai/manuscript_main.docx --strict
```

## What `--strict` changes

- Exit code is non-zero if `submission_safe: false` (any FABRICATED / MISMATCH).
- Exit code is non-zero if any UNVERIFIED row remains.
- Offline verification is not tolerated — the script requires live PubMed /
  CrossRef reachability.

## Reading the output

The only output file is `qc/reference_audit.json`. Inspect with:

```bash
python3 -c "import json; a=json.load(open('qc/reference_audit.json')); \
print('safe=', a['submission_safe'], 'counts=', a['counts'])"
```

Then jump to the records:

```bash
python3 -c "import json; a=json.load(open('qc/reference_audit.json')); \
[print(r['ref_id'], r['status'], r.get('note','')) \
  for r in a['records'] if r['status']!='OK']"
```

## Failure actions

| Status | Action |
|---|---|
| `FABRICATED` | STOP. Locate the citation in the manuscript. Either remove it or replace with a verified entry found by a real search and added through the reference manager. Never patch `refs.bib` by hand. |
| `MISMATCH` | STOP. Usually a copy-paste error (wrong DOI for the title). Confirm the author's intent and correct via Zotero. |
| `UNVERIFIED` | Review. If the reference genuinely lacks DOI/PMID (rare: old conference abstracts, grey literature), check it by hand against the publisher record and get the user's confirmation before accepting it (SKILL.md Gate 2). The script has no manual-override field, so `--strict` keeps failing on that row. |

## Relationship with the reference manager

The verifier is audit-only. All bibliographic corrections flow through the
reference manager (Zotero → Better BibTeX auto-export → `refs.bib`). Never edit
`refs.bib` to satisfy the verifier.

## Change log

- **2026-04-24 v1.1.1 Phase 1A.5** Initial manual checkpoint guide. Aligned to
  audit-only verify-refs contract (no `references/*` writes).
