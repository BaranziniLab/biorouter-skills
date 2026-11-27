// Reads provenance-baseline.json, the baseline of the provenance rules (PV1 to PV13).
//
// The provenance baseline lives beside catalog.json, not inside it, because
// catalog.json is mirrored byte for byte into the Biorouter repository
// (landing/catalog/skills.json), whose check applies the mirror's
// baseline_violations to its own failures and whose test requires that list
// to be empty. The entries have the catalog's baseline shape
// ({ rule, subject, wp, since, note }) and go through the same applyBaseline.
//
// `rows` freezes the ids that existed when the provenance rules landed
// (2026-11-27). Only those rows may be baselined: a new row is written in
// format 2 and passes every provenance rule from its first commit.
//
// Owned by lane checks after step 1's design; the generators and the archive
// builder only read it, through readProvenanceBaseline() here and
// folderProvenanceWanted() in catalog-rules.mjs.

import fs from 'node:fs';
import path from 'node:path';

export const PROVENANCE_BASELINE_FILE = 'provenance-baseline.json';

/** The date the provenance rules landed; every baseline entry is dated on or after it. */
export const PROVENANCE_BASELINE_SINCE = '2026-11-27';

/**
 * The frozen `rows`: the 145 ids of catalog.json at biorouter-skills 2b542a8,
 * sorted and joined with "\n", hashed with SHA-256. A `rows` list that does
 * not hash to this value is refused, so no row added later can be baselined.
 */
export const PROVENANCE_BASELINE_ROWS = 145;
export const PROVENANCE_BASELINE_ROWS_SHA256 = '9ada921ab5778cc177b60ec93553a148107900acf84d2ad3ea6fc8b89762b98a';

/** The work packages that own provenance baseline entries, by audit step. */
export const PROVENANCE_WORK_PACKAGES = Object.freeze({
  'PROV-S1': 'Step 1 migration: the row is rewritten in format 2 after the owner signs off the step 0 table.',
  'PROV-S4': "Step 4: the item's generated folder files (PROVENANCE.md, the front matter credits, the stub's credit, the archive's LICENSE) arrive at its next release (owner answer Q5).",
});

export function emptyProvenanceBaseline() {
  return { format: 1, description: '', since: PROVENANCE_BASELINE_SINCE, rows: [], done_work_packages: [], baseline_violations: [] };
}

/** The parsed provenance baseline of a checkout, or an empty one when the file is absent. */
export function readProvenanceBaseline(root) {
  const p = path.join(root, PROVENANCE_BASELINE_FILE);
  if (!fs.existsSync(p)) return emptyProvenanceBaseline();
  return { ...emptyProvenanceBaseline(), ...JSON.parse(fs.readFileSync(p, 'utf8')) };
}
