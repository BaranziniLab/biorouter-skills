#!/usr/bin/env node
// Builds release archives, deterministically, from the catalog's folders.
//
//   node scripts/build-zip.mjs <id> [<id> ...]   # writes dist/<id>.zip and prints its SHA-256
//   node scripts/build-zip.mjs --all             # every row, active and stub
//   node scripts/build-zip.mjs --out <dir> <id>  # somewhere other than dist/
//
// The archive holds the item's folder under a root folder named by its id
// (bio bundles come from bio-skills/<id>/), entries sorted, every timestamp
// 1980-01-01, stored without compression, .DS_Store and other junk left out.
// The same folder always gives the same bytes, on any machine.

import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './lib/repo.mjs';
import { buildItemZip, sha256 } from './lib/build.mjs';

const argv = process.argv.slice(2);
let out = path.join(REPO_ROOT, 'dist');
const ids = [];
let all = false;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--out') out = path.resolve(argv[++i]);
  else if (argv[i] === '--all') all = true;
  else ids.push(argv[i]);
}
const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
const rows = all ? catalog.items : ids.map((id) => catalog.items.find((r) => r.id === id) ?? (() => { throw new Error(`no catalog row ${id}`); })());
if (!rows.length) {
  console.error('usage: node scripts/build-zip.mjs <id>... | --all [--out <dir>]');
  process.exit(2);
}
fs.mkdirSync(out, { recursive: true });
for (const row of rows) {
  const buf = buildItemZip(REPO_ROOT, row);
  const file = path.join(out, `${row.id}.zip`);
  fs.writeFileSync(file, buf);
  console.log(`${sha256(buf)}  ${path.relative(process.cwd(), file)}  ${row.version}  ${buf.length} bytes`);
}
