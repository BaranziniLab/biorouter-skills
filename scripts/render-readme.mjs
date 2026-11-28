#!/usr/bin/env node
// Generates the README tables, the NOTICE file and the provenance folder files from catalog.json.
//
//   node scripts/render-readme.mjs          # rewrite README.md's generated sections, NOTICE and the folder files
//   node scripts/render-readme.mjs --check  # fail when any of them differs from what the catalog generates
//   node scripts/render-readme.mjs --root <dir>   # another checkout (the tests use a throwaway one)
//
// README.md keeps its hand-written prose; only the text between
// <!-- catalog:begin NAME --> and <!-- catalog:end NAME --> is generated.
//
// The folder files are written only for rows where folderProvenanceWanted()
// holds (format 2, and no PV9 deferral in provenance-baseline.json): the
// item's PROVENANCE.md, and metadata.origin, metadata.credit and
// metadata.curated_by in every SKILL.md of the item (the format 1 keys
// upstream_licence, upstream_author and source go, and upstream unless it
// names a source of the row). A deferred row's files wait for its next
// release, and --check leaves them alone.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  CURATED_BY,
  SHIPPED_USES,
  creditLine,
  currentIdeas,
  folderProvenanceWanted,
  frontmatterCredits,
  groupSources,
  labCopyrightLine,
  licenceTokens,
  provenanceFormat,
  sourceKey,
  sourceName,
  sourceUrl,
  usesOf,
} from './lib/catalog-rules.mjs';
import { readProvenanceBaseline } from './lib/provenance-baseline.mjs';
import { PROVENANCE_FILE, mdCode, mdLink, mdText, oneLine, renderProvenanceMd } from './lib/provenance-md.mjs';
import { retiredMetadataKey, setMetadata } from './lib/frontmatter.mjs';
import { REPO_ROOT, skillFilesIn } from './lib/repo.mjs';

