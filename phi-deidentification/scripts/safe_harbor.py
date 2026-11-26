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
                                  [--encoding NAME]
    python3 safe_harbor.py run    INPUT --output-dir DIR [--locale us] [--keep COL]
                                  [--redact COL] [--reference-year YYYY]
                                  [--mapping-out FILE] [--encoding NAME]
    python3 safe_harbor.py verify FILE [--locale us] [--reference-year YYYY]

What it does, per the 18 identifiers of 45 CFR 164.514(b)(2), is listed in
references/safe-harbor-mode.md. In short: identifier columns found by name
are replaced (names and record numbers by pseudonyms, dates by their year,
ZIP codes by their first three digits or 000, ages over 89 by "90+", the rest
by [REDACTED]). Every other column fails closed: it is kept only when every
value is verified as a measurement (a decimal, a whole number of up to three
digits, or a longer one under a column name that names a measurement), a code of
a closed grammar, a word of a closed vocabulary (sex, yes and no, ...), a date or
an allowed state or country. Any other text, and numbers it cannot tell from
record numbers, dates, ZIP codes or ages, are changed until the person keeps them
with --keep; free text can never be kept. Every kept cell is scrubbed of
identifier patterns, and the output is scanned again before it is kept. A file
that is not UTF-8 is refused unless --encoding names its encoding.

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
import os  # noqa: E402
import re  # noqa: E402
import stat  # noqa: E402
import unicodedata  # noqa: E402
from datetime import date, datetime  # noqa: E402
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
    if re.fullmatch(r"(?i)rs\d+|ENS[A-Z]*\d+(?:\.\d+)?", s):
        return None  # dbSNP and Ensembl identifiers name genes and variants, not people
    return "[ID]"


