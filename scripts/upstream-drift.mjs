#!/usr/bin/env node
// Reports upstreams whose head moved since the commit a skill was taken from.
//
//   node scripts/upstream-drift.mjs            # table on stdout; never fails
//   node scripts/upstream-drift.mjs --json
//
// Uses `gh api repos/<repo>/compare/<commit>...HEAD`, so it needs the GitHub
// CLI and a token (GH_TOKEN in CI). Rows with source.maintained_here (an
// archived upstream maintained in this repository) are skipped. When an
// upstream path is recorded, only commits touching it count: the newest commit
// on the path is compared with the pin (the compare API's file list stops at
// 300 files, so it cannot answer that question for a busy repository).

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT } from './lib/repo.mjs';

const json = process.argv.includes('--json');
const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
const cache = new Map();

function ghJson(args) {
  const out = execFileSync('gh', ['api', ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  return JSON.parse(out);
}

function compare(repo, commit, upstreamPath) {
  const key = `${repo}@${commit}:${upstreamPath ?? ''}`;
  if (cache.has(key)) return cache.get(key);
  let value;
  try {
    const head = ghJson([`repos/${repo}/compare/${commit}...HEAD`, '--jq', '{ahead: .ahead_by}']);
    if (!upstreamPath || head.ahead === 0) value = { ahead: head.ahead, pathMoved: head.ahead > 0 };
    else {
      const latest = ghJson([`repos/${repo}/commits?path=${encodeURIComponent(upstreamPath)}&per_page=1`, '--jq', '[.[0].sha]'])[0];
      let pathMoved = false;
      if (latest && !latest.startsWith(commit)) {
        const c = ghJson([`repos/${repo}/compare/${commit}...${latest}`, '--jq', '{status: .status}']);
        pathMoved = c.status === 'ahead' || c.status === 'diverged';
      }
      value = { ahead: head.ahead, pathMoved, latest: latest?.slice(0, 7) ?? null };
    }
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
    const c = compare(u.repo, u.commit, u.path);
    if (c.error) {
      rows.push({ id: r.id, repo: u.repo, commit: u.commit, state: 'error', detail: c.error });
      continue;
    }
    rows.push({ id: r.id, repo: u.repo, commit: u.commit.slice(0, 7), path: u.path ?? null, state: c.ahead === 0 ? 'current' : c.pathMoved ? 'moved' : 'unrelated-changes', ahead: c.ahead, latest: c.latest ?? null });
  }
}
if (json) console.log(JSON.stringify(rows, null, 2));
else {
  for (const x of rows)
    console.log(`${x.state.padEnd(17)} ${x.id.padEnd(36)} ${x.repo}@${x.commit}${x.path ? ` ${x.path}` : ''}${x.error ? ` ${x.detail}` : ` (repository ahead ${x.ahead}${x.latest ? `, newest commit on the path ${x.latest}` : ''})`}`);
  const moved = rows.filter((x) => x.state === 'moved').length;
  console.log(`${rows.length} upstream pins; ${moved} moved under their path`);
}
