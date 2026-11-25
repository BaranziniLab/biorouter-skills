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
    python3 safe_harbor.py run    INPUT --output-dir DIR [--locale us] [--keep COL]
                                  [--redact COL] [--reference-year YYYY]
                                  [--mapping-out FILE]
    python3 safe_harbor.py verify FILE [--locale us] [--reference-year YYYY]

What it does, per the 18 identifiers of 45 CFR 164.514(b)(2), is listed in
references/safe-harbor-mode.md. In short: identifier columns found by name
are replaced (names and record numbers by pseudonyms, dates by their year,
ZIP codes by their first three digits or 000, ages over 89 by "90+", the rest
by [REDACTED]); free text and columns the scanner cannot vouch for are
redacted unless the person asks to keep them; every kept cell is scrubbed of
identifier patterns; and the output is scanned again before it is kept.

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
import csv  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import stat  # noqa: E402
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
    r"|serial(?:\s+(?:number|no\.?|#))?|s/n|device\s+(?:id|serial|number)|udi|imei|vin"
    r"|plate(?:\s+(?:number|no\.?|#))?|passport(?:\s+(?:number|no\.?|#))?"
    r"|case\s+(?:id|number|no\.?)|accession(?:\s+(?:number|no\.?|#))?"
    r"|specimen\s+(?:id|number|no\.?)|identifier|id)"
)
NAME_LABELS = (r"(?:patient|pt|name|full\s+name|contact|spouse|wife|husband|partner|mother"
               r"|father|parent|son|daughter|sibling|brother|sister|guardian|caregiver"
               r"|emergency\s+contact|next\s+of\s+kin|nok|employer)")


def _year_of(m: re.Match) -> str:
    text = m.group(0)
    y = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})", text)
    return y.group(1) if y else "[DATE]"


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
    # An apostrophe may sit inside the local part ("j.o'brien@...").
    ("email", re.compile(r"(?i)(?<![\w.%+-])[a-z0-9._%+-]+(?:'[a-z0-9._%+-]+)*@[a-z0-9.-]+\.[a-z]{2,}(?![\w-])"), "[EMAIL]"),
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
    # Dates without a four-digit year cannot be reduced to one.
    ("date", re.compile(r"(?<![\d/.-])" + DAY + r"([-/.])" + DAY + r"\1\d{2}(?![\d/.-])"), "[DATE]"),
    ("date", re.compile(r"(?i)(?<![\w])" + DAY + r"[-/]" + MONTH + r"[-/]\d{2}(?!\d)"), "[DATE]"),
    ("date", re.compile(r"(?i)(?<![\w])" + DAY + r"(?:st|nd|rd|th)?\s+(?:of\s+)?" + MONTH_NOT_MAY + r"\b\.?"), "[DATE]"),
    ("date", re.compile(r"(?i)(?<![\w])" + MONTH_NOT_MAY + r"\.?\s+" + DAY + r"(?:st|nd|rd|th)?\b"), "[DATE]"),
    # Month/day without a year; "1/2" (a fraction) is left alone.
    ("date", re.compile(r"(?<![\d/.-])(?:(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])|(?:0?[1-9]|1[0-2])/(?:1[3-9]|2\d|3[01]))(?![\d/.-])"), "[DATE]"),
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
    ("name", re.compile(r"(?i:\b" + NAME_LABELS + r")\s*[:=]?\s*(?P<v>[A-Z][a-zA-Z'-]+(?:[\s,]+[A-Z][a-zA-Z'-]+){0,3})"), _keep_label("[NAME]")),
    # Ages over 89.
    ("age", re.compile(r"(?i)\b(?:" + AGE_NUM + "|" + AGE_WORD + r")\s*-?\s*(?:years?(?:[\s-]*old)?|yrs?|y/o|y\.?o\.?|yo)(?![\w])"), _age90),
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
    # Any other unique identifying number or code.
    ("code", re.compile(r"(?<![\d.])\d{9,}(?![\d.])"), _long_number),
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
        # The year after "born" or "DOB" is judged once full dates have become years.
        at = next(i for i, (kind, _, _) in enumerate(PATTERNS) if kind == "phone")
        self.patterns = PATTERNS[:at] + [birth_year_pattern(year)] + PATTERNS[at:] + locale_patterns(locale)

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

    @staticmethod
    def _scrub_number(text: str, found: list[str]) -> tuple[str, list[str]]:
        """A plain number is a measurement, except a compact date, a telephone number
        in international form (+14155550134) or a long ID."""
        s = text.strip()
        if re.fullmatch(YEAR4 + r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])", s):
            found.append("date")
            return s[:4], found
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
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(header))
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
                     "address", "zip", "zipcode", "postcode", "birthplace"}
