# What safe_harbor.py does with each Safe Harbor identifier

Reference for `scripts/safe_harbor.py`. The rule is 45 CFR 164.514(b)(2): the 18
identifiers of the person, and of the person's relatives, employers and household
members, are removed, and the covered entity has no actual knowledge that what
remains could identify the person. The script does the removal it can automate.
The second half is a human determination.

`references/hipaa_18_identifiers.md` describes the interactive `deidentify.py`
instead, which shifts dates and leaves several of these to the researcher.

## How a column is decided

1. **By its name.** A column named for an identifier (`patient_name`, `dob`, `zip_code`,
   `mrn`, `fax`, `vehicle_vin`, ...) is replaced as the table below says. These columns
   cannot be kept: `--keep` on one is refused. Names are read as words, in any spelling the
   rules know: a birth year as `birth_year`, `yob`, `born`, `byear`, `birth_yr`,
   `yr_birth` or `year_born`; an age as `age`, `ageyrs`, `age_at_dx`, `pt_age`,
   `patient_age_years`, `age_days` or `age_group`; a place of birth as `birthplace`,
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
   allowed and kept.

   A type or status column of an identifier word (`insurance_type`, `insurance_status`,
   `subscriber_status`, `medicaid_eligible`, `account_type`, `license_status`,
   `login_status`, `city_type`, `employer_type`, `type_of_insurance`) is not the identifier
   when its values are a handful of category words with no digit and no identifier
   pattern (Medicare, Commercial, Active, Urban); a payer column (`insurance`, `medicare`)
   is not either, unless its name also says number, ID, member or policy. These go to the
   value rules and are usually kept. For employer, place and login words every value must
   be a known category word, because a single unknown word there can be the employer, the
   town or the login itself. With numbers, codes or names in it, the same column is still
   an identifier by name and cannot be kept.
2. **By a column name that usually holds a name or a place.** A whole column name such as
   `subject`, `member`, `insured`, `first`, `last`, `given`, `parent`, `sibling`, `contact`,
   `family`, `region`, `home`, `company` or `school` has other uses (`insured` can be yes or
   no, `region` a census region), so these are pseudonymized or redacted as columns the
   scanner cannot vouch for, and the person can keep one with `--keep`. When every value is
   a common category word ("Yes", "Mother"), or, apart from `subject` and similar names of
   the person, every value is a number, the rule does not apply.
3. **By its values.** When more than half of a column's cells are nothing but one
   identifier (all dates, all IP addresses, all codes), the column is replaced the same way.
