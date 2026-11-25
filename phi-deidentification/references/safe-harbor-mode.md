# What safe_harbor.py does with each Safe Harbor identifier

Reference for `scripts/safe_harbor.py`. The rule is 45 CFR 164.514(b)(2): the 18
identifiers of the person, and of the person's relatives, employers and household
members, are removed, and the covered entity has no actual knowledge that what
remains could identify the person. The script does the removal it can automate.
The second half is a human determination.

`references/hipaa_18_identifiers.md` describes the interactive `deidentify.py`
instead, which shifts dates and leaves several of these to the researcher.

## The design: fail closed

Earlier versions tried to recognise every name and place in a text column and kept the
column when they found none. Three rounds of review each found a new shape that slipped
through with exit 0: a name with a qualifier ("Alice Nakamura (wife)"), a role header the
word lists did not know (`Visit Dr`), a town under `Service Area`, a name in a script with no
capital letters, a year and a month. A list of what names look like never closes. Since
1.0.1 the script does the opposite: it keeps a column that is not an identifier by name only
when it can positively verify every value in it, and redacts everything else until the
person confirms it. The cost is over-redaction of ordinary text columns (a diagnosis or drug
column written in words), which the person undoes column by column with `--keep`; the gain
is that a value the script has never seen is redacted, not kept.

## How a column is decided

1. **By its name.** A column named for an identifier (`patient_name`, `dob`, `zip_code`,
   `mrn`, `fax`, `vehicle_vin`, ...) is replaced as the table below says. These columns
   cannot be kept: `--keep` on one is refused. Names are read as words, in any spelling the
   rules know: a birth year as `birth_year`, `yob`, `born`, `byear`, `birth_yr`,
   `yr_birth` or `year_born`; an age as `age`, `ageyrs`, `age_at_dx`, `pt_age`,
   `patient_age_years`, `age_days` or `age_group`, and in other languages as `edad`,
   `idade`, `alter`, `età`, `leeftijd`, `wiek`, `ålder`, `年龄`, `年齢`, `나이`, `연령`,
   `возраст`, `العمر`, `גיל`, `आयु` or `อายุ` (`alter` and `alder` alone or beside a word
   for years, because they are English words too, and `ETA` alone is an arrival time); a
   place of birth as `birthplace`,
   `birth_city` or `pob`. A whole column name that is the person (`participant`, `proband`,
   `individual`, `client`, `respondent`, `decedent`) is pseudonymized; one that is a relative
   or a contact (`mother`, `father`, `spouse`, `husband`, `wife`, `guardian`, `caregiver`,
   `informant`) is redacted; `fname`, `lname`, `forename`, `nm` and `pt_nm` are names; and
   `hometown`, `suburb`, `locality`, `district` and `township` are geography smaller than a
   state. A name column of a clinician, staff member or other role is redacted even beside a
   word such as `lab` or `study` (`lab_technician_name`, `specimen_collector_name`), and
   `study_patient_name` is the person's own name, pseudonymized; a title or role word counts
   as well (`visit_dr_name`, `test_verifier_name`, `nombre_medico`). Names and places are
   also read in other languages (`nombre`, `apellido`, `nom`, `vorname`, `cognome`; `ciudad`,
   `municipio`, `ville`, `stadt`, `citta`), and accents in a column name are ignored
   (`Médecin` reads as `medecin`). `birth_weight`, `birth_order` and similar describe the
   birth, not its date, and are left to the value rules. State and country columns
   (`state`, `country`, `country_of_birth`, `country_of_origin`, `nationality`, ...) are
   allowed, and kept when their values verify (step 5).

   A type or status column of an identifier word (`insurance_type`, `insurance_status`,
   `subscriber_status`, `medicaid_eligible`, `account_type`, `license_status`,
   `login_status`, `city_type`, `employer_type`, `type_of_insurance`) is not the identifier
   when its values are a handful of category words with no digit and no identifier
   pattern (Medicare, Commercial, Active, Urban); a payer column (`insurance`, `medicare`)
   is not either, unless its name also says number, ID, member or policy. These go to the
   value rules: Yes and No are verified and kept, and other words are text the script cannot
   verify, which the person can keep with `--keep`. For employer, place and login words every value must
   be a known category word, because a single unknown word there can be the employer, the
   town or the login itself. With numbers, codes or names in it, the same column is still
   an identifier by name and cannot be kept.
