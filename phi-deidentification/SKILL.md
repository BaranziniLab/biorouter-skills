---
name: phi-deidentification
description: "De-identifies clinical tables (CSV, TSV, Excel) under the HIPAA Safe Harbor rule with a local script that makes no network calls, so the raw data never enters the chat. Use before any analysis, sharing or upload of patient-level data that may hold names, dates, addresses, record numbers, contact details or other PHI. The agent runs the script on the files and reads only its report and the de-identified output."
license: Apache-2.0 AND MIT
compatibility: "Python 3.9 or later, standard library only; openpyxl for .xlsx files. Runs locally and makes no network calls."
user-invocable: true
metadata:
  version: "1.0.1"
  origin: "adapted"
  upstream: "Aperivue/medsci-skills/skills/deidentify@7e9d133dd0216c29b0e030729e3719c3db5e0973"
  upstream_licence: "MIT"
  upstream_author: "Aperivue"
---

<!-- Adapted for Biorouter from Aperivue/medsci-skills (skills/deidentify, commit 7e9d133dd021), MIT. Changes: SKILL.md rewritten for an agent that never sees raw data; scripts/safe_harbor.py added; deidentify.py, locale packs and references kept. See LICENSE-UPSTREAM. -->

# PHI De-identification

This skill removes protected health information from a clinical table before anyone
analyses or shares it. The work is done by `scripts/safe_harbor.py`, a local Python script
that you run with the shell on the person's files. It prints column names, counts and
decisions only, never a cell value. It makes no network calls, and it blocks Python's usual
socket functions so a library cannot connect by accident. That is a guard, not a sandbox:
where the data must provably stay offline, run it under an operating-system sandbox with
networking denied (the last section shows one).

## Rules that protect the raw data

Read these before doing anything with a file that may hold PHI.

1. **Run the script on the files directly. Never open, print, quote, summarise, describe
   or preview the raw (pre-de-identification) contents in the chat, and never ask the
   person to paste them.** The chat may run on a model hosted outside the person's
   institution (in Biorouter, a Public model), and anything you read becomes part of it.
2. That includes a quick look: no `cat`, `head`, `tail`, `less`, `grep`, `awk`, `sed`,
   spreadsheet previews, pandas or one-line Python on the raw file, no sample rows, no
   value counts. Do not read the header row yourself either: in a file without one, the
   first row is a patient's data. The script's `plan` shows the column names it can safely
   show.
3. Never open, print or read the mapping file written by `--mapping-out`. It holds the
   original identifiers.
4. Read only three things: what the script prints, its report
   (`deidentification_report.json`), and the de-identified output file. Show the person
   only the de-identified output, never the input. Before you read the output, ask the
   person to spot-check it in their own viewer, and read it only after they confirm. Skip
   that step only when you know the chat runs on a model hosted inside the institution (in
   Biorouter, a Private model); if you cannot tell, ask.
5. If the script exits with 2 or 3, do not open the input to find out why. Pass on the
   script's message, which names columns and counts only, and rerun with the options it
   suggests.
6. Say plainly, every time you hand over a result, that automated de-identification needs
   a human spot-check before the data leaves the institution. Safe Harbor is a human
   determination: besides removing the 18 identifiers, the institution must have no actual
   knowledge that what remains could identify someone. The script does only the automated
   part, and its output is not certified de-identified.

## When to use it

- A person wants to analyse, share or upload a clinical export (EHR extract, registry
  table, study spreadsheet) that may hold identifiers.
- Before another skill (statistics, figures, machine learning) reads patient-level data.
- Data that is already de-identified at the source (the UCSF OMOP and CDW de-identified
  views) does not need it, unless it has since been joined with identified data.

It handles tables only: CSV, TSV, text tables and the first sheet of an Excel workbook.
Clinical notes, images, DICOM files and PDFs are out of scope.

## Workflow

### 1. Ask what you need, not the data

Ask for:

- the path of each file, and an output folder that is separate from the raw data and
  inside the institution's storage;
- the country, if not the United States (`--locale`: `us` by default; also `kr`, `jp`,
  `cn`, `de`, `uk`, `fr`, `ca`, `au`, `in`, `it`, `es`). Safe Harbor is a US rule; for other
  countries the locale adds that country's ID and phone patterns, and the person checks
  the local law;
- whether they will need to link the output back to patients later. If so, the pseudonym
  mapping goes to a restricted location outside the output folder (`--mapping-out`).
  Otherwise write no mapping;
- the year that ages are computed against, if the data is old (`--reference-year`,
  default this year).

If a file name itself contains a patient's name, ask the person to rename the file before
you run anything, and refer to it by the new path.

### 2. Plan

