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

A second review round found the same kind of gap in numbers: record numbers that repeat
across visits passed under 78 of 91 column names (`Chart`, `Hosp No`, `Patid`, `病历号`,
`Col6`), birth years over 89 passed under date column names the rules did not read as birth
dates (`DoB`, `Geburtsdatum`, `出生日期`, `Event Date`), and ages over 89 under age names the
word lists did not know (`Alter bei Diagnose`, `Kor`, `年紀`). Since then numbers fail closed
too: a column of numbers is kept only when it reads as measurements (step 4), every date
column withholds a year 90 or more years ago, and whole numbers up to 125 with some over 89
are grouped as ages unless the column name names a measurement. The word lists remain, to give
better reasons and to make the clearest columns impossible to keep, but no longer decide
whether a value is kept.

A third review round found the gaps that were left in the same two places, and one new one.
Numbers were still judged by their majority, so up to half of a column could be record numbers,
and one decimal, `<1` or outlier switched off the age check; scientific notation, numeric month
and day columns, lone coordinates and Excel serials under time names passed as measurements.
Since then every number is judged on its own (step 4). The new gap was the header row: in a
file without one, a first row of data was read as column names, and a single surname, a titled
name or a name in a script without capital letters was printed, reported and written as a
column name. Column names now fail closed like values (step 0): a name is shown only when every
word in it is a column word the script knows.

A fourth review round found the list pattern in three more places, and one in the numbers of a
column name. `--keep`, the person's override, was accepted for columns named as a relative, a
record number, an address, an email, a plate, a device or notes whenever the word was not
English or not on a list (`Pai`, `Mae`, `父`, `Patientennummer`, `Prontuário`, `Courriel`,
`Kennzeichen`, `Mom`, `ICE`, `AKA`), so `--keep` now fails closed too (step 6): it is refused
unless every word of the column name is a column word the script knows, and when the name ends
in someone other than a clinician or a member of staff, an employer, a school, a home, an
address, a device, an image or notes. Split dates kept their month and day under names the date
word lists did not know (`Mnth`, `DoM`, `Tg`, `SM`, `SD`, `Ay`, `Gün`, `Zi`, `Dan`), so a month
or a day in a column of its own is now found by its numbers, whatever the column is called (step
4). A column that mixed precise and rounded coordinates was kept, because the coordinate check
needed most cells to be precise; it now judges each cell. And a column name could carry a record
number, a ZIP code, a coordinate or an old year (`Patient 3767393`, `Weight 94110`, `Weight
37.7749`), which the first row's check did not know; such a name is now refused (step 0).

## How a column name is shown

0. **Column names.** The first row is the header row unless the person says the file has none
   (`--no-header`, which reads every row as data and names the columns `column_1`,
   `column_2`, ...). A header cell is shown in the plan and the report and copied to the output
   only when every word in it is a word column names are made of: the words the rules below
   read, the category, medical and anatomical words of step 5, a list of ordinary column words
   (in several languages, and common words of other scripts such as `性别`, `진단`, `Диагноз`),
   single letters, short numbers, and codes of letters and digits (`TP53`, `Col1`, `Q3`, `2nd`,
   `ENSG00000141510`). A number in a column name is not a column word the way a value is verified:
   a run of five or more digits (`Patient 3767393`, `Weight 94110`, `4,527,832`, `376-7393`), a
   decimal of four or more places (`Weight 37.7749`) and a year 90 or more years before the
   reference year (`Cohort 1925`) make the first row refused, like an identifier pattern, and
   `--keep-all-names` does not override it: the person renames those columns. The digits of a
   closed code are not counted (Ensembl, RefSeq, rsID, a genomic position after `chr`). A first-row
   cell of a few letters and digits with a leading zero, or of letters the column words do not
   know and three or more digits (`S001`, `sub01`, `PT-0042`, `ABC123`), is withheld as a value.
   At least one word must not also be a common surname or given name: `Reference Low` is shown,
   `Low`, `Ward`, `White` and `Rose Hall` alone are not. Any other cell is withheld as `#N (name
   withheld)` and the output names the column `column_N`, until the person confirms it with
   `--keep-name #N` (or `--keep-all-names` for the whole first row). A first row with an
   identifier pattern in any cell is refused, and so is one in which a third of the cells look
   like values or names, unless the person confirms it; two cells with the same name are refused
   by position, without printing them. The rules below read the real column name whether it is
   shown or not.

## How a column is decided

