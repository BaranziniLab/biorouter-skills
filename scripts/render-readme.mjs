#!/usr/bin/env node
// Generates the README tables and the NOTICE file from catalog.json.
//
//   node scripts/render-readme.mjs          # rewrite README.md's generated sections and NOTICE
//   node scripts/render-readme.mjs --check  # fail when either differs from what the catalog generates
//
// README.md keeps its hand-written prose; only the text between
// <!-- catalog:begin NAME --> and <!-- catalog:end NAME --> is generated.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { REPO_ROOT } from './lib/repo.mjs';

const BSD = new Set(['BSD-2-Clause', 'BSD-3-Clause']);
const esc = (s) => String(s ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const link = (repo) => `[${repo}](https://github.com/${repo})`;

function invocation(row) {
  if (row.kind === 'bundle') return `Bundle, ${Object.values(row.components ?? {}).filter((c) => c.status === 'active').length} skills`;
  return row.invocation === 'user' ? `\`/${row.id}\`` : 'Auto';
}

function itemTable(rows) {
  const lines = ['| Skill | Version | Invocation | Licence | What it does |', '|---|---|---|---|---|'];
  for (const r of rows) {
    lines.push(`| [\`${r.id}\`](${r.path}) | ${r.version} | ${invocation(r)} | ${esc(r.licence)} | ${esc(r.summary)} |`);
  }
  return lines.join('\n');
}

function bioTable(rows) {
  const lines = ['| Bundle | Version | Skills | What it covers |', '|---|---|---|---|'];
  for (const r of rows) {
    const n = Object.values(r.components ?? {}).filter((c) => c.status === 'active').length;
    lines.push(`| [\`${r.id}\`](${r.path}) | ${r.version} | ${n} | ${esc(r.summary)} |`);
  }
  return lines.join('\n');
}

function movedTable(rows, byId) {
  if (!rows.length) return 'Nothing has moved or retired yet.';
  const lines = ['| Old skill | Final version | Status | Use instead |', '|---|---|---|---|'];
  for (const r of rows) {
    let use;
    if (r.status.startsWith('superseded_by:builtin:')) use = `the built-in \`${r.status.slice('superseded_by:builtin:'.length)}\` skill (update Biorouter)`;
    else if (r.status.startsWith('superseded_by:')) {
      const t = r.status.slice('superseded_by:'.length);
      use = `[\`${t}\`](${byId.get(t)?.path ?? t})`;
    } else {
      const u = r.retired?.use;
      use = u ? (u.startsWith('builtin:') ? `the built-in \`${u.slice(8)}\` skill` : `[\`${u}\`](${byId.get(u)?.path ?? u})`) : 'nothing';
    }
    const status = r.status === 'retired' ? `Retired: ${esc(r.retired?.reason)}` : 'Merged';
    lines.push(`| \`${r.id}\` | ${r.version} | ${status} | ${use} |`);
  }
  return lines.join('\n');
}

function sourceLabel(row) {
  const s = row.source ?? {};
  if (s.origin === 'adapted') {
    const ups = [...new Map((s.upstreams ?? []).map((u) => [u.repo, u])).values()];
    return ups.map((u) => `${link(u.repo)} (${u.licence})`).join(', ');
  }
  if (s.origin === 'lab') return 'Lab-original';
  const insp = s.inspired_by ?? [];
  return insp.length ? `Native rewrite inspired by ${insp.map(link).join(' and ')}; no upstream text copied` : 'Native';
}

function sourcesTable(rows) {
  const groups = new Map();
  for (const r of rows) {
    const key = JSON.stringify([sourceLabel(r), r.licence, r.source?.changes ?? '']);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const lines = ['| Skills | Source | Licence of the archive | What changed for Biorouter |', '|---|---|---|---|'];
  for (const [key, list] of groups) {
    const [label, licence, changes] = JSON.parse(key);
    const noun = list.every((r) => r.kind === 'bundle') ? 'bundles' : 'skills';
    const names = `${list.length > 12 ? `${list.length} ${noun}: ` : ''}${list.map((r) => `\`${r.id}\``).join(', ')}`;
    lines.push(`| ${names} | ${label} | ${esc(licence)} | ${esc(changes) || '—'} |`);
  }
  return lines.join('\n');
}

export function renderNotice(catalog) {
  const groups = new Map();
  for (const r of catalog.items.filter((x) => x.status === 'active' && x.source?.origin === 'adapted')) {
    for (const u of r.source.upstreams ?? []) {
      const key = JSON.stringify([u.repo, u.commit, u.licence, u.copyright ?? null, r.source.changes ?? '']);
      if (!groups.has(key)) groups.set(key, { u, changes: r.source.changes ?? '', ids: [], paths: [] });
      const g = groups.get(key);
      g.ids.push(r.id);
      if (u.path) g.paths.push(u.path);
    }
  }
  const blocks = [];
  for (const g of groups.values()) {
    const { u } = g;
    const where = g.paths.length > 3 ? `${g.paths.length} folders, one per skill named here` : g.paths.join(', ');
    const subject = g.ids.length === 1 ? `${g.ids[0]} includes` : `${g.ids.join(', ')} include`;
    let text = `${subject} material from ${u.repo} (${where}${u.commit ? `, commit ${u.commit}` : ''})`;
    text += u.copyright ? `,\n${u.copyright}, licensed under ${u.licence}.` : `, licensed under ${u.licence}.`;
    if (g.changes) text += ` Changes: ${g.changes}`;
    if (BSD.has(u.licence)) text += `\nThe names of the copyright holders and contributors are not used to endorse or promote Biorouter.`;
    blocks.push(text);
  }
  return [
    'Biorouter Skills',
    'Copyright 2026 Baranzini Lab, University of California, San Francisco',
    '',
    'Each skill and bundle carries its own licence, recorded in catalog.json and in',
    'the license line of its SKILL.md files. Material written here is licensed under',
    'the Apache License, Version 2.0 (see LICENSE). Material adapted from upstream',
    'projects keeps its upstream licence; the archive of each such skill carries the',
    'upstream copyright line and licence text in its notice file.',
    '',
    'This file is generated from catalog.json by scripts/render-readme.mjs.',
    '',
    'Upstream material',
    '=================',
    '',
    blocks.join('\n\n'),
    '',
  ].join('\n');
}

export function renderSections(catalog) {
  const items = catalog.items;
  const byId = new Map(items.map((r) => [r.id, r]));
  const active = items.filter((r) => r.status === 'active');
  return {
    core: itemTable(active.filter((r) => r.category === 'core')),
    developer: itemTable(active.filter((r) => r.category === 'developer')),
    biomedical: bioTable(active.filter((r) => r.category === 'biomedical')),
    moved: movedTable(items.filter((r) => r.status !== 'active'), byId),
    sources: sourcesTable(active),
    counts: `${active.filter((r) => r.category === 'core').length} core skills, ${active.filter((r) => r.category === 'developer').length} developer skills and ${active.filter((r) => r.category === 'biomedical').length} biomedical bundles (${active.filter((r) => r.category === 'biomedical').reduce((n, r) => n + Object.values(r.components ?? {}).filter((c) => c.status === 'active').length, 0)} skills) are active; ${items.length - active.length} older skills have moved or retired.`,
  };
}

export function applySections(readme, sections) {
  let out = readme;
  for (const [name, body] of Object.entries(sections)) {
    const re = new RegExp(`(<!-- catalog:begin ${name} -->)[\\s\\S]*?(<!-- catalog:end ${name} -->)`);
    if (!re.test(out)) throw new Error(`README.md has no <!-- catalog:begin ${name} --> ... <!-- catalog:end ${name} --> block`);
    out = out.replace(re, (_, a, b) => `${a}\n${body}\n${b}`);
  }
  return out;
}

function main() {
  const check = process.argv.includes('--check');
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const readmePath = path.join(REPO_ROOT, 'README.md');
  const noticePath = path.join(REPO_ROOT, 'NOTICE');
  const readme = fs.readFileSync(readmePath, 'utf8');
  const nextReadme = applySections(readme, renderSections(catalog));
  const nextNotice = renderNotice(catalog);
  if (check) {
    const stale = [];
    if (nextReadme !== readme) stale.push('README.md');
    if (!fs.existsSync(noticePath) || fs.readFileSync(noticePath, 'utf8') !== nextNotice) stale.push('NOTICE');
    if (stale.length) {
      console.error(`${stale.join(' and ')} differ from what catalog.json generates; run node scripts/render-readme.mjs`);
      process.exit(1);
    }
    console.log('README.md and NOTICE are current');
    return;
  }
  fs.writeFileSync(readmePath, nextReadme);
  fs.writeFileSync(noticePath, nextNotice);
  console.log('wrote README.md and NOTICE');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