def _long_number(m: re.Match):
    # The digits of a dbSNP or Ensembl identifier (rs..., ENSG...) name a variant or a gene.
    if re.search(r"(?:^|[^A-Za-z0-9])(?:[Rr][Ss]|ENS[A-Z]*)$", m.string[max(0, m.start() - 12):m.start()]):
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
    ("date", re.compile(r"(?i)\b(?P<label>" + DATE_CONTEXT + r")\s+(?P<v>(?:(?:1[3-9]|2\d|3[01])/(?:0?[1-9]|1[0-2])"
                        r"|(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])|(?:1[3-9]|2\d|3[01])-(?:0[1-9]|1[0-2]))(?![\d/.-])"
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
    ("photo", re.compile(r"(?i)(?<![\w.-])[\w./\\~:-]*[\w-]\.(?:jpe?g|png|gif|bmp|tiff?|heic|heif|webp|dcm|dicom)(?![\w])"), "[IMAGE_FILE]"),
    ("biometric", re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{32,}(?![0-9a-f])"), "[BIOMETRIC_OR_CODE]"),
    ("biometric", re.compile(r"(?<![A-Za-z0-9+/=])(?=[A-Za-z0-9+/]*\d)(?=[A-Za-z0-9+/]*[A-Za-z])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])"), "[BIOMETRIC_OR_CODE]"),
    # Any other unique identifying number or code, also with thousands separators
    # ("274,365,867"), which a nine-digit number written as money would otherwise dodge.
    ("code", re.compile(r"(?<![\d.])\d{9,}(?![\d.])"), _long_number),
    ("code", re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3}){2,}(?![\d,]|\.\d)"),
     lambda m: "[ID]" if len(_digits(m.group(0))) >= 9 else None),
    ("code", re.compile(r"(?<![\w-])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+(?![\w-])|(?<![\w-])(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9]{6,}(?![\w-])"), _code),
]

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
        self.patterns = patterns[:at] + [birth_year_pattern(year)] + patterns[at:] + locale_patterns(locale)

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
LETTERS_WITHOUT_DECOMPOSITION = str.maketrans({"\u00f8": "o", "\u00d8": "O", "\u00e6": "ae", "\u00c6": "Ae",
                                               "\u0131": "i", "\u0142": "l", "\u0141": "L", "\u0111": "d",
                                               "\u0110": "D", "\u0153": "oe", "\u0152": "Oe",
                                               "\u00fe": "th", "\u00f0": "d"})


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
# arrival time) are not here: their numbers are judged by number_rule like any column's.
AGE_WORDS_OTHER_LANGUAGES = frozenset({"edad", "idade", "leeftijd", "wiek", "umur", "usia", "tuoi",
                                       "eletkor", "varsta", "lebensalter", "levensjaar", "alter", "alder",
                                       "yas", "vek", "ika", "starost", "edat", "edats"})
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
prefer titer titre zoster flutter khmer frontier ringers
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
NOT_PERSON_IST = frozenset({"assist", "resist", "insist", "consist", "persist", "subsist",
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


def name_in_other_script(header: str) -> tuple[str, str, str] | None:
    raw = " ".join(unicodedata.normalize("NFKC", str(header)).casefold().replace("_", " ").split())
    if any(w in raw for w in SCRIPT_NAME_ANYWHERE):
        return ("name (a word for name in another script)", "pseudonym_name", "name")
    rest = raw
    for w in sorted(SCRIPT_PATIENT_WORDS, key=len, reverse=True):
        rest = rest.replace(w, " ")
    words = [w for w in re.split(r"[\s/,;:()\[\].\-]+", rest) if w]
    if words and (" ".join(words) in SCRIPT_NAME_WORDS or all(w in SCRIPT_NAME_WORDS for w in words)):
        return ("name (a word for name in another script)", "pseudonym_name", "name")
    return None


def name_rule(header: str) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column whose name marks a Safe Harbor identifier.

    These are the columns that cannot be kept. The terms are deliberately whole
    words: "ip" (inpatient), "tract" (urinary tract) or "cell" (cell type) are not
    identifiers on their own, and a column of IP addresses is still found by its values.
    """
    t = column_tokens(header)
    if age_in_other_language(header, t):
        return ("age", "age", "age")
    script_rule = birth_in_other_script(header, t) or name_in_other_script(header)
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
            "avatar", "mugshot", "face image", "face photo") or (
                "image" in ts and ts & {"path", "file", "url", "face", "patient", "id"}):
        return ("photograph", "redact", "photo")
    if _has(t, "fingerprint", "finger print", "voiceprint", "voice print", "biometric",
            "biometrics", "retinal scan", "iris scan", "palm print", "palmprint",
            "face template", "facial template", "face encoding", "faceprint"):
        return ("biometric identifier", "redact", "biometric")

    # 14 and 15: URLs and IP addresses.
    if _has(t, "url", "uri", "website", "web site", "homepage", "home page", "web address",
            "weblink", "web link", "hyperlink"):
        return ("web address", "redact", "url")
    if _has(t, "ip address", "ipaddress", "ip addr", "ipv4", "ipv6", "remote addr", "client ip",
            "mac address", "macaddress") or whole in ("ip", "ip no"):
        return ("IP or MAC address", "redact", "ip")
    if _has(t, "username", "user name", "login", "screen name", "user id", "userid", "handle"):
        return ("user name", "redact", "id")

    # 12 and 13: vehicles and devices.
    if _has(t, "vin", "license plate", "licence plate", "licenseplate", "plate number",
            "registration plate", "number plate", "vehicle id", "vehicle identification",
            "vehicle number") or whole == "vehicle":
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
            "group number", "medicare", "medicaid", "mbi", "hicn") or whole == "policy":
        return ("health plan number", "redact", "health_plan")
    if _has(t, "account", "acct", "bank account", "iban", "credit card", "card number",
            "cc number", "routing number"):
        return ("account number", "redact", "account")

    # 4 to 7: telephone, fax, email, social security and national ID numbers.
    if _has(t, "fax", "facsimile"):
        return ("fax number", "redact", "phone")
    if (_has(t, "phone", "telephone", "phonenumber", "homephone", "cellphone", "mobilephone",
             "workphone", "contact number", "pager", "mobile number", "cell number")
            or whole in ("tel", "mobile", "cell", "cell no", "mobile no", "tel no")):
        return ("telephone number", "redact", "phone")
    if _has(t, "email", "e mail", "email address", "emailaddress"):
        return ("email address", "redact", "email")
    if _has(t, "ssn", "social security", "ss number", "national id", "nationalid", "tax id",
            "itin", "nhs number", "nino") or whole in ("sin", "tin"):
        return ("social security or national ID number", "redact", "ssn")

    # 8: medical record numbers and other record identifiers become pseudonyms.
    if _has(t, "mrn", "medical record", "record number", "chart number", "chart no", "chart id",
            "empi", "accession", "barcode", "unit number", "patient number", "health record",
            "case number", "encounter number"):
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
            "zip plus", "postal"):
        return ("ZIP code", "zip3", "zip")
    if _has(t, "address", "addr", "street", "address line", "streetaddress", "homeaddress",
            "city", "town", "village", "municipality", "county", "parish", "borough",
            "precinct", "neighborhood", "neighbourhood", "census tract", "census block",
            "block group", "fips", "geocode", "geohash", "latitude", "longitude",
            "coordinates", "gps", "place of residence", "home location", "hometown",
            "home town", "locality", "suburb", "district", "subdistrict", "township",
            "hamlet", *CITY_WORDS_OTHER_LANGUAGES) \
            or whole in ("lat", "lon", "lng", "long", "residence", "pob", "pob city", "pob town") \
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
            "alias", "nickname", *NAME_WORDS_OTHER_LANGUAGES):
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
    "geburtsname", "madchenname", "maedchenname")
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
    if (payer or qualified_header(header)) and \
            category_values(values, scrubber, strict=rule[2] in ("name", "address", "id")):
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


def person_name_rule(header: str, values: list[str]) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column named for the person's own first, last or given
    name, or for a relative, a household member or a contact, unless every value is a category
    word or a number. Unlike name_hint_rule, the column cannot be kept."""
    t = [x for x in column_tokens(header) if not x.isdigit()]
    if not t:
        return None
    vals = _shape_values(values)
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
    return bool(NUMBER.fullmatch(v.strip()))


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
hemizygous germline somatic copy gain luminal basal enriched claudin
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
        self.loinc = "loinc" in ts
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
_AA1 = "[ACDEFGHIKLMNPQRSTVWY]"
_AA3 = "(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter|Sec|Pyl|Xaa)"
_AA = f"(?:{_AA3}|{_AA1})"
_REFSEQ = r"(?:AC|AP|NC|NG|NM|NP|NR|NT|NW|NZ|XM|XP|XR|YP|WP)_\d{6,9}(?:\.\d{1,3})?"
_ENSEMBL = r"ENS(?:[A-Z]{3})?[EFGPRT]\d{11}(?:\.\d{1,3})?"
_POS = r"[-*]?\d+(?:[+-]\d+)?"
_NUC = "[ACGTUNacgtun]"
_HGVS_NUC = (rf"[cgmnor]\.{_POS}(?:_{_POS})?(?:{_NUC}*>{_NUC}+|(?:del|dup|inv)(?:{_NUC}+|\d+)?"
             rf"|(?:ins|delins){_NUC}+|=|{_NUC}*\[\d+\])")
_P_CHANGE = (rf"{_AA}\d+(?:_{_AA}\d+)?(?:{_AA}|\*|=|\?|fs(?:\*|Ter|X)?\d*|del|dup|(?:ins|delins){_AA}+"
             rf"|ext(?:\*|Ter)?-?\d*)")
_HGVS_PROT = rf"p\.(?:\({_P_CHANGE}\)|{_P_CHANGE}|=|\?|0\??|\(=\))"
_HGVS_REF = (rf"(?:(?:{_REFSEQ}|{_ENSEMBL}|LRG_\d+(?:t\d+|p\d+)?|chr(?:[1-9]|1\d|2[0-2]|X|Y|MT?))"
             r"(?:\([A-Z0-9-]{1,15}\))?:)?")
ICD10_DOTTED = re.compile(r"[A-Z]\d[0-9A-Z]\.(?=[0-9A-Z]{0,3}\d)[0-9A-Z]{1,4}", re.I)
ICD9_DOTTED = re.compile(r"V\d{2}\.\d{1,2}|E\d{3}\.\d", re.I)
ICD_PLAIN = re.compile(r"[A-Z]\d[0-9A-Z](?:\d{1,3}[0-9A-Z]?)?|V\d{2}|E\d{3}", re.I)
LOINC = re.compile(r"(\d{1,7})-(\d)")
ATC = re.compile(r"[ABCDGHJLMNPRSV]\d{2}(?:[A-Z](?:[A-Z](?:\d{2})?)?)?", re.I)
RSID = re.compile(r"rs\d{1,12}", re.I)
ENSEMBL = re.compile(_ENSEMBL)
REFSEQ = re.compile(_REFSEQ)
HGVS = re.compile(_HGVS_REF + rf"(?:{_HGVS_NUC}|{_HGVS_PROT})")
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
ANYWHERE_CODES = (ICD10_DOTTED, ICD9_DOTTED, RSID, ENSEMBL, REFSEQ, HGVS, STAGE_PREFIXED, GRADE,
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


def code_grammar(value: str, ctx: ColumnContext) -> bool:
    """True when the whole value is a code of a closed grammar (see the section comment)."""
    s = _plain(value)
    if not s or any(rx.fullmatch(s) for rx in ANYWHERE_CODES) or loinc_code(s):
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
        allowed = {"code"} | ({"date"} if ctx.loinc and loinc_code(value) else set())
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
    numeric = None
    cells = [v.strip() for v in values if v.strip() and v.strip() not in TOOL_PLACEHOLDERS]
    nums = [n for n in (number_like(v) for v in cells) if n is not None]
    if not bad and nums and not all(is_number(v) for v in cells):
        shape = value_shape_rule(header, nums, reference_year)
        rule = None if shape else number_rule(header, cells, reference_year)
        if shape:
            numeric = (shape[0], "redact")
        elif upstream.is_high_cardinality_numeric(nums) and not measurement_header(header):
            numeric = ("unique numbers (possible record or account number)", "redact")
        elif rule:
            numeric = (rule[0], rule[1])
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
    if check["names"]:
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
# numbers and leaves the decision to the person.
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
""".split())
# Words that make a number column a list of identifiers whatever else it says ("Lab No", "Sample
# ID", "Visit Number"); "number of" is a count.
NUMBER_ID_WORDS = frozenset("""
id ids identifier identifiers uid uuid guid no nr nbr num nummer numero ref refs reference key keys
code codes link linkage token tag tags file files folder dossier record records chart registry
register registration reg accession barcode serial account acct mrn mbi seq sequence fallnummer
""".split())


def measurement_header(header: str) -> bool:
    """True for a column name that says its numbers are measurements: a lab, a vital sign, a
    count, a score, a dose, a unit, money or a duration ("WBC", "Heart Rate", "Steps", "Total
    Cost", "Dose mg", "Number of Visits", "HbA1c (%)"), and no word that says identifier ("Lab
    No", "Sample ID")."""
    t = column_tokens(header)
    ts = set(t)
    raw = str(header)
    count_phrase = _has(t, "number of", "no of", "num of", "count of", "n of", "amount of")
    if ts & NUMBER_ID_WORDS and not count_phrase:
        return False
    if "number" in ts and not count_phrase:
        return False
    compact = re.sub(r"[^a-z0-9]", "", raw.lower())
    return bool(count_phrase or ts & MEASUREMENT_WORDS or "%" in raw or _unit_in_brackets(raw)
                or any(w in compact for w in ("spo2", "sao2", "fio2", "pao2", "paco2", "etco2", "o2sat",
                                              "hba1c", "egfr", "pco2", "po2")))


TIME_UNITS = _phrases("""y|yr|yrs|year|years|mo|mos|month|months|wk|wks|week|weeks|d|day|days|h|hr|hrs|
hour|hours|min|mins|minute|minutes|s|sec|second|seconds|ms|msec""")


def _unit_in_brackets(raw: str) -> bool:
    """A unit of measurement in brackets ("(mg/dL)", "[kg]"); a unit of time ("(years)", "[y]")
    does not count, because ages are written in it."""
    for m in re.finditer(r"[(\[]\s*([^)\]]{1,20})\s*[)\]]", raw):
        unit = fold(m.group(1))
        if unit in UNITS and unit not in TIME_UNITS:
            return True
    return False


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


TIME_UNIT = re.compile(r"(?i)\s*(\d{1,6}(?:\.\d+)?)\s*(y|yr|yrs|years?|yo|y/o|mo|mos|mon|mths?|months?|wk|wks"
                       r"|weeks?|d|dy|dys|days?)\.?")


def _age_years_of_value(v: str) -> float | None:
    """The age in years of a value that is a whole number of up to three digits ("95", "95.0"),
    or a number with a unit of time ("95 y", "1140 mo", "34700 days"); None for anything else."""
    s = _plain(v)
    m = re.fullmatch(r"(\d{1,3})(?:\.0+)?", s)
    if m:
        return float(m.group(1))
    m = TIME_UNIT.fullmatch(s)
    if m:
        unit = m.group(2).lower()
        factor = 365.25 if unit == "d" else (_unit_factor(unit) or 1.0)
        return float(m.group(1)) / factor
    return None


def number_rule(header: str, values: list[str], reference_year: int) -> tuple[str, str, str, int] | None:
    """(finding, action, phi type, cells) for a column whose numbers the script cannot verify as
    measurements (see the section comment). `values` are the column's cells that are not blank
    or missing-value words; only those that read as numbers are judged. None when they are
    measurements."""
    vals = [v.strip() for v in values if v.strip() and v.strip() not in TOOL_PLACEHOLDERS
            and not TOOL_OUTPUT.fullmatch(v.strip()) and fold(v) not in MISSING_PHRASES]
    nums = [(v, number_like(v)) for v in vals]
    nums = [(v, n) for v, n in nums if n is not None and not BLOOD_PRESSURE.fullmatch(_plain(v))]
    if not nums:
        return None
    total = len(nums)
    measurement = measurement_header(header)
    digits = [_integer_digits(n) for _, n in nums]
    whole = [d for d in digits if d is not None]
    # Dates written as whole numbers in an order the value rules do not read (YYMMDD, 3262017).
    if len(whole) == total and len(set(whole)) >= 3 and all(_packed_date(d, reference_year) for d in whole):
        return (f"whole numbers shaped like dates with no separator in {total} cells (possible dates)",
                "redact", "date", total)
    # Excel date and time serials ("44269.4375").
    serial = [n for _, n in nums if re.fullmatch(r"\d{5}\.\d+", n)
              and EXCEL_DATE_RANGE[0] <= int(n.split(".")[0]) <= EXCEL_DATE_RANGE[1]]
    if not measurement and len(serial) >= 0.8 * total and any(_integer_digits(n) is None for n in serial):
        return (f"decimal numbers shaped like Excel date and time serials in {len(serial)} of {total} cells "
                "(possible dates)", "redact", "date", len(serial))
    # Record numbers: whole numbers of four or more digits, or with a leading zero, that are not
    # all years. A leading zero marks a code under any column name.
    long_ = [d for d in whole if len(d) >= 4]
    zero = [d for d in whole if len(d) >= 4 and d.startswith("0")]
    years = all(1880 <= int(d) <= reference_year + 10 and len(d) == 4 for d in whole) and len(whole) == total
    if long_ and len(long_) >= 0.5 * total and not years and (not measurement or len(zero) >= 0.5 * total):
        five = sum(1 for d in long_ if len(d) >= 5)
        what = "five or more digits" if five >= len(long_) / 2 else "four or more digits"
        return (f"whole numbers of {what} in {len(long_)} of {total} cells under a column name that names "
                "no measurement (possible record numbers, account numbers, ZIP codes or dates written as "
                "numbers)", "pseudonym_id", "id", len(long_))
    # Ages: whole numbers up to 125 (or a number with a unit of time) with some over 89.
    if not measurement:
        ages = [_age_years_of_value(v) for v, _ in nums]
        if all(a is not None for a in ages) and all(a <= 125 for a in ages):
            over = sum(1 for a in ages if a >= 90)
            if over:
                return (f"whole numbers up to 125, {over} of them over 89, under a column name that names no "
                        "measurement (possible ages)", "age", "age", over)
    return None


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
            "max": max(abs(x) for x in nums), "cells": n}


def coordinate_pairs(columns: list[tuple[int, list[str]]]) -> dict[int, int]:
    """Column positions (and cell counts) of adjacent columns shaped like latitude and
    longitude: decimal numbers within +-90 next to decimal numbers within +-180, both
    with three or more decimal places, or with two when the second column reaches past
    +-90 with one sign (west or east of the 90th meridian). One of the two must reach
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
                               or lon["beyond_90"] and lon["one_sign"]):
                found[i], found[j] = a["cells"], b["cells"]
                break
    return found


def header_identifier_kinds(header: str, scrubber: Scrubber) -> list[str]:
    """The identifier patterns in a header cell. A labelled name ("Patient Key", "Mother Maiden")
    is the shape of most column names, so it counts only with a colon or an equals sign after the
    label ("Patient: Okafor")."""
    h = str(header).strip()
    kinds = scrubber.find(h) if h else []
    return [k for k in kinds if k != "name" or re.search(r"[:=]", h)]


def header_looks_like_value(header: str, scrubber: Scrubber) -> bool:
    h = str(header).strip()
    return bool(h) and (is_number(h) or len(h) > 80 or bool(header_identifier_kinds(h, scrubber))
                        or header_name_like(h))


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
        if low in HEADER_WORDS() or _vocabulary_word(low) or _is_age_token(low) or _age_word_token(low):
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


def check_header_row(headers: list[str], scrubber: Scrubber) -> set[int]:
    """The positions of header cells that look like a value or a name, which the plan and the
    report withhold and the output renames column_N. Refuses a header row that holds an
    identifier pattern in any cell (an email, a phone or ID number, a date: a patient's record
    read as the header row, or column names that carry identifiers), or in which a third of the
    cells look like values or names. The message names counts only."""
    patterned = [i for i, h in enumerate(headers, start=1) if header_identifier_kinds(h, scrubber)]
    if patterned:
        raise UsageError(
            f"the first row looks like data or carries identifiers: {len(patterned)} of {len(headers)} "
            "header cells are shaped like an identifier (an email or web address, a phone, ID or record "
            "number, a date, ...). If the first row is data, add a header row; if the column names "
            "themselves carry identifiers, rename those columns. Then run again.")
    looks = {i for i, h in enumerate(headers, start=1) if header_looks_like_value(h, scrubber)}
    if len(looks) >= max(2, (len(headers) + 2) // 3):
        raise UsageError(
            f"the first row looks like data rather than column names ({len(looks)} of "
            f"{len(headers)} header cells look like values or names). Add a header row and run again.")
    return looks


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
                or person_name_rule(col, nonempty))
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
                d.update(kind="unverified", finding=f"values: {check['numeric'][0]}",
                         action=check["numeric"][1], phi_type="id")
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
            elif all(is_number(v) for v in present) and numbers:
                # Fail closed on numbers too: record numbers that repeat, dates and ZIP codes
                # written as numbers and ages have no shape that tells them from a measurement.
                d.update(kind="unverified", finding=f"values: {numbers[0]}", action=numbers[1],
                         phi_type=numbers[2])
            elif all(is_number(v) for v in present):
                d.update(kind="none", action="keep", phi_type=None, verified=True,
                         finding="numbers verified as measurements (decimals, whole numbers of up to three "
                                 "digits, or longer ones under a column name that names a measurement)")
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
    unvouched = [(d["index"], [str(row.get(d["column"], "") or "") for row in data])
                 for d in decisions if d["kind"] == "none" and d["action"] == "keep"]
    pairs = coordinate_pairs(unvouched)
    for d in decisions:
        if d["index"] in pairs:
            d.update(kind="uncertain", action="redact", phi_type="geo", verified=False,
                     finding="values: decimal numbers shaped like latitude and longitude "
                             "(with the column next to it)")

    by_name = {str(d["column"]): d for d in decisions}
    by_index = {f"#{d['index']}": d for d in decisions}

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


def to_year(v: str, scrubber: Scrubber) -> str:
    s = v.strip()
    # 20210314, 20210314T0930 and a year and month written as one number, 202103.
    m = re.fullmatch(YEAR4 + r"(?:0[1-9]|1[0-2])(?:(?:0[1-9]|[12]\d|3[01])(?:T?\d{4,6})?)?", s)
    if m:
        return s[:4]
    years = set(_years_in(s))
    if len(years) == 1:
        return years.pop()
    if re.search(r"\d", s) or s.lower() not in MISSING_VALUES:
        return "[DATE]"  # no single year to keep, or text that is not a missing-value word
    return v


def birth(v: str, scrubber: Scrubber, reference_year: int) -> str:
    return cap_old_year(to_year(v, scrubber), reference_year)


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
    (re.compile(r"y|yr|yrs|years?|yo|y/o|yoa|ys|jahre|jahren|anos|anni|jaar|roky"), 1.0),
    (re.compile(r"mo|mos|mon|mths?|months?|monate|monaten|meses|mois|mesi|maanden|manader"), 12.0),
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
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([A-Za-z]+)?", v):
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
岁 歲 才 세 살 лет год года سنة سنوات שנים वर्ष साल ปี ετών ετη
""".split())


def age_text(v: str) -> bool:
    """True for a value an age column may hold: numbers with units of time, ranges, comparators,
    age words ("ninety-two", "infant") and missing-value words; not a name or a place."""
    s = _plain(v)
    if not s or fold(s) in MISSING_PHRASES or s in CASELESS_MISSING or AGE_WORD_RX.search(s) \
            or TOOL_OUTPUT.fullmatch(s) or s in TOOL_PLACEHOLDERS:
        return True
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).casefold()
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
                nv = cap_old_year(to_year(v, scrubber), reference_year)
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
    for i, vals in shape_checked:
        shape = value_shape_rule(headers[i - 1], vals, reference_year)
        if shape:
            shapes[i] = (shape[0], shape[3])
            continue
        check = verify_column(headers[i - 1], vals, reference_year, ctxs[i], own_output=decisions is None)
        numbers = number_rule(headers[i - 1], vals, reference_year)
        if check["unverified"]:
            shapes[i] = (residual_text_finding(check), check["cells"])
        elif check["numeric"]:
            shapes[i] = (check["numeric"][0], sum(1 for v in vals if number_like(v)))
        elif numbers:
            shapes[i] = (numbers[0], numbers[3])
    pairs = coordinate_pairs(shape_checked)
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
    return f"#{d['index']} (name withheld)" if d["index"] in withheld else str(d["column"])


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
        print("  or measurements, with no names, places, dates, ages over 89, record or account numbers,")
        print("  contact details or other identifiers.")
    free = [d for d in decisions if d["free_text"] and d["action"] != "keep"]
    if free:
        print("\n  Free text, redacted and never kept (a name inside a sentence has no pattern to find): "
              + names(free))
    if withheld:
        print(f"\n  Column names withheld because they look like values or names: "
              + ", ".join(f"#{i}" for i in sorted(withheld))
              + "; the output names them " + ", ".join(f"column_{i}" for i in sorted(withheld)) + ".")
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
            and d["action"] != "keep" and not d["forced_redaction"]]


