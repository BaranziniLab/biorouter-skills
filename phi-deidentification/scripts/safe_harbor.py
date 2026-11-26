#!/usr/bin/env python3
# Copyright 2026 Baranzini Lab, University of California, San Francisco
# SPDX-License-Identifier: Apache-2.0
#
# Part of the phi-deidentification skill for Biorouter. It reuses the file
# reader and the pseudonym generators of deidentify.py (MIT, Aperivue
# medsci-skills; see LICENSE-UPSTREAM), which sits next to this file.
"""
HIPAA Safe Harbor de-identification of a clinical table, run without anyone
reading the raw data.

This is the non-interactive counterpart of deidentify.py. An agent runs it on
the person's files with the shell. It prints and writes column names, counts,
decisions and placeholders only: never a cell value of the input, so the chat
that started it never sees the raw data.

    python3 safe_harbor.py plan   INPUT [--locale us] [--keep COL] [--redact COL]
                                  [--encoding NAME] [--delimiter CHAR] [--no-header]
                                  [--keep-name #N] [--keep-all-names]
    python3 safe_harbor.py run    INPUT --output-dir DIR [--locale us] [--keep COL]
                                  [--redact COL] [--reference-year YYYY]
                                  [--mapping-out FILE] [--encoding NAME] [--delimiter CHAR]
                                  [--no-header] [--keep-name #N] [--keep-all-names]
    python3 safe_harbor.py verify FILE [--locale us] [--reference-year YYYY] [--delimiter CHAR]

What it does, per the 18 identifiers of 45 CFR 164.514(b)(2), is listed in
references/safe-harbor-mode.md. In short: identifier columns found by name
are replaced (names and record numbers by pseudonyms, dates by their year,
ZIP codes by their first three digits or 000, ages over 89 by "90+", the rest
by [REDACTED]). Every other column fails closed: it is kept only when every
value is verified as a measurement (a number under a column name that names a
measurement, or with its unit beside it, that passes the record number, date,
coordinate and age checks; years under a name for a year), a code of
a closed grammar, a word of a closed vocabulary (sex, yes and no, ...), a date or
an allowed state or country. Any other text, and numbers under a column name that
names no measurement or that it cannot tell from record numbers, dates, ZIP codes,
coordinates or ages, are changed until the person keeps them with --keep (a name,
#N, or a range #A-#B); free text can never be kept. Numbers are judged cell by cell. Column
names fail closed as well: a name with a word the script does not know as a column
word (a patient's name read from a first row of data) is withheld and written as
column_N until the person confirms it, and --no-header reads a file without a header
row. Every kept cell is scrubbed of identifier patterns, and the output is scanned
again before it is kept. A file that is not UTF-8 is refused unless --encoding names
its encoding, and so is a header cell holding a NUL, a control or a format character.

Exit codes: 0 done and the output passed the residual check; 2 refused (bad
arguments, a file it cannot read, a header row that looks like data); 3 the
residual check found identifiers, and the output was deleted. The residual
check looks for identifier patterns and shapes; passing it is not proof that
the output is de-identified.

The script uses the Python standard library only (openpyxl for .xlsx) and
makes no network calls. Before anything else runs it also replaces Python's
usual socket entry points with a function that refuses, so a library cannot
connect by accident. That is a guard, not a sandbox: for a guarantee, run the
script under an operating-system sandbox with networking denied.
"""

from __future__ import annotations

import socket
import sys


# ---------------------------------------------------------------- no network
# A guard against accidental connections, not a sandbox (see the docstring).
def _network_disabled(*_args, **_kwargs):
    raise OSError("network access is disabled in safe_harbor.py")


for _name in ("create_connection", "getaddrinfo", "gethostbyname",
              "gethostbyname_ex", "gethostbyaddr", "socketpair"):
    setattr(socket, _name, _network_disabled)
for _name in ("connect", "connect_ex", "sendto", "sendmsg", "bind"):
    setattr(socket.socket, _name, _network_disabled)

# No __pycache__ next to the scripts of an installed skill.
sys.dont_write_bytecode = True

import argparse  # noqa: E402
import codecs  # noqa: E402
import csv  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import stat  # noqa: E402
import unicodedata  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deidentify as upstream  # noqa: E402

# deidentify.py logs sheet names and paths at INFO and WARNING; this tool
# reports counts instead.
logging.getLogger("deidentify").setLevel(logging.ERROR)
# A long note in one cell would otherwise stop the CSV reader (128 KiB default).
csv.field_size_limit(64 * 1024 * 1024)

SKILL_VERSION = "1.0.1"
REPORT_NAME = "deidentification_report.json"

# Three-digit ZIP prefixes whose combined population is 20,000 or fewer, which
# Safe Harbor requires to be written as 000 (HHS guidance, 2000 Census).
RESTRICTED_ZIP3 = frozenset({
    "036", "059", "063", "102", "203", "556", "692", "790", "821", "823",
    "830", "831", "878", "879", "884", "890", "893",
})

PLACEHOLDER = re.compile(r"\[[A-Z0-9_]+\]")
# Cell values that say a value is missing. They carry no identifier, so a date
# or age column may keep them; any other text left in such a column is replaced.
MISSING_VALUES = frozenset({
    "unknown", "unk", "not known", "not recorded", "not documented", "not available",
    "not applicable", "n/a", "na", "n.a.", "nan", "none", "null", "nil", "missing",
    "declined", "refused", "nr", "nd", "?", "-", "--", ".",
})
PSEUDONYM = re.compile(r"(?:P|ID)\d{4,}")
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


# ================================================================ patterns
# Each entry: (identifier type, compiled regex, replacement). A replacement is
# a string, or a function of the match that returns the new text or None to
# leave the match alone (a validator said it is not an identifier).

MONTH = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?"
         r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
MONTH_NOT_MAY = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|june?|july?"
                 r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
YEAR4 = r"(?:1[89]\d{2}|20\d{2})"
DAY = r"(?:0?[1-9]|[12]\d|3[01])"
MON_NUM = r"(?:0?[1-9]|1[0-2])"
TIME = r"(?:(?:T|\s+)\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?[AaPp]\.?[Mm]\.?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
US_STATES = (r"(?:AL|AK|AZ|AR|CA|CO|CT|DE|DC|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS"
             r"|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|PR|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)")
STREET_SUFFIX = (r"(?:street|st|avenue|ave|boulevard|blvd|road|rd|drive|dr|lane|ln|court|ct|way"
                 r"|place|pl|terrace|ter|circle|cir|parkway|pkwy|highway|hwy|square|sq|trail|trl"
                 r"|alley|aly|crescent|cres|close|row|walk|loop|plaza|plz)")
ID_LABELS = (
    r"(?:mrn|mr\s*(?:#|no\.?|number)|medical\s+record(?:\s+(?:number|no\.?|#))?|record\s+(?:number|no\.?|#)"
    r"|chart\s+(?:number|no\.?|#)|patient\s+(?:id|number|no\.?)|account(?:\s+(?:number|no\.?|#))?"
    r"|acct\.?(?:\s+(?:number|no\.?|#))?|member\s+(?:id|number|no\.?|#)"
    r"|policy(?:\s+(?:id|number|no\.?|#))?|subscriber(?:\s+(?:id|number|no\.?))?"
    r"|group\s+(?:number|no\.?|#)|beneficiary(?:\s+(?:id|number|no\.?))?"
    r"|health\s+plan(?:\s+(?:id|number|no\.?))?|medicaid(?:\s+(?:id|number|no\.?))?"
    r"|medicare(?:\s+(?:id|number|no\.?))?|insurance(?:\s+(?:id|number|no\.?|#))?"
    r"|driver'?s?\s+licen[cs]e(?:\s+(?:number|no\.?|#))?|licen[cs]e\s+plate"
    r"|licen[cs]e(?:\s+(?:number|no\.?|#))?|certificate(?:\s+(?:number|no\.?|#))?"
    r"|cert\.?(?:\s+(?:number|no\.?|#))?|dea(?:\s+(?:number|no\.?|#))?|npi"
    r"|serial(?:\s+(?:number|no\.?|#))?|s/n|sn(?![a-z])|s\.n\.|device\s+(?:id|serial|number)|udi|imei|vin"
    r"|plate(?:\s+(?:number|no\.?|#))?|passport(?:\s+(?:number|no\.?|#))?"
    r"|case\s+(?:id|number|no\.?)|accession(?:\s+(?:number|no\.?|#))?"
    r"|specimen\s+(?:id|number|no\.?)|identifier|id)"
)
# Domain endings a host-and-path address is recognised by when it has no scheme or www.
URL_TLDS = (r"(?:com|org|net|edu|gov|mil|info|biz|io|me|ly|co|us|uk|ca|au|gl|gd|tv|app|dev|ai"
            r"|xyz|health)")
NAME_LABELS = (r"(?:patient|pt|name|full\s+name|contact|spouse|wife|husband|partner|mother"
               r"|father|parent|son|daughter|sibling|brother|sister|guardian|caregiver"
               r"|emergency\s+contact|next\s+of\s+kin|nok|employer)")
# Month names in French, German, Spanish, Italian, Portuguese and Dutch. They are read as
# a date only with a four-digit year after them, so "Marco" or "mars" alone stay.
FOREIGN_MONTH = (r"(?:janvier|janv|f[ée]vrier|f[ée]vr|mars|avril|avr|mai|juin|juillet|juil|ao[uû]t"
                 r"|septembre|octobre|novembre|d[ée]cembre|d[ée]c|januar|j[äa]nner|jaenner|j[äa]n"
                 r"|februar|m[äa]rz|maerz|m[äa]r|juni|juli|oktober|okt|dezember|dez|enero|febrero"
                 r"|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre"
                 r"|diciembre|dic|gennaio|febbraio|aprile|maggio|giugno|luglio|settembre|ottobre"
                 r"|dicembre|janeiro|fevereiro|mar[çc]o|maio|junho|julho|setembro|outubro|dezembro"
                 r"|januari|februari|maart|mei|augustus)")
# Words after which a day and a month with no year are a date ("seen 14/3", "on 03-14").
DATE_CONTEXT = (r"(?:seen|on|dated|since|until|till|admitted|discharged|visited|visit|appt"
                r"|appointment|returned|presented|scheduled|reviewed)")
# A count after the numbers makes them a range, not a date ("seen 10-12 times").
NOT_A_DATE_AFTER = (r"(?!\s*(?:times|x\b|days?\b|weeks?\b|wks?\b|months?\b|mos?\b|years?\b|yrs?\b"
                    r"|hours?\b|hrs?\b|mins?\b|minutes|mg\b|mcg\b|ml\b|units?\b|%|percent|patients"
                    r"|visits|occasions|episodes|doses|tabs?\b|per\b))")
SOCIAL_NETWORKS = (r"(?:facebook|fb|instagram|ig|twitter|tiktok|snapchat|linkedin|youtube|reddit"
                   r"|telegram|whatsapp|wechat|skype|discord|mastodon|bluesky|tumblr|pinterest"
                   r"|github|myspace)")
# A letter of a script without capital letters, as a regex class: Hebrew, Arabic, the Indic
# scripts, Thai, Lao, Georgian, Hangul, kana and CJK ideographs (see _caseless_letter).
CASELESS_CLASS = ("[\u0590-\u05ff\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\u0900-\u0dff\u0e00-\u0eff"
                  "\u10d0-\u10ff\u1100-\u11ff\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af"
                  "\uf900-\ufaff\ufb1d-\ufdff\ufe70-\ufeff]")
# Words written after "Instagram:" that are not a handle.
NOT_A_HANDLE = (r"(?:yes|no|none|n/?a|nil|unknown|declined|refused|private|deleted|inactive|active"
                r"|not|null|only|user|account|profile|preferred|available|unavailable|ok|okay|group"
                r"|groups|message|messages|messaging|call|calls|video|chat|used|uses|requested|pending"
                r"|blocked|verified|unverified|linked|unlinked|consented|opted)\b")


def _year_of(m: re.Match) -> str:
    text = m.group(0)
    y = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})", text)
    return y.group(1) if y else "[DATE]"


def _year_and_month(m: re.Match):
    """The year of "2021-03". A month that is the next year's last two digits ("2010-11",
    "2011/12") is a season or a school year as often as a month, and is left alone; a
    column of months is still found as a whole, because its other months are read."""
    month = m.group("m")
    if len(month) == 2 and int(month) == (int(m.group("y")) + 1) % 100:
        return None
    return m.group("y")


def cap_old_year(year: str, reference_year: int) -> str:
    """[90_OR_OLDER] for a four-digit year at least 90 years before the reference year: as the
    year of a birth date it reveals an age over 89, so no date column keeps it."""
    if re.fullmatch(r"\d{4}", year) and reference_year - int(year) >= 90:
        return "[90_OR_OLDER]"
    return year


def _capped_year(repl, reference_year: int):
    def capped(m: re.Match):
        out = repl(m)
        return cap_old_year(out, reference_year) if isinstance(out, str) else out
    return capped


def _keep_label(placeholder: str):
    """Replace only the named group `v`, keeping the label before it."""
    def repl(m: re.Match) -> str:
        return m.group(0)[: m.start("v") - m.start()] + placeholder + m.group(0)[m.end("v") - m.start():]
    return repl


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _phone_intl(m: re.Match):
    return "[PHONE]" if 8 <= len(_digits(m.group(0))) <= 15 else None


def _iban(m: re.Match):
    s = re.sub(r"\s", "", m.group(0)).upper()
    if not 15 <= len(s) <= 34:
        return None
    rearranged = s[4:] + s[:4]
    try:
        num = "".join(str(int(c, 36)) for c in rearranged)
    except ValueError:
        return None
    return "[ACCOUNT]" if int(num) % 97 == 1 else None


def _ipv6(m: re.Match):
    return "[IP]" if re.search(r"[0-9A-Fa-f]", m.group(0)) and m.group(0).count(":") >= 2 else None


def _code(m: re.Match):
    s = m.group(0)
    if len(s) < 6 or len(re.findall(r"\d", s)) < 4 or not re.search(r"[A-Za-z]", s):
        return None
    if re.fullmatch(r"rs[1-9]\d{0,9}|ENS(?:[A-Z]{3})?[EFGPRT]\d{11}(?:\.\d{1,3})?", s):
        return None  # dbSNP and Ensembl identifiers name genes and variants, not people (exact shapes)
    return "[ID]"


def _long_number(m: re.Match):
    # The digits of a dbSNP or Ensembl identifier (rs..., ENSG...) name a variant or a gene: an rsID in
    # lower case of up to ten digits, an Ensembl identifier of exactly eleven (round 5).
    before = m.string[max(0, m.start() - 12):m.start()]
    digits = m.group(0)
    if re.search(r"(?:^|[^A-Za-z0-9])rs$", before) and len(digits) <= 10 and not digits.startswith("0"):
        return None
    if re.search(r"(?:^|[^A-Za-z0-9])ENS(?:[A-Z]{3})?[EFGPRT]$", before) and len(digits) == 11:
        return None
    return "[ID]"


def _city_state(m: re.Match) -> str:
    return "[CITY], " + m.group("st")


def _state_zip(m: re.Match) -> str:
    return m.group("st") + " [ZIP]"


def _labelled_name(m: re.Match):
    """A name after "Patient", "Contact" or "Mother", unless it is a category word
    ("Patient Refused", "Contact Phone")."""
    if _is_category_value(m.group("v")):
        return None
    return _keep_label("[NAME]")(m)


def _caseless_labelled_name(m: re.Match):
    """A name in a script without capital letters after a title or a label, unless it is a
    common category word ("Patient: 男")."""
    if m.group("v").strip() in CASELESS_CATEGORY_VALUES:
        return None
    return _keep_label("[NAME]")(m)


def _age90(m: re.Match) -> str:
    return "90+ years"


def _age_label(m: re.Match) -> str:
    return m.group("label") + " 90+"


# Ages of 90 and over written out in words ("ninety-two", "one hundred and one").
AGE_WORD = (r"(?:ninety(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?"
            r"|(?:one|a)[\s-]+hundred(?:[\s-]+(?:and[\s-]+)?(?:one|two|three|four|five|six"
            r"|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen))?)")
AGE_WORD_RX = re.compile(r"(?i)\b(?:ninety|(?:one|a)[\s-]+hundred)\b")
AGE_NUM = r"(?:9\d|1[0-4]\d)"


def _coordinate_pair(m: re.Match):
    a, b = (float(x) for x in re.findall(r"[+-]?\d+(?:\.\d+)?", m.group(0))[:2])
    return "[GEO]" if abs(a) <= 90 and abs(b) <= 180 and max(abs(a), abs(b)) >= 10 else None


def birth_year_pattern(reference_year: int) -> tuple[str, re.Pattern, object]:
    """A year written after "born", "DOB" or "year of birth": kept unless the person
    would be 90 or older in the reference year."""
    def repl(m: re.Match):
        if reference_year - int(m.group("v")) >= 90:
            return _keep_label("[90_OR_OLDER]")(m)
        return None
    rx = re.compile(r"(?i)\b(?:born(?:\s+in)?|b\.|birth\s*year|year\s+of\s+birth|yob|d\.?o\.?b\.?"
                    r"|date\s+of\s+birth|birth\s*date)\s*[:=]?\s*(?P<v>" + YEAR4 + r")(?!\d)")
    return ("birth_year", rx, repl)


# Order matters: earlier patterns take their span before later ones look.
PATTERNS: list[tuple[str, re.Pattern, object]] = [
    ("photo", re.compile(r"(?i)data:image/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+"), "[PHOTO]"),
    ("url", re.compile(r"(?i)\b(?:https?|s?ftp|file)://[^\s<>\"']+|\bwww\.[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s<>\"']*)?"), "[URL]"),
    # A host and a path with no scheme ("fb.me/jane.doe", "clinic-x.org/p/7"), and a bare
    # domain on the commonest endings ("example.com").
    ("url", re.compile(r"(?i)(?<![\w@./-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+" + URL_TLDS
                       + r"(?::\d+)?/[^\s<>\"']*"), "[URL]"),
    ("url", re.compile(r"(?i)(?<![\w@./-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:com|org|net|edu|gov|io|info|biz)"
                       r"(?![\w-])(?!\.[a-z0-9])"), "[URL]"),
    # An apostrophe may sit inside the local part ("j.o'brien@...").
    ("email", re.compile(r"(?i)(?<![\w.%+-])[a-z0-9._%+-]+(?:'[a-z0-9._%+-]+)*@[a-z0-9.-]+\.[a-z]{2,}(?![\w-])"), "[EMAIL]"),
    # A login written as user@host, with no domain ending.
    ("email", re.compile(r"(?i)(?<![\w.%+@-])[a-z][a-z0-9._%+-]*@[a-z][a-z0-9-]*(?![\w@-])(?!\.[a-z0-9])"), "[EMAIL]"),
    # Social media handles: "@jane_doe", and a handle after the name of a network.
    ("social", re.compile(r"(?<![\w@.+/-])@[A-Za-z_][A-Za-z0-9_.]{0,29}[A-Za-z0-9_](?![\w@])"), "[HANDLE]"),
    ("social", re.compile(r"(?i)\b(?P<label>" + SOCIAL_NETWORKS + r")\b\s*(?:handle|account|profile|user(?:name)?)?\s*[:=]?\s*"
                          r"(?P<v>[/@][A-Za-z0-9_.-]{1,}|(?=[A-Za-z0-9_.-]*[A-Za-z])(?=[A-Za-z0-9_.-]*[._\d])"
                          r"[A-Za-z0-9_][A-Za-z0-9_.-]{2,})"), _keep_label("[HANDLE]")),
    # A handle of letters only after "Instagram:" or "skype:", a name in capitals after
    # "Facebook:", and a handle with a digit, dot or underscore after "on Instagram as".
    ("social", re.compile(r"(?i)\b(?P<label>" + SOCIAL_NETWORKS + r"\b\s*(?:handle|account|profile|user(?:name)?|id)?"
                          r"\s*[:=]\s*)(?!" + NOT_A_HANDLE + r")(?P<v>(?-i:[A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){0,2})"
                          r"|[A-Za-z][A-Za-z0-9_.-]{1,29})(?![\w@])"), _keep_label("[HANDLE]")),
    ("social", re.compile(r"(?i)\b(?P<label>" + SOCIAL_NETWORKS + r"\b\s*(?:handle|account|profile|user(?:name)?)?"
                          r"\s+as\s+)(?P<v>(?=[A-Za-z0-9_.-]*[A-Za-z])(?=[A-Za-z0-9_.-]*[._\d])"
                          r"[A-Za-z0-9_][A-Za-z0-9_.-]{2,})(?![\w@])"), _keep_label("[HANDLE]")),
    # A Reddit user ("u/jdoe"), but not a unit ("10 u/day", "u/kg").
    ("social", re.compile(r"(?<![\w/])(?<!\d\s)u/(?!(?:kg|day|days|d|hr|hrs|h|hour|hours|ml|l|dl|min|mins|wk"
                          r"|week|dose|g|mg|mcg|unit|units)\b)[A-Za-z0-9_-]{3,20}(?![\w/])"), "[HANDLE]"),
    ("device", re.compile(r"(?i)(?<![0-9a-f:-])[0-9a-f]{2}([:-])[0-9a-f]{2}(?:\1[0-9a-f]{2}){4}(?![0-9a-f:-])"), "[DEVICE_ID]"),
    ("device", re.compile(r"(?i)(?<![0-9a-f.])[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}(?![0-9a-f.])"), "[DEVICE_ID]"),
    ("ip", re.compile(r"(?i)(?<![0-9a-f:])(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}(?![0-9a-f:])"), _ipv6),
    ("ip", re.compile(r"(?i)(?<![0-9a-f:])(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,6})?::(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,6})?(?:\.\d{1,3}){0,3}(?![0-9a-f:])"), _ipv6),
    ("ip", re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?![\d.])"), "[IP]"),
    # Coordinates: labelled, in degrees with a compass letter, or a precise "lat, lon" pair.
    ("geo", re.compile(r"(?i)\b(?P<label>lat(?:itude)?|lon(?:gitude)?|lng|gps|geocode|coord(?:inate)?s?)\s*[:=]?\s*(?P<v>[+-]?\d{1,3}\.\d+(?:\s*[,/;]\s*[+-]?\d{1,3}\.\d+)?)"), _keep_label("[GEO]")),
    ("geo", re.compile(r"(?<![\w.])[+-]?\d{1,3}(?:\.\d+)?\s*\u00b0\s*(?:\d{1,2}(?:\.\d+)?\s*['\u2032]\s*(?:\d{1,2}(?:\.\d+)?\s*[\"\u2033]\s*)?)?[NSEWnsew](?![A-Za-z])"), "[GEO]"),
    ("geo", re.compile(r"(?<![\d.])[+-]?\d{1,2}\.\d{3,}\s*,\s*[+-]?\d{1,3}\.\d{3,}(?![\d.])"), _coordinate_pair),
    ("id", re.compile(r"(?i)\b(?P<label>" + ID_LABELS + r")\s*(?:[:#=]\s*)?(?P<v>(?=[A-Z0-9/.-]*\d)[A-Z0-9][A-Z0-9/.-]{2,}[A-Z0-9])"), _keep_label("[ID]")),
    # A number written after "#" ("Hospital #A-998").
    ("id", re.compile(r"(?i)(?<![\w&#])#\s?(?P<v>(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{2,}[A-Z0-9])(?![\w-])"), _keep_label("[ID]")),
    # A user name and a four-digit tag ("jdoe#1234"), after the labelled numbers ("MRN#1234").
    ("social", re.compile(r"(?<![\w#@.])[A-Za-z][A-Za-z0-9_.]{1,31}#\d{4}(?![\w#])"), "[HANDLE]"),
    ("ssn", re.compile(r"(?i)\b(?:ssn|social\s+security(?:\s+(?:number|no\.?|#))?)\s*[:#]?\s*(?P<v>\d{3}[\s-]?\d{2}[\s-]?\d{4})(?!\d)"), _keep_label("[SSN]")),
    ("ssn", re.compile(r"(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])"), "[SSN]"),
    # Spaced: a space before it is fine ("ss# 123 45 6789"), a digit and a space is not.
    ("ssn", re.compile(r"(?<!\d)(?<!\d )\d{3} \d{2} \d{4}(?!\d)(?! \d)"), "[SSN]"),
    ("health_plan", re.compile(r"(?i)(?<![A-Z0-9])[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d-?[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d-?[AC-HJKMNP-RT-Y]{2}\d{2}(?![A-Z0-9])"), "[HEALTH_PLAN_ID]"),
    ("account", re.compile(r"(?i)(?<![A-Z0-9])[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?(?![A-Z0-9])"), _iban),
    # Card-style numbers written in groups (contiguous ones fall to the long-number rule).
    ("account", re.compile(r"(?<![\d-])\d{4}([ -])\d{4}\1\d{4}\1\d{1,7}(?![\d-])"), "[ACCOUNT]"),
    ("account", re.compile(r"(?<![\d-])\d{4}([ -])\d{6}\1\d{4,5}(?![\d-])"), "[ACCOUNT]"),
    ("device", re.compile(r"\(01\)\d{14}(?:\(\d{2,4}\)[A-Za-z0-9-]+)*"), "[DEVICE_ID]"),
    ("vehicle", re.compile(r"(?i)(?<![A-Z0-9])(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-HJ-NPR-Z])[A-HJ-NPR-Z0-9]{17}(?![A-Z0-9])"), "[VEHICLE_ID]"),
    # Dates with a four-digit year keep the year only.
    ("date", re.compile(r"(?<![\d.])" + YEAR4 + r"[-/.]" + MON_NUM + r"[-/.]" + DAY + TIME + r"(?![\d])"), _year_of),
    ("date", re.compile(r"(?<![\d.])" + DAY + r"([-/.])" + DAY + r"\1" + YEAR4 + TIME + r"(?!\d)"), _year_of),
    ("date", re.compile(r"(?i)(?<![\w])" + DAY + r"(?:st|nd|rd|th)?[-\s/.]?(?:of\s+)?" + MONTH + r"\.?[-\s/.,]*" + YEAR4 + TIME + r"(?!\d)"), _year_of),
    ("date", re.compile(r"(?i)(?<![\w])" + MONTH + r"\.?[-\s]+" + DAY + r"(?:st|nd|rd|th)?,?[-\s]+" + YEAR4 + TIME + r"(?!\d)"), _year_of),
    ("date", re.compile(r"(?i)(?<!\d)" + YEAR4 + r"[-\s/.]" + MONTH + r"\.?[-\s/.]" + DAY + r"(?!\d)"), _year_of),
    ("date", re.compile(r"(?i)(?<![\w])" + MONTH + r"\.?[-\s/,]+" + YEAR4 + r"(?!\d)"), _year_of),
    ("date", re.compile(r"(?<![\d/.-])" + MON_NUM + r"[/-]" + YEAR4 + r"(?![\d/-])"), _year_of),
    ("date", re.compile(r"(?<![\d.])" + YEAR4 + r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?:T?\d{4,6})?(?![\d.])"), _year_of),
    # Month names of other languages, with a four-digit year ("14 mars 2021", "14. März 2021",
    # "15 de marzo de 2020", "März 2021").
    ("date", re.compile(r"(?i)(?<![\w])" + DAY + r"\.?\s*(?:de\s+)?" + FOREIGN_MONTH + r"\.?,?\s*(?:de\s+)?"
                        + YEAR4 + r"(?!\d)"), _year_of),
    ("date", re.compile(r"(?i)(?<![\w])" + FOREIGN_MONTH + r"\.?,?\s+(?:de\s+)?" + YEAR4 + r"(?!\d)"), _year_of),
    # A year and a month with no day ("2021-03", "2021/03", "2021-3", "2021 Mar", "2021-Mar"),
    # as a monthly export writes them. A year range ("2019-2021", "FY2019-20") is not one,
    # and "2021 may" in a sentence is a verb.
    ("date", re.compile(r"(?<![\w./-])(?P<y>" + YEAR4 + r")[-/](?P<m>" + MON_NUM + r")(?!\d)(?![-/.]\d)"),
     _year_and_month),
    ("date", re.compile(r"(?<![\w./-])" + YEAR4 + r"(?:(?:[-/.]\s*|\s+)(?:(?i:" + MONTH_NOT_MAY + r")|May)"
                        r"|[-/.]\s*(?i:may))\b\.?"), _year_of),
    # Dates without a four-digit year cannot be reduced to one.
    ("date", re.compile(r"(?<![\d/.-])" + DAY + r"([-/.])" + DAY + r"\1\d{2}(?![\d/.-])"), "[DATE]"),
    ("date", re.compile(r"(?i)(?<![\w])" + DAY + r"[-/]" + MONTH + r"[-/]\d{2}(?!\d)"), "[DATE]"),
    ("date", re.compile(r"(?i)(?<![\w])" + DAY + r"(?:st|nd|rd|th)?\s+(?:of\s+)?" + MONTH_NOT_MAY + r"\b\.?"), "[DATE]"),
    ("date", re.compile(r"(?i)(?<![\w])" + MONTH_NOT_MAY + r"\.?\s+" + DAY + r"(?:st|nd|rd|th)?\b"), "[DATE]"),
    # Month/day without a year; "1/2" (a fraction) is left alone.
    ("date", re.compile(r"(?<![\d/.-])(?:(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])|(?:0?[1-9]|1[0-2])/(?:1[3-9]|2\d|3[01]))(?![\d/.-])"), "[DATE]"),
    # Day and month in the other orders, after a word that says a date follows: "seen
    # 14/3" (a day over 12 first), "on 03-14" or "on 14-03", "seen 14.3." (German).
    # Round 8: also with a hyphen or a dash and no leading zero when one number is over 12 ("seen 14-3").
    ("date", re.compile(r"(?i)\b(?P<label>" + DATE_CONTEXT + r")\s+(?P<v>(?:(?:1[3-9]|2\d|3[01])/(?:0?[1-9]|1[0-2])"
                        r"|(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])|(?:1[3-9]|2\d|3[01])[-\u2013](?:0?[1-9]|1[0-2])"
                        r"|(?:0?[1-9]|1[0-2])[-\u2013](?:1[3-9]|2\d|3[01]))(?![\d/.\u2013-])"
                        r"|(?:0?[1-9]|[12]\d|3[01])\.(?:0?[1-9]|1[0-2])\.(?!\d))" + NOT_A_DATE_AFTER),
     _keep_label("[DATE]")),
    # Telephone and fax numbers.
    ("phone", re.compile(r"(?i)\b(?:tel(?:ephone)?|phone|ph|fax|facsimile|cell|mobile|pager)\.?(?:\s*(?:no\.?|number|#))?\s*[:#]?\s*(?P<v>\+?[\d(][\d\s().-]{5,}\d)"), _keep_label("[PHONE]")),
    ("phone", re.compile(r"(?<![\w+])(?:\+1[\s.-]?|1[\s.-])?\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\w])"), "[PHONE]"),
    ("phone", re.compile(r"(?<![\w])\+\d{1,3}(?:[\s.-]?\(?\d{1,4}\)?){2,5}(?![\w])"), _phone_intl),
    # Geography smaller than a state.
    ("zip", re.compile(r"(?i)\b(?:zip(?:\s*code)?|postal\s*code|post\s*code)\s*[:#]?\s*(?P<v>\d{5}(?:-\d{4})?)(?!\d)"), _keep_label("[ZIP]")),
    ("zip", re.compile(r"\b(?P<st>" + US_STATES + r")\s+\d{5}(?:-\d{4})?(?![\d-])"), _state_zip),
    ("zip", re.compile(r"(?<![\d-])\d{5}-\d{4}(?![\d-])"), "[ZIP]"),
    ("address", re.compile(r"(?<![\w])\d{1,6}[A-Za-z]?\s+(?:[NSEW]\.?\s+)?(?:[A-Z0-9][A-Za-z0-9'.-]*\s+){1,4}(?i:" + STREET_SUFFIX + r")\.?(?![\w])(?:,?\s*(?i:apt|apartment|suite|ste|unit|fl|floor|#)\.?\s*#?\s*[A-Za-z0-9-]+)?"), "[ADDRESS]"),
    ("address", re.compile(r"(?i)\bp\.?\s*o\.?\s*box\s+\d+"), "[ADDRESS]"),
    ("address", re.compile(r"(?i)\b(?:address|addr|residence|resides|home\s+address)\s*[:=]\s*(?P<v>[^;|\n]{4,120})"), _keep_label("[ADDRESS]")),
    ("address", re.compile(r"\b[A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,2},\s*(?P<st>" + US_STATES + r")\b(?=\s+\[ZIP\]|\s*$|\s*[,;.])"), _city_state),
    # Names that text marks as names.
    ("name", re.compile(r"\b(?:Mr|Mrs|Ms|Mx|Miss|Dr|Prof)\.?\s+[A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){0,2}"), "[NAME]"),
    # The name may not be another label ("Patient Name: X" replaces X, not "Name").
    ("name", re.compile(r"(?i:\b" + NAME_LABELS + r")\s*[:=]?\s*(?!(?i:" + NAME_LABELS + r")\b)"
                        r"(?P<v>[A-Z][a-zA-Z'-]+(?:[\s,]+[A-Z][a-zA-Z'-]+){0,3})"), _labelled_name),
    # The same in a script without capital letters ("Dr. 박지훈", "Patient: 林子涵").
    ("name", re.compile(r"(?:\b(?:Mr|Mrs|Ms|Mx|Miss|Dr|Prof)\.?\s*|(?i:\b" + NAME_LABELS + r")\s*[:=]?\s*)"
                        r"(?P<v>" + CASELESS_CLASS + r"+(?:[\s\u30fb\u00b7]" + CASELESS_CLASS + r"+){0,2})"),
     _caseless_labelled_name),
    # Ages over 89 ("92 years old", "93 yo", "95 y", "95y"; "95 y/n" is not one).
    ("age", re.compile(r"(?i)\b(?:" + AGE_NUM + "|" + AGE_WORD + r")\s*-?\s*(?:years?(?:[\s-]*old)?|yrs?|y/o|y\.?o\.?|yo"
                       r"|y\.?(?![\w/]))(?![\w])"), _age90),
    # "(?![\d.+])" keeps "aged 90+" from matching again.
    ("age", re.compile(r"(?i)\b(?P<label>age[ds]?)\s*[:=]?\s*(?:" + AGE_NUM + r"(?![\d.+])|" + AGE_WORD + r"\b)"), _age_label),
    # "92F" or "92 M" at the start of a cell or after "a"/"an" ("a 92F with CHF"); a
    # temperature ("temp 98F") has neither.
    ("age", re.compile(r"(?:^\s*|(?<=\b[Aa] )|(?<=\b[Aa]n ))(?P<v>" + AGE_NUM + r")(?=\s?[MF](?![\w]))"), _keep_label("90+")),
    # "pt is 91", "she was 93", unless a unit follows ("he is 95 kg").
    ("age", re.compile(r"(?i)\b(?:pt|patient|he|she|who)\s+(?:is|was)\s+(?P<v>" + AGE_NUM + r")(?![\d.%+])"
                       r"(?!\s*(?:%|percent|kg|kgs|lbs?|pounds|cm|mm|mg|bpm|beats|mmhg|degrees|°)(?![a-z]))"),
     _keep_label("90+")),
    # "in her 90s", "in his late nineties"; "in the 90s" (a blood pressure or a saturation) is left alone.
    ("age", re.compile(r"(?i)\bin\s+(?:his|her|their)\s+(?P<v>(?:(?:early|mid|late)[\s-]+)?(?:9\d'?s|nineties|1\d\d'?s|hundreds))(?![\w])"),
     _keep_label("90+")),
    ("age", re.compile(r"(?i)\b(?:super)?(?:nonagenarian|centenarian)s?\b"), "[90_OR_OLDER]"),
    # Photographs and biometric templates.
    # Round 7: the path before a file name is bounded, so a long cell of slashes ("1/1/1/...") takes linear time.
    ("photo", re.compile(r"(?i)(?<![\w.-])[\w./\\~:-]{0,255}[\w-]\.(?:jpe?g|png|gif|bmp|tiff?|heic|heif|webp|dcm|dicom)(?![\w])"), "[IMAGE_FILE]"),
    ("biometric", re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{32,}(?![0-9a-f])"), "[BIOMETRIC_OR_CODE]"),
    ("biometric", re.compile(r"(?<![A-Za-z0-9+/=])(?=[A-Za-z0-9+/]*\d)(?=[A-Za-z0-9+/]*[A-Za-z])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])"), "[BIOMETRIC_OR_CODE]"),
    # Any other unique identifying number or code, also with thousands separators
    # ("274,365,867"), which a nine-digit number written as money would otherwise dodge.
    ("code", re.compile(r"(?<![\d.])\d{9,}(?![\d.])"), _long_number),
    ("code", re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3}){2,}(?![\d,]|\.\d)"),
     lambda m: "[ID]" if len(_digits(m.group(0))) >= 9 else None),
    ("code", re.compile(r"(?<![\w-])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+(?![\w-])|(?<![\w-])(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9]{6,}(?![\w-])"), _code),
]

# ================================================================ dates in any script (round 8)
# Letters that keep no accent to drop under NFKD (ø, æ, ı, ł, đ, œ, þ, ð), read as the letters they resemble.
LETTERS_WITHOUT_DECOMPOSITION = str.maketrans({"\u00f8": "o", "\u00d8": "O", "\u00e6": "ae", "\u00c6": "Ae",
                                               "\u0131": "i", "\u0142": "l", "\u0141": "L", "\u0111": "d",
                                               "\u0110": "D", "\u0153": "oe", "\u0152": "Oe",
                                               "\u00fe": "th", "\u00f0": "d"})
# One definition of a date, which cells and column names share. Round 8 found column names that held a
# full date written in Chinese, Japanese, Korean, Vietnamese or Malay (2019年3月14日, 2019년 3월 14일,
# 14 tháng 3 năm 2019, 14 Mac 2019, R1.5.1) copied verbatim to the output, because the column-name check
# read 年, 月 and 日 as ordinary column words and the cell patterns above read only Latin month names
# and ASCII digits. Rather than add those strings, the text is folded first (compatibility forms such as
# full-width digits and ㋿, every script's decimal digits written as ASCII, accents and vowel marks of
# Latin, Greek, Cyrillic, Arabic and Hebrew letters dropped), and one set of date grammars reads it:
# year, month and day markers (年 月 日 号, 년 월 일), Japanese eras (令和1年5月1日, 令和元年, R1.5.1,
# H31.4.30), Vietnamese tháng and năm, Chinese numerals (二〇一九年三月十四日), month names of 25
# languages in nine scripts beside a day or a year (14 Mac 2019, 14 марта 2019, 14 มีนาคม 2562), and
# numeric dates with a year of any calendar (2562-03-14, 1398/12/23, 2019. 3. 14.). The Scrubber
# replaces each date of two or more elements in kept text by its Gregorian year (or [DATE] when the
# calendar's year cannot be read as one), and the column-name check refuses a column name that holds one
# and withholds a column name holding a month or a day alone (3月, 3월, tháng 3, 14日).
_DATE_MARKS = re.compile("[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f"
                         "\u0591-\u05c7\u064b-\u065f\u0670\u093c]")


def _date_fold_char(c: str) -> str:
    o = ord(c)
    if 0xAC00 <= o <= 0xD7A3 or 0x3040 <= o <= 0x30FF:
        return c  # Hangul syllables and kana keep their form (NFKD would split them)
    out = []
    for d in unicodedata.normalize("NFKD", c):
        if unicodedata.category(d) == "Nd":
            out.append(str(unicodedata.digit(d)))
        elif not _DATE_MARKS.match(d):
            out.append(d)
    return "".join(out).translate(LETTERS_WITHOUT_DECOMPOSITION)


def fold_for_dates(text: str) -> tuple[str, list[int] | None]:
    """The text as the date grammars read it, and the position in `text` of each folded character
    (None when nothing changed, for ASCII text)."""
    if text.isascii():
        return text, None
    chars: list[str] = []
    index: list[int] = []
    for i, c in enumerate(text):
        for ch in (c if c.isascii() else _date_fold_char(c)):
            chars.append(ch)
            index.append(i)
    return "".join(chars), index


# Month names, folded as above (accents and vowel marks dropped), one language a line, months in order
# and the spellings of a month separated by "/". English and the languages the patterns above read are
# here too, so a column name is read by one table.
_MONTH_NAME_LINES = """
january/jan|february/feb|march/mar|april/apr|may|june/jun|july/jul|august/aug|september/sept/sep|october/oct|november/nov|december/dec
janvier/janv|fevrier/fevr/fev|mars|avril/avr|mai|juin|juillet/juil|aout|septembre|octobre|novembre|decembre
januar/janner/jaenner|februar/feber|marz/maerz/mrz|april|mai|juni|juli|august|september|oktober/okt|november|dezember/dez
enero/ene|febrero|marzo|abril/abr|mayo|junio|julio|agosto/ago|septiembre/setiembre/set|octubre|noviembre|diciembre/dic
gennaio/gen|febbraio|marzo|aprile|maggio/mag|giugno/giu|luglio/lug|agosto|settembre|ottobre/ott|novembre|dicembre
janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro/out|novembro|dezembro
januari|februari|maart/mrt|april|mei|juni|juli|augustus|september|oktober|november|december
januari|februari|mac|april|mei|jun|julai|ogos/ogo|september|oktober|november|disember/dis
januari|februari|maret|april|mei|juni|juli|agustus/agu/ags/agt|september|oktober|november|desember/des
enero|pebrero|marso|abril|mayo|hunyo|hulyo|agosto|setyembre|oktubre|nobyembre|disyembre
ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik
styczen/stycznia/sty|luty/lutego/lut|marzec/marca|kwiecien/kwietnia/kwi|maj/maja|czerwiec/czerwca/cze|lipiec/lipca/lip|sierpien/sierpnia/sie|wrzesien/wrzesnia/wrz|pazdziernik/pazdziernika/paz|listopad/listopada/lis|grudzien/grudnia/gru
leden/ledna|unor/unora|brezen/brezna|duben/dubna|kveten/kvetna|cerven/cervna|cervenec/cervence|srpen/srpna|zari|rijen/rijna|listopad/listopadu|prosinec/prosince
januari/januar|februari/februar|mars/marts|april|maj|juni|juli|augusti/august|september|oktober|november|december/desember
tammikuu/tammikuuta|helmikuu/helmikuuta|maaliskuu/maaliskuuta|huhtikuu/huhtikuuta|toukokuu/toukokuuta|kesakuu/kesakuuta|heinakuu/heinakuuta|elokuu/elokuuta|syyskuu/syyskuuta|lokakuu/lokakuuta|marraskuu/marraskuuta|joulukuu/joulukuuta
januar|februar|marcius|aprilis|majus|junius|julius|augusztus|szeptember|oktober|november|december
ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie
январь/января/янв|февраль/февраля/фев|март/марта|апрель/апреля/апр|май/мая|июнь/июня/июн|июль/июля/июл|август/августа/авг|сентябрь/сентября/сен/сент|октябрь/октября/окт|ноябрь/ноября/ноя|декабрь/декабря/дек
січень/січня|лютий/лютого|березень/березня|квітень/квітня|травень/травня|червень/червня|липень/липня|серпень/серпня|вересень/вересня|жовтень/жовтня|листопад/листопада|грудень/грудня
ιανουαριος/ιανουαριου|φεβρουαριος/φεβρουαριου|μαρτιος/μαρτιου|απριλιος/απριλιου|μαιος/μαιου|ιουνιος/ιουνιου|ιουλιος/ιουλιου|αυγουστος/αυγουστου|σεπτεμβριος/σεπτεμβριου|οκτωβριος/οκτωβριου|νοεμβριος/νοεμβριου|δεκεμβριος/δεκεμβριου
يناير|فبراير|مارس|ابريل|مايو|يونيو/يونيه|يوليو/يوليه|اغسطس|سبتمبر|اكتوبر|نوفمبر|ديسمبر
كانون الثاني|شباط|اذار|نيسان|ايار|حزيران|تموز|اب|ايلول|تشرين الاول|تشرين الثاني|كانون الاول
ژانویه|فوریه|مارس|اوریل|مه|ژوئن|ژوئیه|اوت|سپتامبر|اکتبر|نوامبر|دسامبر
ינואר|פברואר|מרץ/מרס|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר
जनवरी|फरवरी|मार्च|अप्रैल/अप्रेल|मई|जून|जुलाई|अगस्त|सितंबर/सितम्बर|अक्टूबर/अक्तूबर|नवंबर/नवम्बर|दिसंबर/दिसम्बर
""".strip().splitlines()
# Thai months, whose years are Buddhist (2562 is 2019), and the Persian (Jalali) months, whose years are
# not read as Gregorian ones.
_THAI_MONTH_LINE = ("มกราคม/ม.ค.|กุมภาพันธ์/ก.พ.|มีนาคม/มี.ค.|เมษายน/เม.ย.|พฤษภาคม/พ.ค.|มิถุนายน/มิ.ย.|กรกฎาคม/ก.ค."
                    "|สิงหาคม/ส.ค.|กันยายน/ก.ย.|ตุลาคม/ต.ค.|พฤศจิกายน/พ.ย.|ธันวาคม/ธ.ค.")
_JALALI_MONTH_LINE = "فروردین|اردیبهشت|خرداد|تیر|مرداد/امرداد|شهریور|مهر|ابان|اذر|دی|بهمن|اسفند"


def _month_names() -> dict[str, tuple[int, str]]:
    """Each folded month name and its (month, calendar)."""
    out: dict[str, tuple[int, str]] = {}
    lines = [(line, "gregorian") for line in _MONTH_NAME_LINES] + [(_THAI_MONTH_LINE, "thai"),
                                                                    (_JALALI_MONTH_LINE, "jalali")]
    for line, calendar in lines:
        for month, names in enumerate(line.split("|"), start=1):
            for name in names.split("/"):
                folded = fold_for_dates(name)[0].casefold()
                if calendar == "gregorian" and any("\u0590" <= c <= "\u05ff" for c in folded):
                    for prefix in ("", "ב", "ל", "ב-"):  # Hebrew writes "in" before a month: 14 במרץ 2019
                        out.setdefault(prefix + folded, (month, calendar))
                    continue
                out.setdefault(folded, (month, calendar))
    return out


MONTH_NAMES = _month_names()
# A name of three letters or fewer (mar, mai, des, set, out, мая, מאי) is also an ordinary word or an
# abbreviation of one, and so is Mayo (a clinical score): it is a month only with both a day and a year
# beside it.
_WEAK_MONTH_NAMES = frozenset({"mayo"})
_MONTH_NAME_ALT = "|".join(re.escape(n) for n in sorted(MONTH_NAMES, key=len, reverse=True))
_CJK_NUMERAL = "[〇零一二三四五六七八九十廿卅]"
_CJK_DIGIT_VALUES = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_ERAS = {"明治": (1867, 45), "大正": (1911, 15), "昭和": (1925, 64), "平成": (1988, 31), "令和": (2018, None),
         "明": (1867, 45), "大": (1911, 15), "昭": (1925, 64), "平": (1988, 31), "令": (2018, None),
         "M": (1867, 45), "T": (1911, 15), "S": (1925, 64), "H": (1988, 31), "R": (2018, None)}
_VI_SPELLED_MONTHS = {"gieng": 1, "mot": 1, "hai": 2, "ba": 3, "tu": 4, "bon": 4, "nam": 5, "sau": 6, "bay": 7,
                      "tam": 8, "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12, "chap": 12}
_VI_MONTH = r"(?:\d{1,2}|muoi\s+(?:mot|hai)|gieng|chap|mot|hai|ba|tu|bon|nam|sau|bay|tam|chin|muoi)"
_NUM = r"(?:\d{1,4}|" + _CJK_NUMERAL + r"{1,4}|元)"
_LETTER_BEFORE = r"(?<![^\W\d_])"
_LETTER_AFTER = r"(?![^\W\d_])"
# Each grammar names the elements it holds: y (a year), m (a month), d (a day), era, mon (a month name),
# vm (a Vietnamese month) and cal (a calendar, for numeric years).
_DATE_GRAMMARS = [
    # Year, month and day markers: 2019年3月14日, 令和元年5月1日, 2019년 3월 14일, 二〇一九年三月十四日, 19年3月.
    re.compile(r"(?:(?P<era>明治|大正|昭和|平成|令和)\s*)?(?P<y>" + _NUM + r")\s*[年년]\s*(?P<m>\d{1,2}|"
               + _CJK_NUMERAL + r"{1,3})\s*[月월](?:\s*(?P<d>\d{1,2}|" + _CJK_NUMERAL + r"{1,3})\s*[日号號일])?"),
    # A month and a day: 3月14日, 3월 14일, 三月十四日.
    re.compile(r"(?<![\d年년])(?P<m>\d{1,2}|" + _CJK_NUMERAL + r"{1,3})\s*[月월]\s*(?P<d>\d{1,2}|" + _CJK_NUMERAL
               + r"{1,3})\s*[日号號일]"),
    # A Japanese era with separators: R1.5.1, H31/4/30, 令和1.5.1, 令和1-5, 平31.4.30 (a Latin era letter
    # only with a dot or a slash and all three parts, since S1-2-3 also names a sample).
    re.compile(r"(?<![A-Za-z0-9])(?P<era>[MTSHR])\s?(?P<y>\d{1,2})(?P<sep>[./])(?P<m>\d{1,2})(?P=sep)(?P<d>\d{1,2})"
               r"(?![\d])"),
    re.compile(r"(?P<era>明治|大正|昭和|平成|令和|[明大昭平令])\s*(?P<y>\d{1,2}|元)(?P<sep>[./-])(?P<m>\d{1,2})"
               r"(?:(?P=sep)(?P<d>\d{1,2}))?(?!\d)"),
    # Vietnamese: ngày 14 tháng 3 năm 2019, 14 tháng 3, 2019, tháng 3 năm 2019, tháng 3/2019, 14 thg 3.
    re.compile(r"(?i)(?:(?<![^\W\d_])ngay\s+)?(?<!\d)(?P<d>\d{1,2})\s+(?:thang|thg)\s+(?P<vm>" + _VI_MONTH
               + r")(?![^\W_])(?:\s*,?\s*(?:(?:nam|n)\s+)?(?P<y>\d{4})(?!\d)"
               r"|(?!\s*(?:tuan|ngay|gio|phut|lan|vien|lieu|tuoi)\b))"),
    re.compile(r"(?i)(?<!\d)(?<!\d\s)(?<![^\W\d_])(?:thang|thg)\s+(?P<vm>" + _VI_MONTH + r")\s*(?:[/-]|,?\s*nam)\s*"
               r"(?P<y>\d{4})(?!\d)"),
    # A month name beside a day, a year or both, in any of the languages above: 14 Mac 2019, 14hb Mac 2019,
    # 14. März 2019, 14 марта 2019 г., 14 במרץ 2019, 14 มีนาคม 2562, Mac 2019, Agustus 14, 2019. A Latin name
    # takes a separator before a number after it: SEPT9 and MARCH5 are gene symbols (withheld in a column name
    # as a month name, as round 5 withholds them).
    re.compile(r"(?i)(?<![\d.,/])(?P<d>\d{1,2})(?:\s*(?:\.|º|°|er|hb|-?(?:st|nd|rd|th)))?[\s\-/.]*"
               r"(?:(?:de|di|du|van|of)\s+)?" + _LETTER_BEFORE + r"(?P<mon>" + _MONTH_NAME_ALT + r")" + _LETTER_AFTER
               + r"\.?(?:[\s\-/.,]*(?:(?:de|del|di|of|พ\.ศ\.|ค\.ศ\.)\s*)?(?P<y>\d{4})(?!\d)" + TIME + ")?"),
    re.compile(r"(?i)" + _LETTER_BEFORE + r"(?P<mon>" + _MONTH_NAME_ALT + r")" + _LETTER_AFTER
               + r"(?:[\s\-/.,]+|(?<![A-Za-z]))(?:(?P<d>\d{1,2})(?!\d)(?:st|nd|rd|th)?[\s,\-/.]*)?"
               r"(?:(?:de|del|di|of|พ\.ศ\.|ค\.ศ\.)\s*)?(?P<y>\d{4})(?!\d)" + TIME),
    re.compile(r"(?i)" + _LETTER_BEFORE + r"(?P<mon>" + _MONTH_NAME_ALT + r")" + _LETTER_AFTER
               + r"(?:[\s.]+|(?<![A-Za-z]))(?P<d>\d{1,2})(?:st|nd|rd|th)?(?![\d.,:/])"),
    # Numeric dates of three parts whose year any calendar may write (2562-03-14, 1398/12/23, 14/03/2562,
    # 3/14/2562), and the Korean dotted form with spaces (2019. 3. 14.). A month and a year alone are read
    # only in Gregorian years, by the patterns above: 3.2019 and 1/1500 are also a decimal and a dilution.
    re.compile(r"(?<![\d./-])(?P<y>\d{4})(?P<sep>[./-]\s?)(?P<m>\d{1,2})(?P=sep)(?P<d>\d{1,2})\.?" + TIME + r"(?![\d])"),
    re.compile(r"(?<![\d./-])(?P<d>\d{1,2})(?P<sep>[./-])(?P<m>\d{1,2})(?P=sep)(?P<y>\d{4})" + TIME + r"(?![\d])"),
]
# A month or a day alone, which a column name may not hold either (round 8): 3月, 3월, tháng 3, 14日, 14일,
# a month name of another language as a word of its own. A number of months or days (3个月, 3ヶ月,
# 3개월, 3 tháng, 7日間, 14일째, 第14日) is a duration or a study day, not a date element.
_DATE_PART_GRAMMARS = [
    ("m", re.compile(r"(?<![\d年년第])(?P<m>\d{1,2}|" + _CJK_NUMERAL + r"{1,3})\s*[月월](?![龄齢齡]|[日号號일])")),
    ("d", re.compile(r"(?<![\d月월第])(?P<d>\d{1,2}|" + _CJK_NUMERAL + r"{1,3})\s*[日일]"
                     r"(?![目間间째간차후後后前전內内이龄齢齡量回次\d])")),
    ("m", re.compile(r"(?i)(?<!\d)(?<!\d\s)(?<![^\W\d_])(?:thang|thg)\s+(?P<vm>" + _VI_MONTH + r")(?![^\W_])")),
    ("m", re.compile(r"(?i)" + _LETTER_BEFORE + r"(?P<mon>" + _MONTH_NAME_ALT + r")" + _LETTER_AFTER)),
]


def _cjk_number(s: str) -> int | None:
    """1 to 9999 written with digits, with Chinese numerals (三, 十四, 二十一, 廿一, 二〇一九) or 元 (the
    first year of an era)."""
    if s.isdigit():
        return int(s)
    if s == "元":
        return 1
    if s and all(c in _CJK_DIGIT_VALUES for c in s):
        return int("".join(str(_CJK_DIGIT_VALUES[c]) for c in s)) if len(s) > 1 else _CJK_DIGIT_VALUES[s]
    s = s.replace("廿", "二十").replace("卅", "三十")
    m = re.fullmatch(r"([一二三四五六七八九])?十([一二三四五六七八九])?", s)
    if m:
        return (_CJK_DIGIT_VALUES[m.group(1)] if m.group(1) else 1) * 10 + (_CJK_DIGIT_VALUES[m.group(2)]
                                                                             if m.group(2) else 0)
    return None


class DateHit:
    """A date found in a text: its span in the original text, its elements and its Gregorian year (None when
    it has no year, or a year of a calendar this script does not convert)."""

    def __init__(self, start: int, end: int, text: str, elements: int, year: int | None):
        self.start, self.end, self.text, self.elements, self.year = start, end, text, elements, year

    def group(self, _index: int = 0) -> str:
        return self.text


def _hit_elements(m: re.Match, reference_year: int) -> tuple[int, int | None] | None:
    """(number of elements, Gregorian year) of a grammar match that is a valid date, else None."""
    g = m.groupdict()
    month = day = year = None
    calendar = "gregorian"
    if g.get("mon"):
        name = g["mon"].casefold()
        if name not in MONTH_NAMES:
            return None
        month, calendar = MONTH_NAMES[name]
    elif g.get("vm"):
        vm = re.sub(r"\s+", " ", g["vm"].lower())
        month = int(vm) if vm.isdigit() else _VI_SPELLED_MONTHS.get(vm)
    elif g.get("m"):
        month = _cjk_number(g["m"])
    if g.get("d"):
        day = _cjk_number(g["d"])
    if g.get("sep") is not None and month is not None and day is not None and not 1 <= month <= 12 \
            and 1 <= day <= 12:
        month, day = day, month  # a numeric date in the other order (3/14/2562)
    if month is None or not 1 <= month <= 12 or (day is not None and not 1 <= day <= 31):
        return None
    era = g.get("era")
    raw_year = g.get("y")
    if raw_year:
        n = _cjk_number(raw_year)
        if n is None:
            return None
        if era:
            start, last = _ERAS[era]
            if not 1 <= n <= (last if last is not None else reference_year - start):
                return None
            if len(era) == 1 and not era.isascii() and day is None:
                return None  # 大, 平, ... alone are words: a single-character era needs a day
            year = start + n
        elif (raw_year.isdigit() and len(raw_year) not in (2, 4)) or (not raw_year.isdigit() and len(raw_year) != 4):
            return None  # a number of years (3年3月), not a year
        elif calendar == "thai" and 2343 <= n <= reference_year + 553:
            year = n - 543  # a Buddhist year
        elif calendar != "jalali" and len(raw_year) == 4 and 1800 <= n <= reference_year + 10:
            year = n
        elif len(raw_year) == 4 and not 1300 <= n <= 2999:
            return None  # not a year of any calendar this script reads
    elif era:
        return None
    if g.get("mon") and (len(g["mon"]) <= 3 or g["mon"].casefold() in _WEAK_MONTH_NAMES) and not (day and raw_year):
        return None  # a short name is a month only with a day and a year beside it
    return 1 + (day is not None) + bool(raw_year), year


def find_dates(text: str, reference_year: int, parts: bool = False) -> list[DateHit]:
    """The dates written in `text` (see above), longest first where two overlap. With `parts`, a month or a
    day alone is returned too, as a hit of one element."""
    s = str(text)
    if not s or not any(c.isdigit() or "\u3007" <= c <= "\u9fff" or c in "元" for c in s) and not parts:
        return []
    folded, index = fold_for_dates(s)
    found: list[tuple[int, int, int, int | None]] = []
    for rx in _DATE_GRAMMARS:
        for m in rx.finditer(folded):
            got = _hit_elements(m, reference_year)
            if got and got[0] >= 2:
                found.append((m.start(), m.end(), got[0], got[1]))
    if parts:
        for kind, rx in _DATE_PART_GRAMMARS:
            for m in rx.finditer(folded):
                g = m.groupdict()
                if g.get("mon"):
                    name = g["mon"].casefold()
                    if name not in MONTH_NAMES or len(name) <= 3 or name in _WEAK_MONTH_NAMES:
                        continue
                elif g.get("vm"):
                    vm = re.sub(r"\s+", " ", g["vm"].lower())
                    if not 1 <= (int(vm) if vm.isdigit() else _VI_SPELLED_MONTHS.get(vm, 0)) <= 12:
                        continue
                else:
                    n = _cjk_number(g.get("m") or g.get("d") or "")
                    if n is None or not 1 <= n <= (12 if kind == "m" else 31):
                        continue
                found.append((m.start(), m.end(), 1, None))
    found.sort(key=lambda h: (h[0], -(h[1] - h[0]), -h[2]))
    hits: list[DateHit] = []
    end = -1
    for a, b, elements, year in found:
        if a < end:
            continue
        end = b
        if index is None:
            start, stop = a, b
        else:
            start, stop = index[a], index[b - 1] + 1
            while stop < len(s) and not _date_fold_char(s[stop]):
                stop += 1  # a mark the fold dropped belongs to the letter before it
        hits.append(DateHit(start, stop, s[start:stop], elements, year))
    return hits


class DatesInAnyScript:
    """The date grammars above as an entry of the Scrubber's patterns: it has the `sub` of a compiled pattern,
    and replaces each date of two or more elements by its Gregorian year, capped like every other year, or
    by [DATE] when it has none."""

    def __init__(self, reference_year: int):
        self.reference_year = reference_year

    def sub(self, repl, text: str) -> str:
        hits = find_dates(text, self.reference_year)
        if not hits:
            return text
        out, last = [], 0
        for h in hits:
            out.append(text[last:h.start])
            out.append(repl(h))
            last = h.end
        out.append(text[last:])
        return "".join(out)

    def replacement(self, hit: DateHit) -> str:
        return cap_old_year(str(hit.year), self.reference_year) if hit.year else "[DATE]"


def locale_patterns(locale: dict) -> list[tuple[str, re.Pattern, object]]:
    """National ID, IBAN, phone and postcode patterns of a deidentify.py locale pack."""
    out: list[tuple[str, re.Pattern, object]] = []
    for pat in (locale.get("national_id") or {}).get("patterns", []):
        out.append(("national_id", re.compile(pat, re.IGNORECASE), "[ID]"))
    for pat in (locale.get("iban") or {}).get("patterns", []):
        out.append(("account", re.compile(pat, re.IGNORECASE), "[ACCOUNT]"))
    for phone in locale.get("phone", []):
        if phone.get("pattern"):
            out.append(("phone", re.compile(phone["pattern"]), "[PHONE]"))
    post = (locale.get("address") or {}).get("postcode_pattern")
    if post:
        out.append(("zip", re.compile(post, re.IGNORECASE), "[ZIP]"))
    return out


class Scrubber:
    """Finds and replaces identifier patterns inside one cell."""

    def __init__(self, locale: dict, reference_year: int | None = None):
        year = reference_year if reference_year is not None else date.today().year
        self.reference_year = year
        # A date of 90 or more years ago keeps no year: as a birth date it reveals an age over
        # 89, and a date that old in a clinical table is almost always one (DOB 1925-03-14).
        patterns = [(kind, rx, _capped_year(repl, year) if repl in (_year_of, _year_and_month) else repl)
                    for kind, rx, repl in PATTERNS]
        # The year after "born" or "DOB" is judged once full dates have become years.
        at = next(i for i, (kind, _, _) in enumerate(patterns) if kind == "phone")
        # Round 8: dates in any script and calendar (see DatesInAnyScript) are read before the date patterns
        # above, so a day before a month name ("1hb Mei 2019") is not left behind when they take the rest.
        first_date = next(i for i, (kind, _, _) in enumerate(patterns) if kind == "date")
        dates = DatesInAnyScript(year)
        self.patterns = (patterns[:first_date] + [("date", dates, dates.replacement)] + patterns[first_date:at]
                         + [birth_year_pattern(year)] + patterns[at:] + locale_patterns(locale))

    def scrub(self, text: str) -> tuple[str, list[str]]:
        """The text with every identifier pattern replaced, and the types replaced."""
        found: list[str] = []
        if not text or not text.strip():
            return text, found
        if NUMBER.fullmatch(text.strip()):
            return self._scrub_number(text, found)
        out = text
        for _ in range(3):  # a replacement never creates a new match, but check
            before = out
            for kind, rx, repl in self.patterns:
                out = self._apply(rx, repl, out, kind, found)
            if out == before:
                break
        return out, found

    @staticmethod
    def _apply(rx, repl, text, kind, found):
        def sub(m: re.Match) -> str:
            if PLACEHOLDER.fullmatch(m.group(0)):
                return m.group(0)
            new = repl(m) if callable(repl) else repl
            if new is None or new == m.group(0):
                return m.group(0)
            found.append(kind)
            return new
        return rx.sub(sub, text)

    def _scrub_number(self, text: str, found: list[str]) -> tuple[str, list[str]]:
        """A plain number is a measurement, except a compact date, a telephone number
        in international form (+14155550134) or a long ID."""
        s = text.strip()
        if re.fullmatch(YEAR4 + r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])", s):
            found.append("date")
            return cap_old_year(s[:4], self.reference_year), found
        if re.fullmatch(r"\+\d{8,15}", s):
            found.append("phone")
            return "[PHONE]", found
        if re.fullmatch(r"[+-]?\d{9,}", s):
            found.append("code")
            return "[ID]", found
        return text, found

    def find(self, text: str) -> list[str]:
        return self.scrub(text)[1]


# ================================================================ columns


def column_tokens(header: str) -> list[str]:
    # Accents are dropped first, so "Médecin" and "Ärztin" are read as medecin and arztin
    # rather than split at the accented letter.
    s = "".join(c for c in unicodedata.normalize("NFKD", str(header)) if not unicodedata.combining(c))
    # Letters NFKD does not take apart ("Fødselsdato", "Yıl", "Płeć", "Ærø").
    s = s.replace("\u00df", "ss").translate(LETTERS_WITHOUT_DECOMPOSITION)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    toks = [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]
    out = []
    for t in toks:
        stripped = re.sub(r"\d+$", "", t)
        out.append(stripped or t)
    return out


def _has(tokens: list[str], *terms: str) -> bool:
    """True when any term (words joined by spaces) appears as consecutive tokens,
    or as one token written without separators."""
    joined = set(tokens)
    for term in terms:
        words = term.split()
        n = len(words)
        if any(tokens[i:i + n] == words for i in range(len(tokens) - n + 1)):
            return True
        if n > 1 and "".join(words) in joined:
            return True
    return False


# Words that make "name" something other than a person's name.
NOT_A_PERSON_NAME = {
    "drug", "medication", "med", "meds", "test", "lab", "component", "procedure", "proc",
    "gene", "protein", "file", "product", "brand", "generic", "hospital", "facility",
    "clinic", "department", "dept", "unit", "ward", "site", "study", "trial", "specimen",
    "sample", "organism", "variable", "column", "field", "item", "measure", "panel",
    "order", "diagnosis", "dx", "code", "vaccine", "allergen", "payer", "plan", "loinc",
    "concept", "icd", "cpt", "snomed", "rxnorm", "ndc", "analyte", "assay", "result",
    "instrument", "batch", "run", "plate", "well", "region", "country", "state", "location",
    "room", "bed", "service", "program", "project", "form", "question", "visit", "event",
    "pathogen", "antibiotic", "condition", "disease", "problem", "device", "implant",
    "medicamento", "farmaco", "medicament", "medikament", "prueba", "examen", "diagnostico",
    "diagnostic", "diagnose", "hopital", "krankenhaus", "ospedale", "clinica", "clinique",
    "klinik", "servicio", "unidad", "unite", "centro", "estudio", "etude", "studie", "studio",
    "producto", "produit", "produkt", "prodotto", "archivo", "fichier", "datei", "enfermedad",
    "maladie", "krankheit", "malattia", "procedimiento", "procedure", "laboratorio", "labor",
}
# Words that make "id" something other than a person's or a record's identifier.
NOT_A_PERSON_ID = {
    "drug", "medication", "med", "test", "lab", "component", "procedure", "proc", "gene",
    "protein", "product", "brand", "hospital", "facility", "clinic", "department", "dept",
    "unit", "ward", "site", "study", "trial", "organism", "variable", "column", "field",
    "item", "measure", "panel", "diagnosis", "dx", "code", "vaccine", "allergen", "payer",
    "plan", "loinc", "concept", "icd", "cpt", "snomed", "rxnorm", "ndc", "analyte", "assay",
    "instrument", "batch", "run", "plate", "well", "region", "country", "state", "program",
    "project", "form", "question", "file", "pathogen", "antibiotic", "condition", "disease",
    "ensembl", "entrez", "hgnc", "uniprot", "refseq", "transcript", "snp", "rsid", "dbsnp",
    "probe", "probeset", "pathway", "kegg", "reactome", "pubchem", "chembl", "omim", "mesh",
}
DATE_WORDS = ("date", "dt", "datetime", "timestamp", "dob", "dod", "birthdate", "birthday",
              "date of birth", "date of death", "deathdate")
DATE_TIME_CONTEXT = {"admit", "admission", "admitted", "discharge", "discharged", "death",
                     "birth", "visit", "arrival", "encounter", "collection", "collected",
                     "specimen", "order", "result", "service", "procedure", "surgery",
                     "registration", "appointment", "scan", "exam"}
INTERVAL_WORDS = {"days", "day", "weeks", "week", "months", "month", "years", "hours", "hrs",
                  "minutes", "mins", "duration", "interval", "since", "to", "until", "los",
                  "length", "delta", "diff", "difference", "elapsed", "lag", "count", "n"}
RELATIVE_WORDS = {"spouse", "mother", "father", "parent", "guardian", "kin", "nok", "relative",
                  "caregiver", "household", "emergency", "sibling", "child", "husband", "wife",
                  "partner", "contact"}
CLINICIAN_WORDS = {"provider", "physician", "doctor", "attending", "nurse", "clinician",
                   "referring", "author", "signer", "surgeon", "pcp", "staff", "resident"}
# Birth-year columns written as one word.
BIRTH_YEAR_TOKENS = {"byear", "byr", "yob", "birthyear", "birthyr", "yrbirth", "yearbirth",
                     "yearborn", "bornyear", "yrborn", "bornyr", "yearofbirth"}
YEAR_TOKENS = {"year", "yr", "yrs", "yyyy", "y"}
# "birth" or "born" with one of these is a place, which is geography smaller than a state.
BIRTH_PLACE_WORDS = {"place", "city", "town", "village", "county", "location", "municipality",
                     "address", "zip", "zipcode", "postcode", "birthplace", "lugar", "lieu", "luogo",
                     "local", "ort", "ciudad", "ville", "citta", "cidade", "stadt", "tempat", "yeri",
                     "noi", "plaats", "sted", "ort"}
# "birth" with one of these describes the birth, not its date.
BIRTH_NOT_A_DATE = {"weight", "wt", "length", "len", "height", "order", "rank", "plurality",
                    "outcome", "outcomes", "type", "defect", "defects", "control", "rate",
                    "rates", "count", "counts", "cohort", "mode", "method", "gestation",
                    "gestational", "ga", "injury", "trauma", "asphyxia", "attendant",
                    "certificate", "cert", "hospital", "facility", "sex", "gender", "parity",
                    "spacing", "interval", "complication", "complications", "history", "hx",
                    "status", "season", "circumference", "head", "apgar", "presentation",
                    "route", "delivery", "multiple", "twin", "singleton", "registry", "anomaly",
                    "anomalies", "country", "state", "province", "nationality", "cohort", "pais",
                    "pays", "paese", "land", "estado", "staat", "peso", "gewicht", "poids", "talla",
                    "laenge", "orden", "rang", "tipo", "typ", "sexo", "geschlecht", "sexe", "sesso"}
# One-word age columns: ageyrs, agegroup, ageatdx, ...
AGE_TOKEN = re.compile(r"age(?:s|d|yrs?|years?|yo|y|mos?|months?|wks?|weeks?|days?|hrs?|hours?"
                       r"|grp|groups?|cats?|category|categories|bands?|bins?|ranges?|class"
                       r"|brackets?|buckets?|at[a-z]*|dx|adm|onset|death|enrol+|baseline|bl)?")


def _is_age_token(token: str) -> bool:
    return bool(AGE_TOKEN.fullmatch(token))


# "Age" in other languages. These words mean age wherever they stand in a column name
# ("Edad al diagnostico", "Idade (anos)", "Alter bei Diagnose", "Ålder vid diagnos", "Věk
# (roky)"). "Alter" and "alder" are English words too, but hardly in a column name. Words for
# age that have a common other meaning ("Kor" in Hungarian; "Eta" in Italian, which is also an
# arrival time) is not here: its numbers are judged by number_rule like any column's. "Kor"
# (Hungarian) was left out for the same reason until round 3, when decimal ages under it passed.
AGE_WORDS_OTHER_LANGUAGES = frozenset({"edad", "idade", "leeftijd", "wiek", "umur", "usia", "tuoi",
                                       "eletkor", "varsta", "lebensalter", "levensjaar", "alter", "alder",
                                       "yas", "vek", "ika", "starost", "edat", "edats", "kor", "vanus",
                                       "amzius", "vecums", "yasi", "yasinda", "ageing", "aging"})
# German and Scandinavian compounds of the word ("Patientenalter", "Aufnahmealter", "Alters",
# "Altersgruppe", "Aldersgruppe").
NOT_AGE_COMPOUNDS = frozenset({"falter", "halter", "psalter", "salter", "walter", "alderman", "alderney",
                               "alderson", "alderton", "alderwood", "alderbrook", "aldershot"})
# Units an age is counted in, among the column-name tokens ("Years Old", "Months Old", "Alter
# (Monate)").
AGE_UNIT_WORDS = frozenset({"year", "years", "yr", "yrs", "month", "months", "mo", "mos", "week", "weeks",
                            "wk", "wks", "day", "days", "hours", "hrs", "jahre", "jahren", "monate",
                            "monaten", "monat", "wochen", "tage", "tagen", "anos", "meses", "semanas",
                            "dias", "ans", "mois", "semaines", "jours", "anni", "mesi", "settimane",
                            "giorni", "jaar", "maanden", "weken", "dagen", "ar", "manader", "veckor",
                            "dagar", "roky", "mesice", "dny"})
# Words for years: a column named for them holding numbers over 89 holds ages (value_shape_rule).
YEAR_WORDS_OTHER_LANGUAGES = frozenset({"jahre", "jahren", "anni", "anos", "ans", "annees", "jaar",
                                        "jaren", "roky", "rokov", "let", "lata", "vuotta", "yil", "ev",
                                        "evek", "godina", "godine", "yillar"})
# The same in scripts the column-name tokens do not read: Chinese, Japanese and Korean words
# are found inside a name, words of other scripts as whole words.
AGE_WORDS_CJK = ("年龄", "年齡", "年齢", "年纪", "年紀", "岁", "歲", "나이", "연령", "연세")
AGE_WORDS_OTHER_SCRIPTS = frozenset({"возраст", "возраста", "вік", "віку", "عمر", "العمر", "السن", "سن",
                                     "גיל", "आयु", "उम्र", "อายุ", "ηλικία", "ηλικια", "বয়স", "বয়স",
                                     "வயது", "వయస్సు", "ವಯಸ್ಸು", "വയസ്സ്", "ਉਮਰ", "ઉંમર", "वय", "ასაკი",
                                     "տարիք", "жас"})


def _age_word_token(t: str) -> bool:
    """One column-name token that says age: a word of AGE_WORDS_OTHER_LANGUAGES, or a German or
    Scandinavian compound of one ("patientenalter", "alters", "aldersgruppe")."""
    if t in AGE_WORDS_OTHER_LANGUAGES:
        return True
    if t in NOT_AGE_COMPOUNDS:
        return False
    return (len(t) > 5 and t.endswith("alter")) or t.startswith(("alters", "aldersg", "alderen"))


def age_in_other_language(header: str, tokens: list[str]) -> bool:
    """True for a column name that says age in a language other than English or French
    ("Edad", "Alter bei Diagnose", "Patientenalter", "Idade", "年龄", "年纪", "나이", "연세",
    "Возраст", "العمر", "বয়স"), or that names an age by its unit ("Years Old", "Months Old")."""
    if any(_age_word_token(t) for t in tokens):
        return True
    if "old" in tokens and set(tokens) & AGE_UNIT_WORDS:
        return True
    raw = unicodedata.normalize("NFKC", str(header)).casefold()
    if "eta" in tokens and ("età" in raw or set(tokens) & {"anni", "paziente"}):
        return True
    if any(w in raw for w in AGE_WORDS_CJK):
        return True
    return bool(set(re.split(r"[\s_\-/,;:()\[\].]+", raw)) & AGE_WORDS_OTHER_SCRIPTS)


# Words that name a person or a role wherever they stand in a column name ("Treatment
# Physician", "Lab Technician", "Physician (Treatment)"). They make a name column a column of
# a clinician's or another person's name (name_rule), and under such a column name only the
# missing-value words of the vocabulary count as verified (ColumnContext).
PERSON_ROLE_WORDS = frozenset("""
physician doctor md surgeon nurse rn np clinician provider practitioner attending hospitalist
intern fellow technologist midwife midwives pcp author signer cosigner signatory witness
chaperone interpreter translator scribe courier investigator coordinator administrator manager
supervisor director mentor leader reporter collector recorder rater reviewer scorer grader
assessor evaluator examiner observer interviewer abstractor annotator adjudicator auditor
referrer requester requestor submitter enterer caller spouse husband wife wives mother father
parent guardian caregiver carer sibling brother sister son daughter kin nok friend neighbor
neighbour roommate informant respondent proband decedent enrollee enrolee interviewee employee
employer volunteer trainee teacher counselor counsellor chaplain navigator advocate guarantor
policyholder visitor customer captain president deputy liaison steward assistant aide clerk
secretary matron orderly porter registrar prescriber performer operator inspector attendant
consultant dietitian paramedic medic emt doula nanny sitter babysitter cousin aunt uncle niece
nephew grandparent grandmother grandfather stepparent stepmother stepfather godparent fiance
girlfriend boyfriend housemate flatmate classmate coworker colleague boss foreman chairman
chairperson spokesperson salesperson tenant landlord landlady lodger trustee executor heir
custodian analyst bystander facilitator recruiter coder escort victim champion handler
dispatcher perpetrator moderator instructor tutor educator worker staff officer
professor attorney lawyer solicitor notary paralegal pastor priest rabbi imam clergy minister
reverend reader verifier approver authorizer authoriser scheduler biller validator certifier
endorser preparer transcriber releaser organizer organiser greeter companion accompanist
responsable responsabile verantwortlicher
medico medica medici medecin medecins docteur doctora dottore dottoressa arzt arztin aerztin
arzte aerzte enfermera enfermero infirmiere infirmier krankenschwester pfleger pflegerin
infermiere infermiera cirujano cirujana chirurgien chirurgienne chirurg lakare laege lekarz
pielegniarka verpleegkundige huisarts madre padre mere pere mutter vater esposa esposo conjoint
conjointe ehemann ehefrau marito moglie hijo hija fils fille sohn tochter figlio figlia hermano
hermana frere soeur bruder schwester cuidador cuidadora aidant aidante betreuer betreuerin
tutora acompanante accompagnateur accompagnatrice begleiter begleiterin
""".split())
# Words that name a person only as the head of the column name, its last word ("Dept
# Head", "Source Contact", "Event Patient", "Cohort Member", "Visit Dr", "Group Prof").
# Before a category word they say whose category it is ("Head Injury Type", "Contact
# Method", "Patient Diagnosis"). Words with a common other meaning ("Doc" for document,
# "Admin" for administration, "Charge", "Family") are not on the list; their values are
# verified like any other column's (verify_column).
HEAD_ROLE_WORDS = frozenset("""
patient pt subject participant member individual person people client resident contact head
lead chief chair principal pi owner holder donor recipient tech user consumer partner
relative child children student monitor sponsor sender receiver surrogate proxy
representative rep delegate driver survivor
dr drs prof profs emergency responsible party parties team teams paciente patiente paziente
patientin sujet sujeto soggetto participante partecipante teilnehmer teilnehmerin persona
personne kontakt contacto contatto
""".split())
# Words ending in -er or -or that name a thing rather than a person, so a column name ending
# in one ("Tumor Marker", "Visit Number", "Risk Factor") is not read as a role (_agent_noun).
NOT_AGENT_NOUNS = frozenset("""
number order marker biomarker tumor tumour center centre cancer disorder factor receptor
inhibitor blocker booster letter paper other under over upper lower inner outer later never
ever either neither whether weather water fever liver bladder gallbladder ulcer filter cluster
quarter trimester semester meter metre liter litre parameter diameter chamber power tower
folder character matter chapter corner border shoulder finger master register color colour
floor door error vector sector sensor motor major minor junior senior prior anterior posterior
interior exterior superior inferior behavior behaviour humor humour tremor labor labour flavor
flavour favor honor vapor rumor terror mirror horror calculator ventilator generator indicator
denominator numerator accelerator regulator modulator stimulator activator pacemaker container
carrier noncarrier barrier enhancer promoter transporter fiber fibre primer polymer timer spacer
inhaler nebulizer nebuliser catheter laser counter encounter computer printer scanner trigger
cover answer dinner winter summer september october november december hunger danger anger
murmur manner banner roster foster shelter butter theater theatre oximeter glucometer
spirometer thermometer barometer monomer dimer isomer buffer freezer heater cooler shower
flower smoker nonsmoker drinker nondrinker responder nonresponder layer transfer converter
adapter adaptor connector detector projector elevator radiator incubator oscillator inductor
capacitor resistor transistor processor compressor extractor injector applicator dilator
retractor separator simulator evaporator insulator refrigerator predictor descriptor precursor
cursor corridor meteor manor armor armour odor odour rigor pallor stupor liquor harbor harbour
arbor parlor tenor razor anchor decor vigor modifier identifier qualifier classifier multiplier
amplifier humidifier purifier stratifier tracker reminder remainder header footer binder ledger
poster sticker pointer trailer cylinder powder plaster blister diaper charger holter cluster
higher older younger larger smaller greater fewer wider deeper longer shorter faster slower
better earlier lesser gender agender cisgender transgender genderqueer queer payer payor former
prefer titer titre zoster flutter khmer frontier ringers censor stressor tracer stapler defibrillator
oxygenator respirator concentrator aspirator insufflator analyzer analyser
""".split())
# Words that say a column holds places ("Visit Location", "Service Area", "Treatment Center",
# "Event Setting"): under such a column name only missing-value words count as verified.
PLACE_WORDS = frozenset("""
location locations loc locale locales place places area areas venue venues community
communities zone zones campus campuses setting settings site sites center centers centre
centres facility facilities clinic clinics hospital hospitals institution institutions office
offices branch branches station stations building buildings region regions territory
territories catchment destination origin lugar lieu luogo sitio sede ubicacion ubicazione
localizacion localizacao localisation emplacement standort
""".split())
# "-ist" and "-ee" words that are not people.
NOT_PERSON_IST = frozenset({"agonist", "antagonist", "assist", "resist", "insist", "consist", "persist", "subsist",
                            "desist", "exist", "twist", "wrist", "schist", "heist"})
NOT_PERSON_EE = frozenset({"degree", "committee", "pedigree", "coffee", "toffee", "guarantee",
                           "jubilee", "settee", "decree", "agree", "disagree", "carefree",
                           "marquee", "matinee", "filigree", "squeegee", "frisbee", "lychee",
                           "entree", "soiree", "goatee", "toupee", "levee", "banshee",
                           "chimpanzee", "fricassee", "dundee", "spondee", "trochee", "bootee"})


def _role_word(token: str, words: frozenset) -> bool:
    if token in words or (token.endswith("s") and token[:-1] in words):
        return True
    if words is PERSON_ROLE_WORDS:
        # Physician, technician; pharmacist, phlebotomist; sonographer; attendee, examinee.
        word = token[:-1] if token.endswith("s") else token
        if len(word) >= 7 and word.endswith("ician"):
            return True
        if len(word) >= 6 and word.endswith("ist") and not word.endswith("list") \
                and word not in NOT_PERSON_IST:
            return True
        if len(word) >= 9 and word.endswith("grapher"):
            return True
        if len(word) >= 6 and word.endswith("ee") and word not in NOT_PERSON_EE:
            return True
    return False


def _agent_noun(token: str) -> bool:
    """A word ending in -er or -or that names whoever does something (verifier, approver,
    scheduler, releaser, pastor), as opposed to a thing (marker, number, tumor)."""
    word = token[:-1] if token.endswith("s") and len(token) > 5 else token
    return (len(word) >= 5 and word.endswith(("er", "or")) and word not in NOT_AGENT_NOUNS
            and not word.endswith(("meter", "metre", "eter")))


# Phrases that name a person who signed or checked something ("Lab Sign-off").
SIGN_PHRASES = ("sign off", "signoff", "signed off", "sign out", "signout", "signed out",
                "countersigned", "co signed", "cosigned")
# "to" after one of these, or after any word ending in -ed, names a person ("Assigned To").
TO_VERBS = frozenset({"sent", "given", "told", "shown", "brought", "taken", "handed", "passed"})


def person_role_words(tokens: list[str], trailing: frozenset = frozenset()) -> set[str]:
    """The words of a column name that name a person or a role: one of PERSON_ROLE_WORDS
    anywhere, one of HEAD_ROLE_WORDS or a word ending in -er or -or that names whoever does
    something as the last word (numbers and `trailing` words such as "name" after it do not
    count), "by" or "with" after another word ("Test Ordered By", "Visit With"), "to" after
    a word such as "assigned" or "referred", and a sign-off ("Lab Sign-off")."""
    found = {t for t in tokens if _role_word(t, PERSON_ROLE_WORDS)}
    found.update(t for t in tokens[1:] if t in ("by", "with"))
    found.update("to" for a, b in zip(tokens, tokens[1:])
                 if b == "to" and (a.endswith("ed") or a in TO_VERBS))
    if _has(tokens, *SIGN_PHRASES):
        found.add("signature")
    rest = [t for t in tokens if not t.isdigit()]
    while rest and rest[-1] in trailing:
        rest.pop()
    if rest and (_role_word(rest[-1], HEAD_ROLE_WORDS) or _agent_noun(rest[-1])):
        found.add(rest[-1])
    return found


def place_words(tokens: list[str]) -> set[str]:
    """The words of a column name that say its values are places. "Site" in a body site
    ("Primary Site", "Biopsy Site") names a part of the body, not a place."""
    if _has(tokens, *CATEGORY_HEADER_PHRASES):
        tokens = [t for t in tokens if t not in ("site", "sites")]
    return {t for t in tokens if t in PLACE_WORDS}


# Words a person's own name column may carry ("Study Patient Name"), as opposed to the
# name of a clinician or another person ("Lab Technician Name").
SELF_WORDS = frozenset({"patient", "patients", "pt", "subject", "subjects", "participant",
                        "participants", "member", "members", "individual", "individuals",
                        "person", "people", "client", "clients", "resident", "residents",
                        "proband", "probands", "respondent", "respondents", "enrollee",
                        "enrolee", "decedent", "interviewee", "donor", "donors", "recipient",
                        "recipients", "family", "famille", "familia", "familie", "paciente",
                        "patiente", "paziente", "patientin", "sujet", "sujeto", "participante",
                        "teilnehmer", "persona", "personne"})
NAME_TRAILING = frozenset({"name", "names", "nm", "initials", "first", "last", "full", "given",
                           "surname", "surnames", "firstname", "lastname", "fullname"})


# "Birth" in other languages, as column-name tokens (accents already dropped).
BIRTH_WORDS_OTHER_LANGUAGES = frozenset({"natal", "natalicio", "geburt", "naissance", "nacimiento", "nasc",
                                         "nascimento", "nascita", "lahir", "dogum", "nacim", "nasci",
                                         "nacido", "nacida", "geboren", "fodsel", "fodt",
                                         "fodelse", "syntyma", "narozeni", "urodzenia", "szuletes"})
# Single tokens that are a birth date ("BDate" splits into b and date, "Geburtsdatum" does not).
BIRTH_DATE_TOKENS = frozenset({"bdate", "bdt", "bday", "geburtstag", "geburtsdatum", "gebdatum", "gebdat",
                               "gebdt", "fdn", "fnac", "fechanac", "fechanacimiento", "datanasc",
                               "datanascita", "fodselsdato", "fodelsedatum", "syntymaaika",
                               "syntymapaiva", "geboortedatum", "dob", "ddn", "dnasc"})
BIRTH_DATE_WORDS = frozenset({"date", "dt", "fecha", "fec", "fe", "f", "data", "datum", "dato", "tarihi",
                              "tanggal", "ngay", "dia", "giorno", "jour", "tag"})
BIRTH_YEAR_WORDS = frozenset({"jahr", "ano", "anos", "anno", "annee", "tahun", "nam", "yili", "rok",
                              "roku", "aar", "ar", "vuosi"})
# Birth dates, birth years and places of birth in scripts the column-name tokens do not read.
BIRTH_DATE_PHRASES = ("出生日期", "出生日", "出生年月日", "生年月日", "誕生日", "生日", "생년월일", "출생일",
                      "생일", "дата рождения", "день рождения", "дата народження", "تاريخ الميلاد",
                      "تاريخ الولادة", "תאריך לידה", "जन्मतिथि", "जन्म तिथि", "जन्म दिनांक", "जन्मदिन",
                      "วันเกิด", "วันเดือนปีเกิด", "ημερομηνία γέννησης", "ημερομηνια γεννησης")
BIRTH_YEAR_PHRASES = ("出生年", "出生年份", "生年", "출생연도", "출생년도", "출생년", "год рождения",
                      "سنة الميلاد", "שנת לידה", "जन्म वर्ष", "ปีเกิด", "έτος γέννησης")
BIRTH_PLACE_PHRASES = ("出生地", "出身地", "籍贯", "출생지", "место рождения", "مكان الميلاد", "מקום לידה",
                       "जन्मस्थान", "जन्म स्थान", "สถานที่เกิด", "τόπος γέννησης")
BIRTH_SHORT_TOKENS = frozenset({"др", "д.р", "д р"})


def birth_in_other_script(header: str, tokens: list[str]) -> tuple[str, str, str] | None:
    """A birth date, a birth year or a place of birth named in a script the column-name tokens
    do not read ("出生日期", "생년월일", "Дата рождения", "ДР", "تاريخ الميلاد", "תאריך לידה")."""
    raw = " ".join(unicodedata.normalize("NFKC", str(header)).casefold().replace("_", " ").split())
    words = set(re.split(r"[\s/,;:()\[\]]+", raw))
    if any(p in raw for p in BIRTH_PLACE_PHRASES):
        return ("place of birth", "redact", "address")
    if any(p in raw for p in BIRTH_DATE_PHRASES) or words & BIRTH_SHORT_TOKENS:
        return ("date of birth", "birth_date", "date")
    if any(p in raw for p in BIRTH_YEAR_PHRASES):
        return ("year of birth", "birth_year", "date")
    return None


# "Name" in scripts the column-name tokens do not read. These are a person's name wherever they
# stand ("患者姓名", "母亲姓名"): 姓 is a surname, and 성명 and 성함 are said only of people.
SCRIPT_NAME_ANYWHERE = ("姓名", "氏名", "성명", "성함", "фио", "ф.и.о")
# These name a thing as often as a person ("药品名字", "약품이름", "اسم الدواء"), so they count
# alone or beside a word for the patient ("患者名前", "환자 이름", "اسم المريض", "שם החולה").
SCRIPT_NAME_WORDS = frozenset({"名前", "名字", "이름", "اسم", "الاسم", "שם", "नाम", "ชื่อ", "имя",
                               "фамилия", "отчество", "ім'я", "прізвище", "όνομα", "ονομα", "επώνυμο",
                               "επωνυμο", "ชื่อสกุล", "นามสกุล", "שם משפחה", "שם פרטי"})
SCRIPT_PATIENT_WORDS = ("患者", "病人", "病患", "환자", "المريض", "مريض", "החולה", "חולה", "रोगी", "मरीज",
                        "का", "की", "ผู้ป่วย", "пациента", "пациент", "больного", "ασθενούς", "του")
# Words for a surname, a given name or the reading of a name (round 4: 姓, 氏, 성, フリガナ). They are
# names by the rule below, but not column words a column name may be shown with: 성 is also a surname.
SCRIPT_NAME_WORDS_NOT_SHOWN = frozenset({"姓", "氏", "名", "성", "姓氏", "苗字", "フリガナ", "ふりがな", "カナ",
                                         "よみがな", "ヨミガナ", "かな", "拼音", "罗马字", "ローマ字"})


def name_in_other_script(header: str) -> tuple[str, str, str] | None:
    raw = " ".join(unicodedata.normalize("NFKC", str(header)).casefold().replace("_", " ").split())
    if any(w in raw for w in SCRIPT_NAME_ANYWHERE):
        return ("name (a word for name in another script)", "pseudonym_name", "name")
    rest = raw
    for w in sorted(SCRIPT_PATIENT_WORDS, key=len, reverse=True):
        rest = rest.replace(w, " ")
    words = [w for w in re.split(r"[\s/,;:()\[\].\-]+", rest) if w]
    names = SCRIPT_NAME_WORDS | SCRIPT_NAME_WORDS_NOT_SHOWN
    if words and (" ".join(words) in names or all(w in names for w in words)):
        return ("name (a word for name in another script)", "pseudonym_name", "name")
    return None


# Addresses, telephones and email addresses named in scripts the column-name tokens do not read
# (round 4: 住所, 주소, Адрес, 電話, 전화, メール), anywhere in a column name.
SCRIPT_ADDRESS_WORDS = ("住所", "地址", "住址", "주소", "адрес", "عنوان", "כתובת", "पता", "ที่อยู่", "διεύθυνση")
SCRIPT_PHONE_WORDS = ("电话", "電話", "手机", "手機", "携帯", "전화", "휴대폰", "핸드폰", "телефон", "هاتف", "جوال",
                      "טלפון", "फोन", "फ़ोन", "โทรศัพท์", "τηλέφωνο", "τηλεφωνο")
SCRIPT_EMAIL_WORDS = ("メール", "이메일", "邮箱", "电子邮件", "電子郵件", "電郵", "почта", "البريد", "אימייל",
                      "דוא\"ל", "ईमेल", "อีเมล")
SCRIPT_PLATE_WORDS = ("车牌", "車牌", "ナンバープレート", "번호판", "номерной знак", "госномер")


def contact_in_other_script(header: str) -> tuple[str, str, str] | None:
    raw = unicodedata.normalize("NFKC", str(header)).casefold()
    if any(w in raw for w in SCRIPT_ADDRESS_WORDS):
        return ("geography smaller than a state", "redact", "address")
    if any(w in raw for w in SCRIPT_PHONE_WORDS):
        return ("telephone number", "redact", "phone")
    if any(w in raw for w in SCRIPT_EMAIL_WORDS):
        return ("email address", "redact", "email")
    if any(w in raw for w in SCRIPT_PLATE_WORDS):
        return ("vehicle identifier", "redact", "vehicle")
    return None


COORDINATE_WORDS_OTHER_SCRIPTS = ("широта", "долгота", "纬度", "经度", "緯度", "經度", "経度", "위도", "경도",
                                  "خط العرض", "خط الطول", "קו רוחב", "קו אורך", "अक्षांश", "देशांतर",
                                  "ละติจูด", "ลองจิจูด", "γεωγραφικό πλάτος", "γεωγραφικό μήκος")


def name_rule(header: str) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column whose name marks a Safe Harbor identifier.

    These are the columns that cannot be kept. The terms are deliberately whole
    words: "ip" (inpatient), "tract" (urinary tract) or "cell" (cell type) are not
    identifiers on their own, and a column of IP addresses is still found by its values.
    """
    t = column_tokens(header)
    if any(w in unicodedata.normalize("NFKC", str(header)).casefold() for w in COORDINATE_WORDS_OTHER_SCRIPTS):
        return ("geography smaller than a state", "redact", "address")
    if age_in_other_language(header, t):
        return ("age", "age", "age")
    script_rule = birth_in_other_script(header, t) or name_in_other_script(header) or contact_in_other_script(header)
    if script_rule:
        return script_rule
    if not t:
        return None
    ts = set(t)
    whole = " ".join(t)
    # "DoB", "YoB", "BDate" and "DoD" are split at their capitals; read them whole too.
    compact = "".join(t)
    if compact in BIRTH_YEAR_TOKENS:
        return ("year of birth", "birth_year", "date")
    if compact in BIRTH_DATE_TOKENS | {"dateofbirth", "birthdate", "birthday"}:
        return ("date of birth", "birth_date", "date")
    if compact in ("dod", "dateofdeath", "deathdate"):
        return ("date", "year", "date")

    # Allowed geography: a state or a country is not an identifier.
    if whole in ("state", "state code", "province", "country", "country code", "state province",
                 "us state", "home state", "residence state", "state of residence",
                 "country of residence", "country of birth", "birth country", "birthcountry",
                 "state of birth", "birth state", "birthstate", "country of origin",
                 "origin country", "country of citizenship", "citizenship", "nationality",
                 "country name", "state name", "residence country", "home country",
                 "province of residence"):
        return ("state or country (allowed)", "keep", "allowed_geography")

    # 17: full-face photographs and comparable images; 16: biometric identifiers.
    if _has(t, "photo", "photos", "photograph", "picture", "headshot", "portrait", "selfie",
            "avatar", "mugshot", "face image", "face photo", "foto", "fotos", "fotografia",
            "fotografie", "fotografias") or (
                "image" in ts and ts & {"path", "file", "url", "face", "patient", "id"}):
        return ("photograph", "redact", "photo")
    if _has(t, "fingerprint", "finger print", "voiceprint", "voice print", "biometric",
            "biometrics", "retinal scan", "iris scan", "palm print", "palmprint",
            "face template", "facial template", "face encoding", "faceprint"):
        return ("biometric identifier", "redact", "biometric")

    # 14 and 15: URLs and IP addresses.
    if _has(t, "url", "uri", "website", "web site", "homepage", "home page", "web address",
            "weblink", "web link", "hyperlink", "hostname", "host name", "domain name", "web page",
            "webpage", "pagina web", "site web", "sitio web"):
        return ("web address", "redact", "url")
    if _has(t, "ip address", "ipaddress", "ip addr", "ipv4", "ipv6", "remote addr", "client ip",
            "mac address", "macaddress") or whole in ("ip", "ip no"):
        return ("IP or MAC address", "redact", "ip")
    if _has(t, "username", "user name", "login", "screen name", "user id", "userid", "handle"):
        return ("user name", "redact", "id")

    # 12 and 13: vehicles and devices.
    if _has(t, "vin", "license plate", "licence plate", "licenseplate", "plate number",
            "registration plate", "number plate", "vehicle id", "vehicle identification",
            "vehicle number", "kennzeichen", "nummernschild", "autokennzeichen", "targa", "kenteken",
            "immatriculation", "plaque d immatriculation") or whole in ("vehicle", "matricula"):
        return ("vehicle identifier", "redact", "vehicle")
    if (_has(t, "serial number", "serialnumber", "serial no", "udi", "imei", "device id",
             "deviceid", "device identifier", "implant serial", "pacemaker serial")
            or whole in ("serial", "sn")
            or ("device" in ts and ts & {"id", "number", "no", "serial"})):
        return ("device identifier", "redact", "device")

    # 11: certificate and licence numbers.
    if _has(t, "license", "licence", "drivers license", "driver license", "dl number", "dl no",
            "certificate", "cert number", "cert no", "dea", "dea number", "npi", "passport"):
        return ("certificate or licence number", "redact", "license")

    # 9 and 10: health plan beneficiary and account numbers.
    if _has(t, "insurance", "member id", "member number", "memberid", "beneficiary",
            "health plan", "healthplan", "policy number", "policy id", "subscriber",
            "group number", "medicare", "medicaid", "mbi", "hicn", "health card", "healthcard", "ohip",
            "medi cal", "medical card", "carte vitale", "ramq", "ehic", "tessera sanitaria", "tarjeta sanitaria",
            "cartao sus", "versichertennummer", "nhi", "nhi number", "policy no", "policy nr", "policy num") \
            or whole in ("policy", "plan id", "plan number", "plan no", "plan nr", "health plan id"):
        return ("health plan number", "redact", "health_plan")
    if whole in ACCOUNT_WORDS or (ts & ACCOUNT_WORDS and ts & {"no", "nr", "num", "nbr", "number", "id", "ids"}):
        return ("account number", "redact", "account")
    if _has(t, "account", "acct", "bank account", "iban", "credit card", "card number",
            "cc number", "routing number"):
        return ("account number", "redact", "account")

    # 4 to 7: telephone, fax, email, social security and national ID numbers.
    if _has(t, "fax", "facsimile"):
        return ("fax number", "redact", "phone")
    if (_has(t, "phone", "telephone", "phonenumber", "homephone", "cellphone", "mobilephone",
             "workphone", "contact number", "pager", "mobile number", "cell number", "telefon", "telefono",
             "telefone", "telefoon", "telefonnummer", "telefonnr", "celular", "movil", "cellulare",
             "puhelin", "handynummer", "mobilnummer", "telefonu", "telemovel", "telefonnr", "telefonszam")
            or whole in ("tel", "mobile", "cell", "cell no", "mobile no", "tel no", "mobil", "handy", "natel",
                         "gsm", "movil")):
        return ("telephone number", "redact", "phone")
    if _has(t, "email", "e mail", "email address", "emailaddress", "courriel", "correo", "eposta",
            "e posta", "sahkoposti", "epost", "e post", "mail address", "mailadresse"):
        return ("email address", "redact", "email")
    if _has(t, "ssn", "social security", "ss number", "national id", "nationalid", "tax id",
            "itin", "nhs number", "nino", *NATIONAL_ID_WORDS) or whole in ("sin", "tin"):
        return ("social security or national ID number", "redact", "ssn")

    # 8: medical record numbers and other record identifiers become pseudonyms.
    if _has(t, "mrn", "medical record", "record number", "chart number", "chart no", "chart id",
            "empi", "accession", "barcode", "unit number", "patient number", "health record",
            "case number", "encounter number", *RECORD_NAME_WORDS):
        return ("record number", "pseudonym_id", "id")
    if ts & {"id", "identifier", "uid", "guid", "uuid", "pid"} and not (ts & NOT_A_PERSON_ID):
        return ("identifier", "pseudonym_id", "id")

    # 3: ages and dates. An age column in any unit, and age groups, which must not
    # split ages over 89 ("90-94" is refused, "90+" is the one allowed group).
    if any(_is_age_token(x) for x in t):
        return ("age", "age", "age")
    # "Birth" in other languages ("Geburt", "naissance", "nacimiento", "nascita", "Natal",
    # "Doğum", "lahir"), and "nac" or "bth" beside a word for date ("Fecha Nac", "Bth Dt").
    birth_word = bool(ts & ({"birth", "born"} | BIRTH_WORDS_OTHER_LANGUAGES)) or bool(
        ts & {"nac", "bth"} and ts & BIRTH_DATE_WORDS) or bool("sinh" in ts and ts & {"ngay", "nam", "noi"})
    if ts & {"birthplace", "placeofbirth", "birthcity", "geburtsort"} or (birth_word and ts & BIRTH_PLACE_WORDS):
        return ("place of birth", "redact", "address")
    if ts & BIRTH_YEAR_TOKENS or _has(t, "birth year", "year of birth", "yob", "yearofbirth",
                                      "birthyear", "year born", "born year", "yr of birth") \
            or (birth_word and ts & (YEAR_TOKENS | BIRTH_YEAR_WORDS) and not (ts & BIRTH_NOT_A_DATE)):
        return ("year of birth", "birth_year", "date")
    if ts & BIRTH_DATE_TOKENS or _has(t, "dob", "birthdate", "birthday", "date of birth", "dateofbirth",
                                      "birth date", "birth dt", "d of b", "b date", "b dt", "bth dt"):
        return ("date of birth", "birth_date", "date")
    if birth_word and not (ts & BIRTH_NOT_A_DATE):
        return ("date or year of birth", "birth_date", "date")
    if _has(t, *DATE_WORDS) and not (ts & INTERVAL_WORDS):
        return ("date", "year", "date")
    if "time" in ts and ts & DATE_TIME_CONTEXT and not (ts & INTERVAL_WORDS):
        return ("date and time", "year", "date")

    # 2: geography smaller than a state.
    if _has(t, "zip", "zipcode", "zip code", "postal code", "postalcode", "postcode", "zip5",
            "zip plus", "postal", "plz", "cep", "postleitzahl", "codigo postal", "code postal",
            "codice postale", "postnummer", "postinumero", "kod pocztowy", "postcodigo", "post code", "zcta",
            "pin code", "pincode", "eircode"):
        return ("ZIP code", "zip3", "zip")
    if _has(t, "address", "addr", "street", "address line", "streetaddress", "homeaddress",
            "city", "town", "village", "municipality", "county", "parish", "borough",
            "precinct", "neighborhood", "neighbourhood", "census tract", "census block",
            "block group", "fips", "geocode", "geohash", "latitude", "longitude",
            "coordinates", "coordinate", "gps", "easting", "northing", "utm", "geolocation", "latlong",
            "latlon", "latlng", "geolat", "geolon", "geolng", "breitengrad", "langengrad", "latitud",
            "longitud", "latitudine", "longitudine", "latitudes", "longitudes", "place of residence", "home location", "hometown",
            "home town", "locality", "suburb", "district", "subdistrict", "township",
            "hamlet", *CITY_WORDS_OTHER_LANGUAGES, *ADDRESS_WORDS_OTHER_LANGUAGES) \
            or whole in ("lat", "lon", "lng", "long", "residence", "pob", "pob city", "pob town", "road",
                         "avenue", "apt", "apartment", "suite", "domicile", "domicilio") \
            or _has(t, "lives in", "living in", "lives at", "resides in", "residing in", "resident of",
                    "lives near", "lieu de residence", "lugar de residencia", "wohnhaft in"):
        return ("geography smaller than a state", "redact", "address")

    # 1: names of the person, relatives, household members and employers.
    if ts & {"employer", "workplace"} or _has(t, "next of kin", "emergency contact", "next kin",
                                              "nextofkin"):
        return ("relative, household member or employer", "redact", "name")
    if whole in RELATIVE_HEADERS:
        return ("relative or contact of the person", "redact", "name")
    if _has(t, "fname", "lname", "mname", "forename", "forenames") or whole == "nm" \
            or ("nm" in ts and ts & NM_PERSON_WORDS):
        return ("name", "pseudonym_name", "name")
    if _has(t, "name", "names", "surname", "firstname", "lastname", "fullname", "middlename",
            "givenname", "familyname", "maidenname", "patientname", "ptname", "initials",
            "alias", "nickname", "nicknames", "aka", "also known as", "pseudonym", "pseudonyms", "moniker",
            "monikers", "kana", "furigana", "pinyin", "romaji", "romanized", "romanised",
            *NAME_WORDS_OTHER_LANGUAGES) or _whole_name_word(t):
        if ts & RELATIVE_WORDS:
            return ("name of a relative or contact", "redact", "name")
        if ts & CLINICIAN_WORDS:
            return ("name of a clinician", "redact", "name")
        # A role makes it a person's name even beside "lab" or "study": "Lab Technician
        # Name", "Specimen Collector Name"; "Study Patient Name" is the person's own.
        roles = person_role_words(t, NAME_TRAILING)
        if roles - SELF_WORDS:
            return ("name of a clinician, staff member or other person", "redact", "name")
        if ts & NOT_A_PERSON_NAME and not roles:
            return None
        return ("name", "pseudonym_name", "name")
    if whole in PERSON_HEADERS:
        return ("name or identifier of the person", "pseudonym_name", "name")
    return None


# "City", "town", "district" and "neighbourhood" in other languages: geography smaller than
# a state, like their English words.
CITY_WORDS_OTHER_LANGUAGES = (
    "ciudad", "municipio", "municipalidad", "localidad", "pueblo", "barrio", "colonia", "comuna",
    "ville", "commune", "quartier", "localite", "stadt", "gemeinde", "wohnort", "ortschaft",
    "citta", "comune", "frazione", "cidade", "bairro", "concelho", "freguesia", "gemeente",
    "woonplaats", "stad", "kommune", "kommun", "miasto", "gmina")
# "Name" in other languages.
NAME_WORDS_OTHER_LANGUAGES = (
    "nombre", "nombres", "apellido", "apellidos", "nom", "prenom", "prenoms", "nome", "cognome",
    "vorname", "nachname", "familienname", "naam", "voornaam", "achternaam", "navn", "fornavn",
    "etternavn", "efternavn", "namn", "fornamn", "efternamn", "imie", "nazwisko", "sobrenome",
    "sukunimi", "etunimi", "prijmeni", "vezeteknev", "keresztnev", "prenume", "soyad", "soyadi",
    "geburtsname", "madchenname", "maedchenname", "nama", "isim", "isimi", "jmeno", "nimi", "pangalan",
    "numele", "patientnavn", "patientnamn", "patientnaam", "imya", "familiya")
# Words for a name that are short or also given names ("Tên", "Ad", "Adı", "Ime", "Jina"): a name only
# as the whole column name, or beside a word for the patient ("Hasta Adı", "Nama Pasien"). Not column
# words, so a cell holding one is not shown as a column name.
WHOLE_NAME_WORDS = frozenset("ten ad adi ime jina nev navn namn nom".split())
PATIENT_WORDS_OTHER_LANGUAGES = frozenset("""
patient patients pt paciente pacientes patiente paziente patientin patienten pacjent pacjenta pasient pasienten
potilas potilaan pacient pacienta hasta hastanin pasien benh nhan ho
""".split())


def _whole_name_word(tokens: list[str]) -> bool:
    rest = [x for x in tokens if x not in PATIENT_WORDS_OTHER_LANGUAGES and not x.isdigit()]
    return len(rest) == 1 and rest[0] in WHOLE_NAME_WORDS


# National and social security numbers by name (round 4), as column-name tokens with accents
# dropped. Words with a common clinical meaning (CPR, PPS, NSS, NIR, RG) are left out alone.
NATIONAL_ID_WORDS = tuple("""
dni nif cpf aadhaar aadhar bsn burgerservicenummer ahv avs personnummer personnumer fodselsnummer
henkilotunnus hetu curp kvnr krankenversichertennummer sozialversicherungsnummer svnr steuernummer
steueridentifikationsnummer insee rut cedula rrn jumin mynumber pesel nric ktp mykad hkid jmbg egn oib cnp
amka tckn kimlik nik tfn
""".split()) + ("my number", "codice fiscale", "cpr nummer", "cpr nr", "cprnr", "cpr number", "steuer id",
                "numero de securite sociale", "securite sociale", "numero de seguridad social",
                "seguridad social", "sozialversicherung", "tc kimlik", "national insurance",
                "national identity", "identity card", "identity number", "id card", "carte d identite",
                "documento de identidad", "numero de identificacion", "personal number", "personal id",
                "registro nacional", "codice identificativo", "ird number", "pan card", "voter id")
# Bills, invoices, receipts and claims: account numbers as the whole column name or beside a word for
# number ("Claim No", "Invoice Number"); "Claim Amount" is money.
ACCOUNT_WORDS = frozenset("invoice receipt bill billing claim voucher".split())
# Medical record numbers named in other languages (round 4), as tokens with accents dropped.
RECORD_NAME_WORDS = (
    "aktenzeichen", "fallnummer", "patientennummer", "dossiernummer", "krankenblattnummer", "prontuario",
    "expediente", "historia clinica", "cartella clinica", "numero de historia", "numero de dossier",
    "numero dossier", "numero di cartella", "numero de cartella", "journalnummer", "patientnummer",
    "potilasnumero", "registration number", "registration no", "matricule", "numero de prontuario",
    "numero de expediente", "nhc", "numero d identification")
# Street addresses in other languages (round 4).
ADDRESS_WORDS_OTHER_LANGUAGES = (
    "direccion", "adresse", "adressen", "anschrift", "strasse", "wohnadresse", "calle", "rue", "avenida",
    "indirizzo", "endereco", "morada", "woonadres", "adres", "adresa", "adress", "osoite", "postadresse")
# A whole column name that is a relative or a contact: the values are that person's
# name (or identifier). Redacted, never kept.
RELATIVE_HEADERS = {"spouse", "mother", "father", "guardian", "husband", "wife", "caregiver",
                    "carer", "informant"}
# A whole column name that is the person: participant, proband, ... Pseudonymized.
PERSON_HEADERS = {"patient", "pt", "person", "nok", "participant", "participants", "proband",
                  "probands", "individual", "client", "respondent", "enrollee", "enrolee",
                  "decedent", "interviewee"}
# "nm" is a name only next to one of these ("pt_nm", "first_nm"); in "wavelength_nm"
# it is nanometres.
NM_PERSON_WORDS = {"pt", "patient", "first", "last", "full", "given", "family", "person",
                   "member", "subject", "participant", "middle", "maiden", "mother", "father",
                   "spouse", "contact", "client"}


# A column name ending in one of these ("Insurance Type", "Account Status", "Medicaid
# Eligible") says what kind or state its values are, not that they are the identifier.
QUALIFIER_WORDS = frozenset({"type", "types", "status", "statuses", "class", "classes",
                             "category", "categories", "kind", "kinds", "eligible",
                             "eligibility", "flag", "flags", "indicator", "indicators",
                             "coverage", "tier", "level", "yn", "verified", "verification"})
# Identifier types whose name rule gives way to such a column: numbers, codes, addresses,
# names. Dates and ages keep their rules, which already leave words alone.
QUALIFIED_PHI = frozenset({"health_plan", "account", "license", "id", "phone", "email", "url",
                           "ip", "vehicle", "device", "ssn", "address", "zip", "name", "photo",
                           "biometric"})


# A column named for the payer ("Insurance", "Medicare") holds a beneficiary number only
# when its name also says number, ID, member or policy.
PAYER_WORDS = frozenset({"insurance", "insurer", "insurers", "medicare", "medicaid", "payer",
                         "payor", "healthplan"})
NUMBER_WORDS = frozenset({"id", "ids", "number", "numbers", "no", "num", "nbr", "identifier",
                          "code", "codes", "mbi", "hicn", "member", "subscriber", "beneficiary",
                          "policy", "group", "card", "account", "acct"})


def qualified_header(header: str) -> bool:
    """A column name that ends in a qualifier ("Insurance Type") or starts with one and "of"
    ("Type of Insurance")."""
    rest = [t for t in column_tokens(header) if not t.isdigit()]
    return bool(rest) and (rest[-1] in QUALIFIER_WORDS
                           or (len(rest) >= 3 and rest[0] in QUALIFIER_WORDS and rest[1] == "of"))


def category_values(values: list[str], scrubber: "Scrubber", strict: bool = False) -> bool:
    """True when the values are a handful of words, not identifiers: few distinct values (or
    each repeated), no digit, no identifier pattern, at most four words, and none shaped
    like the name of a person or a place. With `strict`, every value must be made of
    category words ("Urban", "Home", "Self-employed"), because a single unknown word under
    a type column of an employer, a city or a login can be the employer, the town or the
    login itself."""
    vals = _shape_values(values)
    if not vals:
        return False
    distinct = set(vals)
    if len(distinct) > CATEGORY_MAX_DISTINCT and len(vals) < CATEGORY_MIN_REPEATS * len(distinct):
        return False
    return all(not re.search(r"\d", v) and len(v.split()) <= 4 and not scrubber.find(v)
               and not name_or_place_like(v) and (not strict or _is_category_value(v))
               for v in distinct)


def column_name_rule(header: str, values: list[str], scrubber: "Scrubber") -> tuple[str, str, str] | None:
    """name_rule, except that a type or status column of an identifier word ("Insurance
    Type", "Subscriber Status", "City Type", "Employer Type") whose values are category
    words is left to the value rules, which keep it unless its values look like names."""
    rule = name_rule(header)
    if not rule or rule[2] not in QUALIFIED_PHI:
        return rule
    t = column_tokens(header)
    # "Insurance", "Primary Insurance", "Medicare": a payer, unless the name says number.
    payer = rule[2] == "health_plan" and bool(set(t) & PAYER_WORDS or _has(t, "health plan")) \
        and not set(t) & NUMBER_WORDS
    # Every value must be a known category word ("Mobile", "Active", "Urban"): a single unknown
    # word under a type or status column of a phone, an email, a ZIP code or a name can be the
    # person's name. Only payers (Medicare, a regional insurer) are not a closed list.
    if (payer or qualified_header(header)) and \
            category_values(values, scrubber, strict=rule[2] != "health_plan"):
        return None
    return rule


def _hints(words: str, finding: str, action: str, phi: str, numbers_are_ids: bool) -> dict:
    return {w: (finding, action, phi, numbers_are_ids) for w in words.split(",")}


# Whole column names that usually hold a person's or a place's name but have other uses
# ("Insured" can be yes or no, "Region" a census region or a brain region). They are
# pseudonymized or redacted by default, like any column the scanner cannot vouch for,
# and the person can keep one with --keep after checking it.
NAME_HINT_HEADERS = {
    **_hints("subject,subjects,member,insured,donor,recipient,resident,policyholder",
             "a person's name or identifier", "pseudonym_name", "name", True),
    **_hints("region,home,place,origin,community,locale",
             "a place smaller than a state", "redact", "address", False),
    **_hints("company,organization,organisation,business,firm,school,college,university",
             "an employer's or a school's name", "redact", "name", False),
}


# Whole column names that are the person's own first, last or given name, and words that name a
# relative, a household member or a contact ("Next Kin", "Contact Person", "Landlord", "Lives
# With"). Such a column is an identifier by its name, which --keep cannot keep, unless every value
# is a category word ("Mother", "Yes") or a number (person_name_rule).
OWN_NAME_HEADERS = frozenset({"first", "last", "given", "middle", "maiden", "first last", "last first",
                              "firsts", "lasts", "givens", "first given", "christian"})
RELATIVE_NAME_WORDS = (frozenset(RELATIVE_WORDS) - {"emergency"}) | frozenset("""
parents guardians relatives caregivers carer carers households siblings children husbands wives
partners contacts spouses mothers fathers family families friend friends neighbor neighbour neighbors
neighbours roommate roommates landlord landlady tenant tenants lodger housemate housemates flatmate
cousin cousins aunt uncle niece nephew grandparent grandparents grandmother grandfather grandson
granddaughter grandchild grandchildren stepparent stepmother stepfather stepson stepdaughter godparent
godmother godfather fiance fiancee girlfriend boyfriend maiden informant brother sister son daughter
brothers sisters sons daughters kin nok madre padre mere pere mutter vater esposa esposo conjoint
conjointe ehemann ehefrau marito moglie hijo hija fils fille sohn tochter figlio figlia hermano
hermana frere soeur bruder schwester cuidador cuidadora aidant aidante angehorige angehoerige
familiar familia famille familie contacto contatto kontakt
""".split())
# Last words that make a relative's word the subject of the column ("Contact Person", "Household
# Member", "Contact Info"), as opposed to "Contact Method" or "Family History".
PERSON_HEAD_WORDS = frozenset({"person", "persons", "people", "member", "members", "individual",
                               "individuals", "info", "information", "details", "detail", "name", "names",
                               "nm", "who", "persona", "personne"})


def _category_or_count(v: str) -> bool:
    """A number, or category words with or without numbers ("Mother", "2 adults, 1 child")."""
    if is_number(v):
        return True
    words = re.findall(r"[^\W\d_]+(?:['\u2019-][^\W\d_]+)*", v.lower())
    return bool(words) and all(_vocabulary_word(w) for w in words)


# Whole column names of name_hint_rule that name the person ("Subject", "Member", "Donor"): with a
# word in them that is not a category word, the column holds the person's name and cannot be kept.
PERSON_HINT_HEADERS = frozenset({"subject", "subjects", "member", "insured", "donor", "recipient", "resident",
                                 "policyholder"})
SOCIAL_NETWORKS = frozenset("""
twitter instagram facebook fb tiktok snapchat linkedin wechat weixin whatsapp telegram skype reddit youtube
mastodon weibo discord threads bluesky pinterest tumblr kakaotalk viber
""".split())
# Abbreviations for a coordinate, read as one only when every value is a number in range.
COORDINATE_ABBREVIATIONS = frozenset({"lat", "lon", "lng", "lats", "lons", "coord", "coords", "latdeg",
                                      "londeg", "lngdeg"})
COORDINATE_COMPANIONS = frozenset({"home", "patient", "pt", "geo", "gps", "residence", "address", "addr",
                                   "site", "location", "loc", "event", "x", "y", "dd", "deg", "degrees"})


def _word_value(v: str) -> bool:
    """A value of letters with no digit that is not made of category words: a name's shape."""
    return bool(re.search(r"[^\W\d_]", v)) and not re.search(r"\d", v) and not _category_or_count(v)


def coordinate_name_rule(header: str, values: list[str]) -> tuple[str, str, str, int] | None:
    """(finding, action, phi type, cells) for a column named with an abbreviation for a coordinate
    ("Home Lat", "Geo_Lon", "Lat (deg)", "Patient Long", "x_coord") whose values are all numbers
    within 180, or numbers of five or more digits before the point (metres of a grid such as UTM).
    An abbreviation has other meanings ("Lat" for a latency or a lateral view), so the person can
    keep such a column; the whole words (latitude, longitude, easting) are identifiers by name."""
    t = column_tokens(header)
    ts = set(t)
    named = bool(ts & COORDINATE_ABBREVIATIONS) or ("long" in ts and ts & COORDINATE_COMPANIONS) or (
        ts & {"x", "y", "e", "n"} and ts & {"utm", "grid", "coord", "coords", "coordinate"})
    if not named:
        return None
    nums = [number_like(v) for v in _shape_values(values)]
    if not nums or any(n is None or re.search(r"[eE]", n) for n in nums):
        return None
    xs = [float(n) for n in nums]
    if all(abs(x) <= 180 for x in xs) or all(len(n.lstrip("+-").split(".")[0]) >= 5 for n in nums):
        return ("numbers in the range of a coordinate under a column name with an abbreviation for latitude "
                "or longitude (a possible coordinate)", "redact", "geo", len(nums))
    return None


def person_name_rule(header: str, values: list[str]) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column named for the person's own first, last or given
    name, or for a relative, a household member or a contact, unless every value is a category
    word or a number; and for a column named for the person ("Subject", "Donor") or for a social
    network ("Twitter") with a value that is a word and not a category word. Unlike
    name_hint_rule, the column cannot be kept."""
    t = [x for x in column_tokens(header) if not x.isdigit()]
    if not t:
        return None
    vals = _shape_values(values)
    if vals and " ".join(t) in PERSON_HINT_HEADERS and any(_word_value(v) for v in vals):
        return ("a person's name (the column name names the person, and a value is a word)", "pseudonym_name",
                "name")
    if vals and (set(t) & SOCIAL_NETWORKS or "".join(t) in SOCIAL_NETWORKS) \
            and not all(_category_or_count(v) for v in vals):
        return ("a social media account", "redact", "url")
    if not vals or all(_category_or_count(v) for v in vals):
        return None
    if " ".join(t) in OWN_NAME_HEADERS:
        return ("a first, last or given name", "pseudonym_name", "name")
    head = t[-1]
    if _has(t, "lives with", "living with", "lives together with", "vive con", "vit avec", "lebt mit") \
            or head in RELATIVE_NAME_WORDS or (head in PERSON_HEAD_WORDS and set(t) & RELATIVE_NAME_WORDS):
        return ("a relative's, household member's or contact's name", "redact", "name")
    return None


def name_hint_rule(header: str, values: list[str]) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column whose whole name is one of
    NAME_HINT_HEADERS, unless every value is a common category word ("Yes", "Mother")
    or, where numbers are not identifiers, every value is a number."""
    hint = NAME_HINT_HEADERS.get(" ".join(column_tokens(header)))
    if not hint:
        return None
    finding, action, phi, numbers_are_ids = hint
    vals = _shape_values(values)
    if not vals or all(_is_category_value(v) for v in vals):
        return None
    if not numbers_are_ids and all(is_number(v) for v in vals):
        return None
    return (f"column name: may hold {finding}", action, phi)


# ================================================================ record numbers by name (round 4)
# Words for "number" in a column name ("Pat No", "Hospital No", "Patientennummer", "Numéro de dossier",
# "病历号", "患者番号", "등록번호", "Номер карты"). With values of four or more digits or codes with digits
# such a column is a record number by its name, which --keep cannot keep; with short numbers it is a
# study or row number, pseudonymized by number_rule and kept on the person's word.
RECORD_NUMBER_WORDS = frozenset("""
id ids identifier identifiers no nr nro nbr num number numbers nummer numero numeros numer nomor nombor
cislo szam numara broj
record records chart charts dossier dossiers akte akten expediente prontuario cartella historia folio ficha
registry register registro
nir nss cpr pps rg nie rfc sus
phn nhs nhi ohip nip prn pid patid ptid patno ptno patref ptref patkey ptkey
""".split())
# Round 6: a key, a reference or a token of the patient is the patient's number ("Patient Ref", "Pat Key",
# "Pt Token"), and so is a name with a number sign after a word ("Pat#", "Patient #", "MR#"; "# of Visits"
# and "# Visits" are counts).
RECORD_NUMBER_OWNERS = frozenset("patient patients pat pats pt pts pnt ptnt paciente pacientes patiente paziente".split())
RECORD_NUMBER_REFERENCES = frozenset("key keys ref refs reference references token tokens".split())
RECORD_NUMBER_SCRIPTS = ("番号", "号", "號", "번호", "номер", "رقم", "מספר", "संख्या", "क्रमांक", "หมายเลข",
                         "αριθμός", "αριθμος")
# Things whose numbers are not a person's or a record's: genes, probes, code systems, batches, plates.
RECORD_NUMBER_EXEMPT = frozenset("""
gene genes protein proteins probe probes probeset snp snps rsid dbsnp transcript transcripts ensembl entrez
hgnc uniprot refseq pathway pathways kegg reactome pubchem chembl omim mesh loinc icd cpt snomed rxnorm ndc
atc concept concepts drug drugs product products catalog catalogue cas batch lot lots plate plates well wells
run runs instrument assay assays panel test tests item items question questions form forms variable variables
field fields column columns version protocol site sites center centre centers centres facility department
dept chromosome chr exon intron position pos lane flowcell primer antibody clone page pages
""".split())
COUNT_PHRASES = ("number of", "no of", "num of", "count of", "n of", "amount of", "nombre de", "anzahl",
                 "aantal", "antal", "liczba", "pocet", "quantidade", "cantidad", "numero totale")
# After "numero de" (Spanish, Portuguese, Italian) a plural is a count ("número de visitas", "numero di
# ricoveri"); these words make it a record ("número de historia", "numero di cartella").
RECORD_TARGETS = frozenset("""
historia expediente dossier cartella prontuario registro paciente pacientes caso ficha matricula seguro
afiliacion documento identidad identificacion socio cliente beneficiario poliza paziente
""".split())


def count_phrase(tokens: list[str]) -> bool:
    if _has(tokens, *COUNT_PHRASES):
        return True
    for a, b, c in zip(tokens, tokens[1:], tokens[2:]):
        if a in ("numero", "numeros") and b in ("de", "di", "do", "da", "dos", "das", "del", "des") \
                and c not in RECORD_TARGETS and c.endswith(("s", "i")):
            return True
    return False


def number_word_header(header: str) -> bool:
    """True for a column name that says number or record ("Pat No", "Hospital No", "Patientennummer",
    "Fallnummer", "Potilasnumero", "Numéro de dossier", "病历号", "번호"), and is not a count ("Number of
    Visits", "Número de visitas") or the number of a thing that is not a person ("Gene ID", "Lot No")."""
    t = column_tokens(header)
    ts = set(t)
    raw = unicodedata.normalize("NFKC", str(header)).casefold()
    if count_phrase(t) or ts & RECORD_NUMBER_EXEMPT:
        return False
    return bool(ts & RECORD_NUMBER_WORDS or any(len(x) > 6 and x.endswith(("nummer", "numero", "number", "numer"))
                                                for x in t)
                or any(w in raw for w in RECORD_NUMBER_SCRIPTS)
                or (ts & RECORD_NUMBER_OWNERS and ts & RECORD_NUMBER_REFERENCES)
                or re.search(r"[^\W\d_]\s*#", raw) is not None)


def _record_shaped(v: str) -> bool:
    """A value with four or more digits in a row (also grouped, 4,527,832, or with an exponent), or a
    code of letters and three or more digits ("HC-00123", "A1234567")."""
    s = _plain(v)
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?[eE][+-]?\d+", s):
        return True
    joined = re.sub(r"(?<=\d)[,.\s'](?=\d{3}(?!\d))", "", s)
    if re.search(r"\d{4,}", joined):
        return True
    return bool(re.search(r"[^\W\d_]", s)) and len(re.findall(r"\d", s)) >= 3


def record_number_name_rule(header: str, values: list[str]) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column named with a word for number or record whose values
    have four or more digits or are codes with digits: a record number by its name. Unlike
    number_rule's finding, the column cannot be kept."""
    vals = _shape_values(values)
    if not vals or not number_word_header(header) or measurement_header(header):
        return None
    if any(_record_shaped(v) for v in vals):
        return ("a record number (the column name says number or record, and its values have four or more "
                "digits or are codes with digits)", "pseudonym_id", "id")
    return None


# Short whole numbers under a column name of a person's or a record's number ("Study ID", "Pat No",
# "Hospital No", "Subject No", "Record", "Chart", "Case", "Reference", "Key"): study and record numbers,
# pseudonymized by number_rule (round 4) and kept on the person's word.
RECORD_STYLE_WHOLE = frozenset("""
case cases chart charts record records reference ref key keys file folder dossier registry
""".split())
RECORD_STYLE_OWNERS = frozenset("""
pat patient patients pt pts subject subjects subj participant participants case chart record hospital hosp
study registry person member client donor enrollee file dossier folder kit proband probands family families
research enrollment enrolment
""".split())
# Round 7: a code, a label, a token or a sequence of the person or the record is a study number too
# ("Pt Code", "Case Code", "Participant Label", "Subject Token", "Patient Seq").
RECORD_STYLE_NUMBERS = frozenset("""
no nr nro nbr num number id ids identifier key ref nummer numero code codes label token seq
""".split())


def record_style_header(header: str) -> bool:
    t = [x for x in column_tokens(header) if not x.isdigit()]
    ts = set(t)
    if not t or count_phrase(t) or ts & RECORD_NUMBER_EXEMPT:
        return False
    return (" ".join(t) in RECORD_STYLE_WHOLE or bool(ts & RECORD_STYLE_OWNERS and ts & RECORD_STYLE_NUMBERS)
            or any(x in ("patno", "ptno", "patid", "ptid", "subjid", "studyid", "recordid", "caseid", "hospno",
                         "chartno", "regno") for x in t)
            or any(len(x) > 6 and x.endswith(("nummer", "numero")) for x in t))


# ================================================================ what --keep may keep (round 4)
# --keep keeps a column the script could not verify on the person's word, scrubbed for patterns only.
# Four review rounds found column names that --keep accepted while the same idea in English was refused
# (Pai, Mae, Elternteil, 父, Patientennummer, Prontuário, Courriel, Kennzeichen, Mom, ICE, AKA). A list of
# identifier words in every language never closes, so --keep now fails closed too: it is refused unless
# every word of the column name is a column word the script knows, and when the name's last word names
# someone other than a clinician or a member of staff (the person, a relative, a household member, a
# contact, someone in the person's life), an employer, a school, a home, an address, a telephone, a web
# address, a device, an image or notes. The person renames such a column or leaves it redacted.
KEEP_REFUSED_PEOPLE = frozenset("""
patient patients pt pts subject subjects participant participants member members individual individuals
person persons people client clients resident residents proband probands respondent respondents enrollee
enrollees enrolee decedent decedents interviewee examinee donor donors recipient recipients paciente
pacientes patiente paziente patientin patienten sujet sujeto soggetto participante partecipante teilnehmer
teilnehmerin persona personne customer customers consumer consumers user users owner owners holder holders
policyholder insured beneficiary beneficiaries subscriber subscribers student students pupil pupils baby
babies infant infants child children kid kids newborn newborns neonate toddler teen teens teenager
adolescent candidate candidates applicant applicants claimant claimants bearer victim victims survivor
survivors perpetrator heir heirs executor trustee custodian guarantor guarantors sponsor sponsors cosigner
proxy proxies surrogate surrogates representative representatives delegate driver employee employees
worker workers volunteer volunteers trainee trainees witness witnesses twin twins nanny babysitter sitter
companion teacher teachers classmate boss colleague colleagues coworker coworkers visitor visitors guest
guests emergency ice relation relations related relationship associate associates acquaintance cohabitant
cohabitants cohabitee tutor tutora tutore vormund betreuer betreuerin partner partners girlfriend boyfriend
fiance fiancee spouse spouses husband wife wives mother father parent parents guardian guardians caregiver
caregivers carer carers sibling siblings brother sister son daughter kin nok friend friends neighbor
neighbour neighbors neighbours roommate roommates landlord landlady tenant tenants lodger housemate
flatmate informant informants contact contacts relative relatives household households family families
mom mum mommy mummy mama mamma mami dad daddy papa pai mae padres genitore genitori elternteil eltern ouder
ouders vader moeder otec matka ojciec baba wali waliyyi grandpa grandma granny grandparent grandparents
grandmother grandfather grandson granddaughter grandchild grandchildren cousin aunt uncle niece nephew
stepparent stepmother stepfather godparent godmother godfather madre padre mere pere mutter vater esposa
esposo conjoint conjointe conjuge conyuge coniuge ehegatte ehepartner lebenspartner epoux epouse sposo sposa
marido hermano hermana irmao irma filho filha hijo hija frere soeur bruder schwester sohn tochter figlio
figlia fils fille abuelo abuela avo nonno nonna oma opa nieto nieta neto neta cuidador cuidadora aidant
aidante angehorige angehoerige verwandte verwandter familiar familiares contacto contatto kontakt
acompanante accompagnateur accompagnatrice begleiter begleiterin pacjent pasient potilas pacient hasta
pasien party parties bystander bystanders caller callers lawyer lawyers attorney attorneys solicitor notary
paralegal pastor priest rabbi imam clergy minister reverend man men woman women boy boys girl girls lady
gentleman sender receiver homemaker soldier veteran inlaw inlaws stepson stepdaughter stepchild stepchildren
stepbrother stepsister halfbrother halfsister godchild dependant dependants
""".split())
KEEP_REFUSED_THINGS = frozenset("""
home homes residence residences domicile house employer employers company companies workplace firm business
school schools college university church mosque temple synagogue congregation address addresses addr street
road avenue apt apartment suite phone phones mobile mobil tel telephone email emails mail courriel correo
url urls link links web website websites hostname device devices image images imagen imagem foto fotos photo
photos picture pictures face faces voice voices alias aliases aka nickname nicknames pseudonym pseudonyms
moniker monikers initials kana furigana pinyin romaji romanized romanised note notes comment comments remark
remarks memo memos narrative narratives freetext notiz notizen bemerkung bemerkungen kommentar kommentare
nota notas comentario comentarios observacion observaciones remarque remarques commentaire commentaires
opmerking opmerkingen anmerkung anmerkungen
""".split())
# Words after the head that say nothing of whose column it is ("Twin Info", "Witness Details", "Proxy
# Other", "Guardian Primary"): they are passed over to find the head.
KEEP_TRAILING_WORDS = frozenset("""
info information details detail data field fields value values entry entries text txt string str column col
item items primary secondary other alt alternate alternative backup additional extra current previous prior
former new old main
""".split())
# Words refused only as the whole column name: as the last word of a longer one they name something else
# ("Assay Plate", "Mutational Signature", "Questionnaire Domain", "Department Head").
KEEP_REFUSED_WHOLE = frozenset("plate signature domain head host mac".split())
# The same in scripts the column-name tokens do not read: the person, notes and remarks.
KEEP_REFUSED_SCRIPTS = SCRIPT_PATIENT_WORDS + ("备注", "備註", "備考", "注释", "註釋", "评论", "비고", "메모",
                                              "примечание", "комментарий", "ملاحظات", "הערות", "टिप्पणी")
# Round 5: --keep under a person word is accepted only for clinical and care staff. Round 4 refused it for
# the person, relatives and contacts and let every other role through, and the review found names kept
# under Who, Case, Reporter, Author, Signer, Agent, Manager, Director, Officer, Rep, Kind, Responsable, Tía,
# Index Case and Deceased. Any word that names a person (the lists of the rules above, a role by its
# ending, -er, -or, -ist, -ee, -ician, and the words below) is now refused as the last word of a column
# name whose values are words, unless it is one of these: physicians, doctors, nurses, surgeons,
# clinicians, providers, attendings, residents, fellows, interns, pharmacists, therapists, technicians,
# technologists and midwives, their common abbreviations (Dr, MD, RN, NP, PCP, Tech) and their names in
# other languages, and physicians named by their specialty (Radiologist, Psychiatrist, Dentist).
CLINICAL_STAFF_WORDS = frozenset("""
physician physicians doctor doctors dr drs md mds mbbs nurse nurses rn rns lpn lvn np nps aprn crna cnm cna
surgeon surgeons clinician clinicians provider providers attending attendings resident residents fellow fellows
intern interns hospitalist hospitalists pcp pcps gp gps practitioner practitioners specialist specialists
pharmacist pharmacists pharmd rph therapist therapists technician technicians tech techs technologist
technologists midwife midwives anesthetist anaesthetist anesthetists anaesthetists anesthesiologist
anaesthesiologist radiologist pathologist cardiologist oncologist neurologist nephrologist urologist
dermatologist hematologist haematologist endocrinologist gastroenterologist pulmonologist rheumatologist
ophthalmologist gynecologist gynaecologist obstetrician pediatrician paediatrician psychiatrist psychologist
podiatrist optometrist audiologist dentist orthodontist intensivist internist neonatologist geriatrician allergist
hepatologist
neurosurgeon sonographer radiographer phlebotomist dietitian dietician physiotherapist
medico medica medici medecin medecins docteur doctora dottore dottoressa arzt arztin aerztin arzte aerzte
enfermera enfermero enfermeira enfermeiro infirmiere infirmier krankenschwester pfleger pflegerin infermiere
infermiera cirujano cirujana chirurgien chirurgienne chirurg lakare laege lekarz pielegniarka
verpleegkundige huisarts farmaceutico farmaceutica pharmacien pharmacienne apotheker matrona hebamme
ostetrica
""".split())
# Two-word staff roles whose last word alone names someone else ("Physician Assistant", "Nurse Manager"
# is not one: a manager).
CLINICAL_STAFF_PAIRS = frozenset({("physician", "assistant"), ("medical", "assistant"), ("nursing", "assistant"),
                                  ("nurse", "assistant"), ("dental", "assistant"), ("care", "assistant"),
                                  ("pharmacy", "assistant"), ("nurse", "aide"), ("nursing", "aide")})
# Words that name a person and are on no list above ("Who", "Case", "Index Case", "Kind" for a child,
# "Tía" for an aunt, "Deceased", "Inpatient").
KEEP_PERSON_WORDS = frozenset("""
who whom whose case cases controls kind kinder deceased decedent enrolled enrollee inpatient inpatients
outpatient outpatients referee referees agent agents tia tio tias tios zia zio tante onkel oom sobrino sobrina
neveu nichte neffe enkel enkelin nipote cugino cugina noivo noiva novio novia admin admins charge
referring ordering admitting treating consulting diagnosing prescribing performing rendering supervising managing
covering signing approving verifying reviewing discharging accountant adult adults chef cook detective
mechanic police dependent dependents servant sergeant lieutenant
""".split())
# Words before a person word that make it a thing: a drug or an organism ("Chemotherapy Agent"), an ECG
# lead, a device that monitors, a part of a bone ("Femoral Head").
KEEP_THING_CONTEXT = {
    "agent": frozenset("""chemotherapy chemo antimicrobial antibiotic antiviral antifungal antineoplastic
infectious causative causal etiologic etiological study investigational therapeutic biologic biological
contrast imaging anesthetic anaesthetic cytotoxic targeted immunosuppressive alkylating sclerosing induction
maintenance chelating hypoglycemic antiplatelet anticoagulant antihypertensive antiepileptic""".split()),
    "lead": frozenset("ecg ekg electrode pacing pacemaker icd crt defibrillator".split()),
    "monitor": frozenset("cardiac holter glucose bp pressure heart fetal apnea event loop telemetry".split()),
    "head": frozenset("""femoral humeral radial ulnar fibular metatarsal metacarpal pancreas pancreatic caudate
epididymal muscle""".split()),
}
# The same in scripts the column-name tokens do not read, as whole words ("who").
KEEP_PERSON_WORDS_SCRIPTS = ("谁", "誰", "누구", "кто", "من", "מי")


def _keep_person_head(t: list[str]) -> str | None:
    """The word for a person a column name ends in, or None (round 5). `t` are the column-name tokens
    with numbers and words such as Info or Other already passed over."""
    head, prev = t[-1], (t[-2] if len(t) > 1 else "")
    if len(t) > 1 and (prev + head in KEEP_REFUSED_PEOPLE or prev + head in KEEP_PERSON_WORDS):
        return prev + head
    if len(t) > 1 and (head in ("by", "with") or (head == "to" and (prev.endswith("ed") or prev in TO_VERBS))):
        return head
    if _has(t, *SIGN_PHRASES):
        return "signature"
    if head in PAYER_WORDS or prev in KEEP_THING_CONTEXT.get(head, ()):
        return None
    if (head in KEEP_REFUSED_PEOPLE or head in RELATIVE_NAME_WORDS or head in KEEP_PERSON_WORDS
            or head in PERSON_HEADERS or head in RELATIVE_HEADERS or head in SELF_WORDS
            or head in CLINICAL_STAFF_WORDS or _role_word(head, PERSON_ROLE_WORDS)
            or _role_word(head, HEAD_ROLE_WORDS) or _agent_noun(head)):
        return head
    return None


def _person_value(v: str) -> bool:
    """A value that can be a person's name: a word of two or more letters, with or without digits beside
    it ("Lee Ana", "Lee Ana 45", "Lee (wife)"), or text in a script without capital letters; not a number, a
    code ("S-014", "PT0042", "sub-01") or category words (round 5)."""
    v = _plain(v)
    if has_caseless_text(v):
        return True
    if not re.search(r"[^\W\d_]{2,}", v) or is_number(v):
        return False
    if re.fullmatch(r"[A-Za-z]{1,4}[-_]?\d[\dA-Za-z_-]*|[A-Z]{1,5} \d[\dA-Z-]*", v):
        return False
    return not _category_or_count(v)


def _clinical_staff(t: list[str], head: str) -> bool:
    word = head[:-1] if head.endswith("s") and head[:-1] in CLINICAL_STAFF_WORDS else head
    return (word in CLINICAL_STAFF_WORDS or word.endswith("therapist")
            or (len(t) > 1 and (t[-2], head) in CLINICAL_STAFF_PAIRS))


# Round 6: --keep refused only when the LAST word of a column name named a person, so a column whose
# person word came first and whose last word named a part of a name was kept on the person's word
# (Patient Last, Mother First, Spouse Last, Kin Last, Caregiver First, Pat Info, MotherLast, pat_last), and
# so were abbreviations of a name (PatNm, PNm, FNm, LNm, Donor_Nm) and In-law: 604 spellings in one sweep.
# Refusal is now decided on the set of the name's words: a word for someone who is not clinical or care
# staff ANYWHERE in the name refuses --keep when a value can be a person's name and either another word
# names a name or a part of one (First, Last, Sur, Nm, Initials, ...), or every other word says nothing
# of what the column holds (Info, Text, Ref, Label, Desc, Detail, Key, ...). A word that says what the
# column holds about that person (Patient Status, Mother Diagnosis, Family History, Contact Method)
# leaves it to the person's word, as before. An abbreviation of a name (Nm, Nme, Nam, PNm, FNm, LNm)
# refuses --keep whenever a value is a word, unless the name names a thing (Drug Nm) and no person.
KEEP_PERSON_ANYWHERE = (KEEP_REFUSED_PEOPLE | RELATIVE_NAME_WORDS | frozenset(PERSON_HEADERS)
                        | frozenset(RELATIVE_HEADERS) | SELF_WORDS | frozenset("""
pat pats pnt pnts ptnt ptnts pac pts inlaw inlaws stepson stepdaughter stepchild stepchildren stepbrother
stepsister halfbrother halfsister godchild dependant dependants
""".split()) | KEEP_PERSON_WORDS) - frozenset("""
charge admin admins kind controls party parties relation relations related relationship driver
""".split())
NAME_PART_WORDS = frozenset("""
first last given middle maiden sur surname surnames forename forenames firstname lastname fullname givenname
familyname name names nam nme nm nombre nombres apellido apellidos nom prenom vorname nachname cognome
initial initials nick nickname nicknames alias called full
""".split())
NAME_ABBREVIATIONS = frozenset("""
nm nme nam pnm fnm lnm gnm snm mnm ptnm patnm pnam fnam lnam gnam snam fnme lnme ptnme fname lname gname
sname mname pname
""".split())
# Words that say nothing of what a column holds about someone: a label, a reference, a description.
KEEP_EMPTY_WORDS = KEEP_TRAILING_WORDS | frozenset("""
label labels ref refs reference references desc descr description descriptions detail details info
information text txt display title titles string str id ids ident identity identification key keys who
record records s of the a an and or de du des del la le el di da do der die das von van y e et und
""".split())


def _keep_people_anywhere(t: list[str]) -> tuple[set[str], set[int]]:
    """The words of a column name, anywhere in it, that name someone who is not clinical or care staff
    (round 6), with adjacent words joined ("In-law", "Step Son"), and the positions of the tokens they
    cover. "Resident" names a care home's resident as often as a physician, so beside a word for a name
    or a word that says nothing else (Info, Text) it counts as a person ("Resident Last", "Resident Info")."""
    found, covered = set(), set()
    names = bool(set(t) & (NAME_PART_WORDS | NAME_ABBREVIATIONS))
    empty = bool(set(t) & (KEEP_EMPTY_WORDS - {"s", "of", "the", "a", "an", "and", "or"}))
    for i, x in enumerate(t):
        for w, span in ((((t[i - 1] + x) if i else ""), {i - 1, i}), (x, {i})):
            if not w:
                continue
            staff = _clinical_staff(t[:i + 1], w) and not ((names or empty) and w in ("resident", "residents"))
            if (w in KEEP_PERSON_ANYWHERE or w in PERSON_ROLE_WORDS
                    or (w.endswith("s") and w[:-1] in PERSON_ROLE_WORDS)) and not staff:
                found.add(w)
                covered |= span
                break
    return found, covered


def _keep_long_number(v: str) -> bool:
    """A value that is a whole number of five or more digits in any written form ("4527832", "00088221",
    "-4527832", "4527832.", "4527832.0", "4.52783E+06"), or a number with seven or more digits before its
    point ("4527832.5"): a possible record, account or health number (round 6)."""
    n = number_like(v)
    if n is None or n != _plain(v).replace(",", ""):
        return False
    m = re.fullmatch(r"[+-]?(\d+)(\.\d*)?", n)
    if m:
        frac = (m.group(2) or ".").strip(".").strip("0")
        return len(m.group(1)) >= (7 if frac else 5)
    # An exponent keeps a record number's digits only with five or more of them ("4.52783E+06", "1.23553E+05");
    # a measurement of two or three ("1.37E+06" copies/mL) is not one.
    mantissa = re.split(r"[eE]", n)[0].lstrip("+-").replace(".", "").strip("0")
    try:
        return len(mantissa) >= 5 and 1e4 <= abs(float(n)) < 1e16
    except ValueError:
        return False


# Round 6: the numbers of a thing that is not a person or a record, which --keep may keep however long:
# genes, probes, code systems, batches, plates, sites, genomic positions and literature identifiers.
KEEP_NUMBER_THINGS = (RECORD_NUMBER_EXEMPT - frozenset("""
item items question questions form forms variable variables field fields column columns version page pages
""".split())) | frozenset("""
start end stop begin offset locus loci bp basepair basepairs coordinate pmid pubmed pmcid doi taxon taxid
ncbi geneid hgnc mim cosmic clinvar dbsnp procedure procedures proc hcpcs drg
""".split())
# (A generic word, Field, Item, Variable or Column, says nothing of whose number it is.)
# Round 6: places that are not places of care. --keep refused only a home, an address and the identifier
# words of step 1, and the review kept towns under Home Area, Lives, Living, Community, Catchment Area,
# Service Area, Area, Locale, Territory, Geography, Location, Place, Venue and Ort. An area, a community, a
# place or where someone lives holds a place smaller than a state as often as not, so --keep refuses it when
# a value can be a place's name. Places of care (Hospital, Clinic, Site, Ward, Unit, Department), a location
# or a destination, which usually name one (Visit Location, Discharge Destination), and state-level areas
# (Region, Province, Prefecture) can still be kept on the person's word.
KEEP_REFUSED_PLACES = frozenset("""
area areas locale locales territory territories catchment catchments community communities lives living
resides residing residence residences residential domicile geography geographic geographical geo place places
venue venues where lugar lugares lieu lieux luogo luoghi ort orte ortschaft gemeinde comune localidad localite
localita neighborhood neighbourhood neighborhoods neighbourhoods barrio quartier vicinity hamlet
""".split())
# Round 6: words for a record, a chart or a file. A value that can be a person's name under one of them is
# the label the record is filed under (Cartella, Chart, Dossier), so --keep refuses it.
KEEP_REFUSED_RECORDS = frozenset("""
record records chart charts dossier dossiers akte akten expediente expedientes prontuario cartella cartelle
historia folio ficha fichas registry registro registros file files folder folders
""".split())


# Round 7: words for a person or a place that the lists above read as ordinary words, refused under --keep
# when a value is a word: as the last word of the name, or as the whole name for the words that have an
# ordinary sense as part of a longer one ("Vital Sign", "AV Block", "Tumor Origin").
KEEP_PERSON_HEADS = frozenset("signed signee signees signatory signatories salutation salutations resp".split())
KEEP_PERSON_WHOLE = frozenset("sign mi to from cc attn".split())
KEEP_PLACE_HEADS = frozenset("shelter shelters building buildings map maps geolocation".split())
KEEP_PLACE_WHOLE = frozenset("block origin".split())
# Digits written for letters ("N4me", "F1rst", "M0ther"), read back as the word they spell.
LEET_DIGITS = ({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}, {"1": "l"})
KEEP_LEET_WORDS = (NAME_PART_WORDS | NAME_ABBREVIATIONS | KEEP_PERSON_ANYWHERE | KEEP_REFUSED_PEOPLE
                   | KEEP_REFUSED_THINGS | KEEP_REFUSED_PLACES | KEEP_REFUSED_RECORDS)


def _leet_spellings(header: str) -> list[str]:
    """The column name with each word that mixes letters and digits and spells a word for a person, a name,
    a thing or a place once its digits are read as letters written that way ("Patient N4me" is "Patient
    name"); empty when no word does (round 7)."""
    out = []
    for extra in ({}, LEET_DIGITS[1]):
        table = {**LEET_DIGITS[0], **extra}

        def spell(m: re.Match) -> str:
            w = m.group(0)
            if not (re.search(r"[a-z]", w, re.I) and re.search(r"\d", w)):
                return w
            read = "".join(table.get(c, c) for c in w.lower())
            return read if read.isalpha() and read in KEEP_LEET_WORDS else w
        spelled = re.sub(r"[A-Za-z0-9]+", spell, str(header))
        if spelled != str(header) and spelled not in out:
            out.append(spelled)
    return out


def keep_refusal(header: str, values: list[str], scrubber: "Scrubber | None" = None) -> str | None:
    """Why --keep cannot keep a column the script could not verify, or None: judged by its name, and for a
    column named for someone, by whether a value is a word (numbers and codes such as S-014 can be kept, as
    under a relative's name; person_name_rule). Names kinds only, never the column name or a value."""
    for spelled in _leet_spellings(header):
        why = keep_refusal(spelled, values, scrubber)
        if why:
            return why + " (with the digits of its name read as the letters they stand for)"
    if not header_known(header):
        return ("a word in its name is not a column word the script knows, so it cannot tell that the name "
                "does not mean a person, a relative, a contact, an address, a record number or another "
                "identifier (in another language, say)")
    t = [x for x in column_tokens(header) if not x.isdigit() and not re.fullmatch(r"\d+(?:st|nd|rd|th)", x)]
    every = list(t)
    while len(t) > 1 and (t[-1] == "s" or t[-1] in KEEP_TRAILING_WORDS):
        t.pop()  # a possessive ("Mother's"), or a word that says nothing of whose ("Twin Info")
    raw = " ".join(re.split(r"[\s_\-/,;:()\[\].]+", unicodedata.normalize("NFKC", str(header)).casefold())).strip()
    vals = _shape_values(values)
    words = any(_person_value(v) for v in vals)
    if any(raw.endswith(w) for w in KEEP_REFUSED_SCRIPTS) and words:
        return "its name names the person, or notes or remarks, and a value is a word"
    # Round 6: numbers of five or more digits are kept on the person's word only under a column name that
    # names a measurement or the number of a thing (Gene ID, Lot No, Position): under any other name they
    # can be record, account or health numbers (PHN, NHS, NIP, Patid, Registration, Token, Code1, Value),
    # and the person confirming that a column holds no record numbers cannot be relied on to know that
    # the name is one.
    people, covered = _keep_people_anywhere(every)
    # A number the scrub replaces in a kept column anyway (a telephone number, nine or more digits) is not
    # one the person's word has to cover.
    if any(_keep_long_number(v) and not (scrubber and scrubber.find(v)) for v in vals) \
            and not measurement_header(header) \
            and not (set(every) & KEEP_NUMBER_THINGS and not people):
        return ("its values are numbers of five or more digits and its name names no measurement, so they can "
                "be record, account or health plan numbers (a measurement name such as Count, Steps, Cost or "
                "WBC, or a unit in brackets, says they are not)")
    if not t:
        return None
    head, whole = t[-1], " ".join(t)
    person = _keep_person_head(t)
    if ((person and not _clinical_staff(t, person)) or set(raw.split()) & set(KEEP_PERSON_WORDS_SCRIPTS)) and words:
        return ("its name names someone other than clinical or care staff (only a physician, a nurse, a surgeon, "
                "a clinician, a provider, a pharmacist, a therapist, a technician, a midwife and similar roles can "
                "be kept on the person's word; not the person, a relative, a contact, a reporter, an author, a "
                "manager, an agent or anyone else)")
    ts = set(every)
    others = [x for i, x in enumerate(every) if i not in covered and x not in NAME_PART_WORDS
              and x not in KEEP_EMPTY_WORDS and x not in NAME_ABBREVIATIONS and len(x) > 1]
    if words and people and (ts & NAME_PART_WORDS or ts & NAME_ABBREVIATIONS or not others):
        return ("its name names someone other than clinical or care staff and, in its other words, a name or a "
                "part of one, or nothing else (Patient Last, Mother First, Kin Info, PatNm): such a column holds "
                "that person's name")
    if words and ts & NAME_ABBREVIATIONS and (any(len(x) == 1 for x in every) or not ts & set(NOT_A_PERSON_NAME)):
        return "its name is an abbreviation of a name (Nm, PNm, FNm, LNm), and a value is a word"
    if words and not others and (ts & NAME_PART_WORDS or (any(len(x) == 1 and x.isalpha() for x in every)
                                                          and ts & KEEP_EMPTY_WORDS)) \
            and not ts & set(NOT_A_PERSON_NAME):
        return ("its name names a name or a part of one, or a letter (P Info, M Text), and nothing else, and a "
                "value is a word")
    if head in KEEP_REFUSED_THINGS or whole in KEEP_REFUSED_WHOLE or ts & {
            "alias", "aka", "nickname", "pseudonym", "moniker", "kana", "furigana", "pinyin", "romaji",
            "romanized", "romanised", "address", "addresses", "email", "courriel", "correo", "hostname"}:
        return ("its name names an employer, a school, a home, an address, a telephone, an email or web "
                "address, a device, an image, another name for the person, or notes, which hold free text")
    if words and (head in KEEP_REFUSED_PLACES or ts & {"lives", "living", "resides", "residing", "residence",
                                                        "residential", "domicile", "wohnort", "where"}
                  or ("home" in ts and ts & KEEP_REFUSED_PLACES)):
        return ("its name names a place that is not a place of care (an area, a community, a place, where the "
                "person lives), which can be a place smaller than a state, and a value is a word; a place of care "
                "(Hospital, Clinic, Site, Ward, Unit), a location or a state-level region can be kept")
    if words and head in KEEP_REFUSED_RECORDS:
        return "its name names a record, a chart or a file, and a value is a word (the name it is filed under)"
    if words and (head in KEEP_PERSON_HEADS or whole in KEEP_PERSON_WHOLE
                  or ("source" in ts and ts & {"history", "hx", "historian"})):
        return ("its name names someone other than clinical or care staff (who signed, who is addressed, a middle "
                "initial, the source of a history, the person responsible), and a value is a word")
    if words and (head in KEEP_PLACE_HEADS or whole in KEEP_PLACE_WHOLE or ts & {"geo", "gps", "geolocation"}
                  or ("institution" in ts and ts & {"education", "educational", "school", "academic"})):
        return ("its name names a place that is not a place of care (a map or a geographic location, a shelter, a "
                "building, a block, an origin, a school), which can be a place smaller than a state, and a value "
                "is a word")
    return None


def locale_name_rule(header: str, locale: dict) -> tuple[str, str, str] | None:
    """Exact matches against the locale pack's own column names (Korean, Japanese, ...)."""
    norm = upstream._normalize_col(str(header))
    phi = (locale.get("column_names") or {}).get(norm)
    if not phi:
        return None
    if norm in ("state",):
        return ("state or country (allowed)", "keep", "allowed_geography")
    action = {"name": "pseudonym_name", "id": "pseudonym_id", "date": "year"}.get(phi, "redact")
    if phi == "address" and norm in ("zip", "zipcode", "zip_code"):
        action = "zip3"
    return (f"{phi} (locale column name)", action, phi)


def is_number(v: str) -> bool:
    v = v.strip()
    return len(v) <= 60 and bool(NUMBER.fullmatch(v))


def _shape_values(values: list[str]) -> list[str]:
    """The values a shape rule looks at: no blanks, placeholders or missing-value words."""
    return [v.strip() for v in values
            if v.strip() and not PLACEHOLDER.fullmatch(v.strip()) and v.strip().lower() not in MISSING_VALUES]


# Category words: a value made only of these is a coded vocabulary, not a name.
CATEGORY_WORDS = frozenset("""
male female man woman men women boy girl other others intersex nonbinary non-binary transgender
trans cisgender yes no y n true false t f present absent positive negative pos neg detected
undetected reactive nonreactive non-reactive normal abnormal high low medium mid moderate mild
severe critical none any some all ok done pending complete completed incomplete partial final
preliminary active inactive resolved chronic acute alive dead deceased living expired died
death survived never former current ever past daily weekly monthly occasional occasionally
quit smoker nonsmoker non-smoker smoking drinker nondrinker heavy light white black asian
african american indian alaska alaskan native hawaiian pacific islander hispanic latino
latina latinx non-hispanic caucasian multiracial multiple race mixed middle eastern arab
south east north west southeast southwest northeast northwest central single married
divorced widowed separated partnered domestic partner left right bilateral both midline
unilateral placebo control controls case cases treatment treated untreated intervention
exposed unexposed baseline screening follow-up followup randomized randomised enrolled
withdrawn ongoing terminated inpatient outpatient emergency ambulatory observation elective
urgent routine hospice rehab rehabilitation home nursing facility skilled health care
discharged transferred admitted english spanish chinese mandarin cantonese vietnamese
tagalog korean russian arabic french german portuguese japanese hindi italian polish
monday tuesday wednesday thursday friday saturday sunday january february march april may
june july august september october november december spring summer autumn fall winter
mother father parent parents spouse sibling child son daughter brother sister grandparent
grandmother grandfather guardian friend self relative husband wife aunt uncle cousin
not or and of to the a an in on with without unknown declined refused missing applicable
available reported stated prefer say decline answer family household multi nuclear extended
physician physicians doctor nurse nurses practitioner practitioners assistant assistants
resident residents fellow fellows attending intern interns student students technician
technologist pharmacist therapist midwife dentist surgeon clinician provider staff specialist
consultant hospitalist md np pa rn lpn cna do registered licensed certified vocational
medicine surgery surgical medical internal general primary secondary tertiary specialty
practice department dept clinic unit service ward center centre hospital office telehealth
telemedicine virtual visit phone telephone email mail letter text video portal
breast lung lungs colon rectum rectal colorectal prostate pancreas pancreatic liver hepatic
kidney kidneys renal bladder brain spine spinal skin bone bones marrow blood heart cardiac
stomach gastric esophagus esophageal ovary ovarian uterus uterine cervix cervical thyroid
neck chest abdomen abdominal pelvis pelvic lymph node nodes muscle joint knee hip shoulder
ankle elbow eye ear nose throat mouth tongue soft tissue upper lower anterior posterior
lateral medial proximal distal small large cell cells icu nicu picu micu sicu cvicu ccu pacu
neuro labor delivery stepdown step-down telemetry floor wing virus
alone children siblings sons daughters brothers sisters grandchildren grandchild roommate roommates
friends girlfriend boyfriend fiance fiancee niece nephew stepmother stepfather stepparent independently
assisted adult adults infant infants baby babies teen teens elderly
catholic protestant christian muslim islam jewish judaism hindu hinduism buddhist buddhism
sikh atheist agnostic mormon lds baptist methodist lutheran orthodox evangelical presbyterian
episcopalian pentecostal adventist quaker unitarian spiritual nonreligious religious
""".split()) | frozenset("""
first second third fourth fifth sixth seventh eighth ninth tenth next last initial subsequent
one two three four five six seven eight nine ten more less double triple races patient patients
pt new up follow end study early late termination unscheduled scheduled week weeks month months
day days year years hour hours cycle course wave round period session time pre post op peri
intra interim washout extension open label blind standard usual dose doses dosage arm arms
cohort group groups team teams alpha beta gamma delta phase stage grade class level risk long
term short life common law gender fluid queer genderqueer agender questioning sign language
haitian creole farsi persian urdu punjabi bengali gujarati tamil telugu thai lao khmer hmong
somali amharic tigrinya swahili yoruba igbo hausa ukrainian armenian greek hebrew turkish
dutch swedish norwegian danish finnish hungarian czech romanian serbian croatian bosnian
albanian burmese nepali indonesian malay samoan tongan marshallese chamorro ilocano cebuano
navajo asl medicare medicaid medi-cal commercial private public government federal state
self-pay selfpay uninsured insured underinsured hmo ppo epo pos tricare champva va veterans
workers compensation charity managed advantage supplemental dual eligible ineligible
nonprofit military employed unemployed self-employed retired disabled homemaker student
teacher engineer farmer laborer driver manager clerk lawyer accountant artist writer
programmer scientist researcher chef cook cashier mechanic electrician plumber carpenter
firefighter police soldier veteran salesperson sales retail construction service
healthcare education agriculture manufacturing urban rural suburban metropolitan frontier
remote midwest mountain coastal inland mobile landline work cell office mailing billing
temporary permanent valid invalid expired suspended revoked locked failed success
successful verified unverified enrolled terminated approved denied birth marriage
failure disease diseases disorder disorders syndrome fracture fractures injury injuries
infection infections deficiency insufficiency embolism stroke attack shock arrest fibrillation
flutter hypertension hypotension diabetes mellitus insipidus obesity overweight underweight
depression depressive anxiety dementia delirium seizure seizures epilepsy migraine headache
pain fever cough nausea vomiting diarrhea diarrhoea constipation bleeding hemorrhage haemorrhage
anemia anaemia sepsis septic pneumonia influenza flu covid sars asthma bronchitis emphysema
fibrosis cirrhosis hepatitis ulcer ulcers reflux hernia obstruction perforation stenosis
thrombosis aneurysm dissection ischemia ischaemia infarction infarct angina palpitations edema
oedema effusion nodule nodules mass masses lesion lesions cyst cysts polyp polyps tumor tumors
tumour tumours cancer cancers carcinoma sarcoma lymphoma leukemia leukaemia melanoma myeloma
metastasis metastases metastatic benign malignant malignancy neoplasm neoplasia adenoma squamous
ductal lobular invasive situ pulmonary coronary atrial ventricular arterial artery arteries
venous vein veins vascular cerebral cerebrovascular cardiovascular respiratory gastrointestinal
gi intestinal bowel urinary tract genital reproductive endocrine metabolic immune nervous
system systemic lupus arthritis gout sclerosis palsy apnea apnoea sleep insomnia cold throat
pink sickle cystic iron vitamin morbid peptic celiac coeliac lyme strep staph hay major minor
bipolar schizophrenia autism adhd ptsd ocd substance abuse dependence overdose withdrawal
poisoning burn burns wound wounds laceration contusion concussion sprain strain dislocation
amputation transplant rejection dialysis esrd ckd aki chf cad mi cva tia dvt pe afib hiv aids
hcv hbv tb tuberculosis essential idiopathic congenital hereditary familial genetic autoimmune
allergic viral bacterial fungal toxic traumatic alcoholic diabetic hypertensive ischemic
hemorrhagic obstructive restrictive interstitial inflammatory degenerative cognitive mental
behavioral behavioural psychiatric impairment decline loss hearing vision visual blindness
deafness disability delay developmental learning intellectual eating personality mood panic
phobia misuse opioid alcohol tobacco nicotine cannabis cocaine recurrent relapsed refractory
remission relapse progression progressive stable unstable controlled uncontrolled response
responder nonresponder equivocal indeterminate inconclusive borderline elevated decreased
increased reduced preserved ejection fraction systolic diastolic herpes zoster simplex
bifida phenomenon dysfunction degeneration macular tunnel carpal tremor exacerbation rule out
stemi nstemi hemoglobin haemoglobin hematocrit platelet platelets count counts wbc rbc cbc bmp
cmp sodium potassium chloride bicarbonate calcium magnesium phosphate phosphorus glucose
creatinine urea nitrogen bun albumin protein proteins bilirubin alkaline phosphatase alt ast
ggt ldh troponin lactate ferritin cholesterol triglycerides triglyceride hdl ldl vldl a1c hba1c
tsh insulin cortisol panel ratio culture cultures screen titer titre antibody antibodies
antigen pcr igg igm iga ige crp esr inr ptt bnp procalcitonin urinalysis urine serum plasma
stool sputum csf saliva swab biopsy aspirate fluid function lipid lipids basic comprehensive
differential smear gram stain sensitivity susceptibility fasting random total free direct
indirect x-ray xray radiograph ct mri pet ultrasound echo ecg ekg eeg emg scan imaging
resection repair replacement bypass graft stent intubation ventilation transfusion infusion
injection implant implantation removal drainage debridement excision incision reduction
fixation fusion cesarean caesarean section vaginal induction epidural anesthesia anaesthesia
sedation regional local block nerve physical occupational speech therapy therapies
rehabilitation progress note notes discharge summary consent report reports form forms order
orders referral admission h&p arm leg legs hand hands foot feet finger fingers toe toes forearm
thigh calf buttock back face facial head scalp nail heel antecubital deltoid gluteal flank
groin axilla axillary inguinal lobe lobes quadrant segment ventricle atrium aorta aortic valve
mitral tricuspid pulmonic temporal frontal parietal occipital cortex cerebellum brainstem
hippocampus thalamus amygdala striatum pituitary adrenal gland glands duodenum jejunum ileum
cecum appendix sigmoid ascending descending transverse anus anal trachea bronchus bronchial
larynx pharynx sinus sinuses mandible maxilla jaw teeth tooth oral dental gum gums lip lips
cheek nipple areola testis testicle scrotum penis vulva vagina endometrium fallopian tube tubes
placenta umbilical spleen splenic biliary bile duct ducts thymus peritoneum peritoneal pleura
pleural pericardium pericardial mediastinum diaphragm rib ribs sternum clavicle scapula humerus
radius ulna femur tibia fibula patella sacrum coccyx vertebra vertebrae disc retina retinal
cornea lens optic orbit hair fundus macula nasal tonsil tonsils parathyroid salivary parotid
lymphatic vessel vessels capillary superficial deep apex base root body tail dome wall line
lines intravenous subcutaneous intramuscular topical inhaled inhalation sublingual
transdermal enteral parenteral po sq sc im intrathecal ophthalmic buccal tablet tablets
capsule capsules solution suspension cream ointment patch spray drops syrup powder gel lotion
inhaler suppository mg ml mcg units extended release er xr sr ir aspirin warfarin morphine
fentanyl acetaminophen paracetamol naproxen tramadol codeine methadone buprenorphine naloxone
saline sulfate oxide hydrochloride citrate acetate carbonate gluconate succinate tartrate
maleate besylate mesylate fumarate bromide ferrous oil lactated ringers bid tid qid prn qd qhs
qam qpm stat proliferative nonproliferative mild-moderate team staff unit units care
inner outer curative palliative adjuvant neoadjuvant maintenance salvage confirmed suspected
probable possible presumed rash hives anaphylaxis itching swelling laparoscopic robotic
endoscopic percutaneous closed person in-person audio procedure procedures test tests exam
examination lab labs blue shield permanente unitedhealthcare anthem molina centene wellcare
ambetter highmark carefirst premera regence wellmark passport license licence mrn ssn itin
national visa card type types status statuses method methods mode modes category categories
class classes level levels code codes value values flag flags score scores result results
given held missed omitted administered documented instructions medication medications list
social ion channel channels transcription translation factor factors receptor receptors ligand
enzyme enzymes kinase kinases transporter hormone cytokine chemokine growth signaling
signalling domain binding membrane nuclear mitochondrial ribosomal coding noncoding rna dna
mrna mirna lncrna gene genes oncogene suppressor wild mutant variant variants deletion
insertion duplication amplification missense nonsense frameshift splice synonymous
pathogenic uncertain significance likely exon intron allele homozygous heterozygous
hemizygous germline somatic copy gain luminal basal enriched claudin checking savings
""".split()) | frozenset("""
escherichia klebsiella clostridioides candida aspergillus salmonella shigella listeria neisseria
haemophilus legionella proteus serratia morganella providencia bacteroides moraxella bordetella
treponema borrelia chlamydia chlamydophila mycoplasma ureaplasma pneumocystis toxoplasma giardia
vibrio yersinia brucella francisella bartonella rickettsia coxiella nocardia actinomyces gardnerella
prevotella veillonella kingella eikenella aggregatibacter coli aureus difficile pylori pneumoniae
aeruginosa epidermidis faecalis faecium influenzae albicans glabrata auris cloacae mirabilis
marcescens baumannii maltophilia fragilis perfringens gonorrhoeae trachomatis pallidum burgdorferi
jejuni enterica typhi typhimurium cholerae monocytogenes agalactiae pyogenes mutans viridans
lugdunensis saprophyticus oxytoca freundii aerogenes vulgaris catarrhalis meningitidis pertussis
parainfluenzae neoformans fumigatus jirovecii falciparum vivax gondii lamblia histolytica vaginalis
hominis genitalium pneumophila avium kansasii abscessus leprae
""".split())
# Category words that are also common given names or surnames ("June", "White", "Ward",
# "Wing", "Long"). They do not stop a value from reading as a person's name.
NAME_LIKE_CATEGORY_WORDS = frozenset("""
may june april august white black ward wing case low long major summer autumn winter fall
north south east west northeast northwest southeast southwest central mass cole head
""".split())
# Multi-word state and country names, which Safe Harbor allows: not names or places of the
# kind a category check looks for.
STATE_COUNTRY_NAMES = frozenset(s.strip() for s in """
new hampshire|new jersey|new mexico|new york|north carolina|north dakota|rhode island|
south carolina|south dakota|west virginia|district of columbia|puerto rico|american samoa|
northern mariana islands|virgin islands|us virgin islands|united states|united states of america|
united kingdom|great britain|south africa|south korea|north korea|new zealand|saudi arabia|
sri lanka|costa rica|el salvador|dominican republic|czech republic|ivory coast|sierra leone|
burkina faso|papua new guinea|trinidad and tobago|bosnia and herzegovina|united arab emirates|
hong kong|cape verde|central african republic|equatorial guinea|east timor|timor-leste|
solomon islands|marshall islands|san marino|vatican city|south sudan|north macedonia|
antigua and barbuda|saint lucia|saint kitts and nevis|guinea-bissau|mainland china|
british columbia|new brunswick|nova scotia|prince edward island|northwest territories|
""".replace("\n", "").split("|") if s.strip())
# Word endings of medical vocabulary (specialties, diseases, procedures, drug stems), with
# the shortest word each one counts in. No given name or surname in common use ends this
# way at that length: "Ingram" is too short for -gram, Lithuanian surnames in -aitis are
# not -itis.
CLINICAL_ENDINGS = (
    ("ology", 7), ("ologic", 8), ("ological", 9), ("iatry", 7), ("iatric", 8), ("iatrics", 9),
    ("itis", 6), ("osis", 7), ("emia", 6), ("aemia", 7), ("oma", 7), ("omas", 8), ("ectomy", 8),
    ("otomy", 7), ("ostomy", 8), ("plasty", 8), ("scopy", 8), ("graphy", 8), ("gram", 8),
    ("pathy", 7), ("algia", 7), ("plegia", 8), ("penia", 8), ("trophy", 7), ("uria", 7),
    ("ism", 6), ("mab", 7), ("tinib", 7), ("pril", 7), ("olol", 7), ("statin", 8),
    ("sartan", 8), ("cillin", 8), ("mycin", 8), ("oxacin", 9), ("azole", 8), ("tidine", 9),
    ("dipine", 9), ("formin", 8), ("gliptin", 9), ("glitazone", 11), ("gliflozin", 11),
    ("glutide", 9), ("parin", 7), ("platin", 9), ("taxel", 9), ("rubicin", 10), ("ovir", 8),
    ("avir", 8), ("ivir", 8), ("ercept", 9), ("dronate", 9), ("semide", 9), ("thiazide", 10),
    ("oxetine", 9), ("azepam", 9), ("triptan", 10), ("lukast", 10), ("olone", 9), ("isone", 9),
    ("profen", 9), ("fenac", 9), ("coxib", 9), ("caine", 9), ("codone", 9), ("phylline", 10),
    ("terol", 9), ("tropium", 10), ("cycline", 10), ("penem", 9), ("bactam", 10), ("xaban", 8),
    ("gatran", 10), ("parib", 9), ("ciclib", 10), ("lisib", 9), ("tecan", 10), ("poside", 9),
    ("fosfamide", 12), ("phosphamide", 14), ("trexate", 11), ("abine", 9), ("sertib", 10),
    ("zole", 8), ("xifen", 9), ("coccus", 9), ("cocci", 8), ("bacter", 10), ("monas", 10),
    ("bacillus", 10),
    # Adjectives and nouns of anatomy, disease and chemistry: fibrillation, ventricular,
    # ischemic, diabetic, psychotic, pancreatic, dialysis, psoriasis, metastasis, obstructive,
    # progressive, fracture, lipase, calcium, steroid, sputum, cholesterol, chloride, sulfate.
    ("ation", 8), ("ular", 7), ("emic", 7), ("etic", 7), ("otic", 7), ("atic", 7), ("ysis", 7),
    ("iasis", 8), ("tasis", 8), ("ctive", 8), ("ssive", 8), ("ture", 7), ("ase", 6), ("ium", 7),
    ("oid", 6), ("tum", 6), ("llum", 8), ("erol", 8), ("adol", 8), ("diol", 8), ("anol", 7),
    ("oride", 7), ("ptide", 7), ("phate", 7), ("lfate", 7), ("trate", 7), ("etate", 7),
    ("onate", 9),
)
NOT_CLINICAL = frozenset({"euphemia", "bohemia"})


def _clinical_word(w: str) -> bool:
    if w in NOT_CLINICAL or (w.endswith("itis") and w[-5:-4] in ("a", "y")):
        return False
    return any(len(w) >= n and w.endswith(end) for end, n in CLINICAL_ENDINGS)


# "site" says what category its values are only after a word that makes it a body site.
CATEGORY_HEADER_PHRASES = ("primary site", "tumor site", "tumour site", "body site", "anatomic site",
                           "anatomical site", "biopsy site", "injection site", "infection site",
                           "surgical site", "metastatic site", "metastasis site", "lesion site",
                           "cancer site", "disease site", "cell line", "cell lines", "cell type")
# A column whose values repeat like a category: at most this many distinct values, or
# every distinct value seen at least this many times on average.
CATEGORY_MAX_DISTINCT = 20
CATEGORY_MIN_REPEATS = 3
NAME_PARTICLES = frozenset({"van", "von", "de", "der", "den", "da", "di", "del", "della", "dos",
                            "du", "la", "le", "bin", "ibn", "al", "el", "y", "e", "st", "ter",
                            "ten", "ap"})


def _is_category_value(v: str) -> bool:
    words = re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", v.lower())
    return bool(words) and not re.search(r"\d", v) and all(
        w in CATEGORY_WORDS or _clinical_word(w) for w in words)


# Scripts written without capital letters (Chinese, Japanese, Korean, Arabic, Hebrew, the
# Indic scripts, Thai, Georgian, ...) give a name no shape that tells it from a category
# word, so a short value in one is read as a possible name or place, unless it is one of
# these common category words (sex, yes and no, positive and negative, unknown, ...).
CASELESS_CATEGORY_VALUES = frozenset("""
男 女 男性 女性 是 否 有 无 無 未知 不详 不詳 不明 阳性 阴性 陽性 陰性 正常 异常 異常 左 右 双侧 雙側 両側
高 中 低 轻 輕 重 轻度 輕度 中度 重度 已婚 未婚 离异 離異 丧偶 喪偶 门诊 門診 住院 急诊 急診 外来 入院 存活
死亡 生存 甲 乙 丙 丁 はい いいえ あり なし
남 여 남성 여성 남자 여자 예 아니오 아니요 네 있음 없음 양성 음성 정상 비정상 미상 모름 외래 입원 생존 사망
ذكر أنثى انثى نعم لا مجهول ايجابي إيجابي سلبي طبيعي
זכר נקבה כן לא חיובי שלילי תקין
पुरुष महिला स्त्री हाँ हां नहीं अज्ञात सकारात्मक नकारात्मक सामान्य
ชาย หญิง ใช่ ไม่ใช่ ไม่ ไม่ทราบ บวก ลบ ปกติ ผิดปกติ
مرد زن بله خیر عورت ہاں نہیں
""".split()) | frozenset({"غير معروف", "לא ידוע"})
# Characters that join the letters of one word in these scripts: zero-width joiners,
# the katakana middle dot, the Arabic tatweel, apostrophes and hyphens.
CASELESS_JOINERS = frozenset("\u200c\u200d\u30fb\u00b7\u2027\u0640'\u2019-")
CASELESS_SPLIT = re.compile("[\\s,;/\u060c\u3001\uff0c]+")


def _caseless_letter(c: str) -> bool:
    """A letter of a script that has no capital letters."""
    if c.isascii():
        return False
    if "\u10d0" <= c <= "\u10ff":
        return True  # Georgian, whose capitals are not used in names
    return (c.isalpha() and c.upper() == c == c.lower()
            and not unicodedata.name(c, "").startswith("LATIN"))


def _caseless_word(w: str) -> bool:
    letters = 0
    for c in w:
        if _caseless_letter(c):
            letters += 1
        elif not (c in CASELESS_JOINERS or unicodedata.category(c).startswith("M")):
            return False
    return letters > 0


def _ideograph(c: str) -> bool:
    """One of these characters can be a whole surname or given name."""
    return unicodedata.name(c, "").startswith(("CJK UNIFIED", "CJK COMPATIBILITY IDEOGRAPH",
                                               "HANGUL SYLLABLE", "HIRAGANA", "KATAKANA"))


def has_caseless_text(v: str) -> bool:
    return any(_caseless_letter(c) for c in v)


def caseless_name_shaped(value: str) -> bool:
    """True for one to four words with no digit, one of which is written in a script that
    has no capital letters and is not a common category word ("林子涵", "محمد الحسن",
    "Dr 박지훈", "seen by 박지훈"). In these scripts a name cannot be told from any other
    word by its shape, so a column of them is redacted unless the person keeps it."""
    s = value.strip()
    if not s or re.search(r"\d", s) or PLACEHOLDER.search(s) or s in CASELESS_CATEGORY_VALUES:
        return False
    words = [w for w in CASELESS_SPLIT.split(s) if w]
    if not 1 <= len(words) <= 4:
        return False
    for w in words:
        if w in CASELESS_CATEGORY_VALUES or not _caseless_word(w):
            continue
        letters = [c for c in w if _caseless_letter(c)]
        if len(letters) >= 2 or _ideograph(letters[0]):
            return True
    return False


def caseless_prose(value: str) -> bool:
    """Text in a script without capital letters that reads as a sentence: these scripts
    (Chinese, Japanese, Thai) put no space between words, so it is found by its length,
    15 letters in one run or 40 in all, where a name or a category word is shorter."""
    counts = [sum(1 for c in w if _caseless_letter(c)) for w in value.split()]
    return bool(counts) and (max(counts) >= 15 or sum(counts) >= 40)


def name_shaped(value: str) -> bool:
    """True for one to four capitalised words ("Alice", "Bob Zeller", "Zeller, Alice",
    "O'Brien", "ZELLER ALICE", "San Francisco") that are not all category words, and for
    short values written in a script without capital letters (caseless_name_shaped)."""
    s = value.strip()
    if not s or PLACEHOLDER.search(s) or s.lower() in MISSING_VALUES or _is_category_value(s):
        return False
    if caseless_name_shaped(s):
        return True
    words = [w for w in re.split(r"[\s,]+", s) if w]
    if not 1 <= len(words) <= 4:
        return False
    title = caps = 0
    for i, w in enumerate(words):
        core = re.sub(r"['’.-]", "", w)
        if not core or not core.isalpha():
            return False
        if i and w.lower() in NAME_PARTICLES:
            continue
        if i and w in ("family", "household"):
            continue  # "Okafor family"
        if len(core) == 1:
            if not core.isupper():
                return False
        elif core[0].isupper() and any(c.islower() for c in core[1:]):
            title += 1
        elif core.isupper():
            caps += 1
        else:
            return False
    # An all-capital word alone is more often a code ("COPD", "ICU") unless it is long.
    return bool(title or caps >= 2 or (caps == 1 and len(words) == 1 and len(words[0]) >= 4))


def is_allowed_geography(header: str) -> bool:
    """A state or country column, which Safe Harbor allows to be kept."""
    rule = name_rule(header)
    return bool(rule) and rule[2] == "allowed_geography"


# Credentials and suffixes written after a name ("Okafor, Alice MD", "Bob Zeller Jr").
NAME_SUFFIXES = frozenset("""
md do rn np pa pac phd mph dds dmd pharmd dnp lpn cna crna msn bsn mba ms ma bs ba jr sr ii iii
iv esq mbbs frcp facs facp od dpm lcsw psyd
""".split())


def _vocabulary_word(w: str) -> bool:
    """A category, medical or anatomical word, or a plural or hyphenated form of one."""
    def known(x: str) -> bool:
        return x in CATEGORY_WORDS or _clinical_word(x)
    if known(w) or (len(w) > 3 and w.endswith("s") and known(w[:-1])):
        return True
    parts = [p for p in re.split(r"['\u2019-]", w) if p]
    return len(parts) > 1 and any(known(p) for p in parts)


def name_or_place_like(value: str) -> bool:
    """True for two or more capitalised words none of which is a category, medical or
    anatomical word: the shape of a person's name ("Alice Okafor", "Okafor, Alice B.",
    "OKAFOR ALICE", "Alice Okafor MD", "A. Okafor") or a place's ("Walnut Grove"). A category value
    almost always holds one such word ("Heart Failure", "Treatment A", "Left Upper Lobe"),
    and state and country names are allowed."""
    s = value.strip()
    if not s or re.search(r"\d", s) or PLACEHOLDER.search(s) or s.lower() in STATE_COUNTRY_NAMES:
        return False
    words = [w for w in re.split(r"[\s,;/]+", s) if w]
    if not 2 <= len(words) <= 6:
        return False
    core = []
    dotted_initial = False
    for w in words:
        letters = re.sub(r"['\u2019.-]", "", w)
        if not letters.isalpha():
            return False
        low = w.lower().strip(".")
        if len(letters) == 1:
            if not letters.isupper():
                return False
            dotted_initial = dotted_initial or w.endswith(".")
            continue  # an initial
        if low in NAME_PARTICLES or low.replace(".", "") in NAME_SUFFIXES:
            continue
        if not (letters[0].isupper() and (letters.isupper() or any(c.islower() for c in letters[1:]))):
            return False  # a word in lower case
        if low not in NAME_LIKE_CATEGORY_WORDS and _vocabulary_word(low):
            return False
        core.append(letters)
    # One name and an initial written with its full stop ("A. Okafor", "Alice O.", "Okafor,
    # A.") is a name too; a category letter has no full stop ("Treatment A", "Plan B").
    return (len(core) >= 2 or (len(core) == 1 and dotted_initial)) and max(len(c) for c in core) >= 3


# ================================================================ verification (fail closed)
# A default run keeps a column that no rule above names as an identifier only when it can
# positively verify every value that is not blank as one of:
#   (a) a number (with an optional comparator and unit) that passes the numeric identifier
#       checks (value_shape_rule, unique numbers, coordinate pairs);
#   (b) a value of a closed code grammar (ICD-9 and ICD-10, LOINC, ATC, HGVS, rsID, Ensembl,
#       RefSeq, TNM, a stage, a grade, ECOG or Karnofsky, a blood group), none of which
#       accepts a bare alphabetic word;
#   (c) a whole value of a closed phrase vocabulary (sex and gender, yes and no, missing-value
#       words, US census race and ethnicity, result flags, laterality, response categories,
#       smoking status, units, and the common words of scripts without capital letters);
#       under a column name that names a person, a role, a relative, a contact or a place,
#       only the missing-value words count;
#   (d) a date, which the value rules reduce to the year, or a state or country name under
#       a state or country column.
# Every other text column is redacted, and the person keeps it with --keep once they confirm
# it. Three rounds of heuristics that tried to recognise every name in text did not converge
# (qualifiers, scripts without capitals, initials, lower case): the script no longer decides
# that text is free of identifiers.


def fold(v: str) -> str:
    """A value with case, width and spacing folded, for whole-value matching."""
    s = unicodedata.normalize("NFKC", str(v)).casefold().replace("_", " ").replace("&", " and ")
    s = " ".join(s.split())
    return re.sub(r"\s*/\s*", "/", s)


def _phrases(text: str) -> frozenset:
    return frozenset(fold(p) for p in text.split("|") if p.strip())


# Words that say a value is missing, unknown or none. These are the only vocabulary words
# that count under a column name naming a person, a role, a relative, a contact or a place.
MISSING_PHRASES = frozenset(fold(v) for v in MISSING_VALUES) | _phrases("""
unkn|u|not reported|not stated|not specified|unspecified|not assessed|not done|not tested|
not evaluated|not performed|not obtained|not asked|asked but unknown|not answered|no answer|
no data|no information|no info|blank|empty|(blank)|prefer not to say|prefer not to answer|
prefer not to disclose|choose not to disclose|declined to answer|declined to state|
declined to specify|patient declined|patient refused|refused to answer|don't know|do not know|
dont know|unable to determine|undetermined|unavailable|not given|not provided|other/unknown|
unknown/not reported|unknown or not reported|not applicable/unknown|unknown/declined|none known
""")
CASELESS_MISSING = frozenset("""
未知 不详 不詳 不明 无 無 なし 미상 모름 없음 مجهول לא ידוע अज्ञात ไม่ทราบ
""".split()) | frozenset({"غير معروف", "לא ידוע"})
SEX_GENDER = _phrases("""
male|female|m|f|man|woman|men|women|boy|girl|intersex|other|nonbinary|non-binary|non binary|
transgender|transgender male|transgender female|transgender man|transgender woman|trans male|
trans female|trans man|trans woman|ftm|mtf|female-to-male|male-to-female|female to male|
male to female|genderqueer|gender queer|gender non-conforming|gender nonconforming|agender|
two-spirit|two spirit|cisgender|cisgender male|cisgender female|cisgender man|cisgender woman|
cis male|cis female|genderfluid|gender fluid|questioning|x|undifferentiated|ambiguous|
masculino|femenino|hombre|mujer|varon|varón|mannlich|männlich|weiblich|divers|masculin|feminin|
féminin|homme|femme|maschio|femmina|maschile|femminile|feminino
""")
YES_NO = _phrases("yes|no|y|n|true|false|t|f|si|sí|ja|nein|oui|non|sim|nao|não|checked|unchecked")
# OMB race and ethnicity categories (1997 and the 2024 revision, with its detailed checkboxes),
# in the spellings exports use.
RACE_ETHNICITY = _phrases("""
white|black|black or african american|black or african-american|african american|african-american|
black/african american|asian|asian american|american indian or alaska native|
american indian or alaskan native|american indian/alaska native|american indian/alaskan native|
american indian|alaska native|alaskan native|native american|
native hawaiian or other pacific islander|native hawaiian and other pacific islander|
native hawaiian/other pacific islander|
native hawaiian or pacific islander|native hawaiian|other pacific islander|pacific islander|
asian or pacific islander|middle eastern or north african|middle eastern|north african|mena|
hispanic or latino|hispanic/latino|hispanic or latina|hispanic|latino|latina|latinx|latine|
not hispanic or latino|not hispanic/latino|non-hispanic|non hispanic|nonhispanic|not hispanic|
not latino|non-hispanic white|non-hispanic black|non-hispanic asian|white non-hispanic|
black non-hispanic|white, non-hispanic|black, non-hispanic|nh white|nh black|nh asian|caucasian|
some other race|other race|multiracial|multi-racial|multiple|multiple races|more than one race|
two or more races|two or more|mixed|mixed race|biracial|asian indian|chinese|filipino|japanese|
korean|vietnamese|other asian|samoan|chamorro|guamanian or chamorro|mexican|mexican american|
chicano|puerto rican|cuban|other hispanic|dominican|salvadoran|guatemalan|colombian|lebanese|
iranian|egyptian|syrian|moroccan|israeli|race unknown|unknown race|ethnicity unknown|api|aian|nhpi
""")
RESULT_FLAGS = _phrases("""
h|l|n|a|aa|hh|ll|hhh|lll|>|<|*|c|critical|crit|panic|high|low|normal|abnormal|abn|abnl|nl|wnl|
within normal limits|within normal range|out of range|in range|above normal|below normal|
above range|below range|abnormal high|abnormal low|critical high|critical low|very high|very low|
elevated|decreased|increased|reduced|raised|positive|negative|pos|neg|+|++|+++|++++|+/-|±|trace|
1+|2+|3+|4+|present|absent|detected|not detected|undetected|none detected|reactive|non-reactive|
nonreactive|non reactive|weakly reactive|indeterminate|equivocal|borderline|inconclusive|
invalid|valid|pending|final|preliminary|prelim|corrected|amended|cancelled|canceled|resulted|
susceptible|sensitive|intermediate|resistant|s|i|r|sdd|ns|non-susceptible|nonsusceptible|
confirmed|not confirmed|presumptive positive|presumptive negative|unremarkable
""")
LATERALITY = _phrases("""
left|right|bilateral|both|unilateral|midline|central|l|r|b|lt|rt|bil|bilat|left side|right side|
both sides|left and right|right and left|left-sided|right-sided|ipsilateral|contralateral
""")
RESPONSE = _phrases("""
cr|pr|sd|pd|ne|non-cr/non-pd|non-cr non-pd|ncr/npd|complete response|partial response|
stable disease|progressive disease|not evaluable|inevaluable|unevaluable|non-evaluable|
objective response|no response|minor response|mr|very good partial response|vgpr|
stringent complete response|scr|pathologic complete response|pathological complete response|
pcr|near complete response|complete remission|partial remission|cri|crh|mlfs|mrd negative|
mrd positive|mrd-negative|mrd-positive|responder|non-responder|nonresponder|non responder|
progression|no progression|relapse|relapsed|refractory|remission|icr|ipr|isd|iupd|icpd|improved|
unchanged|no change|worse|worsened|stable|resolved
""")
SMOKING = _phrases("""
never|never smoker|never smoked|non-smoker|nonsmoker|non smoker|former|former smoker|ex-smoker|
ex smoker|exsmoker|past smoker|quit|current|current smoker|current every day smoker|
current some day smoker|every day|everyday|some days|some day|daily|daily smoker|occasional|
occasional smoker|light smoker|heavy smoker|light tobacco smoker|heavy tobacco smoker|smoker|
smoker, current status unknown|unknown if ever smoked|ever|ever smoker|passive smoker|
secondhand smoke|second hand smoke|never vaper|former vaper|current vaper
""")
UNITS = _phrases("""
%|mg|g|kg|mcg|µg|ug|ng|pg|fg|ml|l|dl|cl|µl|ul|nl|mg/dl|g/dl|g/l|mg/l|µg/l|ug/l|ng/ml|ng/l|pg/ml|
µg/ml|ug/ml|mcg/ml|mg/ml|ug/dl|µg/dl|mcg/dl|mmol/l|µmol/l|umol/l|nmol/l|pmol/l|mol/l|meq/l|
mmol/mol|mosm/kg|mosm/l|iu|iu/l|iu/ml|miu/ml|miu/l|µiu/ml|uiu/ml|u/l|u/ml|ku/l|mu/l|mu/ml|units|
unit|u/day|units/day|mmhg|cmh2o|kpa|bpm|beats/min|/min|breaths/min|cm|mm|m|km|µm|um|nm|in|inch|
inches|ft|feet|lb|lbs|oz|kg/m2|kg/m²|g/m2|mg/m2|mg/kg|mcg/kg|µg/kg|ml/kg|ml/min|ml/min/1.73m2|
ml/min/1.73 m2|ml/min/1.73m²|ml/h|ml/hr|l/min|mg/day|mg/d|g/day|mg/24h|g/24h|mg/24 h|°c|°f|c|k|
sec|s|second|seconds|ms|msec|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|wk|wks|week|
weeks|mo|mos|month|months|y|yr|yrs|year|years|x10^9/l|10^9/l|x10^12/l|10^12/l|x10^3/µl|x10^3/ul|
10^3/µl|10^3/ul|k/µl|k/ul|k/mm3|x10^6/µl|10^6/µl|m/µl|m/ul|cells/µl|cells/ul|cells/mm3|/µl|/ul|
/mm3|/hpf|/lpf|fl|pg/cell|copies/ml|log copies/ml|log iu/ml|ratio|index|score|points|pts|mm/h|
mm/hr|g/kg|kcal|kcal/day|kj|mmol/kg|ppm|ppb|hz|db|mv|µv|uv|ma|gy|cgy|mgy|msv|bq|mbq|mci|mg/g|
mg/mmol|au/ml|eu/ml|times/day|x/day|/day|/week|/wk|per day|per week|puffs/day|cigarettes/day|
packs/day|pack-years|pack years|drinks/week|drinks/day|steps|steps/day|mm2|cm2|cm3|mm3|m2|ml/s
""")
VOCABULARY = (SEX_GENDER | YES_NO | RESULT_FLAGS | LATERALITY | RESPONSE | SMOKING | MISSING_PHRASES)

# States and countries, which Safe Harbor allows, for columns named for them (state, country,
# country of birth, nationality, ...): US states, territories and their postal codes, Canadian
# provinces, Australian states, and countries with their ISO 3166 codes.
GEOGRAPHY_NAMES = _phrases("""
alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|
idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|
minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|
new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|
south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|
wisconsin|wyoming|district of columbia|washington dc|washington d.c.|d.c.|puerto rico|guam|
us virgin islands|u.s. virgin islands|virgin islands|american samoa|northern mariana islands|
alberta|british columbia|manitoba|new brunswick|newfoundland and labrador|newfoundland|
nova scotia|ontario|prince edward island|quebec|québec|saskatchewan|northwest territories|
nunavut|yukon|new south wales|victoria|queensland|south australia|western australia|tasmania|
northern territory|australian capital territory|
afghanistan|albania|algeria|andorra|angola|antigua and barbuda|argentina|armenia|australia|
austria|azerbaijan|bahamas|the bahamas|bahrain|bangladesh|barbados|belarus|belgium|belize|benin|
bhutan|bolivia|bosnia and herzegovina|botswana|brazil|brunei|bulgaria|burkina faso|burundi|
cabo verde|cape verde|cambodia|cameroon|canada|central african republic|chad|chile|china|
people's republic of china|colombia|comoros|congo|republic of the congo|
democratic republic of the congo|dr congo|drc|costa rica|cote d'ivoire|côte d'ivoire|
ivory coast|croatia|cuba|cyprus|czechia|czech republic|denmark|djibouti|dominica|
dominican republic|ecuador|egypt|el salvador|equatorial guinea|eritrea|estonia|eswatini|
swaziland|ethiopia|fiji|finland|france|gabon|gambia|the gambia|germany|ghana|greece|grenada|
guatemala|guinea|guinea-bissau|guyana|haiti|honduras|hungary|iceland|india|indonesia|iran|iraq|
ireland|israel|italy|jamaica|japan|jordan|kazakhstan|kenya|kiribati|kosovo|kuwait|kyrgyzstan|
laos|latvia|lebanon|lesotho|liberia|libya|liechtenstein|lithuania|luxembourg|madagascar|malawi|
malaysia|maldives|mali|malta|marshall islands|mauritania|mauritius|mexico|micronesia|moldova|
monaco|mongolia|montenegro|morocco|mozambique|myanmar|burma|namibia|nauru|nepal|netherlands|
the netherlands|holland|new zealand|nicaragua|niger|nigeria|north korea|north macedonia|
macedonia|norway|oman|pakistan|palau|palestine|panama|papua new guinea|paraguay|peru|
philippines|poland|portugal|qatar|romania|russia|russian federation|rwanda|
saint kitts and nevis|saint lucia|saint vincent and the grenadines|samoa|san marino|
sao tome and principe|são tomé and príncipe|saudi arabia|senegal|serbia|seychelles|sierra leone|
singapore|slovakia|slovenia|solomon islands|somalia|south africa|south korea|korea|
republic of korea|south sudan|spain|sri lanka|sudan|suriname|sweden|switzerland|syria|taiwan|
tajikistan|tanzania|thailand|timor-leste|east timor|togo|tonga|trinidad and tobago|tunisia|
turkey|türkiye|turkiye|turkmenistan|tuvalu|uganda|ukraine|united arab emirates|uae|
united kingdom|uk|great britain|britain|england|scotland|wales|northern ireland|united states|
united states of america|usa|u.s.|u.s.a.|america|uruguay|uzbekistan|vanuatu|vatican city|
holy see|venezuela|vietnam|viet nam|yemen|zambia|zimbabwe|hong kong|macau|macao|greenland|
bermuda|british virgin islands|cayman islands|aruba|curacao|curaçao|gibraltar|faroe islands|
french polynesia|new caledonia|reunion|réunion|martinique|guadeloupe|french guiana|
western sahara|palestinian territories|other|other country|foreign|abroad|outside the us|
ab|bc|mb|nb|nl|ns|nt|nu|on|pe|qc|sk|yt|nsw|vic|qld|sa|wa|tas|act|gu|vi|as|mp|dc|xk|xkx|
ad|ae|af|ag|ai|al|am|ao|aq|ar|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bl|bm|bn|bo|bq|br|bs|bt|
bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|
eh|er|es|et|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gw|gy|hk|hm|hn|hr|
ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|
lr|ls|lt|lu|lv|ly|ma|mc|md|me|mf|mg|mh|mk|ml|mm|mn|mo|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|
ng|ni|no|np|nr|nz|om|pa|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sb|sc|sd|se|sg|sh|
si|sj|sl|sm|sn|so|sr|ss|st|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tr|tt|tv|tw|tz|ua|ug|um|
us|uy|uz|va|vc|ve|vg|vn|vu|wf|ws|ye|yt|za|zm|zw|
afg|alb|dza|and|ago|atg|arg|arm|aus|aut|aze|bhs|bhr|bgd|brb|blr|bel|blz|ben|btn|bol|bih|bwa|bra|
brn|bgr|bfa|bdi|cpv|khm|cmr|can|caf|tcd|chl|chn|col|com|cog|cod|cri|civ|hrv|cub|cyp|cze|dnk|dji|
dma|dom|ecu|egy|slv|gnq|eri|est|swz|eth|fji|fin|fra|gab|gmb|geo|deu|gha|grc|grd|gtm|gin|gnb|guy|
hti|hnd|hun|isl|ind|idn|irn|irq|irl|isr|ita|jam|jpn|jor|kaz|ken|kir|prk|kor|kwt|kgz|lao|lva|lbn|
lso|lbr|lby|lie|ltu|lux|mdg|mwi|mys|mdv|mli|mlt|mhl|mrt|mus|mex|fsm|mda|mco|mng|mne|mar|moz|mmr|
nam|nru|npl|nld|nzl|nic|ner|nga|mkd|nor|omn|pak|plw|pse|pan|png|pry|per|phl|pol|prt|qat|rou|rus|
rwa|kna|lca|vct|wsm|smr|stp|sau|sen|srb|syc|sle|sgp|svk|svn|slb|som|zaf|ssd|esp|lka|sdn|sur|swe|
che|syr|twn|tjk|tza|tha|tls|tgo|ton|tto|tun|tur|tkm|tuv|uga|ukr|are|gbr|usa|ury|uzb|vut|vat|ven|
vnm|yem|zmb|zwe|hkg|mac|pri|grl|bmu|gum|asm|vir|vgb|cym|abw|cuw|gib|fro|pyf|ncl|reu|mtq|glp|guf|
esh
""") | frozenset(s.lower() for s in US_STATES.strip("(?:)").split("|"))

# Words of a column name that make it name a person, a relative or a contact wherever they
# stand (person_role_words and place_words find the rest).
PERSON_ANYWHERE_WORDS = (frozenset(RELATIVE_WORDS) - {"emergency"}) | frozenset(
    {"contacts", "kin", "relatives", "relation", "relationship", "family", "families", "familia",
     "famille", "familie", "households"})
# Column names that let a grammar accept a short form it would not accept under any name.
ICD_HEADER_WORDS = frozenset("""icd dx diag diagnosis diagnoses diagnostic comorbidity comorbidities
condition conditions problem problems cause""".split())
ATC_HEADER_WORDS = frozenset("atc drug drugs medication medications med meds medicine medicines rx".split())
STAGE_HEADER_WORDS = frozenset("""stage stages staging stg figo ajcc uicc nyha rai binet iss riss dukes
bclc class grade grading phase tier tnm""".split())
TNM_HEADER_WORDS = STAGE_HEADER_WORDS | frozenset("t n m ct cn cm pt pn pm yp ypt ypn".split())
BLOOD_HEADER_WORDS = frozenset("blood abo bloodtype bloodgroup rh rhesus".split())
VARIANT_HEADER_WORDS = frozenset("""variant variants mutation mutations mut alteration alterations
change changes hgvs hgvsp hgvsc protein aa amino substitution substitutions codon snv""".split())
# Race and ethnicity words (White, Black, Mixed, Chinese, Cuban, ...) are also surnames and
# nationalities, so they count only under a column name for race or ethnicity; bare units (Ng,
# Ma, Mo, Min) are also surnames, so they count only under a column name for units.
RACE_HEADER_WORDS = frozenset("""race races racial ethnicity ethnicities ethnic ethnical ancestry
ancestries heritage hispanic latino latinx raza etnia etnicidad ethnie rasse ethnizitat razza raca
etniciteit omb""".split())
RACE_HEADER_SCRIPTS = ("人种", "人種", "种族", "種族", "民族", "인종", "민족", "раса", "этнич", "عرق", "גזע")
UNIT_HEADER_WORDS = frozenset("""unit units uom uoms unidad unidades einheit einheiten unite unites unita
eenheid eenheden""".split())


class ColumnContext:
    """What a column name says about the values the vocabulary and the grammars accept."""

    def __init__(self, header: str):
        t = column_tokens(header)
        ts = set(t)
        self.person_or_place = bool(person_role_words(t, NAME_TRAILING) or place_words(t)
                                    or ts & PERSON_ANYWHERE_WORDS)
        self.geography = is_allowed_geography(header)
        self.icd = bool(ts & ICD_HEADER_WORDS)
        self.atc = bool(ts & ATC_HEADER_WORDS)
        self.stage = bool(ts & STAGE_HEADER_WORDS)
        self.tnm = bool(ts & TNM_HEADER_WORDS)
        self.blood = bool(ts & BLOOD_HEADER_WORDS)
        self.variant = bool(ts & VARIANT_HEADER_WORDS)
        self.loinc = bool(ts & LOINC_HEADER_WORDS)
        self.loinc_name = "loinc" in ts
        raw = unicodedata.normalize("NFKC", str(header)).casefold()
        self.race = bool(ts & RACE_HEADER_WORDS) or any(w in raw for w in RACE_HEADER_SCRIPTS)
        self.unit = bool(ts & UNIT_HEADER_WORDS) or _has(t, "unit of measure", "units of measure")


# (a) Numbers, with an optional comparator and a unit of UNITS ("<0.5", "5.2 mg/dL", "12%",
# "1,250"), and a blood pressure ("120/80": the first number larger, both in their range, so a
# day and a month never pass).
_NUM = r"[+-]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
NUMBER_WITH_UNIT = re.compile(r"(?:<=|>=|=<|=>|<|>|≤|≥|=|~|≈)?\s*(?P<n>" + _NUM
                              + r")\s*(?P<u>[^\d\s].*)?")
BLOOD_PRESSURE = re.compile(r"(\d{2,3})\s*/\s*(\d{2,3})(?:\s*mm\s*hg)?", re.I)


def _plain(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split())


def number_like(value: str) -> str | None:
    """The number in a value that is a number, with an optional comparator and unit, or a
    blood pressure; None for anything else."""
    s = _plain(value)
    if len(s) > 60:
        return None  # round 6: a run of thousands of digits is not a measurement, and int() refuses it
    m = NUMBER_WITH_UNIT.fullmatch(s)
    if m and (not m.group("u") or fold(m.group("u")) in UNITS):
        return m.group("n").replace(",", "")
    m = BLOOD_PRESSURE.fullmatch(s)
    if m and 50 <= int(m.group(1)) <= 300 and 20 <= int(m.group(2)) <= 200 \
            and int(m.group(1)) > int(m.group(2)):
        return m.group(1)
    return None


# (b) Closed code grammars. Each needs a digit, a sign or a fixed prefix word, so no bare
# alphabetic word passes; the short forms that are letters only ("IIIA", "Tis", "AB") pass
# only under a column name that says what they are (stage, TNM, blood group).
#
# Round 5: a grammar with an open part ("rs" in any case and any number of digits, RefSeq with
# seven digits, ICD-10 with a letter in the third place, any E code) let a record number with such
# a prefix pass as a whole value under any column name ("RS1234567", "NM_1234567", "H8Q.600",
# "E456.8"). The grammars now take the exact published shapes and nothing else: Ensembl ENSG,
# ENST, ENSP and the like with exactly eleven digits; RefSeq NM_, NR_, XM_, XR_, NP_ and XP_ (and
# the genomic NC_ and NG_ an HGVS name starts with) with six or nine digits; an rsID written in
# lower case, as dbSNP and every variant caller write it, with no leading zero and at most ten
# digits; ICD-10-CM with a letter, two digits (or one of the categories with a letter third, C4A, C7A,
# C7B, D3A, M1A, O9A, Z3A) up to the last category of its chapter letter (E89, H95, T88) and up to four
# more after the dot, in capitals; ICD-9 V codes from V01 to V91
# and E codes from E000 to E030 and E800 to E999; an HGVS substitution of one base by another.
# A LOINC code (digits, a hyphen and its mod 10 check digit) is a code only under a column name
# that names a LOINC code, a lab, a test or an observation, because many record numbers carry the
# same mod 10 check digit ("452783-6").
_AA1 = "[ACDEFGHIKLMNPQRSTVWY]"
_AA3 = "(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter|Sec|Pyl|Xaa)"
_AA = f"(?:{_AA3}|{_AA1})"
_REFSEQ = r"(?:NM|NR|XM|XR|NP|XP|NC|NG)_(?:\d{9}|\d{6})(?:\.\d{1,3})?"
_ENSEMBL = r"ENS(?:[A-Z]{3})?[EFGPRT]\d{11}(?:\.\d{1,3})?"
_RSID = r"rs[1-9]\d{0,9}"
_POS = r"[-*]?\d{1,9}(?:[+-]\d{1,6})?"
_NUC = "[ACGTUNacgtun]"
_HGVS_NUC = (rf"[cgmnor]\.{_POS}(?:_{_POS})?(?:{_NUC}>{_NUC}|(?:del|dup|inv)(?:{_NUC}+|\d+)?"
             rf"|(?:ins|delins){_NUC}+|=|{_NUC}*\[\d+\])")
_P_CHANGE = (rf"{_AA}\d+(?:_{_AA}\d+)?(?:{_AA}|\*|=|\?|fs(?:\*|Ter|X)?\d*|del|dup|(?:ins|delins){_AA}+"
             rf"|ext(?:\*|Ter)?-?\d*)")
_HGVS_PROT = rf"p\.(?:\({_P_CHANGE}\)|{_P_CHANGE}|=|\?|0\??|\(=\))"
_HGVS_REF = (rf"(?:(?:{_REFSEQ}|{_ENSEMBL}|LRG_\d+(?:t\d+|p\d+)?|chr(?:[1-9]|1\d|2[0-2]|X|Y|MT?))"
             r"(?:\([A-Z0-9-]{1,15}\))?:)?")
_ICD10_CATEGORY = r"(?:[A-Z]\d{2}|C4A|C7A|C7B|D3A|M1A|O9A|Z3A)"
# The last category of each ICD-10-CM chapter letter: "D95.1" or "H99.2" has the shape and is no code.
ICD10_LAST_CATEGORY = {"A": 99, "B": 99, "C": 96, "D": 89, "E": 89, "F": 99, "G": 99, "H": 95, "I": 99, "J": 99,
                       "K": 95, "L": 99, "M": 99, "N": 99, "O": 99, "P": 96, "Q": 99, "R": 99, "S": 99, "T": 88,
                       "U": 85, "V": 99, "W": 99, "X": 99, "Y": 99, "Z": 99}
ICD10_DOTTED = re.compile(_ICD10_CATEGORY + r"\.(?=[0-9A-Z]{0,3}\d)[0-9A-Z]{1,4}")
_ICD9_V = r"V(?:0[1-9]|[1-8]\d|9[01])"
_ICD9_E = r"E(?:0[0-2]\d|030|[89]\d\d)"
ICD9_DOTTED = re.compile(rf"{_ICD9_V}\.\d{{1,2}}|{_ICD9_E}\.\d")
ICD_PLAIN = re.compile(_ICD10_CATEGORY + r"(?:(?=[0-9A-Z]{0,3}\d)[0-9A-Z]{1,4})?" + rf"|{_ICD9_V}\d{{0,2}}|{_ICD9_E}\d?")
ICD9_PLAIN = re.compile(rf"{_ICD9_V}\d{{0,2}}|{_ICD9_E}\d?")
LOINC = re.compile(r"(\d{1,6})-(\d)")
ATC = re.compile(r"[ABCDGHJLMNPRSV]\d{2}(?:[A-Z](?:[A-Z](?:\d{2})?)?)?")
RSID = re.compile(_RSID)
ENSEMBL = re.compile(_ENSEMBL)
REFSEQ = re.compile(_REFSEQ)
HGVS = re.compile(_HGVS_REF + rf"(?:{_HGVS_NUC}|{_HGVS_PROT})")
# Column names under which a LOINC code is a code (see above).
LOINC_HEADER_WORDS = frozenset("""
loinc lab labs laboratory test tests observation observations obs component components analyte analytes
assay assays panel panels measurement measurements
""".split())


def _icd10_in_range(value: str) -> bool:
    """An ICD-10-CM code whose category is within its chapter letter's range ("E11.9", not "E95.1")."""
    head = value[:3]
    return not head[1:].isdigit() or int(head[1:]) <= ICD10_LAST_CATEGORY.get(head[0], -1)


def _hgvs(value: str) -> bool:
    """An HGVS name, with a substitution of one base by another ("c.35G>A", not "c.35G>G")."""
    if not HGVS.fullmatch(value):
        return False
    sub = re.search(r"([ACGTUNacgtun])>([ACGTUNacgtun])$", value)
    return not sub or sub.group(1).upper() != sub.group(2).upper()


SHORT_PROTEIN = re.compile(rf"{_AA1}\d{{1,4}}(?:{_AA1}|\*|X|fs\*?\d*|del|dup)")
_TNM_PREFIX = r"(?:[cpyrau]{1,3})?"
TNM_FULL = re.compile(rf"{_TNM_PREFIX}T(?:[0-4][a-d]?[1-3]?|is|x)(?:\((?:m|\d+)\))?\s*{_TNM_PREFIX}"
                      rf"N(?:[0-3][a-c]?|x)(?:\((?:sn|f|i[+-]|mol[+-])\))?\s*{_TNM_PREFIX}M(?:[01][a-d]?|x)",
                      re.I)
TNM_PART = re.compile(rf"{_TNM_PREFIX}(?:T(?:[0-4][a-d]?[1-3]?|is|x)|N(?:[0-3][a-c]?|x)|M(?:[01][a-d]?|x))",
                      re.I)
_STAGE_VALUE = r"(?:(?:0|i{1,3}|iv|v)(?:[a-d][1-3]?)?|[0-5](?:[a-d][1-3]?)?)"
STAGE_PREFIXED = re.compile(
    r"(?:(?:clinical|pathologic(?:al)?|c|p|y|yp)\s+)?(?:stage|stg\.?|class|phase|figo|nyha|ajcc|uicc"
    r"|ann\s+arbor|rai|binet|r-?iss|iss|dukes|ckd|gold|bclc|grade)(?:\s+(?:stage|class|grade|group))?"
    r"\s*:?\s*" + _STAGE_VALUE, re.I)
STAGE_BARE = re.compile(_STAGE_VALUE + r"|gx", re.I)
GRADE = re.compile(
    r"g[1-4]|(?:(?:who|nottingham|isup|fnclcc|histologic(?:al)?|tumou?r|nuclear|fuhrman)\s+)?"
    r"(?:grade|gr\.?)(?:\s+group)?\s*:?\s*(?:[1-5]|i{1,3}|iv|x)|(?:low|high|intermediate)[- ]grade"
    r"|(?:well|moderately|poorly)[- ]differentiated"
    r"|(?:gleason(?:\s+score)?\s*:?\s*)?[1-5]\s*\+\s*[1-5](?:\s*=\s*(?:[2-9]|10))?"
    r"|gleason(?:\s+score)?\s*:?\s*(?:[2-9]|10)|isup\s*[1-5]", re.I)
PERFORMANCE = re.compile(
    r"(?:ecog|who|zubrod)(?:\s*(?:ps|performance\s+status))?\s*[:=]?\s*[0-5]|ps\s*[:=]?\s*[0-5]"
    r"|(?:kps|karnofsky)(?:\s*(?:score|ps))?\s*[:=]?\s*(?:100|[1-9]0|0)\s*%?", re.I)
BLOOD_GROUP = re.compile(
    r"(?:a|b|ab|o)\s*(?:rh\s*(?:\(d\)\s*)?)?(?:[+-]|pos(?:itive)?|neg(?:ative)?)"
    r"|rh\s*(?:\(d\)\s*)?(?:[+-]|pos(?:itive)?|neg(?:ative)?)|(?:a|b|ab|o)\s*[型형](?:\s*rh\s*[+-])?",
    re.I)
BLOOD_BARE = re.compile(r"a[12]?|b|a[12]?b|o", re.I)
ANYWHERE_CODES = (ICD10_DOTTED, ICD9_DOTTED, RSID, ENSEMBL, REFSEQ, STAGE_PREFIXED, GRADE,
                  PERFORMANCE, BLOOD_GROUP)


def _luhn_check_digit(payload: str) -> int:
    """The check digit LOINC appends (the mod 10 algorithm of the LOINC users' guide)."""
    total = 0
    for i, c in enumerate(reversed(payload)):
        d = int(c) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10


def loinc_code(value: str) -> bool:
    m = LOINC.fullmatch(_plain(value))
    return bool(m) and _luhn_check_digit(m.group(1)) == int(m.group(2))


def _hemisphere_shaped(s: str) -> bool:
    """A dotted ICD-10 shape that is also a coordinate written after its hemisphere letter ("N37.7749",
    "S33.869", "W122.419" is not ICD at all): N, S, E or W, two digits, a dot and three or four digits
    (round 7). ICD-10-CM has no N, S or W code whose last four characters are all digits (the seventh
    character of an injury code is a letter), and an E code with them is a diabetes code (E08 to E13)."""
    m = re.fullmatch(r"([NSEW])(\d{2})\.(\d{3,4})", s)
    if not m:
        return False
    return not (m.group(1) == "E" and 8 <= int(m.group(2)) <= 13 and len(m.group(3)) == 4)


def code_grammar(value: str, ctx: ColumnContext) -> bool:
    """True when the whole value is a code of a closed grammar (see the section comment)."""
    s = _plain(value)
    if ICD10_DOTTED.fullmatch(s):
        # Round 7: four digits after the dot of an N, S or W code are no published code, and three or
        # four count only under a column name that names a diagnosis, since a coordinate can be written so.
        tail = s.partition(".")[2]
        if len(tail) == 4 and tail.isdigit() and s[0] in "NSTW":
            return False
        if _hemisphere_shaped(s) and not ctx.icd:
            return False
        return _icd10_in_range(s)
    if ctx.icd and ICD_PLAIN.fullmatch(s):
        return bool(ICD9_PLAIN.fullmatch(s)) or _icd10_in_range(s)
    if not s or any(rx.fullmatch(s) for rx in ANYWHERE_CODES) or _hgvs(s) or (ctx.loinc and loinc_code(s)):
        return bool(s)
    if TNM_FULL.fullmatch(s) or TNM_PART.fullmatch(s):
        return bool(re.search(r"\d", s)) or ctx.tnm
    return bool((ctx.icd and ICD_PLAIN.fullmatch(s)) or (ctx.atc and ATC.fullmatch(s))
                or (ctx.stage and STAGE_BARE.fullmatch(s)) or (ctx.blood and BLOOD_BARE.fullmatch(s))
                or (ctx.variant and SHORT_PROTEIN.fullmatch(s)))


def vocabulary_value(value: str, ctx: ColumnContext) -> bool:
    """(c) and (d): a whole value of the vocabulary (only its missing-value words under a column
    name that names a person, a role, a relative, a contact or a place), or a state or country
    under a state or country column."""
    s = value.strip()
    key = fold(s)
    if key in MISSING_PHRASES or s in CASELESS_MISSING:
        return True
    if ctx.geography and key in GEOGRAPHY_NAMES:
        return True
    if ctx.person_or_place:
        return False
    return (key in VOCABULARY or s in CASELESS_CATEGORY_VALUES or (ctx.race and key in RACE_ETHNICITY)
            or (ctx.unit and key in UNITS))


# Groups of single letters with one meaning each; a column of single letters from more than
# one group may be initials.
SINGLE_LETTER_GROUPS = (frozenset("mfx"), frozenset("yntf"), frozenset("lrb"), frozenset("hlnac"),
                        frozenset("sir"))
# What this tool writes, which a check of its own output reads as verified. Only these
# placeholders count: a cell that is some other word in brackets ("[OKAFOR]") is text.
TOOL_OUTPUT = re.compile(r"90\+(?: years)?")
TOOL_PLACEHOLDERS = frozenset("""
[REDACTED] [PHONE] [URL] [EMAIL] [HANDLE] [DEVICE_ID] [IP] [GEO] [ID] [SSN] [HEALTH_PLAN_ID]
[ACCOUNT] [VEHICLE_ID] [DATE] [ZIP] [ADDRESS] [CITY] [NAME] [90_OR_OLDER] [PHOTO] [IMAGE_FILE]
[BIOMETRIC_OR_CODE]
""".split())


def value_verified(value: str, ctx: ColumnContext, own_output: bool = False) -> bool:
    """True when the value is a number, a code, a vocabulary word, an allowed place or blank."""
    s = value.strip()
    if not s or s in TOOL_PLACEHOLDERS or TOOL_OUTPUT.fullmatch(s):
        return True
    if own_output and PSEUDONYM.fullmatch(s):
        return True
    return number_like(s) is not None or code_grammar(s, ctx) or vocabulary_value(s, ctx)


def scrub_cell(scrubber: "Scrubber", value: str, ctx: ColumnContext) -> tuple[str, list[str]]:
    """Scrubber.scrub, except that a whole value of a code grammar keeps the codes the generic
    code rule would replace ("S72001A" under a diagnosis column, "C10AA05" under a drug column,
    "NM_001126112.3"), and a LOINC code under a LOINC column keeps its "2093-3" shape. Every
    other pattern (a phone, an email, a date, ...) is still replaced."""
    out, found = scrubber.scrub(value)
    if found and code_grammar(value, ctx):
        allowed = {"code"} | ({"date"} if ctx.loinc_name and loinc_code(value) else set())
        if set(found) <= allowed:
            return value, []
    return out, found


def verify_column(header: str, values: list[str], reference_year: int,
                  ctx: ColumnContext | None = None, own_output: bool = False) -> dict:
    """Which values of a column the script can vouch for. Returns the distinct values it cannot
    verify (`unverified`), how many of them have the shape of a name or a place, and for a
    column that mixes numbers with other verified values, a numeric identifier finding."""
    ctx = ctx or ColumnContext(header)
    distinct = {v.strip() for v in values if v.strip()}
    bad = {v for v in distinct if not value_verified(v, ctx, own_output)}
    names = sum(1 for v in bad if not has_caseless_text(v) and (name_shaped(v) or name_or_place_like(v)))
    caseless = sum(1 for v in bad if has_caseless_text(v))
    # Single letters are kept only when they all belong to one group (M and F, Y and N, L and
    # R, H, L and N, ...): a handful of first initials spans several groups.
    singles = {fold(v) for v in distinct - bad if len(fold(v)) == 1 and fold(v).isascii()
               and fold(v).isalpha() and fold(v) not in MISSING_PHRASES}
    groups = SINGLE_LETTER_GROUPS + ((frozenset("abo"),) if ctx.blood else ()) \
        + ((frozenset("iv"),) if ctx.stage else ())
    if singles and not any(singles <= g for g in groups):
        bad |= {v for v in distinct if fold(v) in singles}
    # Round 7: two capital letters verified only as a vocabulary word (NA, SD, PR, CR, LT, HH) are a person's
    # initials as often, so a column of them must take them all from one list (response, result flags,
    # laterality, yes and no, sex, smoking, or a state under a state column), as single letters must.
    doubles = {fold(v) for v in distinct - bad if re.fullmatch(r"[A-Z]{2}", v.strip())
               and not code_grammar(v, ctx) and fold(v) not in MISSING_PHRASES}
    lists = (RESPONSE, RESULT_FLAGS, LATERALITY, YES_NO, SEX_GENDER, SMOKING) \
        + ((GEOGRAPHY_NAMES,) if ctx.geography else ()) + ((RACE_ETHNICITY,) if ctx.race else ()) \
        + ((UNITS,) if ctx.unit else ())
    if len(doubles) > 1 and not any(doubles <= g for g in lists):
        bad |= {v for v in distinct if fold(v) in doubles}
    numeric = None
    cells = [v.strip() for v in values if v.strip() and v.strip() not in TOOL_PLACEHOLDERS]
    nums = [n for n in (number_like(v) for v in cells) if n is not None]
    if not bad and nums and not all(is_number(v) for v in cells):
        shape = value_shape_rule(header, nums, reference_year)
        rule = None if shape else number_rule(header, cells, reference_year)
        if shape:
            numeric = (shape[0], "redact", shape[2])
        elif upstream.is_high_cardinality_numeric(nums) and not measurement_header(header):
            numeric = ("unique numbers (possible record or account number)", "redact", "id")
        elif rule:
            numeric = (rule[0], rule[1], rule[2])
    return {"distinct": len(distinct), "unverified": bad, "names": names, "caseless": caseless,
            "numeric": numeric, "cells": sum(1 for v in values if v.strip() in bad),
            "verified": not bad and numeric is None}


def unverified_finding(check: dict, ctx: ColumnContext) -> str:
    """The plan's reason for redacting a column of text the script cannot verify. It names
    counts only, never a value."""
    n, total = len(check["unverified"]), check["distinct"]
    kinds = ("state or country names, numbers or missing-value words" if ctx.geography
             else "numbers, codes, dates or common category words")
    parts = [f"{n} of {total} distinct values are not {kinds}"]
    if ctx.person_or_place:
        parts.append("the column name names a person, a role, a relative, a contact or a place, "
                     "so only missing-value words count as category words")
    if check["names"] and check["names"] == n and n >= 2:
        # Round 6: a column every unverified value of which is shaped like a name or a place is said to be one.
        parts.append(f"all {n} of them are shaped like names of people or places, so the column probably holds "
                     "names or places; keep it only if the person is sure it does not")
    elif check["names"]:
        parts.append(f"{check['names']} of them {'is' if check['names'] == 1 else 'are'} shaped like "
                     "names or places")
    if check["caseless"]:
        parts.append(f"{check['caseless']} of them {'is' if check['caseless'] == 1 else 'are'} in a "
                     "script without capital letters, where names cannot be told from other words")
    return ("text the script cannot verify is free of identifiers (" + "; ".join(parts)
            + "); keep with --keep COLUMN once the person confirms it")


def residual_text_finding(check: dict) -> str:
    """The residual check's problem for kept text it cannot verify. Counts only."""
    n = len(check["unverified"])
    if check["names"]:
        return f"text values shaped like names or places ({check['names']} of {n} distinct values it cannot verify)"
    if check["caseless"]:
        return f"text in a script without capital letters that it cannot verify ({n} distinct values)"
    return f"text the script cannot verify is free of identifiers ({n} distinct values)"


# 202103 and 2021.03; 2021.1 is October written as a number that lost its last zero.
YEAR_MONTH_NUMBER = re.compile(r"(1[89]\d{2}|20\d{2})(?:0[1-9]|1[0-2]|\.(?:0[1-9]|1[0-2]|1))")


def _year_month_number(v: str, reference_year: int) -> bool:
    m = YEAR_MONTH_NUMBER.fullmatch(v)
    return bool(m) and 1880 <= int(m.group(1)) <= reference_year + 10


def _compact_date(v: str, reference_year: int) -> bool:
    """MMDD or DDMM, MMDDYY or DDMMYY, MMDDYYYY or DDMMYYYY, all of one length."""
    if not re.fullmatch(r"\d{4}|\d{6}|\d{8}", v):
        return False
    a, b = int(v[:2]), int(v[2:4])

    def month_day(m: int, d: int) -> bool:
        return 1 <= m <= 12 and 1 <= d <= 31
    if len(v) == 8 and not 1880 <= int(v[4:]) <= reference_year + 10:
        return False
    return month_day(a, b) or month_day(b, a)


# Words for a day of the month, a month or a weekday, singular (the plurals "days" and "months" are
# durations). A whole number from 1 to 31 under one of these is a date element other than the
# year, which Safe Harbor removes: with the year beside it, it rebuilds the date.
DAY_PART_WORDS = frozenset("""
day dayofmonth dia tag jour giorno dag dzien hari ngay paiva
""".split())
MONTH_PART_WORDS = frozenset("""
month mon mth mes mois monat mese maand manad miesiac bulan thang kuukausi honap mesic
""".split())
WEEKDAY_WORDS = frozenset("weekday dow wochentag weekdag veckodag ukedag".split())
# Words for a week (round 5), singular: with a year beside it, a week of the year fixes a date to seven
# days, a date element finer than the year. The plurals ("Weeks", "Wochen") are durations, as "Days" is.
WEEK_PART_WORDS = frozenset("""
week wk woche semana semaine settimana hafta tydzien minggu tuan viikko vecka uge uke tyden saptamana
kw cw woy mmwr epiweek epiwk isoweek isowk weeknum weekno weeknr wkno wknum wknr calweek
""".split())
WEEK_PART_SCRIPTS = ("周", "週", "주차", "неделя", "недели", "неделю", "нед", "أسبوع", "الأسبوع", "שבוע", "सप्ताह",
                     "हफ्ता", "สัปดาห์", "εβδομάδα")
# Phrases in which these script words mean something else: a cycle, a period, an anniversary, an age.
WEEK_PART_SCRIPTS_NOT = ("周期", "週期", "周年", "週年", "周岁", "週歲", "周歲", "周围", "週圍", "周边")
DAY_OF_YEAR_PHRASES = ("day of year", "day of the year", "dayofyear", "ordinal day", "dia del ano", "dia do ano",
                       "jour de l annee", "jour de lannee", "tag des jahres", "giorno dell anno", "dag van het jaar")
DAY_PART_SCRIPTS = ("日", "일", "день", "يوم", "اليوم", "יום", "दिन", "วัน", "ημέρα")
MONTH_PART_SCRIPTS = ("月", "월", "месяц", "شهر", "الشهر", "חודש", "महीना", "เดือน", "μήνας")
# Beside these, "dd" and "mm" are a day and a month rather than a code or millimetres.
DATE_PART_CONTEXT = DATE_TIME_CONTEXT | frozenset("""
date dt yyyy yy birth dob onset event admit adm dx surgery visit death discharge
""".split())
# The last word of a column of a date written in three columns beside its year ("Admit M").
SHORT_DATE_PARTS = {"m": "month", "mo": "month", "mm": "month", "mon": "month", "mth": "month",
                    "mn": "month", "month": "month", "d": "day", "dy": "day", "dd": "day", "day": "day"}
YEAR_PART_WORDS = YEAR_TOKENS | {"yy", "jahr", "ano", "annee", "anno", "aar", "ar", "year"}


def _whole_numbers(values: list[str]) -> list[int] | None:
    vals = [v for v in _shape_values(values) if fold(v) not in MISSING_PHRASES]
    out = []
    for v in vals:
        n = number_like(v)
        d = _integer_digits(n) if n is not None and n == _plain(v) else None
        if d is None:
            return None
        out.append(int(d))
    return out or None


def date_part_rule(header: str, values: list[str]) -> tuple[str, str, str, int] | None:
    """(finding, action, phi type, cells) for whole numbers that are a day of the month (1 to 31),
    a month (1 to 12) or a weekday (0 to 7) under a column name that says so, in any language and
    with any qualifier ("Admit Day", "Discharge Month", "Day of Month", "MM", "Mois", "Tag",
    "入院月", "Weekday"). A column name that also names a measurement ("Month 6 Pain Score") or a
    duration in the plural ("Days", "Months") is left to the number rules."""
    nums = _whole_numbers(values)
    if not nums:
        return None
    t = column_tokens(header)
    ts = set(t)
    raw = unicodedata.normalize("NFKC", str(header)).casefold()
    if (ts & MEASUREMENT_WORDS) - TIME_WORDS - DAY_PART_WORDS - MONTH_PART_WORDS - {"mm"} \
            or "%" in raw or _has(t, "number of", "no of", "count of", "n of"):
        return None
    context = len(t) == 1 or bool(ts & DATE_PART_CONTEXT)
    week = bool(ts & WEEKDAY_WORDS) or _has(t, "day of week", "day of the week", "dayofweek")
    year_day = bool(ts & {"doy", "yday", "jday", "julian"}) or _has(t, *DAY_OF_YEAR_PHRASES)
    # A week (round 5), under any word for one in any language and with any qualifier ("Week", "Wk", "Epi Wk",
    # "Admit Week", "MMWR Week", "Semana", "Woche", "周"); not "Day of Week", which is a weekday.
    script_week = raw
    for w in WEEK_PART_SCRIPTS_NOT:
        script_week = script_week.replace(w, " ")
    year_week = (bool(ts & WEEK_PART_WORDS) or _has(t, "week of year", "week of the year", "weekofyear", "iso week",
                                                     "epi week", "calendar week", "week number")
                 or any(w in script_week for w in WEEK_PART_SCRIPTS)
                 or "주" in re.split(r"[\s_\-/,;:()\[\].]+", raw))
    if year_day and all(1 <= n <= 366 for n in nums):
        return ("whole numbers under a column name that names a day of the year (1 to 366): a date element other "
                "than the year", "redact", "date", len(nums))
    if year_week and not week and all(0 <= n <= 53 for n in nums):
        return ("whole numbers under a column name that names a week (0 to 53): with a year, a week of the year "
                "fixes a date to seven days, a date element other than the year", "redact", "date", len(nums))
    day = bool(ts & DAY_PART_WORDS) or ("dd" in ts and context) or any(w in raw for w in DAY_PART_SCRIPTS)
    month = bool(ts & MONTH_PART_WORDS) or ("mm" in ts and context) or any(w in raw for w in MONTH_PART_SCRIPTS)
    if week and all(0 <= n <= 7 for n in nums):
        what = "a weekday (0 to 7)"
    elif day and not week and all(1 <= n <= 31 for n in nums):
        what = "a day of the month (1 to 31)"
    elif month and not week and all(1 <= n <= 12 for n in nums):
        what = "a month (1 to 12)"
    else:
        return None
    return (f"whole numbers under a column name that names {what}: a date element other than the year",
            "redact", "date", len(nums))


def date_sibling_positions(columns: list[tuple[int, str, list[str]]], reference_year: int) -> dict[int, str]:
    """Positions of columns that hold a month (1 to 12) or a day (1 to 31) of a date written in three
    columns beside its year, named by a short word and sharing the year's name ("Admit Year", "Admit
    M", "Admit D"; "Y", "M", "D"; "yyyy", "mm", "dd"; "Dx Yr", "Dx Mo", "Dx Dy")."""
    toks = {i: column_tokens(h) for i, h, _ in columns}
    vals = {i: v for i, _, v in columns}

    def year_column(i: int) -> bool:
        nums = _whole_numbers(vals[i])
        return bool(nums) and all(1880 <= n <= reference_year + 10 for n in nums)
    years = [i for i, _, _ in columns if year_column(i) and set(toks[i]) & YEAR_PART_WORDS]
    found: dict[int, str] = {}
    for y in years:
        for i in (y - 2, y - 1, y + 1, y + 2):
            if i not in toks or i in years:
                continue
            shared = set(toks[i]) & set(toks[y])
            rest = [t for t in toks[i] if t not in shared]
            year_rest = [t for t in toks[y] if t not in shared]
            if len(rest) != 1 or rest[0] not in SHORT_DATE_PARTS or not set(year_rest) <= YEAR_PART_WORDS:
                continue
            nums = _whole_numbers(vals[i])
            limit = 12 if SHORT_DATE_PARTS[rest[0]] == "month" else 31
            if nums and all(1 <= n <= limit for n in nums):
                found[i] = SHORT_DATE_PARTS[rest[0]]
    return found


# Split dates (round 4). A date written in three columns (a year, a month and a day) rebuilds the whole
# date, and the words a month or a day is called by never close (Mnth, DoM, Mo of Dx, Tg, dxmo, SM, SD,
# Ay, Gün, Nap, Zi, Dan, Päev, Mjesec, Kuu, Luna). So the column name no longer decides: a column of
# whole numbers from 1 to 12 that covers most months, or from 1 to 31 that covers most days, is a
# possible month or day under any name but one that names a measurement; and in a file with a column of
# years, so is any column of whole numbers from 1 to 31 that is not only 1 and 2 (a code such as a sex).
YEAR_NAME_WORDS = frozenset("""
year yr yyyy yy jahr ano anno annee aar ar yil ev anul aasta rok godina vuosi tahun nam jaar evi
""".split())
# Measurement words that a date part is also called by: under these alone a column is not a measurement.
DATE_PART_MEASURE_WORDS = frozenset("""
day month mo mon mth week wk time hour hr minute min second sec date tg mm interval period
""".split())


def year_columns(columns: list[tuple[int, str, list[str]]], reference_year: int) -> set[int]:
    """Positions of columns of years: whole numbers of four digits from 1880 to ten years after the
    reference year under any column name that does not name a measurement or an age, or whole numbers up
    to 99 under a column name with a word for year ("Dx Yr", "YY", "Jahr")."""
    found = set()
    for i, header, values in columns:
        nums = _whole_numbers(values)
        if not nums:
            continue
        t = column_tokens(header)
        rule = name_rule(header)
        if (rule and rule[2] == "age") or "pack" in t:
            continue
        named = any(x in YEAR_NAME_WORDS or (len(x) > 2 and x.endswith(("yr", "year"))) for x in t)
        digits = [_integer_digits(number_like(v) or "") for v in _shape_values(values)]
        four = all(d is not None and len(d) == 4 for d in digits) and all(1880 <= n <= reference_year + 10
                                                                          for n in nums)
        if (four and (named or not measurement_header(header))) or (named and all(0 <= n <= 99 for n in nums)):
            found.add(i)
    return found


def _date_part_exempt(header: str) -> bool:
    """A column name that names a measurement other than a part of a date or a time ("Pain Score", "Days",
    "LOS", "ECOG", "NYHA Class", "Dose (mg)", "Number of Visits")."""
    t = column_tokens(header)
    ts = set(t)
    raw = str(header)
    if "%" in raw or _unit_in_brackets(raw) or count_phrase(t) or ts & STAGE_HEADER_WORDS:
        return True
    # A measurement named by a compact word (SpO2, HbA1c) has no measurement token; one named only by
    # words for a part of a date or a time ("Week", "Day", "Time") is not a measurement here.
    words = ts & MEASUREMENT_WORDS
    return bool(measurement_header(header) and (not words or words - DATE_PART_MEASURE_WORDS))


# Codes a survey or an export writes for an unknown value (0, 99, -9, ...): a minority of them does not
# make a column of months or days something else.
MISSING_CODES = frozenset({0, 77, 88, 96, 97, 98, 99, 777, 888, 997, 998, 999, 9999, -1, -7, -8, -9, -99, -999})


def _int_values(values: list[str]) -> list[int] | None:
    out = []
    for v in _shape_values(values):
        if fold(v) in MISSING_PHRASES:
            continue
        m = re.fullmatch(r"([+-]?)(\d{1,4})(?:\.0+)?", _plain(v))
        if not m:
            return None
        out.append(int(m.group(2)) * (-1 if m.group(1) == "-" else 1))
    return out or None


# Round 5: a week of the year (1 to 53) or a day of the year (1 to 366) beside a year was kept under any
# name the week words did not know (W, Wk, Period, Sample Week, Semana, Col3), because only numbers from 1
# to 31 counted. In a file with a year (a column of years, or a date column the output reduces to its
# year), any column of whole numbers that fits the range of a date part (1 to 12, 1 to 31, 1 to 53, 1 to
# 366) is now a possible date element, whatever it is called; the smallest range it fits names it. A
# minority of missing-value codes other than 0 (99, 999, -9) does not hide it; a 0 makes it a count.
DATE_PART_RANGES = ((12, "a month (1 to 12)"), (31, "a day of the month (1 to 31)"),
                    (53, "a week of the year (1 to 53)"), (366, "a day of the year (1 to 366)"))


def _date_part_fit(ints: list[int]) -> tuple[str, set[int]] | None:
    """The smallest date part whose range holds every value but a minority of missing-value codes other
    than 0, and the distinct values in range; None when no range holds them."""
    for top, what in DATE_PART_RANGES:
        inside = [n for n in ints if 1 <= n <= top]
        outside = [n for n in ints if not 1 <= n <= top]
        if inside and (not outside or (all(n in MISSING_CODES and n != 0 for n in outside)
                                       and len(outside) <= 0.2 * len(ints))):
            return what, set(inside)
    return None


def date_part_columns(columns: list[tuple[int, str, list[str]]], years: set[int]) -> dict[int, str]:
    """Positions of whole-number columns that may be a month, a day, a week or a day of the year of a date
    written in its own column, with the plan's finding for each (see the section comments)."""
    found = {}
    for i, header, values in columns:
        if i in years:
            continue
        ints = _int_values(values)
        if not ints or _date_part_exempt(header):
            continue
        fit = _date_part_fit(ints)
        if years and fit and not fit[1] <= {1, 2}:
            found[i] = (f"whole numbers that fit the range of {fit[0]} in a file with a year (a column of years or a "
                        "date): possibly a date element other than the year, written in a column of its own")
            continue
        nums = [n for n in ints if 1 <= n <= 31]
        odd = [n for n in ints if not 1 <= n <= 31]
        coded = bool(odd) and all(n in MISSING_CODES for n in odd) and len(odd) <= 0.2 * len(ints)
        weeks = {n for n in ints if 1 <= n <= 53}
        if all(0 <= n <= 53 or (n in MISSING_CODES and n != 0) for n in ints) and len(weeks) >= 27 and max(weeks) >= 32:
            found[i] = (f"whole numbers from 0 to 53 covering {len(weeks)} of the 53 weeks: possibly a week of the "
                        "year, a date element other than the year")
            continue
        if fit and fit[0].startswith("a day of the year") and min(fit[1]) <= 31 and max(fit[1]) >= 300 \
                and len(fit[1]) >= 100:
            found[i] = (f"whole numbers from 1 to 366 covering {len(fit[1])} days of the year: possibly a day of the "
                        "year, a date element other than the year")
            continue
        if not nums or (odd and not coded):
            continue
        distinct = set(nums)
        if max(nums) <= 12 and len(distinct) >= 7:
            found[i] = (f"whole numbers from 1 to 12 covering {len(distinct)} of the 12 months: possibly a month of "
                        "a date, a date element other than the year")
        elif max(nums) >= 13 and len(distinct) >= 13:
            found[i] = (f"whole numbers from 1 to 31 covering {len(distinct)} of the 31 days: possibly a day of "
                        "the month, a date element other than the year")
    return found


def value_shape_rule(header: str, values: list[str], reference_year: int) -> tuple[str, str, str, int] | None:
    """(finding, action, phi type, cells) for an all-number column whose values have
    the shape of an identifier its name does not announce: years old enough to be the
    birth year of someone over 89, ages over 89 in a column named for years, or
    five-digit numbers that may be ZIP codes. Coordinates are found in pairs, by
    coordinate_pairs()."""
    vals = _shape_values(values)
    if not vals or not all(is_number(v) for v in vals):
        return None
    if all(re.fullmatch(r"\d{4}(?:\.0+)?", v) and 1880 <= int(float(v)) <= reference_year for v in vals):
        old = sum(1 for v in vals if reference_year - int(float(v)) >= 90)
        if old:
            return (f"four-digit years, {old} of {len(vals)} at least 90 years before {reference_year} "
                    "(as birth years they reveal an age over 89)", "birth_year", "date", old)
        return None
    # A year and a month written as a number (202103, 2021.03), whatever the column is
    # called: the month is a Safe Harbor date element, so only the year stays.
    if all(_year_month_number(v, reference_year) for v in vals):
        return (f"a year and a month written as a number in {len(vals)} cells (dates)", "year", "date",
                len(vals))
    # A month and a day written with no separator: 0314 or 1403, 031421, 03142021 or 14032021.
    # Four and six digits count only when one of them keeps a leading zero, as dates do and
    # counts do not.
    if all(_compact_date(v, reference_year) for v in vals) and (
            any(len(v) == 8 for v in vals) or any(v.startswith("0") for v in vals)):
        return (f"a month and a day written as a number with no separator in {len(vals)} cells "
                "(possible dates)", "redact", "date", len(vals))
    toks = set(column_tokens(header))
    if toks & ({"years", "yrs", "yr", "yo"} | YEAR_WORDS_OTHER_LANGUAGES):
        nums = [float(v) for v in vals]
        over = sum(1 for n in nums if n >= 90)
        if over and all(0 <= n <= 125 for n in nums):
            return (f"{over} values over 89 in a column named for years (possible ages)", "age", "age", over)
    # Mostly five digits: a lab count such as a white cell count mixes four and five, and a
    # column name that names a measurement ("WBC", "Steps", "Total Cost") says what they are.
    if all(re.fullmatch(r"\d{4,5}(?:\.0+)?", v) for v in vals) and not measurement_header(header):
        five = sum(1 for v in vals if len(v.split(".")[0]) == 5)
        if five >= 0.8 * len(vals):
            return (f"five-digit numbers in {five} of {len(vals)} cells (possible ZIP codes)",
                    "redact", "zip", five)
    return None


# ================================================================ numbers (fail closed)
# A column of numbers is a measurement only when it reads as one: decimals, whole numbers of
# three digits or fewer (an age column excepted), or whole numbers of any length under a column
# name that names a measurement (a lab, a vital sign, a count, a score, a dose, a unit, money, a
# duration). Record numbers that repeat across visits, ZIP codes that lost their leading zero,
# dates written as numbers and ages over 89 have no other shape, and a list of column names that
# hold them never closes (Chart, Hosp No, Patid, 病历号, Col6 ...), so number_rule judges the
# numbers and leaves the decision to the person. Since round 7 the name decides first: numbers are
# kept by default only under a column name that names a measurement (below), whatever their shape
# under any other name, because one-decimal coordinate pairs, decimal years and short record numbers
# have the shapes of measurements.
MEASUREMENT_WORDS = frozenset("""
count counts cnt total totals sum steps step freq frequency times episodes visits admissions
encounters events occurrences reads read depth coverage copies load score scores scale rating
level levels percentile pctl rank tpm fpkm rpkm cpm expression intensity signal auc cmax tmax
dose doses dosage mg mcg ug kg ml dl mmol umol nmol pmol iu units cells cell ul mm cm km
mmhg cmh2o bpm kcal calories kj percent percentage pct ratio fraction rate rates concentration conc
titer titre heart pulse hr bp sbp dbp systolic diastolic map temp temperature rr resp respiratory spo
sao sat sats saturation oxygen fio pao paco gcs pain weight wt height ht bmi bsa length circumference
waist hip size volume vol diameter width depth thickness distance grams kilograms
pounds lbs lb oz inches inch feet ft cost costs charge charges price amount payment paid income salary
dollars usd eur gbp spend spending duration days day weeks week wks months month hours hour hrs
minutes minute min mins seconds second sec secs los interval delay elapsed time latency lag 
hemoglobin haemoglobin hgb hb hematocrit hct platelet platelets plt wbc rbc anc alc neutrophil
neutrophils lymphocyte lymphocytes monocyte monocytes eosinophil eosinophils basophil basophils mcv
mch mchc rdw mpv sodium na potassium chloride bicarbonate hco co calcium magnesium phosphate
phosphorus glucose glu creatinine creat urea bun nitrogen albumin protein bilirubin bili alkaline
phosphatase alp alt ast ggt ldh ck cpk troponin trop lactate ferritin iron tibc transferrin
cholesterol chol triglycerides triglyceride tg hdl ldl vldl a1c hba tsh ft insulin cortisol crp esr
inr ptt aptt bnp ntprobnp probnp procalcitonin psa cea afp ige igg igm iga amylase
lipase urate uric ammonia ketones ketone ph pco po osmolality egfr gfr crcl cd viral vl hiv rna dna
fev fvc pef dlco ef lvef iq mmse moca phq gad nihss apache sofa qsofa news meld apgar kps ecog
karnofsky barthel charlson elixhauser frailty asa braden morse glasgow apfel caprini wells
propensity iptw ipw zscore zscores tscore probability prob likelihood logit odds residual residuals
vitamin folate folic fibrinogen dimer testosterone estradiol oestradiol progesterone prolactin pth lh fsh
hcg acth shbg dhea dheas peptide calcitonin thyroglobulin homocysteine lipoprotein apolipoprotein apob
neut neuts lymph lymphs mono monos eos baso basos phos alb tbili dbili alkphos hscrp tnf
vas nrs moca mrs rankin edss nyha gleason stage grade likert apgar parity gravida qtc qrs qt
fdr padj pvalue pval qvalue coefficient coef mean median iqr max quartile tertile quintile decile centile
fc ebl wavelength amplitude voltage absorbance fluorescence luminescence
""".split())
# Round 7: measurement names whose tokens lose a digit or a short part ("Vitamin B12", "Free T4", "Ki-67",
# "CA 19-9", "IgG", "Log2FC"), matched against the words of the name as written.
# A short code that is also a time point, a stage or a day (T1 to T4, D2, B1) is not one of them.
MEASUREMENT_COMPACT = frozenset("""
b12 ft3 ft4 ki67 ca125 ca199 ca153 cd4 cd8 cd3 cd19 cd20 il6 il2 il10 igg ige iga igm
log2fc logfc ddimer cpeptide hba1c spo2 sao2 fio2 pao2 paco2 etco2 pco2 po2 fev1 fev1fvc vo2 vo2max
moca mrs qtc pfs dfs efs rfs
""".split())
MEASUREMENT_PHRASES = ("p value", "adj p", "fold change", "pack years", "blood loss", "urine output", "fluid balance",
                       "fluid intake", "fluid output", "free t",
                       "c peptide", "d dimer", "vitamin d", "vitamin b", "ki 67", "ca 125", "ca 19", "il 1", "il 2",
                       "il 6", "il 10", "cd 4", "cd 8")
# Words that make a number column a list of identifiers whatever else it says ("Lab No", "Sample
# ID", "Visit Number"); "number of" is a count.
NUMBER_ID_WORDS = frozenset("""
id ids identifier identifiers uid uuid guid no nr nbr num nummer numero ref refs reference key keys
code codes link linkage token tag tags file files folder dossier record records chart registry
register registration reg accession barcode serial account acct mrn mbi seq sequence fallnummer
label labels pseudo pseudonym pseudonyms pseudoid lot lots batch batches
""".split())
# Words that name what a row is about. As the last word of a column name they make it that thing's
# number ("Glucose Case", "Count Patient", "Dose Encounter"), whatever measurement word comes before.
HEAD_ID_WORDS = frozenset("""
case cases episode specimen sample patient pt subject participant encounter chart person client
member donor recipient kit box slot claim claims policy policies invoice invoices account accounts record
records plan bill receipt voucher visit admission
""".split())
# "Days Since Encounter", "Cost per Case": a preposition before the last word makes it a measurement
# of that thing, not its number.
HEAD_ID_PREPOSITIONS = frozenset("since from to after before per of at by until between for in".split())
# Units of time short enough that a number of five digits is still a plausible duration.
SMALL_TIME_WORDS = frozenset("""
hour hours hr hrs h minute minutes min mins second seconds sec secs s ms msec millisecond milliseconds
""".split())
# Words of a column name that say its numbers are durations or times.
TIME_WORDS = frozenset("""
time times day days week weeks wk wks month months duration los interval delay elapsed latency lag
""".split()) | SMALL_TIME_WORDS


def measurement_header(header: str) -> bool:
    """True for a column name that says its numbers are measurements: a lab, a vital sign, a
    count, a score, a dose, a unit, money or a duration ("WBC", "Heart Rate", "Steps", "Total
    Cost", "Dose mg", "Number of Visits", "HbA1c (%)"), and no word that says identifier ("Lab
    No", "Sample ID")."""
    t = column_tokens(header)
    ts = set(t)
    raw = str(header)
    count_phrase = _has(t, "number of", "no of", "num of", "count of", "n of", "amount of") \
        or bool(re.search(r"#\s*of\b", raw, re.I))
    if ts & NUMBER_ID_WORDS and not count_phrase:
        return False
    # Round 8: a number sign names a number of a thing ("Dose #", "Count#", "Lot #"), unless it says "# of" or
    # stands alone in brackets as a unit ("Visits (#)").
    if "#" in re.sub(r"[(\[]\s*#\s*[)\]]", "", raw) and not count_phrase:
        return False
    if "number" in ts and not count_phrase:
        return False
    if len(t) > 1 and t[-1] in HEAD_ID_WORDS and t[-2] not in HEAD_ID_PREPOSITIONS and not count_phrase:
        return False
    # "Number of Visits Record": the thing counted is not the last word, which names whose number it is
    # (round 5); "Number of Records" is a count.
    if count_phrase and len(t) > 2 and (t[-1] in HEAD_ID_WORDS or t[-1] in NUMBER_ID_WORDS) \
            and t[-2] not in HEAD_ID_PREPOSITIONS:
        return False
    compact = re.sub(r"[^a-z0-9]", "", raw.lower())
    written = set(re.split(r"[^a-z0-9]+", unicodedata.normalize("NFKC", raw).lower())) - {""}
    return bool(count_phrase or ts & MEASUREMENT_WORDS or "%" in raw or _unit_in_brackets(raw)
                or written & MEASUREMENT_COMPACT or _has(t, *MEASUREMENT_PHRASES)
                or any(w in compact for w in ("spo2", "sao2", "fio2", "pao2", "paco2", "etco2", "o2sat",
                                              "hba1c", "egfr", "pco2", "po2")))


TIME_UNITS = _phrases("""y|yr|yrs|year|years|mo|mos|month|months|wk|wks|week|weeks|d|day|days|h|hr|hrs|
hour|hours|min|mins|minute|minutes|s|sec|second|seconds|ms|msec""")


def time_only_header(header: str) -> tuple[bool, bool]:
    """(True, small) for a column name that names a measurement only by a word of time ("Time",
    "Event Time", "Visit Day", "Days", "Duration", "LOS"), with `small` True when that word is a
    unit short enough for a five-digit duration (minutes, seconds, hours)."""
    t = column_tokens(header)
    ts = set(t)
    raw = str(header)
    if not measurement_header(header) or "%" in raw or _unit_in_brackets(raw):
        return False, False
    if _has(t, "length of stay", "length of hospital stay", "length of icu stay"):
        ts = (ts - {"length", "stay"}) | {"los"}
    if not ts & TIME_WORDS or (ts & MEASUREMENT_WORDS) - TIME_WORDS:
        return False, False
    units = {fold(m.group(1)) for m in re.finditer(r"[(\[]\s*([^)\]]{1,20})\s*[)\]]", raw)}
    return True, bool(ts & SMALL_TIME_WORDS or units & SMALL_TIME_WORDS)


def _unit_in_brackets(raw: str) -> bool:
    """A unit of measurement in brackets ("(mg/dL)", "[kg]"); a unit of time ("(years)", "[y]")
    does not count, because ages are written in it."""
    for m in re.finditer(r"[(\[]\s*([^)\]]{1,20})\s*[)\]]", raw):
        unit = fold(m.group(1))
        if unit in UNITS and unit not in TIME_UNITS:
            return True
    return False


def _long_integer_part(n: str) -> str | None:
    """The digits before the point of a number in any written form ("-4527832", "4527832.", "4527832.5",
    "4.527832E+06"), for the repeated record number check (round 5)."""
    m = re.fullmatch(r"[+-]?(\d+)(?:\.\d*)?", n.strip())
    if m:
        return m.group(1)
    # An exponent keeps a record number's digits only with five or more of them ("4.52783E+06"); a
    # measurement of two or three ("1.37E+06" copies/mL) is not one.
    mantissa = re.split(r"[eE]", n.strip())[0].lstrip("+-").replace(".", "").strip("0")
    if len(mantissa) < 5:
        return None
    try:
        f = abs(float(n))
    except ValueError:
        return None
    return str(int(f)) if 1e6 <= f < 1e16 else None


def _integer_digits(n: str) -> str | None:
    """The digits of a whole number written as a number ("4527832", "00088221", "6135517.0",
    "2589882.00"), or None for a number with a fraction."""
    m = re.fullmatch(r"[+]?(\d+)(?:\.0+)?", n.strip())
    return m.group(1) if m else None


EXCEL_DATE_RANGE = (10000, 73050)  # Excel serial days 1927-05-18 to 2099-12-31


def _packed_date(d: str, reference_year: int) -> bool:
    """A date written as a whole number with no separator in an order _compact_date does not
    read: YYMMDD of six digits, and M/D/YYYY or YYYY/M/D with a one-digit month or day (seven
    digits: 3262017, 2016112)."""
    def ok(y: int, mo: int, dd: int) -> bool:
        return 1 <= mo <= 12 and 1 <= dd <= 31 and (y < 100 or 1880 <= y <= reference_year + 10)
    if len(d) == 6:
        return ok(int(d[:2]), int(d[2:4]), int(d[4:]))
    if len(d) == 7:
        return (ok(int(d[3:]), int(d[0]), int(d[1:3])) or ok(int(d[3:]), int(d[:2]), int(d[2]))
                or ok(int(d[:4]), int(d[4]), int(d[5:])) or ok(int(d[:4]), int(d[4:6]), int(d[6])))
    return False


def _bare_number(v: str) -> bool:
    """A number with no unit written beside it ("37.8", "-122.4", "<0.5", "1,250", "4.5E+06"); "5.2 mg/dL",
    "12%" and "95 y" carry one (round 7)."""
    m = NUMBER_WITH_UNIT.fullmatch(_plain(v))
    return bool(m) and not m.group("u")


UNIX_EPOCH = datetime(1970, 1, 1)
JULIAN_DAY_ORDINAL_OFFSET = 1721425  # Julian day 2451545 (2000-01-01 at noon) is ordinal 730120


def numeric_date_year(n: str, reference_year: int, whole_julian: bool = True) -> int | None:
    """The calendar year of a number shaped like a date written as a number, or None (round 7): a decimal
    whose integer part is a year from 1850 to five years after the reference year (a decimal year, a year
    and a week or a day, "2021.07", "2021.123", "1926.164"); a number of 10 or 13 digits before its point,
    signed or not, that is a Unix timestamp in seconds or milliseconds within those years
    ("1629478800.373", "-1204783199.85"); and a number of 7 digits that is a Julian day number or a year
    and a day of the year (YYYYDDD) within them ("2459215.5", "2021123"; whole ones only with
    `whole_julian`)."""
    s = n.strip().replace(",", "")
    top = reference_year + 5
    m = re.fullmatch(r"([+-]?)(\d+)(?:\.(\d*))?", s)
    if not m:
        try:  # an exponent ("1.6294788E+09"), as Excel writes a long number
            x = float(s)
        except ValueError:
            return None
        if not math.isfinite(x) or abs(x) < 1e9:
            return None
        m = re.fullmatch(r"([+-]?)(\d+)(?:\.(\d*))?", f"{x:.3f}")
        if not m:
            return None
    sign, ip, frac = m.group(1), m.group(2), m.group(3)
    fraction = bool(frac and frac.strip("0"))
    if len(ip) == 4 and fraction and not sign and 1850 <= int(ip) <= top:
        return int(ip)
    if len(ip) in (10, 13):
        seconds = float(f"{sign}{ip}.{frac or 0}") / (1000 if len(ip) == 13 else 1)
        if abs(seconds) > 5e10:
            return None
        year = (UNIX_EPOCH + timedelta(seconds=seconds)).year
        return year if 1850 <= year <= top else None
    if len(ip) == 7 and not sign and (fraction or whole_julian):
        # A Julian day number counts days from noon; its civil date is the proleptic ordinal 1721425 days on.
        ordinal = math.floor(float(f"{ip}.{frac or 0}") + 0.5) - JULIAN_DAY_ORDINAL_OFFSET
        if 1 <= ordinal <= date.max.toordinal():
            year = date.fromordinal(ordinal).year
            if 1850 <= year <= top:
                return year
        if 1850 <= int(ip[:4]) <= top and 1 <= int(ip[4:]) <= 366:
            return int(ip[:4])
    return None


def year_named_header(header: str, two_digit: bool = False) -> bool:
    """A column name with a word for a year or a date ("Year", "Admit Year", "Dx Yr", "Jahr", "Y", "Years",
    "Visit Date"), under which a column of four-digit years is a column of years (round 7); with `two_digit`,
    one with a word for a year that is not a single letter or a date ("Dx Yr", "YY", "Jahr"), under which
    numbers up to 99 are years too, as year_columns() reads them."""
    t = column_tokens(header)
    if two_digit:
        return any(x in YEAR_NAME_WORDS or (len(x) > 2 and x.endswith(("yr", "year"))) for x in t)
    return any(x in YEAR_NAME_WORDS or x in YEAR_TOKENS or x in DATE_WORDS or x in YEAR_WORDS_OTHER_LANGUAGES
               or x in ("years", "yrs") or (len(x) > 2 and x.endswith(("yr", "year", "years"))) for x in t)


TIME_UNIT = re.compile(r"(?i)\s*(\d{1,6}(?:\.\d+)?)\s*(y|yr|yrs|years?|yo|y/o|mo|mos|mon|mths?|months?|wk|wks"
                       r"|weeks?|d|dy|dys|days?)\.?")


# Words that can mean an age or old age in a column name, under which a decimal from 90 to 125 counts
# as an age too ("Eta" 95.5, "Old", "Y Old", "Year", "Elderly", "Seniority"; round 4).
AGE_LIKE_WORDS = frozenset("eta old older elderly senior seniors seniority year yr anni ans anos jahre yo".split())


def _age_years_of_value(v: str, decimals: bool = False) -> float | None:
    """The age in years of a value that is a whole number of up to three digits ("95", "95.0"),
    or a number with a unit of time ("95 y", "1140 mo", "1,100 months", "34700 days"), and with
    `decimals` a decimal of up to three digits before the point ("95.5"); None for anything else."""
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", _plain(v))
    # Round 7: "older than", written as a comparator before the number (">99", ">= 95", "≥90").
    s = re.sub(r"^(?:>=|=>|>|≥)\s*", "", s)
    m = re.fullmatch(r"(\d{1,3})(?:\.0+)?", s)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"\d{1,3}\.\d+", s)
    if m and decimals:
        return float(s)
    m = TIME_UNIT.fullmatch(s)
    if m:
        unit = m.group(2).lower()
        factor = 365.25 if unit == "d" else (_unit_factor(unit) or 1.0)
        return float(m.group(1)) / factor
    return None


ENCOUNTER_COUNT_WORDS = frozenset("""
visits encounters admissions readmissions episodes stays occurrences appointments appts consults
""".split())


def number_rule(header: str, values: list[str], reference_year: int) -> tuple[str, str, str, int] | None:
    """(finding, action, phi type, cells) for a column whose numbers the script cannot verify as
    measurements (see the section comment). `values` are the column's cells that are not blank
    or missing-value words; only those that read as numbers are judged, and each one is judged
    on its own: a single record number, ZIP code, serial or age over 89 among measurements is
    enough. None when every one of them is a measurement."""
    vals = [v.strip() for v in values if v.strip() and v.strip() not in TOOL_PLACEHOLDERS
            and not TOOL_OUTPUT.fullmatch(v.strip()) and fold(v) not in MISSING_PHRASES]
    nums = [(v, number_like(v)) for v in vals]
    nums = [(v, n) for v, n in nums if n is not None and not BLOOD_PRESSURE.fullmatch(_plain(v))]
    if not nums:
        return None
    total = len(nums)
    measurement = measurement_header(header)
    time_only, small_unit = time_only_header(header)
    digits = [_integer_digits(n) for _, n in nums]
    whole = [d for d in digits if d is not None]
    # Dates written as whole numbers in an order the value rules do not read (YYMMDD, 3262017).
    if len(whole) == total and len(set(whole)) >= 3 and all(_packed_date(d, reference_year) for d in whole):
        return (f"whole numbers shaped like dates with no separator in {total} cells (possible dates)",
                "redact", "date", total)
    # Round 7: dates written as numbers that are not whole (decimal years, year.week and year.day, Unix
    # timestamps with fractional seconds, Julian dates) passed as measurements under any column name. A
    # number whose shape is one of these is a date under any name; under a name that names a measurement
    # it takes most of the column's numbers, so one cost of 1999.99 does not make a column of costs a date.
    # Whole numbers of seven digits under a name that names no measurement are left to the record number
    # rule below, which pseudonymizes them (a record number can have that shape too).
    dated = [n for v, n in nums if _bare_number(v)
             and numeric_date_year(n, reference_year, whole_julian=measurement) is not None]
    if dated and (not measurement or 2 * len(dated) > total):
        every = len(dated) == total and all(_bare_number(v) for v in vals if fold(v) not in MISSING_PHRASES)
        return (f"numbers shaped like dates written as numbers (a decimal year such as 2021.07, a Unix timestamp "
                f"of 10 or 13 digits or a 7-digit Julian date) in {len(dated)} of {total} cells (possible dates)",
                "year" if every else "redact", "date", len(dated))
    # Excel date and time serials ("44269.4375"), under any column name but one that names a
    # measurement other than a time; under a day, a week, a month or a bare time a number of five
    # digits is not a duration either ("Visit Day" 43005), unless the unit is minutes or seconds.
    # Round 7: under such a name every number of five digits before its point counts, whole or not, since
    # a duration of 10000 days, weeks or months is not one.
    # Round 8: under such a name six or more digits are not a duration either: a date or a clock time written as
    # a number (YYMMDD, HHMMSS, an HL7 time 143005.123, a Unix timestamp of nine digits).
    def excel(n: str) -> bool:
        m = re.fullmatch(r"(\d{5,})(?:\.\d+)?", n)
        if not m:
            return False
        if len(m.group(1)) > 5:
            return time_only and not small_unit
        return EXCEL_DATE_RANGE[0] <= int(m.group(1)) <= EXCEL_DATE_RANGE[1] or (time_only and not small_unit)
    serial = [n for _, n in nums if excel(n) and (_integer_digits(n) is None or (time_only and not small_unit))]
    if serial and (not measurement or (time_only and not small_unit)):
        return (f"numbers shaped like Excel date and time serials, or dates and clock times written as numbers, in "
                f"{len(serial)} of {total} cells (possible dates)", "redact", "date", len(serial))
    if not measurement:
        # Scientific notation: how Excel writes a long record, account or phone number in a CSV.
        exponent = [n for _, n in nums if re.search(r"[eE]", n)]
        if exponent:
            return (f"numbers written with an exponent in {len(exponent)} of {total} cells (as Excel writes "
                    "long record, account and phone numbers)", "pseudonym_id", "id", len(exponent))
        # Decimals with five or more digits before the point: grid coordinates in metres (UTM),
        # dates or record numbers with a fraction.
        long_decimal = [n for _, n in nums if _integer_digits(n) is None
                        and len(n.lstrip("+-").split(".")[0]) >= 5]
        if long_decimal:
            return (f"decimal numbers with five or more digits before the point in {len(long_decimal)} of "
                    f"{total} cells (possible grid coordinates, dates or record numbers)", "redact", "id",
                    len(long_decimal))
    # Record numbers: whole numbers of four or more digits that are not all years, under a column
    # name that names no measurement, or with a leading zero under any column name.
    long_ = [d for d in whole if len(d) >= 4]
    zero = [d for d in whole if len(d) >= 4 and d.startswith("0")]
    years = all(1880 <= int(d) <= reference_year + 10 and len(d) == 4 for d in whole) and len(whole) == total
    if (long_ and not measurement and not years) or zero:
        five = sum(1 for d in long_ if len(d) >= 5)
        what = "five or more digits" if five >= len(long_) / 2 else "four or more digits"
        where = ("with a leading zero" if measurement else "under a column name that names no measurement")
        return (f"whole numbers of {what} in {len(long_)} of {total} cells {where} (possible record numbers, "
                "account numbers, ZIP codes or dates written as numbers)", "pseudonym_id", "id", len(long_))
    # Record numbers of seven or more digits that repeat under a measurement name (round 4): a count or
    # an amount that long is rarely the same twice, a record number repeats across a patient's visits.
    # Round 6: a count of a patient's visits, encounters or admissions is never six digits, so under such a
    # name a repeated number of six digits is a record number too.
    least = 6 if set(column_tokens(header)) & ENCOUNTER_COUNT_WORDS else 7
    seven = [d for d in (_long_integer_part(n) for _, n in nums) if d and len(d.lstrip("0")) >= least]
    # Round 8: also when the repeated record numbers are a few cells among measurements (a Glucose column with
    # one record number in twenty cells), whatever their share: a number that long, not a round one, rarely
    # comes out the same twice as a measurement.
    counts: dict[str, int] = {}
    for d in seven:
        counts[d] = counts.get(d, 0) + 1
    repeated = [d for d in seven if counts[d] > 1 and not re.search(r"000$", d)]
    if measurement and seven and (len(seven) - len(set(seven)) > len(set(seven)) or repeated):
        return (f"whole numbers of {'six' if least == 6 else 'seven'} or more digits that repeat, in {len(seven)} of "
                f"{total} cells (possible record numbers, though the column name names a measurement)",
                "pseudonym_id", "id", len(seven))
    # Round 8: a column that names a measurement only by a unit of length ("X (m)", "Y (m)", "Value (km)") holds
    # grid coordinates in metres as often as lengths; numbers of five or more digits before the point are
    # redacted there unless the name says what was measured (Distance, Length, Height, Elevation, Depth).
    if measurement and _length_unit_only(header):
        grid = [n for _, n in nums if len(n.lstrip("+-").split(".")[0].replace(",", "")) >= 5]
        if grid:
            return (f"numbers with five or more digits before the point in {len(grid)} of {total} cells under a column "
                    "name that names only a unit of length (possible grid coordinates)", "redact", "geo", len(grid))
    if measurement:
        return None
    # Short study and record numbers under a column name of a person's or a record's number ("Study ID",
    # "Pat No", "Chart", "Case", round 4).
    if len(whole) == total and not years and record_style_header(header):
        return (f"whole numbers in {total} cells under a column name of a person's or a record's number (possible "
                "study or record numbers)", "pseudonym_id", "id", total)
    # Ages: a whole number from 90 to 125 (or a number with a unit of time) among any others; under a
    # column name with a word that can mean age or old age (ETA, Old, Year, Elderly), a decimal too.
    decimals = bool(set(column_tokens(header)) & AGE_LIKE_WORDS) or "".join(column_tokens(header)) in AGE_LIKE_WORDS
    ages = [_age_years_of_value(v, decimals) for v, _ in nums]
    over = sum(1 for a in ages if a is not None and 90 <= a <= 125)
    if over:
        # Round 7: the other numbers of such a column are not verified either, so under a name that does not say
        # age (Value, Result, Visit No) the column is redacted; under a word that can mean age or old age, or
        # with a unit of time in every cell ("95 y"), it is grouped as ages and the rest kept.
        grouped = decimals or all(not _bare_number(v) for v, _ in nums)
        return (f"whole numbers from 90 to 125 in {over} of {total} cells under a column name that names no "
                "measurement (possible ages over 89" + (")" if grouped else
                                                        "; the script cannot verify the other numbers either)"),
                "age" if grouped else "redact", "age", over)
    # Seven digits written as a decimal of three digits and four places ("555.0134") are the shape of a
    # local telephone number (round 5).
    phone = [n for _, n in nums if re.fullmatch(r"\d{3}\.\d{4}", n) and float(n) >= 200]
    if phone:
        return (f"decimal numbers of three digits and four places in {len(phone)} of {total} cells (the shape of a "
                "telephone number)", "redact", "phone", len(phone))
    # A latitude or a longitude: judged cell by cell (round 4), so a column that mixes precise and rounded
    # coordinates is found by its precise cells. A decimal of four or more places from 1 to 180 in any
    # cell, under a column name that names no measurement, is enough.
    precise = [n for _, n in nums if re.fullmatch(r"[+-]?\d{1,3}\.\d{4,}", n) and 1 <= abs(float(n)) <= 180]
    shape = _coordinate_shape([n for _, n in nums])
    if shape and len(nums) == total and shape["places4"]:
        precise = [n for _, n in nums]
    if precise:
        return (f"decimal numbers of four or more places within the range of a latitude or a longitude in "
                f"{len(precise)} of {total} cells (a possible coordinate)", "redact", "geo", len(precise))
    # Round 6: a latitude or a longitude of two or three places (1.1 km and 110 m, finer than a state) was
    # kept as a measurement under a neutral or axis-like name (Value, X, Y, Loc X, Pos, Point, Geo1, Col4,
    # Index, Result). Under a column name that names no measurement, a column of numbers within 180 with
    # two or more places in three quarters of its cells or more (a coordinate written with two or three
    # places loses a trailing zero in a tenth of them) and one value of 10 or more is a possible coordinate,
    # and so is a column most of whose numbers are negative decimals from -60 to -180 (a longitude in the
    # Americas, also with one place). The person keeps such a column with --keep once they confirm it.
    # (A value written with its unit, "37.77 mg", is a measurement.)
    plain = [(n, float(n)) for v, n in nums if re.fullmatch(r"[+-]?\d{1,3}(?:\.\d+)?", n) and _plain(v) == n]
    if len(plain) == total:
        two = [n for n, _ in plain if len(n.partition(".")[2]) >= 2]
        if all(abs(x) <= 180 for _, x in plain) and 4 * len(two) >= 3 * total and max(abs(x) for _, x in plain) >= 10:
            return (f"decimal numbers of two or more places within the range of a latitude or a longitude in "
                    f"{len(two)} of {total} cells, under a column name that names no measurement (a possible "
                    "coordinate)", "redact", "geo", len(two))
        west = [n for n, x in plain if "." in n and -180 <= x <= -60]
        if 2 * len(west) > total:
            return (f"negative decimal numbers from -60 to -180 in {len(west)} of {total} cells, under a column name "
                    "that names no measurement (a possible longitude)", "redact", "geo", len(west))
    # Round 7: numbers fail closed by NAME, as text does. Rounds 5 and 6 found numbers that passed every
    # shape check under neutral names (one-decimal coordinate pairs, decimal years, record numbers under
    # Value, Result, Col3, X, Y), and a list of the shapes identifiers take never closes. A number is kept
    # by default only under a column name that names a measurement (above), or with a unit of measurement
    # written beside it in its cell ("5.2 mg/dL"); a column of four-digit years under a name for a year is a
    # column of years, which Safe Harbor allows. Any other number goes to the person's decision.
    bare = [v for v, _ in nums if _bare_number(v)]
    written_plainly = all(_plain(v) == n for v, n in nums)
    two_digit_years = len(whole) == total and all(len(d.lstrip("0") or "0") <= 2 for d in whole)
    if bare and not (written_plainly and years and year_named_header(header)) \
            and not (written_plainly and two_digit_years and year_named_header(header, two_digit=True)):
        return (f"numbers ({len(bare)} cells) under a column name that names no measurement: the script cannot verify "
                "that they are not identifiers, dates or coordinates (a measurement name such as WBC, Dose (mg), Pain "
                "Score or Steps, or a unit in the name, says what they are)", "redact", "unverified", len(bare))
    return None


LENGTH_UNIT_WORDS = frozenset("m km mm cm ft feet foot metre metres meter meters mi mile miles yd yard yards".split())
DISTANCE_WORDS = frozenset("""
distance distances dist length lengths len height heights ht elevation altitude alt depth depths width diameter
size circumference thickness radius perimeter travel travelled traveled stride span gap
""".split())


def _length_unit_only(header: str) -> bool:
    """A column name that names a measurement only by a unit of length ("X (m)", "Value (km)"), with no word for
    what was measured."""
    t = column_tokens(header)
    ts = set(t)
    units = {fold(m.group(1)) for m in re.finditer(r"[(\[]\s*([^)\]]{1,20})\s*[)\]]", str(header))}
    if not (units | ts) & LENGTH_UNIT_WORDS or ts & DISTANCE_WORDS:
        return False
    return not (ts & MEASUREMENT_WORDS) - LENGTH_UNIT_WORDS and not (units - LENGTH_UNIT_WORDS) & UNITS


def _coordinate_shape(values: list[str]) -> dict | None:
    vals = _shape_values(values)
    if not vals or not all(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", v) for v in vals):
        return None
    nums = [float(v) for v in vals]
    if any(abs(x) > 180 for x in nums):
        return None
    places = [len(v.split(".", 1)[1]) if "." in v else 0 for v in vals]
    n = len(vals)
    if sum(1 for p in places if p >= 2) / n < 0.8:
        return None
    return {"lat": all(abs(x) <= 90 for x in nums),
            "beyond_90": any(abs(x) > 90 for x in nums),
            "one_sign": all(x < 0 for x in nums) or all(x > 0 for x in nums),
            "precise": sum(1 for p in places if p >= 3) / n >= 0.8,
            "places4": sum(1 for p in places if p >= 4) / n >= 0.8,
            "max": max(abs(x) for x in nums), "cells": n}


def _latitude_partner(values: list[str]) -> bool:
    """Numbers within 90, most of them with a decimal point and one of 10 or more: the latitude beside a
    longitude (round 6)."""
    vals = [v for v in _shape_values(values) if fold(v) not in MISSING_PHRASES]
    if not vals or not all(re.fullmatch(r"[+-]?\d{1,2}(?:\.\d+)?", v) for v in vals):
        return False
    xs = [float(v) for v in vals]
    return all(abs(x) <= 90 for x in xs) and max(abs(x) for x in xs) >= 10 \
        and 2 * sum(1 for v in vals if "." in v) > len(vals)


def coordinate_pairs(columns: list[tuple[int, list[str]]], plain: set[int] = frozenset()) -> dict[int, int]:
    """Column positions (and cell counts) of adjacent columns shaped like latitude and
    longitude: decimal numbers within +-90 next to decimal numbers within +-180, both
    with three or more decimal places, or with two when the second column reaches past
    +-90 with one sign (west or east of the 90th meridian), or, since round 6, when neither
    column name names a measurement (`plain`, positions). One of the two must reach
    10 or more, which every populated place outside the Gulf of Guinea does and which
    scores such as z-scores, propensities and weights rarely do."""
    shapes = {i: _coordinate_shape(vals) for i, vals in columns}
    found: dict[int, int] = {}
    for (i, _), (j, _) in zip(columns, columns[1:]):
        a, b = shapes.get(i), shapes.get(j)
        if not a or not b or j != i + 1 or max(a["max"], b["max"]) < 10:
            continue
        for lat, lon in ((a, b), (b, a)):
            if lat["lat"] and (lat["precise"] and lon["precise"]
                               or lon["beyond_90"] and lon["one_sign"]
                               or i in plain and j in plain):
                found[i], found[j] = a["cells"], b["cells"]
                break
    return found


def header_identifier_kinds(header: str, scrubber: Scrubber) -> list[str]:
    """The identifier patterns in a header cell. A labelled name ("Patient Key", "Mother Maiden")
    is the shape of most column names, so it counts only with a colon or an equals sign after the
    label ("Patient: Okafor")."""
    h = str(header).strip()
    # A fiscal year ("FY2022 Cost", round 5) is a year; the year rules still read it.
    h = re.sub(r"(?i)(?<![a-z0-9])fy[\s_-]?((?:18|19|20)\d{2})(?!\d)", r"FY \1", h)
    kinds = scrubber.find(h) if h else []
    # Round 8: the cell patterns also read the header as the date grammars fold it (full-width and other
    # scripts' digits as ASCII), so a date is one definition for cells and column names.
    folded = fold_for_dates(h)[0]
    if folded != h and "date" in scrubber.find(folded):
        kinds.append("date")
    return [k for k in kinds if k != "name" or re.search(r"[:=]", h)]


# Numbers in a column name (round 4). A wide per-patient table names its columns after the patient
# ("Patient 3767393", "Sample 2065209", "Chart 4749746"), and a column name can carry a ZIP code, a
# coordinate or a birth year ("Weight 94110", "Weight 37.7749", "Cohort 1925"). A column name may hold
# a short number (Col1, TP53, Q3, 2nd, Visit 2021); a run of five or more digits, a decimal of four or
# more places and a year 90 or more years before the reference year make the first row refused, like
# an identifier pattern. The digits of a closed code are not counted: Ensembl, RefSeq, rsID and a
# genomic position written after chr ("chr1:12345678", "chr7_55191822_T_G").
HEADER_CODES = re.compile(
    rf"(?<![A-Za-z0-9])(?:{_ENSEMBL}|{_REFSEQ}|{_RSID}"
    r"|(?i:chr)(?:[1-9]|1\d|2[0-2]|[XYxy]|M[Tt]?|m[Tt]?)[:_.-]\d{1,9}(?:[-_]\d{1,9})?"
    r"(?:[:_.-][ACGTNacgtn]+[:_.>/-][ACGTNacgtn]+)?)"
    r"(?![A-Za-z0-9])")


def header_number_kinds(header: str, reference_year: int) -> list[str]:
    """The numbers in a column name that are not a short number or a closed code: a run of five or
    more digits, also written in groups with any separator (4,527,832, 376 7393, 37_67_393, 12 34
    56 78), a decimal of four or more places, a four-digit year 90 or more years before the reference
    year, and a date element finer than the year (header_date_kinds). No value is returned, only the
    kinds."""
    s = HEADER_CODES.sub(" ", unicodedata.normalize("NFKC", str(header)))
    kinds = []
    if re.search(r"\d[.,]\d{4,}", s):
        kinds.append("a decimal of four or more places (a possible coordinate)")
    grouped = re.sub(r"\d{1,3}(?:[,'  ]\d{3})+(?!\d)|\d{1,3}(?:[. ]\d{3}){2,}(?!\d)",
                     lambda m: re.sub(r"\D", "", m.group(0)), s)
    if any(len(run) >= 5 for run in re.findall(r"\d+", grouped)) or _grouped_record_number(s, reference_year):
        kinds.append("a number of five or more digits, also written in groups (a possible record number or ZIP "
                     "code)")
    if any(len(run) == 4 and 1800 <= int(run) <= reference_year - 90 for run in re.findall(r"\d+", s)):
        kinds.append("a year 90 or more years ago (a possible birth year)")
    kinds += header_date_kinds(s, reference_year)
    return kinds


# Round 5: a record number written into a column name in groups ("Patient 376 7393", "Pt 37 67 393",
# "Patient 37_67_393", "ID 12 34 56 78", "Weight 12 345") was shown, because only a run of digits with
# no separator, or joined by a hyphen, a slash, a comma or a dot in groups of three, was counted. Now the
# separators are removed first: the digits of every run of numbers joined by anything that is not a
# letter or a digit (spaces, underscores, dots, hyphens, commas, slashes, colons, brackets) are counted
# together, and five or more make the first row refused. A run that is only years ("2019-2020"), a
# decimal or a range of two decimals of up to three digits before the point ("37.775", "18.5-24.9"), or
# two whole numbers joined by a hyphen or a slash alone with fewer than six digits ("70-100", "120/80", as
# before) is not counted. A number that starts after a Latin letter is part of a word ("HbA1c 2021", "CD4
# 2020", "Q1 2020") and starts no run.
HEADER_DIGIT_RUN = re.compile(r"(?<![A-Za-z\u00c0-\u024f])\d+(?:[\W_]{1,3}\d+)+")


def _grouped_record_number(s: str, reference_year: int) -> bool:
    for m in HEADER_DIGIT_RUN.finditer(s):
        run = m.group(0)
        groups = re.findall(r"\d+", run)
        if all(len(g) == 4 and 1880 <= int(g) <= reference_year + 10 for g in groups):
            continue
        total = sum(len(g) for g in groups)
        if total < 5:
            continue
        pieces = [p for p in re.split(r"[^\d.,]+", run) if p]
        if len(pieces) <= 2 and all(re.fullmatch(r"\d{1,3}(?:[.,]\d{1,3})?", p) for p in pieces) \
                and any(re.search(r"[.,]", p) for p in pieces):
            continue  # a decimal, or a range of two decimals
        seps = re.findall(r"\D+", run)
        if len(groups) == 2 and seps[0] in ("-", "/", "\u2013") and total < 6:
            continue  # a range or a ratio of two whole numbers (70-100, 120/80)
        return True
    # Numbers joined by a hyphen or a slash, wherever they start (round 4: "376-7393", "45/27832").
    return any(sum(len(g) for g in groups) >= 6
               and not all(len(g) == 4 and 1880 <= int(g) <= reference_year + 10 for g in groups)
               for groups in (re.findall(r"\d+", m.group(0)) for m in re.finditer(r"\d+(?:[-/]\d+)+", s)))


# Round 5: a date written into a column name with a two-digit year or a month and a day ("Mar-19",
# "Jan20", "Sep12", "WBC Feb-20", "Visit Sep-12", "03/14", "14/3", "Q1 20", "W12 2020", "2020-W12") was
# shown, because only a four-digit year beside a month name was read as a date. In a wide per-patient
# export such a name is the month or the day of each person's visit or lab, a date element finer than
# the year, so it is refused like an identifier pattern: a month name or abbreviation (English, Spanish,
# French, German, Italian) next to a number of one, two or four digits, in either order; a month and a
# day written as numbers (with a leading zero, a year, or a day over 12 beside a slash: "03/14", "3-14-21",
# "3/14", "14/3", "14.3."); a quarter beside a year ("Q1 20", "Q1 2020", "2020Q1"); and a week beside a
# four-digit year ("W12 2020", "Week 12 2020", "2020-W12"). A month abbreviation joined to one or two
# digits with no separator is also the shape of a gene symbol (OCT4, Oct4, SEPT9, DEC1, MARCH5): that cell
# is withheld rather than refused (header_code_shaped), so it is never printed or copied ("Sep12" and
# "Mar19" are withheld too), and the person can confirm a gene symbol with --keep-name.
_HEADER_MONTHS = (
    "january|february|march|april|june|july|august|september|october|november|december|sept|jan|feb|mar|apr"
    "|may|jun|jul|aug|sep|oct|nov|dec|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre"
    "|octubre|noviembre|diciembre|ene|abr|dic|janvier|fevrier|mars|avril|juin|juillet|aout|septembre|octobre"
    "|novembre|decembre|janv|fevr|avr|juil|januar|februar|marz|maerz|mai|juni|juli|oktober|dezember|mrz|okt"
    "|dez|gennaio|febbraio|aprile|maggio|giugno|luglio|settembre|ottobre|dicembre")
_HEADER_MONTH_THEN_NUMBER = re.compile(
    r"(?<![^\W\d_])(?P<m>" + _HEADER_MONTHS + r")(?P<sep>\.?[\s'\u2019`._/\-\u2013]{0,3})(?P<n>\d{1,4})(?!\d)",
    re.I)
_HEADER_NUMBER_THEN_MONTH = re.compile(
    r"(?<![\d.,])(?P<n>\d{1,2})(?:st|nd|rd|th)?(?P<sep>[\s'\u2019._/\-\u2013]{0,3})(?P<m>" + _HEADER_MONTHS
    + r")(?![^\W\d_])", re.I)
_HEADER_DAY_MONTH = re.compile(r"(?<![\d.,/\-])(\d{1,2})([/.\-])(\d{1,2})(?:\2(\d{4}|\d{2}))?(?P<dot>\.)?"
                               r"(?![\d/,\-]|\.\d)")
_HEADER_QUARTER = re.compile(
    r"(?<![^\W_])(?:q[1-4](?:\s+of\s+(?:\d{4}|'?\d{2})|[\s'\u2019_/\-]+'?\d{2}|[\s_/\-]*\d{4})|[1-4]q(?:\d{2}|\d{4})"
    r"|\d{4}[\s_/\-]*q[1-4]|'\d{2}\s*q[1-4]"
    r"|(?:[1-4](?:st|nd|rd|th)?[\s_-]*(?:quarter|qtr|quartal|trimestre)|(?:quarter|qtr|quartal|trimestre)[\s_-]*[1-4])"
    r"[\s_/,-]*(?:of\s+)?(?:\d{4}|'?\d{2}))(?![^\W_])", re.I)
_HEADER_WEEK_YEAR = re.compile(
    r"(?<![^\W\d_])(?:week|wk|w|kw|cw|woche|semana|semaine|settimana)\.?\s*[-_#]?\s*(?P<w>\d{1,2})"
    r"(?:\s*[-_/,.]\s*|\s+of\s+|\s+in\s+|\s+)(?P<y>\d{4}|'\d{2})(?!\d)"
    r"|(?<!\d)(?P<y2>\d{4})\s*-?\s*w(?:k|eek)?\s*(?P<w2>\d{1,2})(?!\d)", re.I)


def _month_day(a: int, b: int) -> bool:
    return (1 <= a <= 12 and 1 <= b <= 31) or (1 <= a <= 31 and 1 <= b <= 12)


def _header_ascii(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.replace("\u00df", "ss").translate(LETTERS_WITHOUT_DECOMPOSITION)


def _compact_month_code(m: re.Match, month_first: bool) -> bool:
    """A month abbreviation joined to one or two digits with no separator (OCT4, Oct4, SEPT9, Mar19)."""
    return not m.group("sep") and (not month_first or len(m.group("n")) <= 2)


def header_date_kinds(header: str, reference_year: int) -> list[str]:
    """The date elements finer than the year written into a column name (see above). No value is
    returned, only the kind."""
    s = _header_ascii(HEADER_CODES.sub(" ", unicodedata.normalize("NFKC", str(header))))

    def day_or_year(n: str) -> bool:
        return len(n) <= 2 or (len(n) == 4 and 1880 <= int(n) <= reference_year + 10)
    found = any(day_or_year(m.group("n")) and not _compact_month_code(m, True)
                for m in _HEADER_MONTH_THEN_NUMBER.finditer(s)) \
        or any(not _compact_month_code(m, False) for m in _HEADER_NUMBER_THEN_MONTH.finditer(s))
    for m in _HEADER_DAY_MONTH.finditer(s):
        a, sep, b, year = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
        if not _month_day(a, b):
            continue
        zero = m.group(1).startswith("0") or m.group(3).startswith("0")
        if (year and (len(year) == 2 or 1880 <= int(year) <= reference_year + 10)) or (zero and sep != ".") \
                or (sep == "." and (m.group("dot") or m.group(1).startswith("0"))) \
                or (sep == "/" and max(a, b) >= 13):
            found = True
    if _HEADER_QUARTER.search(s):
        found = True
    for m in _HEADER_WEEK_YEAR.finditer(s):
        w, y = (m.group("w"), m.group("y")) if m.group("w") else (m.group("w2"), m.group("y2"))
        if 1 <= int(w) <= 53 and (y.startswith("'") or 1880 <= int(y) <= reference_year + 10):
            found = True
    # Round 8: a date in any script or calendar the cell patterns read (2019年3月14日, 2019년 3월 14일,
    # 14 tháng 3 năm 2019, 14 Mac 2019, R1.5.1, 14 มีนาคม 2562), and a month and a day written as two numbers
    # with a hyphen or a slash, one of them over 12 (31-12, 14-3, WBC 3-19), or with a leading zero.
    if any(h.elements >= 2 for h in find_dates(HEADER_CODES.sub(" ", unicodedata.normalize("NFKC", str(header))),
                                               reference_year)):
        found = True
    if _header_number_pairs(s, reference_year)[0] or _header_date_words(s, reference_year)[0]:
        found = True
    return ["a date element finer than the year (a month, a day, a quarter or a week beside a number)"] if found else []


# Round 8: a month and a day written into a column name as two numbers. A pair joined by a hyphen, a slash
# or a dash in which one number is from 13 to 31 and the other from 1 to 12 (31-12, 12-31, 14-3, 9-19,
# WBC 3-19), or with a leading zero (03-14), is refused like a date; a pair of two numbers of 12 or less
# (3-4, 3/4), a decimal that reads as a day and a month (WBC 14.3, WBC 3.19) and four digits that read as one
# (WBC 1231) are withheld, since fractions, ranges, thresholds and room numbers are written the same way.
# The pair is read as a range or a value, and shown, beside a word that takes a range or a scale (Grade 3/4,
# Score 1-10, Age 12-18, Weeks 4-12), after a comparator (Hb < 13.5) or before a unit (2.5 mg, 3-4 days); a
# cancer antigen (CA 19-9, CA 15-3) is a lab name. Numbers glued to a letter are part of a word (L4-5, v1.2).
_HEADER_PAIR = re.compile(r"(?<![^\W_])(?<![.,/\-\u2013])(?P<a>\d{1,2})(?P<sep>\s?[/\-\u2013]\s?|\.)(?P<b>\d{1,2})"
                          r"(?P<dot>\.(?!\d))?(?![^\W_])(?![/\-\u2013.,]\d)")
_HEADER_FOUR_DIGITS = re.compile(r"(?<![^\W_])(?<![.,/\-\u2013])(?P<n>\d{4})(?![^\W_])(?![.,/\-\u2013]\d)")
_HEADER_COMPARATOR = re.compile(r"(?:[<>=~\u00b1\u2248\u2264\u2265]|>=|<=|=<|=>)\s*$")
_CANCER_ANTIGEN = re.compile(r"(?i)(?<![^\W_])ca[\s_-]?\d{2,3}(?:[-.]\d{1,2})?(?![^\W\d_])")
RANGE_WORDS = frozenset("""
grade grades score scores stage stages scale scales ecog kps nyha gleason likert rank ranks level levels class
classes tier tiers range ranges ratio ratios fraction age ages aged year years yr yrs month months mos week weeks
wk wks day days hour hours hr hrs minute minutes mins cycle cycles line lines phase phases dose doses step
steps item items question questions gestation gestational parity gravida apgar pain vas nrs percentile quartile
tertile quintile decile
""".split())


def _unit_after(s: str, end: int) -> bool:
    m = re.match(r"\s*(%|[^\W\d_]+(?:/[^\W\d_]+)?)", s[end:])
    return bool(m) and (m.group(1) == "%" or fold(m.group(1)) in UNITS or fold(m.group(1)) in TIME_UNITS
                        or fold(m.group(1)) in ("x", "times"))


def _header_number_pairs(s: str, reference_year: int) -> tuple[bool, bool]:
    """(refuse, withhold) for the numbers of a column name read as a month and a day (see above)."""
    s = _CANCER_ANTIGEN.sub(" ", s)
    ranged = bool(set(column_tokens(s)) & RANGE_WORDS)
    refuse = withhold = False
    for m in _HEADER_PAIR.finditer(s):
        a, b, sep = m.group("a"), m.group("b"), m.group("sep").strip()
        x, y = int(a), int(b)
        if not x or not y or not _month_day(x, y):
            continue
        shown = ranged or bool(_HEADER_COMPARATOR.search(s[:m.start()])) or _unit_after(s, m.end())
        zero = a.startswith("0") or b.startswith("0")
        if sep == ".":
            if m.group("dot") or a.startswith("0"):
                refuse = True
            elif not shown:
                withhold = True
        elif zero:
            refuse = True
        elif max(x, y) >= 13 and (sep == "/" or not shown):
            refuse = True
        elif not shown:
            withhold = True
    for m in _HEADER_FOUR_DIGITS.finditer(s):
        d = m.group("n")
        if 1880 <= int(d) <= reference_year + 10 or not (_month_day(int(d[:2]), int(d[2:])) and int(d[2:])):
            continue
        if d.startswith("0"):
            refuse = True
        elif not (ranged or _HEADER_COMPARATOR.search(s[:m.start()]) or _unit_after(s, m.end())):
            withhold = True
    return refuse, withhold


_DAY_WORD_NUMBER = re.compile(r"(?i)(?<![^\W\d_])(?:" + "|".join(sorted(DAY_PART_WORDS, key=len, reverse=True))
                              + r")\s*[#:.\-_]?\s*(?P<n>\d{1,2})(?!\d)")
_MONTH_WORD_NUMBER = re.compile(r"(?i)(?<![^\W\d_])(?:" + "|".join(sorted(MONTH_PART_WORDS, key=len, reverse=True))
                                + r")\s*[#:.\-_]?\s*(?P<n>\d{1,2})(?!\d)")


def _header_date_words(s: str, reference_year: int) -> tuple[bool, bool]:
    """(refuse, withhold) for a word for a month with a number and a year beside it (Month 3 2019, refused), or
    with a word for a day and a number (Day 14 Month 3, Tag 14 Monat 3, withheld: a study's month and day
    are written so too)."""
    months = [int(m.group("n")) for m in _MONTH_WORD_NUMBER.finditer(s) if 1 <= int(m.group("n")) <= 12]
    if not months:
        return False, False
    days = [int(m.group("n")) for m in _DAY_WORD_NUMBER.finditer(s) if 1 <= int(m.group("n")) <= 31]
    year = any(1880 <= int(y) <= reference_year + 10 for y in re.findall(r"(?<!\d)(\d{4})(?!\d)", s))
    return year, bool(days)


def header_date_withheld(header: str, reference_year: int) -> bool:
    """A column name holding a month or a day alone (3月, 3월, tháng 3, 14日, a month name of another language as
    a word), two numbers that may be a month and a day (3-4, WBC 14.3, WBC 1231) or a word for a day and one for
    a month with numbers (Day 14 Month 3): withheld, never printed or copied (round 8)."""
    h = HEADER_CODES.sub(" ", unicodedata.normalize("NFKC", str(header)))
    if any(hit.elements == 1 for hit in find_dates(h, reference_year, parts=True)):
        return True
    s = _header_ascii(h)
    return _header_number_pairs(s, reference_year)[1] or _header_date_words(s, reference_year)[1]


_HEADER_MONTH_WORD = re.compile(r"(?<![^\W\d_])(?:" + _HEADER_MONTHS + r")(?![^\W\d_])", re.I)


def header_compact_month_code(header: str) -> bool:
    """A month abbreviation joined to one or two digits (OCT4, Oct4, SEPT9, DEC1, Mar19), a gene symbol or
    a date, or a month name as a word of its own ("Weight March", "June Visit"), which in a wide export
    names the month of each person's measurement: withheld, never printed or copied (round 5)."""
    s = _header_ascii(HEADER_CODES.sub(" ", unicodedata.normalize("NFKC", str(header))))
    return any(_compact_month_code(m, True) for m in _HEADER_MONTH_THEN_NUMBER.finditer(s)) \
        or any(_compact_month_code(m, False) for m in _HEADER_NUMBER_THEN_MONTH.finditer(s)) \
        or bool(_HEADER_MONTH_WORD.search(s))


# A first-row cell of letters and digits with a leading zero ("S001", "sub01", "PT-0042"), or of
# letters the column words do not know and three or more digits ("ABC123"), is shaped like a code
# of a person or a sample: in a file with no header row it is a value. It is withheld, not refused,
# because a wide table can name its columns this way ("V01", "Q012").
FIRST_ROW_CODE = re.compile(r"([A-Za-z]{1,4})[-_]?(\d{2,})")


def header_code_shaped(header: str) -> bool:
    if header_compact_month_code(header):
        return True
    h = HEADER_CODES.sub("", unicodedata.normalize("NFKC", str(header)).strip())
    m = FIRST_ROW_CODE.fullmatch(h)
    if not m:
        return False
    letters, digits = m.group(1).lower(), m.group(2)
    return digits.startswith("0") or (len(digits) >= 3 and not _column_word(letters))


# Round 7: a word spelled out one letter at a time ("Z-o-r-b-l-e-t-o-n", "S m i t h", "J.o.n.e.s") reads as
# single letters, each a column word, so a name written so passed as a column name. Four or more letters
# each separated from the next by one character that is not a letter or a digit make a cell a value.
SPELLED_OUT = re.compile(r"(?<![^\W_])[^\W\d_](?:[\W_][^\W\d_]){3,}(?![^\W_])")


def header_looks_like_value(header: str, scrubber: Scrubber) -> bool:
    h = str(header).strip()
    return bool(h) and (is_number(h) or len(h) > 80 or bool(header_identifier_kinds(h, scrubber))
                        or bool(header_number_kinds(h, scrubber.reference_year)) or header_name_like(h)
                        or bool(SPELLED_OUT.search(h)))


# Round 8: joiners and direction marks that a script without capital letters needs (ZWNJ in Persian spelling,
# ZWJ in Indic scripts and emoji, a right-to-left mark ending an Arabic or Hebrew Excel cell).
SCRIPT_JOINERS = frozenset("\u200c\u200d\u200e\u200f\u061c")


def _cased_letters(header: str) -> bool:
    return any(c.isalpha() and (c.isupper() or c.islower()) for c in str(header))


def _invisible_character(header: str) -> bool:
    """A NUL, another control character or a format character (Unicode Cc or Cf: a zero-width space or
    joiner, a direction mark, a soft hyphen, a byte order mark) in a header cell, which can hide a name or a
    number from the column-name checks (round 7). A tab, a line feed and a carriage return read as spaces.
    Round 8: a zero-width joiner or non-joiner and a direction mark are part of the spelling in a header with no
    letter of a script with capitals (Persian, Arabic, Hebrew, Indic scripts, emoji); the checks read such a
    header without them (header_for_checks)."""
    h = str(header)
    allowed = SCRIPT_JOINERS if not _cased_letters(h) else frozenset()
    return any(unicodedata.category(c) in ("Cc", "Cf") and c not in "\t\n\r" and c not in allowed for c in h)


def header_for_checks(header: str) -> str:
    """The header as the column-name checks read it: without the joiners and marks _invisible_character allows."""
    h = str(header)
    return h if _cased_letters(h) else "".join(c for c in h if c not in SCRIPT_JOINERS)


# Words column names are made of. A column name of two or more capitalised words none of which is
# one of these, or a category, medical or anatomical word, has the shape of a person's or a place's
# name ("Okafor Jane", "Walnut Grove"), as a first row of data read as the header row does.
GENERIC_HEADER_WORDS = frozenset("""
symbol purity allele change exon copy margin invasion hormone survival progression event events censor
censored modified version instance redcap survey timestamp complete unnamed chief complaint course
disposition source marital preferred language allergies allergy vital cause pack alcohol use collection
assay platform tumor size gene consent signed study arm cohort site name entry data form repeat flag
overall free nodal lymphovascular perineural pathologic response receptor variant baseline value
investigator coordinator status follow drug sample type specimen method field variable column item
question answer comment comments note notes remark remarks description label group category class
result results test tests panel order date time start end stop first last next previous prior initial
final total new old current former primary secondary main other misc miscellaneous extra additional
derived computed calculated adjusted raw imputed estimated predicted observed expected actual target
reported self measured clinical medical record history family social demographic demographics
outcome outcomes exposure treatment therapy regimen line cycle phase visit week month year
day hour minute quarter period wave round session interval duration frequency count number amount
quantity unit units mean median average min max minimum maximum range std sd se ci lower upper
low high mid level grade stage score index ratio rate percent change delta diff difference
smoker smoking ever never alive dead living deceased survival censor
""".split())


def header_name_like(header: str) -> bool:
    """True for a column name of two to six capitalised words, at least two of them neither a
    word column names are made of nor an abbreviation ("ED", "Pat."), and no word the name rules
    read: the shape of a person's or a place's name ("Okafor Jane", "OKAFOR JANE", "Walnut
    Grove"), not of "Waist Circumference" or "Alter ED"."""
    s = str(header).strip()
    words = [w for w in re.split(r"[\s,;/]+", s) if w]
    if re.search(r"\d", s) or not 2 <= len(words) <= 6 or name_rule(s) is not None:
        return False
    core = 0
    for w in words:
        letters = re.sub(r"['\u2019.-]", "", w)
        if not letters.isalpha():
            return False
        if len(letters) == 1 or w.endswith(".") or (letters.isupper() and len(letters) <= 3):
            continue  # an initial or an abbreviation
        if not letters[0].isupper():
            return False
        low = "".join(column_tokens(letters))
        if low in NAME_PARTICLES or low in NAME_SUFFIXES:
            continue
        if _column_word(low) or _vocabulary_word(low):
            return False
        core += 1
    return core >= 2


_HEADER_WORDS: set[str] = set()


def HEADER_WORDS() -> set[str]:  # noqa: N802 - built once, from tables defined further down
    if not _HEADER_WORDS:
        _HEADER_WORDS.update(
            GENERIC_HEADER_WORDS | MEASUREMENT_WORDS | NUMBER_ID_WORDS | PERSON_ROLE_WORDS | HEAD_ROLE_WORDS
            | PLACE_WORDS | QUALIFIER_WORDS | NAME_TRAILING | SELF_WORDS | INTERVAL_WORDS | DATE_TIME_CONTEXT
            | RELATIVE_NAME_WORDS | STAGE_HEADER_WORDS | ICD_HEADER_WORDS | ATC_HEADER_WORDS
            | VARIANT_HEADER_WORDS | BLOOD_HEADER_WORDS | RACE_HEADER_WORDS | UNIT_HEADER_WORDS
            | AGE_UNIT_WORDS | BIRTH_NOT_A_DATE | BIRTH_WORDS_OTHER_LANGUAGES | BIRTH_DATE_TOKENS
            | BIRTH_DATE_WORDS | BIRTH_YEAR_WORDS | YEAR_WORDS_OTHER_LANGUAGES | frozenset(DATE_WORDS)
            | frozenset(NOT_A_PERSON_NAME) | frozenset(NOT_A_PERSON_ID))
    return _HEADER_WORDS


# Column names fail closed too (round 3). A first row of data read as the header row puts a
# patient's name where a column name belongs, and a single surname, a titled name ("Dr. Lee") or a
# name in a script without capital letters has no shape that tells it from a column word. So a
# header cell is shown, reported and copied to the output only when every word in it is a word
# column names are made of: the word lists of the rules above, the category, medical and
# anatomical words, the words below, single letters, numbers and codes of letters and digits
# ("TP53", "Col1"). Any other cell is withheld and the output names it column_N, until the person
# confirms it (--keep-name, --keep-all-names) or says the file has no header row (--no-header).
# A column name made only of words that are also common surnames or given names ("Long", "Ward",
# "White", "Rose Hall") is withheld too; beside another column word they count ("Reference Low").
# "Case", "Day", "Person", "Weeks" and "Mass" are left out: as a column name alone they are common.
# Measured on 1,161 common US surnames and given names, those four are the only ones shown alone.
SURNAME_WORDS = (NAME_LIKE_CATEGORY_WORDS - {"case", "mass", "central", "fall"}) | frozenset("""
cook french english german polish carpenter farmer driver clerk fisher hunter mason porter steward
foreman baker miller taylor turner parker walker cooper marshal marshall bishop knight dean chase hope
joy grace faith rose lily ivy hall hill wood woods green gray grey brown young king long price bell
ward page lane may mark bond rich love ball bush cross frank gold lord moss nash ng min ma mo
pope post root sharp short small snow strong swift wise rice mills wells banks fox hart hunt grant
stone holmes black white major minor chef artist writer manager teacher engineer cashier mechanic
plumber electrician soldier veteran police braden morse pugh wells iris victoria georgia jordan chad
florence austin dallas lincoln washington madison chelsea sydney paris london branch burns chambers
christian colon fields flowers foster lang le mays molina powers shields singleton summers wall walls
waters winters
lo do du fu da di de la das hay kin nam son man max pat tod sin tin spring al ed val kit best vi
bill charity
""".split())
COLUMN_WORDS_EXTRA = frozenset("""
of to from at in on by with for the a an and or per vs versus since until after before during within
without into over under than as is was if any all not non via plus between among each every whether
id ids no nr num nbr pt pts pat pats col cols var vars row rows field fields item items obs record
records entry entries column columns unnamed index idx key keys ref code codes flag flags yn tf
variable variables label labels value values val vals text desc description comment comments note notes
remark remarks memo info information detail details data dataset source sources origin type types
kind kinds class classes category categories group groups status statuses state states level levels
tier tiers grade grades stage stages score scores scale rank ranks order sequence seq version ver
date dates dt dtm datetime time times timestamp ts year years yr yrs yyyy yy mo mos month months wk
week weeks day days hr hrs hour hours min mins minute minutes sec secs second seconds
start started end ended stop stopped begin onset offset first last next prior previous current
initial final baseline followup follow up fu visit visits encounter encounters episode episodes admit
admission admissions discharge discharged readmission readmit readmitted transfer arrival departure
arrive depart triage disposition dispo outcome outcomes event events endpoint endpoints censor censored
death died dead deceased alive survival surv os pfs dfs efs rfs ttp ttf mortality mort recurrence
relapse progression response remission
patient patients subject subjects participant participants case cases control controls study studies
trial trials arm arms cohort cohorts site sites center centre centers centres clinic clinics hospital
hospitals ward wards unit units department dept service services team teams provider providers
physician physicians surgeon surgeons nurse nurses doctor doctors pcp attending specialist referral
referring referred ordering ordered order orders
diagnosis diagnoses dx ddx diag icd icd9 icd10 cm pcs cpt hcpcs snomed loinc rxnorm ndc atc mesh
umls omop concept concepts vocab vocabulary drg ms apr mdc hcc ccs elixhauser charlson cci
comorbidity comorbidities condition conditions problem problems disease diseases disorder disorders
symptom symptoms sign signs finding findings complaint complaints chief history hx pmh psh fhx shx
medication medications med meds drug drugs rx prescription prescriptions dose doses dosage dosing
route frequency freq strength form formulation brand generic ingredient ingredients regimen regimens
therapy therapies treatment treatments tx intervention interventions procedure procedures proc surgery
surgeries operation operations anesthesia anaesthesia asa implant device devices transfusion
lab labs laboratory test tests result results panel panels assay assays specimen specimens sample
samples biopsy culture cultures organism organisms isolate antibiotic antibiotics susceptibility mic
pathology histology histologic cytology grade tumor tumour tumors size margin margins node nodes
nodal lymph metastasis metastases mets laterality side location sites primary secondary
gene genes symbol symbols transcript transcripts protein proteins variant variants mutation mutations
allele alleles genotype genotypes phenotype phenotypes exon intron chromosome chr chrom pos position
ref alt hgvs cdna rsid snp snps cnv sv vaf af maf tmb msi mmr pdl1 tps cps ki67 her2 er pr ar egfr
kras nras braf alk ros1 ret met ntrk pik3ca pten brca brca1 brca2 tp53 apc atm idh idh1 idh2 mgmt
expression expr tpm fpkm rpkm cpm counts reads log log2 fc logfc pval padj fdr qval
sex gender race ethnicity ethnic ancestry age ages aged born birth dob language lang interpreter
needed marital education educ income employment employed occupation job insurance insured payer
payor plan coverage housing homeless residence urban rural smoker smoking smoke tobacco alcohol
etoh drinking drinks drug substance use uses user bmi weight wt height ht bsa waist hip
temperature temp pulse hr heart rate resp rr bp sbp dbp map spo2 sao2 o2 fio2 gcs pain avpu
glucose lactate wbc rbc hgb hb hct plt mcv mch mchc rdw mpv anc alc na k cl hco3 co2 bun cr creat
scr egfr gfr ca mg phos alk ast alt ggt ldh tbili dbili bili alb tp inr pt ptt aptt fib fibrinogen
ddimer dimer troponin trop tni tnt bnp ntprobnp crp hscrp esr pct procalcitonin ferritin iron tibc
tsat b12 folate tsh t3 t4 ft3 ft4 free a1c hba1c lipid ldl hdl tg chol cholesterol triglycerides
vitamin vit d urine urinalysis ua upcr uacr protein albumin microalbumin ketones serum plasma blood
csf stool sputum swab pcr antigen antibody ab ag igg igm iga ige titer titre viral load copies hiv
hbv hcv covid covid19 sars cov cov2 influenza flu rsv vaccine vaccines vaccination vaccinated dose1 dose2
booster
ecog kps nyha asa apache sofa qsofa news mews meld child nihss mrs gose gos phq gad audit mmse
moca cdr adl iadl barthel braden morse frailty cfs
icu nicu picu micu sicu ccu ed er or pacu ip op inpatient outpatient ambulatory emergency elective
urgent los ventilator ventilation vent mv niv hfnc ecmo crrt dialysis hd pd rrt intubation intubated
pressor pressors vasopressor vasopressors
adverse ae aes sae saes serious severity severe related relatedness relationship action taken ctcae
toxicity toxicities dlt
reference low high normal range abnormal critical units uom unit
total sum mean median avg average sd std se sem iqr min max minimum maximum range lower upper ci
pct percent percentage ratio rate rates count counts number n freq proportion prob probability
predicted observed expected estimate estimated actual raw adjusted imputed derived computed calculated
change delta diff difference increase decrease baseline
consent consented signed eligible eligibility enrolled enrollment enrolment randomized
randomised randomization randomisation allocation allocated withdrawn withdrawal screening screened
screen fail failure failed complete completed completion incomplete missing partial
redcap event name instrument repeat instance survey timestamp form forms dag
address city town zip zipcode postal postcode county state country region phone tel email fax mrn
ssn
geschlecht sexo sexe sesso genere geslacht kon plec diagnose diagnostico diagnosi diagnostic
diagnostik fecha datum data dato fec peso talla altura estatura gewicht groesse grosse poids taille
gewicht lengte vikt langd waga wzrost medicamento medicamentos farmaco farmaci medicament medicaments
medikament medikamente tratamiento traitement behandlung trattamento resultado resultados resultat
resultats ergebnis ergebnisse risultato risultati valor valores valeur valeurs wert werte valore
valori visita visitas besuch consulta ingreso ingresos alta egreso aufnahme entlassung ricovero
dimissione numero nummer numer codigo codice code paciente pacientes patiente patient patienten
paziente pazienti historia clinica numero expediente
de del della dei des du la le les el los las lo il e y und die das dem von vom zur zum bei mit im am het
een voor en og och af pa po na w z ze do da di dal al au aux sur par pour con sin tra fra
seen impression updated created modified when where who what which how reading reply answer epoch
snapshot reporting period ym yyyymm point time timepoint tp stay religion denomination injury marker
biomarker census doc docs admin sign off signoff signature cat htn dm ckd cad copd chf afib hld osa
pg ng ug mcg iu meq mmol umol nmol pmol ml dl l g kg lb lbs oz cm mm in ft mmhg bpm kpa pa mosm mosmol
pressure blood propensity iptw ipw zscore z tscore weight weights wavelength nm hometown suburb
locality district pob company employer workplace school college university fname lname mname
username user login screen handle vin plate serial udi imei device license licence certificate cert
dea npi passport fax facsimile telephone pager mobile cell email ssn itin nhs nino sin tin mrn empi
accession barcode fingerprint voiceprint biometric biometrics retinal palm photo photos photograph
picture headshot portrait selfie avatar url uri website homepage web ip ipv4 ipv6 mac beneficiary
subscriber policy member insurer medicare medicaid hicn mbi account acct iban card routing kin nok
emergency spouse guardian caregiver contact relative household landlord roommate tenant lives living
twitter instagram facebook tiktok snapchat linkedin wechat whatsapp telegram skype reddit youtube
telefon telefono telefone telefoon telefonnummer celular movil cellulare puhelin plz cep postleitzahl
codigo postal codice postale postnummer postinumero lat lon lng long lt ln coord coords latlong latlon
geo gps easting northing utm breitengrad langengrad latitud longitud latitudine longitudine
hosp patid ptid subjid studyid recordid patno ptno patientennummer persoonsnummer henkilotunnus
fodselsnummer rodne cislo matricule cartella phn ohip dni cpf rrn nip sus nhc nhi nir insee cip
kit box slot tube rack well plate aliquot barcode batch lot
eta anni dob byear yob vehicle badge street network template origin resides residing reside lives
living stichtag vid ved diagnos diagnoze inclusion inklusion erstdiagnose pri tod nac bth sinh agent
assigned sent referred ordered signed reviewed entered recorded collected verified approved performed
completed reported created updated modified scheduled cancelled canceled attended accompanied
mutational questionnaire questionnaires subtype subtypes modality modalities organ organs speciality acuity
transport technique approach resistance protocol blinding reason reasons intolerance reaction reactions
industry degree citizenship literacy mobility cognition diet nutrition exercise activity activities
prophylaxis surveillance circumstance circumstances autopsy conclusion goal goals priority bodypart anatomy
storage shelf consequence zygosity pathogenicity clinvar cosmic gnomad quality comorbid sequela sequelae
best haplotype karyotype hpo term terms chemotherapy chemo adherence compliance seriousness prosthesis anatomic
income bracket urbanicity rurality sx pregnancy pregnant menopause menopausal split fold feature features fy
femoral humeral radial ulnar fibular tibial metatarsal metacarpal pancreatic caudate epididymal
ii iii vi vii viii pugh gravida para feeding radiotherapy radiation brachytherapy immunotherapy
""".split())
# Column words in scripts the tokens above do not read, matched as phrases.
OTHER_SCRIPT_COLUMN_WORDS = (
    AGE_WORDS_CJK + tuple(AGE_WORDS_OTHER_SCRIPTS) + BIRTH_DATE_PHRASES + BIRTH_YEAR_PHRASES
    + BIRTH_PLACE_PHRASES + SCRIPT_NAME_ANYWHERE + tuple(SCRIPT_NAME_WORDS) + SCRIPT_PATIENT_WORDS
    + RACE_HEADER_SCRIPTS + tuple("""
性别 性別 诊断 診断 診斷 日期 日付 药物 藥物 药品 藥品 薬剤 薬 結果 结果 检查 檢查 検査 编号 編號 番号 号 病历 病歷
住院 门诊 門診 患者 病人 体重 體重 身高 身長 血压 血壓 血圧 血糖 年 月 日 时间 時間 类型 類型 状态 狀態 状態 国家 國家
省 地区 備考 备注 備註 説明 说明 治疗 治療 手术 手術 科室 医院 醫院 病院 民族 吸烟 喫煙 饮酒 飲酒 分期 分级 分級
성별 진단 날짜 일자 결과 약물 약품 번호 등록번호 등록 환자 체중 키 신장 혈압 혈당 월 일 년 연도 시간 유형 상태 국가
지역 비고 치료 수술 병원 흡연 음주 병기
пол диагноз дата результат номер карта карты истории болезни пациент пациента вес рост давление месяц
день год время тип статус страна регион примечание лечение операция больница курение
الجنس التشخيص التاريخ النتيجة رقم الملف المريض الوزن الطول الشهر اليوم السنة الوقت النوع الحالة الدولة
מין אבחנה תאריך תוצאה מספר תיק חולה משקל גובה חודש יום שנה זמן סוג מצב מדינה
लिंग निदान तारीख परिणाम संख्या रोगी वजन लंबाई महीना दिन वर्ष समय प्रकार स्थिति देश
เพศ การวินิจฉัย วันที่ ผล หมายเลข ผู้ป่วย น้ำหนัก ส่วนสูง เดือน วัน ปี เวลา ประเภท สถานะ ประเทศ
φύλο διάγνωση ημερομηνία αποτέλεσμα αριθμός ασθενής βάρος ύψος μήνας ημέρα έτος 月份 담당
""".split()) + COORDINATE_WORDS_OTHER_SCRIPTS)


def _column_vocab() -> frozenset:
    if not _COLUMN_VOCAB:
        _COLUMN_VOCAB.update(
            set(HEADER_WORDS()) | COLUMN_WORDS_EXTRA | CATEGORY_WORDS | AGE_UNIT_WORDS | YEAR_WORDS_OTHER_LANGUAGES
            | AGE_WORDS_OTHER_LANGUAGES | DAY_PART_WORDS | MONTH_PART_WORDS | WEEKDAY_WORDS | NOT_AGENT_NOUNS
            | frozenset(NAME_WORDS_OTHER_LANGUAGES) | frozenset(CITY_WORDS_OTHER_LANGUAGES) | TIME_WORDS
            | HEAD_ID_WORDS | DATE_PART_CONTEXT | SOCIAL_NETWORKS | COORDINATE_ABBREVIATIONS
            | COORDINATE_COMPANIONS | PAYER_WORDS | NUMBER_WORDS | frozenset(NAME_HINT_HEADERS)
            | PERSON_HEADERS | RELATIVE_HEADERS | PERSON_HEAD_WORDS | frozenset(CLINICIAN_WORDS)
            | frozenset(RELATIVE_WORDS) | frozenset(BIRTH_PLACE_WORDS))
    return frozenset(_COLUMN_VOCAB)


_COLUMN_VOCAB: set[str] = set()


def _column_word(t: str) -> bool:
    """One lower-case word of a column name that column names are made of (see above)."""
    vocab = _column_vocab()
    if not t or t.isdigit() or len(t) == 1 or t in vocab or (len(t) > 3 and t.endswith("s") and t[:-1] in vocab):
        return True
    if _is_age_token(t) or _age_word_token(t) or _clinical_word(t):
        return True
    # A role by its ending (phlebotomist, sonographer, dietician, attendee), but not a Swedish
    # surname in -qvist.
    if _role_word(t, PERSON_ROLE_WORDS) and not t.endswith(("qvist", "quist", "kvist")):
        return True
    if re.search(r"\d", t) and re.search(r"[a-z]", t):
        # A code of letters and digits ("tp53", "col1", "a1c", "ensg00000141510", "covid19").
        return all(len(run) <= 5 or run in vocab for run in re.findall(r"[a-z]+", t))
    return False


def _latin_or_mark(c: str) -> bool:
    return not c.isalpha() or c.isascii() or unicodedata.name(c, "").startswith("LATIN")


def header_shown(header: str) -> bool:
    """True for a column name every word of which is a column word (see above), with at least one
    word that is not also a common surname or given name ("Reference Low", not "Low"): the plan,
    the report and the output may carry it. A surname, a given name, a titled name, a name in a
    script without capital letters or any word the lists do not know makes it False."""
    return _header_words(header, surnames=True)


def header_known(header: str) -> bool:
    """True for a column name every word of which is a column word, whether or not every word is
    also a surname ("Ward", "Long"): what --keep asks of a column name (keep_refusal)."""
    return _header_words(header, surnames=False)


def _header_words(header: str, surnames: bool) -> bool:
    h = str(header).strip()
    if not h:
        return True
    raw = unicodedata.normalize("NFKC", h).casefold()
    other_script = False
    for phrase in sorted(OTHER_SCRIPT_COLUMN_WORDS, key=len, reverse=True):
        if phrase.casefold() in raw:
            other_script = True
            raw = raw.replace(phrase.casefold(), " ")
    stripped = "".join(c for c in unicodedata.normalize("NFKD", raw) if not unicodedata.combining(c))
    stripped = stripped.replace("\u00df", "ss").translate(LETTERS_WITHOUT_DECOMPOSITION)
    if not all(_latin_or_mark(c) for c in stripped):
        return False
    s = "".join(c for c in unicodedata.normalize("NFKD", stripped) if not unicodedata.combining(c))
    s = re.sub(r"([a-z])-(?=\d)", r"\1", s)  # il-6, phq-9, covid-19
    words = []
    for word in re.findall(r"[a-z0-9]+", s):
        if _column_word(word):
            words.append(word)
            continue
        # The original capitals split a word written in camel case ("DayOfMonth", "SpO2").
        return _camel_header_shown(h, surnames)
    letters = [w for w in words if w.isalpha() and len(w) > 1]
    if surnames and _surname_beside_person(words):
        return False
    return not surnames or other_script or not letters or any(not _surname_word(w) for w in letters)


def _surname_word(w: str) -> bool:
    return w in SURNAME_WORDS or (len(w) > 3 and w.endswith("s") and w[:-1] in SURNAME_WORDS)


# Round 8: a word for a person beside a word that can be a surname ("Patient White", "Dr Ward", "Mother Long",
# "Patient Bill White") was shown, because one word was not a surname. A column name made of words for a person
# and words that can be surnames, and one in which two words that can be names stand side by side ("Weight Bill
# White"), are withheld. Words of measurements and ordinary column words do not count as names side by side
# ("Min Max"), nor do the points of the compass.
PERSON_TITLE_WORDS = frozenset("mr mrs ms mx miss mister prof professor sir dame dr drs doc rev".split())
PERSON_BESIDE_SURNAME = (SELF_WORDS | frozenset(PERSON_HEADERS) | frozenset(RELATIVE_WORDS) | frozenset(RELATIVE_HEADERS)
                         | CLINICAL_STAFF_WORDS | frozenset(CLINICIAN_WORDS) | PERSON_TITLE_WORDS)
COMPASS_WORDS = frozenset("north south east west northeast northwest southeast southwest central".split())


def _surname_beside_person(words: list[str]) -> bool:
    letters = [w for w in words if w.isalpha() and len(w) > 1]
    people = [w for w in letters if w in PERSON_BESIDE_SURNAME]
    rest = [w for w in letters if w not in PERSON_BESIDE_SURNAME]
    if people and rest and all(_surname_word(w) for w in rest):
        return True

    def name_word(w: str) -> bool:
        return (w.isalpha() and _surname_word(w) and w not in GENERIC_HEADER_WORDS and w not in MEASUREMENT_WORDS
                and w not in COMPASS_WORDS)
    return any(name_word(a) and name_word(b) for a, b in zip(words, words[1:]))


def _camel_header_shown(header: str, surnames: bool = True) -> bool:
    s = "".join(c for c in unicodedata.normalize("NFKD", header) if not unicodedata.combining(c))
    s = s.replace("\u00df", "ss").translate(LETTERS_WITHOUT_DECOMPOSITION)
    s = re.sub(r"([A-Za-z])-(?=\d)", r"\1", s)
    words = []
    for word in re.findall(r"[A-Za-z0-9]+", s):
        parts = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", word)
        parts = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", parts)
        for p in (x.lower() for x in parts.split("_") if x):
            if not _column_word(p):
                return False
            words.append(p)
    letters = [w for w in words if w.isalpha() and len(w) > 1]
    if surnames and _surname_beside_person(words):
        return False
    return not surnames or not letters or any(not _surname_word(w) for w in letters)


# Public accessions a wide genomic table names its columns by (round 5). Their digits are refused like a
# record number's, because C00031 or P04637 can also be a patient's code; when the person confirms one by
# its position with --keep-name #N, a cell that is exactly one of these shapes is shown.
PUBLIC_ACCESSION = re.compile(
    r"GS[ME]\d{3,8}|GPL\d{2,6}|GDS\d{3,6}|[SED]R[RXSPA]\d{6,9}|PRJ(?:NA|EB|DB)\d{3,9}|SAM(?:N|EA|D)\d{6,10}"
    r"|phs\d{6}(?:\.v\d{1,3}\.p\d{1,3})?|NCT\d{8}|TCGA-[A-Z0-9]{2}-[A-Z0-9]{4}(?:-\d{2}[A-Z]?(?:-\d{2}[A-Z])?"
    r"(?:-[A-Z0-9]{4}-\d{2})?)?|ILMN_\d{5,8}|cg\d{8}|ch\.\d{1,2}\.\d{1,9}[FR]?|\d{6,8}_(?:[sxa]_)?at|LOC\d{3,9}"
    r"|CHEMBL\d{1,9}|CID\d{1,10}|DB\d{5}|HMDB\d{5,7}|[CDK]\d{5}|(?:hsa|mmu|rno)\d{5}|GO:\d{7}|HP:\d{7}"
    r"|MONDO:\d{7}|DOID:\d{1,7}|R-[A-Z]{3}-\d{4,8}|[OPQ]\d[A-Z0-9]{3}\d|[A-NR-Z]\d(?:[A-Z][A-Z0-9]{2}\d){1,2}"
    r"|(?i:chr)(?:[1-9]|1\d|2[0-2]|[XY]|MT?)[:_.-]\d{1,9}(?:[-_]\d{1,9})?")


def check_header_row(headers: list[str], scrubber: Scrubber, confirmed: set[int] = frozenset(),
                     by_position: set[int] = frozenset()) -> set[int]:
    """The positions of header cells the plan and the report withhold and the output renames
    column_N: cells that look like a value or a name, and cells with a word that is not a column
    word (header_shown). Positions in `confirmed` (--keep-name, --keep-all-names) are shown.
    Refuses a header row that holds an identifier pattern in any cell (an email, a phone or ID
    number, a date: a patient's record read as the header row, or column names that carry
    identifiers), or in which a third of the cells look like values or names and the person has
    not confirmed them. The message names counts only.

    Round 7: a header cell holding a NUL, a control character or a format character is refused by its
    position, whatever the person confirms: it is a sign of a file in another encoding or of text written
    to slip past the checks."""
    invisible = [i for i, h in enumerate(headers, start=1) if _invisible_character(h)]
    if invisible:
        where = ", ".join(f"#{i}" for i in invisible[:10]) + (", ..." if len(invisible) > 10 else "")
        raise UsageError(
            f"{len(invisible)} of {len(headers)} header cells ({where}) hold a NUL, a control character or an "
            "invisible formatting character (a zero-width space or joiner, a direction mark, a soft hyphen), "
            "which can hide a name or a number from the column-name check. If the file was saved as UTF-16 "
            "or another encoding, save it again as 'CSV UTF-8' (in Excel: File, Save As, CSV UTF-8) or rerun "
            "with --encoding; otherwise ask the person to retype those column names, or rerun with --no-header, "
            "which reads the first row as data and names the columns column_1, column_2, ... No output was written.")
    headers = [header_for_checks(h) for h in headers]
    patterned = [i for i, h in enumerate(headers, start=1)
                 if (header_identifier_kinds(h, scrubber) or header_number_kinds(h, scrubber.reference_year))
                 and not (i in by_position and PUBLIC_ACCESSION.fullmatch(str(h).strip()))]
    if patterned:
        raise UsageError(
            f"the first row looks like data or carries identifiers: {len(patterned)} of {len(headers)} "
            "header cells are shaped like an identifier (an email or web address, a phone, ID or record "
            "number, a date, a number of five or more digits, a decimal of four or more places, a year 90 "
            "or more years ago, ...). If the file has no header row, rerun with --no-header; if the "
            "column names themselves carry identifiers (a per-patient table whose columns are named after "
            "record numbers), ask the person to rename those columns. A wide matrix whose columns are named "
            "with a prefix and digits (methylation probes, variables V1 to V2000, samples) is refused "
            "the same way, because such names have the shape of a record or a patient's code: a public "
            "accession (a methylation probe, a GEO or SRA sample, a gene identifier) is shown once the person "
            "confirms those columns by position, also as a range (--keep-name '#2-#501'); for any other name "
            "ask the person "
            "to rename them with a word and a short number (probe_1, var_1) and keep a lookup of the original "
            "names outside the data. Then run again.")
    looks = {i for i, h in enumerate(headers, start=1) if header_looks_like_value(h, scrubber)}
    if len(looks - set(confirmed)) >= max(2, (len(headers) + 2) // 3):
        raise UsageError(
            f"the first row looks like data rather than column names ({len(looks)} of "
            f"{len(headers)} header cells look like values or names). If the file has no header row, "
            "rerun with --no-header; if the person confirms that the first row holds column names, "
            "rerun with --keep-all-names. A wide matrix whose columns are named with a prefix and digits "
            "(probes, variables V1 to V2000) is read this way too; the person can confirm its names with "
            "--keep-all-names or rename them with a word and a short number (probe_1, var_1).")
    unknown = {i for i, h in enumerate(headers, start=1) if not header_shown(h) or header_code_shaped(h)
               or header_date_withheld(h, scrubber.reference_year)}
    return (looks | unknown) - set(confirmed)


def output_headers(headers: list[str], withheld: set[int]) -> dict[str, str]:
    """The output name of each column: column_N for a withheld one, its own name otherwise."""
    used = {str(h) for i, h in enumerate(headers, start=1) if i not in withheld}
    out = {}
    for i, h in enumerate(headers, start=1):
        if i in withheld:
            name = f"column_{i}"
            while name in used:
                name += "_"
            used.add(name)
            out[h] = name
        else:
            out[h] = h
    return out


def decide_columns(data: list[dict], headers: list[str], locale: dict, scrubber: Scrubber,
                   keep: set[str], redact: set[str], reference_year: int) -> list[dict]:
    """One decision per column. No cell value goes into a decision."""
    decisions = []
    for i, col in enumerate(headers, start=1):
        values = [str(row.get(col, "") or "") for row in data]
        nonempty = [v for v in values if v.strip()]
        ctx = ColumnContext(col)
        d = {"index": i, "column": col, "kept_on_request": False, "forced_redaction": False,
             "verified": False}
        # Free text is never kept: a name inside a sentence has no pattern to find. A long
        # value made only of category words ("American Indian or Alaska Native") or verified
        # as a whole ("Saint Vincent and the Grenadines" under a country column) is not text.
        prose = [v for v in nonempty if not _is_category_value(v) and not value_verified(v, ctx)]
        d["free_text"] = bool(prose) and (upstream.looks_like_free_text(prose)
                                          or any(caseless_prose(v) for v in prose))
        rule = (column_name_rule(col, nonempty, scrubber) or locale_name_rule(col, locale)
                or person_name_rule(col, nonempty) or record_number_name_rule(col, nonempty))
        # A state or country column is allowed by Safe Harbor, but its values are checked like
        # any other column: only state and country names are vouched for (verify_column).
        if rule and rule[2] == "allowed_geography":
            rule = None
        qualified = not rule and bool(name_rule(col)) and not ctx.geography
        if rule:
            finding, action, phi = rule
            d.update(kind="identifier", finding=f"column name: {finding}", action=action, phi_type=phi)
        elif not nonempty:
            d.update(kind="none", finding="empty column", action="keep", phi_type=None, verified=True)
        else:
            scrubbed = [scrub_cell(scrubber, v, ctx) for v in nonempty]
            hits = [found for _, found in scrubbed if found]
            # A cell that is nothing but one identifier (a date, an email, a code), counted
            # against the cells that are not missing-value words.
            whole = [found[0] for out, found in scrubbed
                     if found and (PLACEHOLDER.fullmatch(out.strip())
                                   or re.fullmatch(r"\d{4}", out.strip())
                                   or out.strip() == "90+ years")]
            present = [v for v in nonempty if fold(v) not in MISSING_PHRASES]
            check = verify_column(col, nonempty, reference_year, ctx)
            numbers = number_rule(col, present, reference_year)
            if hits and numbers and numbers[1] == "age" and all(k == "age" for found in hits for k in found):
                # Ages written with a unit ("95 y", "102 yo"), some over 89: grouped as ages.
                d.update(kind="unverified", finding=f"values: {numbers[0]}", action="age", phi_type="age")
            elif whole and len(whole) / max(1, len(present)) > 0.5:
                phi = max(set(whole), key=whole.count)
                action = {"date": "year", "code": "pseudonym_id", "age": "age"}.get(phi, "redact")
                if phi == "zip" and all(re.fullmatch(r"\s*\d{5}(?:-\d{4})?\s*", v) for v in present):
                    action = "zip3"
                d.update(kind="identifier_values",
                         finding=f"values: {len(whole)} of {len(present)} cells are {phi.replace('_', ' ')} identifiers",
                         action=action, phi_type=phi)
            elif hits:
                d.update(kind="uncertain",
                         finding=f"values: identifier patterns in {len(hits)} of {len(nonempty)} cells",
                         action="redact", phi_type="mixed")
            elif d["free_text"]:
                d.update(kind="uncertain", finding="free text (names inside text cannot be found)",
                         action="redact", phi_type="free_text")
            elif part := date_part_rule(col, present):
                d.update(kind="unverified", finding=f"values: {part[0]}", action="redact", phi_type="date")
            elif coord := coordinate_name_rule(col, present):
                d.update(kind="unverified", finding=f"values: {coord[0]}", action="redact", phi_type="geo")
            elif hint := name_hint_rule(col, nonempty):
                d.update(kind="uncertain", finding=hint[0], action=hint[1], phi_type=hint[2])
            elif (shape := value_shape_rule(col, nonempty, reference_year)) and shape[2] != "zip":
                d.update(kind="uncertain", finding=f"values: {shape[0]}", action=shape[1], phi_type=shape[2])
            elif upstream.is_high_cardinality_numeric(nonempty) and not measurement_header(col):
                d.update(kind="uncertain", finding="unique numbers (possible record or account number)",
                         action="pseudonym_id", phi_type="id")
            elif shape:  # five-digit numbers that repeat: possible ZIP codes
                d.update(kind="uncertain", finding=f"values: {shape[0]}", action=shape[1], phi_type=shape[2])
            elif check["unverified"]:
                # Fail closed: text the script cannot vouch for is the person's decision.
                d.update(kind="unverified", finding=unverified_finding(check, ctx), action="redact",
                         phi_type="unverified")
            elif check["numeric"]:
                by_name = check["numeric"][2] == "unverified"
                d.update(kind="unverified", finding=f"values: {check['numeric'][0]}",
                         action=check["numeric"][1], phi_type="unverified" if by_name else "id")
                d["numbers_by_name"] = by_name
            elif present and all(is_number(v) for v in present) and numbers:
                # Fail closed on numbers too: record numbers that repeat, dates and ZIP codes
                # written as numbers and ages have no shape that tells them from a measurement,
                # and since round 7 numbers under a column name that names no measurement go to
                # the person's decision whatever their shape (also under a state, a type or a
                # status name).
                d.update(kind="unverified", finding=f"values: {numbers[0]}", action=numbers[1],
                         phi_type=numbers[2])
                d["numbers_by_name"] = numbers[2] == "unverified"
            elif ctx.geography:
                d.update(kind="allowed", action="keep", phi_type="allowed_geography", verified=True,
                         finding="column name: state or country (allowed); every value is a state or "
                                 "country name, a number or a missing-value word")
            elif qualified:
                d.update(kind="none", action="keep", phi_type=None, verified=True,
                         finding="category values under an identifier word (a type, status or payer column)")
            elif not present:
                d.update(kind="none", finding="only missing-value words", action="keep",
                         phi_type=None, verified=True)
            elif all(is_number(v) for v in present):
                d.update(kind="none", action="keep", phi_type=None, verified=True,
                         finding="numbers verified as measurements (under a column name that names a "
                                 "measurement, with no record number, date, coordinate or age over 89 shape)"
                         if measurement_header(col) else
                         "numbers verified as years (four-digit years under a column name for a year)")
            else:
                d.update(kind="none", action="keep", phi_type=None, verified=True,
                         finding="every value verified (a number, a code, a date or a common category word)")
            # Only a column every value of which the script verified counts as verified; one kept
            # over a finding is kept on the person's word (kept_unverified_columns).
            if d["kind"] not in ("none", "allowed"):
                d["verified"] = False
        d["text"] = any(not is_number(v) for v in _shape_values(values))
        # A name inside a longer value in a script without capital letters is not found.
        d["caseless"] = any(has_caseless_text(v) for v in _shape_values(values))
        decisions.append(d)

    # Latitude and longitude under names the rules above do not know.
    # Round 7: a column of numbers redacted only because its name names no measurement is read for the
    # shapes below too, so the plan gives the better reason.
    unvouched = [(d["index"], [str(row.get(d["column"], "") or "") for row in data])
                 for d in decisions if (d["kind"] == "none" and d["action"] == "keep") or d.get("numbers_by_name")
                 or (d["kind"] == "unverified" and d["phi_type"] == "geo")]
    pairs = coordinate_pairs(unvouched, {d["index"] for d in decisions if not measurement_header(str(d["column"]))})
    for d in decisions:
        if d["index"] in pairs:
            d.update(kind="uncertain", action="redact", phi_type="geo", verified=False, numbers_by_name=False,
                     finding="values: decimal numbers shaped like latitude and longitude "
                             "(with the column next to it)")
    # Round 6: beside a column found to be a coordinate, a column of decimals within 90 under a name that
    # names no measurement is its partner, also with one place (a longitude of -122.4 beside 37.8).
    geo = {d["index"] for d in decisions if d.get("phi_type") == "geo"}
    for d in decisions:
        if ((d["kind"] == "none" and d["action"] == "keep") or d.get("numbers_by_name")) \
                and ({d["index"] - 1, d["index"] + 1} & geo) \
                and not measurement_header(str(d["column"])) \
                and _latitude_partner([str(row.get(d["column"], "") or "") for row in data]):
            d.update(kind="uncertain", action="redact", phi_type="geo", verified=False, numbers_by_name=False,
                     finding="values: decimal numbers within the range of a latitude beside a column of "
                             "coordinates (a possible coordinate)")
    # A month and a day written in their own columns beside the year.
    parts = date_sibling_positions([(d["index"], d["column"], [str(row.get(d["column"], "") or "") for row in data])
                                    for d in decisions], reference_year)
    for d in decisions:
        if d["index"] in parts and (d["action"] == "keep" or d.get("numbers_by_name")):
            d.update(kind="unverified", action="redact", phi_type="date", verified=False, numbers_by_name=False,
                     finding=f"values: whole numbers that are the {parts[d['index']]} of a date written in "
                             "columns beside its year: a date element other than the year")
    # A month, a day, a week or a day of the year written in a column of its own, whatever the column is
    # called (rounds 4 and 5). A date column counts as a year, since the output keeps its year; and the
    # rule wins over an age found by the values, which would keep every value under 90.
    columns = [(d["index"], d["column"], [str(row.get(d["column"], "") or "") for row in data]) for d in decisions]
    dated = {d["index"] for d in decisions if d["action"] in ("year", "birth_date", "birth_year")}
    parts = date_part_columns(columns, year_columns(columns, reference_year) | dated)
    for d in decisions:
        if d["index"] in parts and (d["action"] == "keep" or d.get("numbers_by_name")
                                    or (d["action"] == "age" and d["kind"] != "identifier")):
            d.update(kind="unverified", action="redact", phi_type="date", verified=False, numbers_by_name=False,
                     finding=f"values: {parts[d['index']]}")
    for d in decisions:
        d["keep_refusal"] = None if d["kind"] in ("none", "allowed", "identifier") or d["free_text"] \
            else keep_refusal(str(d["column"]), [str(row.get(d["column"], "") or "") for row in data], scrubber)
        if d["keep_refusal"]:
            d["finding"] = d["finding"].replace("; keep with --keep COLUMN once the person confirms it",
                                                "; it cannot be kept under this column name")
            d["finding"] += "" if d["finding"].endswith("under this column name") else \
                " (it cannot be kept under this column name)"

    by_name = {str(d["column"]): d for d in decisions}
    by_index = {f"#{d['index']}": d for d in decisions}
    keep = expand_positions(keep, len(decisions), by_name, "--keep")
    redact = expand_positions(redact, len(decisions), by_name, "--redact")

    def lookup(ref: str) -> dict:
        d = by_name.get(ref) or by_index.get(ref)
        if d is None:
            raise UsageError(f"no column named {ref!r} (use the exact name, or #N for the N-th column)")
        return d

    for ref in sorted(redact):
        d = lookup(ref)
        d["action"] = "redact"
        d["forced_redaction"] = True
    for ref in sorted(keep):
        d = lookup(ref)
        if d["forced_redaction"]:
            raise UsageError(f"column {ref!r} is named in both --keep and --redact")
        if d["kind"] == "identifier":
            raise UsageError(
                f"column {ref!r} is a Safe Harbor identifier by its name ({d['finding']}); "
                "it cannot be kept. Rename the column only if its name is wrong.")
        if d["free_text"]:
            raise UsageError(
                f"column {ref!r} holds free text; Safe Harbor mode cannot keep it, because names "
                "inside sentences have no pattern to find. Leave it redacted, or have the person "
                "review it with deidentify.py in their own terminal.")
        if d.get("keep_refusal"):
            raise UsageError(
                f"column {ref!r} cannot be kept: {d['keep_refusal']}. Leave it redacted; if the name is wrong "
                "and the column holds nothing but category values or measurements, ask the person to rename it "
                "to a plain column name (Diagnosis, Drug, Site, Visit, ...) and run again.")
        # Recorded even for a column kept anyway, so the residual check honours the
        # person's confirmation of its shape (it still scans the cells for patterns).
        d["action"] = "keep"
        d["kept_on_request"] = True
    return decisions


# ================================================================ transforms
class UsageError(Exception):
    pass


def _years_in(v: str) -> list[str]:
    return re.findall(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", v)


def to_year(v: str, scrubber: Scrubber, reference_year: int | None = None) -> str:
    s = v.strip()
    # 20210314, 20210314T0930 and a year and month written as one number, 202103.
    m = re.fullmatch(YEAR4 + r"(?:0[1-9]|1[0-2])(?:(?:0[1-9]|[12]\d|3[01])(?:T?\d{4,6})?)?", s)
    if m:
        return s[:4]
    years = set(_years_in(s))
    if len(years) == 1:
        return years.pop()
    # A date of another script or calendar (round 8): its Gregorian year (R1.5.1, 14 มีนาคม 2562, 平成31年4月30日).
    if not years:
        found = {h.year for h in find_dates(s, reference_year or date.today().year) if h.year}
        if len(found) == 1:
            return str(found.pop())
    # A Unix timestamp or a Julian date written as a number (round 7): its year.
    if reference_year is not None and is_number(s):
        year = numeric_date_year(s, reference_year)
        if year is not None:
            return str(year)
    if re.search(r"\d", s) or s.lower() not in MISSING_VALUES:
        return "[DATE]"  # no single year to keep, or text that is not a missing-value word
    return v


def birth(v: str, scrubber: Scrubber, reference_year: int) -> str:
    return cap_old_year(to_year(v, scrubber, reference_year), reference_year)


def zip3(v: str) -> str:
    s = re.sub(r"\s", "", v)
    if re.fullmatch(r"\d{4}", s):
        s = "0" + s  # a ZIP stored as a number loses its leading zero
    m = re.fullmatch(r"(\d{3})\d{2}(?:-?\d{4})?|(\d{3})", s)
    if not m:
        return "[ZIP]"
    prefix = m.group(1) or m.group(2)
    return "000" if prefix in RESTRICTED_ZIP3 else prefix


UNIT_FACTORS = (
    # Single letters other than y are not read as units: "96 M" is more often a sex than
    # months, "aged" is not "age" in days, and an unread unit counts as years, which can only
    # over-group. The words of other languages come from column names ("Alter (Monate)").
    (re.compile(r"y|yr|yrs|years?|yo|y/o|yoa|ys|jahre|jahren|jahr|anos|ano|anni|anno|anys|any|ans|an|jaar"
                r"|jaren|ar|aar|lat|let|roky|rok|rokov|vuotta|yil|yas|sui|tuoi|sal|岁|歲|歳|才|세|살"), 1.0),
    (re.compile(r"mo|mos|mon|mths?|months?|monate|monaten|meses|mes|mois|mesi|maanden|manader|miesiecy"
                r"|kuukautta"), 12.0),
    (re.compile(r"wk|wks|weeks?|wochen|semanas|semaines|settimane|weken|veckor"), 52.18),
    (re.compile(r"dy|dys|days?|tage|tagen|dias|jours|giorni|dagen|dagar"), 365.25),
    (re.compile(r"hr|hrs|hours?"), 8766.0),
)
AGE_RANGE = re.compile(r"\d\s*(?:-|\u2013|to)\s*\d")


def _unit_factor(word: str) -> float | None:
    for rx, factor in UNIT_FACTORS:
        if rx.fullmatch(word.lower()):
            return factor
    return None


def age_years(v: str, header: str) -> list[float]:
    """Every number in an age cell, in years. A unit written after a number wins;
    otherwise the unit in the column name (age_days, age_months), else years."""
    base = 1.0
    for tok in column_tokens(header):
        m = re.fullmatch(r"age(.+)", tok)
        factor = _unit_factor(m.group(1) if m else tok)
        if factor is not None and (m or tok != "y"):
            base = factor
    out = []
    v = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", _without_accents(v))
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([^\W\d_]+)?", v):
        factor = _unit_factor(m.group(2)) if m.group(2) else None
        out.append(float(m.group(1)) / (factor if factor is not None else base))
    return out


def age_over_89(v: str, header: str) -> bool:
    return bool(AGE_WORD_RX.search(v)) or any(y >= 90 for y in age_years(v, header))


# Words an age cell may hold besides its numbers ("45 years", "18 to 29", "65 and over",
# "under 1", "infant"): anything else in an age column (a name, a place) is replaced.
AGE_TEXT_WORDS = frozenset("""
y yr yrs year years yo y/o old m mo mos mon month months mth mths w wk wks week weeks d dy dys day days h
hr hrs hour hours to and or over under above below older younger less more than plus aged age ages
about approx approximately circa ca years-old yrs. at least up infant infants newborn newborns neonate
neonates neonatal child children adolescent adolescents teen teens teenager teenagers adult adults
elderly senior seniors pediatric paediatric geriatric toddler toddlers baby babies preterm term
anos ano ans an anni jahre jahren jahr j jaar ar lat let roky rok yil v vuotta ev meses mes mois
mesi monate monat maanden semanas semaines wochen settimane dias jours tage giorni dagen
岁 歲 歳 才 세 살 лет год года سنة سنوات שנים वर्ष साल ปี ετών ετη anys any aar rokov sui tuoi sal
""".split())


def _without_accents(v: str) -> str:
    """The text with accents dropped and the letters NFKD does not take apart replaced ("años",
    "år"), recomposed so that Hangul syllables stay whole ("세")."""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(v)) if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", s.translate(LETTERS_WITHOUT_DECOMPOSITION))


def age_text(v: str) -> bool:
    """True for a value an age column may hold: numbers with units of time, ranges, comparators,
    age words ("ninety-two", "infant") and missing-value words; not a name or a place."""
    s = _plain(v)
    if not s or fold(s) in MISSING_PHRASES or s in CASELESS_MISSING or AGE_WORD_RX.search(s) \
            or TOOL_OUTPUT.fullmatch(s) or s in TOOL_PLACEHOLDERS:
        return True
    s = _without_accents(s).casefold()
    rest = re.sub(r"\d+(?:[.,]\d+)?", " ", s)
    rest = re.sub(r"[<>≤≥=~+\-\u2013/().,:;%\[\]]", " ", rest)
    words = rest.split()
    return all(w in AGE_TEXT_WORDS for w in words) and bool(re.search(r"\d", s) or words)


def age_cap(v: str, header: str, scrubber: Scrubber) -> str:
    """90+ for an age over 89 (in any unit, or in words). A range that straddles 90
    ("85-94") is replaced, because it would split the ages over 89, and so is a value that is
    not an age ("Alice Okafor" under "Edad")."""
    if AGE_WORD_RX.search(v):
        return "90+"
    if not age_text(v):
        return "[REDACTED]"
    years = age_years(v, header)
    if any(y >= 90 for y in years):
        if any(y < 90 for y in years) and AGE_RANGE.search(v):
            return "[REDACTED]"
        return "90+"
    return scrubber.scrub(v)[0]


def apply_decisions(data: list[dict], headers: list[str], decisions: list[dict],
                    scrubber: Scrubber, reference_year: int):
    """The de-identified rows, the pseudonym mapping, and per-column change counts."""
    by_col = {d["column"]: d for d in decisions}
    pseudo_cols = [d["column"] for d in decisions if d["action"] in ("pseudonym_name", "pseudonym_id")]
    reserved = {str(row.get(c, "") or "").strip() for row in data for c in pseudo_cols}
    reserved.discard("")
    names = upstream.PseudonymGenerator(prefix="P", reserved=reserved)
    ids = upstream.IDReplacer(prefix="ID", reserved=reserved)
    changed = {c: 0 for c in headers}
    ctxs = {c: ColumnContext(c) for c in headers}
    out_rows = []
    for row in data:
        new = {}
        for col in headers:
            v = str(row.get(col, "") or "")
            d = by_col[col]
            action = d["action"]
            if not v.strip():
                new[col] = v
                continue
            if action == "redact":
                nv = "[REDACTED]"
            elif action == "pseudonym_name":
                nv = names.get(v.strip())
            elif action == "pseudonym_id":
                nv = ids.get(v.strip())
            elif action == "year":
                nv = cap_old_year(to_year(v, scrubber, reference_year), reference_year)
            elif action == "birth_date":
                nv = birth(v, scrubber, reference_year)
            elif action == "birth_year":
                nv = birth(v, scrubber, reference_year)
            elif action == "zip3":
                nv = zip3(v)
            elif action == "age":
                nv = age_cap(v, col, scrubber)
            else:  # keep: scrub identifier patterns out of the cell
                nv = scrub_cell(scrubber, v, ctxs[col])[0]
            if nv != v:
                changed[col] += 1
            new[col] = nv
        out_rows.append(new)
    return out_rows, {"names": names.mapping, "ids": ids.mapping}, changed


# ================================================================ residual check
def residual_findings(rows: list[dict], headers: list[str], decisions: list[dict] | None,
                      scrubber: Scrubber, reference_year: int) -> list[dict]:
    """Columns whose output still holds an identifier, with counts. No values.

    Every kept column is scanned for identifier patterns. A kept column the person did not
    name with --keep is also checked as the run classified it: by the shape of its numbers,
    and by verifying again that every value is a number, a code, a vocabulary word or an
    allowed place (verify_column). A column the person kept is trusted for those shapes, never
    for patterns. Without the run's report (decisions is None) no column counts as kept on
    request, so text the script cannot verify fails the check."""
    findings = []
    by_col = {d["column"]: d for d in decisions} if decisions else {}
    actions, kept_on_request = {}, set()
    ctxs = {i: ColumnContext(col) for i, col in enumerate(headers, start=1)}
    for i, col in enumerate(headers, start=1):
        d = by_col.get(col)
        if d is None:
            rule = column_name_rule(col, [str(row.get(col, "") or "") for row in rows], scrubber)
            actions[i] = rule[1] if rule else "keep"
        else:
            actions[i] = d["action"]
            if d.get("kept_on_request"):
                kept_on_request.add(i)
    shape_checked = [(i, [str(row.get(col, "") or "") for row in rows])
                     for i, col in enumerate(headers, start=1)
                     if actions[i] == "keep" and i not in kept_on_request]
    shapes = {}
    # Months and days in columns of their own: the columns of years are those the output keeps as
    # years, a subset of the ones the run counted, so the check is never stricter than the run.
    years = year_columns([(i, col, [str(row.get(col, "") or "") for row in rows])
                          for i, col in enumerate(headers, start=1)
                          if actions[i] in ("keep", "birth_year", "birth_date", "year")], reference_year)
    parts = date_part_columns([(i, headers[i - 1], vals) for i, vals in shape_checked], years)
    for i, vals in shape_checked:
        shape = (value_shape_rule(headers[i - 1], vals, reference_year) or date_part_rule(headers[i - 1], vals)
                 or coordinate_name_rule(headers[i - 1], vals))
        if shape:
            shapes[i] = (shape[0], shape[3])
            continue
        if i in parts:
            shapes[i] = (parts[i], sum(1 for v in vals if v.strip()))
            continue
        check = verify_column(headers[i - 1], vals, reference_year, ctxs[i], own_output=decisions is None)
        numbers = number_rule(headers[i - 1], vals, reference_year)
        if check["unverified"]:
            shapes[i] = (residual_text_finding(check), check["cells"])
        elif check["numeric"]:
            shapes[i] = (check["numeric"][0], sum(1 for v in vals if number_like(v)))
        elif numbers:
            shapes[i] = (numbers[0], numbers[3])
    pairs = coordinate_pairs(shape_checked, {i for i, _ in shape_checked if not measurement_header(headers[i - 1])})
    for i, col in enumerate(headers, start=1):
        action = actions[i]
        counts: dict[str, int] = {}
        if shapes.get(i):
            finding, cells = shapes[i]
            counts[finding] = cells
        if i in pairs:
            counts["decimal numbers shaped like latitude and longitude"] = pairs[i]
        for row in rows:
            v = str(row.get(col, "") or "").strip()
            if not v or v in TOOL_PLACEHOLDERS:
                continue
            problem = None
            # Transformed columns are checked by their shape; a pseudonym such as
            # ID0001 would itself look like a code to the pattern scan.
            scan = False
            if action in ("pseudonym_name", "pseudonym_id"):
                if not PSEUDONYM.fullmatch(v):
                    problem = "not a pseudonym"
            elif action == "redact":
                problem = "not redacted"
            elif action in ("year", "birth_date", "birth_year"):
                if re.fullmatch(r"\d{4}", v):
                    if reference_year - int(v) >= 90:
                        problem = "a year 90 or more years before the reference year (a birth year reveals an age over 89)"
                elif re.search(r"\d", v):
                    problem = "date not reduced to a year"
                elif v.lower() not in MISSING_VALUES:
                    problem = "text left in a date column"
            elif action == "zip3":
                if not re.fullmatch(r"\d{3}", v) or v in RESTRICTED_ZIP3:
                    problem = "ZIP code not reduced to an allowed three-digit prefix"
            elif action == "age":
                if v != "90+":
                    if age_over_89(v, col):
                        problem = "age over 89"
                    elif not age_text(v):
                        problem = "text left in an age column"
                    scan = True
            elif decisions is None and PSEUDONYM.fullmatch(v):
                scan = False  # a pseudonym written by this tool, checked without its report
            else:
                scan = True
            if problem is None and scan:
                kinds = scrub_cell(scrubber, v, ctxs[i])[1]
                if kinds:
                    problem = f"{kinds[0].replace('_', ' ')} pattern"
            if problem:
                counts[problem] = counts.get(problem, 0) + 1
        for problem, n in sorted(counts.items()):
            findings.append({"index": i, "column": col, "problem": problem, "cells": n})
    return findings


# ================================================================ output
def display_name(d: dict, withheld: set[int]) -> str:
    # A line break or a tab in a column name is shown as a space, so the plan keeps one line per column.
    return f"#{d['index']} (name withheld)" if d["index"] in withheld else " ".join(str(d["column"]).split())


def print_plan(decisions: list[dict], withheld: set[int], changed: dict | None = None) -> None:
    width = min(34, max([len(display_name(d, withheld)) for d in decisions] + [6]))
    print(f"  {'#':>3}  {'column':<{width}}  {'action':<16}  {'cells changed' if changed else ''}")
    for d in decisions:
        label = {"pseudonym_name": "pseudonym P####", "pseudonym_id": "pseudonym ID####",
                 "year": "year only", "birth_date": "birth year/90+", "birth_year": "birth year/90+",
                 "zip3": "ZIP first 3", "age": "ages 90+ capped", "redact": "redact",
                 "keep": "keep, scrubbed"}[d["action"]]
        note = ""
        if d["kept_on_request"]:
            note = "  [kept on request]"
        elif d["forced_redaction"]:
            note = "  [redacted on request]"
        count = f"{changed.get(d['column'], 0):>13}" if changed is not None else ""
        name = display_name(d, withheld)
        if len(name) > width:
            name = name[: width - 3] + "..."
        print(f"  {d['index']:>3}  {name:<{width}}  {label:<16}  {count}  {d['finding']}{note}")
    names = lambda ds: ", ".join(display_name(d, withheld) for d in ds)  # noqa: E731
    pending = needing_decision(decisions)
    if pending:
        print("\n  Need the person's decision (changed because the script cannot verify their values are free")
        print("  of identifiers; keep with --keep COLUMN once the person confirms it): " + names(pending))
        print("  Ask the person, naming only these columns, whether each one holds nothing but category values")
        print("  or measurements, with no names, places, coordinates, dates or parts of a date, ages over 89,")
        print("  record or account numbers, contact details or other identifiers. A column of numbers is here")
        print("  when its name names no measurement: the script cannot verify that such numbers are not")
        print("  identifiers, dates or coordinates.")
    unkeepable = cannot_be_kept(decisions)
    if unkeepable:
        print("\n  Changed and cannot be kept under their names (a word in the name is not a column word the")
        print("  script knows, or the name names a person who is not clinical or care staff, such as the")
        print("  person, a relative, a contact, a reporter or a manager, alone or beside a part of a name,")
        print("  or an employer, a home, an address, a device, an image, notes, a place that is not a place")
        print("  of care or a record, or the values are numbers of five or more digits under a name that")
        print("  names no measurement): " + names(unkeepable))
        print("  Do not offer --keep for these. They stay redacted or pseudonymized; if the person says a name")
        print("  is wrong and the column holds only category values or measurements, they rename it and rerun.")
    free = [d for d in decisions if d["free_text"] and d["action"] != "keep"]
    if free:
        print("\n  Free text, redacted and never kept (a name inside a sentence has no pattern to find): "
              + names(free))
    if withheld:
        print("\n  " + WITHHELD_NOTE.format(
            positions=", ".join(f"#{i}" for i in sorted(withheld)),
            names=", ".join(f"column_{i}" for i in sorted(withheld))))
    on_word = kept_unverified_columns(decisions)
    kept = [d for d in decisions if d["action"] == "keep" and d not in on_word]
    if kept:
        print("  Kept (identifier patterns inside them are replaced): " + names(kept))
    verified = [d for d in kept_text_columns(decisions) if d.get("verified")]
    if verified:
        print("  Kept text the script verified (every value a number, a code, a date, a common category")
        print("  word such as a sex, a race or yes and no, or a state or country name): " + names(verified))
    if on_word:
        print("  Kept on the person's word: " + names(on_word))
        print("  " + KEPT_TEXT_WARNING)
        caseless = [d for d in on_word if d.get("caseless")]
        if caseless:
            print("  Of these, text in a script without capital letters (Chinese, Japanese, Korean, Arabic,")
            print("  Hebrew, Hindi, Thai, ...), where not even a titled name inside a longer value is certain")
            print("  to be found: " + names(caseless))


WITHHELD_NOTE = ("Column names withheld, because a word in them is not a column word the script knows or "
                 "they look like a value (a first row of data, or a name): {positions}. The output names "
                 "them {names}. If the file has no header row, rerun with --no-header, so the first row "
                 "is read as data. If the person confirms that a withheld name is an ordinary column name "
                 "with no identifier in it, rerun with --keep-name #N (or --keep-all-names for the whole "
                 "first row).")


KEPT_TEXT_WARNING = ("Columns kept on the person's word are scrubbed for identifier patterns only (phone "
                     "and fax numbers, email and web addresses, labelled ID and record numbers, dates, "
                     "street addresses, IP addresses, titled names): a name, a place, a record number, a "
                     "ZIP code, an age or another identifier with no pattern stays in them, so the person "
                     "must spot-check these columns before the data leaves the institution.")


def kept_text_columns(decisions: list[dict]) -> list[dict]:
    """Kept columns holding text, verified or kept on the person's word."""
    return [d for d in decisions if d["action"] == "keep" and d.get("text")]


def kept_unverified_columns(decisions: list[dict]) -> list[dict]:
    """Columns kept on request that the script could not verify, text or numbers (record
    numbers, ZIP codes, coordinates, old years kept over the finding): kept on the person's word,
    scrubbed for patterns only, and named again for the person's spot-check."""
    return [d for d in decisions if d["action"] == "keep" and d["kept_on_request"] and not d.get("verified")]


def needing_decision(decisions: list[dict]) -> list[dict]:
    """Columns changed only because the script cannot verify their values, which the person may
    keep once they confirm them: text it cannot verify, numbers and other shapes it cannot tell
    from identifiers, and column names that usually hold a name or a place."""
    return [d for d in decisions if d["kind"] in ("unverified", "uncertain") and not d["free_text"]
            and d["action"] != "keep" and not d["forced_redaction"] and not d.get("keep_refusal")]


def cannot_be_kept(decisions: list[dict]) -> list[dict]:
    """Columns the script changed because it could not verify them and that --keep refuses by their
    names (keep_refusal): the person renames them or leaves them changed (round 4)."""
    return [d for d in decisions if d.get("keep_refusal") and d["action"] != "keep" and not d["forced_redaction"]]


def load_input(path: Path, scrubber: Scrubber, encoding: str | None = None, locale_code: str = "us",
               no_header: bool = False, delimiter: str | None = None, keep_names: set[str] | None = None,
               keep_all_names: bool = False, number_duplicates: bool = False):
    if not path.is_file():
        raise UsageError(f"input file not found: {path}")
    data, meta = read_table(path, encoding, locale_code, no_header=no_header, delimiter=delimiter,
                            number_duplicates=number_duplicates)
    headers = list(meta.get("headers") or [])
    if not headers:
        raise UsageError("the file has no header row")
    if not data:
        raise UsageError("the file has a header row but no data rows")
    confirmed = confirmed_names(keep_names or set(), len(headers))
    if keep_all_names:
        confirmed = set(range(1, len(headers) + 1))
    by_position = confirmed_names(keep_names or set(), len(headers))
    withheld = set() if no_header else check_header_row(headers, scrubber, confirmed, by_position)
    return data, meta, headers, withheld


POSITION_RANGE = re.compile(r"#(\d+)\s*-\s*#?(\d+)")


def expand_positions(refs: set[str], width: int, names: dict | None = None, option: str = "--keep-name") -> set[str]:
    """The references with each range of positions ("#2-#501", "#2-501") written out as #2, #3, ... #501
    (round 7), so a wide matrix of measurements can be confirmed in one option. A column whose name is
    the range itself is meant by name."""
    out = set()
    for ref in refs:
        m = POSITION_RANGE.fullmatch(ref.strip())
        if not m or (names and ref in names):
            out.add(ref)
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if not 1 <= a <= b <= width:
            raise UsageError(f"{option} {ref!r}: a range of positions runs from a lower to a higher position, "
                             f"both from 1 to {width}")
        out |= {f"#{i}" for i in range(a, b + 1)}
    return out


def confirmed_names(refs: set[str], width: int) -> set[int]:
    """The positions named with --keep-name, which must be written #N, or as a range #A-#B: the agent never
    sees a withheld name, so it cannot name one."""
    out = set()
    for ref in expand_positions(refs, width):
        m = re.fullmatch(r"#(\d+)", ref.strip())
        if not m or not 1 <= int(m.group(1)) <= width:
            raise UsageError(f"--keep-name takes a column position such as #2 (1 to {width}), or a range of them "
                             "such as #2-#501, the way the plan names a withheld column; it does not take a name")
        out.add(int(m.group(1)))
    return out


# Encodings a locale's exports often use when they are not UTF-8.
LOCALE_ENCODINGS = {"kr": "euc-kr", "jp": "shift_jis", "cn": "gb18030"}


def file_encoding(path: Path, requested: str | None, locale_code: str = "us") -> str | None:
    """The text encoding to read a CSV or TSV file with: the one the person named with
    --encoding, else UTF-8, with or without a byte order mark, or UTF-16 and UTF-32 with one.
    Any other file is refused with the remedy, because guessing an 8-bit encoding can turn names
    into other text silently. No byte of the file is quoted."""
    if upstream.detect_format(path) == "xlsx":
        return None
    raw = path.read_bytes()
    if requested:
        try:
            codecs.lookup(requested)
        except LookupError:
            raise UsageError(f"--encoding {requested!r} is not an encoding this Python knows (for example "
                             "utf-8, cp1252, latin-1, utf-16, euc-kr, shift_jis, gb18030)")
        try:
            raw.decode(requested)
        except (UnicodeDecodeError, UnicodeError):
            raise UsageError(f"the file cannot be read as {requested}. Ask the person which encoding the "
                             "export uses, or save it as 'CSV UTF-8' and run again without --encoding.")
        return requested
    if raw.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return "utf-32"
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    head = raw[:4096]
    # Round 7: UTF-16 text of Latin letters with no byte order mark is valid UTF-8 too, with a NUL beside
    # every letter, so it was read as UTF-8 and a first row of data slipped past the column-name checks. A
    # NUL in a text file's first bytes is read as UTF-16 without a byte order mark and refused.
    if b"\x00" in head:
        odd = sum(1 for k in range(1, len(head), 2) if head[k] == 0)
        even = sum(1 for k in range(0, len(head), 2) if head[k] == 0)
        suggestion = "utf-16-le" if odd >= even else "utf-16-be"
        raise UsageError("the file holds NUL bytes in its first bytes, so it looks like UTF-16 text without a "
                         "byte order mark. Save it again as 'CSV UTF-8' (in Excel: File, Save As, CSV UTF-8) "
                         f"and run again, or rerun with --encoding {suggestion} (or the encoding the person "
                         "names). No output was written.")
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    if head.count(b"\x00") > len(head) // 4:
        kind, suggestion = "UTF-16 text without a byte order mark", "utf-16-le"
    else:
        kind = "an 8-bit encoding such as Windows-1252 or Latin-1, which Excel writes for a plain 'CSV' save"
        suggestion = LOCALE_ENCODINGS.get(locale_code, "cp1252")
    raise UsageError(f"the file is not UTF-8 text; it looks like {kind}. Save it again as 'CSV UTF-8' "
                     "(in Excel: File, Save As, CSV UTF-8) and run again, or rerun with --encoding "
                     f"{suggestion} (or the encoding the person names). No output was written.")


DELIMITERS = {",": ",", "comma": ",", ";": ";", "semicolon": ";", "|": "|", "pipe": "|", "tab": "\t",
              "\\t": "\t", "\t": "\t"}


def _xlsx_rows(path: Path) -> tuple[list[list[str]], int]:
    """The cell text of the first sheet of a workbook, and how many other sheets it has. No sheet
    name is printed or kept: a workbook with one sheet per patient names them."""
    try:
        import openpyxl
    except ImportError:
        raise UsageError("openpyxl is required for .xlsx files (pip install openpyxl), or save the first "
                         "sheet as 'CSV UTF-8' and run on that")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        names = list(wb.sheetnames)
        rows = [[upstream._cell_text(v) for v in row] for row in wb[names[0]].iter_rows(values_only=True)]
    finally:
        wb.close()
    return rows, len(names) - 1


def read_table(path: Path, encoding: str | None = None, locale_code: str = "us", no_header: bool = False,
               delimiter: str | None = None, number_duplicates: bool = False):
    """The rows of a CSV, TSV or Excel file as dicts keyed by column name, and metadata. The first
    row is the header row unless `no_header`, when the columns are named column_1, column_2, ...
    and every row is data. A blank header cell is named column_N too. Every message names
    positions and counts, never a cell: a first row of data, or a sheet name, can be a patient's
    name (deidentify.py quoted duplicate header names)."""
    fmt = upstream.detect_format(path)
    meta = {"format": fmt, "sheets_skipped": [], "delimiter": None}
    if fmt == "xlsx":
        if delimiter:
            raise UsageError("--delimiter applies to CSV and text files, not to an Excel workbook")
        rows, skipped = _xlsx_rows(path)
        meta["sheets_skipped"] = [None] * skipped
        numbered = list(enumerate(rows, start=1))
    else:
        sep = DELIMITERS.get(delimiter, delimiter) if delimiter else ("\t" if fmt == "tsv" else ",")
        if len(sep) != 1:
            raise UsageError("--delimiter takes one character, or comma, semicolon, pipe or tab")
        meta["delimiter"] = sep
        enc = file_encoding(path, encoding, locale_code)
        numbered = []
        with open(path, newline="", encoding=enc) as f:
            reader = csv.reader(f, delimiter=sep)
            for row in reader:
                if row:  # a blank line holds no row, as csv.DictReader reads it
                    numbered.append((reader.line_num, row))
    if not numbered:
        raise UsageError("the file is empty")
    refuse_other_separator([c for c in numbered[0][1]], fmt)
    if no_header:
        width = max(len(r) for _, r in numbered)
        headers = [f"column_{i}" for i in range(1, width + 1)]
        body = numbered
    else:
        first = list(numbered[0][1])
        if first and str(first[0]).startswith("\ufeff"):
            first[0] = str(first[0])[1:]  # a byte order mark read as text (--encoding utf-8 on a UTF-8-BOM file)
        headers = [h if str(h).strip() else f"column_{i}" for i, h in enumerate(first, start=1)]
        body = numbered[1:]
    seen: dict[str, int] = {}
    for i, h in enumerate(headers, start=1):
        if h in seen and number_duplicates:
            # Round 8: a repeated name is given its position (Glucose_7), as an Excel export often repeats one.
            new = f"{h}_{i}"
            while new in seen or new in headers:
                new += "_"
            headers[i - 1] = h = new
        elif h in seen:
            raise UsageError(f"columns #{seen[h]} and #{i} have the same name, so they cannot be told apart. "
                             "If the first row is data (the file has no header row), rerun with --no-header; "
                             "if the person confirms that the first row holds column names, rerun with "
                             "--number-duplicates, which gives each repeated name its position (column #7 of a "
                             "repeated name is written with _7 after it); otherwise ask the person to give each "
                             "column a unique name.")
        seen[h] = i
    data = []
    for line, row in body:
        if len(row) > len(headers) and any(str(c).strip() for c in row[len(headers):]):
            raise UsageError(f"{path.name}, line {line}: this row has more fields than the header "
                             f"({len(headers)} columns). Fix the file (for example an unquoted "
                             f"{'comma' if meta['delimiter'] == ',' else 'separator'}) and run again.")
        data.append({h: (str(row[i]) if i < len(row) else "") for i, h in enumerate(headers)})
    meta["headers"] = headers
    meta["rows"] = len(data)
    return data, meta


def refuse_other_separator(first_row: list[str], fmt: str = "csv") -> None:
    """A file read as one column whose only cell holds ';', '|' or a tab uses another separator:
    every row would be one long text value. The message names no cell, which can be a person's
    name."""
    if fmt != "xlsx" and len(first_row) == 1 and any(c in str(first_row[0]) for c in ";|\t"):
        raise UsageError("the file was read as one column whose first cell contains ';', '|' or a tab, so "
                         "it uses another column separator. Rerun with --delimiter ';' (or '|', or tab), "
                         "or save it as CSV with commas (or as .tsv with tabs).")


def resolve_locale(args) -> dict:
    if args.locale_file:
        return upstream.load_locale_file(args.locale_file)
    return upstream.load_locale(args.locale or "us")


def cmd_plan(args) -> int:
    locale = resolve_locale(args)
    scrubber = Scrubber(locale, args.reference_year)
    data, meta, headers, withheld = load_input(Path(args.input_file), scrubber, args.encoding,
                                               locale.get("code", "us"), args.no_header, args.delimiter,
                                               set(args.keep_name), args.keep_all_names, args.number_duplicates)
    decisions = decide_columns(data, headers, locale, scrubber, set(args.keep), set(args.redact),
                               args.reference_year)
    print("Safe Harbor plan (no cell values are printed)")
    print(f"  input: {Path(args.input_file).name}  rows: {len(data)}  columns: {len(headers)}  "
          f"locale: {locale.get('code', 'custom')}")
    if meta.get("sheets_skipped"):
        print(f"  only the first sheet is read; {len(meta['sheets_skipped'])} other sheet(s) are not written to the output")
    print()
    print_plan(decisions, withheld)
    print("\nNothing was written. Run the same command with 'run' and --output-dir to de-identify.")
    return 0


def cmd_run(args) -> int:
    locale = resolve_locale(args)
    scrubber = Scrubber(locale, args.reference_year)
    input_path = Path(args.input_file).resolve()
    out_dir = Path(args.output_dir).resolve()
    data, meta, headers, withheld = load_input(input_path, scrubber, args.encoding, locale.get("code", "us"),
                                               args.no_header, args.delimiter, set(args.keep_name),
                                               args.keep_all_names, args.number_duplicates)
    decisions = decide_columns(data, headers, locale, scrubber, set(args.keep), set(args.redact),
                               args.reference_year)

    mapping_path = Path(args.mapping_out).resolve() if args.mapping_out else None
    if mapping_path is not None:
        if out_dir == mapping_path.parent or out_dir in mapping_path.parents:
            raise UsageError("--mapping-out must be outside the output directory: the mapping "
                             "holds the original identifiers and must not travel with the data")
        if mapping_path == input_path:
            raise UsageError("--mapping-out names the input file")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{input_path.stem}_deidentified{input_path.suffix}"
    if out_path == input_path:
        raise UsageError("the output would overwrite the input; choose another --output-dir")
    report_path = out_dir / REPORT_NAME

    rows, mapping, changed = apply_decisions(data, headers, decisions, scrubber, args.reference_year)
    residual = residual_findings(rows, headers, decisions, scrubber, args.reference_year)
    pending = needing_decision(decisions)
    out_names = output_headers(headers, withheld)

    report = {
        "tool": "phi-deidentification safe_harbor.py",
        "skill_version": SKILL_VERSION,
        "standard": "HIPAA Safe Harbor, 45 CFR 164.514(b)(2): the automated part only",
        "created": datetime.now().isoformat(timespec="seconds"),
        "input_file": input_path.name,
        "output_file": out_path.name if not residual else None,
        "rows": len(rows),
        "columns": len(headers),
        "sheets_not_processed": len(meta.get("sheets_skipped") or []),
        "locale": locale.get("code", "custom"),
        "reference_year": args.reference_year,
        "header_row": not args.no_header,
        "delimiter": meta.get("delimiter"),
        "decisions": [
            {"index": d["index"],
             "column": None if d["index"] in withheld else d["column"],
             "name_withheld": d["index"] in withheld,
             "finding": d["finding"], "action": d["action"],
             "kept_on_request": d["kept_on_request"], "redacted_on_request": d["forced_redaction"],
             "text": d["text"], "verified": bool(d.get("verified")),
             "needs_decision": d in pending,
             "cells_changed": changed.get(d["column"], 0),
             **({"output_column": out_names[d["column"]]} if d["index"] in withheld else {})}
            for d in decisions
        ],
        "residual_check": {
            "clean": not residual,
            "findings": [{**f, "column": None if f["index"] in withheld else f["column"]} for f in residual],
        },
        "columns_needing_decision": [
            {"index": d["index"], "column": None if d["index"] in withheld else d["column"]}
            for d in pending
        ],
        "columns_that_cannot_be_kept": [
            {"index": d["index"], "column": None if d["index"] in withheld else d["column"],
             "reason": d["keep_refusal"]}
            for d in cannot_be_kept(decisions)
        ],
        "kept_text_columns": [
            {"index": d["index"], "column": None if d["index"] in withheld else d["column"],
             "kept_on_request": d["kept_on_request"], "verified": bool(d.get("verified")),
             "script_without_case": bool(d.get("caseless"))}
            for d in kept_text_columns(decisions)
        ],
        "kept_unverified_columns": [
            {"index": d["index"], "column": None if d["index"] in withheld else d["column"],
             "kept_over": d["finding"], "text": d["text"], "script_without_case": bool(d.get("caseless"))}
            for d in kept_unverified_columns(decisions)
        ],
        "kept_text_note": ("A default run keeps only values it verifies: a measurement (a number under a "
                           "column name that names a measurement, such as a lab, a vital sign, a score, a "
                           "dose, a count, a duration or a unit, or with a unit written beside it, and with no "
                           "record number, date, coordinate or age over 89 shape), a year under a column name "
                           "for a year, a code, a date reduced to the year, a common category word or a state "
                           "or country name. Numbers under any other column name (Value, Result, Col3, X) "
                           "are not verified, since the script cannot tell them from identifiers, dates or "
                           "coordinates. Columns the person kept with --keep "
                           "(kept_unverified_columns) were not verified. Column names are not values: a "
                           "column name is copied when every word in it is a column word the script knows "
                           "and any number in it is short (four digits or fewer, and not a year 90 or more "
                           "years ago); the script cannot tell a record number of four digits or fewer, or "
                           "an identifier in an ordinary word, in a column name. " + KEPT_TEXT_WARNING),
        "mapping_written": False,
        "human_review": ("Automated de-identification is not a Safe Harbor determination. A person "
                         "must spot-check the output, confirm that no remaining information could "
                         "identify anyone, and follow the institution's rules before the data leaves it."),
    }

    print("Safe Harbor de-identification (no cell values are printed)")
    print(f"  input: {input_path.name}  rows: {len(rows)}  columns: {len(headers)}  "
          f"locale: {locale.get('code', 'custom')}  reference year: {args.reference_year}")
    if meta.get("sheets_skipped"):
        print(f"  only the first sheet was read; {len(meta['sheets_skipped'])} other sheet(s) are not in the output")
    print()
    print_plan(decisions, withheld, changed)

    if residual:
        if out_path.exists():
            out_path.unlink()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\nResidual check FAILED: identifiers remain in these columns, so no output was kept:")
        for f in residual:
            name = f"#{f['index']} (name withheld)" if f["index"] in withheld else f["column"]
            print(f"  {name}: {f['problem']} in {f['cells']} cell(s)")
        print(f"Report: {report_path}")
        print("Rerun with --redact for those columns. A column named for the shape of its values "
              "(names or places, ZIP codes, coordinates, old years) may instead be kept with --keep "
              "once the person confirms it holds no identifiers. Do not read the input to find out why.")
        return 3

    # A column name that looks like a value or a name (a patient's record read as the header row,
    # a ZIP code) is not copied into the output; every other column name is copied as it is.
    rows = [{out_names[c]: row[c] for c in headers} for row in rows]
    if meta.get("delimiter"):
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=[out_names[c] for c in headers], delimiter=meta["delimiter"])
            writer.writeheader()
            writer.writerows(rows)
    else:
        upstream.save_tabular(rows, out_path, upstream.detect_format(input_path))
    if not out_path.exists():  # save_tabular falls back to CSV when openpyxl is missing
        alt = out_path.with_suffix(".csv")
        if alt.exists():
            out_path = alt
            report["output_file"] = out_path.name

    if mapping_path is not None:
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"_meta": {"tool": "phi-deidentification safe_harbor.py", "input_file": input_path.name,
                             "created": report["created"],
                             "warning": "holds original identifiers: keep restricted, never share"},
                   **mapping}
        fd = os.open(mapping_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.chmod(mapping_path, stat.S_IRUSR | stat.S_IWUSR)
        report["mapping_written"] = True

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nResidual check passed: the output was scanned again and no identifier pattern or "
          "shape was found. This is a pattern check, not proof that the data is de-identified.")
    on_word = kept_unverified_columns(decisions)
    if on_word:
        print(f"Kept on the person's word, scrubbed for patterns only ({len(on_word)}): "
              + ", ".join(display_name(d, withheld) for d in on_word))
        print(KEPT_TEXT_WARNING)
    if pending:
        print(f"Changed because the script cannot verify them ({len(pending)}); keep one with --keep "
              "COLUMN once the person confirms it: " + ", ".join(display_name(d, withheld) for d in pending))
    if withheld:
        print(f"Column names withheld and written as column_N ({len(withheld)}): "
              + ", ".join(f"#{i}" for i in sorted(withheld)) + "; see the note above (--no-header, --keep-name).")
    print(f"Output: {out_path}")
    print(f"Report: {report_path}")
    if mapping_path is not None:
        print(f"Mapping (restricted, holds original identifiers, never open it in a chat): {mapping_path}")
    print("A person must spot-check the output before it leaves the institution: "
          "Safe Harbor is a human determination, and this tool only does the automated part.")
    return 0


def report_decisions(path: Path, headers: list[str], report_arg: str | None):
    """The column actions recorded by the run that wrote `path`, when its report is found."""
    rp = Path(report_arg) if report_arg else path.parent / REPORT_NAME
    if not rp.is_file():
        if report_arg:
            raise UsageError(f"report not found: {rp}")
        return None, None
    try:
        report = json.loads(rp.read_text(encoding="utf-8"))
        if report.get("output_file") != path.name or len(report.get("decisions", [])) != len(headers):
            if report_arg:
                raise UsageError("the report does not describe this file")
            return None, None
        decisions = [{"column": headers[d["index"] - 1], "action": d["action"],
                      "kept_on_request": bool(d.get("kept_on_request"))}
                     for d in report["decisions"]]
    except (ValueError, KeyError, IndexError, TypeError):
        raise UsageError(f"cannot read the report {rp.name}")
    return decisions, rp.name


def report_delimiter(path: Path, report_arg: str | None) -> str | None:
    """The column separator the run that wrote `path` used, from its report, if there is one."""
    rp = Path(report_arg) if report_arg else path.parent / REPORT_NAME
    try:
        report = json.loads(rp.read_text(encoding="utf-8"))
        if report.get("output_file") == path.name and report.get("delimiter") in (",", ";", "|", "\t"):
            return report["delimiter"]
    except (OSError, ValueError, AttributeError):
        pass
    return None


def cmd_verify(args) -> int:
    locale = resolve_locale(args)
    scrubber = Scrubber(locale, args.reference_year)
    path = Path(args.input_file)
    if not path.is_file():
        raise UsageError(f"file not found: {path}")
    delimiter = args.delimiter or report_delimiter(path, args.report)
    data, meta = read_table(path, args.encoding, locale.get("code", "us"), delimiter=delimiter)
    headers = list(meta.get("headers") or [])
    decisions, used = report_decisions(path, headers, args.report)
    # The names in a file this tool wrote are column_N or names it showed or the person confirmed;
    # any other file's names are shown only when they are ordinary column words.
    withheld = set() if used else {i for i, h in ((i, header_for_checks(h)) for i, h in enumerate(headers, start=1))
                                   if header_looks_like_value(h, scrubber) or not header_shown(h)
                                   or header_code_shaped(h) or _invisible_character(h)
                                   or header_date_withheld(h, scrubber.reference_year)}
    findings = residual_findings(data, headers, decisions, scrubber, args.reference_year)
    print("Residual identifier check (no cell values are printed)")
    print(f"  file: {path.name}  rows: {len(data)}  columns: {len(headers)}")
    print(f"  column actions: {'from ' + used if used else 'guessed from column names (no matching report found)'}")
    if not findings:
        print("  clean: no identifier pattern or shape found")
        print("  This is a pattern check, not proof of de-identification. A person still has to "
              "spot-check the file.")
        return 0
    for f in findings:
        name = f"#{f['index']} (name withheld)" if f["index"] in withheld else f["column"]
        print(f"  {name}: {f['problem']} in {f['cells']} cell(s)")
    print("  NOT clean: do not share this file or read it in a chat.")
    return 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="safe_harbor.py",
        description="HIPAA Safe Harbor de-identification of a CSV, TSV or Excel table, "
                    "with no cell value printed and no network calls.")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        g = sp.add_mutually_exclusive_group()
        g.add_argument("--locale", default="us", metavar="CODE",
                       help="identifier patterns of a deidentify.py locale pack (default: us)")
        g.add_argument("--locale-file", metavar="PATH", help="a custom locale pack")
        sp.add_argument("--reference-year", type=int, default=date.today().year, metavar="YYYY",
                        help="year that ages are computed against (default: this year)")
        sp.add_argument("--encoding", metavar="NAME",
                        help="text encoding of a CSV or TSV file that is not UTF-8 (for example cp1252, "
                             "latin-1, utf-16-le, euc-kr); the output is always UTF-8")
        sp.add_argument("--delimiter", metavar="CHAR",
                        help="column separator of a CSV or text file that does not use commas: ';', '|' or "
                             "tab (the output uses the same one)")

    for name, help_text in (("plan", "show what would happen to each column; writes nothing"),
                            ("run", "de-identify the file")):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("input_file")
        common(sp)
        sp.add_argument("--keep", action="append", default=[], metavar="COLUMN",
                        help="keep a column the scanner could not vouch for (name, #N, or a range #A-#B); "
                             "identifier patterns inside it are still replaced. Refused for a column "
                             "that cannot be kept under its name (the plan lists them)")
        sp.add_argument("--redact", action="append", default=[], metavar="COLUMN",
                        help="replace every value of a column with [REDACTED] (name or #N)")
        sp.add_argument("--no-header", action="store_true",
                        help="the file has no header row: every row is data, and the columns are named "
                             "column_1, column_2, ...")
        sp.add_argument("--keep-name", action="append", default=[], metavar="#N",
                        help="show and copy a withheld column name once the person confirms it is an "
                             "ordinary column name with no identifier in it (#N, or a range #A-#B)")
        sp.add_argument("--keep-all-names", action="store_true",
                        help="the person confirmed that the first row holds column names and that none of "
                             "them carries an identifier: show and copy every one")
        sp.add_argument("--number-duplicates", action="store_true",
                        help="give a column whose name repeats an earlier column's name its position after it "
                             "(Glucose_7), instead of refusing the file")
        if name == "run":
            sp.add_argument("-o", "--output-dir", required=True,
                            help="folder for the de-identified file and the report")
            sp.add_argument("--mapping-out", metavar="FILE",
                            help="also write the pseudonym mapping (original values) to FILE, "
                                 "outside the output folder, mode 0600")
    sp = sub.add_parser("verify", help="check a de-identified file for remaining identifiers")
    sp.add_argument("input_file")
    sp.add_argument("--report", metavar="FILE",
                    help="the run's report (default: deidentification_report.json beside the file)")
    common(sp)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "plan":
            return cmd_plan(args)
        if args.command == "run":
            return cmd_run(args)
        return cmd_verify(args)
    except UsageError as e:
        print(f"safe_harbor.py: {e}", file=sys.stderr)
        return 2
    except SystemExit as e:  # deidentify.py stops with a message that names no cell value
        code = e.code
        if isinstance(code, str):
            print(f"safe_harbor.py: {code}", file=sys.stderr)
            return 2
        return int(code or 0)
    except Exception as e:  # never let a traceback print a cell value
        print(f"safe_harbor.py: stopped with {type(e).__name__}; no output was written. "
              "The message is withheld because it could quote a cell value.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
