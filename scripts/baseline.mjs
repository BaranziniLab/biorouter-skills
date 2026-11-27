#!/usr/bin/env node
// Maintains the two baselines of the check: catalog.json's baseline_violations
// (the duplicate, gap, row and folder rules) and provenance-baseline.json (the
// provenance rules PV1 to PV13, kept beside catalog.json because the catalog is
// mirrored into landing, which must not see them).
//
//   node scripts/baseline.mjs prune                          # drop entries that no longer fail, in both files
//   node scripts/baseline.mjs accept --wp <WP> [--rule <rule>] [--except <subject>]...
//                                                            # record the current failures as owned by <WP>
//   node scripts/baseline.mjs done <WP>                      # mark a work package done (its entries must be gone)
//   node scripts/baseline.mjs init-provenance                # write provenance-baseline.json's frozen rows
//
// `accept` is for a failure a later work package removes (for example a
// redirect to a skill that package adds); every entry names that package, and
// the check refuses the entry once the package is marked done. A provenance
// work package (PROV-S1, PROV-S4) takes the PV failures, with the date they
// were accepted, into provenance-baseline.json; any other package takes the
// other failures into catalog.json. A PV failure of a row added after the
// provenance rules landed is never accepted: such a row passes every rule.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { subjectId } from './lib/catalog-rules.mjs';
import {
  PROVENANCE_BASELINE_FILE,
  PROVENANCE_BASELINE_ROWS,
  PROVENANCE_BASELINE_ROWS_SHA256,
  PROVENANCE_BASELINE_SINCE,
  PROVENANCE_WORK_PACKAGES,
  emptyProvenanceBaseline,
  readProvenanceBaseline,
} from './lib/provenance-baseline.mjs';
import { REPO_ROOT } from './lib/repo.mjs';
import { PROVENANCE_BASELINE_RULE, PROVENANCE_RULE, provenanceRowsDigest, runCheck } from './check-catalog.mjs';

export const PROVENANCE_BASELINE_DESCRIPTION =
  'Baseline of the provenance rules PV1 to PV13 (see README, The catalog). Kept beside catalog.json because the catalog is mirrored into landing.';

const FROZEN = { count: PROVENANCE_BASELINE_ROWS, sha256: PROVENANCE_BASELINE_ROWS_SHA256 };
const SKIP = new Set(['baseline', 'provenance-baseline']);
const isPv = (rule) => PROVENANCE_RULE.test(String(rule ?? ''));

/** The date an accepted provenance entry carries: today, never before the rules landed. */
export function acceptSince(today = new Date().toISOString().slice(0, 10)) {
  return today > PROVENANCE_BASELINE_SINCE ? today : PROVENANCE_BASELINE_SINCE;
}

/**
 * Which current failures `accept --wp <wp>` records, and where. A provenance
 * work package takes PV failures only, a catalog work package everything
 * else. Returns { catalogEntries, provenanceEntries, refused }; a refused PV
 * failure (a row outside the frozen rows, or a PV9 or PV10 entry for a package
 * other than PROV-S4) means nothing should be written.
 */
export function planAccept(errors, { wp, rule = null, except = [], since = acceptSince(), rows = [] } = {}) {
  if (!wp) throw new Error('accept needs --wp <work package>');
  const provenanceWp = String(wp).startsWith('PROV-');
  if (provenanceWp && !Object.hasOwn(PROVENANCE_WORK_PACKAGES, wp)) throw new Error(`${wp} is not a provenance work package; use PROV-S1 or PROV-S4`);
  if (!provenanceWp && rule && isPv(rule)) throw new Error(`${rule} entries belong to a provenance work package, PROV-S1 or PROV-S4`);
  const skip = new Set(except);
  const known = new Set(rows);
  const take = errors.filter((e) => !SKIP.has(e.rule) && (!rule || e.rule === rule) && !skip.has(e.subject) && isPv(e.rule) === provenanceWp);
  const catalogEntries = [];
  const provenanceEntries = [];
  const refused = [];
  for (const e of take) {
    if (!provenanceWp) {
      catalogEntries.push({ rule: e.rule, subject: e.subject, wp, note: e.message });
      continue;
    }
    const id = subjectId(e.subject);
    if (!PROVENANCE_BASELINE_RULE.test(e.rule)) refused.push({ ...e, reason: `${e.rule} is not one of PV1 to PV13` });
    else if (!id || !known.has(id)) refused.push({ ...e, reason: `${id ?? 'its row'} was added after the provenance rules landed, so it must pass every provenance rule` });
    else if ((e.rule === 'PV9' || e.rule === 'PV10') && wp !== 'PROV-S4') refused.push({ ...e, reason: `${e.rule} entries belong to PROV-S4` });
    else provenanceEntries.push({ rule: e.rule, subject: e.subject, wp, since, note: e.message });
  }
  return { catalogEntries, provenanceEntries, refused };
}

/**
 * provenance-baseline.json with `rows` written from the catalog, which must
 * hold exactly the rows frozen when the provenance rules landed. Keeps the
 * existing entries and done list.
 */
