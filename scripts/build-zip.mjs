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
// The same folder always gives the same bytes, on any machine. A row whose
// provenance folder files are wanted (format 2, not deferred in
// provenance-baseline.json) also gets the repository's LICENSE as <id>/LICENSE.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT } from './lib/repo.mjs';
import { archiveOptions, buildItemZip, sha256 } from './lib/build.mjs';

/** The rows a command line names: every row with --all, else the ids in order (an unknown id throws). */
export function selectRows(catalog, ids, all = false) {
  if (all) return catalog.items;
  return ids.map((id) => catalog.items.find((r) => r.id === id) ?? (() => { throw new Error(`no catalog row ${id}`); })());
}

function main(argv) {
  let out = path.join(REPO_ROOT, 'dist');
  const ids = [];
  let all = false;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') out = path.resolve(argv[++i]);
    else if (argv[i] === '--all') all = true;
    else ids.push(argv[i]);
  }
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const rows = selectRows(catalog, ids, all);
  if (!rows.length) {
    console.error('usage: node scripts/build-zip.mjs <id>... | --all [--out <dir>]');
    return 2;
  }
  fs.mkdirSync(out, { recursive: true });
  for (const row of rows) {
    const buf = buildItemZip(REPO_ROOT, row, archiveOptions(REPO_ROOT, row, catalog));
    const file = path.join(out, `${row.id}.zip`);
    fs.writeFileSync(file, buf);
    console.log(`${sha256(buf)}  ${path.relative(process.cwd(), file)}  ${row.version}  ${buf.length} bytes`);
  }
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main(process.argv.slice(2));