def load_input(path: Path, scrubber: Scrubber, encoding: str | None = None, locale_code: str = "us"):
    if not path.is_file():
        raise UsageError(f"input file not found: {path}")
    data, meta = read_table(path, encoding, locale_code)
    headers = list(meta.get("headers") or [])
    if not headers:
        raise UsageError("the file has no header row")
    refuse_other_separator(headers)
    if not data:
        raise UsageError("the file has a header row but no data rows")
    return data, meta, headers, check_header_row(headers, scrubber)


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
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    head = raw[:4096]
    if head.count(b"\x00") > len(head) // 4:
        kind, suggestion = "UTF-16 text without a byte order mark", "utf-16-le"
    else:
        kind = "an 8-bit encoding such as Windows-1252 or Latin-1, which Excel writes for a plain 'CSV' save"
        suggestion = LOCALE_ENCODINGS.get(locale_code, "cp1252")
    raise UsageError(f"the file is not UTF-8 text; it looks like {kind}. Save it again as 'CSV UTF-8' "
                     "(in Excel: File, Save As, CSV UTF-8) and run again, or rerun with --encoding "
                     f"{suggestion} (or the encoding the person names). No output was written.")


def read_table(path: Path, encoding: str | None = None, locale_code: str = "us"):
    """upstream.load_tabular with the encoding chosen by file_encoding, not upstream's guess."""
    enc = file_encoding(path, encoding, locale_code)
    guess = upstream.detect_encoding
    if enc:
        upstream.detect_encoding = lambda _path: enc
    try:
        return upstream.load_tabular(path)
    finally:
        upstream.detect_encoding = guess