1. **By its name.** A column named for an identifier (`patient_name`, `dob`, `zip_code`,
   `mrn`, `fax`, `vehicle_vin`, ...) is replaced as the table below says. These columns
   cannot be kept: `--keep` on one is refused. Names are read as words, in any spelling the
   rules know: a birth year as `birth_year`, `yob`, `YoB`, `born`, `byear`, `birth_yr`,
   `yr_birth` or `year_born`; a birth date as `dob`, `DoB`, `BDate`, `B_Date`, `D of B`,
   `Bth Dt`, `Natal`, `Geburt`, `Geburtsdatum`, `Gebdatum`, `naissance`, `Date de naissance`,
   `Fecha de nacimiento`, `Fecha Nac`, `FDN`, `Data Nasc`, `Data di nascita`, `Doğum Tarihi`,
   `Tanggal Lahir`, `Ngày sinh`, `出生日期`, `生年月日`, `생년월일`, `Дата рождения`, `ДР`,
   `تاريخ الميلاد`, `תאריך לידה`, `जन्मतिथि` or `วันเกิด`; an age as `age`, `ageyrs`,
   `age_at_dx`, `pt_age`, `patient_age_years`, `age_days`, `age_group`, `Years Old` or
   `Months Old`, and in other languages as `edad`, `idade`, `alter`, `età`, `leeftijd`, `wiek`,
   `ålder`, `ikä`, `věk`, `yaş`, `edat`, `年龄`, `年纪`, `年齢`, `나이`, `연령`, `연세`, `возраст`,
   `العمر`, `גיל`, `आयु`, `বয়স`, `வயது` or `อายุ`, with any qualifier (`Alter bei Diagnose`,
   `Ålder vid diagnos`, `Věk (roky)`) and in compounds (`Patientenalter`, `Aufnahmealter`,
   `Alters`); words for age with a common other meaning (`Kor`, and `ETA` alone, which is also
   an arrival time) are left to the ages rule of step 4. A place of birth is `birthplace`,
   `birth_city`, `pob`, `Lieu de naissance` or `出生地`. A whole column name that is the person
   (`participant`, `proband`, `individual`, `client`, `respondent`, `decedent`) is
   pseudonymized; one that is a relative or a contact (`mother`, `father`, `spouse`,
   `husband`, `wife`, `guardian`, `caregiver`, `informant`, `Next Kin`) is redacted; `fname`,
   `lname`, `forename`, `nm`, `pt_nm`, `sukunimi` and `soyadı` are names, and so are `姓名`,
   `氏名`, `성명`, `ФИО` anywhere in a column name and `名前`, `이름`, `اسم`, `שם`, `नाम`,
   `ชื่อ`, `Имя` and `Фамилия` alone or beside a word for the patient (`患者名前`, `환자 이름`);
   and `hometown`, `suburb`, `locality`, `district`, `township` and `Lives In` are geography
   smaller than a state. A column whose last word names a relative, a household member or a
   contact (`Contact Person`, `Primary Contact`, `Household Member`, `Landlord`, `Roommate`,
   `Lives With`), or whose whole name is `first`, `last`, `given`, `middle` or `maiden`, is an
   identifier by name too and cannot be kept, unless every value is a category word (Mother,
   Spouse, Yes) or a number; a name whose last word is something else (`Contact Method`,
   `Family History`, `Household Size`) goes to the value rules. A name column of a clinician, staff member or other role is redacted even beside a
   word such as `lab` or `study` (`lab_technician_name`, `specimen_collector_name`), and
   `study_patient_name` is the person's own name, pseudonymized; a title or role word counts
   as well (`visit_dr_name`, `test_verifier_name`, `nombre_medico`). Names and places are
   also read in other languages (`nombre`, `apellido`, `nom`, `vorname`, `cognome`; `ciudad`,
   `municipio`, `ville`, `stadt`, `citta`), and accents in a column name are ignored
   (`Médecin` reads as `medecin`). `birth_weight`, `birth_order` and similar describe the
   birth, not its date, and are left to the value rules. State and country columns
   (`state`, `country`, `country_of_birth`, `country_of_origin`, `nationality`, ...) are
   allowed, and kept when their values verify (step 5). Since round 3 these are identifiers
   by name too: phone and postal code columns in other languages (`Telefon`, `Teléfono`,
   `Telefone`, `Celular`, `PLZ`, `CEP`, `Postleitzahl`, `Código Postal`, `Codice Postale`);
   coordinates by their whole word in any script (`Latitude`, `Easting`, `Northing`, `UTM`,
   `Breitengrad`, `Latitud`, `纬度`, `위도`, `Широта`); and, when any value is a word that is not
   a category word, a column named for a social network (`Twitter`, `Instagram`, `TikTok`,
   `LinkedIn`, `WeChat`) or one of the whole names of step 2 that name the person (`Subject`,
   `Member`, `Insured`, `Donor`, `Recipient`, `Resident`, `Policyholder`).

   Round 4 added, as identifiers by name: names and readings of names (`AKA`, `Pseudonym`,
   `Moniker`, `Kana`, `Furigana`, `Pinyin`, `Romaji`, `Nama`, `İsim`, `Jmeno`, `Nimi`,
   `Patientnavn`, and `Tên`, `Ad`, `Adı`, `Ime`, `Jina` alone or beside a word for the patient,
   `Hasta Adı`; `姓`, `氏`, `名`, `성` and `フリガナ` in scripts); street addresses (`Dirección`,
   `Adresse`, `Anschrift`, `Straße`, `Calle`, `Rue`, `Indirizzo`, `Endereço`, `Road`, `Apt`, `Suite`,
   `住所`, `주소`, `Адрес`), telephones (`Mobil`, `Handy`, `電話`, `전화`, `Телефон`), email addresses
   (`Courriel`, `Correo`, `メール`, `이메일`, `邮箱`), plates (`Kennzeichen`, `Targa`, `Matricula`,
   `车牌`) and host names; national and social security numbers (`DNI`, `CPF`, `Aadhaar`, `BSN`,
   `AHV`, `Personnummer`, `Fødselsnummer`, `CURP`, `KVNR`, `RUT`, `Cédula`, `RRN`, `My Number`,
   `Codice Fiscale`, `PESEL`, `NRIC`, `Sozialversicherungsnummer`); health cards (`Health Card`,
   `OHIP`, `Medi-Cal`, `NHI`, `Policy No`, `Plan ID`); bills, invoices, receipts and claims as the
   whole name or beside a word for number (`Claim No`, `Invoice`; `Claim Amount` is money);
   medical record numbers in other languages (`Aktenzeichen`, `Fallnummer`, `Prontuário`,
   `Expediente`, `Historia Clínica`, `Cartella Clinica`); and a column named with a word for number
   or record in any language (`Pat No`, `Hospital No`, `Chart`, `Record`, `Patientennummer`,
   `Potilasnumero`, `Numer pacjenta`, `Numéro de dossier`, `Número de historia`, `病历号`, `患者番号`,
   `등록번호`, `Номер карты`, and `NIR`, `NSS`, `CPR`) whose values have four or more digits or are
   codes with digits, unless the name is a count (`Number of Visits`, `Número de visitas`) or the
   number of a thing (`Gene ID`, `Lot No`, `Plate No`).

   A type or status column of an identifier word (`insurance_type`, `insurance_status`,
   `subscriber_status`, `medicaid_eligible`, `account_type`, `license_status`,
   `login_status`, `city_type`, `employer_type`, `type_of_insurance`) is not the identifier
   when its values are a handful of category words with no digit and no identifier
   pattern (Medicare, Commercial, Active, Urban); a payer column (`insurance`, `medicare`)
   is not either, unless its name also says number, ID, member or policy. These go to the
   value rules: Yes and No are verified and kept, and other words are text the script cannot
   verify, which the person can keep with `--keep`. Except for a payer column, every value must
   be a known category word (Mobile, Active, Valid, Urban), because a single unknown word under
   a type or status column of a phone, an email, a ZIP code, a licence, an account, an employer,
   a place or a login can be the person's name, the employer, the town or the login itself.
   With numbers, codes or such words in it, the same column is still an identifier by name and
   cannot be kept.
