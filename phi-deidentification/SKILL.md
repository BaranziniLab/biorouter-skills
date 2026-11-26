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
   first row is a patient's data. The script's `plan` shows a column name only when every
   word in it is an ordinary column word it knows and any number in it is short; it withholds
   any other name as `#N (name withheld)`, and refuses a first row whose names carry a long
   number or a date, so a surname, a record number or a visit date read from a first row never
   reaches the chat.
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
  default this year);
- whether the first row of each file holds column names. Ask it as a yes or no question and
  do not ask what the names are. If a file has no header row, add `--no-header`: every row is
  then read as data and the columns are named `column_1`, `column_2`, and so on. Without it, a
  first row of data is read as column names and that patient's row is lost from the output;
- the column separator, if it is not a comma (`--delimiter ';'` for a semicolon, the usual
  European Excel save; also `'|'` and `tab`). The output uses the same separator.

If the script stops because the file is not UTF-8 (a plain "CSV" save from Excel is usually
Windows-1252), ask the person to save it again as "CSV UTF-8", or to tell you the encoding,
and rerun with `--encoding NAME` (for example `cp1252`, `latin-1`, `utf-16-le`, `euc-kr`). A
UTF-16 file with a byte order mark is read as it is; one without a byte order mark (NUL bytes in its
first bytes) is refused with the same remedy. The output is always UTF-8.

If a file name itself contains a patient's name, ask the person to rename the file before
you run anything, and refer to it by the new path.

### 2. Plan

From this skill's folder:

```bash
python3 scripts/safe_harbor.py plan /path/to/export.csv
```

It writes nothing and prints one line per column: the action and the reason. The script
fails closed, for text and for numbers alike: it keeps a column only when it can verify every
value in it, and a column of numbers only when its name names a measurement. Show the person that
table and explain the groups:

- **Identifiers by name** are replaced and cannot be kept: names (`patient_name`, `fname`,
  `participant`, `proband`, `AKA`, `Pseudonym`, `Kana`, `Pinyin`, `Nama`, `İsim`, `姓名`, `이름`,
  `氏名`, `姓`), relatives, household members and contacts
  (`mother`, `spouse`, `Next Kin`, `Contact Person`, `Landlord`, `Lives With`, and `First`,
  `Last`, `Given` or `Maiden` for the person's own name, unless every value is a category word
  such as Mother or Yes, or a number), birth dates and years (`dob`, `DoB`, `BDate`, `born`,
  `byear`, `Geburtsdatum`, `fecha de nacimiento`, `出生日期`, `생년월일`), ages (`age_group`,
  `edad`, `Alter bei Diagnose`, `Patientenalter`, `年龄`, `연세`, `Years Old`, `Kor`), places
  (`zip_code`, `PLZ`, `CEP`, `hometown`, `suburb`, `Lives In`, `Latitude`, `Easting`, `纬度`),
  phone numbers, email and street addresses and plates in other languages and scripts
  (`Telefon`, `Teléfono`, `Mobil`, `電話`, `Courriel`, `Correo`, `Adresse`, `Calle`, `住所`,
  `Kennzeichen`), national and social security numbers (`DNI`, `CPF`, `Aadhaar`, `BSN`, `CURP`,
  `Personnummer`, `Codice Fiscale`), health cards and claims (`OHIP`, `Health Card`, `Policy No`,
  `Claim No`, `Invoice`), record numbers (`mrn`, `Aktenzeichen`, `Prontuário`, `Expediente`), a
  column named with a word for number or record (`Pat No`, `Hospital No`, `Chart`,
  `Patientennummer`, `Numéro de dossier`, `病历号`, `患者番号`, `등록번호`, `Номер карты`), for a health
  or patient number (`PHN`, `NHS`, `NHI`, `NIP`, `PRN`, `PID`, `Patid`), for a key, a reference or a
  token of the patient (`Patient Ref`, `Pat Key`, `Pt Token`) or with a number sign after a word
  (`Pat#`, `MR#`, `Visit #`; `# of Visits` is a count) whose values have four or more digits or are
  codes with digits, and,
  when a value is a word that is not a category word, a column named for the person
  (`Subject`, `Member`, `Donor`), a social network (`Twitter`, `Instagram`) or a type or status
  of an identifier (`Phone Type`, `Email Status`, `Zip Type`; a payer column such as
  `Insurance Type` excepted).