# "birth" with one of these describes the birth, not its date.
BIRTH_NOT_A_DATE = {"weight", "wt", "length", "len", "height", "order", "rank", "plurality",
                    "outcome", "outcomes", "type", "defect", "defects", "control", "rate",
                    "rates", "count", "counts", "cohort", "mode", "method", "gestation",
                    "gestational", "ga", "injury", "trauma", "asphyxia", "attendant",
                    "certificate", "cert", "hospital", "facility", "sex", "gender", "parity",
                    "spacing", "interval", "complication", "complications", "history", "hx",
                    "status", "season", "circumference", "head", "apgar", "presentation",
                    "route", "delivery", "multiple", "twin", "singleton", "registry", "anomaly",
                    "anomalies", "country", "state", "province", "nationality", "cohort"}
# One-word age columns: ageyrs, agegroup, ageatdx, ...
AGE_TOKEN = re.compile(r"age(?:s|d|yrs?|years?|yo|y|mos?|months?|wks?|weeks?|days?|hrs?|hours?"
                       r"|grp|groups?|cats?|category|categories|bands?|bins?|ranges?|class"
                       r"|brackets?|buckets?|at[a-z]*|dx|adm|onset|death|enrol+|baseline|bl)?")


def _is_age_token(token: str) -> bool:
    return bool(AGE_TOKEN.fullmatch(token))


# Words that name a person or a role wherever they stand in a column name. A column
# named with one holds people, so a category word beside it ("Treatment Physician",
# "Lab Technician", "Physician (Treatment)") never makes its values a category.
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
""".split())
# Words that name a person only as the head of the column name, its last word ("Dept
# Head", "Source Contact", "Event Patient", "Cohort Member"). Before a category word they
# say whose category it is ("Head Injury Type", "Contact Method", "Patient Diagnosis").
HEAD_ROLE_WORDS = frozenset("""
patient pt subject participant member individual person people client resident contact head
lead chief chair principal pi owner holder donor recipient tech user consumer partner
relative child children student monitor sponsor sender receiver surrogate proxy
representative rep delegate driver survivor
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


def person_role_words(tokens: list[str], trailing: frozenset = frozenset()) -> set[str]:
    """The words of a column name that name a person or a role: one of PERSON_ROLE_WORDS
    anywhere, one of HEAD_ROLE_WORDS as the last word (numbers and `trailing` words such
    as "name" after it do not count), and "by" after another word ("Test Ordered By")."""
    found = {t for t in tokens if _role_word(t, PERSON_ROLE_WORDS)}
    found.update(t for t in tokens[1:] if t == "by")
    rest = [t for t in tokens if not t.isdigit()]
    while rest and rest[-1] in trailing:
        rest.pop()
    if rest and _role_word(rest[-1], HEAD_ROLE_WORDS):
        found.add(rest[-1])
    return found