const BSD = new Set(['BSD-2-Clause', 'BSD-3-Clause']);
const esc = (s) => String(s ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
const link = (repo) => `[${repo}](https://github.com/${repo})`;
const list = (x) => (Array.isArray(x) ? x : []);
const uniq = (xs) => [...new Set(xs)];
const shipped = (u) => usesOf(u).some((x) => SHIPPED_USES.includes(x));
const ORIGIN_LABELS = { 'in-house': 'In-house', 'ideas-derived': 'Ideas-derived', adapted: 'Adapted', 'third-party': 'Third-party' };
const NOT_CLASSIFIED = 'Not yet classified';

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

/** The format 1 label, as the catalog records it: every distinct licence of one repository. */
function sourceLabel(row) {
  const s = row.source ?? {};
  if (s.origin === 'adapted') {
    const repos = new Map();
    for (const u of s.upstreams ?? []) {
      if (!repos.has(u.repo)) repos.set(u.repo, []);
      const lics = repos.get(u.repo);
      for (const t of licenceTokens(u.licence)) if (!lics.includes(t)) lics.push(t);
    }
    return [...repos].map(([repo, lics]) => `${link(repo)} (${lics.join(', ')})`).join(', ');
  }
  if (s.origin === 'lab') return 'Lab-original';
  const insp = s.inspired_by ?? [];
  return insp.length ? `Native rewrite inspired by ${insp.map(link).join(' and ')}; no upstream text copied` : 'Native';
}

const USE_NOTES = { dependency: 'a dependency', launched: 'run at run time', hosted: "run on its publisher's servers" };

/** One source group of a format 2 row: "[name](url) by credit (licences)", noting a source that is not redistributed. */
function groupLabel(g) {
  const u = g.entries.find((e) => e.url) ?? g.entries[0];
  const url = sourceUrl(u) ?? (u.repo ? `https://github.com/${u.repo}` : null);
  let s = `${mdLink(g.name, url)} by ${mdText(g.credit) || 'an uncredited author'} (${g.licences.join(', ') || 'licence not recorded'})`;
  if (!g.entries.some(shipped)) {
    const notes = uniq(g.entries.flatMap(usesOf).map((x) => USE_NOTES[x] ?? x));
    if (notes.length) s += `, ${notes.join(' and ')}`;
  }
  return s;
}

/** The Origin and Sources and credit cells of one active row. */
function provenanceCells(row, catalogFormat) {
  if (provenanceFormat(row, catalogFormat) === 1) return [NOT_CLASSIFIED, sourceLabel(row)];
  const origin = row.source?.origin;
  const groups = groupSources(list(row.source?.upstreams)).map(groupLabel).join(', ');
  if (origin === 'in-house' || origin === 'ideas-derived') {
    const line = mdText(creditLine(row));
    return [ORIGIN_LABELS[origin], groups ? `${line} Sources: ${groups}` : line];
  }
  return [ORIGIN_LABELS[origin] ?? mdText(origin), groups || mdText(creditLine(row))];
}

function skillNames(list_) {
  const noun = list_.every((r) => r.kind === 'bundle') ? 'bundles' : 'skills';
  return `${list_.length > 12 ? `${list_.length} ${noun}: ` : ''}${list_.map((r) => `\`${r.id}\``).join(', ')}`;
}

/** Rows grouped by identical cells, in first-appearance order. */
function groupedTable(header, rows, cellsOf) {
  const groups = new Map();
  for (const r of rows) {
    const cells = cellsOf(r);
    if (!cells) continue;
    const key = JSON.stringify(cells);
    if (!groups.has(key)) groups.set(key, { cells, rows: [] });
    groups.get(key).rows.push(r);
  }
  const lines = [`| ${header.join(' | ')} |`, `|${header.map(() => '---').join('|')}|`];
  for (const g of groups.values()) lines.push(`| ${[skillNames(g.rows), ...g.cells.map(esc)].join(' | ')} |`);
  return { lines, count: groups.size };
}

function provenanceTable(rows, catalogFormat) {
  return groupedTable(['Skills', 'Origin', 'Sources and credit', 'Licence'], rows, (r) => [...provenanceCells(r, catalogFormat), r.licence ?? '']).lines.join('\n');
}

const ideaRef = (i) => `${mdLink(i.name, i.url)}${i.credit ? ` (${mdText(i.credit)})` : ''}`;

/** Ideas, references and earlier versions of one active row, or null when it records none. */
function ideasCells(row, catalogFormat) {
  if (provenanceFormat(row, catalogFormat) === 1) {
    const insp = row.source?.inspired_by ?? [];
    return insp.length ? [insp.map(link).join(', '), '', ''] : null;
  }
  const src = row.source ?? {};
  const ideas = currentIdeas(row).map(ideaRef);
  const refs = list(src.references).map(ideaRef);
  for (const [folder, c] of Object.entries(row.kind === 'bundle' ? row.components ?? {} : {})) {
    for (const w of list(c.written_for_biorouter)) {
      const wi = currentIdeas(w).map(ideaRef);
      if (wi.length) ideas.push(`${mdCode(`${folder}/${w.path}`)}: ${wi.join(', ')}`);
      const wr = list(w.references).map(ideaRef);
      if (wr.length) refs.push(`${mdCode(`${folder}/${w.path}`)}: ${wr.join(', ')}`);
    }
    const ci = currentIdeas(c).map(ideaRef);
    if (ci.length) ideas.push(`${mdCode(folder)}: ${ci.join(', ')}`);
    const cr = list(c.references).map(ideaRef);
    if (cr.length) refs.push(`${mdCode(folder)}: ${cr.join(', ')}`);
  }
  const earlier = [];
  for (const h of list(row.history)) {
    if (!h?.origin && !h?.licence) continue;
    earlier.push(`${mdText(h.version)}: ${[h.origin, h.licence].filter(Boolean).map(mdText).join(', ')}`);
  }
  const old = list(src.ideas_from).filter((i) => i?.applies_to === 'earlier').map(ideaRef);
  if (old.length) earlier.push(`Ideas from ${old.join(', ')}`);
  if (!ideas.length && !refs.length && !earlier.length) return null;
  return [ideas.join('; '), refs.join('; '), earlier.join('; ')];
}

function ideasTable(rows, catalogFormat) {
  const t = groupedTable(['Skills', 'Ideas', 'References', 'Earlier versions'], rows, (r) => ideasCells(r, catalogFormat));
  return t.count ? t.lines.join('\n') : 'No item records ideas, references or earlier versions yet.';
}

function subjectOf(ids, singular, plural) {
  return ids.length === 1 ? `${ids[0]} ${singular}` : `${ids.join(', ')} ${plural}`;
}

function whereText(paths) {
  return paths.length > 3 ? `${paths.length} folders across the items named here` : paths.join(', ');
}

function pinText(u) {
  if (u.commit) return `commit ${u.commit}`;
  if (u.version) return `version ${u.version}`;
  return '';
}

const HOLDERLESS = 'its licence names no copyright holder';

/**
 * The repository NOTICE. Format 1 rows keep the shape they always had (active
 * adapted rows, one block per upstream and change note); format 2 rows list
 * every source they redistribute, with its credit, and the work they use
 * without redistributing it (dependencies, programs launched at run time,
 * data and services) under "Other credited work". Each id appears once per
 * block, and a source whose licence names no holder says so.
 */
export function renderNotice(catalog) {
  const catalogFormat = catalog.format;
  const blocks = new Map();
  const others = new Map();
  const add = (map, key, make, id, p) => {
    if (!map.has(key)) map.set(key, { ...make(), ids: [], paths: [] });
    const g = map.get(key);
    if (!g.ids.includes(id)) g.ids.push(id);
    if (p && !g.paths.includes(p)) g.paths.push(p);
  };
  for (const r of (catalog.items ?? []).filter((x) => x.status === 'active')) {
    const ups = list(r.source?.upstreams);
    if (provenanceFormat(r, catalogFormat) === 1) {
      if (r.source?.origin !== 'adapted') continue;
      const changes = r.source.changes ?? '';
      for (const u of ups) {
        add(blocks, JSON.stringify([1, u.repo, u.commit, u.licence, u.copyright ?? null, changes]), () => ({ format: 1, u, changes }), r.id, u.path);
      }
      continue;
    }
    for (const u of ups) {
      if (shipped(u)) add(blocks, JSON.stringify([2, sourceKey(u), u.commit ?? null, u.version ?? null, u.licence ?? null, u.copyright ?? null, u.copyright_note ?? null]), () => ({ format: 2, u }), r.id, u.path);
      else add(others, JSON.stringify(['source', sourceKey(u), u.version ?? null, u.licence ?? null]), () => ({ kind: 'source', u }), r.id, null);
    }
    for (const d of list(r.source?.data_and_services)) add(others, JSON.stringify(['data', d.name, d.url ?? null]), () => ({ kind: 'data', d }), r.id, null);
  }

  const shippedText = [];
  for (const g of blocks.values()) {
    const { u } = g;
    const subject = subjectOf(g.ids, 'includes', 'include');
    const where = whereText(g.paths);
    const ident = g.format === 1 ? u.repo : u.repo ?? sourceUrl(u) ?? sourceName(u);
    const said = [where, pinText(u)].filter(Boolean).join(', ');
    let text = `${subject} material from ${ident}${said ? ` (${said})` : ''}`;
    if (u.copyright) text += `,\n${u.copyright}, licensed under ${u.licence}.`;
    else if (g.format === 2 && u.copyright_note) text += `, licensed under ${u.licence}; ${HOLDERLESS} (${oneLine(u.copyright_note)}).`;
    else text += `, licensed under ${u.licence}; ${HOLDERLESS}.`;
    if (g.format === 1 && g.changes) text += ` Changes: ${g.changes}`;
    if (g.format === 2) {
      const people = list(u.people).filter(Boolean);
      text += `\nCredited to ${oneLine(u.credit) || 'an uncredited author'}${people.length ? `, with ${people.map(oneLine).join(', ')}` : ''}.`;
      if (u.cite) text += `\nCite: ${oneLine(u.cite)}`;
    }
    if (licenceTokens(u.licence).some((x) => BSD.has(x))) text += `\nThe names of the copyright holders and contributors are not used to endorse or promote Biorouter.`;
    if (g.format === 2 && u.upstream_notice === true) text += `\nIts NOTICE file is reproduced in the notice file of each item named here.`;
    shippedText.push(text);
  }

  const otherText = [];
  for (const g of others.values()) {
    const subject = subjectOf(g.ids, 'uses', 'use');
    if (g.kind === 'source') {
      const { u } = g;
      const ident = [u.repo ?? sourceUrl(u), u.version ? `version ${u.version}` : null].filter(Boolean).join(', ');
      let text = `${subject} ${sourceName(u)}${ident ? ` (${ident})` : ''} by ${oneLine(u.credit) || 'an uncredited author'}, licensed under ${u.licence}: ${oneLine(u.what)} (${usesOf(u).join(', ')}, not redistributed).`;
      if (u.cite) text += ` Cite: ${oneLine(u.cite)}`;
      otherText.push(text);
    } else {
      const { d } = g;
      let text = `${subject} ${oneLine(d.name)}${d.url ? ` (${d.url})` : ''}, a ${d.kind ?? 'source'}${d.credit ? ` by ${oneLine(d.credit)}` : ''}`;
      text += d.terms ? `; terms: ${oneLine(d.terms)}.` : '; terms not recorded.';
      if (d.cite) text += ` Cite: ${oneLine(d.cite)}`;
      otherText.push(text);
    }
  }

  return [
    'Biorouter Skills',
    labCopyrightLine(2026),
    CURATED_BY,
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
    shippedText.join('\n\n'),
    '',
    ...(otherText.length ? ['Other credited work', '===================', '', otherText.join('\n\n'), ''] : []),
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
    provenance: provenanceTable(active, catalog.format),
    'provenance-ideas': ideasTable(active, catalog.format),
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

/**
 * The provenance folder files of every active row whose files are wanted now:
 * [{ rel, next, current }] with paths relative to the root (current is null
 * for a missing file). A SKILL.md without front matter is left to
 * check-catalog.mjs, which reports it.
 */
export function folderFiles(root, catalog, baseline = readProvenanceBaseline(root)) {
  const out = [];
  const read = (rel) => (fs.existsSync(path.join(root, rel)) ? fs.readFileSync(path.join(root, rel), 'utf8') : null);
  for (const row of catalog.items ?? []) {
    if (row.status !== 'active' || !row.path) continue;
    if (!folderProvenanceWanted(row, { catalogFormat: catalog.format, baseline })) continue;
    if (!fs.existsSync(path.join(root, row.path))) continue;
    const rel = `${row.path}/${PROVENANCE_FILE}`;
    out.push({ rel, next: renderProvenanceMd(row, catalog), current: read(rel) });
    for (const s of skillFilesIn(root, row.path)) {
      if (!s.ok) continue;
      const next = setMetadata(s.text, frontmatterCredits(row, s.rel), { remove: retiredMetadataKey(row) });
      out.push({ rel: `${row.path}/${s.rel}`, next, current: s.text });
    }
  }
  return out;
}

function main() {
  const argv = process.argv.slice(2);
  const check = argv.includes('--check');
  const at = argv.indexOf('--root');
  const root = at === -1 ? REPO_ROOT : path.resolve(argv[at + 1]);
  const catalog = JSON.parse(fs.readFileSync(path.join(root, 'catalog.json'), 'utf8'));
  const readmePath = path.join(root, 'README.md');
  const noticePath = path.join(root, 'NOTICE');
  const readme = fs.readFileSync(readmePath, 'utf8');
  const nextReadme = applySections(readme, renderSections(catalog));
  const nextNotice = renderNotice(catalog);
  const files = folderFiles(root, catalog);
  const itemCount = files.filter((f) => f.rel.endsWith(`/${PROVENANCE_FILE}`)).length;
  if (check) {
    const stale = [];
    if (nextReadme !== readme) stale.push('README.md');
    if (!fs.existsSync(noticePath) || fs.readFileSync(noticePath, 'utf8') !== nextNotice) stale.push('NOTICE');
    for (const f of files) if (f.current !== f.next) stale.push(f.rel);
    if (stale.length) {
      console.error(`${stale.join(', ')} ${stale.length === 1 ? 'differs' : 'differ'} from what catalog.json generates; run node scripts/render-readme.mjs`);
      process.exit(1);
    }
    console.log(itemCount ? `README.md, NOTICE and the provenance files of ${itemCount} item(s) are current` : 'README.md and NOTICE are current');
    return;
  }
  fs.writeFileSync(readmePath, nextReadme);
  fs.writeFileSync(noticePath, nextNotice);
  let wrote = 0;
  for (const f of files) {
    if (f.current === f.next) continue;
    fs.writeFileSync(path.join(root, f.rel), f.next);
    wrote++;
  }
  console.log(wrote ? `wrote README.md, NOTICE and ${wrote} provenance file(s)` : 'wrote README.md and NOTICE');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
