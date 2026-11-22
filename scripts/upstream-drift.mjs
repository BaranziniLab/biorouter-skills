#!/usr/bin/env node
// Reports upstreams whose head moved since the commit a skill was taken from.
//
//   node scripts/upstream-drift.mjs            # table on stdout; never fails
//   node scripts/upstream-drift.mjs --json
//
// Uses `gh api repos/<repo>/compare/<commit>...HEAD`, so it needs the GitHub
// CLI and a token (GH_TOKEN in CI). Rows with source.maintained_here (an
// archived upstream maintained in this repository) are skipped. When an
// upstream path is recorded, only commits touching files under it count.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT } from './lib/repo.mjs';

const json = process.argv.includes('--json');
const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
const cache = new Map();

function compare(repo, commit) {
  const key = `${repo}@${commit}`;
  if (cache.has(key)) return cache.get(key);
  let value;
  try {
    const out = execFileSync('gh', ['api', `repos/${repo}/compare/${commit}...HEAD`, '--jq', '{ahead: .ahead_by, status: .status, files: [.files[]?.filename]}'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    value = JSON.parse(out);
  } catch (e) {
    value = { error: String(e.stderr || e.message).trim().split('\n')[0] };
  }
  cache.set(key, value);
  return value;
}

const rows = [];
for (const r of catalog.items.filter((x) => x.status === 'active' && !x.source?.maintained_here)) {
  for (const u of r.source?.upstreams ?? []) {
    if (!u.commit) continue;
    const c = compare(u.repo, u.commit);
    if (c.error) {
      rows.push({ id: r.id, repo: u.repo, commit: u.commit, state: 'error', detail: c.error });
      continue;
    }
    const touched = u.path ? c.files.filter((f) => f === u.path || f.startsWith(`${u.path.replace(/\/$/, '')}/`)) : c.files;
    rows.push({ id: r.id, repo: u.repo, commit: u.commit.slice(0, 7), state: c.ahead === 0 ? 'current' : touched.length ? 'moved' : 'unrelated-changes', ahead: c.ahead, files: touched.length });
  }
}
if (json) console.log(JSON.stringify(rows, null, 2));
else {
  for (const x of rows) console.log(`${x.state.padEnd(17)} ${x.id.padEnd(36)} ${x.repo}@${x.commit}${x.ahead != null ? ` ahead ${x.ahead}, ${x.files} file(s) under the path` : ` ${x.detail}`}`);
  const moved = rows.filter((x) => x.state === 'moved').length;
  console.log(`${rows.length} upstream pins; ${moved} moved under their path`);
}
