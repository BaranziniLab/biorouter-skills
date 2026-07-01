---
name: open-science-review
description: "Review a research project for open-science readiness: transparent methods, preregistration or protocol notes, PRISMA/systematic-review structure, data/code availability, reporting checklists, and responsible sharing. Use before public release, submission, or collaborative handoff."
user-invocable: true
license: Apache-2.0
---

# Open Science Review

Source adaptation: BioRouter-original synthesis from Scientific Agent Skills literature/review workflows and Auto-Empirical Research Skills open-science checks, rewritten under Apache-2.0.

Use this skill for publication readiness beyond the statistics.

## Review Checklist

- Methods are detailed enough for another group to reproduce.
- Inclusion/exclusion criteria are explicit for reviews or cohorts.
- Protocol, preregistration, or analysis plan is linked when available.
- Data availability statement is accurate.
- Code availability statement points to a runnable package.
- Ethical, privacy, and restricted-data constraints are stated.
- Reporting checklist matches the study type: CONSORT, STROBE, PRISMA, TRIPOD, STROBE-MR, ARRIVE, or domain-specific equivalent.
- Conflicts, funding, and license terms are documented.

## Output

Return:

1. `Open-science status`: ready, ready with restrictions, or not ready.
2. `Required disclosures`.
3. `Missing artifacts`.
4. `Recommended checklist`.
5. `Next concrete fix`.