- **Kept, verified.** Every value is a measurement, a code of a closed grammar in its exact
  published shape (ICD-9 or ICD-10-CM in capitals, ATC, HGVS, an rsID in lower case, Ensembl with
  eleven digits, RefSeq with six or nine, TNM, a stage, a grade, ECOG, a blood group, and LOINC
  only under a LOINC, lab or test column name; a dotted code of N, S, E or W with three or four
  digits after the dot, the shape of a coordinate after its hemisphere letter, only under a
  diagnosis column name),
  a whole value of a closed vocabulary (sex and gender, yes and no, missing-value words, result
  flags such as H and L, laterality, response categories, smoking status; census race and
  ethnicity only under a race or ethnicity column name, units only under a unit column name; two
  capital letters such as `CR` or `LT` only when all of a column's come from one of these lists,
  since initials take the same shape),
  a date or a state or country under a state or country column. Numbers fail closed by name, as
  text does: a number is a measurement only under a column name that names a measurement (a lab
  analyte such as WBC, Ferritin, Free T4 or Vitamin B12, a vital sign, a score or a scale such as
  Pain Score, ECOG, NYHA, Gleason or a stage or a grade, a dose, a count, a duration, money, a
  statistic such as P Value or Log2FC, or a unit in the name such as `(mg/dL)` or `%`), or with a
  unit of measurement written beside it in its cell (`5.2 mg/dL`), and only when it also passes the
  number checks of the next group; a column of years is kept under a name for a year (`Year`, `Dx
  Yr`, `Jahr`). Numbers are judged cell by cell: one record number, ZIP code, Excel serial, date
  written as a number, age over 89 or precise coordinate among measurements is enough to change the
  column. Under a
  column name that names a person, a role, a relative, a contact or a place
  (`Referring Physician`, `Family History`, `Visit Location`), only the missing-value words
  count. Dates keep the year only, and a year 90 or more years before the reference year
  becomes `[90_OR_OLDER]` in every date column, whatever it is called, because as a birth
  year it reveals an age over 89. Identifier patterns inside kept cells are still replaced.