2. **By a column name that usually holds a name or a place.** A whole column name such as
   `subject`, `member`, `insured`, `first`, `last`, `given`, `parent`, `sibling`, `contact`,
   `family`, `region`, `home`, `company` or `school` has other uses (`insured` can be yes or
   no, `region` a census region), so these are pseudonymized or redacted as columns the
   scanner cannot vouch for, and the person can keep one with `--keep`. When every value is
   a common category word ("Yes", "Mother"), or, apart from `subject` and similar names of
   the person, every value is a number, the rule does not apply and step 5 decides
   (`insured` of Yes and No is kept; `contact` of Mother and Father is not verified).
3. **By its values.** When more than half of a column's cells that are not missing-value
   words are nothing but one identifier (all dates, all IP addresses, all codes), the column
   is replaced the same way.
   A year and a month with no day counts as a date under any column name (`2021-03`,
   `2021/03`, `2021-3`, `2021 Mar`, `Mar 2021`, `03/2021`), so a monthly export written with
   `%Y-%m` keeps the year only, whether the column is called `Visit Month`, `Period`,
   `Enrolled` or `Col1`.
4. **By the shape of its numbers**, for columns whose name says nothing:
   - four-digit years, any of them at least 90 years before the reference year: they may
     be birth years, so those years become `[90_OR_OLDER]` and the rest stay;
   - a year and a month written as a number in every cell (`202103`, `2021.03`, with a
     month from 01 to 12): dates, reduced to the year;
   - a month and a day written as a number with no separator in every cell (`0314`, `1403`,
     `031421`, `03142021`), with a leading zero in one of them when they have four or six
     digits: possible dates, redacted;
   - a column named for years (`years`, `yrs`) holding values over 89: possible ages,
     grouped as `90+`;
   - at least 80% five-digit numbers: possible ZIP codes, redacted (a white cell count
     mixes four and five digits and is kept);
   - two adjacent columns of decimal numbers shaped like latitude (within 90) and
     longitude (within 180), with three or more decimal places, or two when the second
     column passes 90 with one sign, and a value of 10 or more in one of them: redacted;
   - unique numbers of five or more digits: possible record or account numbers,
     pseudonymized.
   The same checks run on the numbers of a column that mixes numbers with other verified
   values (`<0.5`, `5.2 mg/dL`, `unknown`).
5. **Fail closed: every other value must be verified.** A column that no rule above
   replaced is kept only when every value that is not blank is one of:
   - (a) a number, with an optional comparator and unit (`<0.5`, `>= 10`, `5.2 mg/dL`, `12%`,
     `1,250`), or a blood pressure (`120/80`, the first number larger, so a day and a month
     never pass), that the checks of step 4 do not flag;
   - (b) a code of a closed grammar: ICD-10 with a dot and a digit after it (`E11.9`,
     `S72.001A`), ICD-9 `V` and `E` codes with a dot, LOINC with a valid check digit (`2345-7`),
     ATC, HGVS (`c.35G>A`, `p.V600E`, `NM_004333.6:c.1799T>A`), rsID, Ensembl and RefSeq IDs,
     TNM (`T2N0M0`, `pT1a`), a stage with its word (`Stage IIIA`, `FIGO IB1`, `NYHA class III`),
     a grade (`G2`, `Grade 3`, `low grade`, `3+4=7`, `ISUP 2`), ECOG and Karnofsky (`ECOG 1`,
     `KPS 80`) and a blood group (`A+`, `O neg`, `AB positive`, `A型`). No grammar accepts a
     bare alphabetic word. Short forms are accepted only under a column name that says what
     they are: ICD codes without a dot (`I10`, `E119`) under a diagnosis, condition or ICD
     name, ATC codes under a drug or ATC name, Roman stages (`IIIA`, `IV`) under a stage,
     class, grade or phase name, `Tis` and `Tx` under a TNM or stage name, `A`, `B`, `AB` and
     `O` under a blood name, protein changes (`V600E`) under a variant or mutation name, and
     LOINC codes shaped like a year and a month (`2093-3`) under a LOINC name;
   - (c) a whole value, after case and spacing are folded, of a closed vocabulary: sex and
     gender, yes and no, missing-value words (unknown, none, declined, not applicable, patient
     refused, ...), US census race and ethnicity categories (the 1997 and 2024 standards,
     with their detailed checkboxes), result flags (H, L, normal, positive, not detected,
     susceptible, ...), laterality, response categories (CR, partial response, stable
     disease, ...), smoking status, units, and a few common words in scripts without capital
     letters (男, 女, 是, 否, 阳性, 남, 여, ذكر, נקבה, पुरुष, ชาย, ...). A value is matched whole,
     never word by word, so "Female (45)" and "Alice White" are not verified. Under a column
     name that names a person, a role, a relative, a contact or a place (`Referring
     Physician`, `Visit Dr`, `Contact Preference`, `Family History`, `Visit Location`), only the
     missing-value words count, because White, Black and other vocabulary words are also
     surnames. A column of single letters must take them all from one group (M and F, Y and N,
     L, R and B, H, L and N, S, I and R), because a few initials span several groups;
   - (d) a date, which step 3 reduces to the year, or, under a state or country column, a US
     state, territory or postal code, a Canadian province, an Australian state, or a country
     name or ISO code.
   Every other text column is **text the script cannot verify**. It is redacted, and the plan
   lists it as needing the person's decision: "redact: text the script cannot verify is free
   of identifiers; keep with --keep COLUMN once the person confirms it". The finding counts
   its values and says how many are shaped like names or places, or written in a script
   without capital letters, so the person can tell a column of names from a column of
   diagnoses; the script prints no value.