2. **By a column name that usually holds a name or a place.** A whole column name such as
   `subject`, `member`, `insured`, `region`, `home`, `company` or `school` has other uses
   (`insured` can be yes or no, `region` a census region), so these are pseudonymized or
   redacted as columns the scanner cannot vouch for, and the person can keep one with
   `--keep`. When every value is a common category word ("Yes", "Urban"), or, apart from
   `subject` and similar names of the person, every value is a number, the rule does not apply
   and step 5 decides (`insured` of Yes and No is kept). A name of the person (`subject`,
   `member`, `donor`, ...) with a value that is a word and not a category word is an
   identifier by name (step 1); with numbers or codes (`1001`, `S-014`) it is pseudonymized and
   can be kept. Relatives, contacts and the person's own first or last name are identifiers by
   name (step 1).
3. **By its values.** When more than half of a column's cells that are not missing-value
   words are nothing but one identifier (all dates, all IP addresses, all codes), the column
   is replaced the same way.
   A year and a month with no day counts as a date under any column name (`2021-03`,
   `2021/03`, `2021-3`, `2021 Mar`, `Mar 2021`, `03/2021`), so a monthly export written with
   `%Y-%m` keeps the year only, whether the column is called `Visit Month`, `Period`,
   `Enrolled` or `Col1`.