- **Need the person's decision.** Every other column the script changed only because it
  cannot verify it:
  - text such as diagnoses, drugs, sites, arms or visits written as words (a name with a
    qualifier, in lower case, as initials, or in a script without capital letters cannot be
    told from a category word, so the script does not try);
  - **numbers under any column name that names no measurement**, whatever their shape (`Value`,
    `Result`, `Col3`, `X`, `Y`, `Index`, `Point`, `Pos`, `Geo1`, `Measure1`, `Entry`, `Seen`,
    `Event`, `Period`, `Visit Number`, `Cycle`, a sex or a race coded as a number, years under a
    name that is not a year): the plan says the script cannot verify that they are not
    identifiers, dates or coordinates, because one-decimal coordinate pairs, decimal years and
    record numbers have the shapes of measurements. They are redacted, and when a shape below
    fits, the plan gives that reason instead;
  - dates written as numbers under any column name: a decimal whose whole part is a year from 1850
    to five years after the reference year (`2021.07`, a year and a week or a day, `1926.164`), a
    Unix timestamp of 10 or 13 digits, with fractional seconds or negative (`1629478800.373`), and a
    Julian date of 7 digits (`2459215.5`). A column of nothing else keeps only the year (a year 90
    or more years ago becomes `[90_OR_OLDER]`); under a name that names a measurement such numbers
    must be most of the column;
  - whole numbers of four or more digits, or with a leading zero, under a column name that
    names no measurement, in any cell of the column: record numbers that repeat across visits
    (in any written form: `4527832`, `00088221`, `6135517.0`, `4,527,832`), ZIP codes that lost
    a leading zero, and dates written as numbers (`910314`, `3262017`). They are pseudonymized
    (rows of one patient keep one pseudonym);
  - numbers written with an exponent (`4.52783E+06`, as Excel saves a long record, account or
    phone number in a CSV), pseudonymized, and decimals with five or more digits before the
    point (`552345.12`, a grid coordinate in metres), redacted, under a column name that names
    no measurement;
  - Excel date and time serials (`44269.4375`), redacted under any column name except one that
    names a measurement other than time, and also under a day, a week, a month, a duration or a
    bare time (`Visit Day`, `Days`, `LOS`, `Event Time`), where a number from 10000 up is not a
    duration, and six or more digits are a date or a clock time written as a number (`910314`,
    `143005.123`, a Unix timestamp of nine digits); minutes, seconds and hours are left alone;
  - a whole number from 90 to 125 in any cell, under a column name that names no measurement,
    whatever else the column holds (a decimal, `<1`, an outlier): possible ages. Under a name that
    can mean age or old age (`ETA`, `Old`, `Year`, `Elderly`, `Seniority`), where a decimal or
    `>99` counts too, or with a unit of time in every cell (`95 y`), they are grouped as `90+`;
    under any other name the whole column is redacted, since its other numbers are not verified;
  - whole numbers under a column name of a person's or a record's number (`Study ID`, `Pat No`,
    `Chart`, `Case`, `Reference`, `Key`, and a code, a label, a token or a sequence of the person
    or the record: `Pt Code`, `Participant Label`, `Subject Token`, `Patient Seq`), however short:
    study or record numbers, pseudonymized;
  - whole numbers of seven or more digits that repeat, even under a measurement name (`Score`,
    `Count`, `Total`), and of six or more under a count of visits, encounters or admissions
    (`Visits`, `Encounters`, `Admissions`): record numbers, pseudonymized;
  - a month, a day, a week or a day of the year of a date written in a column of its own,
    **whatever the column is called** (`Mnth`, `DoM`, `Tg`, `SM`, `Ay`, `Gün`, `W`, `Wk`,
    `Period`, `Sample Week`, `Semana`, `Col2`, `Q7`). In a file with a year (a column of years, or
    a date column, whose year the output keeps), any column of whole numbers that fits the range of
    a date part (1 to 12, 1 to 31, 1 to 53, 1 to 366) and is not only 1 and 2; in any file, whole
    numbers from 1 to 12 that cover seven or more months, from 1 to 31 that cover thirteen or more
    days, or from 0 to 53 that cover 27 or more weeks. They are redacted as date elements other than
    the year, not grouped as ages (a few missing-value codes such as 99 or -9 do not hide them). So
    are numbers under a name that says day, week, month or weekday in any language (`Admit Day`,
    `Admit Week`, `Epi Wk`, `MMWR Week`, `Woche`, `Semaine`, `周`, `MM`, `Mois`, `入院月`,
    `Weekday`) or a day of the year (`DOY`); a protocol week under `Week` (0, 4, 12, 52) is
    redacted too until the person keeps it. Only a name that names a measurement other than a part
    of a date keeps such a column (`Pain Score`, `Heart Rate`, `Sodium`, `Days`, `Weeks`, `LOS
    (days)`, `Number of Visits`, `ECOG`, `Stage`, `Tumor Grade`, `NYHA Class`), and numbers with a 0
    (`ECOG` of 0 to 4, a count) are not months, days or weeks of the year beside a year;
  - a latitude or a longitude on its own, apart from its partner or under any name, judged cell
    by cell: one decimal of four or more places from 1 to 180 under a column name that names no
    measurement is enough, so a column that mixes precise and rounded coordinates is redacted
    (and numbers in range under `Lat`, `Lon`, `Lng`, `Long` beside a place word, or `Coord`); and,
    under a column name that names no measurement (`Value`, `X`, `Y`, `Loc X`, `Pos`, `Point`,
    `Geo1`, `Index`, `Result`, `Col4`), a column of numbers within 180 with two or more decimal
    places in three quarters of its cells or more and one value of 10 or more, a column most of
    whose numbers are negative decimals from -60 to -180 (a longitude in the Americas, also with
    one place), and a column of decimals within 90 beside a column found to be a coordinate. Two
    places locate a point to about a kilometre and three to about a hundred metres, both finer
    than a state;
  - columns with identifier patterns in some cells, unique numbers, numbers shaped like ZIP
    codes, coordinates or old birth years, and column names that usually hold a place or a
    person's identifier (`Region`, `Home`, `Subject` of numbers).
  The plan lists them under "Need the person's decision" with the reason for each.
