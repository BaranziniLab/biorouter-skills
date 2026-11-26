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

A fifth review round found that the class still open was numbers and column names, where the script
still decided by shape, and each gap was a shape the rules had listed too narrowly. A week of the
year (1 to 53) or a day of the year (1 to 366) beside a year was kept under every name but a few
full phrases, because only numbers from 1 to 31 counted; now any column of whole numbers that fits
the range of a date part is redacted in a file with a year, and a date column counts as a year,
because the output keeps it (step 4). A record number written into a column name in groups (`Patient
376 7393`, `Pt 37_67_393`) and a date with a two-digit year or a month and a day (`Mar-19`, `Sep12`,
`03/14`, `Q1 20`) were shown; now the digits of a column name are counted after its separators are
removed, and any date element finer than the year in it is refused (step 0). Code grammars with an
open part let a record number with a prefix pass as a code under any column name (`RS1234567`,
`NM_1234567`, `H8Q.600`, `E456.8`); now only the exact published shapes count (step 5). And `--keep`
was accepted under any role word that was not a relative (`Who`, `Case`, `Reporter`, `Author`,
`Manager`, `Agent`, `Rep`, `Kind`); now it is accepted under a word for a person only for clinical
and care staff (step 6).

A sixth review round found the same two places still decided by shape, in four forms. `--keep`
refused a word for a person only as the last word of a column name, so a compound or an
abbreviation of a name of the person or a relative was kept on the person's word (`Patient Last`,
`Mother First`, `Spouse Last`, `Kin Last`, `MotherLast`, `pat_last`, `Pat Info`, `PatNm`, `LNm`,
`Donor_Nm`, `In-law`: 604 spellings in one sweep); now the refusal is decided on the set of the
name's words, so a word for someone anywhere in the name refuses `--keep` when another word names a
name or a part of one, or when no other word says what the column holds (step 6). Geocodes of two
or three decimal places (a kilometre and a hundred metres) passed as measurements under neutral and
axis-like names (`Value`, `X`, `Y`, `Loc X`, `Pos`, `Point`, `Geo1`, `Index`); now such a column is
a possible coordinate under any name that names no measurement (step 4). `--keep` kept numbers of
five or more digits under names that are health or record numbers the lists did not know (`PHN`,
`NHS`, `NIP`, `Patid`, `Pat#`, `Patient Ref`) and under any other name; now those names are record
numbers by name, and numbers of five or more digits are kept on the person's word only under a
name that names a measurement or the number of a thing (step 6), because a person who confirms that
a column holds no record numbers cannot be relied on to know that `NHS` names one. And places that
are not places of care (`Home Area`, `Lives`, `Catchment Area`, `Ort`) could be kept; now they
cannot hold words that can be names (step 6).

A seventh review round found the class still open in numbers under neutral names, where the script
still decided by shape: one-decimal coordinate pairs (a point to about ten kilometres), decimal years
(`2018.07`, a year and a week or a day, a decimal birth year of someone over 89), Unix timestamps
with fractional seconds and record numbers passed as verified measurements under `Value`, `Result`,
`Col3`, `X`, `Y` and similar names. Since then numbers fail closed by NAME, as text does: a column of
numbers is kept by default only when its column name names a measurement and its numbers pass the
identifier and date checks of step 4; any other column of numbers goes to the person's decision, and
the plan says the script cannot verify that its numbers are not identifiers, dates or coordinates.
Dates written as numbers (a decimal whose whole part is a calendar year, a Unix timestamp of 10 or 13
digits, a Julian date of 7 digits) are dates under any name. A header cell holding a NUL, a control
character or a format character is refused by its position, and a file whose first bytes hold a NUL
is read as UTF-16 without a byte order mark and refused with the remedy. The cost is over-redaction
of ordinary numbers under neutral names (`Value` of a long lab table, `Visit Number`, a sex or a
Likert item coded as a number), which the person undoes with `--keep`, also for a range of
positions.

An eighth review round found column names that held a full date written in Chinese, Japanese,
Korean, Vietnamese or Malay (`2019年3月14日`, `2019년 3월 14일`, `14 tháng 3 năm 2019`, `14 Mac 2019`,
`R1.5.1`) copied verbatim to the output: the column-name check read `年`, `月` and `日` as column
words, and the date patterns read only Latin month names and ASCII digits. The same dates in cells
were redacted only because unverified text is (step 5). Since then cells and column names share one
definition of a date. The text is folded first (compatibility forms such as full-width digits and
`㋿`, every script's decimal digits as ASCII, the accents and vowel marks of Latin, Greek, Cyrillic,
Arabic and Hebrew letters dropped), and one set of grammars reads it: year, month and day markers
(`年 月 日 号`, `년 월 일`), Japanese eras (`令和1年5月1日`, `令和元年`, `R1.5.1`, `H31.4.30`, `㍻`),
Vietnamese `tháng` and `năm`, Chinese numerals (`二〇一九年三月十四日`), month names of 25 languages in
nine scripts beside a day or a year (`14 Mac 2019`, `14 марта 2019`, `14 במרץ 2019`, `14 มีนาคม 2562`),
and numeric dates of three parts in any calendar (`2562-03-14`, `1398/12/23`, `2019. 3. 14.`). In kept
text each date of two or more elements becomes its Gregorian year (Buddhist and Japanese-era years
converted, a year 90 or more years ago `[90_OR_OLDER]`) or `[DATE]`, and a date column reads those
years too. A column name holding one is refused; one holding a month or a day alone, or numbers that
may be a month and a day, is withheld (step 0). The grammars were proved with a generated sweep of
dates in these scripts and calendars in many contexts, not with the strings the review listed. The
cost is over-redaction of a few ordinary column names (`pH 7.4`, `HbA1c 6.5`, `30日死亡率`), which the
person confirms with `--keep-name`.

## How a column name is shown

