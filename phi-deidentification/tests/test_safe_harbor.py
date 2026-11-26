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


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


class NamesAndShapesTheListMisses(unittest.TestCase):
    """Columns whose names are not in the name list, or carry no name at all, found
    by a name variant or by the shape of their values (review of 2026-11-25)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict]]:
        out_dir = self.tmp / "out"
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified.csv"
        return p, (read_rows(out) if out.exists() else [])

    def test_birth_year_and_age_name_variants(self):
        header = ["born", "byear", "birth_yr", "yr_birth", "year_born", "ageyrs", "age_group",
                  "patient_age_years", "age_days", "age_yrs", "sex"]
        rows = [["1930", "1930", "1930", "1930", "1930", "96", "96", "96", "35000", "ninety-two", "F"],
                ["1955", "1955", "1955", "1955", "1955", "71", "70-79", "71", "26000", "71", "M"],
                ["1980", "1980", "1980", "1980", "1980", "46", "85-94", "46", "17000", "46", "F"],
                ["1962", "1962", "1962", "1962", "1962", "64", "90-94", "64", "23400", "64", "M"]]
        p, out = self.run_file(write_csv(self.tmp / "variants.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in header[:5]:
            self.assertEqual([r[col] for r in out], ["[90_OR_OLDER]", "1955", "1980", "1962"], col)
        for col in ("ageyrs", "patient_age_years", "age_yrs"):
            self.assertEqual([r[col] for r in out], ["90+", "71", "46", "64"], col)
        # A group that straddles 90 would split the ages over 89; a group above 89 is 90+.
        self.assertEqual([r["age_group"] for r in out], ["90+", "70-79", "[REDACTED]", "90+"])
        self.assertEqual([r["age_days"] for r in out], ["90+", "26000", "17000", "23400"])
        self.assertEqual([r["sex"] for r in out], ["F", "M", "F", "M"])

    def test_unnamed_number_columns_shaped_like_identifiers(self):
        header = ["a", "b", "c", "d", "e"]
        rows = [["94110", "37.7749", "-122.4194", "1930", "6.1"],
                ["94117", "37.7694", "-122.4862", "1955", "7.2"],
                ["94110", "37.7849", "-122.4094", "1980", "5.9"],
                ["60614", "41.9214", "-87.6513", "1962", "6.8"]]
        raw = write_csv(self.tmp / "unnamed.csv", header, rows)
        p, out = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("possible ZIP codes", p.stdout)
        self.assertIn("latitude and longitude", p.stdout)
        for col in ("a", "b", "c"):
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        self.assertEqual([r["d"] for r in out], ["[90_OR_OLDER]", "1955", "1980", "1962"])
        self.assertEqual([r["e"] for r in out], ["6.1", "7.2", "5.9", "6.8"])
        # The check does the same on a file it has no report for.
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        for value in ("94110", "37.7749", "122.4194", "1930"):
            self.assertNotIn(value, bad.stdout + bad.stderr)

    def test_ordinary_number_columns_are_kept(self):
        header = ["weight_kg", "bmi", "glucose", "wbc", "year_of_diagnosis", "birth_weight_g",
                  "gestational_age_weeks", "propensity", "iptw", "zscore_a", "zscore_b", "birth_order"]
        rows = [["70.5", "24.13", "105", "10500", "2015", "3400", "38", "0.1234", "1.2345", "-1.234", "0.567", "1"],
                ["82.3", "27.88", "98", "7200", "2018", "2900", "36", "0.5671", "1.8765", "0.456", "-1.123", "2"],
                ["65.1", "22.40", "140", "11200", "2020", "3650", "40", "0.3345", "2.4567", "1.789", "0.234", "1"],
                ["90.2", "30.05", "88", "6400", "2016", "3100", "39", "0.8812", "1.1111", "-0.345", "2.011", "3"]]
        p, out = self.run_file(write_csv(self.tmp / "ordinary.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)

    def test_kept_text_loses_these_identifier_forms(self):
        values = ["+14155550134", "MR# 99123", "Hospital #A-998", "ID 4482113", "born in 1931",
                  "DOB 1930", "born 1975", "ninety-three yo", "93 years old", "aged 94",
                  "lat 37.7749", "37.7749, -122.4194", "ENSG00000141510 and rs12345"]
        raw = write_csv(self.tmp / "kept.csv", ["ref", "sex"], [[v, "F"] for v in values])
        p, out = self.run_file(raw, "--keep", "ref")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ref"] for r in out], [
            "[PHONE]", "MR# [ID]", "Hospital #[ID]", "ID [ID]", "born in [90_OR_OLDER]",
            "DOB [90_OR_OLDER]", "born 1975", "90+ years", "90+ years", "aged 90+",
            "lat [GEO]", "[GEO]", "ENSG00000141510 and rs12345"])

    def test_scrubbing_twice_changes_nothing(self):
        # The residual check scans the output with the same patterns; a replacement that
        # matched again ("aged 94" -> "aged 90+" -> "aged 90++") failed every such run.
        code = (f"import sys\nsys.path.insert(0, {str(SCRIPT.parent)!r})\n"
                "import safe_harbor as s, deidentify as u\n"
                "sc = s.Scrubber(u.load_locale('us'), 2026)\n"
                "cases = ['aged 94', 'age: 96', '93 years old', 'aged ninety-two', 'DOB 03/04/1930',\n"
                "         'MR# 99123', '+14155550134', '37.7749, -122.4194', 'Boston, MA 02134',\n"
                "         'seen by Dr. Halvorsen on 2024-03-05', 'call (415) 555-0134',\n"
                "         '92 y/o female', 'a 92F with CHF', 'pt is 91', 'in her 90s', 'nonagenarian',\n"
                "         \"j.o'brien+clinic@uni-x.ac.uk\", 'ss# 123 45 6789', 'Seen on 2021-03',\n"
                "         '2021 Mar', '14 mars 2021', 'Seen 14/3', 'Instagram: jdoe', 'jdoe#1234',\n"
                "         'u/jdoe', 'Patient: 林子涵', 'Dr. 박지훈']\n"
                "again = [c for c in cases if sc.find(sc.scrub(c)[0])]\n"
                "print('again:', again)\n"
                "raise SystemExit(1 if again else 0)\n")
        p = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_text_in_a_date_column_is_replaced_unless_it_says_missing(self):
        raw = write_csv(self.tmp / "dates.csv", ["birth_date", "sex"],
                        [["Fresno", "F"], ["unknown", "M"], ["1984-02-03", "F"], ["", "M"]])
        p, out = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["birth_date"] for r in out], ["[DATE]", "unknown", "1984", ""])

    def test_the_passed_message_says_it_is_a_pattern_check(self):
        p, _ = self.run_file(FIXTURE)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("pattern check, not proof", p.stdout)

    def test_kept_text_loses_age_email_and_ssn_shorthand(self):
        values = ["92 y/o female", "a 92F with CHF", "pt is 91", "in her 90s", "nonagenarian",
                  "j.o'brien+clinic@uni-x.ac.uk", "ss# 123 45 6789",
                  # Not ages, and left alone: a temperature, a saturation, a weight.
                  "temp 98F", "sats in the 90s", "he is 95 kg"]
        raw = write_csv(self.tmp / "shorthand.csv", ["ref", "sex"], [[v, "F"] for v in values])
        p, out = self.run_file(raw, "--keep", "ref")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ref"] for r in out], [
            "90+ years female", "a 90+F with CHF", "pt is 90+", "in her 90+", "[90_OR_OLDER]",
            "[EMAIL]", "ss# [SSN]", "temp 98F", "sats in the 90s", "he is 95 kg"])


class NamesUnderUnlistedHeaders(unittest.TestCase):
    """Names and places under column names the first rules did not know, with values
    that repeat across visits, so the distinct-values rule never fires (second review
    of 2026-11-25). Every name and place here is invented."""

    PEOPLE = [("Alice", "Zeller", "Bob Zeller", "Fresno", "Bolinas", "Fatima Zeller"),
              ("Odile", "Varga", "Imre Varga", "Tulare", "Inverness", "Hajna Varga"),
              ("Kenji", "Moreau", "Lise Moreau", "Visalia", "Olema", "Noor Moreau")]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def raw_strings(self) -> set[str]:
        out = set()
        for person in self.PEOPLE:
            for v in person:
                out.update(w for w in v.split() if len(w) >= 4)
        return out

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict], Path]:
        out_dir = self.tmp / "out"
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified.csv"
        return p, (read_rows(out) if out.exists() else []), out_dir / "deidentification_report.json"

    def test_person_relative_and_place_column_names(self):
        header = ["First", "Last", "Spouse", "Hometown", "Suburb", "Participant", "Subject", "Proband",
                  "Individual", "Client", "Mother", "Guardian", "Fname", "Nm", "Pt Nm", "Given",
                  "Family", "Locality", "District", "POB", "Company", "Contact", "sex"]
        rows = []
        for i in range(100):
            f, last, spouse, town, suburb, mother = self.PEOPLE[i % 3]
            full = f"{f} {last}"
            rows.append([f, last, spouse, town, suburb, full, full, full, full, full, mother, spouse,
                         f, full, full, f, last, suburb, suburb, town, f"{last} Farms", spouse,
                         "F" if i % 2 else "M"])
        p, out, report = self.run_file(write_csv(self.tmp / "longitudinal.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = (self.tmp / "out" / "longitudinal_deidentified.csv").read_text(encoding="utf-8")
        shown = p.stdout + p.stderr + report.read_text(encoding="utf-8")
        for s in sorted(self.raw_strings()):
            self.assertNotIn(s, text, "raw name or place in the output")
            self.assertNotIn(s, shown, "raw name or place printed or reported")
        for col in ("First", "Last", "Participant", "Subject", "Proband", "Individual", "Client",
                    "Fname", "Nm", "Pt Nm", "Given"):
            self.assertTrue(all(re.fullmatch(r"P\d{4}", r[col]) for r in out), col)
        for col in ("Spouse", "Hometown", "Suburb", "Mother", "Guardian", "Family", "Locality",
                    "District", "POB", "Company", "Contact"):
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])
        # Rows of one person keep one pseudonym.
        self.assertEqual(out[0]["Participant"], out[3]["Participant"])

    def test_unambiguous_names_cannot_be_kept_and_ambiguous_ones_can(self):
        header = ["Mother", "Spouse", "Hometown", "Subject", "Insured", "Children", "wavelength_nm", "sex"]
        rows = [[p[5], p[2], p[3], f"{p[0]} {p[1]}", "Yes" if i % 2 else "No", str(i % 4), "532",
                 "F" if i % 2 else "M"] for i, p in enumerate(self.PEOPLE * 10)]
        raw = write_csv(self.tmp / "kinds.csv", header, rows)
        for col in ("Mother", "Spouse", "Hometown"):
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(all(re.fullmatch(r"P\d{4}", r["Subject"]) for r in out))
        # A yes/no column and counts under such a name are kept as they are.
        for i, col in enumerate(header):
            if col in ("Insured", "Children", "wavelength_nm", "sex"):
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        kept = run("plan", str(raw), "--keep", "Subject")
        self.assertEqual(kept.returncode, 0, kept.stderr)
        self.assertIn("[kept on request]", kept.stdout)

    def test_values_shaped_like_names_under_unknown_column_names(self):
        header = ["x1", "x2", "x3", "x4", "diagnosis", "race", "note", "code"]
        rows = []
        for i in range(60):
            f, last, _, town, _, _ = self.PEOPLE[i % 3]
            rows.append([f"{f} {last}", town, f"{last.upper()}, {f.upper()}", f"{last}, {f}",
                         ["Asthma", "Heart Failure", "COPD"][i % 3], ["White", "Asian", "Black or African American"][i % 3],
                         "ok" if i % 2 else "repeat", ["E11.9", "J45.909", "I50.9"][i % 3]])
        raw = write_csv(self.tmp / "unknown.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("shaped like names or places", p.stdout)
        # Fail closed (round 1 of 2026-11-25): a race column and ICD-10 codes are verified and
        # kept; a diagnosis written in words and a note are text the script cannot verify, so
        # they are redacted until the person keeps them (this test kept them before).
        for col in ("x1", "x2", "x3", "x4", "diagnosis", "note"):
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        for col in ("race", "code"):
            i = header.index(col)
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertIn("Need the person's decision", p.stdout)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual([d["column"] for d in data["kept_text_columns"]], ["race", "code"])
        self.assertEqual([d["column"] for d in data["columns_needing_decision"]],
                         ["x1", "x2", "x3", "x4", "diagnosis", "note"])
        # Kept on the person's word, the two are scrubbed and named with the warning.
        p, out, report = self.run_file(raw, "--keep", "diagnosis", "--keep", "note")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in ("diagnosis", "note"):
            i = header.index(col)
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertIn("scrubbed for identifier patterns only", p.stdout)
        # kept_unverified_columns (round 2; it was kept_unverified_text_columns) also lists number
        # columns kept over a shape finding.
        listed = json.loads(report.read_text(encoding="utf-8"))["kept_unverified_columns"]
        self.assertEqual([d["column"] for d in listed], ["diagnosis", "note"])
        shown = p.stdout + p.stderr + report.read_text(encoding="utf-8")
        for s in sorted(self.raw_strings()):
            self.assertNotIn(s, shown)
            self.assertNotIn(s.upper(), shown)
        # verify finds the same names in a file that has no report.
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        for s in sorted(self.raw_strings()):
            self.assertNotIn(s, bad.stdout + bad.stderr)

    def test_a_file_with_another_separator_is_refused(self):
        for name, sep in (("semi.csv", ";"), ("pipe.txt", "|"), ("tabs.csv", "\t")):
            path = self.tmp / name
            path.write_text(sep.join(["site", "Alice Zeller", "result"]) + "\n"
                            + sep.join(["A", "1", "2"]) + "\n", encoding="utf-8")
            for cmd in (["plan", str(path)], ["verify", str(path)]):
                p = run(*cmd)
                self.assertEqual(p.returncode, 2, (name, cmd[0], p.stdout + p.stderr))
                self.assertIn("another column separator", p.stderr)
                self.assertNotIn("Zeller", p.stdout + p.stderr)


class CategoryWordsDoNotHideNames(unittest.TestCase):
    """A category word in a column name ("Treatment", "Lab", "Visit") must not stop the
    name check when the name also names a person or a role, and a column kept as a state
    or country must pass the residual check (third review of 2026-11-25, 1.0.1). Every
    name and place here is invented."""

    FIRST = ["Alvar", "Brisa", "Corwin", "Delphine", "Ezra", "Fenna", "Gideon", "Hollis",
             "Isolde", "Jarrah", "Kestrel", "Lunet"]
    LAST = ["Quillfeather", "Marrowby", "Tessaly", "Vonderhaar", "Okonjo", "Pellucidi",
            "Ashgrove", "Brennagh", "Calloway", "Duskmoor", "Embersley", "Fawnridge"]
    # The headers of the review, then others built the same way, so the fix is not a list
    # of these: other roles, a role before the category word, a plural, a numbered column.
    ROLE_HEADERS = [
        "Treatment Physician", "Lab Technician", "Visit Provider", "Procedure Surgeon",
        "Unit Nurse", "Group Leader", "Test Ordered By", "Event Reporter", "Specimen Collector",
        "Service Chief", "Source Contact", "Dept Head", "Ward Nurse", "Cohort Lead", "Stage Rater",
        "Study Group Patient", "Visit Subject", "Treatment Participant", "Cohort Member",
        "Diagnosis Contact", "Type Spouse", "Source Informant", "Ward Resident", "Event Patient",
        "Lab Individual", "Unit Husband", "Stage Parent", "Race Guardian",
        "Unit Pharmacist", "Procedure Anesthesiologist", "Event Witness", "Group Coordinator",
        "Diagnosis Reviewer", "Visit Interpreter", "Physician (Treatment)", "Treatment Physicians",
        "Lab Technician 2", "Visit Seen By", "Cohort Investigator", "Test Dietician",
        "Procedure Assistant", "Unit Clerk", "Test Sonographer", "Visit Attendee",
        "Lab Phlebotomist", "Ward Aide", "Event Grandmother", "Service Liaison",
    ]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))
        self.pool = [f"{f} {last}" for f, last in zip(self.FIRST, self.LAST)]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict], Path]:
        out_dir = self.tmp / "out"
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        return p, (read_rows(out) if out.exists() else []), out_dir / "deidentification_report.json"

    def raw_words(self) -> list[str]:
        return self.FIRST + self.LAST

    def test_names_under_a_category_word_and_a_role_word_are_redacted(self):
        header = self.ROLE_HEADERS + ["sex"]
        # 200 visits by a dozen people: the names repeat, so only their shape finds them.
        rows = [[self.pool[(i * (k + 1)) % len(self.pool)] for k in range(len(self.ROLE_HEADERS))]
                + ["F" if i % 2 else "M"] for i in range(200)]
        raw = write_csv(self.tmp / "roles.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = (self.tmp / "out" / "roles_deidentified.csv").read_text(encoding="utf-8")
        shown = p.stdout + p.stderr + report.read_text(encoding="utf-8")
        for w in self.raw_words():
            self.assertNotIn(w, text, "raw name in the output")
            self.assertNotIn(w, shown, "raw name printed or reported")
        for col in self.ROLE_HEADERS:
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])
        # The residual check finds the same names in a file that has no report.
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        for col in self.ROLE_HEADERS:
            self.assertIn(f"{col}: text values shaped like names", bad.stdout)
        for w in self.raw_words():
            self.assertNotIn(w, bad.stdout + bad.stderr)

    def test_a_name_column_of_a_role_is_an_identifier(self):
        header = ["Lab Technician Name", "Study Patient Name", "Specimen Collector Name",
                  "Trial Participant Name", "Drug Name", "sex"]
        rows = [[self.pool[i % 12], self.pool[(i + 3) % 12], self.pool[(i + 5) % 12],
                 self.pool[(i + 7) % 12], ["Metformin", "Lisinopril", "Apixaban"][i % 3],
                 "F" if i % 2 else "M"] for i in range(60)]
        raw = write_csv(self.tmp / "named.csv", header, rows)
        for col in ("Lab Technician Name", "Study Patient Name", "Specimen Collector Name"):
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Lab Technician Name"] for r in out}, {"[REDACTED]"})
        self.assertEqual({r["Specimen Collector Name"] for r in out}, {"[REDACTED]"})
        for col in ("Study Patient Name", "Trial Participant Name"):
            self.assertTrue(all(re.fullmatch(r"P\d{4}", r[col]) for r in out), col)
        # A drug name column is not an identifier by name, but its words are not in the closed
        # vocabulary: redacted by default (it was kept before round 1), kept on request.
        self.assertEqual({r["Drug Name"] for r in out}, {"[REDACTED]"})
        p, out, _ = self.run_file(raw, "--keep", "Drug Name")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Drug Name"] for r in out], [row[4] for row in rows])

    def test_category_columns_wait_for_the_persons_word(self):
        # Before round 1 of the fail-closed design (2026-11-25) a default run kept all of these.
        # Now only the race column, whose values are census categories, is kept by default; the
        # rest are text the script cannot verify, redacted and listed for the person, and kept
        # verbatim with --keep.
        cols = {
            "Visit Type": ["Office", "Telehealth", "Inpatient", "Emergency"],
            "Treatment Arm": ["Placebo", "Treatment A", "Treatment B"],
            "Lab Test": ["Hemoglobin", "Creatinine", "Sodium", "Troponin"],
            "Diagnosis": ["Heart Failure", "Type 2 Diabetes", "COPD", "Atrial Fibrillation"],
            "Patient Status": ["Alive", "Deceased", "Lost to Follow-up"],
            "Patient Diagnosis": ["Asthma", "Heart Failure", "Chronic Kidney Disease"],
            "Contact Method": ["Phone", "Email", "Letter"],
            "Provider Specialty": ["Cardiology", "Internal Medicine", "Family Medicine", "Pediatrics"],
            "Provider Type": ["Physician", "Nurse Practitioner", "Physician Assistant"],
            "Head Injury Type": ["Concussion", "Contusion", "Laceration"],
            "Primary Site": ["Breast", "Lung", "Colon", "Prostate", "Pancreas"],
            "Biomarker": ["EGFR", "HER2", "BRCA1", "KRAS"],
            "Religion": ["Catholic", "Muslim", "Jewish", "Buddhist", "Hindu", "None"],
            "Race": ["White", "Asian", "American Indian or Alaska Native",
                     "Native Hawaiian or Other Pacific Islander", "Black or African American"],
            "Finding": ["Nodule", "Effusion", "Consolidation", "Normal"],
            "Housing": ["Single family", "Multi family"],
        }
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(120)]
        raw = write_csv(self.tmp / "categories.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            expected = [row[i] for row in rows] if col == "Race" else ["[REDACTED]"] * len(rows)
            self.assertEqual([r[col] for r in out], expected, col)
        pending = [d["column"] for d in json.loads(report.read_text(encoding="utf-8"))["columns_needing_decision"]]
        self.assertEqual(pending, [h for h in header if h != "Race"])
        keep = [a for h in header if h != "Race" for a in ("--keep", h)]
        p, out, report = self.run_file(raw, *keep)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)

    def test_state_and_country_columns_pass_the_residual_check(self):
        cases = {
            "birth.csv": (["Country of Birth", "Age"], [["Mexico", "5"], ["Vietnam", "6"],
                                                       ["Philippines", "41"], ["Mexico", "33"]]),
            "country.csv": (["Country", "Age"], [["Mexico", "5"], ["Vietnam", "6"], ["Canada", "7"]]),
            "state.csv": (["State", "sex"], [["California", "F"], ["Oregon", "M"],
                                             ["New Mexico", "F"], ["Oregon", "F"]]),
        }
        for name, (header, rows) in cases.items():
            raw = write_csv(self.tmp / name, header, rows)
            for extra in ((), ("--keep", header[0])):
                p, out, report = self.run_file(raw, *extra)
                self.assertEqual(p.returncode, 0, (name, extra, p.stdout + p.stderr))
                self.assertEqual([r[header[0]] for r in out], [row[0] for row in rows], name)
                listed = [d["column"] for d in json.loads(report.read_text(encoding="utf-8"))["kept_text_columns"]]
                self.assertIn(header[0], listed, "a kept state or country column is listed to confirm")
                written = self.tmp / "out" / f"{raw.stem}_deidentified.csv"
                ok = run("verify", str(written), "--reference-year", REFERENCE_YEAR)
                self.assertEqual(ok.returncode, 0, (name, ok.stdout + ok.stderr))
                alone = self.tmp / "alone"
                alone.mkdir(exist_ok=True)
                shutil.copy(written, alone / written.name)
                guessed = run("verify", str(alone / written.name), "--reference-year", REFERENCE_YEAR)
                self.assertEqual(guessed.returncode, 0, (name, guessed.stdout + guessed.stderr))
                shutil.rmtree(self.tmp / "out")
                shutil.rmtree(alone)

    def test_keep_is_honoured_by_the_residual_check_for_shapes(self):
        # A column the person names with --keep is recorded as kept on request, so the
        # residual check does not second-guess the person's confirmation of its text (patterns
        # inside it are still scanned).
        header = ["Diagnosis", "sex"]
        rows = [[["Heart Failure", "Asthma", "COPD"][i % 3], "F"] for i in range(30)]
        p, out, report = self.run_file(write_csv(self.tmp / "kept.csv", header, rows), "--keep", "Diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        decision = json.loads(report.read_text(encoding="utf-8"))["decisions"][0]
        self.assertTrue(decision["kept_on_request"])
        self.assertEqual([r["Diagnosis"] for r in out], [row[0] for row in rows])
        self.assertIn("[kept on request]", p.stdout)
        # The check, reading that run's report, still finds a phone number written into it.
        written = self.tmp / "out" / "kept_deidentified.csv"
        rows[0][0] = "Asthma, call (415) 555-0134"
        write_csv(written, header, rows)
        bad = run("verify", str(written), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        self.assertIn("phone pattern", bad.stdout)
        self.assertNotIn("555-0134", bad.stdout + bad.stderr)

    def test_a_surname_with_family_is_shaped_like_a_name(self):
        header = ["household_label", "sex"]
        rows = [[f"{self.LAST[i % 4]} family", "F"] for i in range(40)]
        p, out, _ = self.run_file(write_csv(self.tmp / "family.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["household_label"] for r in out}, {"[REDACTED]"})


class ValuesDecideCategoryColumns(unittest.TestCase):
    """A category word in a column name keeps a column only when its values also look
    like a category: names and places shaped like names are found by their values
    whatever the column is called, and a column name with a role or place word in any
    form is never a category column (fourth review of 2026-11-25, 1.0.1). Every name,
    handle and place here is invented."""

    FIRST = ["Ilsabet", "Corvan", "Maelis", "Tobiah", "Wrenna", "Quinlan", "Saoirsa", "Davor",
             "Elowen", "Brannoc", "Ysolde", "Ferrin"]
    LAST = ["Thistlewaite", "Marrowgate", "Pennycastle", "Ravensmoor", "Kettleby", "Ashcombe",
            "Fernhallow", "Wexmoor", "Dunmarrow", "Quellbright", "Sorrowind", "Vantablen"]
    TOWNS = ["Quillbrook", "Marrowfield", "Tessaly Springs", "Duskhaven", "Fawnridge",
             "Embersley", "Ashgrove Bay", "Vonder Flats", "Pellucid Creek", "Calloway Heights",
             "Brennagh", "Okonjo Valley"]
    # The column names of the review, then others built the same way that no word list
    # names, and plain category names whose values are names.
    ROLE_HEADERS = [
        "Treatment Dr", "Lab Dr", "Visit Dr", "Visit Doc", "Group Prof", "Visit Docteur",
        "Test Medecin", "Visit Medico", "Service Arzt", "Treatment Team", "Visit With",
        "Treatment Assigned To", "Test Verifier", "Result Approver", "Treatment Authorizer",
        "Stage Reader", "Visit Scheduler", "Group Admin", "Unit Charge", "Ward Charge",
        "Cohort Responsible", "Group Responsable", "Visit Companion", "Visit Family",
        "Event Emergency", "Type Nombre", "Lab Sign-off", "Test Dr", "Event Dr", "Treatment Doc",
        "Visit Dr Name", "Test Reader", "Test Approver", "Visit Agent", "Visit Biller",
        "Visit Pastor", "Treatment Attorney", "Lab Responsible", "Visit Médecin", "Service Ärztin",
        "Result Validator", "Lab Releaser", "Event Organizer", "Visit Greeter", "Unit Dottore",
        "Visit Referred To", "Sample Sent To", "Stage Signed Off",
        "Visit Type", "Diagnosis", "Treatment Arm", "Cohort", "Lab Test", "Drug",
    ]
    PLACE_HEADERS = [
        "Visit Location", "Event Location", "Test Location", "Unit Location", "Service Area",
        "Specimen Collection Site", "Event Place", "Treatment Center", "Lab Facility",
        "Treatment Clinic", "Dept Campus", "Diagnosis Area", "Visit Zone", "Event Setting",
        "Lab Location", "Sample Location", "Cohort Location", "Unit Locale", "Event Venue",
        "Tumor Location", "Service Location", "Source Location", "Ward Location",
        "Treatment Location", "Visit Region", "Group Territory", "Visit Catchment",
        "Event Destination", "Visit Lugar", "Visit Ubicación", "Visit Ciudad", "Event Municipio",
    ]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict], Path]:
        out_dir = self.tmp / "out"
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        return p, (read_rows(out) if out.exists() else []), out_dir / "deidentification_report.json"

    def raw_words(self) -> list[str]:
        words = self.FIRST + self.LAST
        for town in self.TOWNS:
            words += [w for w in town.split() if len(w) >= 6]
        return words

    def name_forms(self, k: int, i: int) -> str:
        f, last = self.FIRST[(i * (k + 1)) % 12], self.LAST[(i * (k + 1) + k) % 12]
        return [f"{f} {last}", f"{last}, {f}", f"{f.upper()} {last.upper()}", f"{f} R. {last}",
                f"{last}, {f} MD"][k % 5]

    def assert_hidden(self, p, out_dir: Path, report: Path, words: list[str]) -> None:
        text = "".join(f.read_text(encoding="utf-8") for f in out_dir.glob("*_deidentified.csv"))
        shown = p.stdout + p.stderr + report.read_text(encoding="utf-8")
        for w in words:
            self.assertNotIn(w.lower(), text.lower(), "raw name or place in the output")
            self.assertNotIn(w.lower(), shown.lower(), "raw name or place printed or reported")

    def test_names_under_any_category_or_role_header_are_redacted(self):
        header = self.ROLE_HEADERS + ["sex"]
        rows = [[self.name_forms(k, i) for k in range(len(self.ROLE_HEADERS))]
                + ["F" if i % 2 else "M"] for i in range(200)]
        raw = write_csv(self.tmp / "roles2.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, self.tmp / "out", report, self.FIRST + self.LAST)
        for col in self.ROLE_HEADERS:
            self.assertTrue(all(re.fullmatch(r"\[REDACTED\]|P\d{4}", r[col]) for r in out), col)
        self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        for w in self.FIRST + self.LAST:
            self.assertNotIn(w.lower(), (bad.stdout + bad.stderr).lower())

    def test_single_surnames_under_a_role_word_are_redacted(self):
        header = ["Visit Dr", "Treatment Doc", "Group Prof", "Test Verifier", "Visit Docteur",
                  "Unit Charge", "Visit Family", "Result Validator", "Lab Sign-off", "Visit With"]
        rows = [[self.LAST[(i + k) % 12] for k in range(len(header))] for i in range(150)]
        p, out, report = self.run_file(write_csv(self.tmp / "surnames.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, self.tmp / "out", report, self.LAST)
        for col in header:
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)

    def test_a_name_column_of_a_title_or_role_cannot_be_kept(self):
        header = ["Visit Dr Name", "Test Verifier Name", "Nombre Medico", "sex"]
        rows = [[self.name_forms(0, i), self.name_forms(1, i), self.name_forms(2, i), "F"]
                for i in range(60)]
        raw = write_csv(self.tmp / "drname.csv", header, rows)
        for col in header[:3]:
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)

    def test_places_under_a_category_and_place_word_are_redacted(self):
        header = self.PLACE_HEADERS + ["Cohort", "Visit Type", "sex"]
        multi = [t for t in self.TOWNS if " " in t]
        rows = [[self.TOWNS[(i * (k + 1)) % 12] for k in range(len(self.PLACE_HEADERS))]
                + [multi[i % len(multi)], multi[(i + 2) % len(multi)], "F" if i % 2 else "M"]
                for i in range(200)]
        raw = write_csv(self.tmp / "places.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, self.tmp / "out", report, self.raw_words())
        for col in header[:-1]:
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)

    def test_category_values_under_place_and_role_words_wait_for_the_persons_word(self):
        # Kept by default before round 1 (2026-11-25); now only the numbers and the response
        # words are, and the rest are kept on request.
        cols = {
            "Tumor Location": ["Left Upper Lobe", "Right Lower Lobe", "Sigmoid Colon", "Breast"],
            "Care Setting": ["Inpatient", "Outpatient", "Home", "Skilled Nursing Facility"],
            "Location Type": ["Urban", "Rural", "Suburban"],
            "Census Region": ["Northeast", "Midwest", "South", "West"],
            "Pain Location": ["Lower Back", "Left Knee", "Abdomen", "Chest"],
            "Treatment Team": ["Cardiology Team", "Oncology Team", "Surgery Team"],
            "Provider Type": ["Physician", "Nurse Practitioner", "Physician Assistant"],
            "Referred To": ["Cardiology", "Neurology", "Physical Therapy"],
            "Tumor Marker": ["EGFR", "KRAS", "HER2", "BRCA1"],
            "Visit Number": ["1", "2", "3", "4"],
            "Treatment Responder": ["Responder", "Nonresponder"],
            "Doc Type": ["Consent", "Progress Note", "Discharge Summary"],
            "DR Grade": ["Mild", "Moderate", "Severe", "Proliferative"],
            "Drug Admin Route": ["Oral", "Intravenous", "Subcutaneous", "Topical"],
        }
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(120)]
        raw = write_csv(self.tmp / "kept_categories.csv", header, rows)
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        verified = {"Visit Number", "Treatment Responder"}
        for i, col in enumerate(header):
            expected = [row[i] for row in rows] if col in verified else ["[REDACTED]"] * len(rows)
            self.assertEqual([r[col] for r in out], expected, col)
        p, out, _ = self.run_file(raw, *[a for h in header if h not in verified for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)

    def test_ordinary_clinical_category_columns_wait_for_the_persons_word(self):
        # Kept by default before round 1 (2026-11-25); now only Race is (Patient Refused is a
        # missing-value phrase), and the rest are kept on request.
        cols = {
            "Diagnosis": ["Atrial Fibrillation", "Pulmonary Embolism", "Septic Shock", "Heart Failure",
                          "Type 2 Diabetes", "Major Depression", "Bipolar Disorder", "Iron Deficiency",
                          "Chronic Kidney Disease", "Essential Hypertension", "Sleep Apnea",
                          "Cerebral Palsy", "Down Syndrome", "Sickle Cell", "Herpes Zoster"],
            "Drug": ["Insulin Glargine", "Metformin", "Lisinopril", "Potassium Chloride",
                     "Albuterol Sulfate", "Aspirin", "Normal Saline"],
            "Lab Test": ["Hemoglobin", "Creatinine", "Sodium", "Troponin", "Basic Metabolic Panel",
                         "Complete Blood Count"],
            "Visit": ["Screening", "Baseline", "End of Study", "Early Termination", "Follow Up"],
            "Treatment Arm": ["Placebo", "Arm A", "Standard of Care", "High Dose"],
            "Occupation": ["Teacher", "Nurse", "Engineer", "Retired", "Unemployed", "Farmer"],
            "Cell Line": ["HeLa", "MCF-7", "HEK293", "Jurkat"],
            "Language": ["English", "Spanish", "Haitian Creole", "American Sign Language"],
            "Race": ["White", "Two or More Races", "Asian", "Patient Refused"],
            "Insurance": ["Medicare", "Medicaid", "Commercial", "Self-pay"],
            "Specialty": ["Physical Medicine and Rehabilitation", "Hematology Oncology", "Cardiology"],
        }
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(150)]
        raw = write_csv(self.tmp / "clinical.csv", header, rows)
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            expected = [row[i] for row in rows] if col == "Race" else ["[REDACTED]"] * len(rows)
            self.assertEqual([r[col] for r in out], expected, col)
        p, out, _ = self.run_file(raw, *[a for h in header if h != "Race" for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)

    def test_type_and_status_columns_of_identifier_words_can_be_kept(self):
        cols = {
            "Insurance Type": ["Medicare", "Medicaid", "Commercial", "Self-pay", "Uninsured"],
            "Insurance Status": ["Insured", "Uninsured"],
            "Insurance Plan Type": ["HMO", "PPO", "EPO", "Medicare Advantage"],
            "Medicare Status": ["Enrolled", "Not Enrolled", "Pending"],
            "Medicaid Eligible": ["Yes", "No"],
            "Subscriber Status": ["Active", "Inactive", "Terminated"],
            "Account Type": ["Checking", "Savings", "Self-pay"],
            "License Status": ["Active", "Suspended", "Expired"],
            "Certificate Type": ["Birth", "Death", "Marriage"],
            "Login Status": ["Success", "Failed", "Locked"],
            "Passport Status": ["Valid", "Expired", "None"],
            "City Type": ["Urban", "Rural", "Suburban"],
            "Employer Type": ["Private", "Government", "Self-employed", "Nonprofit"],
            "Phone Type": ["Mobile", "Home", "Work"],
            "Type of Insurance": ["Medicare", "Commercial"],
        }
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(90)]
        raw = write_csv(self.tmp / "qualifiers.csv", header, rows)
        # These are not identifiers by name, so a default run exits 0 and they can be kept
        # (prior finding: --keep on them used to exit 2). Yes and No are verified; the other
        # words are text the script cannot verify, redacted until the person keeps them (they
        # were kept by default before round 1 of 2026-11-25).
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            expected = [row[i] for row in rows] if col == "Medicaid Eligible" else ["[REDACTED]"] * len(rows)
            self.assertEqual([r[col] for r in out], expected, col)
        p, out, report = self.run_file(raw, *[a for h in header if h != "Medicaid Eligible" for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        written = self.tmp / "out" / "qualifiers_deidentified.csv"
        ok = run("verify", str(written), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        # Without the run's report the check cannot know the person kept them: it fails closed.
        alone = self.tmp / "alone"
        alone.mkdir()
        shutil.copy(written, alone / written.name)
        guessed = run("verify", str(alone / written.name), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(guessed.returncode, 3, guessed.stdout + guessed.stderr)
        self.assertIn("Insurance Type: text the script cannot verify", guessed.stdout)
        # Numbers, names, towns and logins under the same names are still identifiers by name.
        ids = write_csv(self.tmp / "qualifier_ids.csv",
                        ["Account Type", "Insurance Status", "Employer Type", "City Type",
                         "Login Status", "Subscriber Status", "sex"],
                        [[f"ACCT-{4400 + i}", f"MBR{90210 + i}", self.LAST[i % 3], self.TOWNS[i % 3],
                          self.FIRST[i % 3].lower(), f"{self.FIRST[i % 3]} {self.LAST[i % 3]}", "F"]
                         for i in range(30)])
        for col in ("Account Type", "Insurance Status", "Employer Type", "City Type", "Login Status",
                    "Subscriber Status"):
            refused = run("plan", str(ids), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)

    def test_kept_text_loses_handles_short_urls_and_serials(self):
        values = ["profile fb.me/ilsabet.thistle", "dm @wrenna_kettle", "Facebook /corvan.marrow",
                  "login tobiah@kettlebox", "Device SN 8841-2290", "see quellbright-clinic.org/p/77",
                  "Instagram: elowen_ash22", "Patient Name: Corvan Ashcombe",
                  # Not identifiers, and left alone.
                  "dose @ 2mg q.d.", "a.m. dose", "vs. baseline", "e.g. 5 mg", "Patient Refused"]
        raw = write_csv(self.tmp / "handles.csv", ["ref", "sex"], [[v, "F"] for v in values])
        p, out, _ = self.run_file(raw, "--keep", "ref")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ref"] for r in out], [
            "profile [URL]", "dm [HANDLE]", "Facebook [HANDLE]", "login [EMAIL]", "Device SN [ID]",
            "see [URL]", "Instagram: [HANDLE]", "Patient Name: [NAME]",
            "dose @ 2mg q.d.", "a.m. dose", "vs. baseline", "e.g. 5 mg", "Patient Refused"])


class YearMonthsAndScriptsWithoutCase(unittest.TestCase):
    """Year and month values under any column name, names and places in scripts that have
    no capital letters, and smaller gaps in kept text (fifth review of 2026-11-25, 1.0.1).
    Every name, handle, place and date here is invented."""

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    # The column names of the review, then neutral ones and category ones: the month must
    # go whatever the column is called.
    MONTH_HEADERS = [
        "Visit Month", "Admit", "Encounter", "Period", "Admission", "Cohort Month", "Month",
        "Month of Visit", "Reporting Period", "Sample Month", "Enrollment", "Enrolled", "Visit",
        "Event", "Baseline", "Index Month", "Dx Month", "Ym", "Zxq", "Col1", "Diagnosis",
        "Visit Type", "Treatment Arm",
    ]
    FORMS = {
        "dash": lambda y, m: f"{y}-{m:02d}",
        "slash": lambda y, m: f"{y}/{m:02d}",
        "dot": lambda y, m: f"{y}.{m:02d}",
        "compact": lambda y, m: f"{y}{m:02d}",
        "short": lambda y, m: f"{y}-{m}",
        "word": lambda y, m: f"{y} {YearMonthsAndScriptsWithoutCase.MONTHS[m - 1]}",
    }
    # Invented people and places, twelve of each, written in scripts without letter case.
    SCRIPTS = {
        "zh": ["林子涵", "周嘉怡", "吴宇轩", "郑欣妍", "孙浩然", "马雨桐", "胡梓萱", "郭俊熙",
               "何思琪", "高子墨", "罗一诺", "梁沐阳"],
        "ja": ["森田健太", "高橋美咲", "小林悠斗", "渡辺陽菜", "中村大翔", "山本結衣", "加藤蓮",
               "吉田葵", "佐々木湊", "松本凛", "井上颯太", "木村紬"],
        "ko": ["박지훈", "최서연", "정민준", "강하은", "조도윤", "윤지우", "장서준", "임하린",
               "한예준", "오수아", "서건우", "신지아"],
        "ar": ["محمد الحسن", "فاطمة الزهراني", "أحمد العتيبي", "مريم القحطاني", "يوسف الشمري",
               "نور الدوسري", "عمر المطيري", "ليلى الحربي", "خالد السبيعي", "سارة الغامدي",
               "علي الزهري", "هدى العنزي"],
        "he": ["נועה פרידמן", "איתי שפירא", "תמר גולן", "עומר בן דוד", "מיכל רוזן", "אורי קפלן",
               "יעל אדלר", "גיל ברק", "רוני שחר", "דנה אורן", "עידו לבנון", "הדס כרמי"],
        "hi": ["राहुल शर्मा", "प्रिया वर्मा", "अमित गुप्ता", "नेहा सिंह", "विकास यादव", "पूजा मिश्रा",
               "सुनील पटेल", "अंजलि जोशी", "रोहित चौहान", "कविता त्रिपाठी", "अर्जुन मेहता", "सीमा पांडे"],
        "th": ["สมชาย ใจดี", "สมหญิง รักไทย", "ประเสริฐ ศรีสุข", "วิภา บุญมา", "ธนากร แสงทอง",
               "กาญจนา มีสุข", "ณัฐพล ทองดี", "ปิยะดา สุขใจ", "อนุชา พรหมมา", "รัตนา วงศ์ไทย",
               "สุรชัย แก้วมณี", "จันทร์เพ็ญ ศรีวงศ์"],
        "places": ["青川镇", "柳溪村", "石桥镇", "白沙湾", "桃源乡", "云岭村", "东湖镇", "梅林村",
                   "北山镇", "清河村", "松岗镇", "花溪乡"],
    }
    SCRIPT_HEADERS = ["Zxq", "Col7", "Notes By", "Visit Type", "Referral Source", "Provider",
                      "Visit Provider", "Referring Physician", "Notes", "Info", "Location",
                      "Diagnosis", "Status", "Class"]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict], Path]:
        out_dir = self.tmp / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        return p, (read_rows(out) if out.exists() else []), out_dir / "deidentification_report.json"

    def test_year_month_values_keep_only_the_year(self):
        # 36 months repeating over 180 rows, as a monthly export written with %Y-%m.
        months = [(2019 + k // 12, k % 12 + 1) for k in range(36)]
        for form, write in self.FORMS.items():
            header = self.MONTH_HEADERS + ["sex"]
            rows = [[write(*months[(i + k) % 36]) for k in range(len(self.MONTH_HEADERS))]
                    + ["F" if i % 2 else "M"] for i in range(180)]
            raw = write_csv(self.tmp / f"months_{form}.csv", header, rows)
            p, out, _ = self.run_file(raw)
            self.assertEqual(p.returncode, 0, (form, p.stdout + p.stderr))
            for k, col in enumerate(self.MONTH_HEADERS):
                expected = [str(months[(i + k) % 36][0]) for i in range(180)]
                self.assertEqual([r[col] for r in out], expected, (form, col))
            self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])
            # The check finds the months in a file that has no report.
            bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
            self.assertEqual(bad.returncode, 3, (form, bad.stdout + bad.stderr))

    def test_seasons_stay_and_a_monthly_column_of_those_years_does_not(self):
        # "2010-11" is a flu season or a school year as often as it is November 2010; a column
        # of seasons stays, and a column of months is still found as a whole.
        seasons = [f"{y}-{(y + 1) % 100:02d}" for y in range(2006, 2020)]
        monthly = [f"{2000 + k // 12}-{k % 12 + 1:02d}" for k in range(144)]
        rows = [[seasons[i % len(seasons)], f"{seasons[i % 5][:4]}/{seasons[i % 5][5:]}", monthly[i % 144], "F"]
                for i in range(288)]
        raw = write_csv(self.tmp / "seasons.csv", ["Season", "School Year", "Visit Month", "sex"], rows)
        # A season is not a date the scrubber reduces, nor a value the script verifies, so it is
        # redacted by default since round 1 (2026-11-25; it was kept before) and kept verbatim
        # on request. The column of months keeps the year either way.
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Season"] for r in out}, {"[REDACTED]"})
        self.assertEqual({r["School Year"] for r in out}, {"[REDACTED]"})
        self.assertEqual([r["Visit Month"] for r in out], [row[2][:4] for row in rows])
        p, out, _ = self.run_file(raw, "--keep", "Season", "--keep", "School Year")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Season"] for r in out], [row[0] for row in rows])
        self.assertEqual([r["School Year"] for r in out], [row[1] for row in rows])
        self.assertEqual([r["Visit Month"] for r in out], [row[2][:4] for row in rows])

    def test_year_month_in_kept_text_becomes_the_year(self):
        values = ["Seen on 2021-03", "seen 2021/03 again", "visit 2021-3", "2021 Mar follow-up",
                  "admitted 2021 March", "scheduled 2021-Mar",
                  # Not dates, and left alone.
                  "2019-2021 cohort", "2019-20 season", "BP 120/80", "vision 20/10", "pain 7/10",
                  "In 2021 may improve", "E11.9", "take 1/2 tab"]
        raw = write_csv(self.tmp / "kept_months.csv", ["ref", "sex"], [[v, "F"] for v in values])
        p, out, _ = self.run_file(raw, "--keep", "ref")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ref"] for r in out], [
            "Seen on 2021", "seen 2021 again", "visit 2021", "2021 follow-up", "admitted 2021",
            "scheduled 2021",
            "2019-2021 cohort", "2019-20 season", "BP 120/80", "vision 20/10", "pain 7/10",
            "In 2021 may improve", "E11.9", "take 1/2 tab"])

    def assert_hidden(self, p, report: Path, words: list[str]) -> None:
        text = "".join(f.read_text(encoding="utf-8") for f in (self.tmp / "out").glob("*_deidentified.csv"))
        shown = p.stdout + p.stderr + report.read_text(encoding="utf-8")
        for w in words:
            self.assertNotIn(w, text, "raw name or place in the output")
            self.assertNotIn(w, shown, "raw name or place printed or reported")

    def test_names_in_scripts_without_letter_case_are_redacted(self):
        for script, names in self.SCRIPTS.items():
            header = self.SCRIPT_HEADERS + ["sex"]
            rows = [[names[(i * (k + 1) + k) % 12] for k in range(len(self.SCRIPT_HEADERS))]
                    + ["F" if i % 2 else "M"] for i in range(200)]
            raw = write_csv(self.tmp / f"script_{script}.csv", header, rows)
            locales = {"zh": ("us", "cn"), "ja": ("us", "jp"), "ko": ("us", "kr")}.get(script, ("us",))
            for locale in locales:
                p, out, report = self.run_file(raw, "--locale", locale)
                self.assertEqual(p.returncode, 0, (script, locale, p.stdout + p.stderr))
                self.assert_hidden(p, report, names)
                for col in self.SCRIPT_HEADERS:
                    self.assertTrue(all(re.fullmatch(r"\[REDACTED\]|P\d{4}", r[col]) for r in out),
                                    (script, locale, col))
                self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])
            bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
            self.assertEqual(bad.returncode, 3, (script, bad.stdout + bad.stderr))
            for w in names:
                self.assertNotIn(w, bad.stdout + bad.stderr)

    def test_a_name_in_such_a_script_beside_latin_words_is_found(self):
        rows = [[f"Dr {self.SCRIPTS['zh'][i % 12]}", f"seen by {self.SCRIPTS['ko'][i % 12]}", "F"]
                for i in range(120)]
        p, out, report = self.run_file(write_csv(self.tmp / "mixed.csv", ["Doctor", "Note", "sex"], rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, report, self.SCRIPTS["zh"] + self.SCRIPTS["ko"])
        for col in ("Doctor", "Note"):
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)

    def test_common_category_words_in_such_scripts_are_kept_and_others_can_be(self):
        cols = {"性别": ["男", "女"], "성별": ["남", "여", "남성", "여성"], "الجنس": ["ذكر", "أنثى"],
                "Smoker": ["是", "否"], "Result": ["阳性", "阴性", "未知"], "Sex": ["F", "M"]}
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(80)]
        raw = write_csv(self.tmp / "vocab.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        # A diagnosis column in Chinese is redacted by default (its words cannot be told from
        # names), listed for the person, and kept with --keep; the residual check honours it.
        dx = write_csv(self.tmp / "dx.csv", ["Diagnosis", "sex"],
                       [[["高血压", "糖尿病", "哮喘"][i % 3], "F"] for i in range(60)])
        p, out, _ = self.run_file(dx)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Diagnosis"] for r in out}, {"[REDACTED]"})
        self.assertIn("without capital letters", p.stdout)
        p, out, report = self.run_file(dx, "--keep", "Diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Diagnosis"] for r in out}, {"高血压", "糖尿病", "哮喘"})
        ok = run("verify", str(self.tmp / "out" / "dx_deidentified.csv"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        listed = json.loads(report.read_text(encoding="utf-8"))["kept_text_columns"]
        self.assertTrue(listed and listed[0]["script_without_case"])

    def test_long_text_in_such_a_script_is_free_text(self):
        # Sentences in these scripts have no spaces between words, so they are found by
        # their length, and like any free text they cannot be kept.
        notes = ["患者今日复诊诉胸闷气短加重已三天夜间不能平卧", "術後経過は良好で本日退院予定となりましたが外来で再診",
                 "สมชายมาตรวจตามนัดอาการดีขึ้นมากแล้ววันนี้"]
        raw = write_csv(self.tmp / "notes.csv", ["Note", "sex"], [[notes[i % 3], "F"] for i in range(30)])
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Note"] for r in out}, {"[REDACTED]"})
        self.assertIn("free text", p.stdout)
        refused = run("plan", str(raw), "--keep", "Note")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("free text", refused.stderr)

    def test_an_initial_and_a_surname_under_a_category_name_are_redacted(self):
        last = ["Quillmere", "Tannerby", "Ostrava", "Pelloway", "Grimsdale", "Vantowe", "Harrowick",
                "Lindqvar", "Merrowin", "Sabbatine", "Corrigale", "Wendemuth"]
        first = ["Alma", "Bastien", "Cordula", "Dorian", "Elske", "Florin", "Greta", "Henrik",
                 "Ilona", "Jasper", "Katrin", "Leander"]
        header = ["Group", "Treatment Plan", "Insurance Type", "Cohort", "Arm", "Diagnosis", "sex"]
        forms = [lambda f, s: f"{f[0]}. {s}", lambda f, s: f"{f} {s[0]}.", lambda f, s: f"{s}, {f[0]}."]
        rows = [[forms[(i + k) % 3](first[(i + k) % 12], last[(i + k) % 12]) for k in range(6)] + ["F"]
                for i in range(150)]
        p, out, report = self.run_file(write_csv(self.tmp / "initials.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, report, last + first)
        for col in header[:-1]:
            self.assertTrue(all(re.fullmatch(r"\[REDACTED\]|P\d{4}", r[col]) for r in out), col)
        # A genus written as an initial is not a person, in either case, and a category
        # letter has no full stop.
        cols = {"Organism": ["E. coli", "E. Coli", "S. Aureus", "K. Pneumoniae", "C. difficile",
                             "P. Aeruginosa", "Escherichia Coli", "Candida Albicans"],
                "Treatment Plan": ["Plan A", "Plan B", "Plan C"],
                "Cohort": ["Cohort A", "Cohort B"]}
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(80)]
        raw = write_csv(self.tmp / "species.csv", header, rows)
        # Kept by default before round 1 (2026-11-25); now redacted as text the script cannot
        # verify, and kept verbatim on request.
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in header:
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        p, out, _ = self.run_file(raw, *[a for h in header for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)

    def test_kept_text_loses_day_months_foreign_dates_and_more_handles(self):
        values = ["Seen 14/3", "seen on 03-14", "Seen 14.3.", "14 mars 2021", "14. März 2021",
                  "marzo de 2020", "Instagram: jdoe", "on Instagram as jdoe99", "Facebook /x",
                  "u/jdoe", "jdoe#1234", "skype:jdoe", "Patient: 林子涵", "Dr. 박지훈 to call",
                  # Not identifiers, and left alone.
                  "vision 20/10", "pain 7/10", "BP 140/90", "GCS 14/15", "Instagram: none",
                  "u/s abdomen", "10 u/day", "seen 10-12 times", "on 2-3 occasions", "Hb 14.3",
                  "MRN#88412"]
        raw = write_csv(self.tmp / "gaps.csv", ["ref", "sex"], [[v, "F"] for v in values])
        p, out, _ = self.run_file(raw, "--keep", "ref")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ref"] for r in out], [
            "Seen [DATE]", "seen on [DATE]", "Seen [DATE]", "2021", "2021", "2020",
            "Instagram: [HANDLE]", "on Instagram as [HANDLE]", "Facebook [HANDLE]", "[HANDLE]",
            "[HANDLE]", "skype:[HANDLE]", "Patient: [NAME]", "Dr. [NAME] to call",
            "vision 20/10", "pain 7/10", "BP 140/90", "GCS 14/15", "Instagram: none",
            "u/s abdomen", "10 u/day", "seen 10-12 times", "on 2-3 occasions", "Hb 14.3",
            "MRN#[ID]"])


# In-process probes of safe_harbor.py, run in a child interpreter (the module disables
# sockets when it is imported). They take a JSON file of columns and print JSON.
PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import safe_harbor as s, deidentify as u
mode, path, locale_code = sys.argv[2], sys.argv[3], sys.argv[4]
locale = u.load_locale(locale_code)
sc = s.Scrubber(locale, 2026)
out = []
for header, values in json.load(open(path, encoding="utf-8")):
    if mode == "decide":
        d = s.decide_columns([{header: v} for v in values], [header], locale, sc, set(), set(), 2026)[0]
        out.append([header, d["action"], d["kind"]])
    else:
        ctx = s.ColumnContext(header)
        out.append([header, [s.code_grammar(v, ctx) if mode == "grammar" else s.value_verified(v, ctx)
                             for v in values]])
print(json.dumps(out, ensure_ascii=False))
"""


