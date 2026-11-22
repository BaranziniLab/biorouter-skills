---
name: grant-funding-strategy
description: Plan, draft and review research grant proposals against the exact funding opportunity, for NIH, NSF, DOE, DARPA, ERC, Horizon Europe, Taiwan NSTC and foundations, covering specific aims, significance and innovation, approach, broader impacts, budgets and justifications, compliance matrices, resubmission introductions, and a six-reviewer mock panel before submission. Use when someone is writing, revising or critiquing a grant, aims page, project summary, or response to a previous review.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/research-grants); claesbackman/AI-research-feedback@949d82792ea20c30806147539ed2c70a8898260a (Skills/review-grant)"
---

# Grant and Funding Strategy

Proposals fail most often on fit and compliance, not on science: the wrong mechanism, a missed
page limit, aims that do not match the review criteria. This skill starts from the opportunity's
own rules and keeps the investigator as the author. The two guides under `references/` are
adapted from K-Dense Scientific Agent Skills and claesbackman/AI-research-feedback (MIT; see
`LICENSE-UPSTREAM`).

## Start from the governing opportunity

Before drafting anything, get the exact notice (NIH NOFO or parent announcement, NSF
solicitation or the PAPPG, ERC work programme, foundation call) and its date. Extract into a
compliance matrix:

- eligibility, deadlines and submission system;
- required sections, page and character limits, fonts and margins, file naming;
- review criteria and their weights, and who reviews (study section, panel, programme officer);
- budget caps, allowable costs, cost sharing, indirect rates;
- required plans (data management and sharing, mentoring, resource sharing, human subjects,
  vertebrate animals, safety) and letters.

Rules change between cycles; anything not checked against the current notice is marked
unverified. The research-grants guide has agency overviews to start from, not to replace the
notice (`references/research-grants/references/nih_guidelines.md`,
`references/research-grants/references/nsf_guidelines.md`, and DOE, DARPA and NSTC files beside
them).

## Build the argument

1. **One sentence of significance**: the gap, why it matters now, and what will be different if
   the work succeeds.
2. **Aims that test, not describe.** Each aim has a hypothesis or a clear deliverable, an
   approach, an expected outcome and a fallback; aims are related but do not depend on each
   other succeeding. The aims page is the most-read page; draft it first
   (`references/research-grants/references/specific_aims_guide.md`,
   `references/research-grants/assets/nih_specific_aims_template.md`).
3. **Map every review criterion to a place in the text** where a reviewer finds the answer
   (significance, investigators, innovation, approach, environment for NIH; intellectual merit
   and broader impacts for NSF).
4. **Preliminary data that de-risk the approach**, each figure tied to a claim in the aims.
5. **Rigour and feasibility**: power or sample-size justification (`statistical-modeling-bayes`),
   biological variables such as sex, authentication of key resources, timeline and milestones,
   and potential problems with alternatives.
6. **Budget follows the work**: personnel effort that matches the aims, justification in the
   funder's format (`references/research-grants/assets/budget_justification_template.md`).
7. **Resubmissions** answer every point of the summary statement in the introduction, with
   changes marked in the text (`references/research-grants/references/proposal_types_and_resubmission.md`).

## Review before submission

Run the six-reviewer mock panel in `references/review-grant-panel.md` on a complete draft:
clarity and compliance, internal consistency, significance and innovation, methods and
feasibility, budget and team, and a funder-specific overall reviewer. Each reviewer reads the
proposal independently; the consolidated report ranks issues and gives a preliminary
recommendation. In Biorouter, the reviewers run as subagents when the subagent tool is available
(Completely Autonomous mode), and one after another otherwise.

Treat the panel as a rehearsal: it finds unclear writing, inconsistencies and missing pieces, but
it does not know the field's politics or the study section's taste. The investigator's
colleagues and the programme officer remain the real test.

## Boundaries

- The investigator owns the ideas and the text; drafts are proposals for them to edit, and
  institutional and funder rules on AI assistance must be followed (some funders prohibit
  AI-generated content in applications or in peer review).
- Never invent preliminary data, citations, letters of support or effort commitments.
- Budgets need the institution's research office for rates and final figures.

## In Biorouter

- Figures and diagrams for the proposal: `scientific-artifacts`; data figures:
  `ggplot-visualization` or `python-visualization`.
- Papers drafted from the same work: `scientific-manuscript-writing`; reference lists:
  `citation-library-management`; claims against sources: `claim-evidence-integrity`.
- Data management and sharing plans are a planned native skill; until it exists, follow the
  funder's template and the institution's library guidance.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/research-grants.md` | Opportunity-first workflow, agency overviews (NSF, NIH, DOE, DARPA, NSTC), core components, review criteria, writing principles, common mistakes, resubmissions |
| `references/review-grant-panel.md` | The six-reviewer pre-submission panel: reviewer briefs, consolidation and report format |