4. **By the shape of its numbers.** Numbers fail closed like text, and each cell is judged on
   its own: a column of numbers is verified only when every number in it reads as a
   measurement, that is a decimal, a whole number of up to three digits, or a longer whole
   number under a column name that names a measurement (a lab such as `WBC` or `Ferritin`, a
   vital sign, a count such as `Steps` or `Number of Visits`, a score, a dose, a unit such as
   `(mg/dL)` or `%`, money, a duration, a propensity or a z-score), with no word that says
   identifier (`Lab No`, `Sample ID`) and no last word that names what a row is about (`Glucose
   Case`, `Count Patient`, `Dose Encounter`, but `Cost per Case` is a measurement). Otherwise:
   - a whole number of four or more digits in any cell, in any written form (`4527832`,
     `00088221`, `6135517.0`, `2589882.00`, `4,527,832`), unless every cell is a year: possible
     record or account numbers, ZIP codes that lost their leading zero, or dates written as
     numbers, pseudonymized (the same number keeps the same pseudonym, so the rows of one
     patient stay linked) and listed for the person's decision. A leading zero makes such a
     column a code under any column name;
   - a number written with an exponent (`4.52783E+06`, `1.23457e+11`: how Excel saves a long
     record, account or phone number in a CSV), pseudonymized, and a decimal with five or more
     digits before the point (`552345.12`, a grid coordinate in metres), redacted;
   - short whole numbers under a column name of a person's or a record's number (`Study ID`, `Pat
     No`, `Hospital No`, `Subject No`, `Record`, `Chart`, `Case`, `Reference`, `Key`), however few
     their digits: study or record numbers, pseudonymized and kept on the person's word (round
     4); `Visit No`, `Cycle Number` and `Number of Visits` are sequences or counts;
   - whole numbers of seven or more digits that repeat more often than they differ, even under a
     column name that names a measurement (`Score`, `Count`, `Level`, `Total`, `Weight`,
     `Amount`, `Dose`): record numbers, pseudonymized (round 4);
   - whole numbers shaped like dates with no separator in an order the rules below do not
     read (`910314` as YYMMDD, `3262017` and `2016112` with a one-digit month or day), and
     numbers shaped like Excel date and time serials (`44269.4375`): possible dates, redacted.
     The serial check runs under any column name but one that names a measurement other than
     time; under a day, a week, a month, a duration or a bare time (`Visit Day`, `Days`, `LOS`,
     `Event Time`) a whole number from 10000 up counts too, because such a duration is not
     plausible; minutes, seconds and hours are left alone;
   - a whole number from 90 to 125 in any cell (or a number with a unit of time, `95 y`,
     `1140 mo`, `1,100 months`), under a column name that names no measurement, whatever else the
     column holds (a decimal, `<1`, `130`): possible ages, grouped as `90+`; under a column name
     with a word that can mean age or old age (`ETA`, `Old`, `Y Old`, `Year`, `Elderly`, `Senior`,
     `Seniority`) a decimal from 90 to 125 counts too;
   - a day of the month (1 to 31), a month (1 to 12) or a weekday (0 to 7) written as a whole
     number in every cell, under a column name that says so in any language and with any
     qualifier (`Day`, `Admit Day`, `Day of Month`, `DD`, `Month`, `Discharge Month`, `MM`,
     `Mon`, `Mth`, `Mois`, `Monat`, `Mes`, `Tag`, `Jour`, `入院月`, `日`, `월`, `День`, `Weekday`,
     `Day of Week`), or in a column of one short word beside the year it belongs to (`Admit
     Year`, `Admit M`, `Admit D`; `Y`, `M`, `D`; `Dx Yr`, `Dx Mo`): a date element other than
     the year, redacted. Plural durations (`Days`, `Months`), protocol days past 31 and a column
     name that also names a measurement (`Month 6 Pain Score`, `Day 28 Viral Load`) are left to
     the other checks; a day of the year (`DOY`, `Day of Year`, `Julian Day`, 1 to 366) and a week
     of the year (`Epi Week`, `Week of Year`, `ISO Week`, `KW`, 1 to 53) are redacted by name too;
   - a month or a day of a date written in a column of its own, whatever the column is called
     (round 4): whole numbers from 1 to 12 covering seven or more of the months, or from 1 to 31
     covering thirteen or more of the days, and, in a file with a column of years (four-digit
     years under any column name that names no measurement or age, or numbers up to 99 under a
     word for year), every column of whole numbers from 1 to 31 that is not only 1 and 2 (a code
     such as a sex): possible date elements other than the year, redacted. A minority of
     missing-value codes (0, 99, 88, -9, ...) does not hide such a column. Only a column name that
     names a measurement other than a part of a date or a time keeps it (`Pain Score`, `Days`,
     `LOS (days)`, `Number of Visits`, `GCS`, `Hemoglobin`), and so do a stage, a grade or a class
     (`Stage`, `Tumor Grade`, `NYHA Class`) and numbers that include 0 (`ECOG`, `Comorbidities`).
     `Tg` and `MM` alone are read as a day and a month, not as triglycerides and millimetres;
   - decimals of four or more places within 180 under a column name that names no measurement,
     judged cell by cell (round 4): one decimal of four or more places from 1 to 180 in any cell is
     a possible latitude or longitude, so a column that mixes precise and rounded coordinates is
     redacted, and so is a column of such decimals that are all below 1; and numbers in range under a column
     name with an abbreviation for one (`Lat`, `Lon`, `Lng`, `Coord`, `Long` beside a place word
     such as `Home` or `Patient`), redacted, which the person can keep because `Lat` also means a
     latency or a lateral view;
   - four-digit years, any of them at least 90 years before the reference year: they may
     be birth years, so those years become `[90_OR_OLDER]` and the rest stay;
   - a year and a month written as a number in every cell (`202103`, `2021.03`, with a
     month from 01 to 12): dates, reduced to the year;
   - a month and a day written as a number with no separator in every cell (`0314`, `1403`,
     `031421`, `03142021`), with a leading zero in one of them when they have four or six
     digits: possible dates, redacted;
   - a column named for years (`years`, `yrs`, `anni`, `años`, `jahre`, `roky`) holding
     values over 89: possible ages, grouped as `90+`;
   - at least 80% five-digit numbers under a column name that names no measurement: possible
     ZIP codes, redacted;
   - two adjacent columns of decimal numbers shaped like latitude (within 90) and
     longitude (within 180), with three or more decimal places, or two when the second
     column passes 90 with one sign, and a value of 10 or more in one of them: redacted, and
     reported as a pair;
   - unique numbers of five or more digits under a column name that names no measurement:
     possible record or account numbers, pseudonymized.
   The same checks run on the numbers of a column that mixes numbers with other verified
   values (`<0.5`, `5.2 mg/dL`, `unknown`).
5. **Fail closed: every other value must be verified.** A column that no rule above
   replaced is kept only when every value that is not blank is one of:
   - (a) a number, with an optional comparator and unit (`<0.5`, `>= 10`, `5.2 mg/dL`, `12%`,
     `1,250`), or a blood pressure (`120/80`, the first number larger, so a day and a month
     never pass), when the column's numbers pass step 4;
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
     disease, ...), smoking status, and a few common words in scripts without capital
     letters (男, 女, 是, 否, 阳性, 남, 여, ذكر, נקבה, पुरुष, ชาย, ...). Census race and
     ethnicity words count only under a column name for race or ethnicity (`Race`,
     `Ethnicity`, `Raza`, `人种`), and bare units (`mg/dL`, `Ng`, `Min`) only under a column name
     for units (`Unit`, `UOM`), because White, Black, Mixed, Chinese, Ng, Ma and Min are also
     surnames or nationalities. A value is matched whole,
     never word by word, so "Female (45)" and "Alice White" are not verified. Under a column
     name that names a person, a role, a relative, a contact or a place (`Referring
     Physician`, `Visit Dr`, `Contact Preference`, `Family History`, `Visit Location`), only the
     missing-value words count, because White, Black and other vocabulary words are also
     surnames. A column of single letters must take them all from one group (M and F, Y and N,
     L, R and B, H, L and N, S, I and R), because a few initials span several groups;
   - (d) a date, which step 3 reduces to the year (a year 90 or more years before the
     reference year becomes `[90_OR_OLDER]` in every date column, whatever its name, because as
     a birth year it reveals an age over 89), or, under a state or country column, a US state,
     territory or postal code, a Canadian province, an Australian state, or a country name or
     ISO code.
   Every other text column is **text the script cannot verify**. It is redacted, and the plan
   lists it as needing the person's decision ("text the script cannot verify is free of
   identifiers; keep with --keep COLUMN once the person confirms it"), with the number columns
   of step 4 and the columns of step 6. The finding counts
   its values and says how many are shaped like names or places, or written in a script
   without capital letters, so the person can tell a column of names from a column of
   diagnoses; the script prints no value.
