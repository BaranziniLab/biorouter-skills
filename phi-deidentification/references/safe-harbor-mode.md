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
   cannot be kept: `--keep` on one is refused.
2. **By its values.** When more than half of a column's cells are nothing but one
   identifier (all dates, all IP addresses, all codes), the column is replaced the same way.
3. **Columns the scanner cannot vouch for** are redacted unless the person keeps them with
   `--keep`: some cells hold identifier patterns, the column holds free text, the values are
   unique numbers, or most text values are distinct (names and codes look like this).
   Free text can never be kept, because a name inside a sentence has no pattern to find.
4. **Everything else is kept**, and every kept cell is scrubbed: each identifier pattern
   inside it is replaced with a placeholder such as `[PHONE]`, and a full date becomes its year.
5. **Residual check.** The output is scanned again before it is written. If any identifier
   pattern or untransformed value remains, nothing is written and the run exits with 3.

## The 18 identifiers

| # | Identifier | What the script does | What a person still checks |
|---|---|---|---|
| A | Names | Patient name columns become pseudonyms (`P0001`, the same person keeps the same one); names of relatives, contacts, employers and clinicians become `[REDACTED]`. Titled or labelled names in kept text (`Dr. X`, `Patient: X`) become `[NAME]` | Names in kept short-text columns with no title or label |
| B | Geography smaller than a state | Street, city, county, precinct, census and coordinate columns become `[REDACTED]`. ZIP columns keep the first three digits, or `000` for the 17 prefixes of 20,000 people or fewer (HHS list, 2000 Census). Street addresses, PO boxes, ZIP+4 and "City, ST" in kept text are replaced | A ZIP column under another name (a bare five-digit number cannot be told from other codes); the ZIP list against current Census data |
| C | Dates and ages over 89 | Date columns keep the year only; a date with no four-digit year becomes `[DATE]`. A birth date or birth year of someone aged 90 or over becomes `[90_OR_OLDER]`. Age columns over 89 become `90+` (ages in days, weeks or months are converted first). Dates in kept text become the year; "92 years old" becomes "90+ years" | Other dates that reveal an age over 89 (a death date next to an age) |
| D | Telephone numbers | Phone columns become `[REDACTED]`; numbers in kept text become `[PHONE]` | Local seven-digit numbers with no label |
| E | Fax numbers | As telephone numbers | |
| F | Email addresses | Redacted | |
| G | Social security numbers | Redacted (and national ID numbers of the chosen locale pack) | |
| H | Medical record numbers | Become pseudonyms (`ID0001`), so rows of one patient stay linked; labelled numbers in kept text (`MRN 123`) become `[ID]` | |
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