def probe(tmp: Path, mode: str, columns: list, locale: str = "us") -> list:
    path = tmp / f"probe_{mode}.json"
    path.write_text(json.dumps(columns, ensure_ascii=False), encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", "-B", "-c", PROBE, str(SCRIPT.parent), mode, str(path), locale],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                       timeout=300)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-2000:])
    return json.loads(p.stdout)


class FailClosedTextColumns(unittest.TestCase):
    """Round 1 of the fail-closed design (2026-11-25): a default run keeps a column that is
    not an identifier by name only when it verifies every value as a number, a code of a
    closed grammar, a whole value of a closed vocabulary, a date or an allowed state or
    country. These tests take the high and medium findings of the three earlier reviews and
    show that a default run now redacts or handles each one, across many column names and
    value shapes the reviews did not list. Every name, place and value here is invented."""

    FIRST = ["Corla", "Teodric", "Anwyn", "Brisot", "Maelin", "Ostrid", "Velka", "Junaro", "Feyla",
             "Hadric", "Isaura", "Plover"]
    LAST = ["Nakashira", "Okelbury", "Varnhold", "Quistern", "Delmoray", "Fintallow", "Graybeck",
            "Haskentine", "Lorrimund", "Pemberforth", "Yarrowind", "Zellmoor"]
    TOWNS = ["Brindlecove", "Oakshaw", "Marrowmere", "Quellford", "Tansy Hollow", "Ferncastle",
             "Duskbridge", "Wrenhaven", "Pellmarsh", "Cinderbrook", "Ashwick Falls", "Larkmoor"]
    # Names with what the reviews put around them, and more of the same kind.
    SHAPES = [
        "{f} {l} (wife)", "{f} {l} - spouse", "{l}, {f} (son)", "{f} {l} 45", "{f} {l} (F)",
        "{f} {l} (45)", "{f} {l} - cardiology", "{f} {l} (RN)", "{f} {l} [RN]", "{f} {l} - RN",
        "{f} {l} / RN", "{f} {l} (Cardiology)", "{f} {l} - Oncology", "{f} {l} | Cardiology",
        "{f} {l} (PCP)", "{f} {l} (Lakeside)", "{f} {l} (retired)", "{f} {l} (12)", "{f} {l} #12",
        "{f} {l} 12", "{f} {l}; MD", "{f} {l}*", "{f}_{l}", '{f} "Kit" {l}', "{fl}.{ll}",
        "{fl} {ll}", "{ll}, {fl}", "{f0}{l0}", "{f0}. {l}", "{l}, {f0}.", "{l}", "{f}", "{ll}",
        "{l} family", "{lu}", "{f} {l}, MD", "{f} {l} and {f2} {l2}", "{f} {l}/{f2} {l2}",
        "{f} {l} (guardian)", "{f} {l} - mother", "{f} {l} (age 45)", "{f} {l} M", "{f} von {l}",
        "{f}-{f2} {l}", "{f} {l}-{l2}", "{f} {l} Jr.", "{f} {l} III", "{f0}.{l0}.", "{lu}, {fu}",
    ]
    PERSON_HEADERS = [
        "Contact Person", "Referring Physician", "Guardian", "Treatment Dr", "Notes By", "Contact",
        "Col1", "Group", "Visit Type", "Diagnosis", "Referral", "Provider", "Visit Provider",
        "Reviewer", "Seen By", "Notes Author", "Source", "Comments", "Referral Source", "Status",
        "Class", "Zxq", "Info", "Result", "Finding", "Impression", "Response", "Treatment",
    ]
    CATEGORY_WORDS = ["Visit", "Treatment", "Lab", "Test", "Event", "Group", "Unit", "Ward", "Service",
                      "Cohort", "Stage", "Result", "Sample", "Specimen", "Diagnosis", "Procedure",
                      "Source", "Dept", "Type", "Status"]
    ROLE_WORDS = ["Dr", "Doc", "Prof", "Docteur", "Medecin", "Médecin", "Medico", "Arzt", "Ärztin",
                  "Team", "With", "Assigned To", "Verifier", "Approver", "Authorizer", "Reader",
                  "Scheduler", "Admin", "Charge", "Responsible", "Responsable", "Companion", "Family",
                  "Emergency", "Nombre", "Sign-off", "Agent", "Biller", "Pastor", "Attorney",
                  "Dr Name", "Host", "Owner", "Handler", "Liaison", "Referred To", "Seen By",
                  "Signed Off", "Lead", "Rep"]
    PLACE_WORDS = ["Location", "Venue", "Locale", "Area", "Site", "Place", "Center", "Centre",
                   "Facility", "Clinic", "Campus", "Zone", "Setting", "Region", "Catchment",
                   "Lugar", "Ubicación", "Hospital", "Office", "Branch", "Station", "Destination",
                   "Origin", "Community", "Territory", "City", "Town"]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict], dict]:
        out_dir = self.tmp / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        report = out_dir / "deidentification_report.json"
        return (p, read_rows(out) if out.exists() else [],
                json.loads(report.read_text(encoding="utf-8")) if report.exists() else {})

    def shaped(self, shape: str, i: int) -> str:
        f, l = self.FIRST[i % 12], self.LAST[(i * 5) % 12]
        f2, l2 = self.FIRST[(i + 3) % 12], self.LAST[(i * 5 + 7) % 12]
        return shape.format(f=f, l=l, f2=f2, l2=l2, fl=f.lower(), ll=l.lower(), fu=f.upper(),
                            lu=l.upper(), f0=f[0], l0=l[0])

    def assert_redacted(self, decided: list, what: str) -> None:
        kept = [(h, a, k) for h, a, k in decided if a not in ("redact", "pseudonym_name", "pseudonym_id")]
        self.assertEqual(kept, [], f"{what}: columns kept or transformed without redaction")

    def assert_hidden(self, p, out: list[dict], report: dict, words: list[str]) -> None:
        text = json.dumps(out, ensure_ascii=False).lower()
        shown = (p.stdout + p.stderr + json.dumps(report, ensure_ascii=False)).lower()
        for w in words:
            self.assertNotIn(w.lower(), text, "raw value in the output")
            self.assertNotIn(w.lower(), shown, "raw value printed or reported")

    # High (third review) and medium (second review): names with a qualifier, and names in a
    # person-role column with any suffix, kept verbatim with exit 0.
    def test_names_with_any_qualifier_are_redacted_under_any_column_name(self):
        columns = [(h, [self.shaped(shape, i) for i in range(36)])
                   for shape in self.SHAPES for h in self.PERSON_HEADERS]
        self.assert_redacted(probe(self.tmp, "decide", columns), "names with qualifiers")
        # End to end: one column per shape under a role header, 200 rows, nothing leaks.
        header = [f"{self.PERSON_HEADERS[k % len(self.PERSON_HEADERS)]} {k}" for k in range(len(self.SHAPES))]
        rows = [[self.shaped(shape, i) for shape in self.SHAPES] + ["F" if i % 2 else "M"] for i in range(200)]
        p, out, report = self.run_file(write_csv(self.tmp / "qualified.csv", header + ["sex"], rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, out, report, self.FIRST + self.LAST)
        for col in header:
            self.assertTrue(all(re.fullmatch(r"\[REDACTED\]|P\d{4}", r[col]) for r in out), col)
        self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])

    # High (first review) and medium (second review): names under a category word and a role
    # or title word (Visit Dr, Test Verifier, Lab Sign-off, ...).
    def test_names_under_a_category_word_and_any_role_word_are_redacted(self):
        headers = [f"{c} {r}" for c in self.CATEGORY_WORDS for r in self.ROLE_WORDS]
        headers += [f"{r} ({c})" for c in self.CATEGORY_WORDS[:5] for r in self.ROLE_WORDS[:10]]
        forms = ["{f} {l}", "{l}, {f}", "{fu} {lu}", "{f} R. {l}", "{l}, {f} MD", "{l}", "{f0}. {l}"]
        columns = [(h, [self.shaped(forms[k % len(forms)], i) for i in range(30)])
                   for k, h in enumerate(headers)]
        self.assert_redacted(probe(self.tmp, "decide", columns), "role headers")
        header = headers[::25]
        rows = [[self.shaped(forms[k % len(forms)], i) for k in range(len(header))] for i in range(200)]
        p, out, report = self.run_file(write_csv(self.tmp / "roles.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, out, report, self.FIRST + self.LAST)

    # High (first review) and medium (second review): towns under a category word and a place
    # word (Visit Location, Service Area, Treatment Center), and under neutral names.
    def test_places_under_a_category_and_place_word_are_redacted(self):
        headers = [f"{c} {w}" for c in self.CATEGORY_WORDS for w in self.PLACE_WORDS]
        headers += ["Ciudad", "Municipio", "Neighborhood", "Hometown", "Place", "Residence", "Lives In",
                    "Catchment", "Col3", "Zxq", "Visit", "Cohort", "Treatment City", "Cohort City"]
        columns = [(h, [self.TOWNS[(i * (k + 1)) % 12] for i in range(30)]) for k, h in enumerate(headers)]
        self.assert_redacted(probe(self.tmp, "decide", columns), "place headers")
        header = headers[::20]
        rows = [[self.TOWNS[(i * (k + 1)) % 12] for k in range(len(header))] for i in range(200)]
        p, out, report = self.run_file(write_csv(self.tmp / "places.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, out, report, [w for t in self.TOWNS for w in t.split() if len(w) >= 6])

    # High (second review) and medium (second review): names and places in scripts without
    # letter case, also with qualifiers, under any column name and any locale.
    SCRIPT_NAMES = {
        "zh": ["许清远", "邓若溪", "韩书瑶", "唐景行", "冯语桐", "曹嘉禾", "彭思远", "蒋若琳", "蔡明轩",
               "潘雨萱", "袁浩宇", "卢欣怡"],
        "ja": ["藤原真央", "石川陽斗", "前田花音", "岡田蒼", "後藤咲良", "長谷川樹", "村上楓", "近藤琴音",
               "坂本隼", "遠藤美羽", "青木大和", "藤田芽依"],
        "ko": ["류현우", "배지민", "송예린", "황도현", "안서윤", "홍시우", "전하윤", "고준서", "문지안",
               "양민서", "손태윤", "백나연"],
        "ar": ["حسن المالكي", "ريم السالم", "طارق النجار", "دينا الخطيب", "سامي الحداد", "لمى الصباغ",
               "وليد البيطار", "رنا الشامي", "زياد العلي", "هالة الأحمد", "كريم الفارس", "منى الصالح"],
        "he": ["אביב לוי", "שירה מזרחי", "יונתן אברהם", "ליאת דהן", "נדב פרץ", "מאיה ביטון", "אלון חדד",
               "רותם עזרא", "ברק אוחיון", "נוגה יוסף", "אסף מלכה", "טל עמר"],
        "hi": ["आदित्य कुमार", "स्नेहा राव", "करण मल्होत्रा", "दिव्या नायर", "मनीष अग्रवाल", "रश्मि सक्सेना",
               "तरुण भट्ट", "मीनाक्षी अय्यर", "गौरव कपूर", "श्वेता बंसल", "निखिल सेठी", "पल्लवी दुबे"],
        "th": ["กิตติ สมบูรณ์", "ปวีณา ทองคำ", "วรวุฒิ ศรีงาม", "นภัสสร ใจงาม", "ชยพล รุ่งเรือง", "อรุณี แก้วใส",
               "ภาณุ บุญเลิศ", "สุนิสา มั่นคง", "ธีรวัฒน์ สายทอง", "พิมพ์ชนก ดวงดี", "อภิชาติ ศักดิ์ดี", "จิราพร เพชรงาม"],
        "places": ["清溪镇", "杏林村", "望江镇", "竹园乡", "金沙湾", "凤鸣村", "柳岸镇", "白鹭洲", "松涛村",
                   "青石镇", "梨花乡", "碧水湾"],
    }
    SCRIPT_SHAPES = ["{n}", "{n} 38", "{n}(45)", "{n}（男）", "{n}(F)", "患者：{n}", "{n}（女）", "{n} - RN",
                     "Dr {n}", "{n} 先生", "{n}님"]

    def test_names_in_scripts_without_case_are_redacted_with_any_qualifier(self):
        headers = ["Zxq", "Col7", "Notes By", "Visit Type", "Referral Source", "Provider", "Diagnosis",
                   "Status", "Class", "Location", "Contact Person", "姓名备注", "담당", "Info"]
        for locale in ("us", "cn", "kr", "jp"):
            columns = [(h, [shape.format(n=names[(i * 7) % 12]) for i in range(24)])
                       for names in self.SCRIPT_NAMES.values() for shape in self.SCRIPT_SHAPES for h in headers]
            self.assert_redacted(probe(self.tmp, "decide", columns, locale), f"scripts, locale {locale}")
        header = [f"{script} {k}" for script in self.SCRIPT_NAMES for k in range(len(self.SCRIPT_SHAPES))]
        rows = [[shape.format(n=names[(i * 7) % 12]) for names in self.SCRIPT_NAMES.values()
                 for shape in self.SCRIPT_SHAPES] for i in range(120)]
        p, out, report = self.run_file(write_csv(self.tmp / "scripts.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assert_hidden(p, out, report, [n for names in self.SCRIPT_NAMES.values() for n in names])

    # High (second review): a year and a month under any column name keeps only the year.
    def test_year_months_under_any_column_name_keep_only_the_year(self):
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        forms = [lambda y, m: f"{y}-{m:02d}", lambda y, m: f"{y}/{m:02d}", lambda y, m: f"{y}{m:02d}",
                 lambda y, m: f"{y}.{m:02d}", lambda y, m: f"{y}-{m}", lambda y, m: f"{y} {months[m - 1]}",
                 lambda y, m: f"{months[m - 1]} {y}", lambda y, m: f"{m:02d}/{y}",
                 lambda y, m: f"{months[m - 1]}-{y}"]
        headers = ["Visit Month", "Admit", "Encounter", "Period", "Admission", "Cohort Month", "Month",
                   "Month of Visit", "Reporting Period", "Sample Month", "Enrollment", "Enrolled", "Visit",
                   "Event", "Baseline", "Index Month", "Dx Month", "Ym", "Zxq", "Col1", "Diagnosis",
                   "Visit Type", "Treatment Arm", "Stage", "Notes", "Provider", "Visit Location", "State",
                   "Period Start", "Fecha", "Monat", "Mois", "月份", "Wave", "Cycle", "Epoch", "Snapshot"]
        values = [(2018 + k // 12, k % 12 + 1) for k in range(36)]
        columns = [(h, [form(*values[(i + k) % 36]) for i in range(72)])
                   for k, h in enumerate(headers) for form in forms]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a != "year"], [], "year-month columns")

    # Medium (third review): type, status and payer columns of identifier words are kept on
    # request instead of refused, and a default run exits 0.
    def test_payer_type_and_status_columns_can_be_kept(self):
        cols = {"Insurance Type": ["Medicare", "Commercial", "Medicaid"], "Insurance Status": ["Insured", "Uninsured"],
                "Insurance Plan Type": ["HMO", "PPO"], "Medicare Status": ["Enrolled", "Not Enrolled"],
                "Medicaid Eligible": ["Yes", "No"], "Subscriber Status": ["Active", "Inactive"],
                "Account Type": ["Checking", "Savings"], "License Status": ["Active", "Expired"],
                "Certificate Type": ["Birth", "Death"], "Login Status": ["Success", "Failed"],
                "Passport Status": ["Valid", "Expired"], "Insurance": ["Medicare", "Self-pay"],
                "Primary Insurance": ["Medicaid", "Commercial"], "Payer Type": ["Public", "Private"],
                "Coverage Type": ["Medicare Advantage", "Commercial"], "Plan Category": ["Bronze", "Gold"]}
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(60)]
        raw = write_csv(self.tmp / "payer.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in header:
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 0, (col, refused.stderr))
        p, out, report = self.run_file(raw, *[a for h in header for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)

    # Medium (third review): ages over 89 under a column name for age in another language.
    def test_ages_over_89_are_grouped_under_age_names_in_other_languages(self):
        header = ["Edad", "Alter", "Idade", "年龄", "年齢", "나이", "Età", "Leeftijd", "Wiek", "Возраст",
                  "العمر", "גיל", "आयु", "อายุ", "Edad (años)", "Alter in Jahren", "Âge", "Edad al diagnóstico",
                  "年龄（岁）", "연령", "Idade do paciente", "Eta (anni)", "Ålder", "Yaş", "sex"]
        ages = ["34", "95", "102", "61", "90", "89", "47", "91"]
        rows = [[ages[(i + k) % len(ages)] for k in range(len(header) - 1)] + ["F"] for i in range(40)]
        raw = write_csv(self.tmp / "ages.csv", header, rows)
        for locale in ("us", "es", "de", "cn", "jp", "kr", "fr", "it"):
            p, out, _ = self.run_file(raw, "--locale", locale)
            self.assertEqual(p.returncode, 0, (locale, p.stdout + p.stderr))
            for k, col in enumerate(header[:-1]):
                expected = ["90+" if int(row[k]) >= 90 else row[k] for row in rows]
                self.assertEqual([r[col] for r in out], expected, (locale, col))
        for col in ("Edad", "年龄", "Alter"):
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)
        # "ETA" alone is an arrival time, not an age by its name: it can be kept with --keep and
        # then keeps its numbers. A default run groups 90 to 99 as possible ages since round 2,
        # because whole numbers up to 125 under a name that names no measurement may be ages (it
        # kept them before).
        eta = write_csv(self.tmp / "eta.csv", ["ETA", "sex"], [[str(80 + i), "F"] for i in range(20)])
        p, out, _ = self.run_file(eta)
        self.assertEqual([r["ETA"] for r in out], [str(80 + i) for i in range(10)] + ["90+"] * 10)
        p, out, _ = self.run_file(eta, "--keep", "ETA")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ETA"] for r in out], [str(80 + i) for i in range(20)])

    # Lows of all three reviews: lower case names, initials, surnames alone, short notes and
    # over-redacted measurements.
    def test_documented_limits_are_redacted_and_blood_pressure_is_kept(self):
        cols = {
            "Group": [f"{f.lower()} {l.lower()}" for f, l in zip(self.FIRST, self.LAST)],
            "Staff Code": [f"{f[0]}{l[0]}" for f, l in zip(self.FIRST, self.LAST)],
            "Diagnosis": self.LAST, "Cohort": self.TOWNS,
            "Clinical Notes": [f"Spoke to {f} {l}." for f, l in zip(self.FIRST, self.LAST)],
            "Comments": [f"per {f}" for f in self.FIRST],
            "Initial": [f[0] for f in self.FIRST],
            "Blood Pressure": ["139/76", "120/80", "110/70", "145/92"],
        }
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(120)]
        p, out, report = self.run_file(write_csv(self.tmp / "limits.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in header[:-1]:
            self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)
        self.assertEqual([r["Blood Pressure"] for r in out], [row[-1] for row in rows])
        self.assert_hidden(p, out, report, self.FIRST + self.LAST + self.TOWNS)

    def test_vocabulary_counts_only_as_whole_values_and_not_under_person_names(self):
        verified = probe(self.tmp, "verified", [
            ("Sex", ["Male", "female", " F ", "Non-binary", "Unknown"]),
            ("Race", ["White", "Black or African American", "Native Hawaiian & Other Pacific Islander",
                      "Black / African American", "Two or More Races", "Patient Refused"]),
            ("Ethnicity", ["Not Hispanic or Latino", "Hispanic/Latino", "Unknown"]),
            ("Smoking", ["Never smoker", "Former smoker", "Current every day smoker"]),
            ("Response", ["CR", "Partial response", "Stable disease", "Not evaluable"]),
            ("Unit", ["mg/dL", "mmol/L", "%", "x10^9/L"]),
            ("Lab", ["5.2 mg/dL", "<0.5", ">= 10", "1,250", "12%", "120/80"]),
            ("Referring Physician", ["Unknown", "N/A", "none"]),
            ("State", ["California", "NH", "New Mexico", "Ontario"]),
            ("Country of Birth", ["Mexico", "Saint Vincent and the Grenadines", "USA", "Other"]),
        ])
        for header, flags in verified:
            self.assertTrue(all(flags), (header, flags))
        refused = probe(self.tmp, "verified", [
            # A vocabulary word with anything around it, or a name that is a vocabulary word.
            ("Sex", ["Male (wife)", "Female 45", "male nurse"]),
            ("Race", ["White, Alice", "Alice White", "Black Okafor"]),
            # Under a column name naming a person, a role, a relative, a contact or a place,
            # only missing-value words count.
            ("Referring Physician", ["White", "Yes", "Male", "Black"]),
            ("Visit Location", ["Left", "Right", "Normal"]),
            ("Contact Preference", ["Yes", "No"]),
            ("Mother", ["White"]),
            ("Lab", ["10-20", "5/10", "03/14", "7 apples"]),
            ("State", ["Larkspur County", "Oakshaw"]),
            ("Diagnosis", ["Heart Failure", "Asthma"]),
            # A relative word anywhere in the name, and words in brackets that are not this
            # tool's placeholders.
            ("Family History", ["White", "Black", "Yes"]),
            ("Col1", ["[OKAFOR]", "[ALICE]", "[CORLA_N]"]),
        ])
        for header, flags in refused:
            self.assertFalse(any(flags), (header, flags))

    def test_grammars_never_accept_a_bare_alphabetic_word(self):
        bare = ["Alice", "Okafor", "IV", "II", "III", "IIIA", "Tis", "Tx", "Nx", "Mx", "pTis", "GX", "A",
                "B", "AB", "O", "Stage", "Grade", "Low", "Poorly", "Rh", "Positive", "Gleason", "ECOG",
                "Ensembl", "rs", "Arg", "Gly", "c.", "p.", "Ala", "ENSG", "NM", "LOINC", "Atc", "Mutation"]
        for header in ("Col1", "Notes", "Provider", "Diagnosis", "Drug", "Variant", "Gene", "Code"):
            flags = probe(self.tmp, "grammar", [(header, bare)])[0][1]
            self.assertEqual([w for w, f in zip(bare, flags) if f], [], header)
        codes = {
            "Col1": ["E11.9", "J45.909", "C34.90", "V45.81", "E880.9", "2345-7", "14682-9", "718-7",
                     "rs113488022", "ENSG00000141510", "ENSG00000146648.18", "NM_004333.6",
                     "NM_001126112.3", "c.35G>A", "p.V600E", "p.(Arg248Gln)", "c.5266dupC",
                     "NM_004333.6(BRAF):c.1799T>A", "g.140453136A>T", "T2N0M0", "pT1aN1bM0", "T3", "N1",
                     "Stage IIIA", "stage 2", "FIGO IB1", "NYHA class III", "Grade 2", "G3", "low grade",
                     "poorly differentiated", "3+4=7", "Gleason 7", "ISUP 2", "ECOG 1", "ECOG PS 2",
                     "KPS 80", "A+", "O-", "AB positive", "B neg", "Rh+", "A型", "AB형"],
            "Stage": ["IIIA", "IV", "II", "0", "2a"], "TNM": ["Tis", "Tx", "Nx", "Mx"],
            "Blood Type": ["A", "B", "AB", "O"], "Dx Code": ["I10", "E119", "S72001A"],
            "ATC Code": ["C10AA05", "A10BA02", "N02BE01"], "Mutation": ["V600E", "G12D", "L858R", "T790M"],
        }
        for header, flags in probe(self.tmp, "grammar", list(codes.items())):
            self.assertEqual([v for v, f in zip(codes[header], flags) if not f], [], header)
        # A check digit that does not match is not a LOINC code; record numbers rarely pass.
        flags = probe(self.tmp, "grammar", [("Col1", ["2345-6", "14682-1", "48213-7"])])[0][1]
        self.assertEqual(flags, [False, False, False])
        # Subject numbers shaped like short ICD codes are codes only under a diagnosis name,
        # and letters after the dot of an ICD-10 code need a digit.
        flags = probe(self.tmp, "grammar", [("Subject Code", ["S01", "P012", "A101", "K12.ALIC", "T12.ABC"])])[0][1]
        self.assertEqual(flags, [False] * 5)

    def test_single_letters_from_more_than_one_group_are_not_a_category(self):
        cols = {"Sex": ["M", "F"], "Flag": ["H", "L", "N"], "Side": ["L", "R", "B"], "Reply": ["Y", "N"],
                "Abo": ["A", "B", "O"], "Initial": ["A", "C", "M", "R"], "Col1": ["M", "F", "H", "S"]}
        decided = {h: a for h, a, _ in probe(self.tmp, "decide", list(cols.items()))}
        self.assertEqual(decided, {"Sex": "keep", "Flag": "keep", "Side": "keep", "Reply": "keep",
                                   "Abo": "keep", "Initial": "redact", "Col1": "redact"})

    def test_numbers_shaped_like_dates_with_no_separator_are_not_kept(self):
        cols = {"Visit Day": ["0314", "1225", "0704"], "Col9": ["03142021", "12252020", "07042019"],
                "Code6": ["031421", "122520"], "Steps": ["4500", "7200", "10500"],
                "Counts": ["1012", "1130", "1225"], "Years": ["2015", "2018"]}
        decided = {h: a for h, a, _ in probe(self.tmp, "decide", list(cols.items()))}
        self.assertEqual(decided, {"Visit Day": "redact", "Col9": "redact", "Code6": "redact",
                                   "Steps": "keep", "Counts": "keep", "Years": "keep"})

    def test_plan_names_columns_for_the_persons_decision_and_run_warns_on_kept_text(self):
        header = ["Diagnosis", "Visit", "Sex", "Notes", "Glucose"]
        rows = [[["Heart Failure", "Asthma"][i % 2], ["Screening", "Week 4"][i % 2], "F",
                 "Discussed the plan at length with the family and the team today.", f"{5 + i % 3}.1"]
                for i in range(30)]
        raw = write_csv(self.tmp / "decide.csv", header, rows)
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("Need the person's decision (changed because the script cannot verify their values are free",
                      plan.stdout)
        self.assertIn("keep with --keep COLUMN once the person confirms it): Diagnosis, Visit", plan.stdout)
        self.assertIn("Free text, redacted and never kept", plan.stdout)
        refused = run("plan", str(raw), "--keep", "Notes")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("free text", refused.stderr)
        p, out, report = self.run_file(raw, "--keep", "Diagnosis", "--keep", "Visit")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Kept on the person's word, scrubbed for patterns only (2): Diagnosis, Visit", p.stdout)
        self.assertIn("the person must spot-check these columns", p.stdout)
        self.assertIn("scrubbed for identifier patterns only", report["kept_text_note"])
        self.assertIn("spot-check", report["kept_text_note"])
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], ["Diagnosis", "Visit"])
        self.assertEqual(report["columns_needing_decision"], [])
        self.assertEqual({r["Notes"] for r in out}, {"[REDACTED]"})
        # The residual check honours --keep for names in such a column, never for patterns.
        written = self.tmp / "out" / "decide_deidentified.csv"
        rows[0][0] = f"{self.FIRST[0]} {self.LAST[0]}"
        rows[1][1] = "call 415-555-0199"
        write_csv(written, header, [[r[0], r[1], r[2], "[REDACTED]", r[4]] for r in rows])
        bad = run("verify", str(written), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        self.assertIn("Visit: phone pattern", bad.stdout)
        self.assertNotIn("Diagnosis:", bad.stdout)

    def test_regression_table_of_an_ordinary_clinical_export(self):
        cols = {
            "Diagnosis": ["Heart Failure", "Type 2 Diabetes", "Asthma", "Chronic Kidney Disease"],
            "Diagnosis Code": ["I50.9", "E11.9", "J45.909", "N18.3"],
            "Drug": ["Metformin", "Lisinopril", "Albuterol", "Furosemide"],
            "ATC Code": ["A10BA02", "C09AA03", "R03AC02", "C03CA01"],
            "Dose": ["500 mg", "10 mg", "2.5 mg", "40 mg"],
            "Site": ["North Campus", "Harbor Clinic", "Lakeview Center"],
            "Primary Site": ["Breast", "Lung", "Colon", "Prostate"],
            "Hemoglobin": ["13.2", "11.8 g/dL", "12.5", "9.9"],
            "Creatinine": ["<0.5", "1.1", "0.9", "1.4"],
            "Lab Flag": ["H", "L", "N"],
            "LOINC Code": ["718-7", "2160-0", "2345-7", "2093-3"],
            "Blood Pressure": ["120/80", "139/76", "110/70"],
            "ECOG": ["0", "1", "2"],
            "Pain Score": ["3", "7", "0", "10"],
            "Stage": ["IIA", "IIIB", "IV", "Stage I"],
            "TNM": ["T2N0M0", "T3N1M0", "T1aN0M0"],
            "Grade": ["G1", "G2", "G3"],
            "Gene ID": ["ENSG00000141510", "ENSG00000146648", "ENSG00000133703"],
            "Variant": ["p.V600E", "c.35G>A", "p.G12D"],
            "Treatment Arm": ["Placebo", "Arm A", "Arm B"],
            "Visit": ["Screening", "Baseline", "Week 4", "End of Study"],
            "Visit Number": ["1", "2", "3", "4"],
            "Visit Date": ["2021-03-04", "2021-06-10", "2022-01-15"],
            "Race": ["White", "Asian", "Black or African American", "American Indian or Alaska Native"],
            "Ethnicity": ["Not Hispanic or Latino", "Hispanic or Latino"],
            "Sex": ["Female", "Male"],
            "State": ["California", "Oregon", "Nevada"],
            "Country": ["United States", "Mexico", "Canada"],
            "Smoking Status": ["Never smoker", "Former smoker", "Current every day smoker"],
            "Notes": ["Patient tolerated the infusion well and will return for the next cycle.",
                      "Reports mild nausea after the second dose, managed with ondansetron at home."],
        }
        self.assertEqual(len(cols), 30)
        header = list(cols)
        rows = [[cols[h][(i + k) % len(cols[h])] for k, h in enumerate(header)] for i in range(150)]
        raw = write_csv(self.tmp / "clinical30.csv", header, rows)
        unverified = ["Diagnosis", "Drug", "Site", "Primary Site", "Treatment Arm", "Visit"]
        expected = {h: "keep" for h in header}
        expected.update({h: "redact" for h in unverified + ["Notes"]})
        expected["Visit Date"] = "year"
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({d["column"]: d["action"] for d in report["decisions"]}, expected)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], unverified)
        for i, col in enumerate(header):
            if expected[col] == "keep":
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertEqual({r["Visit Date"] for r in out}, {"2021", "2022"})
        # The person confirms the six columns; the run keeps them and exits 0.
        p, out, report = self.run_file(raw, *[a for h in unverified for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            if col not in ("Notes", "Visit Date"):
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], unverified)
        ok = run("verify", str(self.tmp / "out" / "clinical30_deidentified.csv"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


# A probe of load_input's header checks, run in a child interpreter like PROBE: it takes a JSON
# file of header rows and prints, for each, "refused" or the positions it withholds.
HEADER_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import safe_harbor as s, deidentify as u
sc = s.Scrubber(u.load_locale("us"), 2026)
out = []
for headers in json.load(open(sys.argv[2], encoding="utf-8")):
    try:
        out.append(sorted(s.check_header_row(headers, sc)))
    except s.UsageError:
        out.append("refused")
print(json.dumps(out, ensure_ascii=False))
"""


def header_probe(tmp: Path, rows: list) -> list:
    path = tmp / "probe_headers.json"
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", "-B", "-c", HEADER_PROBE, str(SCRIPT.parent), str(path)],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                       timeout=120)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-2000:])
    return json.loads(p.stdout)


class NumbersDatesAndHeadersOfRoundTwo(unittest.TestCase):
    """Round 2 of the fail-closed review (2026-11-25, 1.0.1): record numbers that repeat across
    visits, numbers shaped like dates, birth years under any date column name, ages under age
    column names the word lists did not know, columns of relatives' and contacts' names that
    could be kept, exports that are not UTF-8, --keep over a shape finding, and a header row
    that is a patient's record. Each test takes the review's cases and generates more of the
    same kind. Every name, number, date and place here is invented."""

    FIRST = ["Corliss", "Thaddeo", "Anwen", "Brisolde", "Maeron", "Ostrava", "Velisse", "Junaro",
             "Feyrin", "Hadwyn", "Isaurel", "Plovette"]
    LAST = ["Quillmont", "Okerbrae", "Varnstead", "Quisterly", "Delmorrow", "Fintally", "Graywick",
            "Haskenvale", "Lorrimere", "Pemberwick", "Yarrowdell", "Zellmorrow"]
    # The column names of the review that kept repeated record numbers, then more of the kind
    # in other languages and neutral names. None of them names a measurement.
    RECORD_HEADERS = [
        "Chart", "Hosp No", "Hospital Number", "Pat No", "PatNo", "Patid", "Pat Nr", "Patient Ref",
        "Patientennummer", "Case No", "Visit No", "Encounter No", "Study No", "Subject No", "Reg No",
        "Registration", "Lab No", "Sample No", "PHN", "OHIP", "Health Card", "DNI", "CPF", "RRN",
        "NIP", "SUS", "病历号", "住院号", "患者番号", "등록번호", "Номер карты", "رقم الملف",
        "Reference", "Record", "Ref No", "File No", "Encounter", "Specimen", "Lab ID", "Order No",
        "Key", "Link", "Patient Key", "Registry No", "Admission No", "Episode", "Folder", "Dossier",
        "Case", "Tag", "Token", "Cohort Key", "Pat Ref", "Pt Ref", "Col6", "Col7", "Col8", "Value",
        "Result", "Entry", "Seen", "Measure", "Fallnummer", "NHC", "Expediente", "Cartella",
        "Numéro de dossier", "Número de historia", "Kit", "Box", "Slot", "X1", "Field 3",
        "Unnamed: 4", "V5", "Var12", "Data", "Info", "Group", "Visit", "Source", "Item", "Pt",
        "Persoonsnummer", "Henkilötunnus", "Fødselsnummer", "Rodné číslo", "Codice", "Matricule",
    ]
    # Integers of four or more digits that are measurements under these names.
    MEASUREMENT_HEADERS = [
        "WBC", "WBC (cells/uL)", "Platelets", "Platelet Count", "Steps", "Daily Steps",
        "Viral Load (copies/mL)", "HIV RNA copies", "Total Cost", "Charges USD", "Birth Weight (g)",
        "Distance m", "Read Count", "Reads", "Counts", "Dose mg", "Volume mL", "Ferritin",
        "Number of Visits", "Minutes", "Duration (days)", "Calories kcal", "Length of Stay",
    ]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_file(self, path: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict], dict]:
        out_dir = self.tmp / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        report = out_dir / "deidentification_report.json"
        return (p, read_rows(out) if out.exists() else [],
                json.loads(report.read_text(encoding="utf-8")) if report.exists() else {})

    @staticmethod
    def patients(digits: int, seed: int) -> list[int]:
        import random
        rng = random.Random(seed)
        return [rng.randrange(10 ** (digits - 1), 10 ** digits) for _ in range(20)]

    FORMS = {
        "plain": lambda n, d: str(n),
        "zero_padded": lambda n, d: str(n).zfill(d + 2),
        "dot_zero": lambda n, d: f"{n}.0",
        "dot_zero_zero": lambda n, d: f"{n}.00",
        "grouped": lambda n, d: f"{n:,}",
    }

    def longitudinal(self, digits: int, form: str, seed: int) -> list[str]:
        """20 patients seen 8 times each: 160 rows in which every record number repeats."""
        people = self.patients(digits, seed)
        return [self.FORMS[form](people[(i * 7) % 20], digits) for i in range(160)]

    # High (both reviewers): repeated record numbers of 6 to 9 digits, in any of their written
    # forms, were kept verbatim under ID-like and neutral column names.
    def test_repeated_record_numbers_are_not_kept_under_any_column_name(self):
        columns = [(h, self.longitudinal(d, form, k))
                   for k, h in enumerate(self.RECORD_HEADERS) for d in (6, 7, 8, 9)
                   for form in self.FORMS if not (form == "grouped" and d < 7)]
        decided = probe(self.tmp, "decide", columns)
        kept = sorted({h for h, action, _ in decided if action == "keep"})
        self.assertEqual(kept, [], "record numbers kept")
        # End to end: one column per form, every number gone, the run lists them for the person.
        header = [f"{h} {k}" for k, h in enumerate(self.RECORD_HEADERS[::6])]
        forms = list(self.FORMS)
        cols = [self.longitudinal(7 + k % 3, forms[k % len(forms)], 100 + k) for k in range(len(header))]
        rows = [[c[i] for c in cols] + ["F" if i % 2 else "M"] for i in range(160)]
        raw = write_csv(self.tmp / "longitudinal_numbers.csv", header + ["Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out)
        for c in cols:
            for v in set(c):
                self.assertNotIn(v.replace(",", "").split(".")[0].lstrip("0"), text.replace(",", ""))
        self.assertEqual([r["Sex"] for r in out], [row[-1] for row in rows])
        pending = {d["column"] for d in report["columns_needing_decision"]}
        decisions = {d["column"]: d for d in report["decisions"]}
        for col in header:
            self.assertIn(decisions[col]["action"], ("pseudonym_id", "redact"), col)
            # Listed for the person's decision, unless an identifier by its name or its values.
            self.assertTrue(col in pending or decisions[col]["finding"].startswith("column name")
                            or decisions[col]["finding"].endswith("identifiers"), col)
        self.assertIn("Need the person's decision", p.stdout)
        # Rows of one patient keep one pseudonym, so the linkage survives.
        self.assertEqual(out[0][header[0]], out[20][header[0]])
        # The check finds them in the raw file, which has no report.
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        # Measurements of four or more digits under a name that says so are kept.
        values = ["10500", "7200", "11200", "6400", "250000", "180000", "12345", "4500"]
        decided = probe(self.tmp, "decide", [(h, [values[(i + k) % 8] for i in range(64)])
                                             for k, h in enumerate(self.MEASUREMENT_HEADERS)])
        self.assertEqual([h for h, action, _ in decided if action != "keep"], [], "measurements")
        # Small whole numbers and decimals are measurements under any name.
        small = probe(self.tmp, "decide", [(h, ["1", "2", "3", "12", "87", "305"] * 5)
                                           for h in ("Value", "Col5", "Result", "Visit No")]
                      + [(h, ["13.2", "7.81", "105.4", "0.03"] * 5) for h in ("Value", "Col5")])
        self.assertEqual([h for h, action, _ in small if action != "keep"], [])

    # High (first reviewer) and medium (second reviewer): other numbers shaped like dates, ZIP
    # codes or record numbers under neutral names: YYMMDD, YYMM, packed dates without zeros,
    # Excel date-time serials and four-digit ZIP codes that lost their leading zero.
    def test_numbers_shaped_like_dates_and_zip_codes_are_not_kept(self):
        from datetime import date, timedelta
        days = [date(1985, 1, 1) + timedelta(days=397 * k + 11) for k in range(25)]
        late = [d for d in days if d.year >= 2015] + [date(2016 + k % 9, k % 12 + 1, k % 27 + 1) for k in range(20)]
        shapes = {
            "yymmdd": [d.strftime("%y%m%d") for d in days],
            "yymmdd_recent": [d.strftime("%y%m%d") for d in late],
            "yymm": [d.strftime("%y%m") for d in late],
            "mdyyyy": [f"{d.month}{d.day:02d}{d.year}" for d in days],
            "yyyymd": [f"{d.year}{d.month}{d.day}" for d in days],
            "mmddyy_no_zero": [f"{d.month}{d.day:02d}{d.year % 100:02d}" for d in late if d.month >= 10],
            "excel_serial": [f"{(d - date(1899, 12, 30)).days}.{(k * 625) % 10000:04d}" for k, d in enumerate(days)],
            "excel_day": [str((d - date(1899, 12, 30)).days) for d in days],
            "zip_lost_zero": ["2134", "1960", "7302", "8540", "6511", "2215", "1103", "3060", "4101",
                              "5401", "2492", "1810", "7030", "8901", "6880"],
            "zip_mixed": ["2134", "94110", "7302", "60614", "8540", "2215", "10027", "1103"],
        }
        headers = ["Value", "Result", "Key", "Entry", "Seen", "Col5", "Measure", "Data", "Field 2",
                   "X3", "Info", "Visit", "Reading", "Item 4", "V9"]
        columns = [(h, [vals[(i * 3) % len(vals)] for i in range(75)]) for name, vals in shapes.items()
                   for h in headers]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual(sorted({h for h, action, _ in decided if action == "keep"}), [], "kept")
        # A column of years is not a date: years are allowed.
        years = probe(self.tmp, "decide", [(h, ["2015", "2018", "2021", "1999", "2024"] * 6) for h in headers[:4]])
        self.assertEqual([a for _, a, _ in years], ["keep"] * 4)

    # High (first reviewer): a birth year of someone over 89 was kept under a date column name
    # that the rules did not read as a birth date.
    BIRTH_HEADERS = [
        "DoB", "BDate", "B_Date", "D of B", "Bth Dt", "Natal", "Natalicio", "Geburt", "Geburtstag",
        "Geburtsdatum", "Gebdatum", "Naissance", "Date de naissance", "Fecha de nacimiento",
        "Fecha_Nac", "F Nac", "Fec Nac", "FDN", "Nasc", "Data Nasc", "Data di nascita",
        "Data de nascimento", "Дата рождения", "ДР", "出生日期", "出生日", "生年月日", "生日", "誕生日",
        "생년월일", "출생일", "Doğum Tarihi", "Tanggal Lahir", "Ngày sinh", "วันเกิด", "تاريخ الميلاد",
        "תאריך לידה", "जन्मतिथि", "Event Date", "Admit", "Col5", "Date1", "Seen On", "Visit", "When",
        "Fecha", "Datum", "日期", "날짜", "Дата", "Index Date", "Start", "D1", "Encounter", "Baseline",
    ]

    def test_old_birth_years_are_withheld_under_any_date_column_name(self):
        births = ["1920-03-14", "1925-11-02", "1931-07-21", "1958-04-17", "1984-02-03", "1999-12-30",
                  "1936-01-09", "1937-06-30", "1970-08-08", "2001-05-05"]
        forms = [lambda s: s, lambda s: f"{s[8:10]}/{s[5:7]}/{s[:4]}", lambda s: f"{s[5:7]}/{s[8:10]}/{s[:4]}",
                 lambda s: s.replace("-", ""), lambda s: s[:7], lambda s: f"{s} 08:30"]
        header = list(self.BIRTH_HEADERS)
        index = [[(i + k) % 10 for k in range(len(header))] for i in range(60)]
        rows = [[forms[k % len(forms)](births[j]) for k, j in enumerate(r)] for r in index]
        raw = write_csv(self.tmp / "births.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for k, col in enumerate(header):
            for r, got in zip(index, [row[col] for row in out]):
                year = int(births[r[k]][:4])
                self.assertEqual(got, "[90_OR_OLDER]" if 2026 - year >= 90 else str(year), (col, births[r[k]]))
        # Kept text: a full date of someone over 89 becomes [90_OR_OLDER] too.
        notes = write_csv(self.tmp / "kept.csv", ["ref", "sex"], [["seen 1925-03-14", "F"], ["admitted 03/04/1931", "M"],
                                                                 ["on 2021-03-04", "F"]])
        p, out, _ = self.run_file(notes, "--keep", "ref")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["ref"] for r in out], ["seen [90_OR_OLDER]", "admitted [90_OR_OLDER]", "on 2021"])
        # The birth-date names are identifiers by name: they cannot be kept.
        for col in ("DoB", "Geburtsdatum", "Fecha de nacimiento", "出生日期", "생년월일", "Дата рождения"):
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)

    # Medium (first reviewer) and high (second reviewer): ages over 89 under age column names the
    # word lists did not know, in compounds and with any qualifier, and under neutral names.
    AGE_WORDS = ["Alter", "Ålder", "Alder", "Ikä", "Věk", "Yaş", "Kor", "Edat", "Vek", "Starost", "Edad",
                 "Idade", "Età", "Leeftijd", "Wiek", "Umur", "Usia", "Tuổi", "Életkor", "Vârsta",
                 "Возраст", "Вік", "Ηλικία"]
    AGE_SUFFIXES = ["", " bei Diagnose", " Dx", " ED", " at baseline", " (Jahre)", " (yrs)", " Pat.",
                    "_bei_ED", " vid diagnos", " ved diagnose", " (v)", " (roky)", " (yıl)", " (év)",
                    " al diagnòstic", " pri diagnóze", " Baseline", " 1", " at Dx", " en años", " (anos)",
                    " bei Aufnahme", " bei Erstdiagnose", " (Jahre) bei Diagnose", " Patient", " t0",
                    " Visit 1", " Screening", " - years", " [y]", " am Stichtag", " inclusion", " Op", " Tod"]
    AGE_HEADERS = ["Patientenalter", "Aufnahmealter", "Diagnosealter", "Eintrittsalter", "Alters",
                   "AlterBeiDiagnose", "Lebensalter", "Erkrankungsalter", "Anni", "Años", "Ans", "Jahre",
                   "Jaar", "年纪", "年紀", "연세", "Eta", "Eta Dx", "বয়স", "வயது", "Year Old", "Years Old",
                   "Ageing", "Kor", "Anni compiuti", "Roky", "Vuotta", "Yıl", "Év"]
    AGES = ["34", "95", "102", "61", "90", "89", "47", "91", "125", "18"]

    def test_ages_over_89_are_grouped_under_unknown_age_names(self):
        headers = [w + s for w in self.AGE_WORDS for s in self.AGE_SUFFIXES] + self.AGE_HEADERS
        columns = [(h, [self.AGES[(i + k) % 10] for i in range(40)]) for k, h in enumerate(headers)]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([h for h, action, _ in decided if action != "age"], [], "ages not grouped")
        header = headers[::9]
        rows = [[self.AGES[(i + k) % 10] for k in range(len(header))] for i in range(40)]
        p, out, _ = self.run_file(write_csv(self.tmp / "ages.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for k, col in enumerate(header):
            self.assertEqual([r[col] for r in out], ["90+" if int(row[k]) >= 90 else row[k] for row in rows], col)
        # Ages in months or days under a name that says so are converted first.
        months = write_csv(self.tmp / "months.csv", ["Months Old", "Days Old", "Alter (Monate)"],
                           [["1140", "34700", "1100"], ["420", "9000", "1080"], ["1100", "33000", "300"]])
        p, out, _ = self.run_file(months)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Months Old"] for r in out], ["90+", "420", "90+"])
        self.assertEqual([r["Days Old"] for r in out], ["90+", "9000", "90+"])
        self.assertEqual([r["Alter (Monate)"] for r in out], ["90+", "90+", "300"])
        # Text in an age column is not an age: a name there is redacted, not kept.
        named = write_csv(self.tmp / "named_age.csv", ["Edad", "Age"],
                          [[f"{self.FIRST[i % 12]} {self.LAST[i % 12]}", "unknown" if i % 3 else "45 years"]
                           for i in range(24)])
        p, out, report = self.run_file(named)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Edad"] for r in out}, {"[REDACTED]"})
        self.assertEqual({r["Age"] for r in out}, {"unknown", "45 years"})
        # Measurements whose values reach 90 to 125 are kept under a name that says what they are.
        values = ["92", "104", "61", "118", "88", "97", "125", "73"]
        decided = probe(self.tmp, "decide", [(h, [values[(i + k) % 8] for i in range(40)]) for k, h in enumerate(
            ["Heart Rate", "Pulse", "SpO2", "O2 Sat (%)", "HDL", "eGFR", "Karnofsky", "Barthel Index",
             "Systolic BP", "Score", "Weight kg", "IQ", "Glucose", "Study Day", "Days", "Minutes",
             "Duration", "Percent", "Resp Rate", "Temp F"])])
        self.assertEqual([h for h, action, _ in decided if action != "keep"], [])

    # Low (first reviewer): a number with the unit "y", "yo" or "mo" is an age when it is over 89.
    def test_ages_written_with_a_short_unit_are_grouped(self):
        cols = {h: ["95 y", "93 y", "102 y", "45 y", "61 yo", "1140 mo", "18 y"]
                for h in ("Value", "Result", "Seen", "Measure", "Col", "Duration", "Time", "Lab Score")}
        decided = probe(self.tmp, "decide", [(h, v * 6) for h, v in cols.items()])
        self.assertEqual([h for h, action, _ in decided if action not in ("age", "redact")], [])
        raw = write_csv(self.tmp / "short_units.csv", ["Value", "sex"], [[v, "F"] for v in cols["Value"]])
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse({"95 y", "93 y", "102 y", "1140 mo"} & {r["Value"] for r in out})
        kept = write_csv(self.tmp / "kept_units.csv", ["ref", "sex"], [["seen at 95 y", "F"], ["now 93y", "M"], ["45 y", "F"]])
        p, out, _ = self.run_file(kept, "--keep", "ref")
        self.assertEqual([r["ref"] for r in out], ["seen at 90+ years", "now 90+ years", "45 y"])

    # Medium (first reviewer): --keep was accepted for columns named for a relative, a contact,
    # a household member or the person's own name in other scripts.
    NAME_HEADERS = [
        "Next Kin", "Contact Person", "Relative", "Parent", "Sibling", "Child", "Partner", "Household",
        "Family", "Friend", "Landlord", "Lives In", "Maiden", "Last", "First", "Given", "姓名", "이름",
        "اسم", "患者姓名", "氏名", "Primary Contact", "Contact 2", "Household Member", "Family Members",
        "Lives With", "Emergency Contact Person", "Guardian 1", "Parent/Guardian", "Spouse Partner",
        "Mother Maiden", "Roommate", "Neighbor", "Cousin", "Grandmother", "Stepfather", "Boyfriend",
        "名前", "患者名前", "환자 이름", "성명", "الاسم", "שם", "नाम", "ชื่อ", "Имя", "Фамилия", "ФИО",
        "Sukunimi", "Soyadı", "Resides In", "Living With", "Visit Contact", "Secondary Contact Person",
    ]

    def test_relative_contact_and_name_columns_cannot_be_kept(self):
        latin = [f"{f} {l}" for f, l in zip(self.FIRST, self.LAST)]
        scripts = ["林清远", "邓若溪", "韩书瑶", "류현우", "배지민", "حسن المالكي", "ريم السالم", "אביב לוי",
                   "आदित्य कुमार", "กิตติ สมบูรณ์", "Олег Ветров", "Мира Ланская"]
        header = self.NAME_HEADERS
        rows = [[(scripts if any(ord(c) > 0x2ff for c in h) else latin)[(i + k) % 12] for k, h in enumerate(header)]
                for i in range(48)]
        raw = write_csv(self.tmp / "relatives.csv", header, rows)
        decided = probe(self.tmp, "decide", [(h, [row[k] for row in rows]) for k, h in enumerate(header)])
        self.assertEqual([h for h, _, kind in decided if kind != "identifier"], [], "not identifiers by name")
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertNotIn("Need the person's decision", plan.stdout)
        for col in header:
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col)
            self.assertIn("cannot be kept", refused.stderr)
            shown = refused.stdout + refused.stderr
            for v in latin + scripts:
                self.assertNotIn(v, shown)
        # Category values under the same names, and names whose last word is not a person, can be kept.
        cats = {"Contact": ["Mother", "Father", "Spouse"], "Family": ["Yes", "No"], "First": ["Yes", "No"],
                "Lives With": ["Spouse", "Parents", "Alone"], "Contact Method": ["Phone", "Email"],
                "Family History": ["Yes", "No", "Diabetes", "CAD in father"], "Household Size": ["2", "3", "4"],
                "Parent Consent": ["Signed", "Declined"], "Household": ["2 adults, 1 child", "1 adult", "Alone"]}
        raw = write_csv(self.tmp / "relative_categories.csv", list(cats),
                        [[cats[h][(i + k) % len(cats[h])] for k, h in enumerate(cats)] for i in range(36)])
        for col in cats:
            kept = run("plan", str(raw), "--keep", col)
            self.assertEqual(kept.returncode, 0, (col, kept.stderr))

    # Medium (first reviewer): a Windows-1252, Latin-1 or UTF-16 export stopped with a message
    # that gave no remedy.
    def test_exports_that_are_not_utf8(self):
        header = ["Patient", "Diagnóstico", "Sexo"]
        rows = [["Zoë Ménard", "Asthme", "F"], ["Renée Fürst", "Diabète", "F"], ["José Núñez", "EPOC", "M"],
                ["Ærin Østby", "Asthme", "M"]]
        text = "\r\n".join(",".join(r) for r in [header] + rows) + "\r\n"
        cases = {"latin1.csv": text.encode("latin-1"),
                 "cp1252.csv": (text.replace("Asthme", "Asthme – légère")).encode("cp1252"),
                 "utf16.csv": text.encode("utf-16"),
                 "utf16be_bom.csv": b"\xfe\xff" + text.encode("utf-16-be"),
                 "utf8_bom.csv": text.encode("utf-8-sig")}
        names = [r[0] for r in rows] + ["Zoë", "Ménard", "Fürst", "Núñez", "Østby"]
        for name, data in cases.items():
            path = self.tmp / name
            path.write_bytes(data)
            p, out, report = self.run_file(path)
            shown = p.stdout + p.stderr
            for v in names:
                self.assertNotIn(v, shown, name)
            if name.startswith(("latin1", "cp1252")):
                self.assertEqual(p.returncode, 2, (name, shown))
                self.assertIn("UTF-8", p.stderr)
                self.assertIn("--encoding", p.stderr)
                self.assertFalse((self.tmp / "out").exists() and any((self.tmp / "out").iterdir()))
                p, out, report = self.run_file(path, "--encoding", "cp1252")
            self.assertEqual(p.returncode, 0, (name, p.stdout + p.stderr))
            self.assertTrue(all(re.fullmatch(r"P\d{4}", r["Patient"]) for r in out), name)
            self.assertEqual([r["Sexo"] for r in out], ["F", "F", "M", "M"], name)
            written = (self.tmp / "out" / f"{path.stem}_deidentified.csv").read_bytes()
            written.decode("utf-8")  # the output is UTF-8 whatever the input was
            for v in names:
                self.assertNotIn(v.encode("utf-8"), written, name)
        # An encoding the file is not in is refused without quoting the bytes it could not read.
        bad = run("plan", str(self.tmp / "latin1.csv"), "--encoding", "utf-8")
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn("0x", bad.stderr)
        unknown = run("plan", str(self.tmp / "latin1.csv"), "--encoding", "no-such-codec")
        self.assertEqual(unknown.returncode, 2)

    # Medium (second reviewer): --keep over a shape finding was reported as verified, and the run
    # said identifier patterns inside such columns are replaced.
    def test_keep_over_a_shape_finding_is_kept_on_the_persons_word(self):
        import random
        rng = random.Random(7)
        rows = [[str(4100000 + 37 * i), f"94{rng.randrange(100, 999)}", f"{37.70 + rng.random() / 10:.4f}",
                 f"{-122.40 - rng.random() / 10:.4f}", ["Asthma", "COPD"][i % 2], "F"] for i in range(40)]
        header = ["Col1", "Col2", "Col3", "Col4", "Diagnosis", "Sex"]
        raw = write_csv(self.tmp / "shapes.csv", header, rows)
        p, out, report = self.run_file(raw, "--keep", "Col1", "--keep", "Col2", "--keep", "Col3", "--keep", "Col4",
                                       "--keep", "Diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Kept on the person's word, scrubbed for patterns only (5): Col1, Col2, Col3, Col4, Diagnosis",
                      p.stdout)
        replaced = [line for line in p.stdout.splitlines() if "identifier patterns inside them are replaced" in line]
        self.assertTrue(all("Col1" not in line and "Col2" not in line for line in replaced), replaced)
        decisions = {d["column"]: d for d in report["decisions"]}
        for col in ("Col1", "Col2", "Col3", "Col4", "Diagnosis"):
            self.assertFalse(decisions[col]["verified"], col)
            self.assertTrue(decisions[col]["kept_on_request"], col)
        self.assertTrue(decisions["Sex"]["verified"])
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]],
                         ["Col1", "Col2", "Col3", "Col4", "Diagnosis"])
        self.assertIn("spot-check", report["kept_text_note"])

    # Medium (second reviewer): a header row that is a patient's record was written verbatim
    # into the output, and names in it were never counted.
    def test_a_header_row_that_is_a_record_is_refused_or_withheld(self):
        records = [
            ["jane.doe@example.org", "Dx"], ["415-555-1234", "Dx"], ["S1", "Okafor Jane", "94110"],
            ["Okafor", "Jane", "1950-03-14"], ["912-34-5678", "Sex"], ["Quillon Marsh", "F", "61"],
            ["MRN 4482113", "Dx"], ["Dx", "Sex", "www.okafor-family.org"], ["2021-03-04", "Sex"],
            ["Corliss Quillmont", "Thaddeo Okerbrae", "Dx", "Sex", "Site", "Arm"], ["Dx", "+14155550123"],
            ["Sex", "Dx", "@jane_okafor"], ["Pt", "192.0.2.44"], ["03/14/1950", "F"],
        ]
        self.assertEqual(header_probe(self.tmp, records), ["refused"] * len(records))
        for k, rec in enumerate(records[:4]):
            path = self.tmp / f"hdr{k}.csv"
            write_csv(path, rec, [["A"] * len(rec), ["B"] * len(rec)])
            p, out, report = self.run_file(path)
            self.assertEqual(p.returncode, 2, (rec, p.stdout))
            self.assertIn("looks like", p.stderr)
            for cell in rec:
                if cell not in ("Dx", "Sex", "S1", "F"):
                    self.assertNotIn(cell, p.stdout + p.stderr)
            self.assertFalse((self.tmp / "out").exists() and any((self.tmp / "out").iterdir()))
        # One value-like or name-like header cell in an otherwise ordinary row is withheld in the
        # plan and the report, and renamed in the output.
        path = write_csv(self.tmp / "one_odd.csv",
                         ["Diagnosis", "94110", "Visit", "Haskenvale Lorrimere", "Sex", "Arm", "Site"],
                         [["Asthma", "3", "Screening", "x", "F", "A", "North"],
                          ["COPD", "4", "Week 4", "y", "M", "B", "South"]])
        p, out, report = self.run_file(path, "--keep", "Diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        written = (self.tmp / "out" / "one_odd_deidentified.csv").read_text(encoding="utf-8")
        self.assertEqual(written.splitlines()[0], "Diagnosis,column_2,Visit,column_4,Sex,Arm,Site")
        for cell in ("94110", "Haskenvale", "Lorrimere"):
            self.assertNotIn(cell, written)
            self.assertNotIn(cell, p.stdout + p.stderr + json.dumps(report))
        ok = run("verify", str(self.tmp / "out" / "one_odd_deidentified.csv"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        # Ordinary column names are neither refused nor withheld.
        ordinary = [
            "Patient Name", "Date of Birth", "Waist Circumference", "Height Cm", "Weight Kg", "Heart Rate",
            "Systolic BP", "HbA1c (%)", "BMI (kg/m2)", "eGFR (mL/min/1.73m2)", "Temp (°F)", "SpO2 %",
            "Age @ Dx", "Pt #", "ICD-10-CM", "COVID-19 Vaccine", "SARS-CoV-2 PCR", "IL-6 pg/mL",
            "PHQ-9", "GAD-7", "ESR (mm/hr)", "Visit 1 Date", "Tumor Size", "Gene Symbol", "Ejection Fraction",
            "Study Arm", "Consent Signed", "Referring Physician", "Visit Location", "First Name", "Zip Code",
            "Hospital Number", "Lab Result", "Treatment Arm", "Smoking Status", "Primary Site", "Grade",
            "Ki67 Index", "ENSG00000141510", "TP53", "CD4 Count", "Viral Load", "Insurance Type",
            "Discharge Disposition", "Length of Stay", "Admission Source", "Marital Status", "Preferred Language",
            "Mother Name", "Emergency Contact", "Blood Type", "Allergies", "Chief Complaint", "Hospital Course",
            "Follow Up", "Vital Status", "Cause of Death", "Pack Years", "Alcohol Use", "Drug Use",
            "Sample Type", "Collection Method", "Specimen Source", "Assay Platform", "Read Depth", "Variant Allele",
            "Protein Change", "Exon Number", "Copy Number", "Tumor Purity", "Stage Group", "Nodal Status",
            "Margin Status", "Lymphovascular Invasion", "Perineural Invasion", "Hormone Receptor", "Her2 Status",
            "Pathologic Response", "Overall Survival", "Progression Free", "Time To Event", "Censor Flag",
            "Visit 2", "Week 12", "Month 6", "Year 1", "Q1", "T0", "Baseline Value", "Change From Baseline",
            "Percent Change", "Dose Level", "Cohort Name", "Site Name", "Investigator Name", "Coordinator",
            "Data Entry Date", "Last Modified", "Record Status", "Form Version", "Event Name", "Repeat Instance",
            "Redcap Event", "Survey Timestamp", "Complete", "Unnamed: 0", "Col1", "X", "V12", "Var 3",
        ]
        self.assertEqual(header_probe(self.tmp, [ordinary])[0], [])

    def test_regression_table_of_ordinary_measurement_columns(self):
        # 30 columns of numbers as a clinical export writes them: a default run keeps every
        # measurement verbatim, pseudonymizes the record number that repeats across visits and
        # groups ages over 89.
        import random
        rng = random.Random(30)
        people = [str(rng.randrange(1000000, 9999999)) for _ in range(25)]
        cols = {
            "Record No": lambda i: people[i % 25],
            "Age": lambda i: str([34, 61, 95, 47, 102, 18][i % 6]),
            "Heart Rate": lambda i: str(55 + (i * 7) % 70), "Systolic BP": lambda i: str(95 + (i * 11) % 80),
            "Diastolic BP": lambda i: str(55 + (i * 5) % 40), "Temp C": lambda i: f"{36 + (i % 30) / 10:.1f}",
            "SpO2": lambda i: str(88 + i % 13), "Resp Rate": lambda i: str(12 + i % 14),
            "Weight kg": lambda i: f"{50 + (i * 3) % 70}.{i % 10}", "Height cm": lambda i: str(150 + i % 45),
            "BMI": lambda i: f"{18 + (i % 200) / 10:.1f}", "WBC": lambda i: str(3800 + (i * 370) % 9000),
            "Platelets (/uL)": lambda i: str(150000 + (i * 7000) % 250000),
            "Hemoglobin": lambda i: f"{9 + (i % 70) / 10:.1f}", "Sodium": lambda i: str(130 + i % 15),
            "Potassium": lambda i: f"{3 + (i % 25) / 10:.1f}", "Creatinine": lambda i: f"{0.5 + (i % 30) / 10:.1f}",
            "Glucose": lambda i: str(70 + (i * 13) % 250), "HbA1c (%)": lambda i: f"{5 + (i % 60) / 10:.1f}",
            "eGFR": lambda i: str(15 + (i * 9) % 105), "LDL": lambda i: str(60 + (i * 7) % 130),
            "HDL": lambda i: str(30 + (i * 3) % 70), "Troponin": lambda i: f"{(i % 50) / 1000:.3f}",
            "CRP": lambda i: f"{(i % 80) / 10:.1f}", "Length of Stay": lambda i: str(1 + i % 21),
            "Number of Admissions": lambda i: str(i % 6), "Pain Score": lambda i: str(i % 11),
            "Charlson Index": lambda i: str(i % 9), "Total Cost": lambda i: str(8000 + (i * 997) % 60000),
            "Year of Diagnosis": lambda i: str(2005 + i % 20),
        }
        self.assertEqual(len(cols), 30)
        header = list(cols)
        rows = [[cols[h](i) for h in header] for i in range(200)]
        p, out, report = self.run_file(write_csv(self.tmp / "measurements30.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        actions = {d["column"]: d["action"] for d in report["decisions"]}
        expected = {h: "keep" for h in header}
        expected.update({"Record No": "pseudonym_id", "Age": "age"})
        self.assertEqual(actions, expected)
        for k, col in enumerate(header):
            if expected[col] == "keep":
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        self.assertEqual({r["Age"] for r in out}, {"34", "61", "90+", "47", "18"})
        self.assertNotIn(people[0], json.dumps(out))

    # Low (first reviewer): a few closed-vocabulary words are also surnames or unit words, and
    # were verified under a neutral column name.
    def test_race_words_and_bare_units_count_only_under_their_own_column_names(self):
        words = ["Black", "White", "Mixed", "Multiple", "Chinese", "Korean", "Cuban", "Samoan", "Latino",
                 "Ma", "Mo", "Ng", "Min", "Mm", "Kg"]
        for header in ("Col1", "Value", "Group", "Result", "Notes"):
            flags = probe(self.tmp, "verified", [(header, words)])[0][1]
            self.assertEqual([w for w, f in zip(words, flags) if f], [], header)
        race = probe(self.tmp, "verified", [(h, words[:9]) for h in ("Race", "Ethnicity", "Race/Ethnicity", "Raza")])
        units = probe(self.tmp, "verified", [(h, words[9:]) for h in ("Unit", "Units", "UOM", "Result Unit")])
        for header, flags in race + units:
            self.assertTrue(all(flags), header)


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