# Words a person's own name column may carry ("Study Patient Name"), as opposed to the
# name of a clinician or another person ("Lab Technician Name").
SELF_WORDS = frozenset({"patient", "patients", "pt", "subject", "subjects", "participant",
                        "participants", "member", "members", "individual", "individuals",
                        "person", "people", "client", "clients", "resident", "residents",
                        "proband", "probands", "respondent", "respondents", "enrollee",
                        "enrolee", "decedent", "interviewee", "donor", "donors", "recipient",
                        "recipients"})
NAME_TRAILING = frozenset({"name", "names", "nm", "initials", "first", "last", "full", "given",
                           "surname", "surnames", "firstname", "lastname", "fullname"})


def name_rule(header: str) -> tuple[str, str, str] | None:
    """(finding, action, phi type) for a column whose name marks a Safe Harbor identifier.

    These are the columns that cannot be kept. The terms are deliberately whole
    words: "ip" (inpatient), "tract" (urinary tract) or "cell" (cell type) are not
    identifiers on their own, and a column of IP addresses is still found by its values.
    """
    t = column_tokens(header)
    if not t:
        return None
    ts = set(t)
    whole = " ".join(t)

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
    birth_word = bool(ts & {"birth", "born"})
    if ts & {"birthplace", "placeofbirth", "birthcity"} or (birth_word and ts & BIRTH_PLACE_WORDS):
        return ("place of birth", "redact", "address")
    if ts & BIRTH_YEAR_TOKENS or _has(t, "birth year", "year of birth", "yob", "yearofbirth",
                                      "birthyear", "year born", "born year", "yr of birth") \
            or (birth_word and ts & YEAR_TOKENS and not (ts & BIRTH_NOT_A_DATE)):
        return ("year of birth", "birth_year", "date")
    if _has(t, "dob", "birthdate", "birthday", "date of birth", "dateofbirth", "birth date",
            "birth dt"):
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
            "hamlet") \
            or whole in ("lat", "lon", "lng", "long", "residence", "pob", "pob city", "pob town"):
        return ("geography smaller than a state", "redact", "address")

    # 1: names of the person, relatives, household members and employers.
    if ts & {"employer", "workplace"} or _has(t, "next of kin", "emergency contact"):
        return ("relative, household member or employer", "redact", "name")
    if whole in RELATIVE_HEADERS:
        return ("relative or contact of the person", "redact", "name")
    if _has(t, "fname", "lname", "mname", "forename", "forenames") or whole == "nm" \
            or ("nm" in ts and ts & NM_PERSON_WORDS):
        return ("name", "pseudonym_name", "name")
    if _has(t, "name", "names", "surname", "firstname", "lastname", "fullname", "middlename",
            "givenname", "familyname", "maidenname", "patientname", "ptname", "initials",
            "alias", "nickname"):
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


def _hints(words: str, finding: str, action: str, phi: str, numbers_are_ids: bool) -> dict:
    return {w: (finding, action, phi, numbers_are_ids) for w in words.split(",")}


