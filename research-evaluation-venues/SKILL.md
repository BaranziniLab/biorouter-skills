---
name: research-evaluation-venues
description: Choose where to publish or present work and prepare it to the venue's current rules (journals, conferences, posters, preprint servers), with LaTeX scaffolds for Nature, PLOS ONE, NeurIPS, NIH and NSF documents and posters, plus evidence-traceable developmental evaluation of scholarly work against an explicit rubric with inter-rater checks. Use for venue shortlists and fit, formatting and anonymity rules, page limits, checking a submission PDF, or structured, low-stakes evaluation of a manuscript, thesis or research programme.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/scholar-evaluation, skills/venue-templates)"
---

# Research Evaluation and Venues

Two related jobs: deciding **where** a piece of work should go and getting it into that venue's
shape, and **evaluating** scholarly work against stated criteria so feedback is traceable rather
than impressionistic. The guides under `references/` are adapted from K-Dense Scientific Agent
Skills (MIT; see `LICENSE-UPSTREAM`).

Refereeing someone else's submitted paper is a different job and belongs to
`manuscript-peer-review`. Taking the person's own paper through submission and a
revise-and-resubmit belongs to `empirical-paper-submission-rr`.

## Choosing a venue

1. **Describe the work honestly**: the main finding, its audience (specialists, a broad field,
   clinicians, methods developers), article type (research article, short report, methods,
   resource, review, software) and its strongest evidence.
2. **Build a shortlist of three to five venues** from where the closest related work was
   published, not from prestige lists. For each, record scope fit, article types, typical
   length, review model (single-blind, double-blind, open), open-access options and fees,
   data and code policies, preprint policy, and turnaround if published.
3. **Check policies that can block submission**: preprint and embargo rules, data availability
   requirements, reporting guidelines (CONSORT, STROBE, ARRIVE, PRISMA), AI-use disclosure,
   ethics statements, and conflicts with conference proceedings.
4. **Rank with the person** by fit first, then by audience and practicalities. Journal metrics
   (impact factor, h5-index) are context at most; never the reason.

## Getting the format right

| Task | Guide |
| --- | --- |
| Find the exact current instructions and template for a venue, then check page limits, anonymity, figures and references | `references/venue-templates.md` |
| Start from a scaffold: Nature article, PLOS ONE, NeurIPS wrapper, NIH Specific Aims, NSF proposal, academic poster | `references/venue-templates.md` (bundled under `references/venue-templates/assets/`) |
| Inspect a compiled PDF for page count, fonts and margins before upload | `references/venue-templates/scripts/validate_format.py` |
| Venue-specific writing patterns and examples (abstracts, introductions) | `references/venue-templates/assets/examples/` and the guide's references |

Instructions change every cycle: the guide's rule is to verify against the venue's live author
guidelines and record the date checked. The bundled scaffolds are drafting aids, not official
templates; switch to the official package (for example the NeurIPS style file or a journal's
class) before submission. Elsevier `elsarticle` files are not bundled here because of their LPPL
licence; download them from CTAN.

## Evaluating scholarly work

Use this for developmental feedback on a manuscript, thesis chapter, grant draft or a lab's body
of work, never to rank or make decisions about people.

1. **Confirm the use and authorisation**: who asked, what the feedback is for, and that the
   author knows.
2. **Define the construct before the criteria**: what "good" means for this work and audience.
3. **Adapt and validate the rubric**: criteria, levels with descriptors, weights if any, and a
   check that the rubric is complete and unambiguous
   (`references/scholar-evaluation/scripts/validate_rubric.py`).
4. **Rate from evidence**: every rating cites the passage, figure or table it is based on
   (`references/scholar-evaluation/scripts/check_traceability.py`).
5. **Use more than one rater when it matters**, rate independently, and report agreement
   (`references/scholar-evaluation/scripts/summarize_agreement.py`); check how weights change the
   result (`weight_sensitivity.py`).
6. **Synthesise qualitatively**: strengths, the few changes that would most improve the work,
   and open questions. Numbers support the narrative; they do not replace it.
7. **Human review and release** of the evaluation to its owner.

## In Biorouter

- Run the scaffold and evaluation tools with the Developer shell; the evaluation scripts are
  local only (no network, no models).
- Drafting the manuscript itself: `scientific-manuscript-writing`; prose polish:
  `scientific-prose-review`; figures: `figure-qa`; claims against evidence:
  `claim-evidence-integrity`; grant targeting: `grant-funding-strategy`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/venue-templates.md` | Currency rule, verification-first workflow, journal, conference, grant and poster scaffolds, helper scripts, final compliance checklist |
| `references/scholar-evaluation.md` | Responsible developmental evaluation, rubric design and validation, evidence records, independent rating, agreement, reporting |