0. **Column names.** The first row is the header row unless the person says the file has none
   (`--no-header`, which reads every row as data and names the columns `column_1`,
   `column_2`, ...). A header cell is shown in the plan and the report and copied to the output
   only when every word in it is a word column names are made of: the words the rules below
   read, the category, medical and anatomical words of step 5, a list of ordinary column words
   (in several languages, and common words of other scripts such as `性别`, `진단`, `Диагноз`),
   single letters, short numbers, and codes of letters and digits (`TP53`, `Col1`, `Q3`, `2nd`,
   `ENSG00000141510`). A number in a column name is not a column word the way a value is verified:
   a run of five or more digits (`Patient 3767393`, `Weight 94110`, `4,527,832`, `376-7393`), and
   since round 5 the digits of numbers joined by any separator that is not a letter or a digit,
   counted together after the separators are removed (`Patient 376 7393`, `Pt 37 67 393`,
   `Patient 37_67_393`, `ID 12 34 56 78`, `Weight 12 345`, `Patient 376:7393`), a decimal of four
   or more places (`Weight 37.7749`), a year 90 or more years before the reference year (`Cohort
   1925`), and a date element finer than the year (round 5) make the first row refused, like an
   identifier pattern, and `--keep-all-names` does not override it: the person renames those
   columns. A run of digits that is only years (`2019-2020`), a decimal or a range of two decimals
   with up to three digits before the point (`37.775`, `18.5-24.9`), or two whole numbers joined by
   a hyphen or a slash alone with fewer than six digits (`70-100`, `120/80`) is not counted, and a
   number that starts after a Latin letter belongs to its word (`HbA1c 2021`, `CD4 2020`). A date
   element is a month name or abbreviation in English, Spanish, French, German or Italian beside a
   number of one, two or four digits in either order (`Mar-19`, `Jan 20`, `WBC Feb-20`, `19-Mar`,
   `Visit Sep.12`); a month and a day written as numbers with a leading zero, a year or a day over
   12 beside a slash (`03/14`, `3-14-21`, `3/14`, `14/3`, `14.3.`); a quarter beside a year (`Q1 20`,
   `Q2 of 2020`, `2020Q1`, `1st Quarter 2020`); and a week beside a four-digit year (`W12 2020`,
   `Week 12 2020`, `2020-W12`). Since round 8 a date element is also any date of two or more elements
   that the date grammars read in cells (see the design above: `2019年3月14日`, `3月14日`, `2019년 3월`,
   `14 tháng 3 năm 2019`, `14 Mac 2019`, `Ogos 2019`, `R1.5.1`, `令和元年5月1日`, `14 มีนาคม 2562`,
   `١٤/٣/٢٠١٩`), and a month and a day written as two numbers joined by a hyphen, a slash or a dash
   in which one number is from 13 to 31 and the other from 1 to 12 (`31-12`, `12-31`, `14-3`, `9-19`,
   `WBC 3-19`) or one has a leading zero (`03-14`, `WBC 0314`); beside a word that takes a range or a
   scale (`Age 12-18`, `Weeks 3-19`) a hyphenated pair is a range and is shown. A month or a day
   alone (`3月`, `3월`, `tháng 3`, `三月`, `14日`, `14일`, a month name of another language as a word of
   its own, `Ogos`, `Desember`), a word for a day and one for a month with numbers (`Day 14 Month 3`,
   `Tag 14 Monat 3`), two numbers of 12 or less joined by a hyphen or a slash (`WBC 3-4`, `3/4`), a
   decimal that reads as a day and a month (`WBC 14.3`, `WBC 3.19`) and four digits that read as one
   with no leading zero (`WBC 1231`) are withheld; such numbers are shown beside a word that takes a
   range or a scale (`Grade 3/4`, `Score 1-10`, `Age 5-12`, `ECOG 0-1`), after a comparator (`Hb <
   13.5`) or before a unit (`Dose 2.5 mg`, `Duration 3-4 days`), and a cancer antigen (`CA 19-9`, `CA
   15-3`) is a lab name. A number of months or days (`3个月`, `3ヶ月`, `3개월`, `3 tháng`, `7日間`,
   `第14天`) and a study day in a language with spaces (`Day 14`, `Jour 14`) are not date elements. A
   month abbreviation joined to one or two digits with no separator is
   also the shape of a gene symbol (`OCT4`, `Oct4`, `SEPT9`, `DEC1`), so that cell is withheld rather
   than refused, and so are `Mar19`, `Sep12` and a month name as a word of its own (`Weight March`,
   `June Visit`), the month of each person's measurement in a wide export; the person confirms a
   gene symbol with `--keep-name #N`. A fiscal year (`FY2022 Cost`) is a year. A public accession
   (`GSM1234567`, `SRR1234567`, `TCGA-02-0001`, `ILMN_1234567`, `cg12345678`, `LOC100132062`, `CHEMBL123456`, `GO:0008150`,
   `HMDB0000001`, `C00031`, `P04637`, `R-HSA-109582`, `PRJNA123456`, `NCT01234567`) is refused like a
   record number, because `C00031` or `P04637` can also be a patient's code, unless the person
   confirms that column by its position with `--keep-name #N`; `--keep-all-names` does not. The
   digits of a closed code are not counted (Ensembl, RefSeq, rsID, a genomic position after
   `chr`). A first-row cell of a few letters and digits with a leading zero, or of letters the column words do not
   know and three or more digits (`S001`, `sub01`, `PT-0042`, `ABC123`), is withheld as a value.
   At least one word must not also be a common surname or given name: `Reference Low` is shown,
   `Low`, `Ward`, `White` and `Rose Hall` alone are not; since round 8 neither is a word for a person
   (`Patient`, `Dr`, `Mother`, `Nurse`, `Subject`) beside words that can be surnames (`Patient White`,
   `Dr Ward`, `Patient Bill White`, `Ward Nurse`), nor two words that can be names side by side
   (`Weight Bill White`) unless one is a measurement or an ordinary column word (`Temp Min Max`) or a
   point of the compass, and since round 5 neither are short
   surnames and given names that are also column words (`Das`, `Fu`, `Lo`, `Kin`, `Son`, `Max`,
   `Pat`, `Tod`, `Sin`, `Spring`, `Hay`, `Best`) unless another column word stands beside them
   (`Max Temp`, `Pat No`, `Best Response`). Any other cell is withheld as `#N (name
   withheld)` and the output names the column `column_N`, until the person confirms it with
   `--keep-name #N` (or `--keep-all-names` for the whole first row). A first row with an
   identifier pattern in any cell is refused, and so is one in which a third of the cells look
   like values or names, unless the person confirms it; two cells with the same name are refused
   by position, without printing them, unless the person confirms that the first row holds column
   names and the agent reruns with `--number-duplicates` (round 8), which gives each repeated name its
   position (`Glucose_7`). The rules below read the real column name whether it is
   shown or not. Since round 7 a header cell holding a NUL, another control character or a format
   character (Unicode Cc or Cf: a zero-width space, joiner or non-joiner, a word joiner, a direction
   mark or override, a soft hyphen, a byte order mark inside the text) is refused, naming only its
   position, whatever the person confirms, because such characters split a name into letters each of
   which is a column word; a tab, a line feed and a carriage return read as spaces, and the plan
   shows such a name on one line. Since round 8 a zero-width joiner or non-joiner and a direction mark
   (`U+200C`, `U+200D`, `U+200E`, `U+200F`, `U+061C`) are accepted in a header cell with no letter of a
   script with capital letters, where the spelling needs them (Persian `شماره‌پرونده`, an Arabic cell
   ending in a right-to-left mark, an Indic conjunct, an emoji sequence), and the checks read the name
   without them; in a name with Latin, Greek or Cyrillic letters they are refused as before, and the
   message names `--no-header`, which reads the first row as data. A word spelled out one letter at a time with one separator between
   letters (`Z-o-r-b-l-e`, `S m i t h`, `J.o.n.e.s`; four letters or more) is withheld as a value.
   `--keep-name` takes a range of positions too (`--keep-name '#2-#501'`), so a wide matrix of public
   accessions can be confirmed in one option.

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
   number of a thing (`Gene ID`, `Lot No`, `Plate No`). Since round 6 the same holds for a health or
   patient number by its abbreviation (`PHN`, `NHS`, `NHI`, `OHIP`, `NIP`, `PRN`, `PID`, `Patid`,
   `Ptid`), for a key, a reference or a token of the patient (`Patient Ref`, `Pat Ref`, `Patient
   Key`, `Pt Token`), and for a name with a number sign after a word (`Pat#`, `Patient #`, `MR#`,
   `Visit #`; `# of Visits` and `# Visits` are counts).

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
4. **By the name and the shape of its numbers.** Numbers fail closed like text, by name since
   round 7, and each cell is judged on its own. A column of numbers is verified only under a column
   name that names a measurement: a lab analyte (`WBC`, `Ferritin`, `Free T4`, `Vitamin B12`,
   `Ki-67`, `CA 19-9`, `IgG`), a vital sign, a count such as `Steps` or `Number of Visits`, a score or
   a scale (`Pain Score`, `ECOG`, `NYHA`, `Gleason`, `MoCA`, `mRS`, `Apgar`, a stage or a grade), a
   dose, a unit such as `(mg/dL)` or `%`, money, a duration, a statistic (`P Value`, `FDR`,
   `Log2FC`, `Mean`, `Median`), a propensity or a z-score, with no word that says identifier (`Lab
   No`, `Sample ID`) and no last word that names what a row is about (`Glucose Case`, `Count
   Patient`, `Dose Encounter`, but `Cost per Case` is a measurement); or written with a unit of
   measurement in its cell (`5.2 mg/dL`, `12%`); or, for a column of four-digit years, or of numbers
   up to 99 under a word for a year, under a name for a year or a date (`Year`, `Admit Year`, `Dx
   Yr`, `YYYY`, `Jahr`, `Years`). Every number must also read as a measurement by the checks below.
   A column of numbers under any other name (`Value`, `Result`, `Col3`, `X`, `Y`, `Index`, `Point`,
   `Pos`, `Geo1`, `Measure1`, `Entry`, `Seen`, `Event`, `Period`, `Visit Number`, a gene symbol) is
   redacted and listed for the person's decision: the script cannot verify that its numbers are not
   identifiers, dates or coordinates (round 7), and when one of the shapes below fits, the plan gives
   that reason. The checks:
   - since round 7, dates written as numbers under any column name: a decimal whose whole part is a
     year from 1850 to five years after the reference year (`2021.07`, `2021.3`, a year and a week or
     a day, `2021.123`, a decimal birth year, `1926.164`, a year and a month and a day, `1931.0314`), a
     number of 10 or 13 digits before its point that is a Unix timestamp in seconds or milliseconds
     within those years, also negative or with fractional seconds (`1629478800.373`,
     `-1204783199.85`), and a number of 7 digits that is a Julian day number or a year and a day of
     the year (`2459215.5`, `2021123`; whole ones of seven digits only under a name that names a
     measurement, since under any other name the record number rule pseudonymizes them). A column of
     nothing else keeps only the year, read from the number (a year 90 or more years ago becomes
     `[90_OR_OLDER]`); a column that mixes them with other numbers is redacted; under a column name
     that names a measurement they must be most of its numbers, so one cost of `1999.99` or one viral
     load of `2450000` does not make a column of measurements a date;
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
     4), and since round 7 a code, a label, a token or a sequence of the person, the record, a
     proband, a family or a study (`Pt Code`, `Case Code`, `Participant Label`, `Subject Token`,
     `Patient Seq`, `Family Number`, `Research Number`); `Visit No` and `Cycle Number` are sequences,
     redacted by their names since round 7, and `Number of Visits` is a count;
   - whole numbers of seven or more digits that repeat more often than they differ, even under a
     column name that names a measurement (`Score`, `Count`, `Level`, `Total`, `Weight`,
     `Amount`, `Dose`), and since round 6 of six or more digits under a count of a patient's visits,
     encounters, admissions, episodes or appointments (`Visits`, `Encounters`, `Admissions`), which
     never reaches six digits: record numbers, pseudonymized (round 4), and since round 5 in any written
     form, signed, with a trailing point, with a fraction or with an exponent of five or more
     significant digits (`-4527832`, `4527832.`, `4527832.5`, `4.527832E+06`; a viral load of
     `1.37E+06` is a measurement). A measurement name whose last word names a claim, a
     policy, an invoice, an account, a plan, a bill, a visit, an admission or a record (`Cost Claim`,
     `Total Policy`, `Rate Plan`, `Length of Stay Visit`, `Number of Visits Record`) names whose
     number it is, not a measurement (round 5); `Claim Amount`, `Cost per Visit` and `Number of
     Records` are measurements;
   - whole numbers shaped like dates with no separator in an order the rules below do not
     read (`910314` as YYMMDD, `3262017` and `2016112` with a one-digit month or day), and
     numbers shaped like Excel date and time serials (`44269.4375`): possible dates, redacted.
     The serial check runs under any column name but one that names a measurement other than
     time; under a day, a week, a month, a duration or a bare time (`Visit Day`, `Days`, `LOS`,
     `Event Time`) a whole number from 10000 up counts too, because such a duration is not
     plausible, and since round 7 any number of five digits before its point, whole or not, also
     beyond the last Excel serial; minutes, seconds and hours are left alone;
   - a whole number from 90 to 125 in any cell (or a number with a unit of time, `95 y`,
     `1140 mo`, `1,100 months`), under a column name that names no measurement, whatever else the
     column holds (a decimal, `<1`, `130`): possible ages. Under a column name with a word that can
     mean age or old age (`ETA`, `Old`, `Y Old`, `Year`, `Elderly`, `Senior`, `Seniority`), where a
     decimal from 90 to 125 and an age written as older than (`>99`, round 7) count too, or with a
     unit of time in every cell, they are grouped as `90+` and the other ages stay; since round 7,
     under any other name (`Value`, `Result`, `Visit No`) the whole column is redacted, because its
     other numbers are not verified either;
   - a day of the month (1 to 31), a month (1 to 12) or a weekday (0 to 7) written as a whole
     number in every cell, under a column name that says so in any language and with any
     qualifier (`Day`, `Admit Day`, `Day of Month`, `DD`, `Month`, `Discharge Month`, `MM`,
     `Mon`, `Mth`, `Mois`, `Monat`, `Mes`, `Tag`, `Jour`, `入院月`, `日`, `월`, `День`, `Weekday`,
     `Day of Week`), or in a column of one short word beside the year it belongs to (`Admit
     Year`, `Admit M`, `Admit D`; `Y`, `M`, `D`; `Dx Yr`, `Dx Mo`): a date element other than
     the year, redacted. Plural durations (`Days`, `Months`), protocol days past 31 and a column
     name that also names a measurement (`Month 6 Pain Score`, `Day 28 Viral Load`) are left to
     the other checks; a day of the year (`DOY`, `Day of Year`, `Julian Day`, `Día del año`, 1 to
     366) and, since round 5, a week under any word for one in any language and with any qualifier
     (`Week`, `Wk`, `Epi Wk`, `Admit Week`, `MMWR Week`, `Weeknum`, `Semana`, `Woche`, `Semaine`,
     `Settimana`, `Hafta`, `Tydzień`, `Minggu`, `周`, `週`, `주`, `неделя`, 0 to 53, because `%U`
     numbers weeks from 0) are redacted by name too; the plurals (`Weeks`, `Wochen`) are durations,
     as `Days` is, and a protocol week under `Week` (0, 4, 12, 52) is redacted until the person keeps
     it;
   - a month, a day, a week or a day of the year of a date written in a column of its own, whatever
     the column is called (rounds 4 and 5): in a file with a year, that is a column of years
     (four-digit years under any column name that names no measurement or age, or numbers up to 99
     under a word for year) or a date column (whose year the output keeps), every column of whole
     numbers that fits the range of a date part, 1 to 12, 1 to 31, 1 to 53 or 1 to 366, and is not
     only 1 and 2 (a code such as a sex); in any file, whole numbers from 1 to 12 covering seven or
     more of the months, from 1 to 31 covering thirteen or more of the days, from 0 to 53 covering
     27 or more of the weeks, or from 1 to 366 with 100 or more distinct values from 31 or below to
     300 or above: possible date elements other than the year, redacted, and redacted rather than
     grouped as ages (a day of the year under a neutral name used to keep every value under 90). A
     minority of missing-value codes other than 0 (99, 88, -9, ...) does not hide such a column; a 0
     makes it a count beside a year. Only a column name that names a measurement other than a part
     of a date or a time keeps it (`Pain Score`, `Heart Rate`, `Sodium`, `SpO2`, `Days`, `Weeks`,
     `LOS (days)`, `Interval (days)`, `Number of Visits`, `GCS`, `Hemoglobin`), and so do a stage, a
     grade or a class (`Stage`, `Tumor Grade`, `NYHA Class`) and numbers that include 0 (`ECOG`,
     `Comorbidities`). `Week`, `Wk`, `Time`, `Period` and `Interval` alone do not name a measurement
     here. `Tg` and `MM` alone are read as a day and a month, not as triglycerides and millimetres;
   - decimals of three digits and four places from 200 (`555.0134`, the shape of a local telephone
     number) under a column name that names no measurement, redacted (round 5);
   - decimals of four or more places within 180 under a column name that names no measurement,
     judged cell by cell (round 4): one decimal of four or more places from 1 to 180 in any cell is
     a possible latitude or longitude, so a column that mixes precise and rounded coordinates is
     redacted, and so is a column of such decimals that are all below 1; and numbers in range under a column
     name with an abbreviation for one (`Lat`, `Lon`, `Lng`, `Coord`, `Long` beside a place word
     such as `Home` or `Patient`), redacted, which the person can keep because `Lat` also means a
     latency or a lateral view;
   - since round 6, numbers within 180 with two or more decimal places in three quarters of the cells
     or more and one value of 10 or more, under a column name that names no measurement (`Value`, `X`, `Y`,
     `Loc X`, `Pos`, `Position`, `Point`, `Geo1`, `Index`, `Result`, `Col4`): a possible latitude or
     longitude, redacted, since two places locate a point to about a kilometre and three to about a
     hundred metres; and so are negative decimals from -60 to -180 in most cells, with one place or
     more (a longitude in the Americas), and, beside a column found to be a coordinate, a column of
     decimals within 90 under such a name (its latitude, also with one place). A z-score, a
     propensity or another column of decimals all below 10 is not read this way, and a column name
     that names a measurement (`Weight kg`, `BMI`, `Hemoglobin`) keeps its decimals;
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
     column passes 90 with one sign or (round 6) when neither column name names a measurement, and
     a value of 10 or more in one of them: redacted, and reported as a pair;
   - unique numbers of five or more digits under a column name that names no measurement:
     possible record or account numbers, pseudonymized.
   The same checks run on the numbers of a column that mixes numbers with other verified
   values (`<0.5`, `5.2 mg/dL`, `unknown`).