From this skill's folder:

```bash
python3 scripts/safe_harbor.py plan /path/to/export.csv
```

It writes nothing and prints one line per column: the action and the reason. The script
fails closed: it keeps a column only when it can verify every value in it. Show the person
that table and explain the groups:

- **Identifiers by name** (`patient_name`, `fname`, `participant`, `proband`, `mother`,
  `spouse`, `dob`, `born`, `byear`, `age_group`, `edad`, `年龄`, `zip_code`, `hometown`,
  `suburb`, `mrn`, ...) are replaced and cannot be kept.
- **Kept, verified.** Every value is a number that passes the numeric checks (not shaped like
  a ZIP code, a phone, a record number, a date, a birth year of someone over 89 or a
  coordinate), a code of a closed grammar (ICD-9 or ICD-10, LOINC, ATC, HGVS, rsID, Ensembl,
  RefSeq, TNM, a stage, a grade, ECOG, a blood group), a whole value of a closed vocabulary
  (sex and gender, yes and no, missing-value words, census race and ethnicity, result flags
  such as H and L, laterality, response categories, smoking status, units), a date (reduced to
  the year) or a state or country under a state or country column. Under a column name that
  names a person, a role, a relative, a contact or a place (`Referring Physician`,
  `Family History`, `Visit Location`), only the missing-value words count. Identifier
  patterns inside kept cells are still replaced.
- **Need the person's decision.** Every other text column, such as diagnoses, drugs, sites,
  arms or visits written as words. The plan lists them under "Need the person's decision" and
  gives each one the line "redact: text the script cannot verify is free of identifiers; keep
  with --keep COLUMN once the person confirms it". A name with a qualifier ("Nakamura,
  Alice (wife)"), in lower case, as initials, or in a script without capital letters cannot
  be told from a category word, so the script does not try.
- **Columns the scanner cannot vouch for** for another reason: identifier patterns in some
  cells, unique numbers, numbers shaped like ZIP codes, coordinates, old birth years or dates,
  and column names that usually hold a name or a place (`Subject`, `First`, `Contact`,
  `Region`, `Home`, `Company`). They are redacted or pseudonymized, and can be kept the same
  way, for example a pair of score columns read as coordinates.
- **Free text** is redacted and can never be kept.

Then ask the person about the columns that need a decision **by column name only**. Do not
describe, sample or guess what they hold. For example:

> The script could not verify these columns, so it redacted them: Diagnosis, Drug, Visit.
> Does each one hold only category values, with no names, places, dates, contact details or
> other identifiers? I will keep the ones you confirm.

Then add `--keep COLUMN` for each column the person confirmed, and `--redact COLUMN` for any
column they want removed. A column can also be named `#N` (its position).

**Kept text is scrubbed for patterns only.** A column kept with `--keep` loses phone numbers,
email and web addresses, ID numbers, dates and the other identifier patterns, but a name, a
place or another identifier with no pattern stays in it. The run prints these columns again
("Kept on the person's word, scrubbed for patterns only") and the report lists them
(`kept_unverified_text_columns`). Tell the person, every time, that they must spot-check each
of these columns before the data leaves the institution.

### 3. Run

```bash
python3 scripts/safe_harbor.py run /path/to/export.csv \
    --output-dir /path/to/deidentified/ \
    [--keep diagnosis] [--redact comments] [--mapping-out /restricted/mapping.json]
```

It writes `<name>_deidentified.<ext>` and `deidentification_report.json` to the output
folder, then scans the output again. Exit codes:

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Done; the residual check found no identifier pattern or shape, and verified again every kept column the person did not name with `--keep` (a check, not proof) | Report the summary, the columns kept on the person's word, and the human spot-check requirement |
| 2 | Refused (unknown column, a request to keep an identifier or free text, a first row that looks like data, a file separated by `;` or `\|`, an unreadable file) | Pass on the message; fix the options, or ask the person to fix the file |
| 3 | The residual check found identifiers; nothing was written | Rerun with `--redact` for the columns it names. A column named for the shape of its values (names or places, text it cannot verify, ZIP codes, coordinates, old years) may instead be kept with `--keep` once the person confirms it holds no identifiers |

To check an output again later: `python3 scripts/safe_harbor.py verify <output file>`
(it reads the report beside the file when there is one; without the report it cannot know
which columns the person kept, so it reports their text as text it cannot verify).

### 4. Hand over

Tell the person, in their language:

- how many rows and columns were processed, which columns were replaced, redacted or kept,
  and how many cells changed (all from the report);
- which columns were kept on the person's word (`kept_unverified_text_columns` in the
  report), that they were scrubbed for patterns only, and that the person has to spot-check
  each one for names, places and other identifiers;
