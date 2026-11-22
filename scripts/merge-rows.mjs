#!/usr/bin/env node
// Merges finished catalog rows from a work package into catalog.json.
//
//   node scripts/merge-rows.mjs <dir or row.json> [...]     # merge, write catalog.json, run the check
//   node scripts/merge-rows.mjs --dry-run <dir> [...]        # report what would change
//
// A content work package writes one row per item it finished, as
// <WP-id>/catalog-rows/<id>.json, after its folders are on this branch. For an
// existing id the incoming fields win and the fields a package does not know
// about are kept (summary, keywords, invocation); aliases and distinct_from are
// united; history keeps every earlier version; release keeps its tag and asset,
// and its sha256 is cleared when the version changes (the release sets it). A
// component entry without a `name` takes the name from its folder's SKILL.md,
// and keeps the boundaries the catalog already recorded for it. A new id must
// be a complete row. The merged catalog is checked afterwards.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT, readSkillFile } from './lib/repo.mjs';
import { checkRowShape, runCheck } from './check-catalog.mjs';

function union(a = [], b = [], key = (x) => x) {
  const out = new Map();
  for (const x of [...a, ...b]) out.set(key(x), x);
  return [...out.values()];
}

export function mergeRow(existing, incoming, root = REPO_ROOT) {
  const base = existing ?? {
    summary: '',
    keywords: [],
    invocation: incoming.kind === 'bundle' ? 'bundle' : 'auto',
    aliases: [],
    distinct_from: [],
    notice_file: null,
    components: null,
    release: { tag: `skill-${incoming.id}`, asset: `${incoming.id}.zip`, sha256: null },
  };
  const merged = { ...base, ...incoming };
  merged.aliases = union(base.aliases, incoming.aliases);
  merged.distinct_from = union(base.distinct_from, incoming.distinct_from, (d) => d.id);
  merged.history = union(base.history ?? [], incoming.history ?? [], (h) => h.version).sort((x, y) => {
    const a = x.version.split('.').map(Number);
    const b = y.version.split('.').map(Number);
    return a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
  });
  merged.release = { ...base.release, ...(incoming.release ?? {}) };
  merged.release.tag = `skill-${merged.id}`;
  merged.release.asset = `${merged.id}.zip`;
  if (existing && existing.version !== merged.version) merged.release.sha256 = incoming.release?.sha256 ?? null;
  if (merged.kind === 'bundle' && merged.components) {
    const out = {};
    for (const [folder, entry] of Object.entries(merged.components)) {
      const old = base.components?.[folder] ?? {};
      const e = { ...entry };
      if (!e.name) {
        const sk = readSkillFile(path.join(root, merged.path, folder, 'SKILL.md'));
        e.name = sk.frontmatter?.name ?? old.name ?? folder;
      }
      const boundaries = union(old.distinct_from ?? [], e.distinct_from ?? [], (d) => d.id);
      if (boundaries.length) e.distinct_from = boundaries;
      out[folder] = e;
    }
    merged.components = out;
  }
  return merged;
}

function rowFiles(args) {
  const files = [];
  for (const a of args) {
    const p = path.resolve(a);
    if (fs.statSync(p).isDirectory()) {
      for (const n of fs.readdirSync(p).sort()) if (n.endsWith('.json')) files.push(path.join(p, n));
    } else {
      files.push(p);
    }
  }
  return files;
}

function main() {
  const argv = process.argv.slice(2);
  const dry = argv.includes('--dry-run');
  const files = rowFiles(argv.filter((a) => a !== '--dry-run'));
  if (!files.length) {
    console.error('usage: node scripts/merge-rows.mjs [--dry-run] <dir or row.json>...');
    process.exit(2);
  }
  const catalogPath = path.join(REPO_ROOT, 'catalog.json');
  const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
  const byId = new Map(catalog.items.map((r, i) => [r.id, i]));
  let updated = 0;
  let added = 0;
  for (const f of files) {
    const incoming = JSON.parse(fs.readFileSync(f, 'utf8'));
    const i = byId.get(incoming.id);
    const merged = mergeRow(i === undefined ? null : catalog.items[i], incoming);
    const shape = checkRowShape(merged);
    if (shape.length) for (const s of shape) console.log(`warn  ${path.basename(f)}: ${s.message}`);
    if (i === undefined) {
      catalog.items.push(merged);
      byId.set(merged.id, catalog.items.length - 1);
      added++;
      console.log(`add   ${merged.id} ${merged.version}`);
    } else {
      const before = catalog.items[i];
      catalog.items[i] = merged;
      updated++;
      console.log(`merge ${merged.id} ${before.version} -> ${merged.version}${before.status !== merged.status ? ` (${before.status} -> ${merged.status})` : ''}`);
    }
  }
  if (dry) {
    console.log(`dry run: ${updated} updated, ${added} added; catalog.json unchanged`);
    return;
  }
  fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
  const builtins = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'builtin-skill-names.json'), 'utf8'));
  const res = runCheck({ root: REPO_ROOT, catalog, builtins });
  for (const e of res.errors) console.log(`FAIL [${e.rule}] ${e.message}`);
  console.log(`${updated} updated, ${added} added; the check reports ${res.errors.length} failure(s)`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