6. **Columns the scanner cannot vouch for** for other reasons are redacted or pseudonymized
   unless the person keeps them with `--keep`, and are listed for the person's decision too:
   some cells hold identifier patterns, the values have one of the number shapes of step 4, or
   the column has a name of step 2. **Free text**
   (a value of 5 or more words or over 50 characters that is not made of category words, or a
   long run of a script without capital letters) can never be kept, because a name inside a
   sentence has no pattern to find.

   **`--keep` fails closed too** (round 4). It keeps a column of step 5 or 6 on the person's word
   only when every word of the column name is a column word the script knows (step 0's words,
   whether or not they are also surnames), so a name in a language or an abbreviation the lists do
   not know (`Pai`, `Mae`, `Elternteil`, `父`, `Mom`, `ICE`, `Pacjent`) cannot be kept. The name's
   last word, passed over possessives, numbers and words such as `Info`, `Details`, `Other` or
   `Primary`, must not name someone other than a clinician or a member of staff (the person, a
   relative, a member of the household, a contact, a witness, a proxy, a guarantor, a customer, a
   student, a teacher, a lawyer, a pastor: `Twin`, `Emergency`, `Witness`, `Customer`, `Paciente`,
   `Co-signer`, `Responsible Party`), unless every value is a number or a code (`Subject` of
   `S-014`); and must not name an employer, a school, a home, an address, a telephone, an email or
   web address, a device, an image, another name for the person, or notes (`Company`, `School`,
   `Church`, `Home`, `Device`, `Image`, `Face`, `Voice`, `Link`, `Web`, `Notes`, `Comments`,
   `Remarks`, `备注`); `Plate`, `Signature`, `Domain`, `Head`, `Host` and `MAC` count only as the
   whole name. A clinician's or a member of staff's column (`Physician`, `Nurse`, `Pharmacist`,
   `Referral`) and a place of care (`Hospital`, `Clinic`, `Site`, `Ward`, `Unit`) can still be kept.
   The plan lists the columns `--keep` refuses as ones that cannot be kept under their names, not
   among those needing the person's decision, and the report names them in
   `columns_that_cannot_be_kept` with the reason; the person renames such a column if its name is
   wrong.
7. **Kept columns are scrubbed**: each identifier pattern inside a cell is replaced with a
   placeholder such as `[PHONE]`, and a full date becomes its year. A whole value of a code
   grammar keeps the shape the generic code rule would replace (`S72001A` under a diagnosis
   column, `C10AA05` under a drug column); every other pattern is still replaced. The report
   lists the kept text columns (`kept_text_columns`, each marked `verified` or kept on
   request). A column the person kept with `--keep` over any finding, text or numbers (record
   numbers, ZIP codes, coordinates, old years, possible ages), is scrubbed for patterns only: a
   name, a place, a record number or another identifier with no pattern stays in it. The run
   prints these columns again ("Kept on the person's word, scrubbed for patterns only") and not
   among the columns whose identifier patterns are replaced, the report marks them
   `verified: false` and lists them in `kept_unverified_columns` with the finding they were
   kept over and a note that says so, and the person must spot-check each one. `--keep` on a
   column the run keeps anyway records it as kept on request. In a column treated as an age,
   a value that is not an age (a name, a place) becomes `[REDACTED]`.
8. **Residual check.** The output is scanned again before it is written. Every kept column
   is scanned for identifier patterns. A column kept by default is also checked by the
   number shapes of step 4 (numeric days and months and abbreviated coordinates included)
   and verified again by step 5. Every date column is checked for a
   year 90 or more years ago, and every age column for an age over 89 and for text that is not
   an age. A column the person named with `--keep` is trusted for those shapes (names, places,
   numbers), never for patterns. If
   anything remains, nothing is written and the run exits with 3. `verify` without the run's
   report cannot know which columns the person kept, so their text fails as text it cannot
   verify. Passing it means no pattern or shape was found; it is not proof that the output
   is de-identified.

## The 18 identifiers