- which columns were redacted because the script could not verify them and nobody kept
  them (`columns_needing_decision`);
- that the output must be spot-checked by a person before it leaves the institution, and
  what to look for: names or other identifiers in columns kept on request, a ZIP code or
  other location in a column not named for it, rare values or combinations that could single
  someone out (very old age, rare diagnosis, small towns), identifiers in column names;
- that only the first sheet of a workbook was processed, when the report says other
  sheets were skipped;
- where the mapping is, if one was written, and that it stays restricted and is never
  shared or opened in a chat.

Only then, and after the person's spot-check (unless the chat is known to run on a model
hosted inside the institution), read the de-identified file for the analysis.

### 5. Methods text

When the person needs a paragraph for a manuscript or an IRB, fill this in from the report:

> Direct identifiers were removed before analysis with a rule-based tool run locally,
> with no network calls (safe_harbor.py, Biorouter phi-deidentification skill 1.0.1,
> adapted from medsci-skills deidentify). The tool classified each column by name, by
> value patterns and by the shape of its numbers for the 18 HIPAA Safe Harbor identifier
> types. Names and record numbers
> were replaced by pseudonyms; dates were reduced to the year; ages over 89 were grouped
> as 90 or older; ZIP codes were truncated to three digits (000 for prefixes of 20,000 or
> fewer people); other direct identifiers and free text were removed. Other text columns
> were kept only when every value was a number, a code of a closed code system, a word of a
> closed category list or an allowed state or country, or when [who] confirmed the column.
> [N] cells in [M] columns were changed. The output was checked again for identifier
> patterns and reviewed by [who] before use.

Do not call the dataset "de-identified under HIPAA Safe Harbor" unless the person confirms
that the human review was done and the limits below were addressed, or that an expert
determination covers it.

## What it does and does not do

`references/safe-harbor-mode.md` lists, for each of the 18 identifiers, what the script
replaces and what a person still has to check. In short, it does not:

- find a name, a place or another identifier with no pattern in a column the person kept
  with `--keep`: such a column is scrubbed for patterns only ("seen by Halvorsen", a name in
  lower case, with a qualifier, as initials, or in a script without capital letters except
  after a title or a label such as "Dr. 박지훈");
- keep any text it cannot match against its closed lists: an ordinary diagnosis, drug,
  site, arm or visit column, and a vocabulary word with anything around it ("Female (45)"),
  are redacted until the person keeps them. Its lists hold a few words that are also
  surnames (White, Black), which it keeps under a column name that names no person, role or
  place;
- recognise a bare five-digit ZIP code inside kept text, a column of ZIP codes that mostly
  lost their leading zero under a name it does not know, a local seven-digit phone number
  without a label, or a record number that repeats across visits in a column of numbers
  under a name it does not know (only unique numbers are pseudonymized);
- recognise a day and a month with no year in kept text unless a word such as "seen",
  "on" or "dated" comes before it ("14/3" alone stays), or a month name in another
  language without a year;
- recognise a latitude or longitude column without its partner next to it, or ages over
  89 in a column of plain numbers whose name says neither age nor years;
- assess rare combinations of values, small cells or rare diagnoses (no k-anonymity check);
- read sheets after the first, images, DICOM headers or attached files;
- detect identifiers in column names or file names.

## The researcher's interactive alternative

`scripts/deidentify.py` is the upstream medsci-skills tool. It walks the researcher through
each column in an interactive terminal review and can shift dates by a per-patient offset
instead of keeping the year (useful under a data use agreement or an expert
determination, not Safe Harbor). It prints sample values of every column, so **you never run
it**: the person runs it in their own terminal, outside the chat, as described in
`references/date_shift_guide.md` and `references/hipaa_18_identifiers.md`.

## Files

| File | What it is |
|---|---|
| `scripts/safe_harbor.py` | The non-interactive Safe Harbor script the agent runs |
| `scripts/deidentify.py`, `scripts/locales/` | Upstream scanner, file reader and locale packs, reused by `safe_harbor.py` |
| `references/safe-harbor-mode.md` | The 18 identifiers and what the script does with each |
| `references/hipaa_18_identifiers.md`, `date_shift_guide.md`, `korean_phi_patterns.md` | Upstream references for `deidentify.py` |
| `tests/run_tests.sh` | Runs the upstream tests and the Safe Harbor tests |
| `tests/fixtures/synthetic_18_identifiers.csv` | Invented people carrying all 18 identifier types |

Run the tests, or the script itself on real data, with networking denied, for example
on macOS:

```bash
sandbox-exec -p '(version 1)(allow default)(deny network*)' bash tests/run_tests.sh
```
