---
name: qualitative-thematic-analysis
description: Plan and carry out qualitative analysis of interviews, focus groups, open-ended survey answers and field notes, with reflexive or codebook thematic analysis, framework analysis and content analysis, including transcript preparation and de-identification, codebook design, analytic memos, coding passes, inter-rater agreement (Cohen's kappa, Krippendorff's alpha), auditable AI-assisted coding, and COREQ or SRQR reporting. Use for coding qualitative data, building a codebook, developing themes, or writing up qualitative methods and findings.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Qualitative Thematic Analysis

Qualitative findings are credible when a reader can follow how quotes became codes, codes
became themes, and themes became claims. This skill keeps that chain visible. It is written for
Biorouter and copies no upstream text.

## Choose the approach with the person

| Approach | Use when | What the analysis produces | Agreement statistics? |
| --- | --- | --- | --- |
| Reflexive thematic analysis (Braun and Clarke) | Exploring meaning and experience; the researcher's interpretation is part of the method | Themes as patterns of shared meaning, with a reflexivity statement | No; quality comes from reflexivity and depth, not consensus |
| Codebook thematic analysis (template analysis) | Several coders, a structured question, partly predefined topics | A codebook and themes summarised across cases | Optional, useful for calibration |
| Framework analysis | Applied health or policy research with set questions and case comparison | A case-by-theme matrix | Optional |
| Qualitative content analysis | Counting how often defined categories appear | Category frequencies with definitions | Yes, report reliability |
| Grounded theory | Building an explanatory theory from data | Categories, relationships and a theory, through theoretical sampling | No |

Mixing approaches is common; say which one leads, and do not report kappa for reflexive
thematic analysis as if consensus validated an interpretation.

## Prepare the data

1. **Ethics first.** Confirm consent covers the analysis and any sharing of quotes, and that the
   data are approved for this environment. Identifiable recordings and transcripts stay in the
   approved location.
2. **De-identify transcripts** before coding: names, places, employers, dates and rare details
   replaced with bracketed tags (`[colleague]`, `[city]`), with a key kept separately and
   securely. Keep speaker labels (`P07`, `Interviewer`).
3. **One file per transcript**, numbered lines or paragraphs, with a header for participant id,
   date, interviewer, setting and key attributes used in comparisons.
4. **Familiarise**: read each transcript fully before coding and write a short summary memo.

## The codebook

Each code gets one row:

| Field | Content |
| --- | --- |
| Code | Short label (`trust_in_clinician`) |
| Definition | One or two sentences on what it captures |
| Include when | Concrete criteria |
| Exclude when | Near misses and the code they belong to instead |
| Example | A short de-identified quote with its transcript and line |
| Notes | Origin (deductive from the interview guide or inductive), date added, changes |

Start with deductive codes from the research question and interview guide only where the
approach allows it, then add inductive codes during the first pass. Version the codebook (a file
in the project with a dated change log) so every coded segment can be tied to the codebook
version used.

## Coding passes

1. **Pilot**: two people code the same two or three transcripts independently, compare, and
   revise definitions where they disagreed. Record what changed.
2. **First full pass**: code every transcript; write memos about surprises, contradictions and
   ideas for themes, each memo dated and linked to the segments that prompted it.
3. **Calibration (codebook and content approaches)**: double-code a random 10 to 20% of
   segments, compute agreement per code, discuss disagreements, refine.
4. **Theme development**: group codes into candidate themes, check each theme against the full
   data (does it hold across cases, what contradicts it), then define and name themes in a
   sentence each.
5. **Negative cases**: actively look for data that do not fit and report them.

## Agreement, when the approach calls for it

Compute agreement per code on segments both coders saw, and report the statistic, the unit
(segment, sentence, transcript), the proportion double-coded and how disagreements were resolved.

```python
from sklearn.metrics import cohen_kappa_score   # two coders, one code, 0/1 per segment
kappa = cohen_kappa_score(coder_a, coder_b)
# Krippendorff's alpha (several coders, missing ratings): pip install krippendorff
import krippendorff
alpha = krippendorff.alpha(reliability_data=matrix, level_of_measurement="nominal")
```

In R, `irr::kappa2` and `irr::kripp.alpha` do the same. Kappa is unstable for rare codes;
report raw agreement and the code's prevalence alongside it.

## AI-assisted coding

A model can suggest codes, find candidate quotes and draft summaries, but:

- send transcripts only to a model approved for the data (a private, institutionally hosted
  model for sensitive data);
- treat every suggestion as a candidate a human accepts, edits or rejects, and log which
  segments were AI-suggested;
- check suggested quotes against the transcript verbatim; models paraphrase and invent;
- never let a model define the themes alone, and describe its use in the methods.

## Reporting

Follow COREQ (interviews and focus groups) or SRQR. Include the approach and why, sampling and
saturation or information-power reasoning, who coded and their position (reflexivity), the
codebook or its summary as a supplement, how themes were developed, and quotes that illustrate
each theme with participant ids. Claims in the write-up go through `claim-evidence-integrity`,
using the transcripts as the evidence.

## Tools

Dedicated software (NVivo, ATLAS.ti, MAXQDA, or the open-source Taguette and QualCoder) handles
coding at scale; a spreadsheet with one row per coded segment (transcript, lines, code, coder,
codebook version, memo link) works for smaller projects and is easy to audit. Run agreement
statistics with the Developer shell.

## Related skills

- `social-science-text-as-data` for computational measurement across large corpora.
- `survey-weights-complex-samples` when open responses come from a weighted survey and counts
  are reported as population estimates.
- `scientific-manuscript-writing` for drafting the paper; `empirical-paper-submission-rr` for
  submission and revision.