6. **Columns the scanner cannot vouch for** for other reasons are redacted or pseudonymized
   unless the person keeps them with `--keep`: some cells hold identifier patterns, the values
   have one of the number shapes of step 4, or the column has a name of step 2. **Free text**
   (a value of 5 or more words or over 50 characters that is not made of category words, or a
   long run of a script without capital letters) can never be kept, because a name inside a
   sentence has no pattern to find.
7. **Kept columns are scrubbed**: each identifier pattern inside a cell is replaced with a
   placeholder such as `[PHONE]`, and a full date becomes its year. A whole value of a code
   grammar keeps the shape the generic code rule would replace (`S72001A` under a diagnosis
   column, `C10AA05` under a drug column); every other pattern is still replaced. The report
   lists the kept text columns (`kept_text_columns`, each marked `verified` or kept on
   request). A text column the person kept with `--keep` is scrubbed for patterns only: a
   name, a place or another identifier with no pattern stays in it. The run prints these
   columns again ("Kept on the person's word, scrubbed for patterns only"), the report lists
   them in `kept_unverified_text_columns` with a note that says so, and the person must
   spot-check each one. `--keep` on a column the run keeps anyway records it as kept on
   request.
8. **Residual check.** The output is scanned again before it is written. Every kept column
   is scanned for identifier patterns. A column kept by default is also checked by the
   number shapes of step 4 and verified again by step 5. A column the person named with
   `--keep` is trusted for those shapes (names, places, numbers), never for patterns. If
   anything remains, nothing is written and the run exits with 3. `verify` without the run's
   report cannot know which columns the person kept, so their text fails as text it cannot
   verify. Passing it means no pattern or shape was found; it is not proof that the output
   is de-identified.

## The 18 identifiers

