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
// stub: one SKILL.md whose description starts "Moved" or "Retired". A row whose
// provenance folder files are wanted (format 2, not deferred) must also carry
// <id>/LICENSE, the repository's licence, and an active one <id>/PROVENANCE.md.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT } from './lib/repo.mjs';
import { ARCHIVE_LICENCE, archiveOptions, buildItemZip, diffArchives, sha256 } from './lib/build.mjs';
import { readZip } from './lib/zip.mjs';
import { readSkillText } from './lib/frontmatter.mjs';
import { PROVENANCE_FILE } from './lib/provenance-md.mjs';

const REPO = 'BaranziniLab/biorouter-skills';

/**
 * Why an asset is not a stub, or null. A stub holds one SKILL.md whose
 * description starts "Moved" or "Retired"; with `licence` (the row wants its
 * provenance folder files) it may also hold the archive's <id>/LICENSE, whose
 * absence missingProvenanceFiles() names.
 */
export function stubProblem(buf, { licence = false } = {}) {
  const entries = readZip(buf).filter((e) => !e.dir);
  const isLicence = (e) => licence && new RegExp(`^[^/]+/${ARCHIVE_LICENCE}$`).test(e.name);
  const rest = entries.filter((e) => !isLicence(e));
  const shape = licence ? `one SKILL.md and the ${ARCHIVE_LICENCE}` : 'one SKILL.md';
  if (rest.length !== 1 || entries.length - rest.length > 1 || !rest[0].name.endsWith('/SKILL.md')) return `holds ${entries.length} files, a stub holds ${shape}`;
  const fm = readSkillText(rest[0].data.toString('utf8')).frontmatter;
  if (!/^(Moved|Retired)/.test(fm.description ?? '')) return `its description does not start with "Moved" or "Retired"`;
  return null;
}

/** The provenance files a wanted row's asset lacks: <id>/LICENSE, and <id>/PROVENANCE.md when the row is active. */
export function missingProvenanceFiles(buf, row, { addLicence = false } = {}) {
  if (!addLicence) return [];
  const have = new Set(readZip(buf).filter((e) => !e.dir).map((e) => e.name));
  const want = [`${row.id}/${ARCHIVE_LICENCE}`];
  if (row.status === 'active') want.push(`${row.id}/${PROVENANCE_FILE}`);
  return want.filter((n) => !have.has(n));
}

/** Every problem of one published asset against a fresh build of the row's folder (an empty list when it matches). */
export function assetProblems(root, row, catalog, asset) {
  const opts = archiveOptions(root, row, catalog);
  const built = buildItemZip(root, row, opts);
  const want = sha256(built);
  const have = sha256(asset);
  const problems = [];
  if (have !== want) {
    const d = diffArchives(asset, built);
    problems.push(`asset ${have.slice(0, 12)} differs from the folder build ${want.slice(0, 12)}${d.length ? ` (${d.length} entr${d.length === 1 ? 'y' : 'ies'}: ${d.slice(0, 3).join('; ')}${d.length > 3 ? '; ...' : ''})` : ' (same contents, different bytes: not built by build-zip.mjs)'}`);
  }
  if (row.release?.sha256 && row.release.sha256 !== have) problems.push(`the row records sha256 ${row.release.sha256.slice(0, 12)}, the asset is ${have.slice(0, 12)}`);
  for (const name of missingProvenanceFiles(asset, row, opts)) problems.push(`lacks ${name}`);
  if (row.status !== 'active') {
    const p = stubProblem(asset, { licence: opts.addLicence });
    if (p) problems.push(`is ${row.status} but its asset is not a stub: ${p}`);
  }
  return problems;
}

function parseArgs(argv) {
  const args = { from: null, all: false, report: false, ids: [] };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--from') args.from = path.resolve(argv[++i]);
    else if (argv[i] === '--all') args.all = true;
    else if (argv[i] === '--report') args.report = true;
    else args.ids.push(argv[i]);
  }
  return args;
}

async function fetchAsset(row, from) {
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

async function main(argv) {
  const { from, all, report, ids } = parseArgs(argv);
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const rows = all ? catalog.items : ids.map((id) => catalog.items.find((r) => r.id === id));
  if (!rows.length || rows.some((r) => !r)) {
    console.error('usage: node scripts/verify-release.mjs <id>... | --all [--from <dir>] [--report]');
    return 2;
  }
  let failed = 0;
  for (const row of rows) {
    let asset;
    try {
      asset = await fetchAsset(row, from);
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
    const problems = assetProblems(REPO_ROOT, row, catalog, asset);
    if (problems.length) {
      failed++;
      console.log(`${report ? 'diff' : 'FAIL'} ${row.id} ${row.version}: ${problems.join('; ')}`);
    } else console.log(`ok   ${row.id} ${row.version} ${sha256(asset).slice(0, 12)}`);
  }
  console.log(failed ? `${failed} of ${rows.length} differ` : `all ${rows.length} match`);
  return failed && !report ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then((code) => process.exit(code), (e) => {
    console.error(e.stack || e.message);
    process.exit(2);
  });
}
