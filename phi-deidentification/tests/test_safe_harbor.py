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
        # Round 4: a column named for notes or comments cannot be kept, short or not.
        p = run("plan", str(FIXTURE), "--reference-year", REFERENCE_YEAR, "--keep", "contact_note")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("notes", p.stderr)
        # The same short cells under an ordinary name, kept on the person's word, lose their patterns.
        rows = read_rows(FIXTURE)
        header = [h if h != "contact_note" else "follow_up" for h in rows[0]]
        renamed = write_csv(self.tmp / "synthetic_18_identifiers.csv", header,
                            [[r[h] for h in rows[0]] for r in rows])
        p = run("run", str(renamed), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR,
                "--keep", "follow_up")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(out_dir / "synthetic_18_identifiers_deidentified.csv")
        notes = [r["follow_up"] for r in out]
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


def output_names(report: dict, header: list[str]) -> dict[str, str]:
    """The output name of each input column: its own, or column_N for a name the run withheld
    (round 3 withholds a column name with a word it does not know, such as "Zxq")."""
    by_index = {d["index"]: d.get("output_column") or d["column"] for d in report["decisions"]}
    return {h: by_index[i] for i, h in enumerate(header, start=1)}


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
        # Round 7: decimals under a name that names no measurement ("e") are the person's decision.
        self.assertEqual([r["e"] for r in out], ["[REDACTED]"] * 4)
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
            if col != "birth_order":
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        # Round 4: in a file with a column of years (year_of_diagnosis), whole numbers from 1 to 31 under
        # a column name that names no measurement may be a month or a day written in a column of its own:
        # birth_order is redacted until the person keeps it.
        self.assertEqual({r["birth_order"] for r in out}, {"[REDACTED]"})
        p, out = self.run_file(write_csv(self.tmp / "ordinary.csv", header, rows), "--keep", "birth_order")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["birth_order"] for r in out], [row[-1] for row in rows])

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
        # A yes/no column and measurements under such a name are kept as they are. Round 7: numbers under a
        # name that names no measurement ("Children") wait for the person's word, which --keep can give,
        # since they are not words (this test kept them by default before).
        for i, col in enumerate(header):
            if col in ("Insured", "wavelength_nm", "sex"):
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertEqual({r["Children"] for r in out}, {"[REDACTED]"})
        p, out, _ = self.run_file(raw, "--keep", "Children")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Children"] for r in out], [row[5] for row in rows])
        # Round 3: a column named for the person ("Subject") that holds names is an identifier by its
        # name, like "Participant", and cannot be kept (it could be kept before). Subject numbers can.
        refused = run("plan", str(raw), "--keep", "Subject")
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("cannot be kept", refused.stderr)
        numbers = write_csv(self.tmp / "subject_numbers.csv", ["Subject", "sex"],
                            [[str(1001 + i % 7), "F"] for i in range(30)])
        kept = run("plan", str(numbers), "--keep", "Subject")
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
        # Round 4: a column named for notes cannot be kept, so it is listed apart, not as a decision.
        self.assertEqual([d["column"] for d in data["columns_needing_decision"]],
                         ["x1", "x2", "x3", "x4", "diagnosis"])
        self.assertEqual([d["column"] for d in data["columns_that_cannot_be_kept"]], ["note"])
        # Round 4: a column named for notes cannot be kept, however short its cells.
        refused = run("plan", str(raw), "--keep", "note")
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("notes", refused.stderr)
        # Kept on the person's word, the diagnosis is scrubbed and named with the warning.
        p, out, report = self.run_file(raw, "--keep", "diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in ("diagnosis",):
            i = header.index(col)
            self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertIn("scrubbed for identifier patterns only", p.stdout)
        # kept_unverified_columns (round 2; it was kept_unverified_text_columns) also lists number
        # columns kept over a shape finding.
        listed = json.loads(report.read_text(encoding="utf-8"))["kept_unverified_columns"]
        self.assertEqual([d["column"] for d in listed], ["diagnosis"])
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
        # Round 8: a column name of a person word and a word that can be a surname (Ward Nurse) is withheld and
        # written as column_N, so the columns are read by their output names.
        names = output_names(json.loads(report.read_text(encoding="utf-8")), header)
        for col in self.ROLE_HEADERS:
            self.assertEqual({r[names[col]] for r in out}, {"[REDACTED]"}, col)
        self.assertEqual([r["sex"] for r in out], [row[-1] for row in rows])
        # The residual check finds the same names in a file that has no report.
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        for i, col in enumerate(header[:-1], start=1):
            label = col if names[col] == col else f"#{i} (name withheld)"
            self.assertIn(f"{label}: text values shaped like names", bad.stdout)
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
        # Round 7: Visit Number names no measurement, so its numbers wait for the person's word too.
        verified = {"Treatment Responder"}
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
            p, out, report = self.run_file(raw)
            self.assertEqual(p.returncode, 0, (form, p.stdout + p.stderr))
            # Round 3: "Zxq" is withheld and written as column_N.
            shown = output_names(json.loads(report.read_text(encoding="utf-8")), header)
            for k, col in enumerate(self.MONTH_HEADERS):
                expected = [str(months[(i + k) % 36][0]) for i in range(180)]
                self.assertEqual([r[shown[col]] for r in out], expected, (form, col))
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
                # Round 3: "Zxq" is withheld and written as column_1.
                shown = output_names(json.loads(report.read_text(encoding="utf-8")), header)
                for col in self.SCRIPT_HEADERS:
                    self.assertTrue(all(re.fullmatch(r"\[REDACTED\]|P\d{4}", r[shown[col]]) for r in out),
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
        # Round 3: "Zxq 21" is not a column name the script knows, so the output calls it column_22.
        names = output_names(report, header + ["sex"])
        self.assertEqual(names["Zxq 21"], "column_22")
        for col in header:
            self.assertTrue(all(re.fullmatch(r"\[REDACTED\]|P\d{4}", r[names[col]]) for r in out), col)
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
        # Round 9: a column named for notes is redacted whatever it holds (this test reduced it to the year before).
        self.assertEqual([(h, a) for h, a, _ in decided if a != "year" and h != "Notes"], [], "year-month columns")
        self.assertEqual({a for h, a, _ in decided if h == "Notes"}, {"redact"})

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
            "Col1": ["E11.9", "J45.909", "C34.90", "V45.81", "E880.9",
                     "rs113488022", "ENSG00000141510", "ENSG00000146648.18", "NM_004333.6",
                     "NM_001126112.3", "c.35G>A", "p.V600E", "p.(Arg248Gln)", "c.5266dupC",
                     "NM_004333.6(BRAF):c.1799T>A", "g.140453136A>T", "T2N0M0", "pT1aN1bM0", "T3", "N1",
                     "Stage IIIA", "stage 2", "FIGO IB1", "NYHA class III", "Grade 2", "G3", "low grade",
                     "poorly differentiated", "3+4=7", "Gleason 7", "ISUP 2", "ECOG 1", "ECOG PS 2",
                     "KPS 80", "A+", "O-", "AB positive", "B neg", "Rh+", "A型", "AB형"],
            "Stage": ["IIIA", "IV", "II", "0", "2a"], "TNM": ["Tis", "Tx", "Nx", "Mx"],
            "Blood Type": ["A", "B", "AB", "O"], "Dx Code": ["I10", "E119", "S72001A"],
            "ATC Code": ["C10AA05", "A10BA02", "N02BE01"], "Mutation": ["V600E", "G12D", "L858R", "T790M"],
            "LOINC Code": ["2345-7", "14682-9", "718-7"], "Lab Test": ["2345-7", "14682-9", "718-7"],
        }
        for header, flags in probe(self.tmp, "grammar", list(codes.items())):
            self.assertEqual([v for v, f in zip(codes[header], flags) if not f], [], header)
        # A check digit that does not match is not a LOINC code. Round 5: a LOINC code counts only under a
        # column name that names a LOINC code, a lab, a test or an observation, because record numbers
        # often carry the same mod 10 check digit.
        flags = probe(self.tmp, "grammar", [("LOINC Code", ["2345-6", "14682-1", "48213-7"]),
                                            ("Col1", ["2345-7", "14682-9", "718-7"])])
        self.assertEqual([f for _, f in flags], [[False, False, False], [False, False, False]])
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
        # Round 5: Visit Date keeps its year, so Visit Number (1 to 4) beside it is a possible date element.
        unverified = ["Diagnosis", "Drug", "Site", "Primary Site", "Treatment Arm", "Visit", "Visit Number"]
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
        # Round 9: a letter tells the columns apart (a number beside the one in Col6 9 is withheld now).
        header = [f"{h} {chr(65 + k)}" for k, h in enumerate(self.RECORD_HEADERS[::6])]
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
        unkeepable = {d["column"] for d in report["columns_that_cannot_be_kept"]}
        decisions = {d["column"]: d for d in report["decisions"]}
        for col in header:
            self.assertIn(decisions[col]["action"], ("pseudonym_id", "redact"), col)
            # Listed for the person's decision, unless an identifier by its name or its values. Round 6:
            # numbers of five or more digits under a column name that names no measurement cannot be kept
            # on the person's word, so those columns are listed as ones that cannot be kept instead.
            self.assertTrue(col in pending or col in unkeepable or decisions[col]["finding"].startswith("column name")
                            or decisions[col]["finding"].endswith("identifiers"), col)
        self.assertEqual(pending & set(header), set())
        self.assertIn("cannot be kept under their names", p.stdout)
        # Rows of one patient keep one pseudonym, so the linkage survives.
        self.assertEqual(out[0][header[0]], out[20][header[0]])
        # The check finds them in the raw file, which has no report.
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        # Measurements of four or more digits under a name that says so are kept.
        values = ["10500", "7200", "11200", "6400", "250000", "180000", "12345", "4500"]
        decided = probe(self.tmp, "decide", [(h, [values[(i + k) % 8] for i in range(64)])
                                             for k, h in enumerate(self.MEASUREMENT_HEADERS)])
        # Round 3: a number of days from 10000 up is not a duration (27 years) but may be an Excel
        # date serial, so "Duration (days)" and "Length of Stay" holding them are no longer kept. Round 6: a
        # count of a patient's visits never reaches six digits, so "Number of Visits" holding repeated
        # six-digit numbers (250000, 180000) is a record number too (it was kept before).
        # Round 9: every cell of a measurement column is checked, and numbers of five or more digits are trusted only
        # under a name for money, a large count, a distance or a small unit of time, so Birth Weight (g), Dose mg,
        # Volume mL and Ferritin holding 10500 to 250000 are the person's decision (this test kept them before).
        self.assertEqual([h for h, action, _ in decided if action != "keep"],
                         ["Birth Weight (g)", "Counts", "Dose mg", "Volume mL", "Ferritin", "Number of Visits",
                          "Duration (days)", "Length of Stay"], "measurements")
        short = probe(self.tmp, "decide", [(h, [str(1 + (i * 7) % 900) for i in range(64)])
                                           for h in ("Duration (days)", "Length of Stay")])
        self.assertEqual([h for h, action, _ in short if action != "keep"], [])
        # Small whole numbers and decimals were measurements under any name. Round 7: numbers fail closed by name,
        # so under a name that names no measurement they are the person's decision, and under one that does they
        # are kept.
        small = probe(self.tmp, "decide", [(h, ["1", "2", "3", "12", "87", "305"] * 5)
                                           for h in ("Value", "Col5", "Result", "Visit No")]
                      + [(h, ["13.2", "7.81", "105.4", "0.03"] * 5) for h in ("Value", "Col5")])
        self.assertEqual([action for _, action, _ in small], ["redact"] * 6)
        small = probe(self.tmp, "decide", [(h, ["1", "2", "3", "12", "87", "305"] * 5)
                                           for h in ("Glucose", "Pain Score", "Steps", "Dose (mg)")]
                      + [(h, ["13.2", "7.81", "105.4", "0.03"] * 5) for h in ("Creatinine", "Ratio")])
        self.assertEqual([action for _, action, _ in small], ["keep"] * 6)

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
        # A column of years is not a date: years are allowed. Round 7: under a name for a year; under a name
        # that names no measurement and no year (Value, Result, Key, Entry) they are the person's decision.
        years = probe(self.tmp, "decide", [(h, ["2015", "2018", "2021", "1999", "2024"] * 6)
                                           for h in headers[:4] + ["Year", "Admit Year", "Dx Yr", "Jahr"]])
        self.assertEqual([a for _, a, _ in years], ["redact"] * 4 + ["keep"] * 4)

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
        # Round 3: "ДР" can be a person's initials as well as a birth date, so its name is withheld.
        shown = output_names(report, header)
        self.assertTrue(shown["ДР"].startswith("column_"))
        for k, col in enumerate(header):
            for r, got in zip(index, [row[shown[col]] for row in out]):
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
        # Round 6: Col1 held record numbers of seven digits and Col2 ZIP codes, which --keep now refuses under
        # a column name that names no measurement; the shape findings kept here are four-digit numbers and
        # possible ages.
        rows = [[str(4100 + 37 * i), str(20 + (i * 7) % 85), f"{37.70 + rng.random() / 10:.4f}",
                 f"{-122.40 - rng.random() / 10:.4f}", ["Asthma", "COPD"][i % 2], "F"] for i in range(40)]
        header = ["Col1", "Col2", "Col3", "Col4", "Diagnosis", "Sex"]
        long_rows = [[str(4100000 + 37 * i), f"94{rng.randrange(100, 999)}"] + r[2:] for i, r in enumerate(rows)]
        refused = self.run_file(write_csv(self.tmp / "long.csv", header, long_rows), "--keep", "Col1")[0]
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("five or more digits", refused.stderr)
        refused = self.run_file(write_csv(self.tmp / "long.csv", header, long_rows), "--keep", "Col2")[0]
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
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
        # Round 4: a header cell of five or more digits (a ZIP code here) is refused like an identifier
        # pattern, without being printed.
        path = write_csv(self.tmp / "zip_header.csv", ["Diagnosis", "94110", "Visit", "Sex"],
                         [["Asthma", "3", "Screening", "F"], ["COPD", "4", "Week 4", "M"]])
        p, out, report = self.run_file(path)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("94110", p.stdout + p.stderr)
        # One value-like or name-like header cell in an otherwise ordinary row is withheld in the
        # plan and the report, and renamed in the output.
        path = write_csv(self.tmp / "one_odd.csv",
                         ["Diagnosis", "9411", "Visit", "Haskenvale Lorrimere", "Sex", "Arm", "Site"],
                         [["Asthma", "3", "Screening", "x", "F", "A", "North"],
                          ["COPD", "4", "Week 4", "y", "M", "B", "South"]])
        p, out, report = self.run_file(path, "--keep", "Diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        written = (self.tmp / "out" / "one_odd_deidentified.csv").read_text(encoding="utf-8")
        self.assertEqual(written.splitlines()[0], "Diagnosis,column_2,Visit,column_4,Sex,Arm,Site")
        for cell in ("9411", "Haskenvale", "Lorrimere"):
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


# A probe of the table reader with a stand-in for openpyxl, run in a child interpreter like
# PROBE. openpyxl is not installed where these tests run, so this checks the script's own
# handling of a workbook (the first sheet only, the header row, --no-header, duplicate names),
# not openpyxl itself. It prints what the reader returned, and whatever it printed.
XLSX_PROBE = r"""
import contextlib, io, json, sys, types
sys.path.insert(0, sys.argv[1])
spec = json.load(open(sys.argv[2], encoding="utf-8"))

class Sheet:
    def __init__(self, rows):
        self.rows = rows
    def iter_rows(self, values_only=True):
        return iter([tuple(r) for r in self.rows])

class Book:
    def __init__(self, sheets):
        self.sheetnames = [name for name, _ in sheets]
        self.sheets = dict(sheets)
    def __getitem__(self, name):
        return Sheet(self.sheets[name])
    def close(self):
        pass

fake = types.ModuleType("openpyxl")
fake.load_workbook = lambda path, read_only=True, data_only=True: Book(spec["sheets"])
sys.modules["openpyxl"] = fake
import safe_harbor as s
out = io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
    try:
        data, meta = s.read_table(s.Path(sys.argv[3]), no_header=spec.get("no_header", False))
        result = {"headers": meta["headers"], "rows": [[r[h] for h in meta["headers"]] for r in data],
                  "sheets_skipped": len(meta.get("sheets_skipped") or [])}
    except s.UsageError as e:
        result = {"refused": str(e)}
result["printed"] = out.getvalue()
print(json.dumps(result, ensure_ascii=False))
"""


# A probe of decide_columns over whole tables, for rules that look at neighbouring columns.
TABLE_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import safe_harbor as s, deidentify as u
locale = u.load_locale("us")
sc = s.Scrubber(locale, 2026)
out = []
for table in json.load(open(sys.argv[2], encoding="utf-8")):
    headers = [h for h, _ in table]
    n = len(table[0][1])
    data = [{h: v[i] for h, v in table} for i in range(n)]
    out.append([[d["column"], d["action"]] for d in s.decide_columns(data, headers, locale, sc, set(), set(), 2026)])
print(json.dumps(out, ensure_ascii=False))
"""


def table_probe(tmp: Path, tables: list) -> list:
    path = tmp / "probe_tables.json"
    path.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", "-B", "-c", TABLE_PROBE, str(SCRIPT.parent), str(path)],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                       timeout=300)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-2000:])
    return json.loads(p.stdout)


class HeadersNumbersAndDatePartsOfRoundThree(unittest.TestCase):
    """Round 3 of the fail-closed review (2026-11-25, 1.0.1): a first row of data read as the
    header row, numbers in scientific notation, ages beside one decimal or outlier, numeric
    month and day columns, coordinates that are alone or not side by side, numbers judged by
    their majority, Excel serials under time and day names, --keep over identifier words with
    a qualifier, and the smaller gaps. Each test takes the review's cases and generates more of
    the same kind. Every name, number, date and place here is invented."""

    SURNAMES = ["Okonkwo", "Quillmont", "Okerbrae", "Varnstead", "Delmorrow", "Fintally", "Graywick",
                "Haskenvale", "Lorrimere", "Pemberwick"]
    GIVEN = ["Marguerite", "Thaddeo", "Anwen", "Brisolde", "Maeron", "Velisse", "Corliss", "Isaurel"]
    OTHER_SCRIPTS = ["山田太郎", "岚溪月", "林子涵", "김민수", "박서윤", "محمد", "يوسف الحسن", "יוסי",
                     "Иванов", "Ольга Петрова", "Αλέξανδρος", "ราตรี", "प्रिया"]

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

    def name_cells(self) -> list[str]:
        """A first row's cell that is a person's name, in the shapes the review found printed."""
        s, g = self.SURNAMES, self.GIVEN
        cells = []
        for k, last in enumerate(s):
            first, other = g[k % len(g)], s[(k + 3) % len(s)]
            cells += [last, first, last.upper(), last.lower(), f"{last} {first[0]}", f"{first[0]}. {last}",
                      f"Dr. {last}", f"Dr {last}", f"Seen by {last}", f"{last}, {first[0]}",
                      f"{first.lower()} {last.lower()}", f"{first[0].lower()}{last.lower()}",
                      f"{last.lower()}.{first.lower()}", f"van der {last}", f"O'{last}", f"{last}-{other}",
                      f"Mr {last}", f"Mrs. {last}", f"Prof. {last}", f"{last} MD", f"{last} (wife)",
                      f"Nurse {last}", f"{first} {last}", f"{last} {other}", f"{last}2"]
        return cells + self.OTHER_SCRIPTS + ["Müllerová", "Ødegårdsen", "Łukasikowa", "Ñandúez"]

    @staticmethod
    def write_lines(path: Path, rows: list[list[str]]) -> Path:
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        return path

    # High (both reviewers): in a file with no header row, a first row of a single-word or
    # titled name, sex, a diagnosis and a number was shown, reported and written as the header.
    def test_a_first_row_of_data_never_shows_a_name(self):
        cells = self.name_cells()
        rows = []
        for c in cells:
            rows += [[c, "F", "Asthma", "61", "Yes"], [c, "Diagnosis", "Sex"], ["Sex", "Visit", c]]
        for headers, result in zip(rows, header_probe(self.tmp, rows)):
            position = headers.index(next(c for c in headers if c in cells)) + 1
            self.assertTrue(result == "refused" or position in result, (headers, result))
        # The review's file, end to end: the name is never printed, reported or written.
        sex = ["F", "M"]
        dx = ["Asthma", "COPD", "Heart Failure"]
        body = [[self.SURNAMES[i % 10], sex[i % 2], dx[i % 3], str(30 + i % 50), ["Yes", "No"][i % 2]]
                for i in range(1, 60)]
        raw = self.write_lines(self.tmp / "headerless.csv", [["Okonkwo", "F", "Asthma", "61", "Yes"]] + body)
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        self.assertNotIn("Okonkwo", plan.stdout + plan.stderr)
        self.assertIn("--no-header", plan.stdout)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        written = (self.tmp / "out" / "headerless_deidentified.csv").read_text(encoding="utf-8")
        self.assertNotIn("Okonkwo", written.splitlines()[0])
        self.assertNotIn("Okonkwo", p.stdout + p.stderr + json.dumps(report))
        # With --no-header the first row is data: every row is read, the columns are column_N,
        # and the names are text the script cannot verify, so they are redacted.
        p, out, report = self.run_file(raw, "--no-header")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(len(out), 60)
        self.assertEqual(list(out[0]), ["column_1", "column_2", "column_3", "column_4", "column_5"])
        self.assertEqual({r["column_1"] for r in out}, {"[REDACTED]"})
        self.assertEqual([r["column_2"] for r in out], ["F"] + [row[1] for row in body])
        shown = p.stdout + p.stderr + json.dumps(report) + json.dumps(out)
        for name in self.SURNAMES:
            self.assertNotIn(name, shown)
        # A first row whose cells repeat (a surname twice) is refused without printing it.
        twice = self.write_lines(self.tmp / "twice.csv", [["Quillmont", "Quillmont", "F"], ["A", "B", "M"]])
        p = run("plan", str(twice))
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("Quillmont", p.stdout + p.stderr)
        p = run("plan", str(twice), "--no-header")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("Quillmont", p.stdout + p.stderr)

    # The other half of the same finding: ordinary column names are still shown, and a name the
    # script withheld is shown once the person confirms it.
    def test_ordinary_column_names_are_shown_and_others_on_the_persons_word(self):
        ordinary = [
            "Diagnosis", "Drug", "Medication", "Site", "Arm", "Visit", "Race", "Sex", "Gender", "State",
            "Country", "Notes", "Age", "Hemoglobin", "Creatinine", "ICD10", "Dx Code", "Admit Date",
            "Discharge Date", "LOS", "Sodium", "BMI", "Weight (kg)", "Height (cm)", "Smoker", "Alcohol",
            "Comorbidities", "Outcome", "Mortality", "Readmission", "ED Visit", "ICU Admission",
            "Ventilator", "Dialysis", "Insurance", "Payer", "Language", "Interpreter Needed",
            "Marital Status", "Education", "Income", "Employment", "Housing", "BRCA1", "EGFR Mutation",
            "PD-L1 TPS", "Ki-67", "ER Status", "PR Status", "HER2", "MSI", "TMB", "Tumor Grade",
            "Histology", "Laterality", "Procedure", "Surgeon", "Anesthesia", "ASA Class",
            "Blood Loss (mL)", "Complications", "Discharge Disposition", "Follow-up (months)",
            "Recurrence", "Vital Status", "Days to Death", "Censored", "Event", "Time (days)", "Group",
            "Treatment", "Control", "Placebo", "Dose (mg)", "Route", "Frequency", "Start Date",
            "Stop Date", "Adverse Event", "Severity", "Serious", "Related", "Action Taken",
            "CTCAE Grade", "Lab Test", "Lab Value", "Units", "Reference Low", "Reference High",
            "Abnormal Flag", "Specimen Type", "Collection Date", "Result Date", "Ordering Department",
            "Encounter Type", "Encounter Date", "Primary Diagnosis", "Secondary Diagnosis",
            "Chief Complaint", "Triage Level", "Arrival Mode", "Disposition", "Pain", "GCS",
            "Temperature", "Pulse", "Resp", "SpO2", "SBP", "DBP", "MAP", "Glucose", "Lactate", "WBC",
            "Hgb", "Plt", "Na", "K", "Cl", "HCO3", "BUN", "Cr", "AST", "ALT", "Alk Phos", "T Bili",
            "Albumin", "INR", "PT", "PTT", "Troponin I", "BNP", "CRP", "ESR", "Procalcitonin",
            "D-dimer", "Ferritin", "LDH", "HbA1c", "TSH", "Free T4", "Vitamin D", "Cholesterol",
            "LDL-C", "HDL-C", "Triglycerides", "eGFR", "Urine Protein", "Culture Result", "Organism",
            "Antibiotic", "Susceptibility", "MIC", "Record ID", "MRN", "Subject ID", "Study ID",
            "Patient ID", "redcap_event_name", "redcap_repeat_instrument", "dob", "sex_at_birth",
            "zip", "city", "phone", "email", "first_name", "last_name", "age_at_dx", "bmi_cat",
            "hx_htn", "hx_dm", "meds_count", "visit_1_date", "visit_2_date", "wt_kg", "ht_cm",
            "sbp_mmhg", "a1c_pct", "egfr_ml_min", "Geschlecht", "Sexo", "Diagnóstico", "Fecha",
            "Datum", "Peso", "Talla", "Edad", "Alter", "Âge", "性别", "诊断", "日期", "年龄", "성별",
            "진단", "나이", "Пол", "Диагноз", "Дата", "Возраст", "الجنس", "التشخيص", "מין", "תאריך",
            "ENSG00000141510", "TP53", "CD4 Count", "Viral Load", "IL-6 pg/mL", "COVID-19 Vaccine",
            "SARS-CoV-2 PCR", "PHQ-9", "GAD-7", "Unnamed: 0", "Col1", "X", "V12", "Var 3", "Q1", "T0",
        ]
        chunks = [ordinary[i:i + 20] for i in range(0, len(ordinary), 20)]
        for chunk, withheld in zip(chunks, header_probe(self.tmp, chunks)):
            self.assertEqual(withheld, [], [chunk[i - 1] for i in withheld] if isinstance(withheld, list) else chunk)
        # A column name the script does not know is withheld until the person confirms it.
        header = ["Diagnosis", "Haskenvale Score", "Sex"]
        raw = write_csv(self.tmp / "odd_name.csv", header,
                        [[["Asthma", "COPD"][i % 2], str(i % 7), "F"] for i in range(30)])
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertNotIn("Haskenvale", plan.stdout)
        self.assertIn("#2 (name withheld)", plan.stdout)
        for extra in (["--keep-name", "#2"], ["--keep-all-names"]):
            p, out, report = self.run_file(raw, *extra)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("Haskenvale Score", p.stdout)
            self.assertIn("Haskenvale Score", out[0])
        bad = run("plan", str(raw), "--keep-name", "Haskenvale Score")
        self.assertEqual(bad.returncode, 2)

    # Medium: numbers in scientific notation, as Excel writes long record, account and phone
    # numbers in a CSV, were kept under every column name.
    def test_numbers_written_with_an_exponent_are_not_kept(self):
        import random
        rng = random.Random(3)
        people = [rng.randrange(10 ** 6, 10 ** 7) for _ in range(15)] + [rng.randrange(10 ** 9, 10 ** 10)
                                                                        for _ in range(5)]
        forms = [lambda n: f"{n:.5E}", lambda n: f"{n:.5e}", lambda n: f"{n:.4E}".replace("E+0", "E+"),
                 lambda n: f"{n:.6E}", lambda n: f"{n * 10 ** 4:.5E}"]
        headers = ["Value", "Result", "Chart", "Col1", "Key", "Ref", "Seen", "Entry", "Record", "Field",
                   "Info", "Data", "Hosp No", "Pat Nr", "Admit", "Updated", "Created", "When", "Obs", "X3",
                   "Var7", "Item", "Source", "Contact", "Number", "Account", "Link"]
        columns = [(h, [forms[k % len(forms)](people[(i * 7) % 20]) for i in range(80)])
                   for k, h in enumerate(headers)]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "exponent numbers kept")
        # Under a column name that names a measurement, scientific notation is a measurement.
        loads = [f"{(i % 9 + 1) * 1.37:.2E}".replace("E+00", "E+06") for i in range(40)]
        kept = probe(self.tmp, "decide", [(h, loads) for h in ("Viral Load (copies/mL)", "HIV RNA copies",
                                                               "Platelets", "Total Cost")])
        self.assertEqual([h for h, a, _ in kept if a != "keep"], [])
        rows = [[columns[k][1][i] for k in range(4)] + ["F"] for i in range(80)]
        p, out, report = self.run_file(write_csv(self.tmp / "exponents.csv", headers[:4] + ["Sex"], rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out)
        for c in columns[:4]:
            for v in set(c[1]):
                self.assertNotIn(v.split("E")[0].split("e")[0], text)
        # Round 4: "Chart" says record, so its long numbers are a record number by name, which cannot be
        # kept. Round 6: the other three hold numbers of five or more digits under a column name that names
        # no measurement, so they cannot be kept on the person's word either (they were the person's decision
        # before): they are listed as columns that cannot be kept under their names.
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, set())
        self.assertEqual({d["column"] for d in report["columns_that_cannot_be_kept"]}, set(headers[:4]) - {"Chart"})
        self.assertEqual({d["column"]: d["action"] for d in report["decisions"]}["Chart"], "pseudonym_id")

    # Medium: one decimal, one "<1" or one outlier switched off the over-89 cap.
    def test_ages_over_89_are_grouped_beside_any_other_value(self):
        ages = [str(20 + (i * 7) % 69) for i in range(40)] + ["93", "95", "97", "102"]
        headers = ["Value", "Result", "Kor", "Eta", "Info", "Obs", "Field", "Col4", "Years Seen", "Item",
                   "Measure", "Entry", "Var2", "Seen", "Px", "Group Value"]
        odd = ["0.5", "<1", "130", "-1", "1.5", "unknown", ">100", "0", "250", "4.5"]
        columns = [(h, ages + [odd[k % len(odd)], odd[(k + 3) % len(odd)]]) for k, h in enumerate(headers)]
        decided = probe(self.tmp, "decide", columns)
        # Round 7: the other numbers of such a column are not verified either, so under a name that does not say
        # age the column is redacted (this test grouped it as ages, keeping the numbers under 90, before); under
        # an age word (Kor, Eta) it is grouped.
        self.assertEqual([(h, a) for h, a, _ in decided if a != ("age" if h in ("Kor", "Eta") else "redact")], [],
                         "ages over 89 not grouped or redacted")
        rows = [[columns[k][1][i] for k in range(5)] + ["F"] for i in range(len(columns[0][1]))]
        p, out, report = self.run_file(write_csv(self.tmp / "ages_mixed.csv", headers[:5] + ["Sex"], rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in headers[:5]:
            self.assertFalse({"93", "95", "97", "102"} & {r[col] for r in out}, col)
            if col in ("Kor", "Eta"):
                self.assertIn("90+", {r[col] for r in out}, col)
            else:
                self.assertEqual({r[col] for r in out}, {"[REDACTED]"}, col)

    # High: numeric month and day-of-month columns were kept, so the admission date could be
    # rebuilt from the year beside them.
    def test_numeric_month_and_day_columns_are_date_elements(self):
        days = [str(1 + (i * 7) % 31) for i in range(93)]
        months = [str(1 + (i * 5) % 12) for i in range(93)]
        weekdays = [str(1 + i % 7) for i in range(93)]
        day_headers = ["Day", "Admit Day", "Visit Day", "Dx Day", "Date Day", "Day of Month", "DayOfMonth",
                       "DD", "dd", "Day_1", "Day of Admission", "Admission Day", "Discharge Day", "Birth Day",
                       "Tag", "Jour", "Dia", "Día", "Giorno", "Dag", "入院日", "日", "일", "День", "Event Day",
                       "Onset Day", "Surgery Day", "Death Day", "Day (admit)", "admit_dd", "dd_admit"]
        month_headers = ["Month", "Admit Month", "Discharge Month", "Dx Month", "Date Month", "Visit Date Month",
                         "MM", "mm", "Mon", "Mth", "Month_1", "Mois", "Monat", "Mes", "Mese", "Maand", "入院月",
                         "月", "월", "Месяц", "Onset Month", "Event Month", "Month of Visit", "admit_mm",
                         "mm_admit", "Surgery Mth", "Birth Month"]
        week_headers = ["Weekday", "Day of Week", "DayOfWeek", "DOW", "Admit Weekday", "Wochentag"]
        columns = ([(h, days) for h in day_headers] + [(h, months) for h in month_headers]
                   + [(h, weekdays) for h in week_headers])
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "date elements kept")
        # Beside a year: one-letter or two-letter parts of a date that shares the year's name.
        years = [str(2018 + i % 5) for i in range(60)]
        tables = [
            [("Admit Year", years), ("Admit M", months[:60]), ("Admit D", days[:60]), ("Sex", ["F", "M"] * 30)],
            [("Y", years), ("M", months[:60]), ("D", days[:60])],
            [("yyyy", years), ("Mo", months[:60]), ("Dy", days[:60])],
            [("Dx Yr", years), ("Dx Mo", months[:60]), ("Dx Dy", days[:60])],
            [("D", days[:60]), ("M", months[:60]), ("Y", years)],
        ]
        for table in table_probe(self.tmp, tables):
            for h, a in table:
                if h in ("Admit Year", "Y", "yyyy", "Dx Yr", "Sex"):
                    self.assertEqual(a, "keep", (h, table))
                else:
                    self.assertNotEqual(a, "keep", (h, table))
        # A year beside an ordinary small number (a stage) is not a date.
        table = table_probe(self.tmp, [[("Year of Diagnosis", years), ("Stage", [str(1 + i % 4) for i in range(60)]),
                                        ("ECOG", [str(i % 3) for i in range(60)])]])[0]
        self.assertEqual([a for _, a in table], ["keep", "keep", "keep"])
        # Durations, counts and visit labels stay measurements.
        controls = probe(self.tmp, "decide", [
            ("Days", [str(1 + i % 30) for i in range(60)]), ("LOS Days", [str(1 + i % 30) for i in range(60)]),
            ("Length of Stay (days)", [str(1 + i % 30) for i in range(60)]),
            ("Months", [str(i % 61) for i in range(60)]), ("Follow-up Months", [str(i % 61) for i in range(60)]),
            ("Study Day", [str(1 + i * 7) for i in range(60)]), ("Month 6 Pain Score", [str(i % 11) for i in range(60)]),
            ("Stage", [str(1 + i % 4) for i in range(60)]),
            ("Day 28 Viral Load", [str(40 + i) for i in range(60)])])
        self.assertEqual([h for h, a, _ in controls if a != "keep"], [])
        # Round 4: a column whose numbers cover the twelve months is a possible month under any column
        # name that names no measurement, so "Visit Number" of 1 to 12 is no longer a control.
        self.assertEqual(probe(self.tmp, "decide", [("Visit Number", months[:60])])[0][1], "redact")
        # End to end: the review's table.
        header = ["Admit Year", "Admit Month", "Admit Day", "Sex"]
        rows = [[str(2015 + i % 8), months[i], days[i], "F" if i % 2 else "M"] for i in range(93)]
        p, out, report = self.run_file(write_csv(self.tmp / "dateparts.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        actions = {d["column"]: d["action"] for d in report["decisions"]}
        self.assertEqual(actions["Admit Year"], "keep")
        self.assertEqual({r["Admit Month"] for r in out} | {r["Admit Day"] for r in out}, {"[REDACTED]"})
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, {"Admit Month", "Admit Day"})
        self.assertIn("date element", p.stdout)

    # High: latitude, longitude and UTM columns that were alone, not side by side, or under a
    # name the rules did not know were kept.
    def test_coordinates_alone_or_apart_are_not_kept(self):
        import random
        rng = random.Random(11)
        lat = [f"{37.2 + rng.random() * 0.6:.5f}" for _ in range(40)]
        lon = [f"{-122.9 + rng.random() * 0.6:.5f}" for _ in range(40)]
        near_equator = [f"{1.2 + rng.random() * 0.3:.4f}" for _ in range(40)]
        east = [f"{550000 + rng.random() * 9000:.2f}" for _ in range(40)]
        north = [f"{4180000 + rng.random() * 9000:.2f}" for _ in range(40)]
        headers = ["Home Lon", "Patient Lat", "Patient Long", "Geo_Lat", "geo_lon", "Lat (deg)", "Lt", "Ln",
                   "Home Lat", "X", "Y", "x_coord", "y_coord", "Coord", "Position", "Location", "Breitengrad",
                   "Längengrad", "Latitud", "Longitud", "经度", "纬度", "緯度", "위도", "Широта", "Col1", "Value",
                   "Notes", "Point", "Where", "Geo", "Pos 1"]
        columns = [(h, (lat, lon, near_equator)[k % 3]) for k, h in enumerate(headers)]
        columns += [(h, (east, north)[k % 2]) for k, h in enumerate(["Easting", "Northing", "UTM E", "UTM N",
                                                                    "X", "Y", "Value", "Col2", "Grid Ref"])]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "coordinates kept")
        # Decimals of four or more places under a measurement name stay; so do two-place decimals under a
        # measurement name and a column named for the lateral meniscus. Round 6: two-place decimals from 10
        # to 180 under a neutral name (Value) are a possible coordinate, redacted until the person keeps them
        # (this test kept them before); decimals below 10 under it (a z-score) stay.
        controls = probe(self.tmp, "decide", [
            ("Troponin", [f"0.0{i % 9}{i % 7}{i % 5}" for i in range(40)]),
            ("Weight kg", [f"{60 + i % 30}.{1000 + i}" for i in range(40)]),
            ("Propensity Score", [f"0.{4000 + i * 13}" for i in range(40)]),
            ("Hemoglobin", [f"{12 + i % 9}.{i % 10}{i % 7}" for i in range(40)]),
            ("Value", [f"{i % 9}.{i % 10}{i % 7}" for i in range(40)]),
            ("Lat Meniscus Tear", ["Yes", "No"] * 20)])
        # Round 7: decimals below 10 under Value, which names no measurement, are the person's decision too.
        # Round 9: four places from 1 to 180 under Weight kg are a possible coordinate (this test kept them before).
        self.assertEqual([h for h, a, _ in controls if a != "keep"], ["Weight kg", "Value"])
        self.assertEqual(probe(self.tmp, "decide", [("Value", [f"{12 + i % 9}.{i % 10}{i % 7}" for i in range(40)])]),
                         [["Value", "redact", "unverified"]])
        # End to end, the review's table: a latitude and a longitude with a column between them.
        header = ["Home Lat", "Mid", "Home Lon", "Sex"]
        rows = [[lat[i], ["Asthma", "COPD"][i % 2], lon[i], "F"] for i in range(40)]
        p, out, report = self.run_file(write_csv(self.tmp / "apart.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out)
        for v in lat + lon:
            self.assertNotIn(v, text)

    # Medium: a number column was judged by its majority, so up to 49% record numbers, or one
    # ZIP code, year or serial in a column of small numbers, passed.
    def test_numbers_are_judged_cell_by_cell(self):
        import random
        rng = random.Random(5)
        records = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(30)]
        columns = []
        for share in (0.02, 0.1, 0.3, 0.45):
            for h in ("Value", "Result", "Col4", "Var", "Obs", "Answer", "Response Value"):
                vals = [records[i % 30] if rng.random() < share else str(1 + rng.randrange(300)) for i in range(200)]
                vals[7] = records[0]
                columns.append((h, vals))
        for odd in (records[3], "1925", "94110", "1234", "44269.4375", "00512", "4.52783E+06", "552345.12"):
            for h, base in (("Value", ["12.5", "13.1", "7"]), ("Result", ["3", "4"]), ("Col2", ["0.8", "1.25"])):
                vals = [base[i % len(base)] for i in range(300)]
                for i in range(0, 300, 50):
                    vals[i] = odd
                columns.append((h, vals))
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(k, h) for k, (h, a, _) in enumerate(decided) if a == "keep"], [], "kept")
        header = ["Value", "Result", "Sex"]
        rows = [[columns[0][1][i], columns[-1][1][i], "F"] for i in range(200)]
        p, out, report = self.run_file(write_csv(self.tmp / "minority.csv", header, rows))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out)
        for v in records + ["552345.12"]:
            self.assertNotIn(v, text)

    # Medium: Excel date and time serials were kept under time and day names, which made them
    # measurements.
    def test_excel_serials_under_time_and_day_names_are_dates(self):
        frac = [f"{43000 + (i * 37) % 900}.{(i * 7919) % 10000:04d}" for i in range(200)]
        whole = [str(43000 + (i * 37) % 900) for i in range(200)]
        headers = ["Time", "Event Time", "Start Time", "Visit Day", "Day", "Days", "Duration", "LOS",
                   "Admit Time", "Time (days)", "Stop Time", "Interval", "Days Since Admission", "Delay",
                   "Elapsed", "Weeks", "Time Point"]
        columns = [(h, v) for h in headers for v in (frac, whole)]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "serials kept")
        # Small units of time and money make large numbers plausible. Round 9: an Excel serial with a time (four
        # places) under Total Cost is the person's decision, as under every measurement name but a small unit of
        # time (this test kept it before); whole numbers stay.
        controls = probe(self.tmp, "decide", [(h, v) for h in ("Minutes", "Seconds", "Duration (min)",
                                                              "Time (s)", "Hours", "Total Cost")
                                              for v in (frac, whole)])
        self.assertEqual([h for h, a, _ in controls if a != "keep"], ["Total Cost"])

    # Medium (cut short in the review): --keep was accepted for columns whose names carry an
    # identifier word, when their values were words: a type or status column of an identifier
    # word, a person's column name such as Subject, a social network, and phone and postal code
    # column names in other languages.
    def test_keep_is_refused_over_identifier_words_holding_names(self):
        names = [self.SURNAMES[i % 10] for i in range(40)]
        refused = ["Phone Type", "Email Status", "SSN Flag", "License Status", "Account Type", "Zip Type",
                   "Address Type", "Name Type", "Patient ID Status", "Username Type", "Device ID Type",
                   "Subject", "Member", "Donor", "Recipient", "Resident", "Policyholder", "Insured",
                   "Twitter", "Instagram", "Facebook", "TikTok", "LinkedIn", "WeChat", "Telefon", "Teléfono",
                   "Telefone", "Telefoon", "Celular", "PLZ", "CEP", "Postleitzahl", "Código Postal",
                   "Code Postal", "Codice Postale"]
        header = refused + ["Sex"]
        raw = write_csv(self.tmp / "named.csv", header, [[names[i]] * len(refused) + ["F"] for i in range(40)])
        for col in refused:
            p = run("plan", str(raw), "--keep", col)
            self.assertEqual(p.returncode, 2, (col, p.stdout))
            self.assertIn("cannot be kept", p.stderr, col)
            self.assertNotIn("Quillmont", p.stdout + p.stderr)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in refused:
            self.assertFalse(set(self.SURNAMES) & {r[col] for r in out}, col)
        # The same names with category words or numbers are kept, or can be.
        ok = {"Phone Type": ["Mobile", "Home", "Work"], "Insurance Type": ["Medicare", "Commercial", "Medicaid"],
              "Subject": [str(1001 + i % 20) for i in range(40)], "Twitter": ["Yes", "No"],
              "Member": ["Yes", "No"], "Email Status": ["Valid", "Invalid"], "Donor": ["Yes", "No"]}
        header = list(ok)
        raw = write_csv(self.tmp / "category.csv", header,
                        [[ok[h][i % len(ok[h])] for h in header] for i in range(40)])
        p, out, report = self.run_file(raw, *[a for h in header for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for col in header:
            self.assertEqual({r[col] for r in out}, set(ok[col]), col)

    # Low: decimal ages under age names the lists did not know, ages with a unit of years in
    # another language under an age column in months, and measurement names with an identifier
    # word at their end.
    def test_smaller_age_and_record_number_gaps(self):
        decided = probe(self.tmp, "decide", [(h, ["95.2", "102.7", "45.5", "61.0", "33.3"] * 8)
                                             for h in ("Kor", "Vanus", "Amzius", "Vecums", "Ageing", "Aging",
                                                       "Kac yasinda", "Yasi")])
        self.assertEqual([(h, a) for h, a, _ in decided if a != "age"], [])
        values = ["94 ans", "95 anos", "95 años", "95 anni", "95 jahre", "95岁", "95歳", "95세", "95 år",
                  "95 lat", "18 mois", "24"]
        raw = write_csv(self.tmp / "months_old.csv", ["Months Old", "Sex"], [[v, "F"] for v in values])
        p, out, _ = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Months Old"] for r in out], ["90+"] * 10 + ["18 mois", "24"])
        import random
        rng = random.Random(9)
        people = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(20)]
        decided = probe(self.tmp, "decide", [(h, [people[i % 20] for i in range(120)])
                                             for h in ("Glucose Case", "Count Episode", "Count Specimen",
                                                       "Count Patient", "Dose Encounter", "Score Participant",
                                                       "Level Chart", "Total Subject", "Amount Sample")])
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [])

    # Low: a file separated by semicolons (the European Excel default) needed a re-save.
    def test_a_semicolon_file_is_read_with_delimiter(self):
        path = self.tmp / "semi.csv"
        rows = [["Diagnosis", "Sex", "Glucose"]] + [[["Asthma", "COPD"][i % 2], "F", f"{5 + i % 3},1"]
                                                    for i in range(20)]
        path.write_text("\n".join(";".join(r) for r in rows) + "\n", encoding="utf-8")
        p = run("plan", str(path))
        self.assertEqual(p.returncode, 2)
        self.assertIn("--delimiter", p.stderr)
        p, out, report = self.run_file(path, "--delimiter", ";")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        written = self.tmp / "out" / "semi_deidentified.csv"
        self.assertTrue(written.read_text(encoding="utf-8").startswith("Diagnosis;Sex;Glucose"))
        ok = run("verify", str(written), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)

    # Low: the workbook path could not be exercised. With a stand-in for openpyxl: only the first
    # sheet is read, no sheet name is printed, --no-header works, and duplicate names are refused
    # without printing them.
    def test_workbook_reading_with_a_stand_in_for_openpyxl(self):
        book = self.tmp / "book.xlsx"
        book.write_bytes(b"PK")

        def read(spec):
            path = self.tmp / "xlsx_spec.json"
            path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            p = subprocess.run([sys.executable, "-I", "-B", "-c", XLSX_PROBE, str(SCRIPT.parent), str(path),
                                str(book)], capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            return json.loads(p.stdout)

        sheets = [["Okerbrae Family", [["Diagnosis", "Sex", None], ["Asthma", "F", None], ["COPD", 1, 2.5]]],
                  ["Quillmont", [["x"], ["y"]]]]
        got = read({"sheets": sheets})
        self.assertEqual(got["headers"], ["Diagnosis", "Sex", "column_3"])
        self.assertEqual(got["rows"], [["Asthma", "F", ""], ["COPD", "1", "2.5"]])
        self.assertEqual(got["sheets_skipped"], 1)
        self.assertNotIn("Okerbrae", got["printed"] + json.dumps(got))
        self.assertNotIn("Quillmont", got["printed"] + json.dumps(got))
        got = read({"sheets": sheets[:1], "no_header": True})
        self.assertEqual(got["headers"], ["column_1", "column_2", "column_3"])
        self.assertEqual(len(got["rows"]), 3)
        got = read({"sheets": [["S", [["Varnstead", "Varnstead"], ["a", "b"]]]]})
        self.assertIn("refused", got)
        self.assertNotIn("Varnstead", got["refused"] + got["printed"])

    def test_regression_table_of_an_ordinary_clinical_export_after_round_three(self):
        import random
        rng = random.Random(33)
        records = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(25)]
        cols = {
            "Record ID": lambda i: records[i % 25],
            "Diagnosis": lambda i: ["Heart Failure", "Type 2 Diabetes", "Asthma", "Chronic Kidney Disease"][i % 4],
            "ICD-10": lambda i: ["I50.9", "E11.9", "J45.909", "N18.3"][i % 4],
            "Drug": lambda i: ["Metformin", "Lisinopril", "Albuterol", "Furosemide"][i % 4],
            "Dose (mg)": lambda i: ["500", "10", "2.5", "40"][i % 4],
            "Specimen Site": lambda i: ["Breast", "Lung", "Colon", "Prostate"][i % 4],
            "Study Site": lambda i: ["Site 01", "Site 02", "Site 03"][i % 3],
            "Hemoglobin": lambda i: f"{9 + (i % 70) / 10:.1f}",
            "Creatinine": lambda i: f"{0.5 + (i % 30) / 10:.2f}",
            "Troponin": lambda i: f"{(i % 50) / 1000:.4f}",
            "Pain Score": lambda i: str(i % 11),
            "ECOG": lambda i: str(i % 4),
            "Charlson Index": lambda i: str(i % 9),
            "Gene Symbol": lambda i: ["TP53", "EGFR", "KRAS", "BRAF"][i % 4],
            "Ensembl ID": lambda i: ["ENSG00000141510", "ENSG00000146648", "ENSG00000133703"][i % 3],
            "Variant": lambda i: ["p.V600E", "c.35G>A", "p.G12D"][i % 3],
            "Treatment Arm": lambda i: ["Placebo", "Arm A", "Arm B"][i % 3],
            "Visit": lambda i: ["Screening", "Baseline", "Week 4", "End of Study"][i % 4],
            "Visit Number": lambda i: str(1 + i % 6),
            "Study Day": lambda i: str(1 + (i * 7) % 400),
            "Admit Year": lambda i: str(2015 + i % 9),
            "Length of Stay (days)": lambda i: str(1 + i % 21),
            "Age": lambda i: str([34, 61, 95, 47, 102, 18][i % 6]),
            "Race": lambda i: ["White", "Asian", "Black or African American"][i % 3],
            "Sex": lambda i: ["Female", "Male"][i % 2],
            "State": lambda i: ["California", "Oregon", "Nevada"][i % 3],
            "Country": lambda i: ["United States", "Mexico", "Canada"][i % 3],
            "Smoking Status": lambda i: ["Never smoker", "Former smoker", "Current every day smoker"][i % 3],
            "Weight (kg)": lambda i: f"{50 + (i * 3) % 70}.{i % 10}",
            "Notes": lambda i: ["Patient tolerated the infusion well and will return for the next cycle.",
                                "Reports mild nausea after the second dose, managed at home."][i % 2],
        }
        self.assertEqual(len(cols), 30)
        header = list(cols)
        rows = [[cols[h](i) for h in header] for i in range(200)]
        raw = write_csv(self.tmp / "clinical30_r3.csv", header, rows)
        # Round 4: Visit Number (1 to 6) in a file with a column of years (Admit Year) is a possible month
        # or day of a date written in columns of its own, so it is the person's decision too.
        unverified = ["Diagnosis", "Drug", "Specimen Site", "Study Site", "Gene Symbol", "Treatment Arm", "Visit",
                      "Visit Number"]
        expected = {h: "keep" for h in header}
        expected.update({h: "redact" for h in unverified + ["Notes"]})
        expected.update({"Record ID": "pseudonym_id", "Age": "age"})
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({d["column"]: d["action"] for d in report["decisions"]}, expected)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], unverified)
        self.assertFalse(any(d["name_withheld"] for d in report["decisions"]))
        for k, col in enumerate(header):
            if expected[col] == "keep":
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        p, out, report = self.run_file(raw, *[a for h in unverified for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for k, col in enumerate(header):
            if col in unverified:
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], unverified)
        ok = run("verify", str(self.tmp / "out" / "clinical30_r3_deidentified.csv"), "--reference-year",
                 REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


# A probe of --keep, run in a child interpreter like PROBE: for each column (name, values) it prints
# "kept" or "refused" and the start of the refusal, which never quotes a value.
KEEP_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import safe_harbor as s, deidentify as u
locale = u.load_locale("us")
sc = s.Scrubber(locale, 2026)
out = []
for header, values in json.load(open(sys.argv[2], encoding="utf-8")):
    data = [{header: v} for v in values]
    try:
        d = s.decide_columns(data, [header], locale, sc, {header}, set(), 2026)[0]
        out.append([header, "kept", d["kind"]])
    except s.UsageError as e:
        out.append([header, "refused", str(e)])
print(json.dumps(out, ensure_ascii=False))
"""


def keep_probe(tmp: Path, columns: list) -> list:
    path = tmp / "probe_keep.json"
    path.write_text(json.dumps(columns, ensure_ascii=False), encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", "-B", "-c", KEEP_PROBE, str(SCRIPT.parent), str(path)],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                       timeout=300)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-2000:])
    return json.loads(p.stdout)


class ColumnNamesKeepSplitDatesAndCoordinatesOfRoundFour(unittest.TestCase):
    """Round 4 of the fail-closed review (2026-11-25, 1.0.1): record numbers, ZIP codes, coordinates
    and old years written into column names; --keep over columns named for a person, a relative, a
    record number, an address, a device or notes in other languages and in plain English; dates split
    into a year, a month and a day under names the word lists did not know; coordinates of mixed
    precision; and the smaller gaps. Each test takes the review's cases and generates more of the same
    kind. Every name, number, date and place here is invented."""

    NAMES = ["Quillmont Ana", "Okerbrae Joao", "Varnstead Lia", "Delmorrow Rui", "Fintally Mae",
             "Graywick Ines", "Haskenvale Teo", "Lorrimere Sol"]

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

    # Medium: record numbers, ZIP codes and coordinates inside a column name were shown, reported and
    # copied to the output header in a default run.
    def test_numbers_in_column_names_are_refused_and_never_printed(self):
        import random
        rng = random.Random(41)
        templates = ["Patient {}", "Sample {}", "Case {}", "Chart {}", "Subject {}", "Specimen {}", "Pt {}",
                     "Participant {}", "Person {}", "Donor {}", "Visit {}", "Record {}", "Encounter {}",
                     "Weight_{}", "wt_{}", "col_{}", "BP {}", "Hb {}", "TP53 {}", "Day {}", "Weight {}",
                     "Col{}", "X{}", "{}", "Pt#{}", "Patient-{}", "{} Visit", "Score ({})", "Dx_{}_flag",
                     "患者{}", "Patient {} Weight"]
        numbers = ([str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(4)] + [str(rng.randrange(10 ** 4, 10 ** 5))]
                   + ["94110", "021345", "4,527,832", "4.527.832", "37.7749", "-122.41942", "33.82601",
                      "1925", "1930", "1899", str(rng.randrange(10 ** 8, 10 ** 9)), "376-7393", "415-555", "45/27832"])
        rows = []
        for t in templates:
            for n in numbers:
                rows.append(["Diagnosis", t.format(n), "Sex"])
        results = header_probe(self.tmp, rows)
        self.assertEqual([r[1] for r, res in zip(rows, results) if res != "refused"], [])
        # Short numbers and closed codes in a column name are not refused.
        ordinary = ["Col1", "TP53", "Q3", "2nd Dose", "Visit 2021", "Year 2020", "Week 104", "Day 28",
                    "ENSG00000141510", "ENSG00000141510.5", "rs12345678", "NM_004333.6", "chr1:12345678",
                    "chr7_55191822_T_G", "IL-6", "CA 19-9", "Col 4527", "HbA1c (%)", "pH 7.40", "V12", "Q10"]
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in ordinary])
        self.assertEqual([h for h, res in zip(ordinary, results) if res == "refused"], [])
        # The review's wide per-patient table: eight columns named for record numbers. Nothing is
        # printed, reported or written.
        ids = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(8)]
        for template in ("Patient {}", "Sample {}", "Visit {}", "Weight_{}"):
            header = ["Measure"] + [template.format(n) for n in ids]
            raw = write_csv(self.tmp / "wide.csv", header,
                            [[f"m{k}"] + [str(40 + (i * 7 + k) % 50) for i in range(8)] for k in range(20)])
            for command in ("plan", "run"):
                extra = ("-o", str(self.tmp / "out")) if command == "run" else ()
                p = run(command, str(raw), "--reference-year", REFERENCE_YEAR, *extra)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                for n in ids:
                    self.assertNotIn(n, p.stdout + p.stderr)
                self.assertFalse((self.tmp / "out").exists() and any((self.tmp / "out").iterdir()))
            # --keep-all-names does not override it: the person renames the columns.
            p = run("plan", str(raw), "--keep-all-names")
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        # verify withholds such a name in a file that has no report.
        stray = write_csv(self.tmp / "stray.csv", ["Diagnosis", f"Patient {ids[0]}"], [["Asthma", "3"]])
        p = run("verify", str(stray), "--reference-year", REFERENCE_YEAR)
        self.assertNotIn(ids[0], p.stdout + p.stderr)

    # Low (part of the same finding): in a file with no header row read as one, a first-row cell shaped
    # like a person's or a sample's code was shown as a column name.
    def test_a_first_row_code_is_withheld(self):
        codes = ["S001", "sub01", "PT-0042", "ABC123", "P01", "pt_007", "XYZ12345", "S0012", "ID01", "zx9921"]
        results = header_probe(self.tmp, [["Diagnosis", c, "Sex", "Visit", "Drug", "Arm"] for c in codes])
        for code, res in zip(codes, results):
            self.assertTrue(res == "refused" or 2 in res, (code, res))
        shown = header_probe(self.tmp, [["Diagnosis", c, "Sex"] for c in ("Col12", "V12", "TP53", "Q10", "CD34")])
        self.assertEqual(shown, [[], [], [], [], []])

    # Medium (three findings): --keep was accepted, and the identifier written verbatim, for columns named
    # as a person, a relative, an alias, a contact, an address, an email, a phone, a plate, a device, a
    # link, an image, an employer, a school or notes, in other languages and in plain English, and for
    # record, account, health-plan and national ID numbers named in other languages.
    PEOPLE = """Pai|Mae|Mãe|Elternteil|父|母|配偶者|부모|Родитель|Мать|Waliyyi|Tutor|Cohabitant|Co-habitant|Proxy|
Guarantor|Sponsor|Emergency|Mom|Dad|Mum|Papa|Mama|Grandpa|Granny|Twin|Nanny|Witness|Surrogate|Heir|Boss|Colleague|
ICE|AKA|Pseudonym|Moniker|Signature|Customer|Claimant|Applicant|Candidate|Student|Pupil|Baby|Infant|Kid|氏|姓|성|
Tên|İsim|Ad|フリガナ|ふりがな|Kana|Pinyin|Romaji|Romanized|Ten|Nama|Isim|Adi|Nimi|Jmeno|Nev|Pangalan|Ime|Numele|
Jina|Hasta Adı|Nama Pasien|Paciente|Pacjent|Pasient|Patientnavn|Potilas|Pacient|Policy Holder|Bearer|Head|Owner|
Teacher|Relation|Related|Associate|Co-signer|Responsible Party|Stepdaughter|Godmother|Lodger|Examinee|Attendee|
Primary Mom|Second Guardian|Patient's Twin|Contact 2|Hermana|Ehefrau|Moglie|Fiancee|Twin Info|Witness Details|
Contact 1st|Proxy Other|Guardian Primary|Customer Data|Department Head""".replace("\n", "").split("|")
    PLACES_AND_THINGS = """Dirección|Adresse|Anschrift|Straße|Rue|Calle|住所|주소|Адрес|Avenue|Road|Apt|Suite|Courriel|
Correo|Mobil|電話|전화|Телефон|メール|이메일|邮箱|Foto|Imagen|Matricula|Kennzeichen|Targa|车牌|Domain|Hostname|Plate|
Device|Link|Web|Image|Face|Voice|Company|School|Church|Home|Indirizzo|Endereço|Adres|Notes|Comments|Note|Remarks|
Kommentar|备注|Memo|Patient Home|Work Phone 2|Implant Device|Profile Image|Home Link""".replace("\n", "").split("|")
    NUMBERS = """Patientennummer|Numéro de dossier|Número de historia|病历号|Fallnummer|Aktenzeichen|Dossiernummer|
Prontuário|Historia Clinica|Matricula|DNI|CPF|Aadhaar|BSN|AHV|Personnummer|Fødselsnummer|CURP|NIR|KVNR|RUT|Cédula|
RRN|My Number|Codice Fiscale|Health Card|OHIP|Medi-Cal|NHI|Claim No|Policy No|Plan ID|Invoice|Receipt|Bill|
Pat No|Hospital No|Expediente|Cartella|住院号|患者番号|カルテ番号|등록번호|병원번호|Номер карты|История болезни|
Sozialversicherungsnummer|NSS|PESEL|CPR|NRIC|NIK|Chart|Record|Subject No|Study No|Lab No|Visit No|Encounter No|
Potilasnumero|Numer pacjenta|Nomor RM|Dosya No|Journalnummer|Patiëntnummer|Billing ID|Invoice Number""".replace("\n", "").split("|")
    KEEPABLE = """Diagnosis|Drug|Medication|Site|Primary Site|Visit|Treatment Arm|Arm|Physician|Provider|Surgeon|
Attending|Referring Physician|Referral|Hospital|Clinic|Unit|Ward|Department|Location|Visit Location|Service|Procedure|
Organism|Histology|Outcome|Disposition|Result|Value|Col6|Comorbidity|Allergy|Language|Religion|Occupation|Specimen Type|
Gene Symbol|Lab Test|Antibiotic|Symptom|Chief Complaint|Diagnosis Description|Cause of Death|Study Site|Cohort|Group|
Category|Family History|Contact Method|Discharge Destination|Ward Name|Nurse|Pharmacist|Technician|Mutational Signature|
Questionnaire Domain|Assay Plate""".replace("\n", "").split("|")

    def test_keep_is_refused_for_columns_named_for_people_places_records_and_notes_in_any_language(self):
        names = self.NAMES * 3
        numbers = [str(4527832 + i % 6) for i in range(24)]
        phones = [f"415-555-01{i % 10}{i % 7}" for i in range(24)]
        mixed = [names[i] if i % 3 else numbers[i] for i in range(24)]
        columns = ([(h, names) for h in self.PEOPLE] + [(h, mixed) for h in self.PEOPLE[:30]]
                   + [(h, names) for h in self.PLACES_AND_THINGS] + [(h, phones) for h in self.PLACES_AND_THINGS[:20]]
                   + [(h, numbers) for h in self.NUMBERS] + [(h, names) for h in self.KEEPABLE])
        results = keep_probe(self.tmp, columns)
        refused = len(columns) - len(self.KEEPABLE)
        self.assertEqual([(h, kind) for h, outcome, kind in results[:refused] if outcome != "refused"], [])
        for (h, values), (_, outcome, message) in zip(columns[:refused], results[:refused]):
            self.assertIn("cannot be kept", message, h)
            for v in set(values):
                self.assertNotIn(v, message)
        # Ordinary category and measurement names, clinicians' and staff roles and places of care are
        # still kept on the person's word.
        self.assertEqual([(h, m[:160]) for h, outcome, m in results[refused:] if outcome != "kept"], [])
        # A column named for someone can be kept when its values are numbers or codes, as before.
        codes = keep_probe(self.tmp, [(h, ["S-014", "S-015", "1001", "1002"] * 5) for h in ("Subject", "Donor", "Member")])
        self.assertEqual([outcome for _, outcome, _ in codes], ["kept"] * 3)
        # End to end: the plan lists these columns as ones that cannot be kept, not as the person's
        # decision, and names no value.
        header = ["Diagnosis", "Pai", "Mom", "Patientennummer", "Courriel", "Notes", "Sex"]
        rows = [["Asthma", names[i], names[i + 1], numbers[i], f"{names[i].split()[0].lower()}@example.org",
                 "called back", "F"] for i in range(20)]
        raw = write_csv(self.tmp / "people.csv", header, rows)
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        tail = plan.stdout.split("Need the person's decision", 1)
        self.assertIn("cannot be kept under their names", plan.stdout)
        decision_line = tail[1].split("\n\n", 1)[0] if len(tail) > 1 else ""
        for h in ("Pai", "Mom", "Patientennummer", "Courriel", "Notes"):
            self.assertNotIn(h, decision_line)
        for v in names + numbers:
            self.assertNotIn(v, plan.stdout + plan.stderr)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        unkeepable = {d["index"] for d in report["columns_that_cannot_be_kept"]}
        self.assertTrue({2, 3, 6} <= unkeepable, report["columns_that_cannot_be_kept"])
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], ["Diagnosis"])
        written = json.dumps(out)
        for v in names + numbers:
            self.assertNotIn(v, written)
        for col in ("#2", "Mom", "Patientennummer", "Courriel", "Notes"):
            p, out, report = self.run_file(raw, "--keep", col)
            self.assertEqual(p.returncode, 2, (col, p.stdout + p.stderr))
            self.assertIn("cannot be kept", p.stderr)

    # High: a date split into a year, a month and a day kept the month and the day when they were named
    # with an abbreviation or in a language outside the word lists.
    def test_split_dates_lose_month_and_day_whatever_they_are_called(self):
        import random
        rng = random.Random(44)
        sets = [("Year", "Mnth", "DoM"), ("Dx Year", "Mo of Dx", "Day of Dx"), ("Visit Yr", "Visit Mth", "Visit Dom"),
                ("Jahr", "Mon", "Tg"), ("dxyr", "dxmo", "dxdy"), ("SY", "SM", "SD"), ("Yil", "Ay", "Gun"),
                ("Ev", "Honap", "Nap"), ("Anul", "Luna", "Zi"), ("Rok", "Mjesec", "Dan"), ("Aasta", "Kuu", "Paev"),
                ("Col1", "Col2", "Col3"), ("A", "B", "C"), ("Var 7", "Var 8", "Var 9"), ("F1", "F2", "F3"),
                ("Event Year", "Q7", "Q8"), ("YY", "Item 2", "Item 3"), ("Year", "Admit", "Discharge"),
                ("Year of Onset", "Onset", "Onset 2"), ("Ano", "Mes", "Dia"), ("Year", "Wday", "DOW")]
        tables = []
        for y, m, d in sets:
            two_digit = y in ("YY", "dxyr")
            years = [str(rng.randrange(10, 23) if two_digit else rng.randrange(2010, 2023)) for _ in range(60)]
            months = [str(rng.randrange(1, 13)) for _ in range(60)]
            days = [str(rng.randrange(1, 29)) for _ in range(60)]
            if d in ("DOW",):
                days = [str(rng.randrange(1, 8)) for _ in range(60)]
            tables.append([(y, years), (m, months), (d, days), ("Sex", ["F", "M"] * 30)])
            tables.append([(m, months), (d, days), ("Sex", ["F", "M"] * 30), (y, years)])
        # Round 7: years are kept by default only under a name for a year (Year, Yr, Jahr, Rok, YY); under a
        # neutral name (Col1, A, Var 7, F1, SY) they are the person's decision (this test kept them before).
        neutral = {"Col1", "A", "Var 7", "F1", "SY"}
        for table, result in zip(tables, table_probe(self.tmp, tables)):
            actions = dict(result)
            year = next(h for h, _ in table if h in {s[0] for s in sets})
            self.assertEqual(actions[year], "redact" if year in neutral else "keep", table)
            self.assertEqual(actions["Sex"], "keep", table)
            for h, _ in table:
                if h not in (year, "Sex"):
                    self.assertNotEqual(actions[h], "keep", (h, [x for x, _ in table]))
        # On their own, without a year: numbers covering most of the months, or most of the days.
        alone = [(h, [str(1 + i % 12) for i in range(48)]) for h in
                 ("Mo", "M", "Mnth", "Adm M", "Disch Mo", "Visit Mo", "Ay", "Luna", "Kuu", "Mjesec", "Col3", "Q4", "X")]
        alone += [(h, [str(13 + i % 19) for i in range(48)]) for h in
                  ("Dy", "D", "Dom", "DoM", "Adm D", "Gun", "Dien", "Nap", "Zi", "Den", "Dan", "Paev", "Tg", "Col4", "Q5")]
        alone += [(h, [str(1 + (i * 5) % 28) for i in range(48)]) for h in ("Wochentag", "Wday", "Field 9")]
        # Missing-value codes (99, 0, -9) in a minority of the cells do not hide the column.
        alone += [(h, [str(1 + i % 12) for i in range(44)] + ["99", "0", "-9", "99"]) for h in ("Mo", "Col7", "Q9")]
        alone += [(h, [str(1 + i % 28) for i in range(44)] + ["99", "-1", "0", "88"]) for h in ("Dy", "Col8", "Q10")]
        # A day of the year and a week of the year, by name.
        alone += [(h, [str(1 + (i * 11) % 365) for i in range(48)]) for h in ("Day of Year", "DOY", "Julian Day")]
        alone += [(h, [str(1 + i % 52) for i in range(48)]) for h in ("Epi Week", "Week of Year", "ISO Week", "KW")]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", alone) if a == "keep"], [])
        # Measurements beside a year stay: scores, durations, counts, grades and stages, and numbers with 0.
        years = [str(2010 + i % 12) for i in range(60)]
        controls = [("Admit Year", years), ("Pain Score", [str(1 + i % 10) for i in range(60)]),
                    ("LOS (days)", [str(1 + i % 30) for i in range(60)]), ("Days", [str(1 + i % 30) for i in range(60)]),
                    ("Number of Visits", [str(1 + i % 12) for i in range(60)]), ("Tumor Grade", [str(1 + i % 3) for i in range(60)]),
                    ("NYHA Class", [str(1 + i % 4) for i in range(60)]), ("ECOG", [str(i % 5) for i in range(60)]),
                    ("GCS", [str(3 + i % 13) for i in range(60)]), ("Hemoglobin", [str(8 + i % 9) for i in range(60)]),
                    ("Sex Code", [str(1 + i % 2) for i in range(60)]), ("Comorbidities", [str(i % 6) for i in range(60)])]
        # Round 7: a sex code and "Comorbidities" name no measurement, so their numbers wait for the person's
        # word (this test kept them before); they are not read as dates either way.
        self.assertEqual([h for h, a in table_probe(self.tmp, [controls])[0] if a != "keep"], ["Sex Code", "Comorbidities"])
        # End to end: the review's table, written as it was found, and verify catches a written month.
        rows = [[str(rng.randrange(2010, 2023)), str(rng.randrange(1, 13)), str(rng.randrange(1, 29)), "F"]
                for _ in range(60)]
        raw = write_csv(self.tmp / "split.csv", ["Year", "Mnth", "DoM", "Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({list(r.values())[1] for r in out} | {list(r.values())[2] for r in out}, {"[REDACTED]"})
        self.assertEqual([r["Year"] for r in out], [row[0] for row in rows])
        self.assertIn("date element", p.stdout)
        ok = run("verify", str(self.tmp / "out" / "split_deidentified.csv"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        bad = write_csv(self.tmp / "written.csv", ["Year", "Q1", "Q2", "Sex"], rows)
        p = run("verify", str(bad), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("date element", p.stdout)
        # A column the person confirms is kept on their word, under an ordinary name.
        raw = write_csv(self.tmp / "visits.csv", ["Year", "Visit Number", "Sex"], [[r[0], r[1], "F"] for r in rows])
        p, out, report = self.run_file(raw, "--keep", "Visit Number")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Visit Number"] for r in out], [row[1] for row in rows])
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], ["Visit Number"])

    # Medium: latitude and longitude columns that mix precise and rounded values were kept.
    def test_coordinates_of_mixed_precision_are_redacted_cell_by_cell(self):
        import random
        rng = random.Random(45)
        headers = ["Value", "Col1", "Result", "Location", "Site", "X", "Pos", "Reading", "Field 3", "Var 2"]
        columns = []
        for k, h in enumerate(headers):
            for share in (1, 5, 10, 30, 50, 70, 100):
                for lo, hi in ((32.5, 42.0), (-124.4, -114.1), (2.0, 9.9), (114.0, 153.0)):
                    vals = []
                    for i in range(100):
                        x = rng.uniform(lo, hi)
                        vals.append(f"{x:.{rng.choice((4, 5, 6))}f}" if i < share else f"{x:.{rng.choice((1, 2, 3))}f}")
                    rng.shuffle(vals)
                    columns.append((h, vals))
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [])
        # Under a column name that names a measurement, and below 1, four places are a measurement.
        # Round 7: numbers fail closed by name, so the same decimals under Value, which names no measurement, are
        # the person's decision (this test kept them before).
        # Round 9: under a measurement name every cell is checked too, so four places from 1 to 180 under Weight (kg)
        # are a possible coordinate and the person's decision (this test kept them before); below 1 they stay.
        controls = [("Weight (kg)", [f"{50 + i / 7:.4f}" for i in range(40)]),
                    ("Troponin", [f"{(i % 50) / 1000:.4f}" for i in range(40)]),
                    ("Creatinine", [f"{0.5 + (i % 30) / 10:.2f}" for i in range(40)]),
                    ("Value", [f"{0.5 + (i % 30) / 10:.2f}" for i in range(40)])]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", controls) if a != "keep"], ["Weight (kg)", "Value"])
        # End to end with half the cells precise: nothing of the column is written.
        vals = [f"{rng.uniform(32.5, 42):.5f}" if i % 2 else f"{rng.uniform(32.5, 42):.2f}" for i in range(100)]
        raw = write_csv(self.tmp / "gps.csv", ["Value", "Sex"], [[v, "F"] for v in vals])
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Value"] for r in out}, {"[REDACTED]"})
        self.assertIn("latitude or a longitude", p.stdout)

    # Lows: repeated long record numbers under measurement names, short record numbers under record-style
    # names, decimal ages under age-like names and ages in months with a thousands separator.
    def test_record_numbers_and_ages_the_number_rules_missed(self):
        import random
        rng = random.Random(46)
        records = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(25)]
        repeated = [records[i % 25] for i in range(200)]
        columns = [(h, repeated) for h in ("Score", "Count", "Level", "Total", "Weight", "Amount", "Dose", "Steps",
                                           "Total Cost", "Visits")]
        columns += [(h, [f"{int(r):,}" for r in repeated]) for h in ("Score", "Count")]
        columns += [(h, [f"{r}.0" for r in repeated]) for h in ("Level", "Total")]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", columns) if a == "keep"], [])
        unique = [str(10 ** 6 + i * 3711) for i in range(200)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [("Steps", unique), ("Total Cost", unique)])],
                         ["keep", "keep"])
        small = [str(1 + i % 30) for i in range(150)]
        heads = ["Study ID", "Pat No", "Hospital No", "Subject No", "Record", "Chart", "Case", "Reference", "Key",
                 "Patient Nr", "Hosp ID", "PatNo", "Fallnummer", "Registry No", "Participant ID"]
        decided = probe(self.tmp, "decide", [(h, small) for h in heads])
        self.assertEqual([h for h, a, _ in decided if a != "pseudonym_id"], [])
        kept = keep_probe(self.tmp, [(h, small) for h in ("Study ID", "Pat No", "Chart", "Case")])
        self.assertEqual([o for _, o, _ in kept], ["kept"] * 4)
        # Round 7: a visit, cycle, dose or line number names no measurement, so its numbers are the person's
        # decision, redacted rather than pseudonymized (this test kept them before); a count is a measurement.
        controls = probe(self.tmp, "decide", [(h, [str(1 + i % 6) for i in range(60)]) for h in
                                              ("Visit No", "Cycle Number", "Dose Number", "Line No", "Number of Visits")])
        self.assertEqual([a for _, a, _ in controls], ["redact"] * 4 + ["keep"])
        decimals = [f"{30 + (i * 3) % 60}.5" for i in range(40)] + ["95.5", "102.5"]
        ages = probe(self.tmp, "decide", [(h, decimals) for h in ("Eta", "Old", "Y Old", "Year", "Elderly",
                                                                  "Seniority", "Senior")])
        self.assertEqual([h for h, a, _ in ages if a != "age"], [])
        header = ["Age", "Sex"]
        raw = write_csv(self.tmp / "months.csv", header, [["1,100 months", "F"], ["612 months", "M"],
                                                          ["1,140 mo", "F"], ["30 y", "M"]])
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Age"] for r in out][0], "90+")
        self.assertEqual([r["Age"] for r in out][2], "90+")
        self.assertNotIn("1,100", json.dumps(out))

    # The regression table of round 4: an ordinary 30-column clinical export with a column of years.
    def test_regression_table_of_an_ordinary_clinical_export_after_round_four(self):
        import random
        rng = random.Random(47)
        cols = {
            "Diagnosis": lambda i: ["Heart Failure", "Type 2 Diabetes", "Asthma", "Chronic Kidney Disease"][i % 4],
            "ICD-10": lambda i: ["I50.9", "E11.9", "J45.909", "N18.3"][i % 4],
            "Drug": lambda i: ["Metformin", "Lisinopril", "Albuterol", "Furosemide"][i % 4],
            "ATC Code": lambda i: ["A10BA02", "C09AA03", "R03AC02", "C03CA01"][i % 4],
            "Dose (mg)": lambda i: ["500", "10", "2.5", "40"][i % 4],
            "Primary Site": lambda i: ["Breast", "Lung", "Colon", "Prostate"][i % 4],
            "Study Site": lambda i: ["North Campus", "Harbor Clinic", "Lakeview Center"][i % 3],
            "Hemoglobin": lambda i: f"{9 + (i % 70) / 10:.1f}",
            "Creatinine": lambda i: f"{0.5 + (i % 30) / 10:.2f}",
            "Sodium": lambda i: str(130 + i % 15),
            "Lab Flag": lambda i: ["H", "L", "N"][i % 3],
            "Pain Score": lambda i: str(i % 11),
            "ECOG": lambda i: str(i % 4),
            "NYHA Class": lambda i: str(1 + i % 4),
            "Stage": lambda i: ["IIA", "IIIB", "IV", "Stage I"][i % 4],
            "Gene Symbol": lambda i: ["TP53", "EGFR", "KRAS", "BRAF"][i % 4],
            "Gene ID": lambda i: ["ENSG00000141510", "ENSG00000146648", "ENSG00000133703"][i % 3],
            "Variant": lambda i: ["p.V600E", "c.35G>A", "p.G12D"][i % 3],
            "Treatment Arm": lambda i: ["Placebo", "Arm A", "Arm B"][i % 3],
            "Visit": lambda i: ["Screening", "Baseline", "Week 4", "End of Study"][i % 4],
            "Visit Number": lambda i: str(1 + i % 6),
            "Diagnosis Year": lambda i: str(2012 + i % 11),
            "Length of Stay (days)": lambda i: str(1 + i % 21),
            "Race": lambda i: ["White", "Asian", "Black or African American"][i % 3],
            "Sex": lambda i: ["Female", "Male"][i % 2],
            "State": lambda i: ["California", "Oregon", "Nevada"][i % 3],
            "Country": lambda i: ["United States", "Mexico", "Canada"][i % 3],
            "Smoking Status": lambda i: ["Never smoker", "Former smoker", "Current every day smoker"][i % 3],
            "Weight (kg)": lambda i: f"{50 + (i * 3) % 70}.{i % 10}",
            "Notes": lambda i: ["Tolerated the infusion well and will return for the next cycle as planned.",
                                "Mild nausea after the second dose, managed with ondansetron at home."][i % 2],
        }
        self.assertEqual(len(cols), 30)
        header = list(cols)
        rows = [[cols[h](i) for h in header] for i in range(rng.randrange(180, 220))]
        raw = write_csv(self.tmp / "clinical30_r4.csv", header, rows)
        unverified = ["Diagnosis", "Drug", "Primary Site", "Study Site", "Gene Symbol", "Treatment Arm", "Visit",
                      "Visit Number"]
        expected = {h: "keep" for h in header}
        expected.update({h: "redact" for h in unverified + ["Notes"]})
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({d["column"]: d["action"] for d in report["decisions"]}, expected)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], unverified)
        # Round 9: a column named for notes is listed among the columns that cannot be kept, since --keep refuses it by
        # its name (this test listed none before).
        self.assertEqual([d["column"] for d in report["columns_that_cannot_be_kept"]], ["Notes"])
        self.assertFalse(any(d["name_withheld"] for d in report["decisions"]))
        for k, col in enumerate(header):
            if expected[col] == "keep":
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        # The person confirms the eight columns: the run keeps them and exits 0, and the notes stay redacted.
        p, out, report = self.run_file(raw, *[a for h in unverified for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for k, col in enumerate(header):
            if col != "Notes":
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        self.assertEqual({r["Notes"] for r in out}, {"[REDACTED]"})
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], unverified)
        refused = run("plan", str(raw), "--keep", "Notes")
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        ok = run("verify", str(self.tmp / "out" / "clinical30_r4_deidentified.csv"), "--reference-year",
                 REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


class NumbersColumnNamesCodesAndKeepOfRoundFive(unittest.TestCase):
    """Round 5 of the fail-closed review (2026-11-25, 1.0.1): numbers and column names, where the script
    still decided by shape. A week or a day of the year beside a year; record numbers and dates written in
    groups or with a two-digit year in a column name; code grammars with an open part; and --keep under a
    person word that is not clinical or care staff. Each test generates many header variants and value
    shapes of the kind the review found. Every name, number, date and place here is invented."""

    NAMES = ["Quillmont Ana", "Okerbrae Joao", "Varnstead Lia", "Delmorrow Rui", "Fintally Mae",
             "Graywick Ines", "Haskenvale Teo", "Lorrimere Sol"]

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

    WEEK_NAMED = """Wk|Week|Epi Wk|Epi Week|Sample Week|Admit Week|Weeknum|Week No|Week Number|ISO Wk|Epiweek|MMWR Week|
Semana|Woche|Semaine|Settimana|Hafta|Tydzien|Tydzień|Minggu|Viikko|Vecka|周|週|주|неделя|أسبوع|Wk of Dx|Dx Week|
Admit Wk|Onset Week|Event Week|Visit Week|Calendar Week|KW""".replace("\n", "").split("|")
    NEUTRAL = """W|Col3|Z|V4|Value|Result|Group|Col2|Period|Interval|Field 7|X|Q9|Var 3|Wochen|Item|Entry|Seen|Code|
Stratum|Cluster|Bin""".replace("\n", "").split("|")

    # Medium (two findings): a week of the year (1 to 53) beside a year column was kept verbatim under
    # every name but a few full phrases, and a day of the year (1 to 366) kept every value under 90.
    def test_weeks_and_days_of_the_year_beside_a_year_are_redacted(self):
        import random
        rng = random.Random(51)
        n = 120
        years = [str(rng.randrange(2005, 2024)) for _ in range(n)]
        year_forms = [("Year", years), ("Admit Year", years), ("Dx Yr", [y[2:] for y in years]),
                      ("Col1", years), ("Visit Date", [f"{y}-0{1 + i % 9}-1{i % 9}" for i, y in enumerate(years)])]

        def weeks(kind: int) -> list[str]:
            if kind == 0:
                return [str(1 + (i * 7) % 53) for i in range(n)]
            if kind == 1:  # a few missing-value codes
                return [str(1 + (i * 5) % 52) if i % 17 else "99" for i in range(n)]
            return [str(rng.randrange(1, 54)) for _ in range(n)]
        tables = []
        for k, h in enumerate(self.WEEK_NAMED + self.NEUTRAL):
            yh, yv = year_forms[k % len(year_forms)]
            tables.append([(yh, yv), (h, weeks(k % 3)), ("Sex", ["F", "M"] * (n // 2))])
        for table, result in zip(tables, table_probe(self.tmp, tables)):
            actions = dict(result)
            self.assertNotIn(actions[table[1][0]], ("keep", "age"), [h for h, _ in table])
            self.assertEqual(actions["Sex"], "keep")
        # A day of the year beside a year is redacted, not grouped as ages (which kept every value under 90).
        doy = [str(1 + (i * 37) % 366) for i in range(n)]
        tables = [[(yh, yv), (h, doy)] for h in ("Col2", "Value", "Result", "Seen", "Day", "Q", "Entry", "Ordinal")
                  for yh, yv in year_forms[:3]]
        for table, result in zip(tables, table_probe(self.tmp, tables)):
            self.assertEqual(dict(result)[table[1][0]], "redact", [h for h, _ in table])
        # Named for a week, a column is redacted without a year too (0 to 53, as %U writes it); under a
        # neutral name, numbers covering most of the 53 weeks are.
        alone = [(h, [str((i * 3) % 54) for i in range(n)]) for h in self.WEEK_NAMED]
        alone += [(h, [str(1 + (i * 11) % 53) for i in range(n)]) for h in ("Col3", "Value", "Z", "X")]
        alone += [(h, [str((i * 11) % 54) for i in range(n)]) for h in ("Col3", "Value", "Z", "X")]
        alone += [(h, [str(1 + (i * 37) % 366) for i in range(300)]) for h in ("Col2", "Value", "Result")]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", alone) if a in ("keep", "age")], [])
        # Measurements beside a year stay: vital signs, labs, scores, plural durations, counts and numbers with 0.
        controls = [("Admit Year", years), ("Heart Rate", [str(55 + i % 60) for i in range(n)]),
                    ("Sodium", [str(130 + i % 15) for i in range(n)]), ("Systolic BP", [str(95 + i % 90) for i in range(n)]),
                    ("SpO2", [str(88 + i % 12) for i in range(n)]), ("Glucose", [str(70 + (i * 13) % 250) for i in range(n)]),
                    ("Pain Score", [str(1 + i % 10) for i in range(n)]), ("Weeks", [str(1 + i % 40) for i in range(n)]),
                    ("Gestational Weeks", [str(20 + i % 22) for i in range(n)]), ("LOS (days)", [str(1 + i % 60) for i in range(n)]),
                    ("Number of Visits", [str(1 + i % 30) for i in range(n)]), ("ECOG", [str(i % 5) for i in range(n)]),
                    # Round 7: "Comorbidities" alone names no measurement, so a count names itself one.
                    ("Comorbidity Count", [str(i % 6) for i in range(n)]), ("eGFR", [str(15 + (i * 9) % 105) for i in range(n)]),
                    ("Interval (days)", [str(1 + i % 40) for i in range(n)]), ("Week 4 Pain Score", [str(i % 11) for i in range(n)])]
        self.assertEqual([h for h, a in table_probe(self.tmp, [controls])[0] if a != "keep"], [])
        # End to end: the review's table. No week is written, the plan says why, and verify catches a
        # written week of the year.
        rows = [[years[i], str(1 + (i * 7) % 53), ["F", "M"][i % 2]] for i in range(n)]
        raw = write_csv(self.tmp / "weeks.csv", ["Admit Year", "Admit Week", "Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Admit Week"] for r in out}, {"[REDACTED]"})
        self.assertEqual([r["Admit Year"] for r in out], years)
        self.assertIn("date element", p.stdout)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], ["Admit Week"])
        written = write_csv(self.tmp / "written.csv", ["Year", "Q4", "Sex"], rows)
        p = run("verify", str(written), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        # The person can keep it on their word.
        p, out, report = self.run_file(raw, "--keep", "Admit Week")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], ["Admit Week"])

    # Medium: a record number written into a column name in groups with spaces or underscores was shown,
    # reported and copied to the output.
    def test_record_numbers_written_in_groups_in_column_names_are_refused(self):
        import random
        rng = random.Random(52)
        templates = ["Patient {}", "Pt {}", "ID {}", "Weight {}", "Sample {}", "{} Visit", "Chart_{}", "Subject {}",
                     "MRN {}", "Lab {} Result", "Hb {}", "Col {}", "Case {}", "患者{}", "{}"]
        loose = [" ", "_", "  ", " _ ", "'", " ' ", ":", ") ", " #", "+"]
        rows, numbers = [], []
        for t in templates:
            for _ in range(6):
                digits = str(rng.randrange(10 ** 4, 10 ** 10))
                parts, rest = [], digits
                while rest:
                    k = rng.randrange(1, 5)
                    parts.append(rest[:k])
                    rest = rest[k:]
                if len(parts) < 2:
                    parts = [digits[:2], digits[2:]]
                sep = rng.choice(loose) if len(parts) == 2 else rng.choice(loose + ["-", ".", ",", "/", " - "])
                numbers.append(sep.join(parts))
                rows.append(["Diagnosis", t.format(numbers[-1]), "Sex"])
        self.assertEqual([r[1] for r, res in zip(rows, header_probe(self.tmp, rows)) if res != "refused"], [])
        # Ordinary numbers in a column name are still shown.
        ordinary = ["Col1", "TP53", "Q3", "2nd Dose", "Visit 2021", "Year 2020", "Day 28", "IL-6",
                    "CA 19-9", "CA 15-3", "HbA1c (%)", "pH 7.40", "BMI 18.5-24.9", "Temp 37.5-38.5",
                    "Glucose 70-100", "BP 120/80", "2019-2020", "CD4 2020", "HbA1c 2021", "Score 0-10", "Grade 3/4",
                    "PHQ-9", "Dose 2.5 mg", "Week 12-24", "COVID-19 Vaccine 2"]
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in ordinary])
        self.assertEqual([h for h, res in zip(ordinary, results) if res != []], [])
        # Round 9: a number of three or more digits that is no recent year, two numbers side by side and a number of
        # three parts are withheld, never refused (this test showed them before).
        withheld = ["Week 104", "Col 4527", "Version 1.2.3", "Visit 1 2"]
        self.assertEqual(header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in withheld]), [[2]] * 4)
        # End to end: nothing of the numbers is printed or written, and --keep-all-names does not override.
        header = ["Measure", "Patient 376 7393", "Pt 37 67 393", "Patient 37_67_393", "ID 12 34 56 78", "Weight 12 345"]
        raw = write_csv(self.tmp / "wide.csv", header, [[f"m{k}"] + [str(40 + k)] * 5 for k in range(12)])
        for extra in ((), ("--keep-all-names",)):
            p = run("plan", str(raw), *extra)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            for h in header[1:]:
                self.assertNotIn(h.split(" ", 1)[1], p.stdout + p.stderr)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertFalse((self.tmp / "out").exists() and any((self.tmp / "out").iterdir()))

    # Medium: a date written into a column name with a two-digit year or a month and a day was shown and
    # copied to the output.
    def test_dates_in_column_names_with_two_digit_years_or_days_are_never_shown(self):
        import random
        rng = random.Random(53)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Sept", "Oct", "Nov", "Dec",
                  "March", "October", "Ene", "Abr", "Dic", "Janv", "Mrz", "Okt", "Dez", "Juin", "Mai"]
        prefixes = ["", "Visit ", "Lab ", "WBC ", "HbA1c ", "Hb_", "Weight ", "Dx "]
        separated, compact = [], []
        for _ in range(140):
            m = rng.choice(months)
            m = rng.choice([m, m.lower(), m.upper()])
            num = f"{rng.randrange(0, 100):02d}" if rng.random() < 0.5 else str(rng.randrange(1, 32))
            p = rng.choice(prefixes)
            sep = rng.choice(["-", " ", "/", ".", "'", " - ", "_"])
            separated.append(p + (f"{m}{sep}{num}" if rng.random() < 0.6 else f"{num}{sep}{m}"))
            compact.append(p + (f"{m}{num}" if rng.random() < 0.6 else f"{num}{m}"))
        numeric = ["03/14", "3/14", "14/3", "12/24/20", "3-14-21", "03-14", "14-03-21", "14.3.", "03.14", "1/13",
                   "Visit 03/14", "Lab 3/14", "WBC 14/3", "Hb 03-14", "Score 10.03.21", "Day 3/14/2021"]
        quarters = ["Q1 20", "Q1 2020", "2020Q1", "Q3-21", "Q4'19", "1Q20", "2021 Q2", "Lab Q2 21", "q1_2020",
                    "Q2 of 2020", "1st Quarter 2020", "Quarter 2 2021", "Qtr 3 '21"]
        weeks = ["Wk 12 2020", "Week 12 2020", "W12 2020", "2020-W12", "2020W05", "Week 12, 2021", "Wk 3/2019",
                 "2021 Week 7", "Visit W40 2020"]
        refused = separated + numeric + quarters + weeks
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in refused])
        self.assertEqual([h for h, res in zip(refused, results) if res != "refused"], [])
        # Joined with no separator, a month abbreviation and one or two digits is also the shape of a gene
        # symbol (OCT4, SEPT9, DEC1): never shown, withheld rather than refused.
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in compact])
        self.assertEqual([h for h, res in zip(compact, results) if res != "refused" and 2 not in res], [])
        genes = ["OCT4", "Oct4", "SEPT9", "DEC1", "MARCH5", "NOV", "Mar19", "Sep12", "Jan20",
                 # A month name as a word of its own names the month of each person's measurement.
                 "Weight March", "June Visit", "Visit May", "Lab Oct", "Marzo"]
        self.assertEqual(header_probe(self.tmp, [["Diagnosis", g, "Sex"] for g in genes]), [[2]] * len(genes))
        # Ordinary names with a number are still shown.
        shown = ["Q3", "Q10", "Week 12", "Week 12-24", "Grade 3/4", "Score 3/10", "Marker 2",
                 "Sepsis 3", "Apgar 5", "Decline 2", "Visit 12", "Month 6", "Day 14", "Junior 2", "Dose 1/2"]
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in shown])
        self.assertEqual([h for h, res in zip(shown, results) if res != []], [])
        # Round 9: a number of three or more digits after a word is no ordinal under 100, so it is withheld (this test
        # showed them before).
        self.assertEqual(header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in ("Q123", "Week 104")]), [[2], [2]])
        # End to end: a wide export of monthly labs is refused without printing a name, and a gene symbol
        # is shown once the person confirms it by position.
        raw = write_csv(self.tmp / "monthly.csv", ["Diagnosis", "WBC Mar-19", "WBC Apr-19", "Sex"],
                        [["Asthma", "6.1", "5.9", "F"]] * 10)
        p = run("plan", str(raw))
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("Mar-19", p.stdout + p.stderr)
        raw = write_csv(self.tmp / "genes.csv", ["Diagnosis", "OCT4", "Sex"], [["Asthma", "6.1", "F"]] * 10)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("OCT4", p.stdout + json.dumps(report) + json.dumps(out))
        p, out, report = self.run_file(raw, "--keep-name", "#2")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        # Round 7: a gene symbol names no measurement, so its numbers wait for the person's word too.
        self.assertEqual([r["OCT4"] for r in out], ["[REDACTED]"] * 10)
        p, out, report = self.run_file(raw, "--keep-name", "#2", "--keep", "OCT4")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["OCT4"] for r in out], ["6.1"] * 10)

    # Medium: code grammars with an open part let prefixed record numbers pass verbatim under any column name.
    def test_code_grammars_accept_only_exact_published_shapes(self):
        import random
        rng = random.Random(54)

        def ids(prefix: str, lo: int, hi: int, k: int = 8) -> list[str]:
            return [f"{prefix}{rng.randrange(10 ** (d - 1), 10 ** d)}" for d in
                    (rng.randrange(lo, hi + 1) for _ in range(k))]
        shapes = {
            "upper and mixed-case rs": ids("RS", 1, 11) + ids("Rs", 3, 9) + ids("rS", 3, 9),
            "rs with a leading zero or eleven digits": ["rs0" + x[2:] for x in ids("rs", 5, 8)] + ids("rs", 11, 12),
            "RefSeq of the wrong length": [f"{p}_{rng.randrange(10 ** (d - 1), 10 ** d)}" for p in ("NM", "NR", "XM", "XP",
                                           "NP", "XR") for d in (5, 7, 8, 10)],
            "Ensembl of the wrong length": ids("ENSG", 10, 10) + ids("ENST", 12, 12) + ids("ENSP", 9, 9),
            "ICD-10 with a letter third or in lower case": ["H8Q.600", "T3L.K9", "B7Z.12", "Q4X.1", "e11.9", "j45.909",
                                                           "K1A.22", "A0B.1"],
            "ICD-9 E codes outside their ranges": ["E456.8", "E321.4", "E700.1", "E031.0", "E099.1", "E512.3"],
            "ICD-10 categories past their chapter's last": ["E95.1", "H99.2", "T90.1", "D95.0", "K99.1", "P99.2"],
            "HGVS of a base by itself": ["c.722478C>C", "c.12345A>A", "g.140453136T>T", "c.35G>G"],
            "a mod 10 check digit": [f"{n}-{_luhn(str(n))}" for n in range(452783, 452813)],
        }
        headers = ["Col1", "Value", "Ref", "Code", "Seen", "Entry", "Result", "Measure", "Key", "Encounter", "Specimen"]
        columns = [(h, values * 4) for values in shapes.values() for h in headers]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for (h, _), (_, a, _) in zip(columns, decided) if a == "keep"], [])
        for name, values in shapes.items():
            flags = probe(self.tmp, "grammar", [("Col1", values)])[0][1]
            self.assertEqual([v for v, f in zip(values, flags) if f], [], name)
        # The exact published shapes are codes under any column name; LOINC under a LOINC, lab or test name.
        exact = ["rs113488022", "rs7412", "rs1570391677", "ENSG00000141510", "ENST00000269305.4", "ENSMUSG00000059552",
                 "NM_004333.6", "NP_000537.3", "XM_011523456.2", "NC_000007.14:g.140453136A>T", "NG_007726.3",
                 "E11.9", "C4A.9", "Z3A.20", "M1A.071", "O9A.111", "C7B.00", "T88.7", "J45.909", "S72.001A", "V45.81",
                 "E880.9", "E001.0", "c.35G>A",
                 "p.V600E"]
        flags = probe(self.tmp, "grammar", [("Col1", exact)])[0][1]
        self.assertEqual([v for v, f in zip(exact, flags) if not f], [])
        loinc = ["2345-7", "14682-9", "718-7", "2160-0"]
        flags = probe(self.tmp, "grammar", [(h, loinc) for h in ("LOINC", "Lab Test", "Test Code", "Observation",
                                                                  "Col1", "Code", "Ref")])
        self.assertEqual([all(f) for _, f in flags], [True] * 4 + [False] * 3)
        # End to end: record numbers with the RS prefix repeating over visits are not written, and in kept
        # text an upper-case RS number is replaced while an rsID stays.
        mrns = ids("RS", 7, 7, 10)
        rows = [[mrns[i % 10], ["rs7412 and RS4527832 noted", "rs429358 seen"][i % 2], "F"] for i in range(40)]
        raw = write_csv(self.tmp / "rs.csv", ["Ref", "Finding", "Sex"], rows)
        p, out, report = self.run_file(raw, "--keep", "Finding")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        written = json.dumps(out)
        for m in mrns + ["RS4527832"]:
            self.assertNotIn(m, written)
        self.assertIn("rs7412", written)
        self.assertIn("rs429358", written)

    PERSON_HEADS = """Who|Case|Cases|Index Case|Controls|Reporter|Author|Signer|Signatory|Agent|Advocate|Chaplain|Courier|
Manager|Supervisor|Director|Principal|Officer|Rep|Referrer|Kind|Responsable|Tía|Tío|Requester|Endorser|Deceased|
Enrolled|Referred By|Referred_By|Interpreter|Inpatient|Outpatient|Department Head|Investigator|Coordinator|Reviewer|
Rater|Seen By|Signed By|Visit With|Assigned To|Lab Sign-off|Scribe|Navigator|Social Worker|Case Manager|Nurse Manager|
Witness|Teacher|Insurance Agent|Study Coordinator|Principal Investigator|Recorder|Abstractor|Translator|Primary Reporter|
Reporter 2|Author Info|Visit Reporter|Treatment Author|Test Reader|Ward Charge Manager|Unit Supervisor|Group Admin Officer|
Sponsor|Monitor|Team|Care Team|Owner|Lead|Chief|Examiner|Assessor|Observer|Interviewer|Volunteer|Employee|Statistician|
Receptionist|Paramedic|Clerk|Secretary|Analyst|Consultant|Prof|Mentor|Referee|Group Admin|Unit Charge|Ward Charge|
Referring|Ordering|Admitting|Treating|Consulting|Diagnosing""".replace("\n", "").split("|")
    STAFF_HEADS = """Physician|Physicians|Doctor|Dr|MD|Nurse|RN|NP|Surgeon|Clinician|Provider|Attending|Attending Physician|
Resident Physician|Fellow|Intern|Pharmacist|Therapist|Physical Therapist|Respiratory Therapist|Physiotherapist|
Technician|Lab Technician|Tech|Technologist|Midwife|Referring Physician|Ordering Provider|PCP|Radiologist|Psychiatrist|
Physician Assistant|Nurse Practitioner|Médecin|Arzt|Enfermera|Surgeon 2|Primary Nurse|Charge Nurse|Seen By Physician|
Ward Resident|
Chemotherapy Agent|Femoral Head|Holter Monitor|Diagnosis|Hospital|Site|Ward|Clinic|Patient Status|Patient Type|
Provider Specialty|Referral|Payer|Insurer""".replace("\n", "").split("|")

    # Medium (and a low of the same kind): --keep was accepted for columns named for someone who is not
    # clinical staff (Who, Case, Reporter, Author, Signer, Manager, Director, Officer, Rep, Kind, Tía, ...).
    def test_keep_under_a_person_word_is_accepted_only_for_clinical_and_care_staff(self):
        names = self.NAMES * 3
        columns = [(h, names) for h in self.PERSON_HEADS] + [(h, names) for h in self.STAFF_HEADS]
        results = keep_probe(self.tmp, columns)
        refused = len(self.PERSON_HEADS)
        self.assertEqual([h for h, outcome, _ in results[:refused] if outcome != "refused"], [])
        for (h, _), (_, outcome, message) in zip(columns[:refused], results[:refused]):
            self.assertIn("cannot be kept", message, h)
            for v in names:
                self.assertNotIn(v, message)
        self.assertEqual([(h, m[:120]) for h, outcome, m in results[refused:] if outcome != "kept"], [])
        # Numbers and codes under a person word can still be kept (a case or a subject number).
        codes = keep_probe(self.tmp, [(h, ["S-014", "S-015", "1001", "1002"] * 5) for h in ("Case", "Who", "Reporter",
                                                                                              "Controls")])
        self.assertEqual([o for _, o, _ in codes], ["kept"] * 4)
        # End to end: the plan lists the column apart, --keep exits 2, and no name is printed.
        rows = [["Asthma", names[i], names[i + 1], "F"] for i in range(20)]
        raw = write_csv(self.tmp / "roles.csv", ["Diagnosis", "Reporter", "Physician", "Sex"], rows)
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        tail = plan.stdout.split("cannot be kept under their names", 1)
        self.assertEqual(len(tail), 2, plan.stdout)
        self.assertIn("Reporter", tail[1].split("\n\n", 1)[0])
        p, out, report = self.run_file(raw, "--keep", "Reporter")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("clinical or care staff", p.stderr)
        for v in names:
            self.assertNotIn(v, p.stdout + p.stderr + plan.stdout)
        p, out, report = self.run_file(raw, "--keep", "Physician", "--keep", "Diagnosis")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], ["Diagnosis", "Physician"])
        self.assertEqual({r["Reporter"] for r in out}, {"[REDACTED]"})

    # Lows of round 5 that were cheap and safe to fix.
    def test_smaller_gaps_of_round_five(self):
        # Short surnames that are also column words are withheld alone, and shown beside another column word.
        alone = ["Das", "Fu", "Du", "Do", "Lo", "Da", "Di", "De", "La", "Kin", "Nam", "Son", "Man", "Max", "Pat",
                 "Tod", "Sin", "Tin", "Spring", "Hay", "Best", "Al", "Ed", "Val", "Kit"]
        self.assertEqual(header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in alone]), [[2]] * len(alone))
        beside = ["Max Temp", "Pat No", "Best Response", "Next Kin", "Spring Visit", "LOS", "Day", "Case", "Gene"]
        self.assertEqual(header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in beside]), [[]] * len(beside))
        # A fiscal year is a year; ordinary clinical words are column words and can be kept.
        words = ["FY2022 Cost", "FY2020", "FY 2021", "Haplotype", "Karyotype", "HPO Terms", "Chemotherapy",
                 "Adherence", "Compliance", "Seriousness", "Prosthesis", "Income Bracket", "Urbanicity", "Rurality",
                 "Sx", "Pregnancy", "Menopause", "Split", "Fold", "Feature3"]
        self.assertEqual(header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in words]), [[]] * len(words))
        kept = keep_probe(self.tmp, [(h, ["Alpha", "Beta", "Gamma"] * 4) for h in words[3:]])
        self.assertEqual([h for h, o, _ in kept if o != "kept"], [])
        # A public accession in a column name is refused, and shown when the person confirms it by position.
        accessions = ["GSM1234567", "SRR1234567", "TCGA-02-0001", "ILMN_1234567", "cg12345678", "LOC100132062",
                      "CHEMBL123456", "GO:0008150", "HMDB0000001", "C00031", "P04637", "R-HSA-109582", "PRJNA123456",
                      "NCT01234567"]
        for acc in accessions:
            raw = write_csv(self.tmp / "acc.csv", ["Diagnosis", acc, "Sex"], [["Asthma", "2.5", "F"]] * 5)
            p = run("plan", str(raw))
            self.assertEqual(p.returncode, 2, (acc, p.stdout + p.stderr))
            self.assertNotIn(acc, p.stdout + p.stderr)
            p = run("plan", str(raw), "--keep-name", "#2")
            self.assertEqual(p.returncode, 0, (acc, p.stdout + p.stderr))
            self.assertIn(acc, p.stdout)
        raw = write_csv(self.tmp / "acc.csv", ["Diagnosis", "Patient 3767393", "Sex"], [["Asthma", "2.5", "F"]] * 5)
        self.assertEqual(run("plan", str(raw), "--keep-name", "#2").returncode, 2)
        # Repeated record numbers of seven digits in any written form under a measurement name; a viral load
        # written with an exponent is a measurement.
        base = [4527832 + k for k in range(5)]
        forms = [lambda x: f"-{x}", lambda x: f"{x}.", lambda x: f"{x}.5", lambda x: f"{x:.6E}", lambda x: f"{x:.5e}"]
        columns = [(h, [f(base[i % 5]) for i in range(60)]) for h in ("Level", "Total", "Score", "Count") for f in forms]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", columns) if a == "keep"], [])
        loads = [f"{(i % 9 + 1) * 1.37:.2E}".replace("E+00", "E+06") for i in range(40)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [("Viral Load (copies/mL)", loads)])], ["keep"])
        # A claim, policy, invoice, plan, visit or record word as the last word of a measurement name.
        unique = [str(10 ** 6 + i * 3711) for i in range(60)]
        heads = ["Rate Plan", "Total Policy", "Cost Claim", "Charge Invoice", "Length of Stay Visit",
                 "Number of Visits Record", "Amount Account"]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", [(h, unique) for h in heads]) if a == "keep"], [])
        # Round 9: a count that names no large quantity holding numbers of seven digits is the person's decision (this
        # test kept Number of Records before); money keeps them.
        money = ["Claim Amount", "Number of Records", "Total Cost", "Cost per Visit", "Policy Cost"]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", [(h, unique) for h in money]) if a != "keep"],
                         ["Number of Records"])
        # A local telephone number written as a decimal, ZIP prefixes under postal code names, and decimal
        # ages under Y.O.
        phones = [f"555.{rng4:04d}" for rng4 in range(100, 160)]
        decided = probe(self.tmp, "decide", [("Value", phones), ("Result", phones),
                                             ("Post Code", ["036", "059", "941", "100"] * 5),
                                             ("ZCTA", ["036", "059", "941", "100"] * 5),
                                             ("PIN Code", ["036", "059", "941", "100"] * 5),
                                             ("Y.O.", [f"{30 + i}.5" for i in range(40)] + ["95.5"])])
        self.assertEqual([a for _, a, _ in decided], ["redact", "redact", "zip3", "zip3", "zip3", "age"])
        raw = write_csv(self.tmp / "zip.csv", ["Post Code", "Sex"], [[z, "F"] for z in ("036", "059", "941", "100")])
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Post Code"] for r in out], ["000", "000", "941", "100"])

    # The regression table of round 5: an ordinary 30-column clinical export with a year and a date column.
    def test_regression_table_of_an_ordinary_clinical_export_after_round_five(self):
        import random
        rng = random.Random(55)
        cols = {
            "Diagnosis": lambda i: ["Heart Failure", "Type 2 Diabetes", "Asthma", "Chronic Kidney Disease"][i % 4],
            "ICD-10": lambda i: ["I50.9", "E11.9", "J45.909", "N18.3"][i % 4],
            "Drug": lambda i: ["Metformin", "Lisinopril", "Albuterol", "Furosemide"][i % 4],
            "ATC Code": lambda i: ["A10BA02", "C09AA03", "R03AC02", "C03CA01"][i % 4],
            "Dose (mg)": lambda i: ["500", "10", "2.5", "40"][i % 4],
            "Primary Site": lambda i: ["Breast", "Lung", "Colon", "Prostate"][i % 4],
            "Study Site": lambda i: ["North Campus", "Harbor Clinic", "Lakeview Center"][i % 3],
            "Hemoglobin": lambda i: f"{9 + (i % 70) / 10:.1f}",
            "Sodium": lambda i: str(130 + i % 15),
            "Heart Rate": lambda i: str(55 + (i * 7) % 70),
            "LOINC": lambda i: ["718-7", "2160-0", "2345-7"][i % 3],
            "Lab Flag": lambda i: ["H", "L", "N"][i % 3],
            "Pain Score": lambda i: str(i % 11),
            "ECOG": lambda i: str(i % 4),
            "Stage": lambda i: ["IIA", "IIIB", "IV", "Stage I"][i % 4],
            "Gene ID": lambda i: ["ENSG00000141510", "ENSG00000146648", "ENSG00000133703"][i % 3],
            "SNP": lambda i: ["rs7412", "rs429358", "rs113488022"][i % 3],
            "Variant": lambda i: ["p.V600E", "c.35G>A", "p.G12D"][i % 3],
            "Treatment Arm": lambda i: ["Placebo", "Arm A", "Arm B"][i % 3],
            "Visit": lambda i: ["Screening", "Baseline", "Week 4", "End of Study"][i % 4],
            "Visit Week": lambda i: str([0, 4, 12, 24, 52][i % 5]),
            "Diagnosis Year": lambda i: str(2012 + i % 11),
            "Admission Date": lambda i: f"{2012 + i % 11}-0{1 + i % 9}-1{i % 9}",
            "Length of Stay (days)": lambda i: str(1 + i % 21),
            "Race": lambda i: ["White", "Asian", "Black or African American"][i % 3],
            "Sex": lambda i: ["Female", "Male"][i % 2],
            "State": lambda i: ["California", "Oregon", "Nevada"][i % 3],
            "Country": lambda i: ["United States", "Mexico", "Canada"][i % 3],
            "Attending Physician": lambda i: self.NAMES[i % 8],
            "Notes": lambda i: ["Tolerated the infusion well and will return for the next cycle as planned.",
                                "Mild nausea after the second dose, managed with ondansetron at home."][i % 2],
        }
        self.assertEqual(len(cols), 30)
        header = list(cols)
        rows = [[cols[h](i) for h in header] for i in range(rng.randrange(180, 220))]
        raw = write_csv(self.tmp / "clinical30_r5.csv", header, rows)
        unverified = ["Diagnosis", "Drug", "Primary Site", "Study Site", "Treatment Arm", "Visit", "Visit Week",
                      "Attending Physician"]
        expected = {h: "keep" for h in header}
        expected.update({h: "redact" for h in unverified + ["Notes"]})
        expected["Admission Date"] = "year"
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({d["column"]: d["action"] for d in report["decisions"]}, expected)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], unverified)
        # Round 9: a column named for notes is listed among the columns that cannot be kept, since --keep refuses it by
        # its name (this test listed none before).
        self.assertEqual([d["column"] for d in report["columns_that_cannot_be_kept"]], ["Notes"])
        self.assertFalse(any(d["name_withheld"] for d in report["decisions"]))
        for k, col in enumerate(header):
            if expected[col] == "keep":
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        for v in self.NAMES:
            self.assertNotIn(v, json.dumps(out) + p.stdout)
        # The person confirms the eight columns: the run keeps them and exits 0, and the notes stay redacted.
        p, out, report = self.run_file(raw, *[a for h in unverified for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for k, col in enumerate(header):
            if col not in ("Notes", "Admission Date"):
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        self.assertEqual({r["Notes"] for r in out}, {"[REDACTED]"})
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], unverified)
        ok = run("verify", str(self.tmp / "out" / "clinical30_r5_deidentified.csv"), "--reference-year",
                 REFERENCE_YEAR)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)