- **Cannot be kept under their names.** A column the script could not verify whose name has a
  word the script does not know (it cannot tell that `Pai`, `Mae`, `父` or `Patientnavn` is not a
  father, a mother or a patient's name); whose name ends in a word for a person who is not
  clinical or care staff (the person, a relative, a contact, and every other role: `Mom`, `Twin`,
  `ICE`, `Witness`, `Customer`, `Who`, `Case`, `Index Case`, `Reporter`, `Author`, `Signer`,
  `Agent`, `Manager`, `Director`, `Officer`, `Rep`, `Kind`, `Tía`, `Deceased`, `Seen By`,
  `Referring`, `Department Head`, `Subject` of words); whose name has such a word anywhere and, in
  its other words, a name or a part of one, or nothing else (`Patient Last`, `Mother First`,
  `Spouse Last`, `Kin Last`, `Caregiver Full`, `MotherLast`, `pat_last`, `Pat Info`, `Kin Ref`,
  `In-law`); that is an abbreviation of a name (`PatNm`, `PNm`, `FNm`, `LNm`, `Donor_Nm`); that ends
  in an employer, a school, a home, an address, a telephone, a web address, a device, an image or
  notes (`Company`, `School`, `Home`, `Device`, `Image`, `Link`, `Notes`, `Comments`), or in a place
  that is not a place of care (`Home Area`, `Lives`, `Living`, `Community`, `Catchment Area`,
  `Service Area`, `Area`, `Locale`, `Territory`, `Geography`, `Place`, `Venue`, `Ort`) or a record
  (`Cartella`, `Dossier`, `File`) when a value is a word, and since round 7 who signed or is
  addressed, a middle initial and the source of a history (`Signed`, `Sign`, `Salutation`, `To`,
  `From`, `MI`, `Hx Source`, `Resp`), a map, a geographic location, a shelter, a building, a block,
  an origin or a school (`Geo Location`, `Map`, `Shelter`, `Building`, `Block`, `Origin`, `Education
  Institution`), and a name word spelled with digits (`Patient N4me`); or that holds numbers of five or more
  digits, in any written form, under a column name that names no measurement and no thing whose
  numbers are not a person's (`Value`, `Col6`, `Code1`, `Registration`, `Token`, `Identification`,
  `VID`; `Steps`, `Total Cost`, `Visits`, `Gene ID`, `Position`, `Lot No` and `CPT` can be kept),
  because a person who confirms that a column holds no record numbers cannot be relied on to know
  that a name such as `NHS` or `PHN` is one. Only clinical and care staff can be
  kept on the person's word: physicians, doctors, nurses, surgeons, clinicians, providers,
  attendings, residents, fellows, interns, pharmacists, therapists, technicians, technologists and
  midwives, their common abbreviations (`Dr`, `MD`, `RN`, `NP`, `PCP`, `Tech`), the same words in
  other languages (`Médecin`, `Arzt`, `Enfermera`) and physicians named by their specialty
  (`Radiologist`, `Psychiatrist`). `--keep` refuses the others. The plan lists them apart, and
  they stay redacted or pseudonymized unless the person renames the column. A column named for
  someone can still be kept when its values are numbers or codes (`Subject` or `Case` of `S-014`).
- **Free text**, and any column named for notes, comments or remarks however short its cells, is
  redacted and can never be kept.

