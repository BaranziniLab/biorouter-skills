#!/usr/bin/env node
// Writes the redirect stub of every merged or retired row into its folder.
//
//   node scripts/write-stubs.mjs           # replace each such folder's contents with its stub
//   node scripts/write-stubs.mjs --check   # fail when a folder differs from its stub
//
// The stub text comes from scripts/lib/stub.mjs, so it always matches the row.

import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './lib/repo.mjs';
import { stubFiles } from './lib/stub.mjs';
import { checkRowFolder } from './check-catalog.mjs';

const check = process.argv.includes('--check');
const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
let bad = 0;
for (const row of catalog.items.filter((r) => r.status !== 'active')) {
  const dir = path.join(REPO_ROOT, row.path);
  if (check) {
    const problems = checkRowFolder(REPO_ROOT, row, catalog).filter((f) => f.rule === 'stub' || f.rule === 'folder');
    for (const p of problems) console.error(p.message);
    bad += problems.length;
    continue;
  }
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  for (const [name, text] of Object.entries(stubFiles(row, catalog))) fs.writeFileSync(path.join(dir, name), text);
  console.log(`stub ${row.path} (${row.status})`);
}
if (check) {
  console.log(bad ? `${bad} stub problem(s)` : 'every merged or retired folder holds its stub');
  process.exit(bad ? 1 : 0);
}
