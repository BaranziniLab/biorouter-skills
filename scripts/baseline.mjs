#!/usr/bin/env node
// Maintains catalog.json's baseline_violations.
//
//   node scripts/baseline.mjs prune                         # drop entries that no longer fail
//   node scripts/baseline.mjs accept --wp <WP> [--rule D4]  # record the current failures as owned by <WP>
//   node scripts/baseline.mjs done <WP>                     # mark a work package done (its entries must be gone)
//
// `accept` is for a failure a later work package removes (for example a
// redirect to a skill that package adds); every entry names that package, and
// the check refuses the entry once the package is marked done.

import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './lib/repo.mjs';
import { runCheck } from './check-catalog.mjs';

const [cmd, ...rest] = process.argv.slice(2);
const arg = (name) => {
  const i = rest.indexOf(name);
  return i === -1 ? null : rest[i + 1];
};
const catalogPath = path.join(REPO_ROOT, 'catalog.json');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
const builtins = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'builtin-skill-names.json'), 'utf8'));
const save = () => fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
const res = runCheck({ root: REPO_ROOT, catalog, builtins });

if (cmd === 'prune') {
  const stale = new Set(res.errors.filter((e) => e.rule === 'baseline').map((e) => e.subject));
  const before = catalog.baseline_violations.length;
  catalog.baseline_violations = catalog.baseline_violations.filter((b) => b.cross_kind || !stale.has(`${b.rule}::${b.subject}`));
  save();
  console.log(`removed ${before - catalog.baseline_violations.length} stale entries; ${catalog.baseline_violations.length} remain`);
} else if (cmd === 'accept') {
  const wp = arg('--wp');
  const rule = arg('--rule');
  if (!wp) throw new Error('accept needs --wp <work package>');
  const add = res.errors.filter((e) => e.rule !== 'baseline' && (!rule || e.rule === rule));
  for (const e of add) catalog.baseline_violations.push({ rule: e.rule, subject: e.subject, wp, note: e.message });
  save();
  console.log(`recorded ${add.length} failure(s) as owned by ${wp}`);
} else if (cmd === 'done') {
  const wp = rest[0];
  const left = catalog.baseline_violations.filter((b) => b.wp === wp);
  if (left.length) {
    console.error(`${wp} still owns ${left.length} baseline entr${left.length === 1 ? 'y' : 'ies'}; it is not done`);
    process.exit(1);
  }
  catalog.done_work_packages = [...new Set([...(catalog.done_work_packages ?? []), wp])].sort();
  save();
  console.log(`${wp} marked done`);
} else {
  console.error('usage: node scripts/baseline.mjs prune | accept --wp <WP> [--rule <rule>] | done <WP>');
  process.exit(2);
}
