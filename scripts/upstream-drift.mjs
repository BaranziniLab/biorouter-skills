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
//
// Format 2 rows: only sources with a repo and a commit can be compared. Sources
// with a url and no repo, with a version and no commit, or with neither pin are
// skipped and counted, and a lab-owned source (owner "lab") is labelled.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT } from './lib/repo.mjs';
import { PROVENANCE_FORMAT, isLabOwned, provenanceFormat } from './lib/catalog-rules.mjs';

/**
 * The upstream pins to compare: { targets: [{ id, format, repo, commit, path,
 * owner (format 2 only) }], skipped: { urlOnly, versionOnly, unpinned } }.
 * Active rows not maintained here only. Format 1 rows give every upstream with
 * a commit, as before format 2, and count nothing they skip.
 */
export function driftTargets(catalog) {
  const targets = [];
  const skipped = { urlOnly: 0, versionOnly: 0, unpinned: 0 };
  for (const r of (catalog.items ?? []).filter((x) => x.status === 'active' && !x.source?.maintained_here)) {
    const format = provenanceFormat(r, catalog.format);
    for (const u of r.source?.upstreams ?? []) {
      if (format !== PROVENANCE_FORMAT) {
        if (u.commit) targets.push({ id: r.id, format, repo: u.repo, commit: u.commit, path: u.path ?? null });
        continue;
      }
      if (!u.repo) skipped.urlOnly++;
      else if (!u.commit) skipped[u.version ? 'versionOnly' : 'unpinned']++;
      else targets.push({ id: r.id, format, repo: u.repo, commit: u.commit, path: u.path ?? null, owner: isLabOwned(u) ? 'lab' : 'external' });
    }
  }
  return { targets, skipped };
}

function ghJson(args) {
  const out = execFileSync('gh', ['api', ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  return JSON.parse(out);
}

const cache = new Map();

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

function main(argv) {
  const json = argv.includes('--json');
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const { targets, skipped } = driftTargets(catalog);
  const rows = [];
  for (const t of targets) {
    const owner = t.format === PROVENANCE_FORMAT ? { owner: t.owner } : {};
    const c = compare(t.repo, t.commit, t.path);
    if (c.error) {
      rows.push({ id: t.id, repo: t.repo, commit: t.commit, state: 'error', detail: c.error, ...owner });
      continue;
    }
    rows.push({ id: t.id, repo: t.repo, commit: t.commit.slice(0, 7), path: t.path, state: c.ahead === 0 ? 'current' : c.pathMoved ? 'moved' : 'unrelated-changes', ahead: c.ahead, latest: c.latest ?? null, ...owner });
  }
  if (json) console.log(JSON.stringify(rows, null, 2));
  else {
    for (const x of rows)
      console.log(`${x.state.padEnd(17)} ${x.id.padEnd(36)} ${x.repo}@${x.commit}${x.path ? ` ${x.path}` : ''}${x.owner === 'lab' ? ' [lab-owned]' : ''}${x.state === 'error' ? ` ${x.detail}` : ` (repository ahead ${x.ahead}${x.latest ? `, newest commit on the path ${x.latest}` : ''})`}`);
    const moved = rows.filter((x) => x.state === 'moved').length;
    const skips = skipped.urlOnly + skipped.versionOnly + skipped.unpinned;
    console.log(`${rows.length} upstream pins; ${moved} moved under their path${skips ? `; skipped ${skips} format 2 source(s) that cannot be compared (${skipped.urlOnly} url only, ${skipped.versionOnly} version only, ${skipped.unpinned} unpinned)` : ''}`);
  }
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main(process.argv.slice(2));