| # | Identifier | What the script does | What a person still checks |
|---|---|---|---|
| A | Names | Patient name columns, and columns named for the person (`participant`, `proband`, `first`, `fname`, `nm`, `姓名`, `이름`, and `subject`, `member` or `donor` holding words), become pseudonyms (`P0001`, the same person keeps the same one); names of relatives, household members, contacts (`Next Kin`, `Contact Person`, `Landlord`, `Lives With`), employers, schools, clinicians and other roles become `[REDACTED]`, and a relative's, contact's or the person's own name column cannot be kept unless every value is a category word or a number. Every other text column is kept only when every value is verified (step 5), so a name in any form is redacted by default whatever the column is called: with a qualifier (`Nakamura, Alice (wife)`, `Alice Nakamura - RN`), in lower case, as initials, a surname alone, or in a script without capital letters (Chinese, Japanese, Korean, Arabic, Hebrew, Hindi, Thai). Titled or labelled names in kept text (`Dr. X`, `Patient: X`, `Patient Name: X`, also `Dr. 박지훈` and `Patient: 林子涵`) become `[NAME]`. A name read from a first row of data as a column name (a surname alone, a titled name, a name in any script) is withheld from the plan, the report and the output (step 0). `--keep` is refused for a column whose name has a word the script does not know or names the person, a relative, a contact or another person in the person's life, in any language (`Pai`, `Mom`, `ICE`, `Twin`, `Witness`, `Paciente`), and AKA, pseudonym, kana and pinyin columns are names (step 6) | Names with no title or label in a column the person kept with `--keep` (`kept_unverified_columns`), which is scrubbed for patterns only, including a clinician's or another role's column kept on the person's word; a vocabulary word that is also a surname (White, Black) under a race column; a column name that carries a name in an ordinary shape |
| B | Geography smaller than a state | Street, city, county, hometown, suburb, locality, district, precinct, census, coordinate, place-of-birth and `Lives In` columns (also `ciudad`, `municipio`, `ville`, `stadt`, `出生地`, ...) become `[REDACTED]`, and `region`, `home` and `place` columns unless the person keeps them. A town under any other column name is text the script cannot verify, redacted by default (`Visit Location`, `Service Area`, `Cohort`, `Col3`). State and country columns are kept, as Safe Harbor allows, when every value is a state, territory, province or country name or code; a county or a town in one makes the column text the script cannot verify. ZIP columns keep the first three digits, or `000` for the 17 prefixes of 20,000 people or fewer (HHS list, 2000 Census). Columns of mostly five-digit numbers, of four-digit ZIP codes that lost their leading zero, adjacent latitude and longitude columns, a latitude or a longitude on its own (one cell of four or more decimal places, or numbers in range under `Lat`, `Lon`, `Lng` or `Coord`), and grid coordinates in metres (`552345.12`) are redacted or pseudonymized by shape unless the column name names a measurement; postal code, coordinate and street address column names in other languages and scripts (`PLZ`, `CEP`, `Breitengrad`, `纬度`, `Adresse`, `Calle`, `住所`) are identifiers by name, and a column name carrying a ZIP code or a coordinate (`Weight 94110`, `Weight 37.7749`) is refused. Street addresses, PO boxes, ZIP+4, "City, ST", labelled coordinates, degrees with N/S/E/W and precise "lat, lon" pairs in kept text are replaced | A bare five-digit ZIP inside kept text; a ZIP column under a column name that names a measurement; a lone coordinate of three decimal places or fewer under a neutral name; towns in a column the person kept; the ZIP list against current Census data |
| C | Dates and ages over 89 | Date columns keep the year only, and so does a column of a year and a month with no day under any name (`2021-03`, `2021/03`, `2021-3`, `2021 Mar`, `202103`, `2021.03`); a date with no four-digit year, or text that is not a missing-value word such as "unknown", becomes `[DATE]`. A year 90 or more years before the reference year becomes `[90_OR_OLDER]` in every date column, whatever its name (`DoB`, `Geburtsdatum`, `出生日期`, `Event Date`, `Col5`), because as a birth year it reveals an age over 89, and so does such a year in unnamed columns of years. A month and a day written as a number with no separator (`0314`, `03142021`, `910314`, `3262017`), an Excel date serial (`44269.4375`, also under `Visit Day`, `Event Time` or `LOS`), and a day of the month, a month or a weekday written as a whole number under a column name for it in any language (`Admit Day`, `Discharge Month`, `MM`, `Mois`, `入院月`, `Weekday`) or in a short column beside its year (`Admit M`, `Admit D`), make a column `[REDACTED]`; so does a month or a day in a column of its own under any name (`Mnth`, `DoM`, `Tg`, `SM`, `Gün`, `Col2`), found by its numbers (step 4), and a day or a week of the year by name. Age columns over 89 become `90+`, also under age names in other languages, with any qualifier and in compounds (`Edad`, `Alter bei Diagnose`, `Patientenalter`, `Idade`, `年龄`, `年纪`, `年齢`, `나이`, `연세`, `Возраст`, `العمر`, `বয়স`), and under `Years Old` or `Months Old` (ages in days, weeks, months or hours are converted first, ages in words such as "ninety-two" count, and text that is not an age becomes `[REDACTED]`); a whole number from 90 to 125 in any cell, under any column name that names no measurement, groups the column the same way whatever else it holds (`ETA`, `Value`, beside a decimal or `<1`), and so do numbers with a unit of time (`95 y`, `1140 mo`, and in other languages `94 ans`, `95 años`, `95岁`, `95세`); `Kor`, `Vanus`, `Amžius` and `Vecums` are age names; an age group above 89 becomes `90+`, and one that straddles 90 ("85-94") becomes `[REDACTED]`. Dates in kept text become the year, including a year and a month (`seen on 2021-03`) and a date with a month name in French, German, Spanish, Italian, Portuguese or Dutch and a four-digit year (`14 mars 2021`, `14. März 2021`); a day and a month with no year after a word such as seen, on or dated (`seen 14/3`, `on 03-14`, `seen 14.3.`) become `[DATE]`; a year after "born", "DOB" or "year of birth" of someone 90 or over becomes `[90_OR_OLDER]`; "92 years old", "92 y/o", "95 y" and "ninety-three yo" become "90+ years"; a full date 90 or more years ago becomes `[90_OR_OLDER]`; "a 92F", "pt is 91" and "in her 90s" become 90+, and "nonagenarian" `[90_OR_OLDER]` | Other dates that reveal an age over 89 (a death date next to an age); ages over 89 written as decimals under a neutral column name (`Value`, `Result`), or under a column name that names a measurement; a month or a day in a column of its own that covers fewer than seven months or thirteen days in a file with no column of years, or under a column name that names a measurement; in kept text, a day and a month with no year and no such word before it (`14/3`), a month name in another language with no year, and a year and a month that read as a season or school year (`2011-12` is left alone, because `2010-11` is usually a flu season; a column of months is still reduced as a whole) |
| D | Telephone numbers | Phone columns, also in other languages (`Telefon`, `Teléfono`, `Celular`), become `[REDACTED]`; a phone number that Excel wrote with an exponent (`4.15555E+09`) is pseudonymized under a column name that names no measurement; numbers in kept text, including a cell that is only an international number (`+14155550134`), become `[PHONE]` | Local seven-digit numbers with no label |
| E | Fax numbers | As telephone numbers | |
| F | Email addresses | Redacted | |
| G | Social security numbers | Redacted (and national ID numbers of the chosen locale pack) | |
| H | Medical record numbers | Become pseudonyms (`ID0001`), so rows of one patient stay linked, whether the column is named for them or not: a whole number of four or more digits in any cell, in any written form and also with an exponent (`4.52783E+06`), makes a column under a column name that names no measurement pseudonymized (`Chart`, `Hosp No`, `Patid`, `病历号`, `Col6`, a `Value` column of a long export); a column named with a word for number or record in any language (`Pat No`, `Hospital No`, `Patientennummer`, `Prontuário`, `病历号`, `등록번호`) holding numbers of four or more digits or codes is a record number by name and cannot be kept, and short numbers under such a name (`Study ID` of 1 to 30) are pseudonymized; repeated numbers of seven or more digits are pseudonymized even under a measurement name; labelled numbers in kept text (`MRN 1234`, `MR# 1234`, `ID 1234`, `#A-998`) become `[ID]`; a column name holding a number of five or more digits (`Patient 3767393`) is refused | A record number of three digits or fewer under a column name that names no record; a record number of four to six digits, or one that does not repeat, under a column name that names a measurement (`Steps`, `Total Cost`, `Count`), also written with an exponent; a record number of four digits or fewer in a column name |
| I | Health plan beneficiary numbers | Member, policy, subscriber, Medicare and Medicaid columns redacted; Medicare MBI-shaped values in text replaced. A payer or type column (`insurance`, `insurance_type`, `medicare_status`) of category words such as Medicare or Commercial is not an identifier by name: Yes and No in it are kept, and other words are redacted as text the script cannot verify until the person keeps the column | |
| J | Account numbers | Account, card and IBAN columns redacted; grouped card numbers and valid IBANs in text replaced | |
| K | Certificate and licence numbers | Licence, certificate, DEA, NPI and passport columns redacted; labelled numbers in text replaced | |
| L | Vehicle identifiers and plates | VIN and plate columns redacted; 17-character VINs and labelled plates in text replaced | Unlabelled plate numbers in text |
| M | Device identifiers and serial numbers | Device ID, serial, UDI and IMEI columns redacted; MAC addresses, GS1 UDIs and labelled serials in text (`serial 8841`, `S/N 8841`, `SN 8841-2290`) replaced | |
| N | Web URLs | Redacted, and so are columns named for a social network (`Twitter`, `Instagram`, `TikTok`) unless every value is a category word. In kept text: addresses with a scheme or `www.`, a host and a path with neither (`fb.me/jane.doe`), bare domains ending in .com, .org, .net, .edu, .gov, .io, .info or .biz, social media handles (`@jane_doe`, `Facebook /jane.doe`, `Instagram: jdoe`, `skype:jdoe`, `on Instagram as jdoe99`, `u/jdoe`, `jdoe#1234`) and logins written `user@host` | Bare domains on other endings; a handle written with no `@`, no network name and no dot, digit or underscore, or with letters only after a network name and no colon |
| O | IP addresses | Redacted, by column name or by values (IPv4 and IPv6) | |
| P | Biometric identifiers | Fingerprint, voiceprint, retina, iris and face-template columns redacted; long hex or base64 blobs in text replaced | Biometrics stored in another form |
| Q | Full-face photographs | Photo and image columns redacted; image file names and `data:image` values in text replaced | Images themselves (DICOM and photo files are out of scope) |
| R | Any other unique identifying number or code | Unique numbers, and whole numbers of four or more digits under a column name that names no measurement, are pseudonymized; text codes that no closed grammar verifies are redacted until the person keeps them; in kept text, numbers of nine or more digits (also written `274,365,867`) and codes with four or more digits and a letter become `[ID]` (dbSNP, Ensembl and RefSeq identifiers, and whole values of a code grammar, are left alone) | Rare combinations of values (quasi-identifiers), small cells; a number column kept on the person's word |