# Whole column names that usually hold a person's or a place's name but have other uses
# ("Insured" can be yes or no, "Region" a census region or a brain region). They are
# pseudonymized or redacted by default, like any column the scanner cannot vouch for,
# and the person can keep one with --keep after checking it.
NAME_HINT_HEADERS = {
    **_hints("subject,subjects,member,insured,donor,recipient,resident,policyholder",
             "a person's name or identifier", "pseudonym_name", "name", True),
    **_hints("first,last,given,middle,maiden,first last,last first",
             "a first, last or given name", "pseudonym_name", "name", False),
    **_hints("parent,parents,partner,sibling,siblings,brother,sister,son,daughter,child,"
             "children,relative,relatives,contact,contacts,family,household,friend",
             "a relative's or contact's name", "redact", "name", False),
    **_hints("region,home,place,origin,community,locale",
             "a place smaller than a state", "redact", "address", False),
    **_hints("company,organization,organisation,business,firm,school,college,university",
             "an employer's or a school's name", "redact", "name", False),
}


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
catholic protestant christian muslim islam jewish judaism hindu hinduism buddhist buddhism
sikh atheist agnostic mormon lds baptist methodist lutheran orthodox evangelical presbyterian
episcopalian pentecostal adventist quaker unitarian spiritual nonreligious religious
""".split())
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
)
NOT_CLINICAL = frozenset({"euphemia", "bohemia"})


def _clinical_word(w: str) -> bool:
    if w in NOT_CLINICAL or (w.endswith("itis") and w[-5:-4] in ("a", "y")):
        return False
    return any(len(w) >= n and w.endswith(end) for end, n in CLINICAL_ENDINGS)


# Column names that say what category a value belongs to. Their values are not read as
# names when they also repeat like a category and the name names no person (category_column).
CATEGORY_HEADER_WORDS = frozenset("""
sex gender race ethnicity ethnic ancestry smoking smoker tobacco alcohol drinking status
vital outcome outcomes result results diagnosis diagnoses dx diag drug drugs medication
medications med meds treatment treatments therapy regimen arm procedure procedures test
tests lab labs specimen sample organism pathogen bacteria virus antibiotic condition
conditions disease diseases problem comorbidity comorbidities symptom symptoms allergy
allergies allergen vaccine gene genes protein variant mutation tissue cancer tumor tumour
histology stage grade severity type subtype category class phenotype genotype response
marital language laterality side blood specialty speciality department dept service unit
ward disposition source route modality method indication complication complications event
events adverse toxicity cohort group visit diet education insurance payer biomarker biomarkers
marker markers finding findings impression religion religious faith denomination
""".split())
# "site" says what category its values are only after a word that makes it a body site.
CATEGORY_HEADER_PHRASES = ("primary site", "tumor site", "tumour site", "body site", "anatomic site",
                           "anatomical site", "biopsy site", "injection site", "infection site",
                           "surgical site", "metastatic site", "metastasis site", "lesion site",
                           "cancer site", "disease site")
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


def name_shaped(value: str) -> bool:
    """True for one to four capitalised words ("Alice", "Bob Zeller", "Zeller, Alice",
    "O'Brien", "ZELLER ALICE", "San Francisco") that are not all category words."""
    s = value.strip()
    if not s or PLACEHOLDER.search(s) or s.lower() in MISSING_VALUES or _is_category_value(s):
        return False
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


def category_column(header: str, vals: list[str]) -> bool:
    """True when the column name says what category its values are ("Diagnosis", "Visit
    Type", "Primary Site") and names no person or role, and the values repeat like a
    category. A role anywhere in the name ("Treatment Physician", "Physician (Lab)") or a
    person as its last word ("Event Patient") makes it a column of people, whose names
    repeat across visits as much as any category does."""
    t = column_tokens(header)
    if not (set(t) & CATEGORY_HEADER_WORDS or _has(t, *CATEGORY_HEADER_PHRASES)):
        return False
    if person_role_words(t):
        return False
    distinct = len(set(vals))
    return distinct <= CATEGORY_MAX_DISTINCT or len(vals) >= CATEGORY_MIN_REPEATS * distinct


def name_shape_rule(header: str, values: list[str]) -> tuple[str, str, str, int] | None:
    """(finding, action, phi type, cells) for a text column holding values shaped like
    names of people or places, unless it is a category column (category_column) or a
    state or country column, which Safe Harbor allows."""
    if is_allowed_geography(header):
        return None
    vals = _shape_values(values)
    if not vals or all(is_number(v) for v in vals) or category_column(header, vals):
        return None
    shaped = {v for v in set(vals) if name_shaped(v)}
    if not shaped:
        return None
    return (f"text values shaped like names or places ({len(shaped)} of {len(set(vals))} distinct "
            "values are capitalised words that are not common category words)", "redact", "name",
            sum(1 for v in vals if v in shaped))


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
    toks = set(column_tokens(header))
    if toks & {"years", "yrs", "yr", "yo"}:
        nums = [float(v) for v in vals]
        over = sum(1 for n in nums if n >= 90)
        if over and all(0 <= n <= 125 for n in nums):
            return (f"{over} values over 89 in a column named for years (possible ages)", "age", "age", over)
    # Mostly five digits: a lab count such as a white cell count mixes four and five.
    if all(re.fullmatch(r"\d{4,5}(?:\.0+)?", v) for v in vals):
        five = sum(1 for v in vals if len(v.split(".")[0]) == 5)
        if five >= 0.8 * len(vals):
            return (f"five-digit numbers in {five} of {len(vals)} cells (possible ZIP codes)",
                    "redact", "zip", five)
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


def header_looks_like_value(header: str, scrubber: Scrubber) -> bool:
    h = str(header).strip()
    return bool(h) and (is_number(h) or len(h) > 80 or bool(scrubber.find(h)))


def decide_columns(data: list[dict], headers: list[str], locale: dict, scrubber: Scrubber,
                   keep: set[str], redact: set[str], reference_year: int) -> list[dict]:
    """One decision per column. No cell value goes into a decision."""
    decisions = []
    for i, col in enumerate(headers, start=1):
        values = [str(row.get(col, "") or "") for row in data]
        nonempty = [v for v in values if v.strip()]
        d = {"index": i, "column": col, "kept_on_request": False, "forced_redaction": False}
        # Free text is never kept: a name inside a sentence has no pattern to find. A long
        # value made only of category words ("American Indian or Alaska Native") is not text.
        prose = [v for v in nonempty if not _is_category_value(v)]
        d["free_text"] = bool(prose) and upstream.looks_like_free_text(prose)
        rule = name_rule(col) or locale_name_rule(col, locale)
        if rule:
            finding, action, phi = rule
            d.update(kind="allowed" if phi == "allowed_geography" else "identifier",
                     finding=f"column name: {finding}", action=action, phi_type=phi)
        elif not nonempty:
            d.update(kind="none", finding="empty column", action="keep", phi_type=None)
        else:
            scrubbed = [scrubber.scrub(v) for v in nonempty]
            hits = [found for _, found in scrubbed if found]
            # A cell that is nothing but one identifier (a date, an email, a code).
            whole = [found[0] for out, found in scrubbed
                     if found and (PLACEHOLDER.fullmatch(out.strip())
                                   or re.fullmatch(r"\d{4}", out.strip())
                                   or out.strip() == "90+ years")]
            if whole and len(whole) / len(nonempty) > 0.5:
                phi = max(set(whole), key=whole.count)
                action = {"date": "year", "code": "pseudonym_id", "age": "age"}.get(phi, "redact")
                if phi == "zip" and all(re.fullmatch(r"\s*\d{5}(?:-\d{4})?\s*", v) for v in nonempty):
                    action = "zip3"
                d.update(kind="identifier_values",
                         finding=f"values: {len(whole)} of {len(nonempty)} cells are {phi.replace('_', ' ')} identifiers",
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
            elif upstream.is_high_cardinality_numeric(nonempty):
                d.update(kind="uncertain", finding="unique numbers (possible record or account number)",
                         action="pseudonym_id", phi_type="id")
            elif shape:  # five-digit numbers that repeat: possible ZIP codes
                d.update(kind="uncertain", finding=f"values: {shape[0]}", action=shape[1], phi_type=shape[2])
            elif not all(is_number(v) for v in nonempty) and len(set(nonempty)) >= 2 \
                    and len(set(nonempty)) / len(nonempty) > 0.5:
                d.update(kind="uncertain",
                         finding=f"many distinct text values ({len(set(nonempty))} of {len(nonempty)}): possible names or codes",
                         action="redact", phi_type="unknown")
            elif names := name_shape_rule(col, nonempty):
                d.update(kind="uncertain", finding=f"values: {names[0]}", action=names[1], phi_type=names[2])
            else:
                d.update(kind="none", finding="no identifier found", action="keep", phi_type=None)
        # Text the scanner keeps can still hold a name it has no way to see (lower case,
        # a category word, a single all-capital word); the plan lists these for the person.
        d["text"] = any(not is_number(v) for v in _shape_values(values))
        decisions.append(d)

    # Latitude and longitude under names the rules above do not know.
    unvouched = [(d["index"], [str(row.get(d["column"], "") or "") for row in data])
                 for d in decisions if d["kind"] == "none" and d["action"] == "keep"]
    pairs = coordinate_pairs(unvouched)
    for d in decisions:
        if d["index"] in pairs:
            d.update(kind="uncertain", action="redact", phi_type="geo",
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
        if d["free_text"] and d["kind"] != "allowed":
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
    m = re.fullmatch(YEAR4 + r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?:T?\d{4,6})?", s)
    if m:
        return s[:4]
    years = set(_years_in(s))
    if len(years) == 1:
        return years.pop()
    if re.search(r"\d", s) or s.lower() not in MISSING_VALUES:
        return "[DATE]"  # no single year to keep, or text that is not a missing-value word
    return v


def birth(v: str, scrubber: Scrubber, reference_year: int) -> str:
    y = to_year(v, scrubber)
    if re.fullmatch(r"\d{4}", y) and reference_year - int(y) >= 90:
        return "[90_OR_OLDER]"
    return y


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
    # Single letters other than y are not read as units: "96 M" is more often a sex
    # than months, and an unread unit counts as years, which can only over-group.
    (re.compile(r"y|yr|yrs|years?|yo|yoa|ys"), 1.0),
    (re.compile(r"mo|mos|mon|mths?|months?"), 12.0),
    (re.compile(r"wk|wks|weeks?"), 52.18),
    (re.compile(r"dy|dys|days?"), 365.25),
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


def age_cap(v: str, header: str, scrubber: Scrubber) -> str:
    """90+ for an age over 89 (in any unit, or in words). A range that straddles 90
    ("85-94") is replaced, because it would split the ages over 89."""
    if AGE_WORD_RX.search(v):
        return "90+"
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
                nv = to_year(v, scrubber)
            elif action == "birth_date":
                nv = birth(v, scrubber, reference_year)
            elif action == "birth_year":
                nv = birth(v, scrubber, reference_year)
            elif action == "zip3":
                nv = zip3(v)
            elif action == "age":
                nv = age_cap(v, col, scrubber)
            else:  # keep: scrub identifier patterns out of the cell
                nv = scrubber.scrub(v)[0]
            if nv != v:
                changed[col] += 1
            new[col] = nv
        out_rows.append(new)
    return out_rows, {"names": names.mapping, "ids": ids.mapping}, changed


# ================================================================ residual check
def residual_findings(rows: list[dict], headers: list[str], decisions: list[dict] | None,
                      scrubber: Scrubber, reference_year: int) -> list[dict]:
    """Columns whose output still holds an identifier, with counts. No values."""
    findings = []
    by_col = {d["column"]: d for d in decisions} if decisions else {}
    actions, kept_on_request = {}, set()
    for i, col in enumerate(headers, start=1):
        d = by_col.get(col)
        if d is None:
            rule = name_rule(col)
            actions[i] = rule[1] if rule else "keep"
        else:
            actions[i] = d["action"]
            if d.get("kept_on_request"):
                kept_on_request.add(i)
    # Kept columns (unless the person kept them on request) are also checked by the
    # shape of their values, as the run classified them.
    shape_checked = [(i, [str(row.get(col, "") or "") for row in rows])
                     for i, col in enumerate(headers, start=1)
                     if actions[i] == "keep" and i not in kept_on_request]
    shapes = {i: value_shape_rule(headers[i - 1], vals, reference_year) or name_shape_rule(headers[i - 1], vals)
              for i, vals in shape_checked}
    pairs = coordinate_pairs(shape_checked)
    for i, col in enumerate(headers, start=1):
        action = actions[i]
        counts: dict[str, int] = {}
        if shapes.get(i):
            finding, _, _, cells = shapes[i]
            counts[finding] = cells
        if i in pairs:
            counts["decimal numbers shaped like latitude and longitude"] = pairs[i]
        for row in rows:
            v = str(row.get(col, "") or "").strip()
            if not v or PLACEHOLDER.fullmatch(v):
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
                    if action != "year" and reference_year - int(v) >= 90:
                        problem = "birth year of a person aged 90 or over"
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
                    scan = True
            elif decisions is None and PSEUDONYM.fullmatch(v):
                scan = False  # a pseudonym written by this tool, checked without its report
            else:
                scan = True
            if problem is None and scan:
                kinds = scrubber.find(v)
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
    uncertain = [display_name(d, withheld) for d in decisions if d["kind"] == "uncertain" and d["action"] != "keep"]
    if uncertain:
        print("\n  Redacted or changed because the scanner cannot vouch for them: " + ", ".join(uncertain))
        print("  Keep one only after the person confirms it holds no identifiers (--keep COLUMN).")
    kept = [display_name(d, withheld) for d in decisions if d["action"] == "keep"]
    if kept:
        print("  Kept (identifier patterns inside them are replaced): " + ", ".join(kept))
    text = kept_text_columns(decisions)
    if text:
        print("  Kept text the scanner cannot fully check for names (a name in lower case, a short")
        print("  all-capital name, any name under a category column such as diagnosis, or a place")
        print("  under a state or country column): " + ", ".join(display_name(d, withheld) for d in text))
        print("  Ask the person to confirm these hold no names, places or other identifiers.")


def kept_text_columns(decisions: list[dict]) -> list[dict]:
    """Kept columns holding text, including state and country columns: their values are
    not checked for the shape of a name or a place, so the person confirms each one."""
    return [d for d in decisions if d["action"] == "keep" and d.get("text")]


def load_input(path: Path, scrubber: Scrubber):
    if not path.is_file():
        raise UsageError(f"input file not found: {path}")
    data, meta = upstream.load_tabular(path)
    headers = list(meta.get("headers") or [])
    if not headers:
        raise UsageError("the file has no header row")
    refuse_other_separator(headers)
    if not data:
        raise UsageError("the file has a header row but no data rows")
    looks = {i for i, h in enumerate(headers, start=1) if header_looks_like_value(h, scrubber)}
    if len(looks) >= max(2, (len(headers) + 2) // 3):
        raise UsageError(
            f"the first row looks like data rather than column names ({len(looks)} of "
            f"{len(headers)} header cells look like values). Add a header row and run again.")
    return data, meta, headers, looks


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
    data, meta, headers, withheld = load_input(Path(args.input_file), scrubber)
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
    data, meta, headers, withheld = load_input(input_path, scrubber)
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
             "text": d["text"], "cells_changed": changed.get(d["column"], 0)}
            for d in decisions
        ],
        "residual_check": {
            "clean": not residual,
            "findings": [{**f, "column": None if f["index"] in withheld else f["column"]} for f in residual],
        },
        "kept_text_columns": [
            {"index": d["index"], "column": None if d["index"] in withheld else d["column"],
             "kept_on_request": d["kept_on_request"]}
            for d in kept_text_columns(decisions)
        ],
        "kept_text_note": ("Kept text columns can hold names the scanner cannot see (lower case, a short "
                           "all-capital name, a name under a category column, a place under a state "
                           "or country column); the person confirms each one holds no identifiers."),
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
    text = kept_text_columns(decisions)
    if text:
        print(f"Kept text columns the person must confirm hold no names or places ({len(text)}): "
              + ", ".join(display_name(d, withheld) for d in text))
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
    data, meta = upstream.load_tabular(path)
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