| # | Identifier | What the script does | What a person still checks |
|---|---|---|---|
| A | Names | Patient name columns, and columns named for the person (`participant`, `proband`, `first`, `fname`, `nm`), become pseudonyms (`P0001`, the same person keeps the same one); names of relatives, contacts, employers, schools, clinicians and other roles become `[REDACTED]`. Every other text column is kept only when every value is verified (step 5), so a name in any form is redacted by default whatever the column is called: with a qualifier (`Nakamura, Alice (wife)`, `Alice Nakamura - RN`), in lower case, as initials, a surname alone, or in a script without capital letters (Chinese, Japanese, Korean, Arabic, Hebrew, Hindi, Thai). Titled or labelled names in kept text (`Dr. X`, `Patient: X`, `Patient Name: X`, also `Dr. 박지훈` and `Patient: 林子涵`) become `[NAME]` | Names with no title or label in a column the person kept with `--keep` (`kept_unverified_text_columns`), which is scrubbed for patterns only; a vocabulary word that is also a surname (White, Black) under a column name that names no person, role or place |
| B | Geography smaller than a state | Street, city, county, hometown, suburb, locality, district, precinct, census, coordinate and place-of-birth columns (also `ciudad`, `municipio`, `ville`, `stadt`, ...) become `[REDACTED]`, and `region`, `home` and `place` columns unless the person keeps them. A town under any other column name is text the script cannot verify, redacted by default (`Visit Location`, `Service Area`, `Cohort`, `Col3`). State and country columns are kept, as Safe Harbor allows, when every value is a state, territory, province or country name or code; a county or a town in one makes the column text the script cannot verify. ZIP columns keep the first three digits, or `000` for the 17 prefixes of 20,000 people or fewer (HHS list, 2000 Census). Unnamed columns of mostly five-digit numbers, and adjacent latitude and longitude columns, are redacted by shape. Street addresses, PO boxes, ZIP+4, "City, ST", labelled coordinates, degrees with N/S/E/W and precise "lat, lon" pairs in kept text are replaced | A bare five-digit ZIP inside kept text; a ZIP column under an unknown name whose values mostly lost their leading zero; a lone coordinate column; towns in a column the person kept; the ZIP list against current Census data |
| C | Dates and ages over 89 | Date columns keep the year only, and so does a column of a year and a month with no day under any name (`2021-03`, `2021/03`, `2021-3`, `2021 Mar`, `202103`, `2021.03`); a date with no four-digit year, or text that is not a missing-value word such as "unknown", becomes `[DATE]`. A birth date or birth year of someone aged 90 or over becomes `[90_OR_OLDER]`, also in unnamed columns of old years. A month and a day written as a number with no separator (`0314`, `03142021`) makes a column `[REDACTED]`. Age columns over 89 become `90+`, also under age names in other languages (`Edad`, `Alter`, `Idade`, `年龄`, `年齢`, `나이`, `Возраст`, `العمر`) (ages in days, weeks, months or hours are converted first, and ages in words such as "ninety-two" count); an age group above 89 becomes `90+`, and one that straddles 90 ("85-94") becomes `[REDACTED]`. Dates in kept text become the year, including a year and a month (`seen on 2021-03`) and a date with a month name in French, German, Spanish, Italian, Portuguese or Dutch and a four-digit year (`14 mars 2021`, `14. März 2021`); a day and a month with no year after a word such as seen, on or dated (`seen 14/3`, `on 03-14`, `seen 14.3.`) become `[DATE]`; a year after "born", "DOB" or "year of birth" of someone 90 or over becomes `[90_OR_OLDER]`; "92 years old", "92 y/o" and "ninety-three yo" become "90+ years"; "a 92F", "pt is 91" and "in her 90s" become 90+, and "nonagenarian" `[90_OR_OLDER]` | Other dates that reveal an age over 89 (a death date next to an age); ages over 89 in an unnamed column of plain numbers; in kept text, a day and a month with no year and no such word before it (`14/3`), a month name in another language with no year, and a year and a month that read as a season or school year (`2011-12` is left alone, because `2010-11` is usually a flu season; a column of months is still reduced as a whole) |
| D | Telephone numbers | Phone columns become `[REDACTED]`; numbers in kept text, including a cell that is only an international number (`+14155550134`), become `[PHONE]` | Local seven-digit numbers with no label |
| E | Fax numbers | As telephone numbers | |
| F | Email addresses | Redacted | |
| G | Social security numbers | Redacted (and national ID numbers of the chosen locale pack) | |
| H | Medical record numbers | Become pseudonyms (`ID0001`), so rows of one patient stay linked; labelled numbers in kept text (`MRN 1234`, `MR# 1234`, `ID 1234`, `#A-998`) become `[ID]` | |
| I | Health plan beneficiary numbers | Member, policy, subscriber, Medicare and Medicaid columns redacted; Medicare MBI-shaped values in text replaced. A payer or type column (`insurance`, `insurance_type`, `medicare_status`) of category words such as Medicare or Commercial is not an identifier by name: Yes and No in it are kept, and other words are redacted as text the script cannot verify until the person keeps the column | |
| J | Account numbers | Account, card and IBAN columns redacted; grouped card numbers and valid IBANs in text replaced | |
| K | Certificate and licence numbers | Licence, certificate, DEA, NPI and passport columns redacted; labelled numbers in text replaced | |
| L | Vehicle identifiers and plates | VIN and plate columns redacted; 17-character VINs and labelled plates in text replaced | Unlabelled plate numbers in text |
| M | Device identifiers and serial numbers | Device ID, serial, UDI and IMEI columns redacted; MAC addresses, GS1 UDIs and labelled serials in text (`serial 8841`, `S/N 8841`, `SN 8841-2290`) replaced | |
| N | Web URLs | Redacted. In kept text: addresses with a scheme or `www.`, a host and a path with neither (`fb.me/jane.doe`), bare domains ending in .com, .org, .net, .edu, .gov, .io, .info or .biz, social media handles (`@jane_doe`, `Facebook /jane.doe`, `Instagram: jdoe`, `skype:jdoe`, `on Instagram as jdoe99`, `u/jdoe`, `jdoe#1234`) and logins written `user@host` | Bare domains on other endings; a handle written with no `@`, no network name and no dot, digit or underscore, or with letters only after a network name and no colon |
| O | IP addresses | Redacted, by column name or by values (IPv4 and IPv6) | |
| P | Biometric identifiers | Fingerprint, voiceprint, retina, iris and face-template columns redacted; long hex or base64 blobs in text replaced | Biometrics stored in another form |
| Q | Full-face photographs | Photo and image columns redacted; image file names and `data:image` values in text replaced | Images themselves (DICOM and photo files are out of scope) |
| R | Any other unique identifying number or code | Unique numbers are pseudonymized; text codes that no closed grammar verifies are redacted until the person keeps them; in kept text, numbers of nine or more digits and codes with four or more digits and a letter become `[ID]` (dbSNP, Ensembl and RefSeq identifiers, and whole values of a code grammar, are left alone) | Rare combinations of values (quasi-identifiers), small cells; a record number that repeats across visits in a column of numbers under a name the rules do not know |