5. **Fail closed: every other value must be verified.** A column that no rule above
   replaced is kept only when every value that is not blank is one of:
   - (a) a number, with an optional comparator and unit (`<0.5`, `>= 10`, `5.2 mg/dL`, `12%`,
     `1,250`), or a blood pressure (`120/80`, the first number larger, so a day and a month
     never pass), when the column's numbers pass step 4, which since round 7 includes its name:
     a bare number under a column name that names no measurement is not verified, also beside
     verified words (`Result` of `Positive` and `12.5`);
   - (b) a code of a closed grammar in its exact published shape (round 5), and nothing else:
     ICD-10-CM in capitals, a letter and two digits (or `C4A`, `C7A`, `C7B`, `D3A`, `M1A`, `O9A`, `Z3A`)
     no later than the last category of its chapter letter (`E89`, `H95`, `K95`, `T88`), with a dot and
     up to four letters or digits after it, one of them a digit (`E11.9`, `S72.001A`, not `E95.1`); since
     round 7 not an `N`, `S`, `T` or `W` code with four digits after the dot, which ICD-10-CM never has
     (the seventh character of an injury code is a letter), and an `N`, `S`, `E` or `W` code with three
     or four digits after the dot (`N37.7749`, the shape of a latitude after its hemisphere letter) only
     under a column name that names a diagnosis, except a diabetes code `E08` to `E13` with four
     (`E11.3211`); ICD-9 `V` codes
     from V01 to V91 and `E` codes from E000 to E030 and E800 to E999, with a dot; LOINC with a valid
     check digit (`2345-7`) under a column name that names a LOINC code, a lab, a test, an
     observation, a component, an analyte, an assay or a panel, because many record numbers carry
     the same mod 10 check digit; ATC; HGVS with a substitution of one base by another (`c.35G>A`,
     `p.V600E`, `NM_004333.6:c.1799T>A`, not `c.35G>G`); an rsID in lower case with no leading zero
     and up to ten digits (`rs113488022`, not `RS1234567`); Ensembl with exactly eleven digits
     (`ENSG00000141510`, `ENST00000269305.4`); RefSeq `NM_`, `NR_`, `XM_`, `XR_`, `NP_`, `XP_`, `NC_`
     and `NG_` with six or nine digits (`NM_004333.6`, not `NM_1234567`);
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
     L, R and B, H, L and N, S, I and R), because a few initials span several groups, and since
     round 7 so must a column of two capital letters verified only as vocabulary words (`CR`, `PR`,
     `SD`, `NE` of response; `HH`, `LL` of result flags; `LT`, `RT` of laterality; `NO`, `SI`, `JA` of
     yes and no; `CA`, `NY` of states under a state column), since `NA`, `SD` or `LT` are also a
     person's initials;
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
   diagnoses; since round 6, when every one of two or more such values is shaped like a name or a
   place, it says the column probably holds names or places. The script prints no value.
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
   `Primary`, must not be a word for a person unless that person is clinical or care staff (round
   5): physicians, doctors, nurses, surgeons, clinicians, providers, attendings, residents, fellows,
   interns, hospitalists, practitioners, specialists, pharmacists, therapists (`Physical
   Therapist`), technicians, technologists and midwives, their common abbreviations (`Dr`, `MD`,
   `RN`, `NP`, `LPN`, `PCP`, `GP`, `Tech`), the same words in other languages (`Médecin`, `Arzt`,
   `Enfermera`, `Infirmière`, `Chirurg`), physicians named by their specialty (`Radiologist`,
   `Psychiatrist`, `Dentist`) and `Physician Assistant` and `Nursing Assistant`. Every other word for
   a person is refused when a value can be a person's name (a word of letters, with or without digits
   beside it): the person, a relative, a member of the household, a contact, and every other role,
   whether it is on a list of the rules above, is recognised by its ending (-er, -or, -ist, -ee,
   -ician), or is one of the words that name people without one (`Who`, `Case`, `Index Case`,
   `Controls`, `Kind`, `Tía`, `Deceased`, `Enrolled`, `Inpatient`, `Agent`, `Admin`, `Charge`,
   `Adult`, `Police`, `Referring`, `Ordering`, `Treating`): `Twin`, `Emergency`, `Witness`,
   `Customer`, `Paciente`, `Co-signer`, `Responsible Party`, `Reporter`, `Author`, `Signer`,
   `Manager`, `Supervisor`, `Director`, `Officer`, `Rep`, `Interpreter`, `Social Worker`, `Department
   Head`, `Seen By`, `Lab Sign-off`. A word before it can make it a thing (`Chemotherapy Agent`,
   `ECG Lead`, `Holter Monitor`, `Femoral Head`), and a payer (`Insurer`, `Payer`) is an
   organisation. Numbers and codes can still be kept under any of these (`Subject` or `Case` of
   `S-014`). The name must also not name an employer, a school, a home, an address, a telephone, an email or
   web address, a device, an image, another name for the person, or notes (`Company`, `School`,
   `Church`, `Home`, `Device`, `Image`, `Face`, `Voice`, `Link`, `Web`, `Notes`, `Comments`,
   `Remarks`, `备注`); `Plate`, `Signature`, `Domain`, `Head`, `Host` and `MAC` count only as the
   whole name. A clinical or care staff column (`Physician`, `Nurse`, `Pharmacist`, `Technician`)
   and a place of care (`Hospital`, `Clinic`, `Site`, `Ward`, `Unit`) can still be kept, and so can a
   column whose name names no person (`Referral`, `Patient Status`, `Provider Specialty`).
   Since round 6 the refusal is decided on the set of the name's words, not on its last word only. A
   word for someone who is not clinical or care staff anywhere in the name (the lists above, an
   abbreviation of the patient, `Pat`, `Pt`, `Pnt`, and words joined across a separator, `In-law`,
   `Step Son`) refuses `--keep` when a value can be a person's name and either another word names a
   name or a part of one (`First`, `Last`, `Full`, `Sur`, `Surname`, `Given`, `Middle`, `Maiden`,
   `Nam`, `Nme`, `Nm`, `Name`, `Initials`, `Nick`, `Alias`) or every other word says nothing of what
   the column holds (`Info`, `Text`, `Ref`, `Label`, `Desc`, `Detail`, `Key`, `Data`, `Title`):
   `Patient Last`, `Mother First`, `Spouse Last`, `Kin Last`, `Caregiver Full`, `MotherLast`,
   `pat_last`, `PATIENT_LAST`, `Pat Info`, `Kin Ref`, `Contact Info`, `Resident Last` (a care home's
   resident is the person). A word that says what the column holds about that person leaves it to the
   person's word (`Patient Status`, `Mother Diagnosis`, `Family History`, `Contact Method`, `Spouse
   Occupation`), and so does a clinician after the person (`Patient Physician`). An abbreviation of a
   name (`Nm`, `Nme`, `Nam`, `PNm`, `FNm`, `LNm`, `PtNm`, `Fname`) refuses `--keep` whenever a value is
   a word, unless the name names a thing and no person (`Drug Nm`), and so does a letter beside a
   word that says nothing else (`P Info`, `M Text`). A place that is not a place of care refuses
   `--keep` when a value is a word (`Area`, `Home Area`, `Service Area`, `Catchment Area`, `Locale`,
   `Territory`, `Community`, `Geography`, `Place`, `Venue`, `Where`, `Lives`, `Living`, `Residence`,
   `Ort`, `Lieu`, `Lugar`, `Luogo`, `Barrio`, `Quartier`), and so does a record, a chart or a file
   (`Cartella`, `Dossier`, `Ficha`, `File`, `Folder`). Numbers of five or more digits in any written
   form (`4527832`, `0452783`, `4527832.0`, `-4527832`, `4,527,832`, `4.52783E+06`) are kept on the
   person's word only under a column name that names a measurement or the number of a thing that is
   not a person (`Steps`, `Total Cost`, `Visits`, `Gene ID`, `Position`, `Chr Start`, `Lot No`, `CPT`,
   `Procedure Code`); under any other name (`Value`, `Col6`, `Code1`, `Registration`, `Token`,
   `Identification`, `VID`, `BID`) they can be record, account or health plan numbers, and `--keep`
   refuses the column. A number that the scrub of step 7 replaces in a kept column anyway (a telephone
   number, nine or more digits) does not count.

   Round 7 added, when a value is a word: who signed, who is addressed and a middle initial
   (`Signed`, `Salutation`, `Resp`, and as the whole name `Sign`, `MI`, `To`, `From`), the source of
   a history (`Hx Source`, `Source of History`), a map, a geographic location, a shelter or a building
   (`Map`, `Geo Location`, `GPS Location`, `Shelter`, `Building`, and as the whole name `Block` and
   `Origin`) and an educational institution (`Education Institution`); `Vital Sign`, `Clinical Sign`
   and `Tumor Origin` are not refused by these words. A word of a column name that mixes letters and digits
   is also read with its digits as the letters they are written for (0 as o, 1 as i or l, 3 as e, 4 as
   a, 5 as s, 7 as t), and refuses `--keep` when it then spells a word for a name, a person, a place or
   a record that would refuse it (`Patient N4me`, `M0ther Info`, `Fu11 Name`); `Col1`, `HbA1c`, `CD4`
   and `Q3` spell no such word. `--keep` and `--redact` take a range of positions (`--keep '#2-#501'`),
   and every column in the range is judged as if it were named on its own.

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
| A | Names | Patient name columns, and columns named for the person (`participant`, `proband`, `first`, `fname`, `nm`, `姓名`, `이름`, and `subject`, `member` or `donor` holding words), become pseudonyms (`P0001`, the same person keeps the same one); names of relatives, household members, contacts (`Next Kin`, `Contact Person`, `Landlord`, `Lives With`), employers, schools, clinicians and other roles become `[REDACTED]`, and a relative's, contact's or the person's own name column cannot be kept unless every value is a category word or a number. Every other text column is kept only when every value is verified (step 5), so a name in any form is redacted by default whatever the column is called: with a qualifier (`Nakamura, Alice (wife)`, `Alice Nakamura - RN`), in lower case, as initials, a surname alone, or in a script without capital letters (Chinese, Japanese, Korean, Arabic, Hebrew, Hindi, Thai). Titled or labelled names in kept text (`Dr. X`, `Patient: X`, `Patient Name: X`, also `Dr. 박지훈` and `Patient: 林子涵`) become `[NAME]`. A name read from a first row of data as a column name (a surname alone, a titled name, a name in any script) is withheld from the plan, the report and the output (step 0). `--keep` is refused for a column whose name has a word the script does not know or names any person who is not clinical or care staff, in any language (`Pai`, `Mom`, `ICE`, `Twin`, `Witness`, `Paciente`, `Who`, `Case`, `Reporter`, `Author`, `Manager`, `Agent`, `Kind`, `Tía`, `Seen By`), and, since round 6, for a column whose name has such a word anywhere beside a part of a name or nothing else (`Patient Last`, `Mother First`, `MotherLast`, `Pat Info`, `In-law`) or is an abbreviation of a name (`PatNm`, `LNm`), and since round 7 for a name word spelled with digits (`Patient N4me`) and for who signed or is addressed (`Signed`, `Salutation`, `MI`, `To`, `From`); a name spelled out letter by letter in a first row read as column names is withheld, and a header cell with an invisible character refused; AKA, pseudonym, kana and pinyin columns are names (step 6) | Names with no title or label in a column the person kept with `--keep` (`kept_unverified_columns`), which is scrubbed for patterns only, including a clinical or care staff column kept on the person's word; a vocabulary word that is also a surname (White, Black) under a race column; a column name that carries a name in an ordinary shape |
| B | Geography smaller than a state | Street, city, county, hometown, suburb, locality, district, precinct, census, coordinate, place-of-birth and `Lives In` columns (also `ciudad`, `municipio`, `ville`, `stadt`, `出生地`, ...) become `[REDACTED]`, and `region`, `home` and `place` columns unless the person keeps them. A town under any other column name is text the script cannot verify, redacted by default (`Visit Location`, `Service Area`, `Cohort`, `Col3`). State and country columns are kept, as Safe Harbor allows, when every value is a state, territory, province or country name or code; a county or a town in one makes the column text the script cannot verify. ZIP columns keep the first three digits, or `000` for the 17 prefixes of 20,000 people or fewer (HHS list, 2000 Census). Columns of mostly five-digit numbers, of four-digit ZIP codes that lost their leading zero, adjacent latitude and longitude columns, a latitude or a longitude on its own (one cell of four or more decimal places, or numbers in range under `Lat`, `Lon`, `Lng` or `Coord`), grid coordinates in metres (`552345.12`), and since round 6 decimals of two or more places within 180 that reach 10, negative decimals from -60 to -180 and a column of decimals within 90 beside a coordinate, under a column name that names no measurement (`Value`, `X`, `Loc X`, `Pos`, `Geo1`), are redacted or pseudonymized by shape unless the column name names a measurement; `--keep` is refused for a place that is not a place of care holding words (`Home Area`, `Lives`, `Catchment Area`, `Area`, `Place`, `Ort`), and for ZIP codes and other numbers of five or more digits under a name that names no measurement; postal code, coordinate and street address column names in other languages and scripts (`PLZ`, `CEP`, `Breitengrad`, `纬度`, `Adresse`, `Calle`, `住所`) are identifiers by name, and a column name carrying a ZIP code or a coordinate (`Weight 94110`, `Weight 37.7749`) is refused. Since round 7 every column of numbers under a column name that names no measurement is redacted until the person keeps it, so a coordinate of any precision under such a name, a one-decimal pair included, is not kept, and a coordinate written after its hemisphere letter (`N37.7749`) is no longer read as an ICD-10 code under a neutral name; since round 8 numbers of five or more digits before the point under a column name that names only a unit of length (`X (m)`, `Y (m)`, `Value (km)`) are redacted as possible grid coordinates, unless the name says what was measured (`Distance`, `Height`, `Elevation`, `Depth`). Street addresses, PO boxes, ZIP+4, "City, ST", labelled coordinates, degrees with N/S/E/W and precise "lat, lon" pairs in kept text are replaced | A bare five-digit ZIP inside kept text; a ZIP column under a column name that names a measurement; a coordinate under a column name that names a measurement (`Ratio`, `Score`), or in a number column the person kept; towns in a column the person kept (a place of care, a location or a destination can be kept); the ZIP list against current Census data |
| C | Dates and ages over 89 | Date columns keep the year only, and so does a column of a year and a month with no day under any name (`2021-03`, `2021/03`, `2021-3`, `2021 Mar`, `202103`, `2021.03`); a date with no four-digit year, or text that is not a missing-value word such as "unknown", becomes `[DATE]`. A year 90 or more years before the reference year becomes `[90_OR_OLDER]` in every date column, whatever its name (`DoB`, `Geburtsdatum`, `出生日期`, `Event Date`, `Col5`), because as a birth year it reveals an age over 89, and so does such a year in unnamed columns of years. A month and a day written as a number with no separator (`0314`, `03142021`, `910314`, `3262017`), an Excel date serial (`44269.4375`, also under `Visit Day`, `Event Time` or `LOS`), and a day of the month, a month or a weekday written as a whole number under a column name for it in any language (`Admit Day`, `Discharge Month`, `MM`, `Mois`, `入院月`, `Weekday`) or in a short column beside its year (`Admit M`, `Admit D`), make a column `[REDACTED]`; so does a month, a day, a week or a day of the year in a column of its own under any name (`Mnth`, `DoM`, `Tg`, `SM`, `Gün`, `W`, `Sample Week`, `Semana`, `Col2`), found by its numbers beside a year or a date column (step 4), and a week or a day of the year by name (`Wk`, `Epi Wk`, `Admit Week`, `MMWR Week`, `Woche`, `周`, `DOY`); a date element in a column name (`Mar-19`, `03/14`, `Q1 20`, `W12 2020`) is refused, and a month name in a column name (`Weight March`, `Mar19`) is withheld. Age columns over 89 become `90+`, also under age names in other languages, with any qualifier and in compounds (`Edad`, `Alter bei Diagnose`, `Patientenalter`, `Idade`, `年龄`, `年纪`, `年齢`, `나이`, `연세`, `Возраст`, `العمر`, `বয়স`), and under `Years Old` or `Months Old` (ages in days, weeks, months or hours are converted first, ages in words such as "ninety-two" count, and text that is not an age becomes `[REDACTED]`); a whole number from 90 to 125 in any cell, under any column name that names no measurement, groups the column the same way whatever else it holds (`ETA`, `Value`, beside a decimal or `<1`), and so do numbers with a unit of time (`95 y`, `1140 mo`, and in other languages `94 ans`, `95 años`, `95岁`, `95세`); `Kor`, `Vanus`, `Amžius` and `Vecums` are age names; an age group above 89 becomes `90+`, and one that straddles 90 ("85-94") becomes `[REDACTED]`. Dates in kept text become the year, including a year and a month (`seen on 2021-03`) and a date with a month name in French, German, Spanish, Italian, Portuguese or Dutch and a four-digit year (`14 mars 2021`, `14. März 2021`); a day and a month with no year after a word such as seen, on or dated (`seen 14/3`, `on 03-14`, `seen 14.3.`) become `[DATE]`; a year after "born", "DOB" or "year of birth" of someone 90 or over becomes `[90_OR_OLDER]`; since round 7 a date written as a number under any column name (a decimal year, `2018.07`, `2021.123`, `1926.164`; a Unix timestamp of 10 or 13 digits, `1629478800.373`, `-1204783199.85`; a Julian date of 7 digits, `2459215.5`) is a date, reduced to its year in a column of nothing else (a year 90 or more years ago becomes `[90_OR_OLDER]`) and redacted in a column that mixes them, and under a name that names no measurement any column of numbers, a decimal age over 89 included, is redacted until the person keeps it; "92 years old", "92 y/o", "95 y" and "ninety-three yo" become "90+ years"; a full date 90 or more years ago becomes `[90_OR_OLDER]`; "a 92F", "pt is 91" and "in her 90s" become 90+, and "nonagenarian" `[90_OR_OLDER]`; since round 8 a date of two or more elements in any script and calendar the grammars read (`2019年3月14日`, `3月14日`, `2019년 3월 14일`, `14 tháng 3 năm 2019`, `14 Mac 2019`, `14 марта 2019`, `R1.5.1`, `令和元年5月1日`, `14 มีนาคม 2562`, `١٤/٣/٢٠١٩`) becomes its Gregorian year in kept text and in a date column (Buddhist and Japanese-era years converted; a calendar whose year is not converted, `1398/12/23`, gives `[DATE]`), "seen 14-3" becomes `[DATE]`, a column name holding such a date is refused and one holding a month or a day alone (`3月`, `tháng 3`, `14日`) is withheld, and under a day, week, month, duration or bare time name six or more digits are a date or a clock time written as a number (`910314`, `143005.123`) | Other dates that reveal an age over 89 (a death date next to an age); ages over 89 under a column name that names a measurement, and in a number column the person kept; a date written as a number that is one value among a measurement's numbers (a cost of `1999.99`); a month, a day or a week in a column of its own that covers fewer than seven months, thirteen days or 27 weeks in a file with no year, a week numbered from 0 beside a year under a name that is not a word for a week, or one under a column name that names a measurement; a season or a half year beside a year in a column name (`Spring 2020`, `H1 2020`); in kept text, a day and a month with no year and no such word before it (`14/3`), a month name in another language with no year, and a year and a month that read as a season or school year (`2011-12` is left alone, because `2010-11` is usually a flu season; a column of months is still reduced as a whole) |
| D | Telephone numbers | Phone columns, also in other languages (`Telefon`, `Teléfono`, `Celular`), become `[REDACTED]`; a phone number that Excel wrote with an exponent (`4.15555E+09`) is pseudonymized under a column name that names no measurement; numbers in kept text, including a cell that is only an international number (`+14155550134`), become `[PHONE]` | Local seven-digit numbers with no label |
| E | Fax numbers | As telephone numbers | |
| F | Email addresses | Redacted | |
| G | Social security numbers | Redacted (and national ID numbers of the chosen locale pack) | |
| H | Medical record numbers | Become pseudonyms (`ID0001`), so rows of one patient stay linked, whether the column is named for them or not: a whole number of four or more digits in any cell, in any written form and also with an exponent (`4.52783E+06`), makes a column under a column name that names no measurement pseudonymized (`Chart`, `Hosp No`, `Patid`, `病历号`, `Col6`, a `Value` column of a long export); a column named with a word for number or record in any language (`Pat No`, `Hospital No`, `Patientennummer`, `Prontuário`, `病历号`, `등록번호`) holding numbers of four or more digits or codes is a record number by name and cannot be kept, and short numbers under such a name (`Study ID` of 1 to 30) are pseudonymized; repeated numbers of seven or more digits are pseudonymized even under a measurement name, in any written form (`-4527832`, `4527832.5`, `4.527832E+06`), and so are long numbers under a measurement name whose last word names a claim, a policy, an invoice, a plan, a visit or a record (`Cost Claim`); labelled numbers in kept text (`MRN 1234`, `MR# 1234`, `ID 1234`, `#A-998`) become `[ID]`; a code grammar takes only its exact published shape, so a record number with a prefix (`RS1234567`, `NM_1234567`, `H8Q.600`) is not a code, and a LOINC-shaped number counts as a code only under a lab or test name; a column name holding a number of five or more digits, also in groups (`Patient 3767393`, `Patient 376 7393`, `Pt 37_67_393`), is refused; since round 6 health and patient numbers by abbreviation (`PHN`, `NHS`, `NIP`, `PRN`, `Patid`), a key or a reference of the patient (`Patient Ref`, `Patient Key`) and a name with a number sign (`Pat#`, `MR#`) are record numbers by name with four or more digits, repeated six-digit numbers under `Visits`, `Encounters` or `Admissions` are pseudonymized, and `--keep` is refused for numbers of five or more digits under any column name that names no measurement and no thing whose numbers are not a person's; since round 7 short numbers under a code, a label, a token or a sequence of the person or the record (`Pt Code`, `Participant Label`) are pseudonymized, and any column of numbers under a column name that names no measurement is redacted until the person keeps it; since round 8 repeated numbers of seven or more digits (not round ones) are pseudonymized under a measurement name whatever their share of the cells (a `Glucose` column with a few), and a label, a pseudonym, a lot, a batch or a number sign beside a measurement word (`WBC Label`, `Dose Lot`, `Dose #`, `Count#`) makes the name a number's name | A record number of three digits or fewer kept on the person's word under a column name that names no record; a record number of four to six digits, or one that does not repeat, under a column name that names a measurement (`Steps`, `Total Cost`, `Count`), or one of four digits kept on the person's word under a neutral name; a record number written exactly as an rsID (`rs` in lower case and up to ten digits), an Ensembl identifier (`ENSG` and eleven digits) or a dotted ICD-10 code (`S21.1234`); a record number of four digits or fewer in a column name |
| I | Health plan beneficiary numbers | Member, policy, subscriber, Medicare and Medicaid columns redacted; Medicare MBI-shaped values in text replaced. A payer or type column (`insurance`, `insurance_type`, `medicare_status`) of category words such as Medicare or Commercial is not an identifier by name: Yes and No in it are kept, and other words are redacted as text the script cannot verify until the person keeps the column | |
| J | Account numbers | Account, card and IBAN columns redacted; grouped card numbers and valid IBANs in text replaced | |
| K | Certificate and licence numbers | Licence, certificate, DEA, NPI and passport columns redacted; labelled numbers in text replaced | |
| L | Vehicle identifiers and plates | VIN and plate columns redacted; 17-character VINs and labelled plates in text replaced | Unlabelled plate numbers in text |
| M | Device identifiers and serial numbers | Device ID, serial, UDI and IMEI columns redacted; MAC addresses, GS1 UDIs and labelled serials in text (`serial 8841`, `S/N 8841`, `SN 8841-2290`) replaced | |
| N | Web URLs | Redacted, and so are columns named for a social network (`Twitter`, `Instagram`, `TikTok`) unless every value is a category word. In kept text: addresses with a scheme or `www.`, a host and a path with neither (`fb.me/jane.doe`), bare domains ending in .com, .org, .net, .edu, .gov, .io, .info or .biz, social media handles (`@jane_doe`, `Facebook /jane.doe`, `Instagram: jdoe`, `skype:jdoe`, `on Instagram as jdoe99`, `u/jdoe`, `jdoe#1234`) and logins written `user@host` | Bare domains on other endings; a handle written with no `@`, no network name and no dot, digit or underscore, or with letters only after a network name and no colon |
| O | IP addresses | Redacted, by column name or by values (IPv4 and IPv6) | |
| P | Biometric identifiers | Fingerprint, voiceprint, retina, iris and face-template columns redacted; long hex or base64 blobs in text replaced | Biometrics stored in another form |
| Q | Full-face photographs | Photo and image columns redacted; image file names and `data:image` values in text replaced | Images themselves (DICOM and photo files are out of scope) |
| R | Any other unique identifying number or code | Unique numbers, and whole numbers of four or more digits under a column name that names no measurement, are pseudonymized, and since round 7 every other column of numbers under such a name is redacted until the person keeps it; text codes that no closed grammar verifies are redacted until the person keeps them; in kept text, numbers of nine or more digits (also written `274,365,867`) and codes with four or more digits and a letter become `[ID]` (dbSNP identifiers in lower case, Ensembl identifiers of eleven digits, RefSeq identifiers, and whole values of a code grammar, are left alone; `RS1234567` is replaced) | Rare combinations of values (quasi-identifiers), small cells; a number column kept on the person's word |

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
  given names tested, only `Case`, `Day`, `Person` and `Weeks` are shown, and of given names that
  are also column words `Gene` and `Field` (since round 7 `Bill` and `Charity` alone are withheld,
  beside another column word they are shown). A column word that
  is an eponym of a score (`Charlson`, `Glasgow`, `Barthel`) is shown alone. A first row with an identifier
  pattern in any cell (an email, a phone or ID number, a date, a number of five or more digits
  also written in groups, a decimal of four or more places, a year 90 or more years ago, a month,
  a day, a quarter or a week beside a number) is refused, and so is one in which a third of the
  cells look like values or names. A number of four digits or fewer in a column name is shown
  (`Patient 4527`, `Patient 45 27`), so a short record number written into a column name is not
  found; nor is an identifier written as an ordinary word, nor a season or a half year beside a
  year (`Spring 2020` is withheld only because `Spring` is also a surname; `H1 2020` is shown), nor
  a month and a day written as two numbers beside a word that takes a range or a scale (`Grade 3/4`,
  `Score 1-10`, `Age 12-18`), nor a study day alone (`Day 14`, `Jour 14`), nor a surname beside a
  measurement word (`WBC Cook`, `Wells Hb`). Since round 8 the other way round some ordinary names
  are withheld until the person confirms them: a threshold written as a decimal that reads as a day
  and a month (`pH 7.4`, `HbA1c 6.5`), a Japanese count of days before a noun (`30日死亡率`, read as the
  30th), two colours of anatomy side by side (`Gray White Matter Ratio`), a person word beside a
  hospital word (`Patient Ward`, `Ward Nurse`). A
  wide table of five or more digits in a row of separators that is not a date (`Range 1-5 (2020)`,
  `Dose 1 2 3 4 5`) is refused too, and the person renames those columns. Since round 7 a header
  cell holding a NUL, a control or a format character is refused and a word spelled out one letter
  at a time with one separator is withheld; a name broken up another way a person still reads
  (`Zor-ble-ton`, or digits for letters) is not found in a column name.