def refuse_other_separator(headers: list[str]) -> None:
    """A file read as one column whose name holds ';', '|' or a tab uses another separator:
    every row would be one long text value. The message names no header, which in a
    pivoted table can be a person's name."""
    if len(headers) == 1 and any(c in str(headers[0]) for c in ";|\t"):
        raise UsageError("the file was read as one column whose name contains ';', '|' or a tab, so "
                         "it uses another column separator. Save it as CSV with commas (or as .tsv "
                         "with tabs) and run again.")


def resolve_locale(args) -> dict:
    if args.locale_file:
        return upstream.load_locale_file(args.locale_file)
    return upstream.load_locale(args.locale or "us")


def cmd_plan(args) -> int:
    locale = resolve_locale(args)
    scrubber = Scrubber(locale, args.reference_year)
    data, meta, headers, withheld = load_input(Path(args.input_file), scrubber, args.encoding,
                                               locale.get("code", "us"))
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
    data, meta, headers, withheld = load_input(input_path, scrubber, args.encoding, locale.get("code", "us"))
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
        "kept_text_note": ("A default run keeps only values it verifies: a measurement (a decimal, a whole "
                           "number of up to three digits, or a longer one under a column name that names "
                           "a measurement), a code, a date reduced to the year, a common category word or "
                           "a state or country name. Columns the person kept with --keep "
                           "(kept_unverified_columns) were not verified. " + KEPT_TEXT_WARNING),
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


def cmd_verify(args) -> int:
    locale = resolve_locale(args)
    scrubber = Scrubber(locale, args.reference_year)
    path = Path(args.input_file)
    if not path.is_file():
        raise UsageError(f"file not found: {path}")
    data, meta = read_table(path, args.encoding, locale.get("code", "us"))
    headers = list(meta.get("headers") or [])
    refuse_other_separator(headers)
    withheld = {i for i, h in enumerate(headers, start=1) if header_looks_like_value(h, scrubber)}
    decisions, used = report_decisions(path, headers, args.report)
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

    for name, help_text in (("plan", "show what would happen to each column; writes nothing"),
                            ("run", "de-identify the file")):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("input_file")
        common(sp)
        sp.add_argument("--keep", action="append", default=[], metavar="COLUMN",
                        help="keep a column the scanner could not vouch for (name or #N); "
                             "identifier patterns inside it are still replaced")
        sp.add_argument("--redact", action="append", default=[], metavar="COLUMN",
                        help="replace every value of a column with [REDACTED] (name or #N)")
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