Then ask the person about the columns that need a decision **by column name only**. Do not
describe, sample or guess what they hold, and do not offer `--keep` for a column the plan lists
as one that cannot be kept under its name. When the plan says that every value of a column is
shaped like a name of a person or a place, say so in the question, by the column's name, without
quoting a value. For example:

> The script could not verify these columns, so it changed them: Diagnosis, Drug, Visit,
> Visit Week, Col6, Value, Result. The script says every value of Col6 is shaped like a name of a
> person or a place, Value may hold coordinates, and Result holds numbers under a name that names
> no measurement, which it cannot tell from record numbers, dates or coordinates. Does each one hold
> only category values or measurements, with no names, places, coordinates, dates or parts of a date
> (a month, a week or a day, or a date written as a number), ages over 89, record or account numbers,
> contact details or other identifiers? I will keep the ones you confirm.

Then add `--keep COLUMN` for each column the person confirmed, and `--redact COLUMN` for any
column they want removed. A column can also be named `#N` (its position), and a run of columns
by a range of positions (`--keep '#2-#501'`, for a wide matrix of measurements the person
confirms as a whole). Do not ask to keep a column of numbers by guessing what it holds: name it,
and say that its name names no measurement. For a column that
cannot be kept under its name, ask only whether the name is wrong; if the person says it holds
nothing but category values or measurements, they rename it in their own copy to a plain column
name (`Diagnosis`, `Drug`, `Site`, `Visit`) and you run again on that copy.

**Kept columns are scrubbed for patterns only.** A default run redacts every text column it
cannot verify, and every column of numbers whose name names no measurement; a column the person
keeps with `--keep` loses phone numbers, email and web
addresses, labelled ID numbers, dates and the other identifier patterns, but a name, a place, a
record number, a ZIP code, an age, a month, a week or a day of a date written as a number, or
another identifier with no pattern stays in it (a clinician's column kept on the person's word
keeps the clinicians' names, and a column of numbers kept under a name such as `Value` keeps
them as written, record numbers of up to four digits, coordinate pairs, decimal years and ages
included). The run prints these columns again
("Kept on the person's word, scrubbed for patterns only") and the report lists them
(`kept_unverified_columns`, text and number columns alike). Tell the person, every time, that they
must spot-check each of these columns before the data leaves the institution.