def _luhn(payload: str) -> int:
    """The mod 10 check digit LOINC appends, for generating record numbers that carry it."""
    total = 0
    for i, c in enumerate(reversed(payload)):
        d = int(c) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10


class NamesNumbersCoordinatesAndPlacesOfRoundSix(unittest.TestCase):
    """Round 6 of the fail-closed review (2026-11-25, 1.0.1): the class still open was numbers and column
    names, decided by shape. --keep refused a person word only as the last word of a column name, so a
    compound or an abbreviation of a name of the person or a relative was kept on the person's word
    (Patient Last, Mother First, PatNm, LNm, In-law); geocodes of two or three places passed as
    measurements under neutral and axis-like names; --keep kept numbers of five or more digits under names
    that are health or record numbers (PHN, NHS, NIP, Patid, Pat#, Patient Ref); and places that are not
    places of care could be kept (Home Area, Lives, Catchment Area, Ort). Each test generates many header
    variants and value shapes. Every name, number, place and coordinate here is invented."""

    NAMES = ["Quillmont Ana", "Okerbrae Joao", "Varnstead Lia", "Delmorrow Rui", "Fintally Mae",
             "Graywick Ines", "Haskenvale Teo", "Lorrimere Sol"]
    SURNAMES = ["Quillmont", "Okerbrae", "Varnstead", "Delmorrow", "Fintally", "Graywick"]
    TOWNS = ["Brindlecove", "Oakshaw", "Marrowmere", "Quellford", "Tansy Hollow", "Ferncastle"]
    PERSONS = """Pat Pt P Patient Patients Mother Mom Father Dad Spouse Husband Wife Kin NOK Child Parent Contact
Caregiver Carer Friend Partner Witness Subject Proband Donor Client Member Insured Owner Household Resident Tenant
Landlord Informant In-Law InLaw Guardian Sibling Brother Sister Son Daughter Relative Family Person Participant
Respondent Enrollee Recipient Beneficiary Subscriber Policyholder Emergency Neighbor Roommate Grandmother Aunt
Uncle Cousin StepSon Step-Daughter Dependant Proxy Surrogate Sponsor User Holder Customer Student Employee Twin
Case Mother-in-law Madre Padre Esposa Hijo Mutter Vater Ehefrau Paciente""".split()
    NAME_PARTS = """First Last Full Sur Surname Nam Nm Nme Label Ref Desc Detail Details Info Text Name Given Middle
Maiden Initials Forename Called Nick Alias Display Title String Key""".split()

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
    def spellings(p: str, x: str) -> list[str]:
        return [f"{p} {x}", f"{p}{x}", f"{p}_{x}".lower(), f"{p}.{x}".lower(), f"{p}-{x}",
                f"{p.upper()}_{x.upper()}", f"{p.lower()}{x}", f"{x} {p}", f"{x}_{p}".lower(), f"{p} {x} 2",
                f"{p}'s {x}", f"{p} {x} (Primary)"]

    # Medium: --keep was accepted, and offered by the plan, for compound or abbreviated name columns of the
    # person or a relative; a 2 x 26 x 23 sweep found 604 accepted spellings.
    def test_keep_is_refused_for_compound_and_abbreviated_name_columns(self):
        import random
        rng = random.Random(61)
        forms = [lambda i: self.NAMES[i % 8], lambda i: self.SURNAMES[i % 6],
                 lambda i: f"{self.NAMES[i % 8].split()[1]} {self.NAMES[i % 8].split()[0]}",
                 lambda i: f"{self.SURNAMES[i % 6]}, {self.NAMES[i % 8].split()[1]}",
                 lambda i: self.NAMES[i % 8].upper()]
        columns = []
        for p in self.PERSONS:
            for x in self.NAME_PARTS:
                for h in rng.sample(self.spellings(p, x), 2):
                    f = forms[len(columns) % len(forms)]
                    columns.append((h, [f(i) for i in range(24)]))
        alone = """PatNm|PNm|FNm|LNm|PtNm|Donor_Nm|Kin_Nm|Mother_Nm|pt.nme|In-law|InLaw|In Law|Mother-in-law|
Brother In Law|Sister-in-Law|Step Son|P Info|M Text|L Nm|F Nm|Pat Info|Pt Text|Pat Label|Mother Info|Kin Ref|
Spouse Desc|Guardian Data|Contact Info|Emergency Detail|Case Label|Resident Info|Resident Last|Fname|Lname""".replace(
            "\n", "").split("|")
        columns += [(h, [forms[k % len(forms)](i) for i in range(24)]) for k, h in enumerate(alone)]
        self.assertGreater(len(columns), 4000)
        results = keep_probe(self.tmp, columns)
        self.assertEqual([h for h, outcome, _ in results if outcome != "refused"], [])
        for (h, values), (_, _, message) in zip(columns[::97], results[::97]):
            self.assertIn("cannot be kept", message, h)
            for v in set(values):
                self.assertNotIn(v, message)
        # What a column holds about someone, a clinician's or staff role, a place of care and numbers or codes
        # under a word for someone can still be kept on the person's word.
        diagnoses = ["Type 2 diabetes", "Hypertension", "Asthma", "Crohn disease", "Migraine", "Gout"] * 4
        keepable = [(h, self.NAMES * 3) for h in ("Physician", "Referring Physician", "Patient Physician", "Physician Last",
                                                  "Nurse First", "Attending", "Pharmacist", "Technician", "Midwife",
                                                  "Provider", "Surgeon", "Physician Assistant", "Hospital", "Clinic",
                                                  "Site", "Ward Name", "Hospital Name", "Diagnosis", "Visit")]
        keepable += [(h, diagnoses) for h in ("Patient Status", "Mother Diagnosis", "Family History", "Patient Diagnosis",
                                               "Contact Method", "Provider Specialty", "Driver Mutation", "Spouse Occupation")]
        keepable += [(h, ["S-014", "S-015", "1001", "1002"] * 6) for h in ("Subject", "Case", "Donor", "Patient Code",
                                                                           "Subject Code", "Member")]
        kept = keep_probe(self.tmp, keepable)
        self.assertEqual([(h, m[:120]) for h, outcome, m in kept if outcome != "kept"], [])
        # A default run redacts or pseudonymizes them all (the fail-closed design already did), the plan lists
        # them as columns that cannot be kept, and --keep exits 2 without printing a value.
        header = ["Patient Last", "Mother First", "PatNm", "LNm", "Kin Info", "Caregiver Full", "InLaw", "Sex"]
        rows = [[forms[k % len(forms)](i) for k in range(7)] + [["F", "M"][i % 2]] for i in range(60)]
        raw = write_csv(self.tmp / "compound.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out) + p.stdout + p.stderr + json.dumps(report)
        for v in self.NAMES + self.SURNAMES:
            self.assertNotIn(v.split()[0], text)
        decisions = {d["column"]: d for d in report["decisions"]}
        for col in header[:-1]:
            self.assertIn(decisions[col]["action"], ("redact", "pseudonym_name", "pseudonym_id"), col)
        self.assertEqual(report["columns_needing_decision"], [])
        self.assertEqual([r["Sex"] for r in out], [r[-1] for r in rows])
        for col in header[:-1]:
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, col + refused.stdout + refused.stderr)
            self.assertIn("cannot be kept", refused.stderr)
            for v in self.NAMES + self.SURNAMES:
                self.assertNotIn(v.split()[0], refused.stdout + refused.stderr)

    # Medium: latitudes and longitudes of two or three places (1.1 km and 110 m) were written unchanged as
    # verified measurements under neutral and axis-like column names, alone and apart from their partner.
    def test_coordinates_of_two_or_three_places_are_not_kept_under_neutral_names(self):
        import random
        rng = random.Random(62)
        regions = [(34, 40, -123, -117), (40, 45, -80, -70), (45, 55, 5, 15), (-38, -28, 145, 153), (30, 40, 120, 140),
                   (19, 25, -105, -97), (-35, -20, -70, -45), (50, 58, -5, 2.5)]
        neutral = """Value|Col4|Result|X|Y|Loc X|Loc Y|Pos|Position|Point|Geo1|Geo2|Sample X|Meas1|Meas2|Index|Var 3|
Field 7|Data|Q9|Entry|Item|Obs|V5|Z1|Coordinate Value|Reading|Output|Response|Group|Seen|Unnamed: 3""".replace(
            "\n", "").split("|")
        columns = []
        for k, h in enumerate(neutral):
            la0, la1, lo0, lo1 = regions[k % len(regions)]
            for places in (2, 3):
                base_lat = [f"{rng.uniform(la0, la1):.{places}f}" for _ in range(25)]
                base_lon = [f"{rng.uniform(lo0, lo1):.{places}f}" for _ in range(25)]
                columns.append((h, [base_lat[i % 25] for i in range(100)]))
                if max(abs(lo0), abs(lo1)) >= 10:  # a longitude that reaches 10 (see the limits)
                    columns.append((h, [base_lon[i % 25] for i in range(100)]))
        # A longitude in the Americas with one place, and a column written with trailing zeros dropped.
        for h in neutral[:12]:
            columns.append((h, [f"{rng.uniform(-123, -70):.1f}" for _ in range(60)]))
            columns.append((h, [f"{rng.uniform(34, 40):.3f}".rstrip("0").rstrip(".") for _ in range(60)]))
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "coordinates kept")
        self.assertEqual([(h, k) for h, _, k in decided if k not in ("unverified", "uncertain", "identifier")], [])
        # A latitude of one place beside a longitude found as such is its partner.
        lat1 = [f"{rng.uniform(34, 40):.1f}" for _ in range(60)]
        lon1 = [f"{rng.uniform(-123, -117):.1f}" for _ in range(60)]
        for a, b in (("X", "Y"), ("Col1", "Col2"), ("Value", "Result"), ("Geo1", "Geo2")):
            self.assertEqual([act for _, act in table_probe(self.tmp, [[(a, lat1), (b, lon1), ("Sex", ["F", "M"] * 30)]])[0]],
                             ["redact", "redact", "keep"], (a, b))
        # Measurements stay: two-place decimals under a measurement name, and decimals below 10 (a z-score)
        # under a neutral one.
        controls = [("Weight kg", [f"{rng.uniform(50, 120):.2f}" for _ in range(60)]),
                    ("BMI", [f"{rng.uniform(18, 40):.2f}" for _ in range(60)]),
                    ("Hemoglobin", [f"{rng.uniform(9, 17):.2f}" for _ in range(60)]),
                    ("Creatinine", [f"{rng.uniform(0.5, 3):.2f}" for _ in range(60)]),
                    ("Temperature (C)", [f"{rng.uniform(36, 40):.2f}" for _ in range(60)]),
                    ("Pain Score", [f"{rng.uniform(0, 10):.2f}" for _ in range(60)]),
                    ("Total Cost", [f"{rng.uniform(10, 170):.2f}" for _ in range(60)]),
                    ("Value", [f"{rng.uniform(-3, 3):.2f}" for _ in range(60)]),
                    ("Z", [f"{rng.uniform(-4, 4):.3f}" for _ in range(60)]),
                    ("Col3", [f"{rng.uniform(0, 1):.3f}" for _ in range(60)])]
        # Round 7: under a neutral name even decimals below 10 are the person's decision (this test kept them
        # before), and they are not read as coordinates.
        decided = probe(self.tmp, "decide", controls)
        self.assertEqual([h for h, a, _ in decided if a != "keep"], ["Value", "Z", "Col3"])
        # End to end: a latitude and a longitude of three places under Value and Result, apart.
        lat = [f"{rng.uniform(34, 40):.3f}" for _ in range(25)]
        lon = [f"{rng.uniform(-123, -117):.3f}" for _ in range(25)]
        rows = [[lat[i % 25], ["Asthma", "COPD"][i % 2], lon[i % 25], ["F", "M"][i % 2]] for i in range(100)]
        raw = write_csv(self.tmp / "geo.csv", ["Value", "Diagnosis", "Result", "Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out) + p.stdout + p.stderr
        for v in lat + lon:
            self.assertNotIn(v, text)
        self.assertIn("possible coordinate", p.stdout)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], ["Value", "Diagnosis", "Result"])
        bad = run("verify", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        p, out, report = self.run_file(raw, "--keep", "Value", "--keep", "Result")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], ["Value", "Result"])

    # Medium: --keep was accepted, and the numbers written verbatim, for columns named as patient or health
    # identifiers (PHN, NHS, Patid, Pat#, PRN, Patient Ref, Patient Key, NIP) and for any other column name
    # that names no measurement (Registration, Token, Identification, VID, BID, Code1).
    def test_numbers_of_five_or_more_digits_cannot_be_kept_without_a_measurement_name(self):
        import random
        rng = random.Random(63)
        names = """PHN|NHS|Patid|Pat#|Patient #|MR#|PRN|Patient Ref|Pat Ref|Patient Key|Pt Key|Pt Token|NIP|Registration|
Cohort Key|Token|Identification|VID|BID|Code1|Value|Col6|Result|Entry|Seen|Field 3|Item|Variable 2|Data|Info|Group|Ref|
Number|Admission|Ingreso|Ricovero|Aufnahme|Status|Source|Link|Tag|Measure|Obs|X1|Q7|Var12|Unnamed: 4|Code|Kit|
Specimen|Sample|Order|Episode|Encounter|Folder|Case|Subject|Member|Donor|Index""".replace("\n", "").split("|")
        # (Nine or more digits, also with leading zeros, are replaced by the scrub in a kept column anyway.)
        forms = [str, lambda n: ("0" if n < 10 ** 7 else "") + str(n), lambda n: f"{n}.0", lambda n: f"{n}.", lambda n: f"-{n}",
                 lambda n: f"{n:,}", lambda n: f"{n:.5E}"]
        columns = []
        for k, h in enumerate(names):
            digits = 5 + k % 4
            people = [rng.randrange(10 ** (digits - 1), 10 ** digits) for _ in range(20)]
            form = forms[k % len(forms)] if digits >= 6 or k % len(forms) != 6 else str
            columns.append((h, [form(people[(i * 7) % 20]) for i in range(80)]))
        results = keep_probe(self.tmp, columns)
        self.assertEqual([h for h, outcome, _ in results if outcome != "refused"], [])
        for (h, values), (_, _, message) in zip(columns, results):
            self.assertIn("cannot be kept", message, h)
            for v in set(values):
                digits = re.sub(r"\D", "", re.split(r"[eE]", v)[0]) if re.search(r"[eE]", v) else \
                    v.replace(",", "").split(".")[0].lstrip("-0")
                self.assertNotIn(digits, message)
        # Under the names of health and record numbers, four digits are a record number by name.
        four = [str(rng.randrange(1000, 10000)) for _ in range(20)]
        by_name = """PHN|NHS|NHI|OHIP|NIP|PRN|PID|Patid|Ptid|Pat#|MR#|Visit #|Patient Ref|Pat Ref|Patient Key|Pt Key|
Pt Token|Patient Reference""".replace("\n", "").split("|")
        decided = probe(self.tmp, "decide", [(h, [four[i % 20] for i in range(60)]) for h in by_name])
        self.assertEqual([(h, k) for h, _, k in decided if k != "identifier"], [])
        # Measurements, the numbers of things that are not people, four-digit numbers and numbers the scrub
        # replaces anyway can still be kept on the person's word; counts and yes and no under these names stay.
        long_ = [str(rng.randrange(10 ** 5, 10 ** 7)) for _ in range(20)]
        keepable = [(h, [long_[(i * 7) % 20] for i in range(80)]) for h in (
            "Steps", "Total Cost", "Reads", "Read Count", "Visits", "Gene ID", "Entrez Gene ID", "Position",
            "Chr Start", "Lot No", "CPT", "Procedure Code", "Amount (USD)", "Income", "Plate No")]
        keepable += [(h, [four[i % 20] for i in range(60)]) for h in ("Value", "Col6", "Result", "Code1")]
        keepable += [("Contact Phone Type", ["Mobile", "Home"] * 10), ("Col2", [f"+1415555{i:04d}" for i in range(20)])]
        kept = keep_probe(self.tmp, keepable)
        self.assertEqual([(h, m[:100]) for h, outcome, m in kept if outcome != "kept"], [])
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [("PRN", ["Y", "N"] * 10),
                                                                      ("# of Visits", [str(1 + i % 9) for i in range(20)])])],
                         ["keep", "keep"])
        # End to end: PHN and Value of seven digits are pseudonymized, the rows of a patient keep one pseudonym,
        # neither can be kept, and the refusal prints no number.
        people = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(15)]
        rows = [[people[(i * 4) % 15], people[(i * 4) % 15], ["F", "M"][i % 2]] for i in range(90)]
        raw = write_csv(self.tmp / "phn.csv", ["PHN", "Value", "Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = json.dumps(out) + p.stdout
        for v in people:
            self.assertNotIn(v, text)
        self.assertEqual(out[0]["PHN"], out[15]["PHN"])
        self.assertEqual([d["column"] for d in report["columns_that_cannot_be_kept"]], ["Value"])
        for col in ("PHN", "Value"):
            refused = run("plan", str(raw), "--keep", col)
            self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
            for v in people:
                self.assertNotIn(v, refused.stdout + refused.stderr)

    # Low (three findings): places that are not places of care, record words with names, six-digit numbers
    # under counts of visits, a 6000-digit number, the plan's wording and wide matrices.
    def test_places_records_and_smaller_gaps_of_round_six(self):
        towns = self.TOWNS * 4
        places = """Home Area|Lives|Living|Community|Catchment Area|Service Area|Area|Locale|Territory|Geography|Place|
Venue|Ort|Lieu|Lugar|Luogo|Neighbourhood|Barrio|Quartier|Where|Residence Area|Home Locale|Areas Served|Living Area|
Home Location|Comunidad""".replace("\n", "").split("|")
        results = keep_probe(self.tmp, [(h, towns) for h in places])
        self.assertEqual([h for h, outcome, _ in results if outcome != "refused"], [])
        records = keep_probe(self.tmp, [(h, self.NAMES * 3) for h in ("Cartella", "Dossier", "Ficha", "Folio", "Registro",
                                                                     "File", "Folder", "Chart")])
        self.assertEqual([h for h, outcome, _ in records if outcome != "refused"], [])
        kept = keep_probe(self.tmp, [(h, towns) for h in ("Region", "Province", "Prefecture", "Hospital", "Clinic",
                                                          "Site", "Ward", "Unit", "Department", "Location",
                                                          "Visit Location", "Discharge Destination")])
        self.assertEqual([(h, m[:100]) for h, outcome, m in kept if outcome != "kept"], [])
        # Body places are category words, so a treatment area of them can still be kept on the person's word.
        self.assertEqual(keep_probe(self.tmp, [("Treatment Area", ["Left knee", "Lower back", "Chest"] * 8)])[0][1],
                         "kept")
        # A default run redacts a town under any of these names (the fail-closed design already did).
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", [(h, towns) for h in places]) if a == "keep"], [])
        # Six digits that repeat under a count of visits, encounters or admissions are record numbers.
        six = [str(400000 + i * 7919) for i in range(10)]
        rep = [six[(i * 3) % 10] for i in range(60)]
        decided = probe(self.tmp, "decide", [(h, rep) for h in ("Visits", "Encounters", "Admissions", "Episodes",
                                                                  "Number of Visits", "Readmissions", "Steps")])
        # Round 9: under Steps too, since repeated five- and six-digit numbers are record numbers under any measurement
        # name but money and small units of time (this test kept them before).
        self.assertEqual([a for _, a, _ in decided], ["pseudonym_id"] * 6 + ["redact"])
        # A number of 6000 digits does not stop the run; it is redacted and never printed.
        huge = "7" * 6000
        raw = write_csv(self.tmp / "huge.csv", ["Value", "Steps", "Sex"], [[huge, huge, "F"], ["12", "13", "M"]] * 3)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("7" * 30, p.stdout + p.stderr + json.dumps(out) + json.dumps(report))
        self.assertEqual({r["Sex"] for r in out}, {"F", "M"})
        # The plan says when every unverified value is shaped like a name or a place.
        raw = write_csv(self.tmp / "names.csv", ["Col1", "Sex"], [[self.NAMES[i % 8], "F"] for i in range(40)])
        p = run("plan", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("all 8 of them are shaped like names of people or places", p.stdout)
        # A wide matrix named by methylation probes is refused with a remedy, and no probe name is printed.
        probes = [f"cg{12345678 + 1111 * i:08d}" for i in range(30)]
        raw = write_csv(self.tmp / "wide.csv", probes + ["Sex"], [[f"0.{i}" for i in range(30)] + ["F"]] * 5)
        p = run("plan", str(raw), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("rename them with a word and a short number", p.stderr)
        for name in probes:
            self.assertNotIn(name, p.stdout + p.stderr)

    # Medium (finding 1, made moot by the fail-closed design in a default run): a neutrally named column of
    # names, record numbers or towns is redacted or pseudonymized by default, whatever the person later keeps.
    def test_default_runs_redact_what_round_six_found_behind_keep(self):
        import random
        rng = random.Random(64)
        neutral = ["Status", "Seen", "Col1", "Ref", "Value", "Result", "Group", "Info", "Q3", "Field 2", "Entry"]
        numbers = [str(rng.randrange(10 ** 6, 10 ** 7)) for _ in range(12)]
        columns = [(h, self.NAMES * 4) for h in neutral] + [(h, self.TOWNS * 5) for h in neutral]
        columns += [(h, [numbers[(i * 5) % 12] for i in range(60)]) for h in neutral]
        columns += [(h, self.NAMES * 4) for h in ("Patient Last", "Mother First", "PatNm", "LNm", "In-law", "Kin Info")]
        columns += [(h, self.TOWNS * 5) for h in ("Home Area", "Lives", "Catchment Area", "Ort", "Place")]
        columns += [(h, [numbers[(i * 5) % 12] for i in range(60)]) for h in ("PHN", "NHS", "NIP", "Patid", "Pat#")]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a not in ("redact", "pseudonym_id", "pseudonym_name")], [])

    # The regression table of round 6: an ordinary 30-column clinical export (diagnoses, drugs, sites, labs,
    # scores, gene ids, arms, visits, race, sex, state, country and free-text notes) with a date column.
    def test_regression_table_of_an_ordinary_clinical_export_after_round_six(self):
        import random
        rng = random.Random(66)
        n = 120
        cols = {
            "Study ID": [f"S-{1 + (i * 7) % 40:04d}" for i in range(n)],
            "Sex": [rng.choice(["F", "M"]) for _ in range(n)],
            "Race": [rng.choice(["White", "Asian", "Black or African American"]) for _ in range(n)],
            "Ethnicity": [rng.choice(["Hispanic or Latino", "Not Hispanic or Latino"]) for _ in range(n)],
            "State": [rng.choice(["CA", "NY", "TX", "WA"]) for _ in range(n)],
            "Country": [rng.choice(["United States", "Canada", "Mexico"]) for _ in range(n)],
            "Age": [str(rng.randrange(34, 89)) for _ in range(n)],
            "Diagnosis": [rng.choice(["Type 2 diabetes", "Hypertension", "Asthma", "Heart failure"]) for _ in range(n)],
            "ICD10 Code": [rng.choice(["E11.9", "I10", "J45.909", "I50.9"]) for _ in range(n)],
            "Drug": [rng.choice(["Metformin", "Lisinopril", "Albuterol", "Furosemide"]) for _ in range(n)],
            "ATC Code": [rng.choice(["A10BA02", "C09AA03", "R03AC02", "C03CA01"]) for _ in range(n)],
            "Dose mg": [rng.choice(["500", "1000", "20", "40"]) for _ in range(n)],
            "Site": [rng.choice(["North Campus", "Harbor Clinic", "Lakeview Center"]) for _ in range(n)],
            "Arm": [rng.choice(["Placebo", "Treatment"]) for _ in range(n)],
            "Visit": [rng.choice(["Baseline", "Week 4", "Week 12", "Week 24"]) for _ in range(n)],
            "Visit Number": [str(1 + i % 6) for i in range(n)],
            "Visit Date": [f"20{rng.randrange(18, 24)}-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}"
                           for _ in range(n)],
            "WBC": [f"{rng.uniform(4.0, 11.5):.1f}" for _ in range(n)],
            "Hemoglobin": [f"{rng.uniform(11.0, 16.0):.2f}" for _ in range(n)],
            "Glucose": [str(rng.randrange(70, 250)) for _ in range(n)],
            "HbA1c (%)": [f"{rng.uniform(5.2, 10.1):.1f}" for _ in range(n)],
            "Systolic BP": [str(rng.randrange(105, 165)) for _ in range(n)],
            "PHQ-9 Score": [str(rng.randrange(0, 28)) for _ in range(n)],
            "ECOG": [str(rng.randrange(0, 5)) for _ in range(n)],
            "Stage": [rng.choice(["Stage I", "Stage II", "Stage IIIA", "Stage IV"]) for _ in range(n)],
            "Gene": [rng.choice(["TP53", "KRAS", "EGFR", "BRAF"]) for _ in range(n)],
            "Ensembl ID": [rng.choice(["ENSG00000141510", "ENSG00000133703", "ENSG00000146648"]) for _ in range(n)],
            "Variant": [rng.choice(["p.V600E", "c.35G>A", "p.L858R"]) for _ in range(n)],
            "Smoking Status": [rng.choice(["Never", "Former", "Current"]) for _ in range(n)],
            "Clinical Note": [rng.choice(["Reports mild fatigue after starting the new medication regimen this month.",
                                          "Follow up in three months with repeat labs and a review of home readings.",
                                          "No acute distress today; continue the current plan and reassess next visit."])
                              for _ in range(n)],
        }
        self.assertEqual(len(cols), 30)
        header = list(cols)
        rows = [[cols[h][i] for h in header] for i in range(n)]
        raw = write_csv(self.tmp / "clinical30_r6.csv", header, rows)
        unverified = ["Diagnosis", "Drug", "Site", "Arm", "Visit", "Visit Number", "Gene"]
        expected = {h: "keep" for h in header}
        expected.update({h: "redact" for h in unverified + ["Clinical Note"]})
        expected.update({"Study ID": "pseudonym_id", "Age": "age", "Visit Date": "year"})
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({d["column"]: d["action"] for d in report["decisions"]}, expected)
        self.assertEqual([d["column"] for d in report["columns_needing_decision"]], unverified)
        # Round 9: a column named for notes is listed among the columns that cannot be kept, since --keep refuses it by
        # its name (this test listed none before).
        self.assertEqual([d["column"] for d in report["columns_that_cannot_be_kept"]], ["Clinical Note"])
        for k, col in enumerate(header):
            if expected[col] in ("keep", "age"):
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        # The person confirms the seven columns: the run keeps them and exits 0; the notes stay redacted.
        p, out, report = self.run_file(raw, *[a for h in unverified for a in ("--keep", h)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for k, col in enumerate(header):
            if col in unverified:
                self.assertEqual([r[col] for r in out], [row[k] for row in rows], col)
        self.assertEqual({r["Clinical Note"] for r in out}, {"[REDACTED]"})
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], unverified)


class NumbersByNameDecimalDatesAndHeaderCharactersOfRoundSeven(unittest.TestCase):
    """Round 7 of the fail-closed review (2026-11-25, 1.0.1): the class still open was numbers under
    neutral names (one-decimal coordinate pairs, decimal years, Unix timestamps with fractional seconds,
    record numbers under Value, Result, Col3, X, Y), decided by their shape. Numbers now fail closed by
    NAME, as text does: a column of numbers is kept by default only under a column name that names a
    measurement and only when its numbers pass the identifier and date checks. Dates written as decimal
    numbers are dates under any name, and a header cell holding a NUL, a control or a format character is
    refused. Each test generates many header variants and value shapes. Every name, number, place and
    coordinate here is invented."""

    NEUTRAL = """Value|Result|Col3|X|Y|Index|Point|Pos|Geo1|Measure1|Entry|Seen|Event|Period|Item|Field 2|Var 7|Data|
Reading|Obs|Q7|Response|Outcome|Status|Group|Arm|Cycle|Visit|Wave|Column 12|V9|F1|A|Z|Mid|Spot|Loc|Record|Notes 2|
Code|Group 2|Measure|Test|Lab|Kind 2|Val|Res|Num|Entry Type|Category|Class|Type|Flag|Label|Tag""".replace(
        "\n", "").split("|")
    MEASURED = """Glucose|WBC|Hemoglobin|Sodium|Heart Rate|Systolic BP|SpO2|Temperature (C)|Weight (kg)|BMI|Pain Score|GCS|
MMSE|PHQ-9|ECOG|Dose (mg)|Daily Dose|Steps|Number of Visits|Visit Count|LOS (days)|Duration (min)|Cost|Free T4|
Vitamin B12|Ki-67|CA 19-9|IgG|Log2FC|P Value|FDR|Stage|Gleason|Apgar|Value (mg/dL)|Result (%)|Creatinine|eGFR|
Platelets|Tumor Size (mm)|Gestational Weeks|Charlson|NIHSS|Hematocrit|Albumin|Ferritin|TSH|Lactate""".replace(
        "\n", "").split("|")

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
    def shapes(rng) -> dict:
        """Ordinary-looking numbers of many shapes, none of them an identifier: the point is that the script
        cannot tell them from one by their shape alone."""
        return {
            "small whole": [str(rng.randrange(1, 6)) for _ in range(40)],
            "whole to 200": [str(rng.randrange(0, 200)) for _ in range(40)],
            "one place": [f"{rng.uniform(0, 80):.1f}" for _ in range(40)],
            "two places": [f"{rng.uniform(0, 9):.2f}" for _ in range(40)],
            "three places": [f"{rng.uniform(0, 1):.3f}" for _ in range(40)],
            "negative": [f"{rng.uniform(-5, 5):.1f}" for _ in range(40)],
            "comparator": [rng.choice(["<0.5", ">10", "3.2", "4.4", "<=1"]) for _ in range(40)],
            "binary": [str(i % 2) for i in range(40)],
            "with words": [rng.choice(["12.5", "8.1", "Positive", "Negative"]) for _ in range(40)],
        }

    # The core of round 7: numbers under a column name that names no measurement are the person's decision,
    # whatever their shape, and the plan says the script cannot verify that they are not identifiers, dates
    # or coordinates.
    def test_numbers_under_names_that_name_no_measurement_wait_for_the_persons_word(self):
        import random
        rng = random.Random(71)
        columns = [(h, vals) for h in self.NEUTRAL for vals in self.shapes(rng).values()]
        self.assertGreater(len(columns), 450)
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "numbers kept under a neutral name")
        # The same numbers under a column name that names a measurement are kept.
        plain = {k: v for k, v in self.shapes(rng).items() if k != "with words"}
        columns = [(h, plain[k]) for h in self.MEASURED for k in ("small whole", "whole to 200", "one place",
                                                                  "two places", "comparator")]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a != "keep"], [], "measurements not kept")
        # A number written with its unit names its own measurement, under any column name.
        units = [rng.choice(["5.2 mg/dL", "140 mmol/L", "12%", "75 kg", "7.1 g/dL"]) for _ in range(40)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [(h, units) for h in ("Value", "Result", "Col3")])],
                         ["keep"] * 3)
        # Years are allowed under a name for a year, and the person's decision under any other name.
        years = [str(rng.randrange(2005, 2025)) for _ in range(40)]
        named = ["Year", "Admit Year", "Dx Yr", "Jahr", "Year of Diagnosis", "YYYY", "Years", "Ano"]
        decided = probe(self.tmp, "decide", [(h, years) for h in named + ["Value", "Col3", "Index", "X", "Entry"]])
        self.assertEqual([a for _, a, _ in decided], ["keep"] * len(named) + ["redact"] * 5)
        # End to end: the plan lists such a column for the person's decision, says why, names no value, and
        # --keep keeps it.
        header = ["Value", "Result", "Sex", "Glucose"]
        rows = [[f"{40 + i % 50}.{i % 10}", str(i % 7), "F" if i % 2 else "M", str(80 + i % 60)] for i in range(60)]
        raw = write_csv(self.tmp / "neutral.csv", header, rows)
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        self.assertIn("cannot verify that they are not identifiers, dates or coordinates", plan.stdout)
        decision = plan.stdout.split("Need the person's decision", 1)[1].split("Ask the person", 1)[0]
        self.assertIn("Value", decision)
        self.assertIn("Result", decision)
        self.assertNotIn("Glucose", decision)
        for row in rows[:10]:
            self.assertNotIn(row[0], plan.stdout)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Value"] for r in out} | {r["Result"] for r in out}, {"[REDACTED]"})
        self.assertEqual([r["Glucose"] for r in out], [row[3] for row in rows])
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, {"Value", "Result"})
        p, out, report = self.run_file(raw, "--keep", "Value", "--keep", "Result")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Value"] for r in out], [row[0] for row in rows])
        self.assertEqual({d["column"] for d in report["kept_unverified_columns"]}, {"Value", "Result"})
        self.assertIn("scrubbed for patterns only", p.stdout)

    # An ordinary long-format lab table (Patient ID, Lab, Value, Unit) completes once the person keeps Value.
    def test_long_format_lab_table_completes_once_the_person_keeps_value(self):
        import random
        rng = random.Random(72)
        labs = [("Glucose", "mg/dL", 70, 180), ("Hemoglobin", "g/dL", 9, 17), ("Sodium", "mmol/L", 132, 146),
                ("Creatinine", "mg/dL", 0.5, 2.5), ("WBC", "10^3/uL", 3, 15), ("Platelets", "10^3/uL", 120, 420),
                ("ALT", "U/L", 8, 90), ("Potassium", "mmol/L", 3.2, 5.6)]
        ids = [str(4100000 + 37 * k) for k in range(30)]
        rows = []
        for i in range(240):
            name, unit, lo, hi = labs[i % 8]
            x = lo + (hi - lo) * rng.random()
            rows.append([ids[i % 30], name, f"{x:.1f}" if hi < 50 else str(round(x)), unit])
        raw = write_csv(self.tmp / "labs_long.csv", ["Patient ID", "Lab", "Value", "Unit"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("Value", [r["Value"] for r in out])
        # Some values reach 90 (a glucose, an ALT), which under Value reads as a possible age: the column is
        # redacted, not grouped, because its other numbers are not verified either.
        self.assertEqual({r["Value"] for r in out}, {"[REDACTED]"})
        self.assertIn("Value", {d["column"] for d in report["columns_needing_decision"]})
        self.assertEqual([r["Unit"] for r in out], [row[3] for row in rows])
        for extra in (("--keep", "Value"), ("--keep", "Value", "--keep", "Lab")):
            p, out, report = self.run_file(raw, *extra)
            self.assertEqual(p.returncode, 0, (extra, p.stdout + p.stderr))
            self.assertEqual([r["Value"] for r in out], [row[2] for row in rows])
            self.assertTrue(all(re.fullmatch(r"ID\d{4}", r["Patient ID"]) for r in out))
            for i in ids:
                self.assertNotIn(i, json.dumps(out))
        self.assertEqual([r["Lab"] for r in out], [row[1] for row in rows])

    # Medium: dates written as decimal numbers (decimal years, year.week, year.day, decimal birth years, Unix
    # timestamps with fractional seconds, Julian dates) passed as verified measurements.
    def test_dates_written_as_decimal_numbers_are_dates_under_any_name(self):
        import random
        from datetime import datetime, timezone
        rng = random.Random(73)

        def epoch(y: int) -> float:
            return datetime(y, rng.randrange(1, 13), rng.randrange(1, 28), tzinfo=timezone.utc).timestamp()
        shapes = {
            "decimal year": [f"{rng.randrange(2015, 2024)}.{rng.randrange(1, 99):02d}" for _ in range(40)],
            "decimal year 3": [f"{rng.randrange(2015, 2024)}.{rng.randrange(1, 999):03d}" for _ in range(40)],
            "year.week": [f"{rng.randrange(2015, 2024)}.{rng.randrange(1, 53):02d}" for _ in range(40)],
            "year.day": [f"{rng.randrange(2015, 2024)}.{rng.randrange(100, 366)}" for _ in range(40)],
            "year.month one digit": [f"{rng.randrange(2015, 2024)}.{rng.randrange(2, 10)}" for _ in range(40)],
            "old decimal year": [f"{rng.randrange(1920, 1935)}.{rng.randrange(1, 999):03d}" for _ in range(40)],
            "year.mmdd": [f"{rng.randrange(1925, 1936)}.{rng.randrange(1, 13):02d}{rng.randrange(1, 29):02d}"
                          for _ in range(40)],
            "epoch seconds": [f"{epoch(rng.randrange(2015, 2024)):.0f}.{rng.randrange(100, 999)}" for _ in range(40)],
            "epoch millis": [f"{epoch(rng.randrange(2015, 2024)) * 1000:.0f}.{rng.randrange(1, 9)}" for _ in range(40)],
            "negative epoch": [f"{epoch(rng.randrange(1925, 1937)):.0f}.{rng.randrange(10, 99)}" for _ in range(40)],
            "julian day": [f"{2457000 + rng.randrange(0, 3000)}.5" for _ in range(40)],
        }
        headers = self.NEUTRAL[:20] + ["Start Time", "End Time", "Time", "Time Stamp", "Draw Time", "Event Time",
                                       "Year", "Visit", "Measure", "Period", "Seen", "Entry"]
        columns = [(h, vals) for h in headers for vals in shapes.values()]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "dates written as decimals kept")
        # End to end: each becomes its year, and a year 90 or more years ago [90_OR_OLDER].
        header = ["Value", "Start Time", "Time", "Sex"]
        rows = [[shapes["decimal year"][i], shapes["epoch seconds"][i], shapes["negative epoch"][i], "F"]
                for i in range(40)]
        raw = write_csv(self.tmp / "decimal_dates.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("dates written as numbers", p.stdout)
        self.assertEqual([r["Value"] for r in out], [v.split(".")[0] for v in shapes["decimal year"]])
        self.assertTrue(all(re.fullmatch(r"20(1[5-9]|2[0-3])", r["Start Time"]) for r in out), out[:3])
        self.assertEqual({r["Time"] for r in out}, {"[90_OR_OLDER]"})
        written = json.dumps(out)
        for row in rows:
            for v in row[:3]:
                self.assertNotIn(v, written)
        # Under a column name that names a measurement, one number that has the shape of a date among
        # measurements is not enough: a cost of 1999.99, a viral load of 2,450,000.
        controls = [("Total Cost", ["1999.99"] + [f"{rng.uniform(10, 900):.2f}" for _ in range(39)]),
                    ("Viral Load", ["2450000"] + [str(rng.randrange(50, 90000)) for _ in range(39)]),
                    ("Weight (g)", ["1950.5"] + [f"{rng.uniform(2500, 4200):.1f}" for _ in range(39)])]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", controls)], ["keep"] * 3)
        # Round 7 too: under a day, a week, a month or a bare time a number of five digits is not a duration,
        # whole or not, even beyond the range of an Excel serial.
        late = [f"{rng.randrange(80000, 99999)}.{rng.randrange(1, 9)}" for _ in range(40)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [(h, late) for h in
                                                                      ("Visit Day", "Days", "LOS", "Event Time")])],
                         ["redact"] * 4)

    # Medium (moot under round 7): one-decimal latitude and longitude pairs under neutral names were kept as
    # verified measurements. They are now redacted by default, as numbers under names that name no measurement.
    def test_one_decimal_coordinate_pairs_under_neutral_names_are_redacted_by_default(self):
        import random
        rng = random.Random(74)
        boxes = {"Munich": (48.0, 48.3, 11.4, 11.8), "Tokyo": (35.5, 35.8, 139.5, 139.9),
                 "Sydney": (-34.0, -33.7, 151.0, 151.3), "London": (51.4, 51.6, -0.3, 0.1),
                 "Nairobi": (-1.4, -1.2, 36.7, 36.9), "Beijing": (39.8, 40.0, 116.3, 116.5),
                 "San Francisco": (37.7, 37.8, -122.5, -122.4), "Boston": (42.3, 42.4, -71.1, -71.0)}
        pairs = [("Value", "Result"), ("X", "Y"), ("Loc X", "Loc Y"), ("Pos1", "Pos2"), ("Col1", "Col2"),
                 ("Geo1", "Geo2"), ("A", "B"), ("Y1", "X1"), ("Index", "Group"), ("Point", "Spot"),
                 ("Measure1", "Measure2"), ("Entry", "Seen"), ("Event", "Period"), ("V1", "V2"), ("Data", "Data 2")]
        tables = []
        for lo1, hi1, lo2, hi2 in boxes.values():
            lat = [f"{rng.uniform(lo1, hi1):.1f}" for _ in range(60)]
            lon = [f"{rng.uniform(lo2, hi2):.1f}" for _ in range(60)]
            for a, b in pairs:
                tables.append([(a, lat), (b, lon), ("Sex", ["F", "M"] * 30)])
        for table, result in zip(tables, table_probe(self.tmp, tables)):
            self.assertEqual([a for _, a in result], ["redact", "redact", "keep"], [h for h, _ in table])
        # End to end: the review's table, 120 rows of Munich at one decimal under Value and Result.
        rows = [[f"{rng.uniform(48.0, 48.3):.1f}", f"{rng.uniform(11.4, 11.8):.1f}", "F"] for _ in range(120)]
        raw = write_csv(self.tmp / "munich.csv", ["Value", "Result", "Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Value"] for r in out} | {r["Result"] for r in out}, {"[REDACTED]"})
        self.assertNotIn("verified as measurements", json.dumps(report["decisions"][:2]))
        self.assertIn("coordinates", p.stdout)

    # Medium: a first row of data whose letters are separated by NUL, zero-width or other format characters
    # passed the header check, and its raw text reached the plan and the output; a UTF-16 file with no byte
    # order mark was read as UTF-8.
    def test_header_cells_with_control_or_format_characters_are_refused(self):
        name = "Zorbleton Quillmont"
        seps = ["​", "‌", "‍", "⁠", "﻿", "‎", "‏", "­", "‮",
                "⁦", "\x01", "\x1f", "\x7f", "\x00"]
        for k, sep in enumerate(seps):
            hidden = sep.join(name)
            for header in ([hidden, "Sex", "Temp"], ["Sex", hidden, "Temp"], ["Sex", "Temp", "Weight" + sep]):
                path = self.tmp / f"hidden_{k}.csv"
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(header)
                    w.writerow(["F", "36.6", "70"])
                p = run("plan", str(path), "--encoding", "utf-8")
                self.assertEqual(p.returncode, 2, (repr(sep), header, p.stdout + p.stderr))
                position = next(i for i, h in enumerate(header, start=1) if sep in h)
                self.assertIn(f"#{position}", p.stderr)
                self.assertIn("invisible formatting character", p.stderr)
                for part in name.split():
                    self.assertNotIn(part, p.stdout + p.stderr)
                self.assertNotIn(hidden, p.stdout + p.stderr)
        # A BOM-less UTF-16 file, little or big endian, with a first row of data: refused, with the remedy.
        rows = ["Zorbleton Smith,M,100.5", "Quillmont Ana,F,98.2", "Okerbrae Joao,M,99.1"]
        for codec, hint in (("utf-16-le", "utf-16-le"), ("utf-16-be", "utf-16-be")):
            path = self.tmp / f"u16_{codec}.csv"
            path.write_bytes("\n".join(rows).encode(codec))
            for cmd in (("plan", str(path)), ("run", str(path), "-o", str(self.tmp / "o16"))):
                p = run(*cmd)
                self.assertEqual(p.returncode, 2, (codec, p.stdout + p.stderr))
                self.assertIn("UTF-16 text without a byte order mark", p.stderr)
                self.assertIn("CSV UTF-8", p.stderr)
                self.assertIn(hint, p.stderr)
                for part in ("Zorbleton", "Smith", "Quillmont"):
                    self.assertNotIn(part, p.stdout + p.stderr)
            self.assertFalse((self.tmp / "o16").exists() and any((self.tmp / "o16").iterdir()))
        # A name spelled out one letter at a time with an ordinary separator is withheld, never shown.
        spelled = ["-".join("Zorbleton") + " " + "-".join("Smith"), " ".join("Quillmont"), ".".join("Okerbrae"),
                   "_".join("Varnstead"), "/".join("Delmorrow"), "*".join("Fintally"), "Z-o-r-b"]
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in spelled])
        self.assertEqual([r for r in results if r != [2]], [])
        raw = self.tmp / "spelled.csv"
        write_csv(raw, ["-".join("Zorbleton") + " " + "-".join("Smith"), "Sex", "Temp"],
                  [["Quillmont Ana", "F", "98.2"]] * 4)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        written = (self.tmp / "out" / "spelled_deidentified.csv").read_text(encoding="utf-8")
        self.assertNotIn("Z-o-r", p.stdout + json.dumps(report) + written)
        self.assertTrue(written.startswith("column_1,Sex,Temp"), written[:40])
        # The first row of data in a file without one, read as the header row, is refused outright when a
        # third of its cells look like values.
        write_csv(raw, ["-".join("Zorbleton") + " " + "-".join("Smith"), "M", "100.5"],
                  [["Quillmont Ana", "F", "98.2"]] * 4)
        p = run("plan", str(raw))
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("Z-o-r", p.stdout + p.stderr)
        # Ordinary names, single letters and codes stay shown; a line break in a column name reads as a space.
        shown = ["T N M", "A B", "X Y Z", "Systolic\nBP", "Heart\tRate", "Q1 Q2", "HbA1c", "U.S. State"]
        results = header_probe(self.tmp, [["Diagnosis", h, "Sex"] for h in shown])
        self.assertEqual([h for h, r in zip(shown, results) if r != []], [])
        # Without a header row the first row is data: format characters in a value make it text the script
        # cannot verify, redacted, not a refusal.
        raw = self.tmp / "noheader.csv"
        raw.write_text("​".join("Zorbleton") + ",F,36.6\nQuillmont Ana,M,37.0\n", encoding="utf-8")
        p = run("run", str(raw), "-o", str(self.tmp / "nh"), "--no-header")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("Zorbleton", (self.tmp / "nh" / "noheader_deidentified.csv").read_text(encoding="utf-8")
                         .replace("​", ""))

    # Lows and smaller gaps of round 7.
    def test_smaller_gaps_of_round_seven(self):
        import random
        rng = random.Random(75)
        # A coordinate written after its hemisphere letter is not an ICD-10 code under a neutral name.
        hemis = [f"{rng.choice('NS')}{rng.randrange(10, 60)}.{rng.randrange(1000, 9999)}" for _ in range(40)]
        hemis3 = [f"{rng.choice('NSEW')}{rng.randrange(10, 60)}.{rng.randrange(100, 999)}" for _ in range(40)]
        heads = ["Value", "Col3", "Result", "X", "Y", "Pos", "Code", "Geo", "Point", "Loc"]
        decided = probe(self.tmp, "decide", [(h, v) for h in heads for v in (hemis, hemis3)])
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [])
        flags = probe(self.tmp, "grammar", [("Diagnosis", ["E11.3211", "S72.001A", "N18.30", "I25.110", "E11.9"]),
                                            ("Code", ["E11.3211", "S72.001A", "N37.7749", "S33.8688", "W12.4194"])])
        self.assertEqual([f for _, f in flags], [[True] * 5, [True, True, False, False, False]])
        # Two capital letters from more than one vocabulary list are initials as often as codes.
        initials = ["NA", "SD", "PR", "LT", "HH", "NO", "CR", "RT", "NE", "JA", "SI", "LL"]
        cols = [(h, [initials[(i * 5 + k) % 12] for i in range(150)]) for k, h in
                enumerate(["Ref", "Value", "Notes", "Code", "Item", "Col1", "Group", "Initials 2"])]
        self.assertEqual([(h, a) for h, a, _ in probe(self.tmp, "decide", cols) if a == "keep"], [])
        lists = [("Response", ["CR", "PR", "SD", "PD", "NE"] * 20), ("Side", ["LT", "RT"] * 20),
                 ("Flag", ["H", "L", "HH", "LL", "N"] * 20), ("State", ["CA", "NY", "TX", "WA"] * 20),
                 ("Reply", ["NO", "SI", "JA"] * 20)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", lists)], ["keep"] * 5)
        # --keep is refused for words for a person or a place the lists read as ordinary words, and for a
        # name word spelled with digits.
        names = ["Quillmont Ana", "Okerbrae Joao", "Varnstead Lia", "Delmorrow Rui"] * 6
        towns = ["Brindlecove", "Oakshaw", "Marrowmere", "Quellford"] * 6
        refused = [(h, names) for h in ("Signed", "Sign", "Hx Source", "Source of History", "Salutation", "MI", "To",
                                        "From", "Resp", "Patient N4me", "Patient Nam3", "M0ther Info", "L4st Name",
                                        "Sp0use Info", "Fu11 Name")]
        refused += [(h, towns) for h in ("Geo Location", "Map", "Shelter", "Building", "Block",
                                         "Education Institution", "Origin", "Geo Area", "GPS Location")]
        results = keep_probe(self.tmp, refused)
        self.assertEqual([h for h, outcome, _ in results if outcome != "refused"], [])
        for (h, values), (_, _, message) in zip(refused, results):
            for v in set(values):
                self.assertNotIn(v, message)
        kept = keep_probe(self.tmp, [(h, ["Rash", "Fever", "Edema"] * 8) for h in ("Vital Sign", "Clinical Sign",
                                                                                     "Injury Location", "Tumor Origin")]
                          + [(h, ["Arm A", "Arm B"] * 8) for h in ("Col1", "HbA1c Group", "CD4 Group", "Q3")])
        self.assertEqual([h for h, outcome, _ in kept if outcome != "kept"], [])
        # Short study numbers under a code, a label, a token or a sequence of the person or the record are
        # pseudonymized, so the rows of one patient stay linked.
        short = [str(100 + (i * 7) % 20) for i in range(100)]
        heads = ["Pt Code", "Case Code", "Record Code", "Research Number", "Proband No", "Family Number",
                 "Participant Label", "Subject Token", "Patient Seq", "Subject Code"]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [(h, short) for h in heads])],
                         ["pseudonym_id"] * len(heads))
        # Ages written as >99 under words that can mean old age, and numbers under neutral names, are not kept.
        over = [">99", "45", "62", ">99", "71"] * 8
        decided = probe(self.tmp, "decide", [(h, over) for h in ("Elderly", "Senior", "Old", "Year", "Lifetime", "Eta")])
        self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [])
        # A long cell of slashes no longer takes quadratic time.
        raw = write_csv(self.tmp / "slashes.csv", ["Comment Code", "Sex"], [["1/" * 30000, "F"], ["2/2", "M"]])
        import time
        start = time.monotonic()
        p = run("run", str(raw), "-o", str(self.tmp / "sl"))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertLess(time.monotonic() - start, 15)
        # A wide matrix named by public accessions is confirmed by a range of positions, and its numbers kept
        # the same way.
        probes = [f"cg{10000000 + k * 7919:08d}" for k in range(300)]
        header = ["Sex"] + probes
        rows = [["F" if i % 2 else "M"] + [f"{rng.random():.3f}" for _ in probes] for i in range(8)]
        raw = write_csv(self.tmp / "wide.csv", header, rows)
        p = run("plan", str(raw))
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("--keep-name '#2-#501'", p.stderr)
        for acc in probes[:20]:
            self.assertNotIn(acc, p.stderr)
        p, out, report = self.run_file(raw, "--keep-name", "#2-#301", "--keep", "#2-#301")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r[probes[0]] for r in out], [row[1] for row in rows])
        p = run("plan", str(raw), "--keep-name", "#2-#999")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("range of positions", p.stderr)

    # The regression table: an ordinary invented 30-column clinical table. A default run keeps the columns it
    # can verify (measurements under measurement names, codes, category words, states and countries), redacts
    # the text and the numbers it cannot, and completes with exit 0 once the person keeps the columns they
    # confirm.
    def test_ordinary_clinical_table_regression(self):
        header = ["Patient ID", "Age", "Sex", "Race", "Ethnicity", "State", "Country", "Diagnosis", "ICD10", "Drug",
                  "ATC", "Dose (mg)", "Site", "Arm", "Visit", "Visit Number", "Visit Date", "Glucose", "HbA1c",
                  "Creatinine (mg/dL)", "Systolic BP", "Heart Rate", "BMI", "Pain Score", "ECOG", "Stage", "Gene",
                  "Ensembl ID", "Smoking Status", "Notes"]
        dx = [("Type 2 diabetes", "E11.9"), ("Hypertension", "I10"), ("Asthma", "J45.909"), ("Heart failure", "I50.9"),
              ("CKD stage 3", "N18.30"), ("Lung cancer", "C34.90")]
        drugs = [("Metformin", "A10BA02"), ("Lisinopril", "C09AA03"), ("Albuterol", "R03AC02"), ("Furosemide", "C03CA01")]
        genes = [("TP53", "ENSG00000141510"), ("EGFR", "ENSG00000146648"), ("KRAS", "ENSG00000133703"),
                 ("BRCA1", "ENSG00000012048")]
        pids = [str(4100000 + 37 * k) for k in range(40)]
        rows = []
        for i in range(160):
            d, code = dx[i % 6]
            dr, atc = drugs[i % 4]
            g, ens = genes[i % 4]
            rows.append([pids[i % 40], str(25 + (i * 7) % 60), "F" if i % 2 else "M",
                         ["White", "Black or African American", "Asian", "American Indian or Alaska Native"][i % 4],
                         ["Hispanic or Latino", "Not Hispanic or Latino"][i % 2], ["CA", "NY", "TX", "WA"][i % 4],
                         ["United States", "Canada", "Mexico"][i % 3], d, code, dr, atc, str([500, 1000, 10, 40][i % 4]),
                         ["Lung", "Breast", "Colon", "Prostate"][i % 4], ["Placebo", "Active"][i % 2],
                         ["Baseline", "Week 4", "Week 12", "Week 24"][i % 4], str(1 + i % 4),
                         f"2021-{1 + i % 12:02d}-{1 + i % 28:02d}", str(80 + (i * 13) % 120), f"{5.2 + (i % 30) / 10:.1f}",
                         f"{0.6 + (i % 20) / 10:.2f}", str(100 + (i * 3) % 60), str(55 + (i * 5) % 50),
                         f"{19 + (i % 15) * 0.7:.1f}", str(i % 11), str(i % 5),
                         ["Stage I", "Stage II", "Stage IIIA", "Stage IV"][i % 4], g, ens,
                         ["Never smoker", "Former smoker", "Current smoker"][i % 3],
                         "Follow-up in clinic as planned, tolerating treatment well with no new complaints today."])
        raw = write_csv(self.tmp / "clinical30.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        actions = {d["column"]: d["action"] for d in report["decisions"]}
        kept = {"Sex", "Race", "Ethnicity", "State", "Country", "ICD10", "ATC", "Dose (mg)", "Glucose", "HbA1c",
                "Creatinine (mg/dL)", "Systolic BP", "Heart Rate", "BMI", "Pain Score", "ECOG", "Stage", "Ensembl ID",
                "Smoking Status"}
        unverified = {"Diagnosis", "Drug", "Site", "Arm", "Visit", "Visit Number", "Gene"}
        self.assertEqual({c for c, a in actions.items() if a == "keep"}, kept)
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, unverified)
        self.assertEqual(actions["Patient ID"], "pseudonym_id")
        self.assertEqual(actions["Visit Date"], "year")
        self.assertEqual(actions["Notes"], "redact")
        for i, col in enumerate(header):
            if col in kept:
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        p, out, report = self.run_file(raw, *[a for c in sorted(unverified) for a in ("--keep", c)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            if col in kept | unverified:
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        self.assertEqual({d["column"] for d in report["kept_unverified_columns"]}, unverified)
        written = json.dumps(out)
        for pid in pids:
            self.assertNotIn(pid, written)



SCRUB_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import safe_harbor as s, deidentify as u
sc = s.Scrubber(u.load_locale("us"), 2026)
print(json.dumps([sc.scrub(t) for t in json.load(open(sys.argv[2], encoding="utf-8"))], ensure_ascii=False))
"""


def scrub_probe(tmp: Path, texts: list) -> list:
    path = tmp / "probe_scrub.json"
    path.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", "-B", "-c", SCRUB_PROBE, str(SCRIPT.parent), str(path)],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                       timeout=300)
    if p.returncode != 0:
        raise AssertionError(p.stderr[-2000:])
    return json.loads(p.stdout)


# Round 8: dates written in many scripts and calendars, generated for the tests from month names written here
# (not read from the script), so the tests prove the grammar rather than a list of strings.
_CJK_DIGITS = "〇一二三四五六七八九"
_MONTHS_BY_LANGUAGE = {
    "ms": "Januari Februari Mac April Mei Jun Julai Ogos September Oktober November Disember",
    "id": "Januari Februari Maret April Mei Juni Juli Agustus September Oktober November Desember",
    "ru": "января февраля марта апреля мая июня июля августа сентября октября ноября декабря",
    "uk": "січня лютого березня квітня травня червня липня серпня вересня жовтня листопада грудня",
    "el": "Ιανουαρίου Φεβρουαρίου Μαρτίου Απριλίου Μαΐου Ιουνίου Ιουλίου Αυγούστου Σεπτεμβρίου Οκτωβρίου "
          "Νοεμβρίου Δεκεμβρίου",
    "ar": "يناير فبراير مارس أبريل مايو يونيو يوليو أغسطس سبتمبر أكتوبر نوفمبر ديسمبر",
    "lev": "كانون_الثاني شباط آذار نيسان أيار حزيران تموز آب أيلول تشرين_الأول تشرين_الثاني كانون_الأول",
    "he": "בינואר בפברואר במרץ באפריל במאי ביוני ביולי באוגוסט בספטמבר באוקטובר בנובמבר בדצמבר",
    "hi": "जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर",
    "tr": "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık",
    "pl": "stycznia lutego marca kwietnia maja czerwca lipca sierpnia września października listopada grudnia",
    "de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember",
    "fr": "janvier février mars avril mai juin juillet août septembre octobre novembre décembre",
    "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",
    "pt": "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro",
    "it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre",
    "nl": "januari februari maart april mei juni juli augustus september oktober november december",
    "fi": "tammikuuta helmikuuta maaliskuuta huhtikuuta toukokuuta kesäkuuta heinäkuuta elokuuta syyskuuta "
          "lokakuuta marraskuuta joulukuuta",
    "th": "มกราคม กุมภาพันธ์ มีนาคม เมษายน พฤษภาคม มิถุนายน กรกฎาคม สิงหาคม กันยายน ตุลาคม พฤศจิกายน ธันวาคม",
    "th_abbr": "ม.ค. ก.พ. มี.ค. เม.ย. พ.ค. มิ.ย. ก.ค. ส.ค. ก.ย. ต.ค. พ.ย. ธ.ค.",
}
_MONTHS = {k: [w.replace("_", " ") for w in v.split()] for k, v in _MONTHS_BY_LANGUAGE.items()}
_VI_MONTHS = ["Giêng", "Hai", "Ba", "Tư", "Năm", "Sáu", "Bảy", "Tám", "Chín", "Mười", "Mười Một", "Chạp"]


def _cjk_year(y: int) -> str:
    return "".join(_CJK_DIGITS[int(c)] for c in str(y))


def _cjk_small(n: int) -> str:
    if n < 10:
        return _CJK_DIGITS[n]
    t, u = divmod(n, 10)
    return ("" if t == 1 else _CJK_DIGITS[t]) + "十" + (_CJK_DIGITS[u] if u else "")


def _in_digits(s: str, zero: int) -> str:
    return "".join(chr(zero + int(c)) if "0" <= c <= "9" else c for c in s)


def dates_with_a_year(y: int, m: int, d: int) -> list[str]:
    """A month with a year, and with a day, written in many scripts and calendars."""
    f = [f"{y}年{m}月{d}日", f"{y}年{m:02d}月{d:02d}日", f"{y} 年 {m} 月 {d} 日",
         _in_digits(f"{y}年{m}月{d}日", 0xFF10), f"{y}年{m}月", f"{y}年{m}月{d}号", f"{y % 100:02d}年{m}月{d}日",
         _cjk_year(y) + "年" + _cjk_small(m) + "月" + _cjk_small(d) + "日",
         f"{y}년 {m}월 {d}일", f"{y}년{m}월{d}일", f"{y}년 {m}월", f"{y}. {m}. {d}.",
         f"ngày {d} tháng {m} năm {y}", f"{d} tháng {m} năm {y}", f"tháng {m} năm {y}", f"tháng {m}/{y}",
         f"Ngày {d:02d} Tháng {m:02d} Năm {y}", f"ngay {d} thang {m} nam {y}", f"{d} thg {m}, {y}",
         f"Tháng {_VI_MONTHS[m - 1]} năm {y}", f"{d}/{m}/{y + 543}", f"{y + 543}-{m:02d}-{d:02d}",
         _in_digits(f"{d}/{m}/{y}", 0x0660), _in_digits(f"{y}/{m}/{d}", 0x06F0), _in_digits(f"{d}.{m}.{y}", 0x0966),
         _in_digits(f"{d}/{m}/{y + 543}", 0x0E50), _in_digits(f"{y}-{m:02d}-{d:02d}", 0xFF10),
         f"{d}hb {_MONTHS['ms'][m - 1]} {y}", f"{d}. {_MONTHS['de'][m - 1]} {y}",
         f"{d} de {_MONTHS['es'][m - 1]} de {y}", f"{d} {_MONTHS['ru'][m - 1]} {y} г.",
         f"{d} {_MONTHS['th'][m - 1]} {y + 543}", f"{d} {_MONTHS['th_abbr'][m - 1]} {y + 543}",
         f"{_MONTHS['th'][m - 1]} {y + 543}", f"{d} {_MONTHS['th'][m - 1]} พ.ศ. {y + 543}"]
    if y >= 2019:
        n = y - 2018
        f += [f"令和{n}年{m}月{d}日", f"R{n}.{m}.{d}", f"R{n:02d}/{m:02d}/{d:02d}", f"㋿{n}.{m}.{d}"]
        if n == 1:
            f.append(f"令和元年{m}月{d}日")
    if 1989 <= y <= 2019:
        n = y - 1988
        f += [f"平成{n}年{m}月{d}日", f"H{n}.{m}.{d}", f"H{n}/{m}/{d}", f"㍻{n}年{m}月{d}日",
              "平成" + _cjk_small(n) + "年" + _cjk_small(m) + "月" + _cjk_small(d) + "日"]
    for lang in ("ms", "id", "ru", "uk", "el", "ar", "lev", "he", "hi", "tr", "pl", "de", "fr", "es", "pt", "it",
                 "nl", "fi"):
        mon = _MONTHS[lang][m - 1]
        f.append(f"{d} {mon} {y}")
        if lang in ("ar", "lev"):
            f.append(_in_digits(f"{d} {mon} {y}", 0x0660))
        if len(mon) > 3:
            f.append(f"{mon} {y}")
    return f


def dates_without_a_year(m: int, d: int) -> list[str]:
    """A month and a day with no year."""
    f = [f"{m}月{d}日", f"{m}月{d}号", f"{m} 月 {d} 日", _cjk_small(m) + "月" + _cjk_small(d) + "日", f"{m}월 {d}일",
         f"{d} tháng {m}", f"{m:02d}-{d:02d}", f"{m:02d}{d:02d}", f"{d:02d}.{m:02d}.", f"{d}.{m}."]
    if d > 12:  # read as a day by its number over 12
        f += [f"{m}/{d}", f"{d}/{m}", f"{d}-{m}", f"{m}-{d}", f"{m} - {d}", f"{d}–{m}"]
    return f


def a_month_or_a_day_alone(m: int, d: int) -> list[str]:
    f = [f"{m}月", f"{m}월", f"tháng {m}", f"{d}日", f"{d}일", _cjk_small(m) + "月", f"Day {d} Month {m}",
         f"Tag {d} Monat {m}", f"Jour {d} Mois {m}", f"Dia {d} Mes {m}"]
    f += [_MONTHS[lang][m - 1] for lang in ("ms", "id", "ru", "de", "tr", "pl", "fi", "nl", "th")
          if len(_MONTHS[lang][m - 1]) > 4]
    if d <= 12 and m != d:
        f += [f"{m}-{d}", f"{m}/{d}"]
    if d > 12:
        f += [f"{d}.{m}", f"{m}.{d}"] + ([f"{m}{d}"] if m >= 10 else [])
    return f


_DATE_CONTEXTS = ["{x}", "WBC {x}", "{x} Glucose", "体重 {x}", "Visit {x}", "Weight ({x})", "{x}_HbA1c", "Lab: {x}",
                  "Hb {x} (g/dL)", "检查 {x}"]
_ORDINARY_HEADERS = ["Sex", "WBC", "Glucose", "Age", "Weight", "Height", "Sodium", "Potassium", "BMI", "Stage",
                     "Diagnosis", "Drug", "Arm", "Visit", "Race", "State", "Country", "Notes", "Score", "Dose"]


class DatesInColumnNamesInAnyScriptOfRoundEight(unittest.TestCase):
    """Round 8 of the fail-closed review (2026-11-25, 1.0.1): a column name holding a full date written in
    Chinese, Japanese, Korean, Vietnamese or Malay (2019年3月14日, 2019년 3월 14일, 14 tháng 3 năm 2019, 14 Mac
    2019, R1.5.1) was copied to the output, because the column-name check read 年, 月 and 日 as column words and
    the date patterns read only Latin month names and ASCII digits. One set of date grammars now reads cells and
    column names alike, after folding compatibility forms and every script's digits. The tests generate the
    dates from month names, numerals and calendars written here, in many contexts. Every date is invented."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def some_dates(seed: int, n: int = 6) -> list[tuple[int, int, int]]:
        import random
        rng = random.Random(seed)
        out = [(2019, 3, 14), (2019, 5, 1), (2021, 12, 31), (2008, 11, 5)]
        while len(out) < n + 4:
            out.append((rng.choice([1998, 2003, 2008, 2012, 2016, 2019, 2020, 2021, 2023]), rng.randint(1, 12),
                        rng.randint(1, 28)))
        return out

    def judge(self, names: list[str]) -> dict[str, object]:
        rows = [_ORDINARY_HEADERS + [h] for h in names]
        return {h: ("refused" if r == "refused" else "withheld" if len(_ORDINARY_HEADERS) + 1 in r else "shown")
                for h, r in zip(names, header_probe(self.tmp, rows))}

    # High: a full date, a month and a year, or a month and a day in a column name, in any script or calendar the
    # cells are read in, is refused like an identifier pattern; four digits with no leading zero that read as a
    # month and a day (1231) are withheld, since a room or a code is written so too.
    def test_dates_in_column_names_in_any_script_are_refused(self):
        import random
        rng = random.Random(81)
        names, four = [], set()
        for y, m, d in self.some_dates(80):
            for x in dates_with_a_year(y, m, d) + dates_without_a_year(m, d):
                variants = [c.format(x=x) for c in rng.sample(_DATE_CONTEXTS, 3)]
                names += variants
                if re.fullmatch(r"[1-9]\d{3}", x):
                    four.update(variants)
        self.assertGreater(len(names), 2500)
        judged = self.judge(names)
        self.assertEqual([h for h, r in judged.items() if r == "shown"], [], "a date in a column name was shown")
        self.assertEqual([h for h, r in judged.items() if r != "refused" and h not in four], [],
                         "a date in a column name was not refused")
        # The headers of the finding, end to end: the run is refused and prints no column name.
        finding = ["2019年3月14日", "WBC 2019年3月14日", "体重 3月14日", "体重 2019年3月", "2019年12月31日", "2019年1月",
                   "3月14日", "2019년 3월 14일", "3월 14일", "2019년 3월", "14 tháng 3 năm 2019", "14 Mac 2019",
                   "R1.5.1", "3 月 14 日"]
        for h in finding:
            raw = write_csv(self.tmp / "wide.csv", _ORDINARY_HEADERS + [h], [[str(i)] * 21 for i in range(30)])
            p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR)
            self.assertEqual(p.returncode, 2, (h, p.stdout + p.stderr))
            self.assertIn("looks like data or carries identifiers", p.stderr)
            self.assertNotIn(h, p.stdout + p.stderr)
            self.assertFalse((self.tmp / "out" / "wide_deidentified.csv").exists())

    # Low: a month or a day alone (3月, 3월, tháng 3, 14日, a month name of another language as a word), a word
    # for a day and one for a month with numbers (Day 14 Month 3), two numbers of 12 or less joined by a hyphen or
    # a slash, and a decimal that reads as a day and a month are withheld: never printed, written as column_N.
    def test_a_month_or_a_day_alone_in_a_column_name_is_withheld(self):
        import random
        rng = random.Random(82)
        names = []
        for y, m, d in self.some_dates(82):
            for x in a_month_or_a_day_alone(m, d):
                names += [c.format(x=x) for c in rng.sample(_DATE_CONTEXTS, 2)]
        self.assertGreater(len(names), 300)
        judged = self.judge(names)
        self.assertEqual([h for h, r in judged.items() if r == "shown"], [], "a date element in a column name was shown")
        header = ["Patient ID", "3月", "tháng 3", "Day 14 Month 3", "WBC 14.3", "WBC 3-4", "Glucose"]
        rows = [[str(4100000 + i), str(80 + i), str(90 + i), str(i % 5), f"{6 + i % 4}.{i % 10}", str(i % 9), str(70 + i)]
                for i in range(40)]
        raw = write_csv(self.tmp / "parts.csv", header, rows)
        plan = run("plan", str(raw))
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        for h in header[1:6]:
            self.assertNotIn(h, plan.stdout)
        p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        report = json.loads((self.tmp / "out" / "deidentification_report.json").read_text(encoding="utf-8"))
        names = output_names(report, header)
        self.assertEqual([names[h] for h in header[1:6]], [f"column_{i}" for i in range(2, 7)])
        self.assertEqual(names["Glucose"], "Glucose")

    # Over-redaction check: ordinary column names with numbers and dates of a year alone stay shown.
    def test_ordinary_column_names_with_numbers_stay_shown(self):
        shown = """2019年|2019년|Visit 2019|Day 14|Month 3|Weeks 1-4|Grade 3/4|Score 1-10|Age 12-18|Age 18-65|BMI 18.5-24.9|
Hb < 13.5|Dose 2.5 mg|HbA1c (%)|eGFR 60|Year of Diagnosis|体重|Stage|COVID-19|IL-6|CA 19-9|CA 15-3|PHQ-9|L4-5|
Glucose 70-100|K 3.5-5.0|Cycle 1 Day 1|C1D1|Week 12|Jour 14|Día 14|Creatinine 1.0|Grade 2.1|Weeks 4-12|Q1|2nd Line|
FY2022 Cost|Hb 13-17|Temp 36.5-37.5|Age 5-12|Ratio 3/4|Day 3-4|Weeks 3-19|Score 0-10|ECOG 0-1|Dose 1-2 mg|
Duration 3-4 days|SF-36|EQ-5D|T2-T4|Visit 1|Week 2|Year 1|Hb > 12.5|Pain 3-4|Level 2-3|Stage 3/4|Glucose (mg/dL)|
Age 90+|Grade 3/4 AE|Week 12 Score|Weight (kg)|Sodium|Patient ID|Visit Date|Year""".replace("\n", "").split("|")
        judged = self.judge(shown)
        self.assertEqual({h: r for h, r in judged.items() if r != "shown"}, {}, "an ordinary column name was hidden")

    # The cells and the column names share one definition: in a column the person keeps, every date of the sweep
    # with a year keeps only its Gregorian year (Buddhist and Japanese-era years converted), or [DATE] when its
    # calendar's year is not read as one, and a month and a day with no year become [DATE].
    def test_dates_in_kept_text_in_any_script_keep_only_the_year(self):
        texts, expected = [], []
        for y, m, d in self.some_dates(83):
            for x in dates_with_a_year(y, m, d):
                texts.append(f"Seen {x} in clinic")
                expected.append(str(y))
            for x in [f"{m}月{d}日", f"{m}월 {d}일", f"{d} tháng {m}", _cjk_small(m) + "月" + _cjk_small(d) + "日"]:
                texts.append(f"Seen {x} in clinic")
                expected.append("[DATE]")
        self.assertGreater(len(texts), 700)
        results = scrub_probe(self.tmp, texts)
        missed = [t for t, (out, kinds) in zip(texts, results) if "date" not in kinds or out == t]
        self.assertEqual(missed, [], "a date in kept text was kept")
        for t, want, (out, _) in zip(texts, expected, results):
            self.assertTrue(out.startswith("Seen ") and out.endswith(" in clinic"), (t, out))
            # What is left of the date is its year, or a placeholder, and no other number (a word of the date may stay,
            # as "tháng" when the cell patterns took "3/2019" first).
            middle = re.sub(r"\[[A-Z0-9_]+\]", "", out[len("Seen "):-len(" in clinic")])
            self.assertLessEqual(set(re.findall(r"\d+", middle)), {want}, (t, out))
            self.assertNotIn(t[len("Seen "):-len(" in clinic")], out)
        # Years of a Buddhist or a Japanese era are converted; years of a calendar the script does not convert are not
        # kept as a year.
        converted = scrub_probe(self.tmp, ["14 มีนาคม 2562", "令和元年5月1日", "H31.4.30", "平成三十一年四月三十日",
                                           "١٤ آذار ٢٠١٩", "1398/12/23", "14/03/2562"])
        self.assertEqual([o for o, _ in converted], ["2019", "2019", "2019", "2019", "2019", "[DATE]", "[DATE]"])
        # End to end: a column of such dates under any name keeps only the years in a default run (every value is a
        # date), and a kept text column of notes that mention them keeps only the years too.
        header = ["Patient ID", "Visit", "Follow Up", "Glucose"]
        dated = ["2019年3月14日", "14 tháng 3 năm 2019", "R1.5.1", "14 Mac 2019", "平成31年4月30日", "14 มีนาคม 2562"]
        short = ["2019年3月14日", "R1.5.1", "14 Mac 2019", "平成31年4月30日", "2019년 3월 14일", "14 มีนาคม 2562"]
        rows = [[str(4200000 + i), dated[i % 6], f"Seen {short[(i + 1) % 6]}", str(80 + i)] for i in range(42)]
        raw = write_csv(self.tmp / "kept.csv", header, rows)
        p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(self.tmp / "out" / "kept_deidentified.csv")
        self.assertEqual({r["Visit"] for r in out}, {"2019"})
        self.assertEqual({r["Follow Up"] for r in out}, {"[REDACTED]"})
        p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR, "--keep", "Follow Up")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(self.tmp / "out" / "kept_deidentified.csv")
        self.assertEqual({r["Follow Up"] for r in out}, {"Seen 2019"})

    # Low: a word for a person beside a word that can be a surname ("Patient White", "Dr Ward"), and two words that
    # can be names side by side ("Weight Bill White"), are withheld; a person word beside a column word is shown.
    def test_a_person_word_beside_a_surname_in_a_column_name_is_withheld(self):
        people = ["Patient", "Pt", "Dr", "Doctor", "Nurse", "Mother", "Father", "Subject", "Mrs", "Prof", "Spouse",
                  "Surgeon", "Participant", "Guardian", "Physician"]
        surnames = ["White", "Cook", "Ward", "Price", "Long", "Foster", "Young", "Black", "Hall", "King", "Bell",
                    "Rose", "Mills", "Grant"]
        names = [f"{p} {s}" for p in people for s in surnames] + [f"{s} {p}" for p in people[:5] for s in surnames]
        names += [f"{p} Bill White" for p in people[:4]] + ["Weight Bill White", "Glucose Rose Hall", "WBC Grace Cook"]
        judged = self.judge(names)
        self.assertEqual([h for h, r in judged.items() if r == "shown"], [], "a surname beside a person word was shown")
        ordinary = ["Patient Status", "Patient Age", "Doctor Visit", "Nurse Station", "Mother Height", "Subject Weight",
                    "Patient Head Circumference", "Temp Min Max", "Reference Low", "Race White", "Physician Specialty",
                    "Wells Score", "White Matter Volume", "Patient ID"]
        self.assertEqual({h: r for h, r in self.judge(ordinary).items() if r != "shown"}, {})

    # Low: grid coordinates in metres under a column name that names only a unit of length ("X (m)") were kept.
    def test_grid_coordinates_under_a_bare_unit_of_length_are_redacted(self):
        import random
        rng = random.Random(84)
        east = [f"{rng.uniform(500000, 600000):.2f}" for _ in range(60)]
        north = [str(rng.randint(4100000, 4200000)) for _ in range(60)]
        grid = ["X (m)", "Y (m)", "Value (m)", "Pos (km)", "X [m]", "Coord (ft)", "Loc (m)", "E (m)", "N (m)"]
        for values in (east, north):
            decided = probe(self.tmp, "decide", [(h, values) for h in grid])
            self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], "grid coordinates kept")
        lengths = [f"{rng.uniform(10000, 99999):.1f}" for _ in range(60)]
        named = ["Distance (m)", "Height (m)", "Elevation (m)", "Depth (m)", "Length (km)", "Altitude (ft)"]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [(h, lengths) for h in named])], ["keep"] * 6)

    # Low: a measurement name beside a word for a label, a pseudonym, a lot or a batch, or a number sign, names a
    # number of a thing; under a name of time, six or more digits are a date or a clock time written as a number.
    def test_label_lot_and_number_sign_beside_a_measurement_name_are_identifiers(self):
        import random
        rng = random.Random(85)
        for digits in (4, 5, 6):
            pool = [str(rng.randrange(10 ** (digits - 1), 10 ** digits)) for _ in range(12)]
            values = [rng.choice(pool) for _ in range(60)]
            names = [f"{m} {w}" for m in ("WBC", "Score", "Count", "Dose", "Glucose") for w in
                     ("Label", "Pseudo", "Pseudonym", "Lot", "Batch", "#", "Lot No")] + ["Count#", "Dose#"]
            decided = probe(self.tmp, "decide", [(h, values) for h in names])
            self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], digits)
        counts = [str(rng.randint(1, 40)) for _ in range(60)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [(h, counts) for h in
                                                                       ("# of Visits", "Visits (#)", "Count")])],
                         ["keep"] * 3)
        clock = [f"{rng.randint(0, 23):02d}{rng.randint(0, 59):02d}{rng.randint(0, 59):02d}" for _ in range(40)]
        hl7 = [f"{rng.randint(10, 23)}{rng.randint(10, 59)}{rng.randint(10, 59)}.{rng.randint(100, 999)}" for _ in range(40)]
        unix9 = [f"{rng.randint(100000000, 999999999)}.{rng.randint(10, 99)}" for _ in range(40)]
        for values in (clock, hl7, unix9):
            decided = probe(self.tmp, "decide", [(h, values) for h in ("Time", "Duration", "Days", "Interval",
                                                                       "Event Time", "Visit Day")])
            self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [])

    # Low: record numbers that repeat in a few cells of a measurement column were kept below a share; viral loads
    # and read counts that do not repeat, or repeat as a round assay limit, are kept.
    def test_repeated_record_numbers_among_measurements_are_found_whatever_their_share(self):
        import random
        rng = random.Random(86)
        for share in (2, 3, 5, 8):
            values = [str(rng.randint(60, 140)) for _ in range(100 - share)]
            values += [rng.choice(["4527832", "5521003", "6617221"]) for _ in range(share)]
            values += [values[-1]]
            rng.shuffle(values)
            decided = probe(self.tmp, "decide", [(h, values) for h in ("Glucose", "WBC", "Count", "Score", "Dose")])
            self.assertEqual([(h, a) for h, a, _ in decided if a == "keep"], [], share)
        loads = [str(rng.randint(1000000, 9000000)) for _ in range(60)] + ["10000000"] * 6
        reads = [str(rng.randint(10 ** 7, 9 * 10 ** 7)) for _ in range(60)]
        self.assertEqual([a for _, a, _ in probe(self.tmp, "decide", [("Viral Load (copies/mL)", loads),
                                                                       ("Total Reads", reads)])], ["keep", "keep"])

    # Low: a zero-width joiner or non-joiner, or a direction mark, in a column name of a script without capital
    # letters (Persian spelling, an Arabic export, an Indic conjunct, an emoji) no longer stops the run; in a name
    # with capital letters it is refused as before, and the message names --no-header.
    def test_joiners_in_a_script_without_capitals_are_allowed(self):
        allowed = ["نام\u200cخانوادگی", "شماره\u200cپرونده", "تاریخ\u200cتولد", "الجنس\u200f", "\u200fالوزن",
                   "קוד\u200f", "क्\u200dष", "👨\u200d👩\u200d👧", "\u061cالعمر"]
        judged = self.judge(allowed)
        self.assertEqual([h for h, r in judged.items() if r == "refused"], [])
        refused = ["Ok\u200cafor", "Smi\u200bth", "Hb\u200f", "W\u200dBC", "Glu\u00adcose", "Na\u2060me"]
        self.assertEqual(set(self.judge(refused).values()), {"refused"})
        raw = write_csv(self.tmp / "joiner.csv", ["Sex", "Smi\u200bth"], [["F", "1"]] * 5)
        p = run("plan", str(raw))
        self.assertEqual(p.returncode, 2)
        self.assertIn("--no-header", p.stderr)
        raw = write_csv(self.tmp / "persian.csv", ["Sex", "شماره\u200cپرونده", "Glucose"],
                        [["F", str(4300000 + i), str(90 + i)] for i in range(20)])
        p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(self.tmp / "out" / "persian_deidentified.csv")
        self.assertEqual(list(out[0]), ["Sex", "column_2", "Glucose"])
        self.assertNotIn("4300000", json.dumps(out))

    # Low: two columns with the same name stopped the run with no option the agent could use; --number-duplicates
    # gives the later one its position.
    def test_repeated_column_names_can_be_numbered(self):
        header = ["Patient ID", "Glucose", "Sex", "Glucose", "Glucose"]
        rows = [[str(4400000 + i), str(80 + i), "F", str(90 + i), str(100 + i)] for i in range(30)]
        raw = write_csv(self.tmp / "dups.csv", header, rows)
        p = run("plan", str(raw))
        self.assertEqual(p.returncode, 2)
        self.assertIn("--number-duplicates", p.stderr)
        p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR, "--number-duplicates")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = read_rows(self.tmp / "out" / "dups_deidentified.csv")
        self.assertEqual(list(out[0]), ["Patient ID", "Glucose", "Sex", "Glucose_4", "Glucose_5"])
        self.assertEqual([r["Glucose_4"] for r in out], [row[3] for row in rows])
        p = run("verify", str(self.tmp / "out" / "dups_deidentified.csv"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    # The regression table of round 8: an ordinary invented 30-column clinical table whose column names carry
    # numbers, units, a year and words in other scripts. A default run keeps the columns it can verify, redacts the
    # text and the numbers it cannot, shows every column name, and completes with exit 0 once the person keeps the
    # columns they confirm.
    def test_ordinary_clinical_table_regression_after_round_eight(self):
        header = ["Patient ID", "Age", "Sex", "Race", "State", "Country", "Diagnosis", "ICD10", "Drug", "Dose (mg)",
                  "Site", "Arm", "Visit", "Visit Date", "Glucose (mg/dL)", "HbA1c (%)", "Hb 13-17", "CA 19-9",
                  "Systolic BP", "体重 (kg)", "BMI", "Pain Score", "ECOG 0-1", "Grade 3/4 AE", "Stage", "Gene",
                  "Ensembl ID", "Week 12 Score", "2019年 Cohort", "Notes"]
        dx = [("Type 2 diabetes", "E11.9"), ("Hypertension", "I10"), ("Asthma", "J45.909"), ("Heart failure", "I50.9")]
        genes = [("TP53", "ENSG00000141510"), ("EGFR", "ENSG00000146648"), ("KRAS", "ENSG00000133703")]
        pids = [str(4500000 + 41 * k) for k in range(40)]
        rows = []
        for i in range(160):
            d, code = dx[i % 4]
            g, ens = genes[i % 3]
            rows.append([pids[i % 40], str(25 + (i * 7) % 60), "F" if i % 2 else "M",
                         ["White", "Asian", "Black or African American"][i % 3], ["CA", "NY", "TX"][i % 3],
                         ["United States", "Canada"][i % 2], d, code, ["Metformin", "Lisinopril"][i % 2],
                         str([500, 1000, 10][i % 3]), ["Lung", "Breast", "Colon"][i % 3], ["Placebo", "Active"][i % 2],
                         ["Baseline", "Week 4", "Week 12"][i % 3], f"2021-{1 + i % 12:02d}-{1 + i % 28:02d}",
                         str(80 + (i * 13) % 120), f"{5.2 + (i % 30) / 10:.1f}", f"{12 + (i % 6) * 0.5:.1f}",
                         str(10 + (i * 3) % 50), str(100 + (i * 3) % 60), f"{55 + (i % 30) * 0.8:.1f}",
                         f"{19 + (i % 15) * 0.7:.1f}", str(i % 11), str(i % 2), ["Yes", "No"][i % 2],
                         ["Stage I", "Stage II", "Stage IV"][i % 3], g, ens, str(i % 10), ["Yes", "No"][(i + 1) % 2],
                         "Follow-up in clinic as planned, tolerating treatment well with no new complaints today."])
        raw = write_csv(self.tmp / "clinical30_r8.csv", header, rows)
        p, out, report = self._run(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(output_names(report, header), {h: h for h in header})
        actions = {d["column"]: d["action"] for d in report["decisions"]}
        kept = {"Sex", "Race", "State", "Country", "ICD10", "Dose (mg)", "Glucose (mg/dL)", "HbA1c (%)", "Hb 13-17",
                "CA 19-9", "Systolic BP", "体重 (kg)", "BMI", "Pain Score", "ECOG 0-1", "Grade 3/4 AE", "Stage",
                "Ensembl ID", "Week 12 Score", "2019年 Cohort"}
        unverified = {"Diagnosis", "Drug", "Site", "Arm", "Visit", "Gene"}
        self.assertEqual({c for c, a in actions.items() if a == "keep"}, kept)
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, unverified)
        self.assertEqual((actions["Patient ID"], actions["Visit Date"], actions["Notes"]), ("pseudonym_id", "year", "redact"))
        p, out, report = self._run(raw, *[a for c in sorted(unverified) for a in ("--keep", c)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            if col in kept | unverified:
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        written = json.dumps(out)
        for pid in pids:
            self.assertNotIn(pid, written)

    def _run(self, path: Path, *extra: str):
        out_dir = self.tmp / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        report = out_dir / "deidentification_report.json"
        return (p, read_rows(out) if out.exists() else [],
                json.loads(report.read_text(encoding="utf-8")) if report.exists() else {})


# Round 9 helpers: month abbreviations the cells are read in, written as the review wrote them (with accents).
_ABBREVIATED_MONTHS = {
    "pl": ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"],
    "cs": ["led", "úno", "bře", "dub", "kvě", "čvn", "čvc", "srp", "zář", "říj", "lis", "pro"],
    "tr": ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
    "nl": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
    "id": ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"],
    "ms": ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"],
    "ro": ["ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct", "noi", "dec"],
    "hu": ["jan", "febr", "márc", "ápr", "máj", "jún", "júl", "aug", "szept", "okt", "nov", "dec"],
    "fi": ["tammik", "helmik", "maalisk", "huhtik", "toukok", "kesäk", "heinäk", "elok", "syysk", "lokak", "marrask",
           "jouluk"],
    "sv": ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    "it": ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "tl": ["Ene", "Peb", "Mar", "Abr", "May", "Hun", "Hul", "Ago", "Set", "Okt", "Nob", "Dis"],
    "uk": ["січ", "лют", "бер", "квіт", "трав", "черв", "лип", "серп", "вер", "жовт", "лист", "груд"],
    "el": ["Ιαν", "Φεβ", "Μαρ", "Απρ", "Μάι", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ"],
}
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


class ColumnNameTokensAndMeasurementCellsOfRoundNine(unittest.TestCase):
    """Round 9 of the fail-closed review (2026-11-26, 1.0.1). The classes still open were column names, where a
    date, an age over 89 or a coordinate was shown when an underscore, a dot, a pipe or a comma joined its parts
    (WBC_03_14, Age_102, Lat_37.77) or when its month was a Roman numeral or an abbreviation of another language
    (14.III.2019, 14-Paź-19), and measurement columns, whose name was trusted although the plan said every cell was
    checked. Column names are now read as tokens and fail closed by token, the detectors read every
    separator-normalised form of a name, and every cell of a measurement column is checked. The tests generate the
    names and values; every name, number, date and place here is invented."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="safe_harbor_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def judge(self, names: list[str]) -> dict[str, object]:
        rows = [_ORDINARY_HEADERS + [h] for h in names]
        return {h: ("refused" if r == "refused" else "withheld" if len(_ORDINARY_HEADERS) + 1 in r else "shown")
                for h, r in zip(names, header_probe(self.tmp, rows))}

    def run_file(self, path: Path, *extra: str):
        out_dir = self.tmp / "out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        p = run("run", str(path), "-o", str(out_dir), "--reference-year", REFERENCE_YEAR, *extra)
        out = out_dir / f"{path.stem}_deidentified{path.suffix}"
        report = out_dir / "deidentification_report.json"
        return (p, read_rows(out) if out.exists() else [],
                json.loads(report.read_text(encoding="utf-8")) if report.exists() else {})

    # Medium: a month and a day, an age over 89 or a coordinate in a column name was shown when the parts were joined
    # by an underscore, a space, a dot, a pipe, a comma or brackets, although the slash or the hyphen form was refused.
    def test_dates_ages_and_coordinates_in_column_names_fail_closed_with_any_separator(self):
        seps = ["_", " ", ".", "-", "|", ",", "/", "__", " _ ", ": ", "; "]
        pairs = [(3, 14), (14, 3), (12, 31), (31, 12), (7, 4), (1, 13), (9, 19), (3, 4), (11, 12), (2, 28)]
        contexts = ["WBC", "Glucose", "Hb", "Visit", "Lab", "CRP", "Weight", "Score", "Na"]
        names = []
        for c in contexts:
            for a, b in pairs:
                for pad in (False, True):
                    x, y = (f"{a:02d}", f"{b:02d}") if pad else (str(a), str(b))
                    names += [f"{c}{sep}{x}{sep}{y}" for sep in seps] + [f"{c} ({x}_{y})"]
                    if a <= 12:
                        names.append(f"{c}_M{x}_D{y}")  # a month and a day after letters for them
        ages = [f"{w}{sep}{n}" for w in ("Age", "Aged", "Age at Dx", "Edad") for n in (90, 95, 102, 110, 125)
                for sep in seps + [""]]
        coords = [f"{w}{sep}{v}" for w in ("Lat", "Lon", "Lng", "Loc", "Location", "Coord", "GPS", "Geo")
                  for v in ("37.77", "-122.45", "37.7749", "51.50", "-33.87") for sep in seps + [""]]
        coords += [f"{w}{sep}37.77{sep}-122.45" for w in ("Loc", "Site", "Point", "Home") for sep in (" ", "_", ", ", "|")]
        judged = self.judge(names + ages + coords + ["M3D14", "Mo3Dy14", "m03d14", "Month3Day14"])
        self.assertGreater(len(judged), 2400)
        self.assertEqual([h for h, r in judged.items() if r == "shown"], [], "a date, an age or a coordinate was shown")
        finding = ["WBC_03_14", "WBC_14_03", "WBC_3_14", "WBC_12_31", "Glucose_03_14", "Hb_14_3", "Visit_03_14",
                   "Visit_14_03", "Visit 14 03", "Visit 3 14", "Visit 31 12", "Lab_31_12", "Lab 31 12", "CRP_07_04",
                   "WBC 03 14", "WBC.03.14", "WBC|03|14", "WBC,03,14", "WBC (03_14)", "WBC__03__14", "Age_102",
                   "Aged_102", "Age-95", "Age.95", "Lat_37.77", "Lon_-122.45", "Loc 37.77 -122.45", "Loc_37.77_-122.45"]
        self.assertEqual({h: r for h, r in self.judge(finding).items() if r != "refused"}, {}, "not refused")
        # End to end: the run is refused, names the column's position and never prints its name.
        raw = write_csv(self.tmp / "wide.csv", ["Patient ID", "WBC", "WBC_03_14", "Sex"],
                        [[str(4100000 + i), "5.1", "6.2", "F"] for i in range(20)])
        p = run("run", str(raw), "-o", str(self.tmp / "out"), "--reference-year", REFERENCE_YEAR)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("(#3)", p.stderr)
        self.assertNotIn("03_14", p.stdout + p.stderr)
        # Ordinary names with numbers stay shown.
        ordinary = ["Visit 3", "Cycle 2 Day 15", "C1D15", "Age 18-64", "Age 90+", "BMI 18.5-24.9", "Score 1-10",
                    "Grade 3/4", "HbA1c (%)", "IL-6", "CD34", "Week 12", "30 Day Mortality", "Hb < 13.5", "Weight_kg",
                    "eGFR (mL/min/1.73m2)", "FY2022 Cost", "Glucose_mg_dL", "PHQ9_Item_3", "Visit_2021", "Ki-67", "L4-5"]
        self.assertEqual({h: r for h, r in self.judge(ordinary).items() if r != "shown"}, {}, "an ordinary name hidden")

    # Low: a plate, an email written with its punctuation replaced, a given name that folds to a score and a role
    # alone were shown as column names.
    def test_identifier_shapes_and_name_like_words_in_column_names_are_not_shown(self):
        names = ["Plate_7ABC123", "Email_a_b_co", "Mail_j_doe_org", "Åsa", "Priest", "Plate 7ABC123", "Tel_415_555_0134"]
        self.assertEqual([h for h, r in self.judge(names).items() if r == "shown"], [])
        self.assertEqual({h: r for h, r in self.judge(["Âge", "Età", "Yaş", "Ålder", "Año"]).items() if r != "shown"}, {})

    # Medium: a full date with a Roman-numeral month or an abbreviated month of another language was shown and copied
    # to the output; with a day and a year it is refused now, and a month with one number is withheld.
    def test_roman_and_abbreviated_months_in_column_names_fail_closed(self):
        import random
        rng = random.Random(91)
        contexts = ["{x}", "WBC {x}", "Hb {x}", "Visit {x}", "Glucose_{x}"]
        full, partial = [], []
        for lang, months in _ABBREVIATED_MONTHS.items():
            for m, mon in enumerate(months, start=1):
                d, y = rng.randint(1, 28), rng.choice([2008, 2015, 2019, 2021, 2024])
                full += [f"{d}-{mon}-{y % 100:02d}", f"{d}/{mon}/{y % 100:02d}", f"{d}.{mon}.{y % 100:02d}",
                         f"{d}{mon}{y}", f"{d} {mon} {y}", f"{d}-{mon}-{y}", f"{d}.{mon}.{y}", f"{d}/{mon}/{y}"]
                partial += [f"{mon}-{y % 100:02d}", f"{mon} {y}", f"{mon}'{y % 100:02d}", f"{d} {mon}"]
        for m, r in enumerate(_ROMAN, start=1):
            for d, y in ((14, 2019), (5, 2021), (28, 2008)):
                full += [f"{d}.{r}.{y}", f"{d}/{r}/{y}", f"{d}-{r}-{y}", f"{d}.{r.lower()}.{y}", f"{r}/{y}", f"{r}.{y}",
                         f"{y}.{r}", f"{y}-{r}", f"{r}-{y}"]
                if len(r) > 1:
                    full.append(f"{d} {r} {y}")
                partial += [f"{r} {y}", f"{d} {r}", f"{d}.{r}."]
        full_names = [c.format(x=x) for x in full for c in rng.sample(contexts, 2)]
        partial_names = [c.format(x=x) for x in partial for c in rng.sample(contexts, 2)]
        self.assertGreater(len(full_names) + len(partial_names), 3000)
        judged = self.judge(full_names + partial_names)
        self.assertEqual([h for h, r in judged.items() if r == "shown"], [], "a date element in a column name was shown")
        self.assertEqual([h for h in full_names if judged[h] != "refused"], [], "a full date was not refused")
        finding = ["Hb 14.III.2019", "Hb 5 IV 2019", "WBC 14/III/2019", "Visit 14 VII 2020", "Hb 14 III 2019",
                   "Hb 2019.III", "Hb III/2019", "WBC 14-Paź-19", "WBC 14-Úno-19", "WBC 14Úno2019", "WBC 14Bře2019",
                   "WBC 14-Kvě-19", "WBC 14Říj2019"]
        self.assertEqual({h: r for h, r in self.judge(finding).items() if r != "refused"}, {})
        # The same dates in kept text become the year, or [DATE] for a two-digit year.
        values = ["seen 14.III.2019", "seen 14-Paź-19", "seen 14Úno2019", "seen 5 IV 2021", "seen III/2019"]
        raw = write_csv(self.tmp / "cells.csv", ["Visit", "Sex"], [[values[i % 5], "F"] for i in range(20)])
        p, out, _ = self.run_file(raw, "--keep", "Visit")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Visit"] for r in out}, {"seen 2019", "seen [DATE]", "seen 2021"})

    # Medium: under a measurement name a ZIP code, a record number, an Excel serial, a date written as a number and a
    # coordinate were kept verbatim while the plan and the report said the numbers had no such shape. Every cell is
    # checked now, and one such cell puts the column under the person's decision.
    def test_measurement_columns_are_checked_cell_by_cell(self):
        base = ["5.1", "6.2", "4.8", "7.3"] * 30
        odd = ["94110", "7771234", "44269.4375", "37.7749", "-122.4194", "910314", "43538", "4,527,832", "4.52783E+06",
               "20190314", "552345.12", "02134"]
        names = ["WBC", "Weight (kg)", "Score", "Glucose", "Platelets", "Cost", "Steps", "Count", "Total", "Heart Rate",
                 "Dose (mg)", "Pain Score", "Level", "Units", "Rank", "Reads"]
        columns = [(h, base[:k] + [v] + base[k:]) for h in names for k, v in enumerate(odd)]
        decided = probe(self.tmp, "decide", columns)
        self.assertEqual([(h, columns[i][1][i % len(odd)]) for i, (h, a, _) in enumerate(decided) if a == "keep"], [])
        import random
        rng = random.Random(92)
        whole_columns = []
        for h in ("Count", "Score", "Weight", "Total", "Amount", "Steps", "Heart Rate", "Glucose", "Pulse", "Dose", "BMI"):
            whole_columns.append((h, [str(rng.choice([94110, 94117, 10025, 60614, 30309])) for _ in range(60)]))
            whole_columns.append((h, [f"{rng.uniform(32.5, 42):.4f}" for _ in range(60)]))
        records = [str(rng.randint(100000, 999999)) for _ in range(20)]
        for h in ("Count", "Total", "Level", "Score", "Units", "Reads", "Rank", "Steps", "Cost", "Platelets"):
            for form in (str, lambda x: f"{int(x):,}", lambda x: f"{x}.0", lambda x: f"{float(x):.5E}"):
                whole_columns.append((h, [form(records[i % 20]) for i in range(160)]))
        for h in ("Count", "Total", "Score", "Glucose"):  # ZIP codes and Excel serials of whole days, unique
            whole_columns.append((h, [str(rng.randint(43000, 45000)) for _ in range(90)]))
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", whole_columns) if a == "keep"], [])
        # Ordinary measurements stay verified.
        controls = [("WBC", [f"{rng.uniform(4, 11):.1f}" for _ in range(80)]),
                    ("Platelets", [str(rng.randint(150000, 450000)) for _ in range(80)]),
                    ("Steps", [str(rng.randint(2000, 15000)) for _ in range(80)]),
                    ("Total Cost", [f"{rng.uniform(100, 99999):.2f}" for _ in range(80)]),
                    ("Heart Rate", [str(rng.randint(50, 130)) for _ in range(80)]),
                    ("Weight (kg)", [f"{rng.uniform(40, 140):.1f}" for _ in range(80)]),
                    ("Troponin", [f"{rng.uniform(0, 0.5):.4f}" for _ in range(80)]),
                    ("P Value", [f"{rng.uniform(0, 1):.5f}" for _ in range(80)]),
                    ("Log2FC", [f"{rng.uniform(-8, 8):.4f}" for _ in range(80)]),
                    ("Time (s)", [str(rng.randint(10, 99999)) for _ in range(80)]),
                    ("Distance (m)", [f"{rng.uniform(1000, 99999):.1f}" for _ in range(80)]),
                    ("Glucose (mg/dL)", [str(rng.randint(60, 400)) for _ in range(80)])]
        self.assertEqual([h for h, a, _ in probe(self.tmp, "decide", controls) if a != "keep"], [])
        # End to end, the review's file: none of the five values is written, the plan says why, and the person can
        # keep the column with --keep.
        rows = [[f"S{i:03d}", v, "F"] for i, v in enumerate(["5.1", "6.2"] * 60 + odd[:5])]
        raw = write_csv(self.tmp / "wbc.csv", ["Study ID", "WBC", "Sex"], rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for v in odd[:5]:
            self.assertNotIn(v, json.dumps(out))
        wbc = report["decisions"][1]
        self.assertEqual((wbc["action"], wbc["verified"], wbc["needs_decision"]), ("redact", False, True))
        self.assertIn("checks every cell", wbc["finding"])
        p, out, report = self.run_file(raw, "--keep", "WBC")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["WBC"] for r in out], [row[1] for row in rows])
        self.assertEqual([d["column"] for d in report["kept_unverified_columns"]], ["WBC"])
        # A verified measurement column says what was checked.
        raw = write_csv(self.tmp / "ok.csv", ["Study ID", "WBC", "Sex"], [[f"S{i:03d}", "5.1", "F"] for i in range(20)])
        p, _, report = self.run_file(raw)
        self.assertIn("every cell checked", report["decisions"][1]["finding"])
        self.assertIn("every cell", report["kept_text_note"])

    # Medium: a column named for notes, comments or remarks of vocabulary words was kept, although SKILL.md said such a
    # column is never kept.
    def test_notes_columns_are_redacted_whatever_they_hold(self):
        names = ["Notes", "Comments", "Remarks", "Free Text", "Narrative", "Note", "Comment", "Clinical Notes", "Remark",
                 "Nurse Comments", "Notes 2", "Comment Text", "备注", "Bemerkung", "Observaciones", "Commentaires",
                 "Kommentar", "Opmerking", "Memo", "Annotations"]
        values = ["Yes", "No", "stable", "none"] * 30
        decided = probe(self.tmp, "decide", [(h, v) for h in names for v in (values, ["2021-03-14"] * 20, ["5", "7"] * 9)])
        self.assertEqual([(h, a) for h, a, _ in decided if a != "redact"], [])
        refused = keep_probe(self.tmp, [(h, values) for h in names])
        self.assertEqual([h for h, outcome, m in refused if outcome != "refused" or "cannot be kept" not in m], [])
        # End to end: the report lists the column among those that cannot be kept, and --keep exits 2.
        raw = write_csv(self.tmp / "notes.csv", ["Patient ID", "Notes", "Sex"],
                        [[str(4200000 + i), values[i % 4], "F"] for i in range(40)])
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({r["Notes"] for r in out}, {"[REDACTED]"})
        self.assertEqual([d["column"] for d in report["columns_that_cannot_be_kept"]], ["Notes"])
        self.assertEqual(self.run_file(raw, "--keep", "Notes")[0].returncode, 2)
        # A word for notes that qualifies another word names that other thing.
        controls = probe(self.tmp, "decide", [("Comment Type", ["Yes", "No"] * 20), ("Note Date", ["2021-03-14"] * 20)])
        self.assertEqual([a for _, a, _ in controls], ["keep", "year"])

    # Low: --keep on a column of years removed the cap on years 90 or more years ago.
    def test_keep_on_a_column_of_years_keeps_the_cap(self):
        years = ["1931", "1990", "1925", "2001"]
        for h in ("Year", "Dx Yr", "Jahr", "Visit Year", "Cohort Year", "Col3"):
            raw = write_csv(self.tmp / "years.csv", ["Patient ID", h, "Sex"],
                            [[str(4300000 + i), years[i % 4], "F"] for i in range(40)])
            p, out, report = self.run_file(raw, "--keep", h)
            self.assertEqual(p.returncode, 0, (h, p.stdout + p.stderr))
            self.assertEqual({r[h] for r in out}, {"[90_OR_OLDER]", "1990", "2001"}, h)
            self.assertIn("[90_OR_OLDER]", report["decisions"][1]["finding"], h)

    # Low: ordinary clinical column names could not be kept, even with --keep-name.
    def test_ordinary_clinical_words_can_be_kept(self):
        names = ["Gender Identity", "Sexual Orientation", "Pronouns", "Species", "Financial Class", "Advance Directive",
                 "Causality", "Assessment", "Reagent", "Contraception"]
        results = keep_probe(self.tmp, [(h, ["Alpha", "Beta", "Gamma"] * 8) for h in names])
        self.assertEqual([(h, m[:120]) for h, outcome, m in results if outcome != "kept"], [])

    # Low: a wide matrix named V1 to V2000, Gene1 to Gene1000, Feature_00001 or by probe could not be confirmed as a
    # group, and the refusal named no position.
    def test_wide_matrices_are_confirmed_as_a_group(self):
        import random
        rng = random.Random(93)
        cases = [([f"V{i}" for i in range(1, 2001)], "V*"), ([f"Gene{i}" for i in range(1, 1001)], "Gene*"),
                 ([f"Feature_{i:05d}" for i in range(1, 300)], "Feature_*"),
                 (sorted({f"cg{rng.randint(0, 27999999):08d}" for _ in range(500)}), "cg*")]
        for names, pattern in cases:
            header = ["Study ID"] + names
            rows = [[f"S{i:03d}"] + [f"{rng.uniform(0, 1):.3f}" for _ in names] for i in range(12)]
            raw = write_csv(self.tmp / "wide.csv", header, rows)
            p = run("plan", str(raw))
            self.assertEqual(p.returncode, 2, names[0])
            self.assertRegex(p.stderr, r"\(#\d+", names[0])
            last = f"#{len(header)}"
            for extra in (("--keep-name", f"#2-{last}"), ("--keep-name", pattern)):
                p, out, report = self.run_file(raw, *extra, "--keep", f"#2-{last}")
                self.assertEqual(p.returncode, 0, (names[0], extra, p.stderr[-300:]))
                self.assertEqual(list(out[0]), header, names[0])
        # A prefix that names a person, a record or a sample is never confirmed so.
        for prefix in ("Patient ", "MRN_", "Sample ", "Chart"):
            header = ["Study ID"] + [f"{prefix}{3700000 + k}" for k in range(4)]
            raw = write_csv(self.tmp / "people.csv", header, [[f"S{i}"] + ["1.5"] * 4 for i in range(10)])
            p = run("plan", str(raw), "--keep-name", "#2-#5")
            self.assertEqual(p.returncode, 2, prefix)
            self.assertNotIn("3700000", p.stdout + p.stderr)

    # Low: --keep was accepted for a column named Pa holding names.
    def test_keep_is_refused_for_pa_of_names(self):
        names = ["Quillmont Ana", "Okerbrae Joao", "Varnstead Lia"] * 8
        results = keep_probe(self.tmp, [("Pa", names), ("Pa", [str(100 + i) for i in range(24)])])
        self.assertEqual([outcome for _, outcome, _ in results], ["refused", "kept"])

    # Column names fail closed by token: a number is shown only where it is allowed (an ordinal under 100 after a
    # word, a range or a scale, an amount before a unit, a threshold after a comparator, a recent year).
    def test_column_names_fail_closed_by_token(self):
        words = ["Visit", "Glucose", "Col", "Week", "Patient", "Score", "Lab", "Sample", "Item", "Gene"]
        hidden = []
        for w in words:
            for n in ("100", "123", "999", "4527", "8841", "0042", "007", "07", "1.234", "12.345"):
                hidden += [f"{w} {n}", f"{w}_{n}", f"{w}{n}"]
            hidden += [f"{w} {a} {b}" for a, b in ((3, 4), (2, 5), (1, 12), (6, 7))]
            hidden += [f"{w} 1 2 3", f"{w} 2019 3", f"{w} 3 2019", f"{w}_4_2020", f"{w} 1.2.3"]
        judged = self.judge(hidden)
        self.assertEqual([h for h, r in judged.items() if r == "shown"], [], "a number shown where it is not allowed")
        shown = []
        for w in words:
            shown += [f"{w} {k}" for k in (1, 2, 7, 12, 24, 52, 99)] + [f"{w}{k}" for k in (1, 3, 12)]
            shown += [f"{w} 13-17", f"{w} 0-1", f"{w} 2021", f"{w} (mg)", f"{w} 2.5 mg", f"{w} < 13.5", f"{w} 24h"]
        judged = self.judge(shown)
        self.assertEqual({h: r for h, r in judged.items() if r != "shown"}, {}, "an allowed number was hidden")

    # The regression table of round 9: an ordinary invented 30-column clinical table whose column names are written
    # with underscores, camel case and numbers. A default run keeps the columns it can verify, redacts the text and
    # the numbers it cannot, shows every column name, and completes with exit 0 once the person keeps the columns they
    # confirm; an ordinary long-format lab table completes once the person keeps Value (and Lab).
    def test_ordinary_clinical_table_regression_after_round_nine(self):
        import random
        rng = random.Random(94)
        header = ["Patient_ID", "Age", "Sex", "Race", "State", "Country", "Diagnosis", "ICD10_Code", "Drug", "Dose_mg",
                  "Site", "Arm", "Visit", "Visit_Date", "Glucose_mg_dL", "HbA1c_pct", "WBC", "Platelets", "PainScore",
                  "ECOG", "Stage", "Gene", "Ensembl_ID", "Week_12_Score", "Cycle1_Day1_Hb", "BMI", "Steps",
                  "Total_Cost", "HeartRate", "Notes"]
        dx = [("Type 2 diabetes", "E11.9"), ("Hypertension", "I10"), ("Asthma", "J45.909"), ("Heart failure", "I50.9")]
        genes = [("TP53", "ENSG00000141510"), ("EGFR", "ENSG00000146648"), ("KRAS", "ENSG00000133703")]
        pids = [str(4600000 + 37 * k) for k in range(40)]
        rows = []
        for i in range(160):
            d, code = dx[i % 4]
            g, ens = genes[i % 3]
            rows.append([pids[i % 40], str(25 + (i * 7) % 60), "F" if i % 2 else "M",
                         ["White", "Asian", "Black or African American"][i % 3], ["CA", "NY", "TX"][i % 3],
                         ["United States", "Canada"][i % 2], d, code, ["Metformin", "Lisinopril"][i % 2],
                         str([500, 1000, 10][i % 3]), ["Lung", "Breast", "Colon"][i % 3], ["Placebo", "Active"][i % 2],
                         ["Baseline", "Week 4", "Week 12"][i % 3], f"2021-{1 + i % 12:02d}-{1 + i % 28:02d}",
                         str(rng.randint(70, 250)), f"{rng.uniform(5, 11):.1f}", f"{rng.uniform(3, 12):.1f}",
                         str(rng.randint(150000, 450000)), str(i % 11), str(i % 3),
                         ["Stage I", "Stage II", "Stage IV"][i % 3], g, ens, str(i % 10), f"{rng.uniform(10, 16):.1f}",
                         f"{rng.uniform(18, 35):.1f}", str(rng.randint(2000, 15000)), f"{rng.uniform(100, 20000):.2f}",
                         str(rng.randint(55, 120)), "Follow-up in clinic as planned, tolerating treatment well today."])
        raw = write_csv(self.tmp / "clinical30_r9.csv", header, rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(output_names(report, header), {h: h for h in header})
        actions = {d["column"]: d["action"] for d in report["decisions"]}
        kept = {"Sex", "Race", "State", "Country", "ICD10_Code", "Dose_mg", "Glucose_mg_dL", "HbA1c_pct", "WBC",
                "Platelets", "PainScore", "ECOG", "Stage", "Ensembl_ID", "Week_12_Score", "Cycle1_Day1_Hb", "BMI",
                "Steps", "Total_Cost", "HeartRate"}
        unverified = {"Diagnosis", "Drug", "Site", "Arm", "Visit", "Gene"}
        self.assertEqual({c for c, a in actions.items() if a == "keep"}, kept)
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, unverified)
        self.assertEqual((actions["Patient_ID"], actions["Visit_Date"], actions["Notes"]),
                         ("pseudonym_id", "year", "redact"))
        p, out, report = self.run_file(raw, *[a for c in sorted(unverified) for a in ("--keep", c)])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for i, col in enumerate(header):
            if col in kept | unverified:
                self.assertEqual([r[col] for r in out], [row[i] for row in rows], col)
        for pid in pids:
            self.assertNotIn(pid, json.dumps(out))
        # The long-format lab table: Value names no measurement, so it waits for the person's word.
        labs = [("WBC", "4.5-11.0", "10^3/uL", "6.2"), ("Glucose", "70-99", "mg/dL", "104"), ("Sodium", "", "mmol/L", "139")]
        long_rows = [[pids[i % 40], labs[i % 3][0], labs[i % 3][3], labs[i % 3][2]] for i in range(90)]
        raw = write_csv(self.tmp / "labs_long.csv", ["Patient ID", "Lab", "Value", "Unit"], long_rows)
        p, out, report = self.run_file(raw)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual({d["column"] for d in report["columns_needing_decision"]}, {"Lab", "Value"})
        p, out, report = self.run_file(raw, "--keep", "Value", "--keep", "Lab")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([r["Value"] for r in out], [row[2] for row in long_rows])
        self.assertEqual([r["Unit"] for r in out], [row[3] for row in long_rows])


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
