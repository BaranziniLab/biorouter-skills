#!/usr/bin/env node
// Verifies published release assets against a fresh build of their folders.
//
//   node scripts/verify-release.mjs <id> [<id> ...]
//   node scripts/verify-release.mjs --all
//   node scripts/verify-release.mjs --all --from <dir>   # compare local copies (<dir>/<id>.zip or <id>-<version>.zip)
//   node scripts/verify-release.mjs --all --report       # list differences, exit 0
//
// For every row it downloads https://github.com/BaranziniLab/biorouter-skills/
// releases/download/skill-<id>/<id>.zip and fails when the asset's SHA-256
// differs from scripts/build-zip.mjs's build of the folder, or from the row's
// release.sha256 once that is set. A merged or retired row's asset must be a
// stub: one SKILL.md whose description starts "Moved" or "Retired".

import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './lib/repo.mjs';
import { buildItemZip, diffArchives, sha256 } from './lib/build.mjs';
import { readZip } from './lib/zip.mjs';
import { readSkillText } from './lib/frontmatter.mjs';

const REPO = 'BaranziniLab/biorouter-skills';
const argv = process.argv.slice(2);
let from = null;
let all = false;
let report = false;
const ids = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--from') from = path.resolve(argv[++i]);
  else if (argv[i] === '--all') all = true;
  else if (argv[i] === '--report') report = true;
  else ids.push(argv[i]);
}
const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
const rows = all ? catalog.items : ids.map((id) => catalog.items.find((r) => r.id === id));
if (!rows.length || rows.some((r) => !r)) {
  console.error('usage: node scripts/verify-release.mjs <id>... | --all [--from <dir>] [--report]');
  process.exit(2);
}

async function fetchAsset(row) {
  if (from) {
    for (const name of [`${row.id}.zip`, `${row.id}-${row.version}.zip`]) {
      const p = path.join(from, name);
      if (fs.existsSync(p)) return fs.readFileSync(p);
    }
    return null;
  }
  const url = `https://github.com/${REPO}/releases/download/${row.release.tag}/${row.release.asset}`;
  const res = await fetch(url, { redirect: 'follow' });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return Buffer.from(await res.arrayBuffer());
}

export function stubProblem(buf) {
  const entries = readZip(buf).filter((e) => !e.dir);
  if (entries.length !== 1 || !entries[0].name.endsWith('/SKILL.md')) return `holds ${entries.length} files, a stub holds one SKILL.md`;
  const fm = readSkillText(entries[0].data.toString('utf8')).frontmatter;
  if (!/^(Moved|Retired)/.test(fm.description ?? '')) return `its description does not start with "Moved" or "Retired"`;
  return null;
}

let failed = 0;
for (const row of rows) {
  const built = buildItemZip(REPO_ROOT, row);
  const want = sha256(built);
  let asset;
  try {
    asset = await fetchAsset(row);
  } catch (e) {
    console.log(`FAIL ${row.id}: ${e.message}`);
    failed++;
    continue;
  }
  if (!asset) {
    if (row.release.sha256) {
      console.log(`FAIL ${row.id}: no published asset, but the row records sha256 ${row.release.sha256.slice(0, 12)}`);
      failed++;
    } else console.log(`new  ${row.id}: not released yet`);
    continue;
  }
  const have = sha256(asset);
  const problems = [];
  if (have !== want) {
    const d = diffArchives(asset, built);
    problems.push(`asset ${have.slice(0, 12)} differs from the folder build ${want.slice(0, 12)}${d.length ? ` (${d.length} entr${d.length === 1 ? 'y' : 'ies'}: ${d.slice(0, 3).join('; ')}${d.length > 3 ? '; ...' : ''})` : ' (same contents, different bytes: not built by build-zip.mjs)'}`);
  }
  if (row.release.sha256 && row.release.sha256 !== have) problems.push(`the row records sha256 ${row.release.sha256.slice(0, 12)}, the asset is ${have.slice(0, 12)}`);
  if (row.status !== 'active') {
    const p = stubProblem(asset);
    if (p) problems.push(`is ${row.status} but its asset is not a stub: ${p}`);
  }
  if (problems.length) {
    failed++;
    console.log(`${report ? 'diff' : 'FAIL'} ${row.id} ${row.version}: ${problems.join('; ')}`);
  } else console.log(`ok   ${row.id} ${row.version} ${have.slice(0, 12)}`);
}
console.log(failed ? `${failed} of ${rows.length} differ` : `all ${rows.length} match`);
process.exit(failed && !report ? 1 : 0);
