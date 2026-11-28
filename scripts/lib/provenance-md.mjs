// Generates an item folder's PROVENANCE.md from its catalog row (format 2).
//
// One file per item (a bundle gets one, with a section per component that is
// not plain copied material). check-catalog.mjs (PV9) compares the folder's
// file with this function's output, and render-readme.mjs writes it, only for
// rows where folderProvenanceWanted() holds.
//
// Step 1 contract: the export names and signatures of PROVENANCE_FILE,
// GENERATED_MARK and renderProvenanceMd are fixed. Every credit text comes
// from scripts/lib/catalog-rules.mjs, so this file, the README, the front
// matter, the page and the app print the same words.
//
// The sections, in order, each only when it has something to say: the credit
// line and origin sentence; Sources (a table of every upstream entry);
// the citations its sources ask for; Written for Biorouter (a bundle's
// components that are not plain copied material, and the files written here
// inside copied components); Ideas;
// Data and services; References; Contributors; Earlier versions; Licences;
// then the curator line, last.

import {
  CURATED_BY,
  LAB_COPYRIGHT_HOLDER,
  SHIPPED_USES,
  componentCreditLine,
  componentRecord,
  creditLine,
  currentIdeas,
  isLabOwned,
  isPublication,
  labCopyrightLine,
  originSentence,
  sourceKey,
  sourceName,
  sourceUrl,
  stubCreditLines,
  usesOf,
  viaOf,
} from './catalog-rules.mjs';

export const PROVENANCE_FILE = 'PROVENANCE.md';
export const GENERATED_MARK = '<!-- Generated from catalog.json by scripts/render-readme.mjs. Do not edit by hand. -->';

const list = (x) => (Array.isArray(x) ? x : []);
const has = (x) => x != null && String(x).trim() !== '';
const URL_OK = /^https?:\/\/\S+$/;

/**
 * One line of plain text: a missing value is empty, a newline is a space.
 * For plain-text files (NOTICE); Markdown takes mdText.
 */
export function oneLine(value) {
  return value == null ? '' : String(value).replace(/\s*\r?\n\s*/g, ' ').trim();
}

/**
 * One line of Markdown prose from an untrusted value (an upstream's credit,
 * what, evidence, copyright note): as oneLine, with every character that could
 * start markup escaped, so the value reads as the text it is. Backslashes,
 * backticks (code spans), asterisks and tildes (emphasis, strikethrough),
 * brackets (links) and angle brackets (raw HTML, autolinks) are escaped; an
 * underscore only where it could open or close emphasis (snake_case stays as
 * written); an ampersand only where it would start an entity.
 */
