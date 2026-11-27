#!/usr/bin/env node
// Writes the redirect stub of every merged or retired row into its folder.
//
//   node scripts/write-stubs.mjs           # replace each such folder's contents with its stub
//   node scripts/write-stubs.mjs --check   # fail when a folder differs from its stub
//   node scripts/write-stubs.mjs --root <dir>   # another checkout (the tests use a throwaway one)
//
// The stub text comes from scripts/lib/stub.mjs, so it always matches the row.
// A format 2 row whose folder files are wanted now (folderProvenanceWanted:
// no PV9 deferral in provenance-baseline.json) gets the stub with its credit
// lines; a deferred row keeps the stub it has until its next release.

import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './lib/repo.mjs';
import { stubFiles } from './lib/stub.mjs';
import { folderProvenanceWanted } from './lib/catalog-rules.mjs';
import { readProvenanceBaseline } from './lib/provenance-baseline.mjs';
import { checkRowFolder } from './check-catalog.mjs';

const argv = process.argv.slice(2);
const check = argv.includes('--check');
const at = argv.indexOf('--root');
const root = at === -1 ? REPO_ROOT : path.resolve(argv[at + 1]);
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'catalog.json'), 'utf8'));
const baseline = readProvenanceBaseline(root);
let bad = 0;
for (const row of catalog.items.filter((r) => r.status !== 'active')) {
  const dir = path.join(root, row.path);
  if (check) {
    const problems = checkRowFolder(root, row, catalog).filter((f) => f.rule === 'stub' || f.rule === 'folder');
    for (const p of problems) console.error(p.message);
    bad += problems.length;
    continue;
  }
  const provenance = folderProvenanceWanted(row, { catalogFormat: catalog.format, baseline });
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  for (const [name, text] of Object.entries(stubFiles(row, catalog, { provenance }))) fs.writeFileSync(path.join(dir, name), text);
  console.log(`stub ${row.path} (${row.status})`);
}
if (check) {
  console.log(bad ? `${bad} stub problem(s)` : 'every merged or retired folder holds its stub');
  process.exit(bad ? 1 : 0);
}
