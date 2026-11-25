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
   `patient_age_years`, `age_days` or `age_group`; a place of birth as `birthplace` or
   `birth_city`. `birth_weight`, `birth_order` and similar describe the birth, not its date,
   and are left to the value rules.
2. **By its values.** When more than half of a column's cells are nothing but one
   identifier (all dates, all IP addresses, all codes), the column is replaced the same way.
3. **By the shape of its numbers**, for columns whose name says nothing:
   - four-digit years, any of them at least 90 years before the reference year: they may
     be birth years, so those years become `[90_OR_OLDER]` and the rest stay;
   - a column named for years (`years`, `yrs`) holding values over 89: possible ages,
     grouped as `90+`;
   - at least 80% five-digit numbers: possible ZIP codes, redacted (a white cell count
     mixes four and five digits and is kept);
   - two adjacent columns of decimal numbers shaped like latitude (within 90) and
     longitude (within 180), with three or more decimal places, or two when the second
     column passes 90 with one sign, and a value of 10 or more in one of them: redacted.
   These are columns the scanner cannot vouch for, so the person can keep one with `--keep`.
4. **Columns the scanner cannot vouch for** are redacted unless the person keeps them with
   `--keep`: some cells hold identifier patterns, the column holds free text, the values are
   unique numbers, or most text values are distinct (names and codes look like this).
   Free text can never be kept, because a name inside a sentence has no pattern to find.
5. **Everything else is kept**, and every kept cell is scrubbed: each identifier pattern
   inside it is replaced with a placeholder such as `[PHONE]`, and a full date becomes its year.
6. **Residual check.** The output is scanned again before it is written, for patterns and
   for the number shapes of step 3 in kept columns (except those kept on request). If
   anything remains, nothing is written and the run exits with 3. Passing it means no
   pattern or shape was found; it is not proof that the output is de-identified.

## The 18 identifiers

| # | Identifier | What the script does | What a person still checks |
|---|---|---|---|
| A | Names | Patient name columns become pseudonyms (`P0001`, the same person keeps the same one); names of relatives, contacts, employers and clinicians become `[REDACTED]`. Titled or labelled names in kept text (`Dr. X`, `Patient: X`) become `[NAME]` | Names in kept short-text columns with no title or label |
| B | Geography smaller than a state | Street, city, county, precinct, census, coordinate and place-of-birth columns become `[REDACTED]`. ZIP columns keep the first three digits, or `000` for the 17 prefixes of 20,000 people or fewer (HHS list, 2000 Census). Unnamed columns of mostly five-digit numbers, and adjacent latitude and longitude columns, are redacted by shape. Street addresses, PO boxes, ZIP+4, "City, ST", labelled coordinates, degrees with N/S/E/W and precise "lat, lon" pairs in kept text are replaced | A bare five-digit ZIP inside text; a ZIP column under an unknown name whose values mostly lost their leading zero; a lone coordinate column; the ZIP list against current Census data |
| C | Dates and ages over 89 | Date columns keep the year only; a date with no four-digit year, or text that is not a missing-value word such as "unknown", becomes `[DATE]`. A birth date or birth year of someone aged 90 or over becomes `[90_OR_OLDER]`, also in unnamed columns of old years. Age columns over 89 become `90+` (ages in days, weeks, months or hours are converted first, and ages in words such as "ninety-two" count); an age group above 89 becomes `90+`, and one that straddles 90 ("85-94") becomes `[REDACTED]`. Dates in kept text become the year; a year after "born", "DOB" or "year of birth" of someone 90 or over becomes `[90_OR_OLDER]`; "92 years old" and "ninety-three yo" become "90+ years" | Other dates that reveal an age over 89 (a death date next to an age); ages over 89 in an unnamed column of plain numbers |
| D | Telephone numbers | Phone columns become `[REDACTED]`; numbers in kept text, including a cell that is only an international number (`+14155550134`), become `[PHONE]` | Local seven-digit numbers with no label |
| E | Fax numbers | As telephone numbers | |
| F | Email addresses | Redacted | |
| G | Social security numbers | Redacted (and national ID numbers of the chosen locale pack) | |
| H | Medical record numbers | Become pseudonyms (`ID0001`), so rows of one patient stay linked; labelled numbers in kept text (`MRN 1234`, `MR# 1234`, `ID 1234`, `#A-998`) become `[ID]` | |
| I | Health plan beneficiary numbers | Member, policy, subscriber, Medicare and Medicaid columns redacted; Medicare MBI-shaped values in text replaced | |
| J | Account numbers | Account, card and IBAN columns redacted; grouped card numbers and valid IBANs in text replaced | |
| K | Certificate and licence numbers | Licence, certificate, DEA, NPI and passport columns redacted; labelled numbers in text replaced | |
| L | Vehicle identifiers and plates | VIN and plate columns redacted; 17-character VINs and labelled plates in text replaced | Unlabelled plate numbers in text |
| M | Device identifiers and serial numbers | Device ID, serial, UDI and IMEI columns redacted; MAC addresses, GS1 UDIs and labelled serials in text replaced | |
| N | Web URLs | Redacted | Bare domain names without `www.` or a scheme |
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
- Header names it shows are its only view of the file; a header that looks like a value
  is shown as `#N (name withheld)`, and a file whose first row looks like data is refused.
- The number shapes of step 3 are guesses. A pair of score columns can read as
  coordinates, and a column of step counts as ZIP codes; the plan lists them, and the
  person keeps them with `--keep` once they confirm.
- Its network guard replaces Python's usual socket functions; it is not a sandbox. Run it
  under an operating-system sandbox with networking denied when that must be guaranteed.