**Column names fail closed too.** A column name is shown in the plan and the report and copied
to the output only when every word in it is an ordinary column word the script knows (the words
of its rules, category, medical and anatomical words, single letters, short numbers and codes
such as `TP53`, `Col1`, `Q3` or `2nd`), and at least one of those words is not also a common
surname or given name (`Reference Low` is shown, `Low` and `Ward` alone are not). A number in a
column name is not verified as a value is: a name holding a number of five or more digits, also
written in groups with any separator (`Patient 3767393`, `Weight 94110`, `376-7393`, `Patient
376 7393`, `Pt 37_67_393`, `ID 12 34 56 78`), a decimal of four or more places (`Weight
37.7749`), a year 90 or more years ago (`Cohort 1925`), or a date element finer than the year
(a month beside a number, `Mar-19`, `WBC Feb-20`, `Visit Sep 12`; a month and a day, `03/14`,
`14/3`, `31-12`, `14-3`, `WBC 3-19`; a quarter or a week beside a year, `Q1 20`, `Q2 2021`, `W12
2020`, `2020-W12`) is refused like an identifier pattern, and the person renames those columns.
Column names and cells share one definition of a date, read after the script folds full-width and
other scripts' digits: year, month and day markers (`2019年3月14日`, `3月14日`, `2019년 3월 14일`),
Japanese eras (`令和1年5月1日`, `R1.5.1`, `H31.4.30`), Vietnamese `tháng` and `năm` (`14 tháng 3
năm 2019`), Chinese numerals, month names of 25 languages in nine scripts beside a day or a year
(`14 Mac 2019`, `Ogos 2019`, `14 марта 2019`, `14 มีนาคม 2562`) and numeric dates in any calendar
(`14/03/2562`, `1398/12/23`). A month or a day alone (`3月`, `3월`, `tháng 3`, `14日`, a month name
of another language), a word for a day and one for a month with numbers (`Day 14 Month 3`), two
numbers of 12 or less joined by a hyphen or a slash (`WBC 3-4`), a decimal that reads as a day and
a month (`WBC 14.3`) and four digits that read as one (`WBC 1231`) are withheld; such a pair is shown
beside a word that takes a range or a scale (`Grade 3/4`, `Score 1-10`, `Age 12-18`), after a
comparator (`Hb < 13.5`) or before a unit (`2.5 mg`). A word for a person beside a word that can be a
surname (`Patient White`, `Dr Ward`) and two words that can be names side by side (`Weight Bill
White`) are withheld too. The digits of a
closed code are not counted (`ENSG00000141510`, `rs12345678`, `chr1:12345678`), and a fiscal year
(`FY2022 Cost`) is a year. A month abbreviation joined to one or two digits (`Mar19`, `OCT4`,
`SEPT9`) is also the shape of a gene symbol, so it is withheld rather than refused. A public
accession (`GSM1234567`, `SRR1234567`, `TCGA-02-0001`, `cg12345678`, `NCT01234567`) is refused
like a record number unless the person confirms that column by its position with `--keep-name
#N` (or a range, `--keep-name '#2-#501'`, for a wide matrix of probes). A first-row cell shaped like
a person's or a sample's code (`S001`, `sub01`, `PT-0042`) is withheld, and so is a word spelled
out one letter at a time (`Z-o-r-b-l-e`, `S m i t h`). A header cell holding a NUL, a control
character or an invisible formatting character (a zero-width space or joiner, a direction mark, a
soft hyphen) is refused by its position, and the person retypes that name or saves the file again
as "CSV UTF-8" (or you rerun with `--no-header`, which reads the first row as data); a zero-width
joiner or non-joiner and a direction mark are accepted in a name with no letter of a script with
capital letters (Persian, Arabic, Hebrew, Indic scripts, emoji), whose spelling needs them; a line
break or a tab in a column name reads as a space. Any other name, such as a patient's
surname, a titled name (`Dr. Lee`) or a name in a script without capital letters read from a
first row of data, is withheld (`#N (name withheld)`) and the output calls the column
`column_N`. The plan says so. Then:

- if the file has no header row, rerun with `--no-header`, so the first row is read as data;
- if the person, looking at the file in their own viewer, confirms that a withheld name is an
  ordinary column name with no identifier in it, rerun with `--keep-name #N` for that column,
  or `--keep-all-names` when they confirm the whole first row. Ask about the withheld columns
  by position only (`#3`, `#7`), never by guessing what they say.

A first row with an identifier pattern in any cell (an email, a phone number, a date) is
refused, and so is one in which a third of the cells look like values, unless the person
confirms it with `--keep-all-names`; repeated names in the first row are refused by position, and
once the person confirms that the first row holds column names, `--number-duplicates` gives each
repeated name its position (`Glucose_7`) instead.
The script cannot find an identifier in an ordinary column name, so ask the person to rename any
column whose name carries one.

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
| 2 | Refused (unknown column, a request to keep an identifier, free text or a column that cannot be kept under its name, a first row that looks like data or holds an identifier pattern, a long number, a date in any script or an invisible character, two columns with the same name, a file separated by `;` or `\|` without `--delimiter`, a file that is not UTF-8 or is UTF-16 without a byte order mark, an unreadable file) | Pass on the message; fix the options (`--no-header` for a file without a header row, `--delimiter` for another separator, `--encoding` for a file that is not UTF-8, `--number-duplicates` for repeated column names once the person confirms the first row holds names), or ask the person to fix the file |
| 3 | The residual check found identifiers; nothing was written | Rerun with `--redact` for the columns it names. A column named for the shape of its values (names or places, text it cannot verify, record numbers, ZIP codes, coordinates, old years, possible ages) may instead be kept with `--keep` once the person confirms it holds no identifiers, unless `--keep` refuses it under its name (numbers of five or more digits under a name that names no measurement, among others) |