4. **By the shape of its values**, for columns whose name says nothing:
   - four-digit years, any of them at least 90 years before the reference year: they may
     be birth years, so those years become `[90_OR_OLDER]` and the rest stay;
   - a column named for years (`years`, `yrs`) holding values over 89: possible ages,
     grouped as `90+`;
   - at least 80% five-digit numbers: possible ZIP codes, redacted (a white cell count
     mixes four and five digits and is kept);
   - two adjacent columns of decimal numbers shaped like latitude (within 90) and
     longitude (within 180), with three or more decimal places, or two when the second
     column passes 90 with one sign, and a value of 10 or more in one of them: redacted;
   - text values shaped like names or places: one to four capitalised words ("Alice",
     "Bob Zeller", "Zeller, Alice", "ZELLER ALICE", "San Francisco", "Okafor family") that
     are not all common category or medical words (Male, White, Never, Positive, Home,
     Breast, Cardiology, Physician, Fibrillation, Medicare, Teacher, and words ending like a
     disease, a procedure, an anatomical adjective or a drug stem, such as -itis, -ectomy,
     -ation, -ular, -mab or -statin): redacted, unless it is a category column. A category
     column is recognised by its name and its values together:
     - its name says what category its values are (`diagnosis`, `drug`, `race`, `status`,
       `visit type`, `primary site`, `biomarker`, `occupation`, `cell line`, ...);
     - its name names no person or role. A role word anywhere (`physician`, `nurse`,
       `surgeon`, `provider`, `coordinator`, `verifier`, `approver`, `attorney`, `pastor`,
       `companion`, `medico`, `medecin`, `arzt`, words ending in -ician, -ist, -grapher or
       -ee, a sign-off, `by` or `with` after another word, `to` after a word such as
       `assigned` or `referred`), or as its last word a person, a title or a word for whoever
       does something (`patient`, `subject`, `contact`, `head`, `dr`, `prof`, `team`,
       `emergency`, `responsible`, and -er or -or words such as `scheduler` or `releaser`,
       but not `marker`, `number` or `tumor`), makes it a column of people, whose names
       repeat across visits as much as any category does. Last words with a common other
       meaning (`doc`, `admin`, `charge`, `family`) are left to the values, below;
     - its name names no place (`location`, `place`, `area`, `site` outside a body site,
       `setting`, `venue`, `locale`, `zone`, `campus`, `center`, `facility`, `clinic`,
       `hospital`, `region`, `catchment`, `lugar`, `ubicacion`, ...), which makes it a column
       of places;
     - its values repeat like a category: 20 or fewer distinct values, or each seen three
       times on average;
     - and few of its values have the shape of a name of a person or a place: two or more
       capitalised words none of which is a category, medical or anatomical word ("Alice
       Okafor", "Okafor, Alice B.", "OKAFOR ALICE", "Alice Okafor MD", "Walnut Grove"),
       and, when the last word of the column name is not a category noun (`Visit Host`, as
       opposed to `Visit Type` or `Diagnosis Code`), a single capitalised word the
       vocabulary does not know ("Okafor"). Two such values, or a third of the distinct
       values, make it a column of names, whatever its name says.

     So `Treatment Physician`, `Visit Dr`, `Test Verifier`, `Lab Sign-off`, `Visit
     Location`, `Service Area` and `Diagnosis` holding names of people are checked like any
     other column, while `Patient Diagnosis`, `Contact Method`, `Head Injury Type`, `Tumor
     Marker`, `Doc Type` and a `Diagnosis` of Heart Failure and Atrial Fibrillation are
     category columns. Under a place or role word, values that are all category words
     ("Inpatient", "Left Upper Lobe", "Cardiology Team") are still kept.
   These are columns the scanner cannot vouch for, so the person can keep one with `--keep`.
5. **Columns the scanner cannot vouch for** are redacted unless the person keeps them with
   `--keep`: some cells hold identifier patterns, the column holds free text, the values are
   unique numbers, or most text values are distinct (names and codes look like this).
   Free text can never be kept, because a name inside a sentence has no pattern to find. A
   long value made only of category words ("American Indian or Alaska Native") is not free
   text.
6. **Everything else is kept**, and every kept cell is scrubbed: each identifier pattern
   inside it is replaced with a placeholder such as `[PHONE]`, and a full date becomes its year.
   The plan, the run and the report (`kept_text_columns`) list the kept columns that hold
   text, because a name in lower case, initials, a short all-capital name, a single word
   under a category column name (a surname alone, a one-word town) or a place under a state
   or country column is not found; the person confirms each one. `--keep` on a column the run keeps anyway records it as kept on
   request.
7. **Residual check.** The output is scanned again before it is written, for patterns and
   for the shapes of step 4 in kept columns. Columns the person named with `--keep`, and
   state and country columns, are scanned for patterns only: the person has confirmed their
   shape, or confirms it from the kept text list. If anything remains, nothing is written
   and the run exits with 3. Passing it means no pattern or shape was found; it is not
   proof that the output is de-identified.

## The 18 identifiers

| # | Identifier | What the script does | What a person still checks |
|---|---|---|---|
| A | Names | Patient name columns, and columns named for the person (`participant`, `proband`, `first`, `fname`, `nm`), become pseudonyms (`P0001`, the same person keeps the same one); names of relatives, contacts, employers, schools, clinicians and other roles become `[REDACTED]`. Columns of capitalised words that are not category words are redacted whatever their name, unless they are category columns (step 4); a column named for a role, a title or a person (`Treatment Physician`, `Visit Dr`, `Test Verifier`, `Event Patient`) never is one, and names of two or more words make any category column a column of names. Titled or labelled names in kept text (`Dr. X`, `Patient: X`, `Patient Name: X`) become `[NAME]` | Names in kept text with no title or label, in lower case, as a short all-capital word or initials, or as a single word (a surname alone) under a category column name with no person or role in it (the kept text columns the run lists) |
| B | Geography smaller than a state | State and country columns are kept, as Safe Harbor allows, and listed for the person to confirm. Street, city, county, hometown, suburb, locality, district, precinct, census, coordinate and place-of-birth columns (also `ciudad`, `municipio`, `ville`, `stadt`, ...) become `[REDACTED]`, and `region`, `home` and `place` columns unless the person keeps them. Town names under a category word and a place word (`Visit Location`, `Service Area`, `Treatment Center`, `Event Setting`) are redacted by their shape, as are place names of two or more words under any category column. ZIP columns keep the first three digits, or `000` for the 17 prefixes of 20,000 people or fewer (HHS list, 2000 Census). Unnamed columns of mostly five-digit numbers, and adjacent latitude and longitude columns, are redacted by shape. Street addresses, PO boxes, ZIP+4, "City, ST", labelled coordinates, degrees with N/S/E/W and precise "lat, lon" pairs in kept text are replaced | A bare five-digit ZIP inside text; a ZIP column under an unknown name whose values mostly lost their leading zero; a lone coordinate column; a one-word town under a category column name with no place word (`Cohort`, `Visit`); that a state or country column holds only states or countries; the ZIP list against current Census data |
| C | Dates and ages over 89 | Date columns keep the year only; a date with no four-digit year, or text that is not a missing-value word such as "unknown", becomes `[DATE]`. A birth date or birth year of someone aged 90 or over becomes `[90_OR_OLDER]`, also in unnamed columns of old years. Age columns over 89 become `90+` (ages in days, weeks, months or hours are converted first, and ages in words such as "ninety-two" count); an age group above 89 becomes `90+`, and one that straddles 90 ("85-94") becomes `[REDACTED]`. Dates in kept text become the year; a year after "born", "DOB" or "year of birth" of someone 90 or over becomes `[90_OR_OLDER]`; "92 years old", "92 y/o" and "ninety-three yo" become "90+ years"; "a 92F", "pt is 91" and "in her 90s" become 90+, and "nonagenarian" `[90_OR_OLDER]` | Other dates that reveal an age over 89 (a death date next to an age); ages over 89 in an unnamed column of plain numbers |
| D | Telephone numbers | Phone columns become `[REDACTED]`; numbers in kept text, including a cell that is only an international number (`+14155550134`), become `[PHONE]` | Local seven-digit numbers with no label |
| E | Fax numbers | As telephone numbers | |
| F | Email addresses | Redacted | |
| G | Social security numbers | Redacted (and national ID numbers of the chosen locale pack) | |
| H | Medical record numbers | Become pseudonyms (`ID0001`), so rows of one patient stay linked; labelled numbers in kept text (`MRN 1234`, `MR# 1234`, `ID 1234`, `#A-998`) become `[ID]` | |
| I | Health plan beneficiary numbers | Member, policy, subscriber, Medicare and Medicaid columns redacted; Medicare MBI-shaped values in text replaced. A payer or type column (`insurance`, `insurance_type`, `medicare_status`) of category words such as Medicare or Commercial is kept | |
| J | Account numbers | Account, card and IBAN columns redacted; grouped card numbers and valid IBANs in text replaced | |
| K | Certificate and licence numbers | Licence, certificate, DEA, NPI and passport columns redacted; labelled numbers in text replaced | |
| L | Vehicle identifiers and plates | VIN and plate columns redacted; 17-character VINs and labelled plates in text replaced | Unlabelled plate numbers in text |
| M | Device identifiers and serial numbers | Device ID, serial, UDI and IMEI columns redacted; MAC addresses, GS1 UDIs and labelled serials in text (`serial 8841`, `S/N 8841`, `SN 8841-2290`) replaced | |
| N | Web URLs | Redacted. In kept text: addresses with a scheme or `www.`, a host and a path with neither (`fb.me/jane.doe`), bare domains ending in .com, .org, .net, .edu, .gov, .io, .info or .biz, social media handles (`@jane_doe`, `Facebook /jane.doe`) and logins written `user@host` | Bare domains on other endings; a handle written with no `@`, no network name and no dot, digit or underscore |
| O | IP addresses | Redacted, by column name or by values (IPv4 and IPv6) | |
| P | Biometric identifiers | Fingerprint, voiceprint, retina, iris and face-template columns redacted; long hex or base64 blobs in text replaced | Biometrics stored in another form |
| Q | Full-face photographs | Photo and image columns redacted; image file names and `data:image` values in text replaced | Images themselves (DICOM and photo files are out of scope) |
| R | Any other unique identifying number or code | Unique numbers and mostly distinct codes are pseudonymized or redacted; in kept text, numbers of nine or more digits and codes with four or more digits and a letter become `[ID]` (dbSNP and Ensembl identifiers are left alone) | Rare combinations of values (quasi-identifiers), small cells |

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
- The shapes of step 4 and the column names of step 2 are guesses. A pair of score
  columns can read as coordinates, a column of step counts as ZIP codes, and a column of
  hospital, site, clinic or facility names as names or places; so can a category column
  whose name also names a role or a place (`provider_specialty`, `tumor_location`) with
  values the medical vocabulary does not know. The plan lists them, and the person keeps
  them with `--keep` once they confirm.
- A category column with no person, role or place in its name is read for names of two
  or more words, but not for single words: a column named `diagnosis` or `cohort` holding
  surnames alone, or one-word towns, that repeat across visits is kept and only listed.
  Names in lower case ("alice okafor"), initials and a single lower-case word are not
  found by their shape anywhere (a column of mostly distinct ones is still redacted as
  possible names or codes), and a year of birth written in prose without a label ("in
  1928") is kept.
- Its network guard replaces Python's usual socket functions; it is not a sandbox. Run it
  under an operating-system sandbox with networking denied when that must be guaranteed.