## What the script does not do

- It does not assess rare combinations (age, sex, ZIP prefix and admission year together
  can single out a person), small cells or rare diagnoses. No k-anonymity check is run.
- It reads only the first sheet of an Excel file; the other sheets are not written.
- It does not look inside images, DICOM headers or other attached files.
- It cannot find identifiers written in column names or in the file name.
- It refuses a file that uses `;`, `|` or tabs in a `.csv` file as its separator, because
  each row would be read as one text value; save it with commas, or with tabs as `.tsv`.
- Header names it shows are its only view of the file; a header that looks like a value
  is shown as `#N (name withheld)`, and a file whose first row looks like data is refused.
- The number shapes of step 4 and the column names of step 2 are guesses. A pair of score
  columns can read as coordinates, a column of step counts as ZIP codes, and a column of
  four-digit codes with a leading zero as dates. The plan lists them, and the person keeps
  them with `--keep` once they confirm.
- Its closed lists are short on purpose. Ordinary text columns (diagnoses, drugs, sites,
  arms, visits, organisms, languages, religions, occupations written as words, seasons such
  as `2010-11`, a vital status) are redacted until the person keeps them, and so is a
  vocabulary word with anything around it (`Female (45)`) or a value with a stray full stop.
  Under a column name that names a person, a role, a relative, a contact or a place, even Yes
  and No are redacted (`Family History`, `Contact Preference`).
- A column kept with `--keep` is scrubbed for patterns only. A name, a place or another
  identifier with no pattern stays in it: in lower case, with a qualifier, as initials, as a
  single word, or in a script without capital letters, where only a name after a title or a
  label is found. A year of birth written in prose without a label ("in 1928") is kept.
- A few vocabulary words are also surnames (White, Black) and are kept under a column name
  that names no person, role or place. A column of single letters is kept only when they all
  come from one group (M and F, H, L and N, ...), so first initials from one group pass.
- Its network guard replaces Python's usual socket functions; it is not a sandbox. Run it
  under an operating-system sandbox with networking denied when that must be guaranteed.