To check an output again later: `python3 scripts/safe_harbor.py verify <output file>`
(it reads the report beside the file when there is one; without the report it cannot know
which columns the person kept, so it reports their text as text it cannot verify).

### 4. Hand over

Tell the person, in their language:

- how many rows and columns were processed, which columns were replaced, redacted or kept,
  and how many cells changed (all from the report);
- which columns were kept on the person's word (`kept_unverified_columns` in the report),
  that they were scrubbed for patterns only, and that the person has to spot-check each one
  for names, places, record numbers, ZIP codes, ages over 89 and other identifiers;
- which columns were changed because the script could not verify them and nobody kept them
  (`columns_needing_decision`), and which of them cannot be kept under their names
  (`columns_that_cannot_be_kept`);
- which column names were withheld and written as `column_N`, if any, by position only; and,
  when the file had no header row and you used `--no-header`, that every row was read as data;
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
> were replaced by pseudonyms; dates were reduced to the year, and years 90 or more years
> before [reference year] and ages over 89 were grouped as 90 or older; ZIP codes were
> truncated to three digits (000 for prefixes of 20,000 or fewer people); other direct
> identifiers and free text were removed. Other columns were kept only when every value was a
> measurement under a column name that names one, a code of a closed code system, a word of a
> closed category list or an allowed state or country, or when [who] confirmed the column.
> [N] cells in [M] columns were changed. The output was checked again for identifier
> patterns and reviewed by [who] before use.

Do not call the dataset "de-identified under HIPAA Safe Harbor" unless the person confirms
that the human review was done and the limits below were addressed, or that an expert
determination covers it.

## What it does and does not do

`references/safe-harbor-mode.md` lists, for each of the 18 identifiers, what the script
replaces and what a person still has to check. In short, it does not:

- find a name, a place, a record number or another identifier with no pattern in a column
  the person kept with `--keep`: such a column is scrubbed for patterns only ("seen by
  Halvorsen", a name in lower case, with a qualifier, as initials, or in a script without
  capital letters except after a title or a label such as "Dr. 박지훈");
- keep any text it cannot match against its closed lists: an ordinary diagnosis, drug,
  site, arm or visit column, and a vocabulary word with anything around it ("Female (45)"),
  are redacted until the person keeps them. Its lists hold a few words that are also
  surnames (White and Black under a race column, Victoria or Georgia under a state column),
  which it keeps under such a column name;
- keep by default a column of numbers whose name names no measurement, even when every value is
  an ordinary measurement (`Value`, `Result`, `Visit Number`, `Cycle`, a sex coded as 1 and 2, a
  Likert item `Q7`): it is redacted until the person keeps it. A long-format lab table (`Patient
  ID`, `Lab`, `Value`, `Unit`) completes once the person keeps `Value` (and `Lab`, for the lab
  names); a `Value` of five or more digits (a platelet count of `250000`) is kept only once the
  person renames it with a unit or a measurement word (`Value (cells/uL)`);