export function mdText(value) {
  return oneLine(value)
    .replace(/[\\`*~[\]<>]/g, '\\$&')
    .replace(/(?<![\p{L}\p{N}])_|_(?![\p{L}\p{N}])/gu, '\\_')
    .replace(/&(?=#?[A-Za-z0-9]+;)/g, '&amp;');
}

/** A Markdown table cell: as mdText, with pipes escaped. */
export function mdCell(value) {
  return mdText(value).replace(/\|/g, '\\|');
}

/** An http(s) URL as a Markdown link destination: the characters that would end or break it percent-encoded. */
export function mdUrl(url) {
  return String(url).replace(/[<>()`\\]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
}

/** `[name](url)` when the URL is an http(s) URL, else the name alone. */
export function mdLink(name, url) {
  const label = mdText(name);
  if (!has(url) || !URL_OK.test(String(url))) return label;
  return `[${label}](${mdUrl(url)})`;
}

/** A code span around an untrusted value: its fence is longer than any run of backticks inside it. */
export function mdCode(value) {
  const t = oneLine(value);
  const longest = Math.max(0, ...(t.match(/`+/g) ?? []).map((run) => run.length));
  const fence = '`'.repeat(longest + 1);
  const pad = t.startsWith('`') || t.endsWith('`') ? ' ' : '';
  return `${fence}${pad}${t}${pad}${fence}`;
}

const code = mdCode;
const sentence = (s) => {
  const t = mdText(s);
  return t && !/[.!?]$/.test(t) ? `${t}.` : t;
};
const capital = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const article = (word) => (/^[aeiou]/i.test(word) ? `an ${word}` : `a ${word}`);

function upstreamUrl(u) {
  return sourceUrl(u);
}

function sourceCell(u) {
  const name = sourceName(u);
  const head = mdLink(name, upstreamUrl(u));
  const details = [];
  if (has(u.repo) && u.repo !== name) details.push(code(u.repo));
  if (has(u.path)) details.push(code(u.path));
  return details.length ? `${head}: ${details.join(', ')}` : head;
}

function pinCell(u) {
  const parts = [];
  if (has(u.version)) parts.push(`version ${mdText(u.version)}`);
  else if (has(u.commit)) parts.push(`commit ${code(String(u.commit).slice(0, 12))}`);
  else if (isPublication(u)) parts.push(has(u.doi) ? `DOI ${code(u.doi)}` : 'pinned by its citation');
  else parts.push('not pinned');
  if (has(u.taken)) parts.push(`taken ${mdText(u.taken)}`);
  return parts.join(', ');
}

const shipped = (u) => usesOf(u).some((x) => SHIPPED_USES.includes(x));

function licenceCell(u, row) {
  // The lab's own work: its holder, and no licence claim for a repository
  // with no licence file (licence_file false).
  if (isLabOwned(u)) {
    const parts = [u.licence_file === false ? 'no licence file in its repository' : mdText(u.licence) || 'licence not recorded', `held by ${LAB_COPYRIGHT_HOLDER}`];
    if (u.upstream_notice === true) parts.push(`its NOTICE file ships with this item${has(row.notice_file) ? ` in ${mdText(row.notice_file)}` : ''}`);
    return parts.join('; ');
  }
  const parts = [mdText(u.licence) || 'licence not recorded'];
  if (has(u.copyright)) parts.push(`${mdText(u.copyright)}${has(u.copyright_note) ? ` (${mdText(u.copyright_note)})` : ''}`);
  else if (shipped(u) || has(u.copyright_note)) parts.push(`its licence names no copyright holder${has(u.copyright_note) ? ` (${mdText(u.copyright_note)})` : ''}`);
  if (u.upstream_notice === true) parts.push(`its NOTICE file ships with this item${has(row.notice_file) ? ` in ${mdText(row.notice_file)}` : ''}`);
  return parts.join('; ');
}

function creditCell(u) {
  const parts = [mdText(u.credit) || 'not recorded'];
  const people = list(u.people).filter(has).map(mdText);
  if (people.length) parts.push(`people: ${people.join(', ')}`);
  if (isLabOwned(u)) parts.push("the Baranzini Lab's own work");
  return parts.join('; ');
}

/**
 * The Via cell of one source: the other sources of the row it was reached
 * through, that is, those whose `via` names its repository: Cua Driver's row
 * names iFurySt/open-computer-use, whose own `via` lists trycua/cua.
 */
function viaCell(u, ups) {
  if (!has(u?.repo)) return '';
  const through = ups.filter((o) => o !== u && o?.repo !== u.repo && viaOf(o).includes(u.repo));
  return [...new Set(through.map((o) => o.repo ?? sourceName(o)))].map(code).join(', ');
}

function sourcesTable(ups, row) {
  const out = ['| Source | Commit or version | Licence | Credit and people | Use and what | Files | Via |', '|---|---|---|---|---|---|---|'];
  for (const u of ups) {
    const use = `${usesOf(u).map(mdText).join(', ')}: ${mdText(u.what)}`;
    const files = list(u.files).filter(has).map(code).join(', ');
    const via = viaCell(u, ups);
    // Cells are assembled from mdText pieces, then every pipe is escaped once.
    out.push(`| ${[sourceCell(u), pinCell(u), licenceCell(u, row), creditCell(u), use, files, via].map((c) => c.replace(/\|/g, '\\|')).join(' | ')} |`);
  }
  return out;
}

/** One line per source and citation it asks for (`cite`, as CITATION.cff's preferred-citation gives it), in source order. */
function citationLines(ups) {
  const seen = new Set();
  const out = [];
  for (const u of ups) {
    if (!has(u?.cite)) continue;
    const key = `${sourceKey(u)}\n${oneLine(u.cite)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(`- ${mdLink(sourceName(u), upstreamUrl(u))}: ${sentence(u.cite)}`);
  }
  return out;
}

/** "[name](url), a repository by Credit (licence): what." */
function ideaLine(i, { withEvidence = true } = {}) {
  const kind = has(i.kind) ? article(mdText(i.kind)) : 'a source';
  const by = has(i.credit) ? ` by ${mdText(i.credit)}` : '';
  const lic = has(i.licence) ? ` (${mdText(i.licence)})` : '';
  let s = `${mdLink(i.name, i.url)}, ${kind}${by}${lic}: ${sentence(i.what) || 'not recorded.'}`;
  if (withEvidence && has(i.evidence)) s += ` Ideas only, no text or code taken: ${sentence(i.evidence)}`;
  if (has(i.version_read)) s += ` Version read: ${sentence(i.version_read)}`;
  if (has(i.cite)) s += ` Cite: ${sentence(i.cite)}`;
  return s;
}

function referenceLine(r) {
  let s = mdLink(r.name, r.url);
  if (has(r.credit)) s += `, by ${mdText(r.credit)}`;
  s += '.';
  if (has(r.cite)) s += ` Cite: ${sentence(r.cite)}`;
  return s;
}

function dataLine(d) {
  const kind = has(d.kind) ? article(mdText(d.kind)) : 'a source';
  let s = `${mdLink(d.name, d.url)}, ${kind}${has(d.credit) ? ` by ${mdText(d.credit)}` : ''}.`;
  s += ` Terms: ${has(d.terms) ? sentence(d.terms) : 'not recorded.'}`;
  if (has(d.how)) s += ` How it is used: ${sentence(d.how)}`;
  if (has(d.cite)) s += ` Cite: ${sentence(d.cite)}`;
  return s;
}

function statusText(status) {
  const s = String(status ?? '');
  if (s === 'active') return 'active';
  if (s === 'removed') return 'removed';
  if (s.startsWith('superseded_by:')) return `merged into ${code(s.slice('superseded_by:'.length))}`;
  return mdText(s) || 'not recorded';
}

/** A component that is copied as published: an upstream path and nothing of its own. */
function plainCopied(comp) {
  return has(comp?.upstream_path) && !has(comp.origin) && !list(comp.written_for_biorouter).length && !has(comp.content_moved_to);
}

/** Components that get their own section: an origin of their own, files written here, or moved content. */
function ownSectionComponents(row) {
  if (row.kind !== 'bundle' || !row.components) return [];
  return Object.entries(row.components).filter(([, c]) => !plainCopied(c) && (has(c.origin) || list(c.written_for_biorouter).length || has(c.content_moved_to)));
}

function ideasClause(ideas) {
  const cur = list(ideas).filter((i) => i?.applies_to !== 'earlier');
  if (!cur.length) return '';
  return ` Ideas from ${cur.map((i) => ideaLine(i, { withEvidence: false }).replace(/\.$/, '')).join('; ')}.`;
}

function referencesClause(refs) {
  const r = list(refs);
  if (!r.length) return '';
  return ` References: ${r.map((x) => referenceLine(x).replace(/\.$/, '')).join('; ')}.`;
}

function componentSection(row, folder, comp) {
  const out = [`### ${mdText(folder)} (${code(comp.name ?? folder)})`, ''];
  out.push(mdText(componentCreditLine(row, folder)), '');
  if (has(comp.origin)) out.push(mdText(originSentence(componentRecord(row, folder))), '');
  const facts = [];
  if (has(comp.licence)) facts.push(`Licence: ${sentence(comp.licence)}`);
  facts.push(`Status: ${statusText(comp.status)}.`);
  if (has(comp.upstream_path)) facts.push(`Source path: ${code(comp.upstream_path)}.`);
  if (has(comp.content_moved_to)) facts.push(`Its content now lives in ${code(comp.content_moved_to)}.`);
  out.push(facts.join(' '), '');
  const ups = list(row.source?.upstreams);
  if (Array.isArray(comp.sources) && comp.sources.length && has(comp.origin)) {
    const names = comp.sources.map((i) => ups[i]).filter(Boolean).map((u) => mdLink(sourceName(u), upstreamUrl(u)));
    if (names.length) out.push(`Sources: ${names.join(', ')}.`, '');
  }
  const ideas = currentIdeas(comp);
  if (ideas.length) out.push(...ideas.map((i) => `Ideas from ${ideaLine(i)}`), '');
  if (list(comp.references).length) out.push(`References: ${list(comp.references).map((r) => referenceLine(r).replace(/\.$/, '')).join('; ')}.`, '');
  const written = list(comp.written_for_biorouter);
  if (written.length) {
    out.push('Files written for Biorouter in this component:', '');
    for (const w of written) {
      const lineage = [has(w.origin) ? capital(mdText(w.origin)) : null, has(w.licence) ? mdText(w.licence) : null].filter(Boolean).join(', ');
      out.push(`- ${code(`${folder}/${w.path}`)}: ${sentence(w.what) || 'not recorded.'}${lineage ? ` ${lineage}.` : ''}${ideasClause(w.ideas_from)}${referencesClause(w.references)}`);
    }
    out.push('');
  }
  return out;
}

function earlierLines(row) {
  const out = [];
  for (const h of list(row.history)) {
    if (!has(h?.origin) && !has(h?.licence)) continue;
    const what = [has(h.origin) ? mdText(h.origin) : null, has(h.licence) ? `licensed under ${mdText(h.licence)}` : null].filter(Boolean).join(', ');
    out.push(`- ${mdText(h.version)}${has(h.date) ? ` (${mdText(h.date)})` : ''}: ${what}.${has(h.note) ? ` Note: ${sentence(h.note)}` : ''}`);
  }
  for (const i of list(row.source?.ideas_from).filter((x) => x?.applies_to === 'earlier')) out.push(`- Ideas for an earlier version: ${ideaLine(i)}`);
  return out;
}

function licenceLines(row) {
  const year = String(list(row.history)[0]?.date ?? '').slice(0, 4) || '2026';
  const out = [
    `The archive's LICENSE file is the Apache License 2.0; it covers Biorouter's own text in this folder. ${labCopyrightLine(year)}.`,
  ];
  if (has(row.licence)) out.push(`The item as a whole is licensed under ${sentence(row.licence)}`);
  const ups = list(row.source?.upstreams);
  if (has(row.notice_file)) {
    out.push(`The copyright lines and licence texts of its sources are in ${mdText(row.notice_file)}.`);
    for (const u of ups.filter((x) => x.upstream_notice === true)) {
      out.push(`${mdText(row.notice_file)} also reproduces the NOTICE file of ${mdText(u.repo ?? sourceName(u))}, as section 4(d) of the Apache License asks.`);
    }
  } else if (!ups.some(shipped)) {
    out.push('No outside text, code or data ships with it, so it owes no other licence text.');
  } else {
    out.push("The material it ships from its sources owes no licence text beyond the archive's LICENSE.");
  }
  return out;
}

/**
 * row: a format 2 catalog row. catalog: the whole parsed catalog.json (for
 * display names of moved targets and hosts). Returns the file's text, ending
 * in one newline.
 */
export function renderProvenanceMd(row, catalog) {
  const src = row.source ?? {};
  const items = list(catalog?.items);
  const lines = [`# Provenance and credits: ${mdText(row.display_name ?? row.id)}`, '', GENERATED_MARK, '', mdText(creditLine(row)), '', mdText(originSentence(row)), ''];
  if (row.status && row.status !== 'active') lines.push(mdText(stubCreditLines(row, items)[0]), '');

  const ups = list(src.upstreams);
  if (ups.length) {
    lines.push('## Sources', '', ...sourcesTable(ups, row), '');
    const cites = citationLines(ups);
    if (cites.length) lines.push('How each source asks to be cited:', '', ...cites, '');
    if (has(src.changes)) lines.push(`Changes for Biorouter: ${sentence(src.changes)}`, '');
    if (src.maintained_here === true) lines.push('Maintained in this repository: the copy is not resynced from its source.', '');
    const plain = row.kind === 'bundle' ? Object.entries(row.components ?? {}).filter(([, c]) => plainCopied(c)) : [];
    if (plain.length) lines.push(`Components kept from these sources: ${plain.map(([f, c]) => `${code(f)} (${code(c.upstream_path)})`).join(', ')}.`, '');
  } else if (has(src.changes)) {
    lines.push(`Changes for Biorouter: ${sentence(src.changes)}`, '');
  }

  const own = ownSectionComponents(row);
  if (own.length) {
    lines.push('## Written for Biorouter', '');
    for (const [folder, comp] of own) lines.push(...componentSection(row, folder, comp));
  }

  const ideas = currentIdeas(row);
  if (ideas.length) lines.push('## Ideas', '', ...ideas.map((i) => `- ${ideaLine(i)}`), '');

  const data = list(src.data_and_services);
  if (data.length) lines.push('## Data and services', '', ...data.map((d) => `- ${dataLine(d)}`), '');

  const refs = list(src.references);
  if (refs.length) lines.push('## References', '', ...refs.map((r) => `- ${referenceLine(r)}`), '');

  lines.push('## Contributors', '');
  const people = list(row.contributors);
  if (people.length) {
    for (const c of people) lines.push(`- ${mdText(c.name) || 'not recorded'}${has(c.affiliation) ? `, ${mdText(c.affiliation)}` : ''}: ${mdText(c.role) || 'role not recorded'}`);
  } else {
    lines.push('None recorded.');
  }
  lines.push('');

  const earlier = earlierLines(row);
  if (earlier.length) lines.push('## Earlier versions', '', ...earlier, '');

  lines.push('## Licences', '', ...licenceLines(row), '', CURATED_BY, '');
  return lines.join('\n');
}