## What the script does not do

- It does not assess rare combinations (age, sex, ZIP prefix and admission year together
  can single out a person), small cells or rare diagnoses. No k-anonymity check is run.
- It reads only the first sheet of an Excel file; the other sheets are not written, and no
  sheet name is printed or kept (a workbook with one sheet per patient names them). The output
  workbook is written new from the first sheet's cell values, so comments, document properties
  and hidden sheets are not copied. The workbook reader was tested with a stand-in for
  openpyxl, which was not installed where the tests ran, not with openpyxl itself.
- It does not look inside images, DICOM headers or other attached files.
- It cannot find identifiers written in ordinary column names or in the file name. A column
  name is copied to the output only when every word in it is a column word (step 0); any other
  name is withheld as `#N (name withheld)` and written as `column_N` until the person confirms
  it. A surname that is also an ordinary column word (`Price`, `Ward`, `Long`) is shown when
  another column word stands beside it (`Price (USD)`); alone, of 1,161 common US surnames and
  given names tested, only `Case`, `Day`, `Person` and `Weeks` are shown. A column word that
  is an eponym of a score (`Charlson`, `Glasgow`, `Barthel`) is shown alone. A first row with an identifier
  pattern in any cell (an email, a phone or ID number, a date, a number of five or more digits, a
  decimal of four or more places, a year 90 or more years ago) is refused, and so is one in
  which a third of the cells look like values or names. A number of four digits or fewer in a
  column name is shown (`Patient 4527`), so a short record number written into a column name is
  not found; nor is an identifier written as an ordinary word.
