#!/usr/bin/env python3
# Copyright 2026 Baranzini Lab, University of California, San Francisco
# SPDX-License-Identifier: Apache-2.0
"""Tests of scripts/safe_harbor.py against a synthetic export.

tests/fixtures/synthetic_18_identifiers.csv holds invented people only: names
made up for this file, phone numbers in the 555-01xx range, social security
numbers in the 9xx area that is never issued, IP addresses and URLs from the
documentation ranges (RFC 5737, RFC 3849, example.org). It carries every one of
the 18 HIPAA Safe Harbor identifier types, and the main test asserts that none
of them is left in the output, in the report, or in what the script prints.

Run with: python3 tests/test_safe_harbor.py   (standard library only, offline)
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "safe_harbor.py"
FIXTURE = HERE / "fixtures" / "synthetic_18_identifiers.csv"
REFERENCE_YEAR = "2026"

# The 18 identifier types of 45 CFR 164.514(b)(2)(i), and the fixture columns
# that carry each one.
SAFE_HARBOR_18 = {
    "A names": ["patient_name", "emergency_contact_name", "employer"],
    "B geographic subdivisions smaller than a state": ["street_address", "city", "county", "zip_code"],
    "C dates and ages over 89": ["date_of_birth", "admission_date", "discharge_date", "date_of_death", "age"],
    "D telephone numbers": ["phone"],
    "E fax numbers": ["fax"],
    "F email addresses": ["email"],
    "G social security numbers": ["ssn"],
    "H medical record numbers": ["mrn"],
    "I health plan beneficiary numbers": ["health_plan_member_id"],
    "J account numbers": ["account_number"],
    "K certificate and license numbers": ["drivers_license"],
    "L vehicle identifiers and license plates": ["vehicle_vin", "license_plate"],
    "M device identifiers and serial numbers": ["device_serial_number"],
    "N web URLs": ["patient_portal_url"],
    "O IP addresses": ["portal_ip_address", "network_origin"],
    "P biometric identifiers": ["fingerprint_template"],
    "Q full-face photographs": ["photo_file"],
    "R any other unique identifying number or code": ["study_badge_code"],
}
# Free text that carries several of the above inside sentences.
TEXT_WITH_IDENTIFIERS = ["clinical_note", "contact_note"]
# Columns that hold no identifier and must come out unchanged.
NOT_IDENTIFIERS = ["state", "sex", "diagnosis_code", "hba1c", "visit_count"]
DATE_COLUMNS = ["admission_date", "discharge_date", "date_of_death"]


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *args], capture_output=True,
                          text=True, cwd=cwd, env=env, timeout=120)


def raw_identifier_strings(rows: list[dict]) -> set[str]:
    """Every raw value of an identifier column, and every word of four or more
    letters in names, places and employers, so a surname alone is caught too."""
    out: set[str] = set()
    for columns in SAFE_HARBOR_18.values():
        for col in columns:
            for row in rows:
                v = row[col].strip()
                if col == "age" or col == "zip_code":
                    continue  # short numbers; checked by their transformed shape below
                if len(v) >= 4:
                    out.add(v)
                if col in ("patient_name", "emergency_contact_name", "employer", "city",
                           "county", "street_address"):
                    out.update(w for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", v)
                               if w.lower() not in ("county", "court", "lane", "hollow", "works"))
    for col in TEXT_WITH_IDENTIFIERS:
        for row in rows:
            out.add(row[col].strip())
    # Names that appear only inside the notes.
    out.update(["Ingrid", "Halvorsen"])
    return out


class SyntheticFixture(unittest.TestCase):
    def test_fixture_covers_all_18_identifier_types(self):
        rows = read_rows(FIXTURE)
        self.assertEqual(len(SAFE_HARBOR_18), 18)
        header = set(rows[0])
        for kind, columns in SAFE_HARBOR_18.items():
            for col in columns:
                self.assertIn(col, header, kind)
                self.assertTrue(any(r[col].strip() for r in rows), f"{kind}: {col} is empty")
        ages = [float(re.match(r"\d+", r["age"]).group()) for r in rows]
        self.assertTrue(any(a > 89 for a in ages), "the fixture needs an age over 89")


class SafeHarborRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))
        cls.out_dir = cls.tmp / "out"
        cls.proc = run("run", str(FIXTURE), "--output-dir", str(cls.out_dir),
                       "--reference-year", REFERENCE_YEAR)
        cls.raw = read_rows(FIXTURE)
        cls.out_file = cls.out_dir / "synthetic_18_identifiers_deidentified.csv"
        cls.report_file = cls.out_dir / "deidentification_report.json"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_run_succeeds_and_writes_only_output_and_report(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertEqual(sorted(p.name for p in self.out_dir.iterdir()),
                         sorted([self.out_file.name, self.report_file.name]))

    def test_no_identifier_remains_in_output(self):
        text = self.out_file.read_text(encoding="utf-8")
        low = text.lower()
        leaked = sorted(s for s in raw_identifier_strings(self.raw) if s.lower() in low)
        self.assertEqual(leaked, [], "raw identifiers found in the de-identified file")

    def test_nothing_raw_is_printed_or_reported(self):
        shown = (self.proc.stdout + self.proc.stderr).lower()
        report = self.report_file.read_text(encoding="utf-8").lower()
        for where, text in (("stdout/stderr", shown), ("report", report)):
            leaked = sorted(s for s in raw_identifier_strings(self.raw) if s.lower() in text)
            self.assertEqual(leaked, [], f"raw identifiers in the {where}")
        # Ages and ZIP codes are short: check that the raw ones are not printed either.
        for row in self.raw:
            for col in ("zip_code",):
                self.assertNotIn(row[col], self.proc.stdout + self.proc.stderr)

    def test_each_identifier_column_is_replaced(self):
        out = read_rows(self.out_file)
        self.assertEqual(len(out), len(self.raw))
        placeholder = re.compile(r"\[[A-Z0-9_]+\]")
        for kind, columns in SAFE_HARBOR_18.items():
            for col in columns:
                for raw_row, out_row in zip(self.raw, out):
                    raw, new = raw_row[col].strip(), out_row[col].strip()
                    if not raw:
                        self.assertEqual(new, "")
                        continue
                    if col != "age":  # ages up to 89 are allowed as they are
                        self.assertNotEqual(new, raw, f"{kind}: {col} kept a raw value")
                    if col == "patient_name":
                        self.assertRegex(new, r"^P\d{4}$")
                    elif col in ("mrn", "study_badge_code"):
                        self.assertRegex(new, r"^ID\d{4}$")
                    elif col in DATE_COLUMNS:
                        self.assertRegex(new, r"^\d{4}$", f"{col} must keep the year only")
                    elif col == "date_of_birth":
                        self.assertRegex(new, r"^(\d{4}|\[90_OR_OLDER\])$")
                    elif col == "zip_code":
                        self.assertRegex(new, r"^\d{3}$")
                    elif col == "age":
                        self.assertRegex(new, r"^(90\+|[1-8]?\d( years)?)$")
                    else:
                        self.assertRegex(new, placeholder, f"{kind}: {col}")

    def test_dates_keep_only_the_year(self):
        out = read_rows(self.out_file)
        expected_admission = ["2024", "2024", "2023", "2022", "2024", "2025"]
        self.assertEqual([r["admission_date"] for r in out], expected_admission)
        self.assertEqual([r["date_of_birth"] for r in out],
                         ["1958", "[90_OR_OLDER]", "1984", "1999", "1972", "1958"])
        month = re.compile(r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")
        for row in out:
            for col in DATE_COLUMNS + ["date_of_birth"]:
                self.assertIsNone(month.search(row[col]), col)

    def test_ages_over_89_are_grouped(self):
        out = read_rows(self.out_file)
        for raw_row, out_row in zip(self.raw, out):
            age = float(re.match(r"\d+", raw_row["age"]).group())
            if age > 89:
                self.assertEqual(out_row["age"], "90+")
            else:
                self.assertEqual(out_row["age"], raw_row["age"])

    def test_zip_codes_keep_three_digits_or_000(self):
        out = read_rows(self.out_file)
        self.assertEqual([r["zip_code"] for r in out], ["941", "000", "000", "941", "606", "941"])

    def test_pseudonyms_are_consistent_for_the_same_person(self):
        out = read_rows(self.out_file)
        # Rows 1 and 6 are two visits of the same invented patient.
        for col in ("patient_name", "mrn", "study_badge_code"):
            self.assertEqual(out[0][col], out[5][col], col)
            self.assertEqual(len({r[col] for r in out}), 5, col)

    def test_non_identifying_columns_are_unchanged(self):
        out = read_rows(self.out_file)
        for col in NOT_IDENTIFIERS:
            self.assertEqual([r[col] for r in out], [r[col] for r in self.raw], col)

    def test_free_text_is_redacted_whole(self):
        out = read_rows(self.out_file)
        for col in TEXT_WITH_IDENTIFIERS:
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)

    def test_report_records_decisions_and_a_clean_residual_check(self):
        report = json.loads(self.report_file.read_text(encoding="utf-8"))
        self.assertTrue(report["residual_check"]["clean"])
        self.assertFalse(report["mapping_written"])
        self.assertEqual(len(report["decisions"]), len(self.raw[0]))
        self.assertIn("spot-check", report["human_review"])

    def test_verify_passes_on_output_and_fails_on_raw_input(self):
        ok = run("verify", str(self.out_file), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("from deidentification_report.json", ok.stdout)
        # Without the report, column actions are guessed from the names and still pass.
        alone = Path(tempfile.mkdtemp(prefix="safe_harbor_test_")) / self.out_file.name
        try:
            shutil.copy(self.out_file, alone)
            guessed = run("verify", str(alone), "--reference-year", REFERENCE_YEAR)
            self.assertEqual(guessed.returncode, 0, guessed.stdout + guessed.stderr)
        finally:
            shutil.rmtree(alone.parent, ignore_errors=True)
        bad = run("verify", str(FIXTURE), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3)
        shown = (bad.stdout + bad.stderr).lower()
        self.assertEqual(sorted(s for s in raw_identifier_strings(self.raw) if s.lower() in shown), [])


class KeepAndRedactRequests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_kept_short_text_is_scrubbed_of_identifiers(self):
        out_dir = self.tmp / "out"
        p = run("run", str(FIXTURE), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR,
                "--keep", "contact_note")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(out_dir / "synthetic_18_identifiers_deidentified.csv")
        notes = [r["contact_note"] for r in out]
        self.assertEqual(notes, ["fax [PHONE] after noon", "portal [URL] only",
                                 "remote login from [IP]", "MRN [ID] on file",
                                 "seen by [NAME]", "home [ADDRESS]"])

    def test_free_text_cannot_be_kept(self):
        out_dir = self.tmp / "out"
        p = run("run", str(FIXTURE), "-o", str(out_dir), "--keep", "clinical_note")
        self.assertEqual(p.returncode, 2)
        self.assertIn("free text", p.stderr)
        self.assertFalse(out_dir.exists() and any(out_dir.iterdir()))

    def test_an_identifier_column_cannot_be_kept(self):
        out_dir = self.tmp / "out"
        for col in ("ssn", "patient_name", "date_of_birth", "zip_code"):
            p = run("run", str(FIXTURE), "-o", str(out_dir), "--keep", col)
            self.assertEqual(p.returncode, 2, col)
            self.assertIn("cannot be kept", p.stderr)
        self.assertFalse(out_dir.exists() and any(out_dir.iterdir()))

    def test_redact_request_wins_over_keep_default(self):
        out_dir = self.tmp / "out"
        p = run("run", str(FIXTURE), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR,
                "--redact", "diagnosis_code", "--redact", "#33")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(out_dir / "synthetic_18_identifiers_deidentified.csv")
        self.assertEqual({r["diagnosis_code"] for r in out}, {"[REDACTED]"})
        self.assertEqual({r["sex"] for r in out}, {"[REDACTED]"})

    def test_mapping_is_optional_restricted_and_kept_apart(self):
        out_dir = self.tmp / "out"
        inside = run("run", str(FIXTURE), "-o", str(out_dir), "--mapping-out", str(out_dir / "mapping.json"))
        self.assertEqual(inside.returncode, 2)
        self.assertIn("outside the output directory", inside.stderr)
        mapping = self.tmp / "restricted" / "mapping.json"
        p = run("run", str(FIXTURE), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR,
                "--mapping-out", str(mapping))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(stat.S_IMODE(mapping.stat().st_mode), 0o600)
        data = json.loads(mapping.read_text(encoding="utf-8"))
        self.assertEqual(data["names"]["Quentin Fairweather"], "P0001")
        self.assertNotIn("Quentin", p.stdout + p.stderr)
        self.assertNotIn("mapping.json", [x.name for x in out_dir.iterdir()])

    def test_a_first_row_of_data_is_refused_without_printing_it(self):
        headerless = self.tmp / "headerless.csv"
        rows = read_rows(FIXTURE)
        with open(headerless, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow([r["patient_name"], r["phone"], r["email"], r["ssn"], r["sex"]])
        p = run("run", str(headerless), "-o", str(self.tmp / "out"))
        self.assertEqual(p.returncode, 2)
        self.assertIn("looks like data", p.stderr)
        for r in rows:
            for col in ("patient_name", "phone", "email", "ssn"):
                self.assertNotIn(r[col], p.stdout + p.stderr)

    def test_unknown_column_in_a_request_is_an_error(self):
        p = run("plan", str(FIXTURE), "--keep", "no_such_column")
        self.assertEqual(p.returncode, 2)
        self.assertIn("no column named", p.stderr)

    def test_plan_writes_nothing_and_prints_no_values(self):
        before = set(os.listdir(self.tmp))
        p = run("plan", str(FIXTURE), cwd=self.tmp)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(set(os.listdir(self.tmp)), before)
        raw = read_rows(FIXTURE)
        shown = (p.stdout + p.stderr).lower()
        self.assertEqual(sorted(s for s in raw_identifier_strings(raw) if s.lower() in shown), [])


class NoNetwork(unittest.TestCase):
    def test_socket_connections_are_disabled_in_process(self):
        code = ("import runpy, socket, sys\n"
                "sys.argv = ['safe_harbor.py', '--help']\n"
                f"sys.path.insert(0, {str(SCRIPT.parent)!r})\n"
                "import safe_harbor\n"
                "for call in (lambda: socket.create_connection(('127.0.0.1', 9)),\n"
                "             lambda: socket.getaddrinfo('localhost', 80),\n"
                "             lambda: socket.socket().connect(('127.0.0.1', 9))):\n"
                "    try:\n"
                "        call()\n"
                "    except OSError as e:\n"
                "        assert 'disabled' in str(e), e\n"
                "    else:\n"
                "        raise SystemExit('a network call was not refused')\n"
                "print('refused')\n")
        p = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("refused", p.stdout)

    def test_scripts_import_no_network_module(self):
        banned = re.compile(r"^\s*(?:import|from)\s+(?:urllib|http|socketserver|ftplib|smtplib|"
                            r"requests|httpx|aiohttp|ssl|xmlrpc|telnetlib|poplib|imaplib)\b", re.M)
        for name in ("safe_harbor.py", "deidentify.py"):
            text = (SCRIPT.parent / name).read_text(encoding="utf-8")
            self.assertIsNone(banned.search(text), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