- tell a record number from a measurement under a column name that names a measurement unless
  it has seven or more digits and repeats, in any written form and in any share of the cells (a
  record number of four to six digits, or one that does not repeat, under `Steps`, `Total Cost` or
  `Count Entry` is kept; a label, a pseudonym, a lot, a batch or a number sign beside the
  measurement word, `Dose Lot`, `Dose #`, makes the name a number's name), or a date written as three
  digits (`314` for March 14) from a measurement under such a name; under a name that names only a
  unit of length (`X (m)`), numbers of five or more digits before the point are redacted as
  possible grid coordinates;
- tell a record number written exactly in the shape of a code from that code: an rsID (lower-case
  `rs` and up to ten digits), an Ensembl identifier (`ENSG` and eleven digits) or a dotted ICD-10
  code (a capital letter, two digits, a dot and up to four characters, as an accession number
  `S21.1234` can be) is kept as a code under any column name;
- recognise a bare five-digit ZIP code inside kept text, or a local seven-digit phone number
  without a label (also as a number under a measurement name such as `Ph`, which reads as pH);
- keep its list of restricted three-digit ZIP prefixes current: the 17 prefixes written as `000`
  are the list HHS published from the 2000 Census, and the institution should check them against
  a newer count;
- recognise a day and a month with no year in kept text unless a word such as "seen",
  "on" or "dated" comes before it ("14/3" alone stays), or written as two numbers with spaces or
  as four digits ("seen 0314"), or a month name of another language with no year and no day
  (dates of two or more elements in any script and calendar it reads, `2019年3月14日`, `14 tháng 3
  năm 2019`, `R1.5.1`, `14 มีนาคม 2562`, become the Gregorian year, or `[DATE]`);
- recognise, under a column name that names a measurement (`Ratio`, `Score`, `Steps`), a
  coordinate of any precision, an age over 89 (a `Score` of 95), or a date written as a number that
  is one value among measurements (a cost of `1999.99`): such a name says the numbers are
  measurements. Under any other name these are redacted by the name, whatever their shape;
- recognise a month, a day or a week in a column of its own under a column name that names a
  measurement (`Score` of 1 to 12); under any other name such a column is redacted by its name,
  and the plan names it as a possible date element when its numbers fit one. The other way round, a protocol week
  under a word for a week (`Visit Week` of 0, 4, 12, 52) is redacted in a file with a year, and
  `--keep` keeps it only on the person's word; if the person needs it, they can recode it as weeks
  since the first visit under a duration name (`Weeks Since Baseline`), or remove the date columns,
  before the run;
- tell a surname from a vocabulary word in a column whose every value is that one word
  (`Si`, `Quit`, `Final`, `MR` for a minor response), or a surname that is also an ordinary
  column word from a column name when another column word stands beside it;
- read a number written with a decimal comma (`5,1`, common in a file separated by `;`) as a
  number: such a column is text it cannot verify, redacted until the person keeps it;
- assess rare combinations of values, small cells or rare diagnoses (no k-anonymity check);
- read sheets after the first, images, DICOM headers or attached files;
- detect identifiers in ordinary column names or file names (a column name with a word it does
  not know, or that looks like a value or a word spelled out letter by letter, is withheld and
  renamed; a first row with an identifier pattern, a long number, a date or an invisible
  character is refused; a record number of four digits or
  fewer in a column name, `Patient 4527`, is shown, and so are a season or a half year beside a
  year, `Spring 2020`, `H1 2020`, a day alone in a language with spaces, `Day 14`, `Jour 14`, a study
  day, and a month and a day written as two numbers beside a word that takes a range or a scale,
  `Grade 3/4`, `Score 1-10`, `Age 12-18`; a surname beside a measurement word, `WBC Cook`, is shown;
  some ordinary names are withheld the other way round, `pH 7.4`, `HbA1c 6.5`, `30日死亡率`, `Gray White
  Matter Ratio`, until the person confirms them with `--keep-name`);
- refuse `--keep` on a column named for clinical or care staff (`Physician`, `Provider`,
  `Nurse`, `Pharmacist`, `Technician`), for a place of care (`Hospital`, `Clinic`, `Site`,
  `Ward`, `Unit`), for a location or a destination (`Visit Location`, `Discharge Destination`, which
  usually name a place of care), for a state-level region (`Region`, `Province`), or for a payer
  (`Payer`, `Payor`): such a column is text it cannot verify, and kept on the person's word it is
  scrubbed for patterns only, so the clinicians' names, and any town or name in it, stay. `--keep`
  is refused for a column named for any other person, an employer, a school, a home, a relative,
  the person, a place that is not a place of care, or a record, and for numbers of five or more
  digits under a name that names no measurement (see the plan above);
- read a wide matrix whose columns are named with a prefix and digits (methylation probes,
  variables `V1` to `V2000` when many of them look like codes) without the person's word: it refuses
  the first row. The person confirms public accessions by a range of positions (`--keep-name
  '#2-#501'`) and keeps their numbers the same way (`--keep '#2-#501'`, since a probe or a gene
  symbol names no measurement), renames other columns with a word and a short number (`probe_1`), or
  confirms them with `--keep-all-names` when the message allows it.

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