- In a file with no header row, read without `--no-header`, the first row is lost from the
  output (its cells become withheld column names). The skill asks the person whether the first
  row holds column names before it runs.
- It reads CSV and TSV files in UTF-8, with or without a byte order mark, and UTF-16 or
  UTF-32 with one. Any other file (a Windows-1252 or Latin-1 export, Excel's plain "CSV" save)
  is refused with the remedy: save it as "CSV UTF-8", or rerun with `--encoding` (`cp1252`,
  `latin-1`, `utf-16-le`, `euc-kr`, ...). It does not guess an 8-bit encoding, because a wrong
  guess turns names into other text silently. The output is always UTF-8.
- It refuses a file that uses `;`, `|` or tabs in a `.csv` file as its separator unless
  `--delimiter` names it, because each row would be read as one text value; the output uses
  the same separator, and `verify` reads it from the report. A number written with a decimal
  comma (`5,1`), as such files often hold, is not read as a number: its column is text the
  script cannot verify, redacted until the person keeps it.
- Header names it shows are its only view of the file; a header with a word it does not know,
  or that looks like a value, is shown as `#N (name withheld)`, and a file whose first row looks
  like data is refused.
- The number shapes of step 4 and the column names of step 2 are guesses, and they err
  towards redaction. A pair of score columns can read as coordinates, a column of decimals of
  four places under a neutral name (`Value`, `X`) as a latitude, a column of measurements under
  a column name that names no measurement (`Value`, `Col5`) as record numbers as soon as one cell
  has four digits, a glucose or an oxygen saturation under `Result` as ages as soon as one cell is
  from 90 to 125, a protocol day under `Visit Day` as a day of the month, and a column of
  four-digit codes with a leading zero as dates. Since round 4, a column of whole numbers from 1 to
  12 or 1 to 31 that covers most months or days (a visit number of 1 to 12, a cycle) is read as a
  month or a day under any name that names no measurement, and so is every column of whole
  numbers from 1 to 31 that is not only 1 and 2 in a file with a column of years (a coded race,
  a birth order, a Likert item), and short numbers under `Study ID`, `Case` or `Key` as study
  numbers. The plan lists them, and the person keeps them with `--keep` once they confirm. The
  other way round, a record number of three digits or fewer under a column name that names no
  record, or one of four to six digits, or of seven or more that does not repeat, under a column
  name that names a measurement (`Steps`, `Total Cost`, also written with an exponent under
  `Count` or `Total`), is kept, and so is a date written as three digits (`314`). A month or a
  day in a column of its own that covers fewer than seven months or thirteen days is kept in a
  file with no column of years, as in a small file or one whose years are only inside full dates,
  and so is one under a column name that names a measurement (`Score` of 1 to 12) or a stage, a
  grade or a class. A day or a week of the year is found only by its column name.
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
- A few vocabulary words are also surnames (White and Black under a race column; Victoria,
  Georgia, Jordan and Chad under a state or country column) and are kept under such a column
  name, which matters only when every value of the column is one of them. The same holds for
  a column whose every value is one vocabulary word that is also a surname (`Si` for yes,
  `Quit`, `Final`, `MR` for a minor response). A column of single letters is kept only when
  they all come from one group (M and F, H, L and N, ...), so first initials from one group
  pass.
- `--keep` is accepted on a column named for a clinician or a member of staff (`Physician`,
  `Provider`, `Referring Physician`, `Nurse`, `Pharmacist`), a place of care (`Hospital`,
  `Clinic`, `Site`, `Ward`, `Unit`, `Department`), an organisation that is not an employer, and
  a payer column: their values are not a closed list. Kept on the person's word, such a column is
  scrubbed for patterns only and named in `kept_unverified_columns`. Since round 4 `--keep` is
  refused for any other column whose name has a word the script does not know, so a person whose
  column names are in a language the lists do not cover renames the columns they want to keep;
  and for a column named for the person, a relative, an employer, a school, a home, an address, a
  device, an image or notes. Its word lists of people and things are still lists: a column named
  for a person with an ordinary column word that the lists do not read as a person can be kept.
- Its network guard replaces Python's usual socket functions; it is not a sandbox. Run it
  under an operating-system sandbox with networking denied when that must be guaranteed.