export function initProvenance(catalog, existing = null, frozen = FROZEN) {
  const ids = (catalog?.items ?? []).map((r) => r.id).sort();
  if (ids.length !== frozen.count || provenanceRowsDigest(ids) !== frozen.sha256) {
    throw new Error(`catalog.json holds ${ids.length} rows that are not the ${frozen.count} rows frozen when the provenance rules landed; rows is written once, from that catalog, and never grows`);
  }
  const base = { ...emptyProvenanceBaseline(), ...(existing ?? {}) };
  return {
    format: base.format ?? 1,
    description: base.description || PROVENANCE_BASELINE_DESCRIPTION,
    since: base.since || PROVENANCE_BASELINE_SINCE,
    rows: ids,
    done_work_packages: base.done_work_packages ?? [],
    baseline_violations: base.baseline_violations ?? [],
  };
}

/** Removes the stale entries `errors` names from both baselines. Returns how many went from each. */
export function pruneBaselines(errors, catalog, provenance) {
  const stale = new Set(errors.filter((e) => e.rule === 'baseline').map((e) => e.subject));
  const key = (b) => `${b.rule}::${b.subject}`;
  const before = { catalog: (catalog.baseline_violations ?? []).length, provenance: (provenance.baseline_violations ?? []).length };
  catalog.baseline_violations = (catalog.baseline_violations ?? []).filter((b) => b.cross_kind || !stale.has(key(b)));
  provenance.baseline_violations = (provenance.baseline_violations ?? []).filter((b) => !stale.has(key(b)));
  return { catalog: before.catalog - catalog.baseline_violations.length, provenance: before.provenance - provenance.baseline_violations.length };
}

/** Marks a work package done in the file that owns it; throws while either file still lists it. */
export function markDone(wp, catalog, provenance) {
  const left = [...(catalog.baseline_violations ?? []), ...(provenance.baseline_violations ?? [])].filter((b) => b.wp === wp);
  if (left.length) throw new Error(`${wp} still owns ${left.length} baseline entr${left.length === 1 ? 'y' : 'ies'}; it is not done`);
  const target = String(wp).startsWith('PROV-') ? provenance : catalog;
  target.done_work_packages = [...new Set([...(target.done_work_packages ?? []), wp])].sort();
}

function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const arg = (name) => {
    const i = rest.indexOf(name);
    return i === -1 ? null : rest[i + 1];
  };
  const args = (name) => rest.flatMap((a, i) => (a === name && i + 1 < rest.length ? [rest[i + 1]] : []));
  const catalogPath = path.join(REPO_ROOT, 'catalog.json');
  const provenancePath = path.join(REPO_ROOT, PROVENANCE_BASELINE_FILE);
  const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
  const provenance = readProvenanceBaseline(REPO_ROOT);
  const builtins = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'builtin-skill-names.json'), 'utf8'));
  const saveCatalog = () => fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
  const saveProvenance = (p = provenance) => fs.writeFileSync(provenancePath, `${JSON.stringify(p, null, 2)}\n`);
  const check = () => runCheck({ root: REPO_ROOT, catalog, builtins, provenance });

  if (cmd === 'init-provenance') {
    const next = initProvenance(catalog, fs.existsSync(provenancePath) ? provenance : null);
    saveProvenance(next);
    console.log(`${PROVENANCE_BASELINE_FILE}: ${next.rows.length} frozen rows, ${next.baseline_violations.length} entries`);
  } else if (cmd === 'prune') {
    const removed = pruneBaselines(check().errors, catalog, provenance);
    saveCatalog();
    if (fs.existsSync(provenancePath)) saveProvenance();
    console.log(`removed ${removed.catalog} stale catalog.json entries and ${removed.provenance} stale ${PROVENANCE_BASELINE_FILE} entries; ${catalog.baseline_violations.length} and ${provenance.baseline_violations.length} remain`);
  } else if (cmd === 'accept') {
    const wp = arg('--wp');
    const plan = planAccept(check().errors, { wp, rule: arg('--rule'), except: args('--except'), rows: provenance.rows });
    if (plan.refused.length) {
      for (const r of plan.refused) console.error(`refused ${r.rule} ${r.subject}: ${r.reason}`);
      console.error(`nothing recorded: ${plan.refused.length} failure(s) may not be baselined (pass --except <subject> to leave one out)`);
      process.exit(1);
    }
    if (plan.catalogEntries.length) {
      catalog.baseline_violations = [...(catalog.baseline_violations ?? []), ...plan.catalogEntries];
      saveCatalog();
    }
    if (plan.provenanceEntries.length) {
      if (!provenance.rows.length) throw new Error(`${PROVENANCE_BASELINE_FILE} has no rows yet; run node scripts/baseline.mjs init-provenance first`);
      provenance.baseline_violations = [...provenance.baseline_violations, ...plan.provenanceEntries];
      saveProvenance();
    }
    const n = plan.catalogEntries.length + plan.provenanceEntries.length;
    console.log(`recorded ${n} failure(s) as owned by ${wp}${plan.provenanceEntries.length ? ` in ${PROVENANCE_BASELINE_FILE}` : ''}`);
  } else if (cmd === 'done') {
    const wp = rest[0];
    try {
      markDone(wp, catalog, provenance);
    } catch (e) {
      console.error(e.message);
      process.exit(1);
    }
    if (String(wp).startsWith('PROV-')) saveProvenance();
    else saveCatalog();
    console.log(`${wp} marked done`);
  } else {
    console.error('usage: node scripts/baseline.mjs prune | accept --wp <WP> [--rule <rule>] [--except <subject>]... | done <WP> | init-provenance');
    process.exit(2);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}