- In a file with no header row, read without `--no-header`, the first row is lost from the
  output (its cells become withheld column names). The skill asks the person whether the first
  row holds column names before it runs.
- It reads CSV and TSV files in UTF-8, with or without a byte order mark, and UTF-16 or
  UTF-32 with one. Any other file (a Windows-1252 or Latin-1 export, Excel's plain "CSV" save)
  is refused with the remedy: save it as "CSV UTF-8", or rerun with `--encoding` (`cp1252`,
  `latin-1`, `utf-16-le`, `euc-kr`, ...). It does not guess an 8-bit encoding, because a wrong
  guess turns names into other text silently. Since round 7 a file with a NUL byte in its first
  4096 bytes and no byte order mark is refused as UTF-16 without a byte order mark (which is valid
  UTF-8 with a NUL beside every letter), with the same remedy and the byte order the NULs suggest
  (`--encoding utf-16-le` or `utf-16-be`). The output is always UTF-8.
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
  other way round, a record number of four to six digits, or of seven or more that does not repeat,
  under a column name that names a measurement (`Steps`, `Total Cost`), is kept, and so is a date
  written as three digits (`314`) under such a name; since round 7 a record number of three digits
  or fewer under a column name that names no measurement is redacted by the name. Since round 5, in a file with a year or a date column, any column of
  whole numbers from 1 to 366 under a column name that names no measurement is read as a possible
  date element (a visit number, a room number, a coded category, ages under `Value`), and a
  protocol week under `Week` (0, 4, 12, 52) as a week; the person keeps them with `--keep`. A
  month, a day or a week in a column of its own under a column name that names a measurement
  (`Score` of 1 to 12) or a stage, a grade or a class is kept; under any other name such a column
  is redacted by its name since round 7, and the plan names it as a possible date element only when
  its numbers fit the rules above (most months or days, or a file with a year).
- Since round 7 every column of numbers under a column name that names no measurement is redacted
  until the person keeps it, whatever its numbers are: a long lab export's `Value`, a `Visit Number`,
  a `Cycle`, a sex, a race or a Likert item coded as a number (`Q7`), a `Children` count, years under
  a neutral name (`Col1`), a gene symbol or a probe in a wide matrix, and a z-score under `Z`. A long
  lab table (`Patient ID`, `Lab`, `Value`, `Unit`) completes once the person keeps `Value` (and
  `Lab`, whose lab names are text the script cannot verify); `--keep` refuses numbers of five or more
  digits under such a name, so a `Value` holding a platelet count of `250000` cannot be kept until the
  person renames it with a unit in brackets (`Value (units)`) or a measurement word. The measurement
  names are a list, so a measurement under a name the list does not know (`Comorbidities`, `Output`,
  `Loss`) is redacted too, and the person keeps it or renames it (`Comorbidity Count`). The other way
  round, a coordinate of any precision, an age over 89 and a record number that does not repeat
  under a column name that names a measurement (`Ratio`, `Score`, `Steps`), and a date written as a
  number that is one value among a measurement's numbers, are kept. A protocol week under a word for a week
  (`Visit Week` of 0, 4, 12, 52) is redacted in a file with a year and kept only on the person's word;
  to keep it as data the person recodes it as a duration before the run (`Weeks Since Baseline`) or
  removes the date and year columns.
- Since round 6 `--keep` is refused on the set of a column name's words: a word for someone who is not
  clinical or care staff anywhere in the name beside a part of a name or a word that says nothing
  else, an abbreviation of a name, a place that is not a place of care and a record word refuse it
  when a value is a word. A name made only of column words that names a person in a way none of
  these read can still be kept (`Patient Hometown` is refused by its place word, `Patient Moniker` by
  its name word; a person word beside an ordinary attribute word, `Spouse Occupation`, is kept), and
  so can a staff role, a place of care, a location, a destination, a region and a payer holding
  names or towns.
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
- `--keep` is accepted on a column named for clinical or care staff (`Physician`, `Provider`,
  `Referring Physician`, `Nurse`, `Pharmacist`, `Technician`, `Midwife`), a place of care
  (`Hospital`, `Clinic`, `Site`, `Ward`, `Unit`, `Department`), a location or a destination, which
  usually name a place of care (`Location`, `Visit Location`, `Discharge Destination`), a state-level
  region (`Region`, `Province`, `Prefecture`), an organisation that is not an employer, and a payer
  column (`Payer`, `Payor`): their values are not a closed list, so a town or a person's name in one
  stays when the person keeps it, and so do a zone, a cluster, a sector, a station, a campus, an
  injury or an exposure location, and where a patient was admitted or referred from or discharged to
  (`Zone`, `Station`, `Campus`, `Exposure Location`, `Admitted From`, `Discharge To`); since round 7
  `Origin`, `Block`, `Shelter`, `Building`, `Map` and a geographic location are refused. Kept on the person's word,
  such a column is scrubbed for patterns only and named in `kept_unverified_columns`, and a
  clinical staff column keeps the clinicians' names. Since round 4 `--keep` is refused for any
  other column whose name has a word the script does not know, so a person whose column names are
  in a language the lists do not cover renames the columns they want to keep; and since round 5
  for every column whose name ends in a word for a person who is not clinical or care staff, when
  a value can be a person's name. A word for a person is found by the rules' word lists, by its
  ending (-er, -or, -ist, -ee, -ician) and by a short list of words that have none (`Who`, `Case`,
  `Kind`, `Deceased`, `Agent`); an ordinary column word that names a person in a sense none of
  these read can still be kept, and a word for a thing that ends like a role (`Monitor`, `Lead`)
  is refused unless a word before it makes it a thing (`Holter Monitor`, `ECG Lead`). Under such
  a name, a staff role the list does not name (`Social Worker`, `Case Manager`, `Navigator`,
  `Paramedic`) is refused too, and the person renames the column.
- Its code grammars are the exact published shapes, so a record number written exactly as an
  rsID (lower-case `rs` and up to ten digits), an Ensembl identifier (`ENSG` and eleven digits) or
  a dotted ICD-10 code (a capital letter, two digits in the chapter's range, a dot and up to four
  characters, as a pathology accession number `S21.1234` can be) is kept as a code under any column
  name; a code in lower case or with a letter where the
  published shape has a digit (`e11.9`, `C3A.1`), and a LOINC code under a column name that names
  no LOINC code, lab, test or observation, are redacted until the person keeps them.
- Its network guard replaces Python's usual socket functions; it is not a sandbox. Run it
  under an operating-system sandbox with networking denied when that must be guaranteed.
