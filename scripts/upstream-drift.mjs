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
// 300 files, so it cannot answer that question for a busy repository). A path
// field that lists several paths is read as that list, and the pin moved when
// any one of them moved.
//
// Format 2 rows: only sources with a repo and a commit can be compared. Sources
// with a url and no repo, with a version and no commit, or with neither pin are
// skipped and counted, and a lab-owned source (owner "lab") is labelled.

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT } from './lib/repo.mjs';
import { PROVENANCE_FORMAT, isLabOwned, pathEntries, provenanceFormat } from './lib/catalog-rules.mjs';

/**
 * The paths an upstream's `path` field names. The field is a comma-separated
 * list ("skills/prd, skills/ralph, prompt.md"), and an entry may end in a note
 * in parentheses, which may itself hold commas ("plugins/code-review (v1.0.1,
 * c905cd8 command)"). Notes and trailing slashes are dropped; a missing or
 * empty field gives [].
 */
export function upstreamPaths(field) {
  const paths = [];
  for (const e of pathEntries(field)) {
    const p = e.replace(/\s+\(.*\)\s*$/s, '').trim().replace(/\/+$/, '');
    if (p && !paths.includes(p)) paths.push(p);
  }
  return paths;
}

/**
 * The upstream pins to compare: { targets: [{ id, format, repo, commit, path,
 * paths, owner (format 2 only) }], skipped: { urlOnly, versionOnly, unpinned } }.
 * `path` is the field as recorded and `paths` the list it names (upstreamPaths).
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
        if (u.commit) targets.push({ id: r.id, format, repo: u.repo, commit: u.commit, path: u.path ?? null, paths: upstreamPaths(u.path) });
        continue;
      }
      if (!u.repo) skipped.urlOnly++;
      else if (!u.commit) skipped[u.version ? 'versionOnly' : 'unpinned']++;
      else targets.push({ id: r.id, format, repo: u.repo, commit: u.commit, path: u.path ?? null, paths: upstreamPaths(u.path), owner: isLabOwned(u) ? 'lab' : 'external' });
    }
  }
  return { targets, skipped };
}

function ghJson(args) {
  const out = execFileSync('gh', ['api', ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  return JSON.parse(out);
}

/**
 * Compares one pin with its repository's head: { ahead, pathMoved } with no
 * paths, or also { latest, paths: [{ path, moved, latest }] } when paths are
 * given and the repository moved. Each path is asked about on its own, and the
 * pin moved when any path moved; `latest` is the newest commit on the first
 * path that moved, or on the first path when none did. `gh` runs `gh api` and
 * returns its JSON (a test passes a fake). A failure gives { error }.
 */
export function comparePin(repo, commit, paths, gh = ghJson) {
  try {
    const head = gh([`repos/${repo}/compare/${commit}...HEAD`, '--jq', '{ahead: .ahead_by}']);
    if (!paths.length || head.ahead === 0) return { ahead: head.ahead, pathMoved: head.ahead > 0 };
    const perPath = paths.map((p) => {
      const latest = gh([`repos/${repo}/commits?path=${encodeURIComponent(p)}&per_page=1`, '--jq', '[.[0].sha]'])[0];
      let moved = false;
      if (latest && !latest.startsWith(commit)) {
        const c = gh([`repos/${repo}/compare/${commit}...${latest}`, '--jq', '{status: .status}']);
        moved = c.status === 'ahead' || c.status === 'diverged';
      }
      return { path: p, moved, latest: latest?.slice(0, 7) ?? null };
    });
    const shown = perPath.find((x) => x.moved) ?? perPath[0];
    return { ahead: head.ahead, pathMoved: perPath.some((x) => x.moved), latest: shown.latest, paths: perPath };
  } catch (e) {
    return { error: String(e.stderr || e.message).trim().split('\n')[0] };
  }
}

const cache = new Map();

function compare(repo, commit, paths) {
  const key = `${repo}@${commit}:${paths.join('\n')}`;
  if (!cache.has(key)) cache.set(key, comparePin(repo, commit, paths));
  return cache.get(key);
}

/** The bracketed detail of a table line: how far the repository moved, and which of a list of paths moved. */
function detail(x) {
  if (x.state === 'error') return ` ${x.detail}`;
  if (!x.paths || x.paths.length < 2) return ` (repository ahead ${x.ahead}${x.latest ? `, newest commit on the path ${x.latest}` : ''})`;
  const moved = x.paths.filter((p) => p.moved);
  const which = moved.length ? `: ${moved.map((p) => `${p.path} (${p.latest})`).join(', ')}` : '';
  return ` (repository ahead ${x.ahead}, ${moved.length} of ${x.paths.length} paths moved${which})`;
}

function main(argv) {
  const json = argv.includes('--json');
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const { targets, skipped } = driftTargets(catalog);
  const rows = [];
  for (const t of targets) {
    const owner = t.format === PROVENANCE_FORMAT ? { owner: t.owner } : {};
    const c = compare(t.repo, t.commit, t.paths);
    if (c.error) {
      rows.push({ id: t.id, repo: t.repo, commit: t.commit, state: 'error', detail: c.error, ...owner });
      continue;
    }
    rows.push({ id: t.id, repo: t.repo, commit: t.commit.slice(0, 7), path: t.path, state: c.ahead === 0 ? 'current' : c.pathMoved ? 'moved' : 'unrelated-changes', ahead: c.ahead, latest: c.latest ?? null, ...(c.paths ? { paths: c.paths } : {}), ...owner });
  }
  if (json) console.log(JSON.stringify(rows, null, 2));
  else {
    for (const x of rows)
      console.log(`${x.state.padEnd(17)} ${x.id.padEnd(36)} ${x.repo}@${x.commit}${x.path ? ` ${x.path}` : ''}${x.owner === 'lab' ? ' [lab-owned]' : ''}${detail(x)}`);
    const moved = rows.filter((x) => x.state === 'moved').length;
    const skips = skipped.urlOnly + skipped.versionOnly + skipped.unpinned;
    console.log(`${rows.length} upstream pins; ${moved} moved under their path${skips ? `; skipped ${skips} format 2 source(s) that cannot be compared (${skipped.urlOnly} url only, ${skipped.versionOnly} version only, ${skipped.unpinned} unpinned)` : ''}`);
  }
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main(process.argv.slice(2));
