#!/usr/bin/env node
// Checks catalog.json against the skill folders, the BAAM duplicate rules and
// the provenance rules (PV1 to PV13; the row rules live in lib/catalog-rules.mjs,
// the folder halves of PV7 to PV11 and PV13 here). Failures that exist today are
// accepted from catalog.json's baseline_violations and, for the provenance
// rules, from provenance-baseline.json.
//
//   node scripts/check-catalog.mjs                       # this repository alone
//   node scripts/check-catalog.mjs --jobs <jobs.json> --extensions <extensions.json>
//                                                        # plus the cross-kind rules (D1, D2, D4, G1)
//   node scripts/check-catalog.mjs --json                # machine-readable result
//   node scripts/check-catalog.mjs --scores 0.10         # print every look-alike pair at or above 0.10
//
// Exit code 0 when nothing fails (warnings allowed), 1 when something fails.
// No dependencies.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ALLOWED_LICENCES,
  DEFAULT_COMPONENT_SIMILARITY_THRESHOLD,
  DEFAULT_GENERIC_WORDS,
  DEFAULT_SIMILARITY_THRESHOLD,
  COMPONENT_STATUS_PATTERN,
  FORMAT1_NOTICE_LICENCES,
  FORMAT1_ORIGINS,
  JOB_PATTERN,
  ORIGINS,
  PROVENANCE_FORMAT,
  STATUS_PATTERN,
  applyBaseline,
  componentOfFile,
  containsCopyright,
  fixedTextProblems,
  folderProvenanceWanted,
  frontmatterCredits,
  licenceTokens,
  lookalikeScores,
  methodSkillWarnings,
  missingLicenceTexts,
  noticeSources,
  provenanceFormat,
  ruleD1,
  ruleD2,
  ruleD3,
  ruleD4,
  ruleD5,
  ruleD6,
  ruleG1,
  ruleProvenance,
  shippedSources,
  sourceKey,
  subjectId,
  upstreamNoticeMarker,
} from './lib/catalog-rules.mjs';
import {
  FOLDER_FILE_SUBJECTS,
  PROVENANCE_BASELINE_ROWS,
  PROVENANCE_BASELINE_ROWS_SHA256,
  PROVENANCE_BASELINE_SINCE,
  PROVENANCE_WORK_PACKAGES,
  isFolderFileSubject,
  readProvenanceBaseline,
} from './lib/provenance-baseline.mjs';

/** "PV7 notice, notice-apache, ...; PV8 frontmatter-licence; ...": what PROV-S4 may own, for a message. */
export function folderFileKinds() {
  return Object.entries(FOLDER_FILE_SUBJECTS).map(([rule, kinds]) => `${rule} ${kinds.join(', ')}`).join('; ');
}
import { PROVENANCE_FILE, renderProvenanceMd } from './lib/provenance-md.mjs';
import { REPO_ROOT, bundleComponents, discoverFolders, readSkillFile, skillFilesIn, listTree } from './lib/repo.mjs';
import { stubFiles } from './lib/stub.mjs';

// The licence lists and the SPDX reader moved to lib/catalog-rules.mjs, which
// landing shares; they are re-exported here so nothing that imports them breaks.
export { ALLOWED_LICENCES, licenceTokens };
/** Upstream licences whose text and copyright line a format 1 notice file had to carry. */
export const NOTICE_LICENCES = FORMAT1_NOTICE_LICENCES;
export const CATEGORIES = new Set(['core', 'developer', 'biomedical']);
const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SHA256 = /^[0-9a-f]{64}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
/** The rules a provenance baseline entry may name. */
export const PROVENANCE_BASELINE_RULE = /^PV(?:[1-9]|1[0-3])$/;
/** Any provenance rule, PV14 and later included (landing's): none may sit in catalog.json. */
export const PROVENANCE_RULE = /^PV\d+$/;

function cmpSemver(a, b) {
  const pa = a.split('.').map(Number);
  const pb = b.split('.').map(Number);
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] - pb[i];
  return 0;
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const fail = (rule, subject, message, refs = []) => ({ rule, subject, message, refs });
const list = (x) => (Array.isArray(x) ? x : []);
const str = (x) => typeof x === 'string' && x.trim().length > 0;

/**
 * Structural checks of one row's fields, independent of the folder. A format 2
 * row (its own source.format 2, or any row of a format 2 catalog) takes the
 * four format 2 origins and leaves its sources to PV6; a format 1 row is
 * checked as before.
 */
export function checkRowShape(row, catalogFormat = 1) {
  const out = [];
  const s = (sub, msg) => out.push(fail('row', `${sub}:${row.id}`, `${row.id}: ${msg}`, [`skill:${row.id}`]));
  if (!ID.test(row.id ?? '')) s('id', `id "${row.id}" is not kebab-case`);
  if (row.kind !== 'skill' && row.kind !== 'bundle') s('kind', `kind must be "skill" or "bundle"`);
  if (!CATEGORIES.has(row.category)) s('category', `category "${row.category}" is not core, developer or biomedical`);
  if (typeof row.display_name !== 'string' || !row.display_name.trim()) s('display-name', 'display_name is empty');
  if (!SEMVER.test(row.version ?? '')) s('version', `version "${row.version}" is not semver`);
  if (!STATUS_PATTERN.test(row.status ?? '')) s('status', `status "${row.status}" is not valid`);
  if (!Array.isArray(row.aliases)) s('aliases', 'aliases must be a list');
  if (!JOB_PATTERN.test(row.job ?? '')) s('job', `job "${row.job}" is not <domain>.<task>`);
  if (!Array.isArray(row.distinct_from)) s('distinct-from', 'distinct_from must be a list');
  else
    for (const d of row.distinct_from)
      if (!d || !d.id || typeof d.boundary !== 'string' || !d.boundary.trim())
        s('distinct-from', `a distinct_from entry needs an id and a non-empty boundary`);
  const expectedPath = row.category === 'biomedical' ? `bio-skills/${row.id}` : row.id;
  if (row.path !== expectedPath) s('path', `path must be "${expectedPath}" for a ${row.category} item`);
  const src = row.source ?? {};
  if (provenanceFormat(row, catalogFormat) === PROVENANCE_FORMAT) {
    // Every other source field is PV1 to PV6's (lib/catalog-rules.mjs).
    if (!ORIGINS.includes(src.origin)) s('origin', `source.origin "${src.origin}" is not ${ORIGINS.join(', ')}`);
    if (typeof src.maintained_here !== 'boolean') s('maintained-here', 'source.maintained_here must be true or false');
  } else {
    if (!FORMAT1_ORIGINS.includes(src.origin)) s('origin', `source.origin "${src.origin}" is not native, lab or adapted`);
    if (!Array.isArray(src.upstreams)) s('upstreams', 'source.upstreams must be a list');
    if (typeof src.maintained_here !== 'boolean') s('maintained-here', 'source.maintained_here must be true or false');
    if (src.origin === 'adapted' && !(src.upstreams ?? []).length) s('upstreams', 'an adapted item names its upstreams');
    for (const u of src.upstreams ?? []) {
      if (!u.repo || !u.licence) s('upstream', `an upstream needs repo and licence`);
      if (u.licence && !ALLOWED_LICENCES.has(u.licence)) s('upstream-licence', `upstream ${u.repo} is ${u.licence}, which may not be integrated`);
      if (u.commit && !/^[0-9a-f]{7,40}$/.test(u.commit)) s('upstream-commit', `upstream ${u.repo} commit "${u.commit}" is not a hex sha`);
    }
  }
  for (const t of licenceTokens(row.licence)) if (!ALLOWED_LICENCES.has(t)) s('licence', `licence "${row.licence}" contains ${t}, which is not allowed`);
  const rel = row.release ?? {};
  if (rel.tag !== `skill-${row.id}`) s('release-tag', `release.tag must be "skill-${row.id}"`);
  if (rel.asset !== `${row.id}.zip`) s('release-asset', `release.asset must be "${row.id}.zip"`);
  if (rel.sha256 != null && !SHA256.test(rel.sha256)) s('release-sha', 'release.sha256 is not a SHA-256');
  if (!Array.isArray(row.history) || !row.history.length) s('history', 'history is empty');
  else {
    for (let i = 1; i < row.history.length; i++)
      if (cmpSemver(row.history[i].version, row.history[i - 1].version) <= 0) s('history', 'history versions must increase');
    if (row.history.at(-1).version !== row.version) s('history', `the last history entry is ${row.history.at(-1).version}, not the row's ${row.version}`);
  }
  if (row.kind === 'bundle' && row.status === 'active' && (!row.components || typeof row.components !== 'object')) s('components', 'an active bundle lists its components');
  if (row.kind === 'skill' && row.components != null) s('components', 'a single skill has components: null');
  if (row.status === 'retired' && !row.retired?.reason) s('retired', 'a retired row says why in retired.reason');
  return out;
}

/** The ways a stub folder differs from the files it should hold, or none. */
function stubMismatches(abs, expected) {
  const tree = listTree(abs);
  const have = tree.files.map((x) => x.rel).sort();
  const want = Object.keys(expected).sort();
  if (have.join('\n') !== want.join('\n') || tree.dirs.length) return [`folder holds ${have.join(', ') || 'nothing'}`];
  return want.filter((name) => fs.readFileSync(path.join(abs, name), 'utf8') !== expected[name]).map((name) => `${name} differs`);
}

/**
 * PV7, the notice file, for every active row: the copyright line, the licence
 * text and (format 2) the Apache NOTICE of each source the notice file must
 * carry, and no top-level LICENSE in a format 2 folder (the archive builder
 * adds Biorouter's own there). Returns [subject, message] pairs.
 */
export function noticeProblems(abs, row, catalogFormat = 1) {
  const out = [];
  const id = row.id;
  const fmt2 = provenanceFormat(row, catalogFormat) === PROVENANCE_FORMAT;
  if (fmt2 && fs.existsSync(path.join(abs, 'LICENSE'))) {
    out.push([`reserved-licence:${id}`, 'the folder has its own top-level LICENSE; the archive builder adds Biorouter\'s LICENSE there, so name a source\'s licence file LICENSE-UPSTREAM']);
  }
  const sources = noticeSources(row, catalogFormat);
  const apache = fmt2 ? shippedSources(row, catalogFormat).filter((u) => u?.upstream_notice === true) : [];
  const wanted = [...sources, ...apache.filter((u) => !sources.includes(u))];
  const file = row.notice_file ? path.join(abs, row.notice_file) : null;
  if (!wanted.length) {
    if (file && !fs.existsSync(file)) out.push([`notice:${id}`, `notice_file ${row.notice_file} is missing from the folder`]);
    return out;
  }
  if (!file) {
    out.push([`notice:${id}`, `has ${wanted.map((u) => `${sourceKey(u)} (${u.licence})`).join(', ')} upstream material but no notice_file`]);
    return out;
  }
  if (!fs.existsSync(file)) {
    out.push([`notice:${id}`, `notice_file ${row.notice_file} is missing from the folder`]);
    return out;
  }
  const text = fs.readFileSync(file, 'utf8');
  const licences = [...new Set(sources.flatMap((u) => licenceTokens(u.licence)))];
  for (const lic of missingLicenceTexts(text, licences)) {
    out.push([`notice-licence:${id}:${lic}`, `${row.notice_file} lacks the ${lic} licence text${lic === 'BSD-3-Clause' ? ' (with its non-endorsement clause)' : ''}`]);
  }
  // One failure per repository. A format 1 upstream under an old notice
  // licence (MIT, BSD, ISC, BlueOak, CC-BY) must record its copyright line, as
  // the format 1 rule always asked; in format 2 a null copyright is PV6's to
  // judge (it needs a copyright_note), so PV7 has no line to look for.
  const byRepo = new Map();
  for (const u of sources) {
    const key = sourceKey(u);
    if (!byRepo.has(key)) byRepo.set(key, { lines: [], unrecorded: [] });
    if (str(u?.copyright)) byRepo.get(key).lines.push(u.copyright);
    else if (!fmt2 && FORMAT1_NOTICE_LICENCES.has(u?.licence)) byRepo.get(key).unrecorded.push(u.licence);
  }
  for (const [key, { lines, unrecorded }] of byRepo) {
    const missing = [...new Set(lines)].filter((c) => !containsCopyright(text, c));
    const said = [];
    if (missing.length) said.push(`${row.notice_file} lacks the copyright line of ${key}: ${missing.map((c) => `"${c}"`).join(', ')}`);
    if (unrecorded.length) said.push(`the row records no copyright line for ${key}, whose ${[...new Set(unrecorded)].join(', ')} licence names its holder, so ${row.notice_file} cannot be checked for it`);
    if (said.length) out.push([`notice-copyright:${id}:${key}`, said.join('; ')]);
  }
  const marked = new Set();
  for (const u of apache) {
    const key = sourceKey(u);
    if (marked.has(key)) continue;
    marked.add(key);
    const marker = upstreamNoticeMarker(u.repo ?? key);
    if (!text.includes(marker)) out.push([`notice-apache:${id}:${key}`, `${key} publishes a NOTICE file (upstream_notice), but ${row.notice_file} has no "${marker}" section carrying it`]);
  }
  return out;
}

/** The files of a format 2 row's folder that PV13 reads: the notice file, every SKILL.md and PROVENANCE.md. */
function fixedTextFiles(abs, row, skillFiles) {
  const rels = [...new Set([row.notice_file, ...skillFiles.map((s) => s.rel), PROVENANCE_FILE].filter(Boolean))];
  return rels.filter((rel) => fs.existsSync(path.join(abs, rel)));
}

/**
 * Folder, frontmatter, version, licence, notice and stub checks for one row,
 * and the folder halves of the provenance rules: PV7 for every active row;
 * PV8's front matter part, PV9, PV10, PV11's file part and PV13's file part
 * for format 2 rows. `provenance` is the parsed provenance-baseline.json: a
 * row whose PV9 entry defers its folder files keeps today's stub.
 */
export function checkRowFolder(root, row, catalog, provenance = readProvenanceBaseline(root)) {
  const out = [];
  const ref = `skill:${row.id}`;
  const id = row.id;
  const f = (rule, sub, msg) => out.push(fail(rule, `${sub}:${row.id}`, `${row.id}: ${msg}`, [ref]));
  const pv = (rule, subject, msg) => out.push(fail(rule, subject, `${id}: ${msg}`, [ref]));
  const abs = path.join(root, row.path ?? '');
  if (!row.path || !fs.existsSync(abs)) {
    f('folder', 'missing', `folder ${row.path} does not exist`);
    return out;
  }
  const catalogFormat = catalog?.format ?? 1;
  const fmt2 = provenanceFormat(row, catalogFormat) === PROVENANCE_FORMAT;
  const active = row.status === 'active';
  if (!active) {
    // A merged or retired item's folder is exactly its generated stub: with
    // its credit lines once its folder files are due, today's text until then.
    const wanted = folderProvenanceWanted(row, { catalogFormat, baseline: provenance });
    let expected;
    try {
      expected = stubFiles(row, catalog, { provenance: wanted });
    } catch (e) {
      f('stub', 'stub', e.message);
      return out;
    }
    const mismatches = stubMismatches(abs, expected);
    if (mismatches.length && mismatches[0].startsWith('folder holds')) {
      f('stub', 'stub', `${mismatches[0]}; a ${row.status} item holds only its generated stub (run node scripts/write-stubs.mjs)`);
    } else {
      for (const m of mismatches) f('stub', 'stub', `${m.replace(/ differs$/, '')} differs from the generated stub (run node scripts/write-stubs.mjs)`);
    }
    // PV9: the stub with its credit lines, whether or not the row is deferred,
    // so a deferral whose stub is already written is stale.
    if (fmt2) {
      let full = null;
      try {
        full = stubFiles(row, catalog, { provenance: true });
      } catch (e) {
        pv('PV9', `folder:${id}`, `the stub generator failed: ${e.message}`);
      }
      const m = full ? stubMismatches(abs, full) : [];
      if (m.length) pv('PV9', `folder:${id}`, `the folder is not its format 2 stub with credit lines (${m.join('; ')}); node scripts/write-stubs.mjs writes it once the row's folder files are due`);
    }
    return out;
  }
  const skillFiles = [];
  if (row.kind === 'skill') {
    const sk = readSkillFile(path.join(abs, 'SKILL.md'));
    if (!sk.exists) f('folder', 'skill-md', 'has no SKILL.md');
    else if (!sk.ok) f('frontmatter', 'frontmatter', 'SKILL.md has no frontmatter');
    else {
      if (sk.frontmatter.name !== row.id) f('frontmatter', 'name', `frontmatter name is "${sk.frontmatter.name}", not the id`);
      skillFiles.push({ rel: 'SKILL.md', ...sk });
    }
  } else {
    if (path.posix.basename(row.path) !== row.id) f('folder', 'root', `a bundle's root folder is its id`);
    const comps = bundleComponents(root, row.path);
    const listed = row.components ?? {};
    const onDisk = new Set(comps.map((c) => c.folder));
    for (const c of comps) {
      const entry = listed[c.folder];
      if (!entry) {
        f('components', `unlisted-${c.folder}`, `component folder ${c.folder} has no entry in components`);
        continue;
      }
      if (entry.status !== 'active') f('components', `inactive-${c.folder}`, `component ${c.folder} is ${entry.status} but its folder is still there`);
      if (!c.ok) f('frontmatter', `frontmatter-${c.folder}`, `${c.folder}/SKILL.md has no frontmatter`);
      else if (c.frontmatter.name !== entry.name)
        f('frontmatter', `component-name-${c.folder}`, `${c.folder}/SKILL.md is named "${c.frontmatter.name}", but the row pins "${entry.name}" (a component name never moves)`);
    }
    for (const [folder, entry] of Object.entries(listed)) {
      if (entry.status === 'active' && !onDisk.has(folder)) f('components', `missing-${folder}`, `active component ${folder} has no folder`);
      if (!COMPONENT_STATUS_PATTERN.test(entry.status ?? '')) f('components', `status-${folder}`, `component ${folder} has status "${entry.status}"`);
      if (entry.status === 'active' && !JOB_PATTERN.test(entry.job ?? '')) f('components', `job-${folder}`, `component ${folder} has no valid job`);
    }
    for (const s of skillFilesIn(root, row.path)) skillFiles.push(s);
    // Optional package record (plan 1.6; the install probe of 2026-11-22 showed
    // the installed id, path and files are the same with and without it). When
    // present it must agree with the row.
    const pkgPath = path.join(abs, 'biorouter-package.json');
    if (fs.existsSync(pkgPath)) {
      let pkg = null;
      try {
        pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      } catch {
        f('package', 'package-json', 'biorouter-package.json is not valid JSON');
      }
      if (pkg && (pkg.id !== row.id || pkg.version !== row.version || pkg.displayName !== row.display_name))
        f('package', 'package-json', `biorouter-package.json says ${JSON.stringify({ id: pkg.id, displayName: pkg.displayName, version: pkg.version })}; the row says ${JSON.stringify({ id: row.id, displayName: row.display_name, version: row.version })}`);
    }
  }
  for (const s of skillFiles) {
    const fm = s.frontmatter ?? {};
    const declared = fm.metadata && typeof fm.metadata === 'object' ? fm.metadata.version : undefined;
    // A folder released before the catalog existed carries no version; that is 1.0.0.
    const effective = declared ?? (row.version === '1.0.0' ? '1.0.0' : undefined);
    if (effective !== row.version)
      f('version', `version-${s.rel}`, `${s.rel} has metadata.version ${declared ?? '(none)'}, the row says ${row.version}`);
    if (!fmt2) {
      if (fm.license !== row.licence) f('licence', `licence-${s.rel}`, `${s.rel} declares license "${fm.license}", the row says "${row.licence}"`);
      continue;
    }
    // PV8: a component file declares its component's licence, else the row's.
    const folder = componentOfFile(row, s.rel);
    const own = folder ? row.components[folder]?.licence : null;
    const want = own ?? row.licence;
    if (fm.license !== want)
      pv('PV8', `frontmatter-licence:${id}:${s.rel}`, `${s.rel} declares license "${fm.license}"; ${own ? `its component ${folder}` : 'the row'} says "${want}"`);
  }

  // PV7, the notice file.
  for (const [subject, msg] of noticeProblems(abs, row, catalogFormat)) pv('PV7', subject, msg);
  if (!fmt2) return out;

  // PV9: PROVENANCE.md is the generator's, whether or not the row is deferred.
  let expected = null;
  try {
    expected = renderProvenanceMd(row, catalog);
  } catch (e) {
    pv('PV9', `folder:${id}`, `the ${PROVENANCE_FILE} generator failed: ${e.message}`);
  }
  if (expected != null) {
    const p = path.join(abs, PROVENANCE_FILE);
    if (!fs.existsSync(p)) pv('PV9', `folder:${id}`, `has no ${PROVENANCE_FILE}; node scripts/render-readme.mjs writes it once the row's folder files are due`);
    else if (fs.readFileSync(p, 'utf8') !== expected) pv('PV9', `folder:${id}`, `${PROVENANCE_FILE} differs from the catalog (run node scripts/render-readme.mjs)`);
  }

  // PV10: each SKILL.md carries the generated credits.
  const off = [];
  for (const s of skillFiles) {
    const meta = s.frontmatter?.metadata && typeof s.frontmatter.metadata === 'object' ? s.frontmatter.metadata : {};
    const want = frontmatterCredits(row, s.rel);
    const keys = ['origin', 'credit', 'curated_by'].filter((k) => meta[k] !== want[k]);
    if (keys.length) off.push(`${s.rel} (${keys.map((k) => `metadata.${k}`).join(', ')})`);
  }
  if (off.length) pv('PV10', `frontmatter:${id}`, `front matter credits differ from the catalog in ${off.join(', ')}; node scripts/render-readme.mjs writes them once the row's folder files are due`);

  // PV11: the files a component lists as written for Biorouter exist.
  if (row.kind === 'bundle') {
    for (const [folder, comp] of Object.entries(row.components ?? {})) {
      if (comp?.status !== 'active') continue;
      for (const w of list(comp.written_for_biorouter)) {
        const rel = String(w?.path ?? '');
        const norm = path.posix.normalize(rel);
        const inside = str(rel) && !path.posix.isAbsolute(rel) && norm === rel && !norm.startsWith('../') && norm !== '..';
        if (!inside || !fs.existsSync(path.join(abs, folder, rel)) || !fs.statSync(path.join(abs, folder, rel)).isFile()) {
          pv('PV11', `written-file:${id}/${folder}:${rel}`, `component ${folder} lists ${rel || '(no path)'} under written_for_biorouter, but ${inside ? 'that file is not in the folder' : 'the path is not a plain path inside the component folder'}`);
        }
      }
    }
  }

  // PV13: no file states a fixed text differently from its constant.
  const allowed = list(row.source?.upstreams).map((u) => u?.copyright).filter(str);
  for (const rel of fixedTextFiles(abs, row, skillFiles)) {
    const problems = fixedTextProblems(fs.readFileSync(path.join(abs, rel), 'utf8'), { allowed });
    if (problems.length) {
      pv('PV13', `fixed-text:${id}:${rel}`, `${rel} states a fixed text differently: ${problems.map((p) => `line ${p.line} "${p.text}" (write "${p.expected}")`).join('; ')}`);
    }
  }
  return out;
}

/**
 * PV10's warnings for a format 2 active row: older provenance keys in a
 * SKILL.md's metadata that the generated credits replace.
 */
export function frontmatterWarnings(root, row, catalog) {
  if (row.status !== 'active' || !row.path) return [];
  if (provenanceFormat(row, catalog?.format ?? 1) !== PROVENANCE_FORMAT) return [];
  const abs = path.join(root, row.path);
  if (!fs.existsSync(abs)) return [];
  const files = row.kind === 'skill' ? [{ rel: 'SKILL.md', ...readSkillFile(path.join(abs, 'SKILL.md')) }] : skillFilesIn(root, row.path);
  const repos = list(row.source?.upstreams).flatMap((u) => [u?.repo, u?.url]).filter(str).map((x) => x.toLowerCase());
  const out = [];
  for (const s of files) {
    const meta = s.frontmatter?.metadata && typeof s.frontmatter.metadata === 'object' ? s.frontmatter.metadata : {};
    for (const k of ['upstream_licence', 'upstream_author', 'source'])
      if (meta[k] !== undefined) out.push(`${row.id}: ${s.rel} metadata.${k} is an older provenance key; the catalog and metadata.credit carry it now`);
    if (meta.upstream !== undefined && !repos.some((r) => String(meta.upstream).toLowerCase().includes(r)))
      out.push(`${row.id}: ${s.rel} metadata.upstream "${meta.upstream}" names no upstream of the row`);
  }
  return out;
}

/** Warnings that never fail: the brand spelling a re-release should fix. */
export function brandWarnings(root, row) {
  if (row.status !== 'active' || !row.path) return [];
  const files = row.kind === 'skill' ? [{ rel: 'SKILL.md', ...readSkillFile(path.join(root, row.path, 'SKILL.md')) }] : skillFilesIn(root, row.path);
  const n = files.filter((s) => /BioRouter/.test(s.text ?? '')).length;
  return n ? [`${row.id}: ${n} SKILL.md file(s) spell "BioRouter"; the brand is "Biorouter"`] : [];
}

/** The catalog rows as rule items, plus their components. */
export function skillItems(root, catalog) {
  const items = [];
  const bodies = [];
  for (const row of catalog.items ?? []) {
    const ref = `skill:${row.id}`;
    const text = [row.display_name, row.summary ?? '', ...(row.keywords ?? [])];
    if (row.kind === 'skill' && row.status === 'active') {
      const sk = readSkillFile(path.join(root, row.path, 'SKILL.md'));
      if (sk.frontmatter?.description) text.push(sk.frontmatter.description);
      if (sk.exists) bodies.push({ ref, id: row.id, body: sk.body });
    }
    items.push({
      ref, catalog: 'skills', kind: row.kind, id: row.id, display_name: row.display_name,
      status: row.status, aliases: row.aliases ?? [], job: row.job, distinct_from: row.distinct_from ?? [], text,
    });
    if (row.kind === 'bundle' && row.components) {
      const comps = row.status === 'active' ? new Map(bundleComponents(root, row.path).map((c) => [c.folder, c])) : new Map();
      for (const [folder, entry] of Object.entries(row.components)) {
        const c = comps.get(folder);
        items.push({
          ref: `component:${row.id}/${folder}`, catalog: 'skills', kind: 'component', id: `${row.id}/${folder}`,
          name: entry.name ?? folder, display_name: entry.name ?? folder,
          status: row.status === 'active' ? entry.status : row.status === 'retired' ? 'retired' : entry.status,
          aliases: [], job: entry.job, distinct_from: entry.distinct_from ?? [], parent: ref,
          text: [entry.name ?? folder, folder.replace(/-/g, ' '), c?.frontmatter?.description ?? ''],
        });
      }
    }
  }
  return { items, bodies };
}

/** The extension catalog's rows and bundled skills as rule items. */
export function extensionItems(extCatalog) {
  const items = [];
  for (const row of extCatalog?.items ?? []) {
    const ref = `extension:${row.id}`;
    items.push({
      ref, catalog: 'extensions', kind: 'extension', id: row.id, display_name: row.display_name,
      status: row.status, aliases: row.aliases ?? [], job: row.job, distinct_from: row.distinct_from ?? [],
      text: [row.display_name, row.summary ?? '', ...(row.keywords ?? [])],
    });
    for (const b of row.bundled_skills ?? []) {
      items.push({
        ref: `bundled:${row.id}/${b.name}`, catalog: 'extensions', kind: 'bundled-skill', id: b.name,
        display_name: b.name, status: row.status, aliases: [], job: b.job, distinct_from: [], parent: ref,
        method_skill: b.method_skill ?? null, text: [b.name],
      });
    }
  }
  return items;
}

/** The baseline's template lines (scripts/fixtures/template-lines.json), as a predicate for D6. */
export function templatePredicate(root) {
  const p = path.join(root, 'scripts/fixtures/template-lines.json');
  if (!fs.existsSync(p)) return () => false;
  const set = new Set(JSON.parse(fs.readFileSync(p, 'utf8')).lines);
  return (line) => set.has(crypto.createHash('sha256').update(line).digest('hex').slice(0, 16));
}

/** The SHA-256 of a sorted id list joined with newlines: what PROVENANCE_BASELINE_ROWS_SHA256 freezes. */
export function provenanceRowsDigest(ids) {
  return crypto.createHash('sha256').update([...ids].sort().join('\n')).digest('hex');
}

/**
 * The guard of the provenance baseline. Only the rows that existed when the
 * provenance rules landed may be baselined, every entry is a dated PV1 to PV13
 * entry owned by PROV-S1 or PROV-S4 (PV9 and PV10, the folder files waiting for
 * a release, by PROV-S4 alone, and PROV-S4 owns nothing but folder files:
 * FOLDER_FILE_SUBJECTS), and catalog.json, which landing mirrors, holds
 * no provenance entry. Returns { problems, entries }: the guard's failures and
 * the entries that may be applied. A refused entry is never applied, so the
 * failure it named shows too.
 */
export function provenanceBaselineProblems(provenance, catalog, frozenRows = { count: PROVENANCE_BASELINE_ROWS, sha256: PROVENANCE_BASELINE_ROWS_SHA256 }, { extensions = null } = {}) {
  const problems = [];
  const g = (subject, message) => problems.push(fail('provenance-baseline', subject, message));
  const rows = list(provenance?.rows);
  const entries = list(provenance?.baseline_violations);
  if (rows.length || entries.length) {
    const canonical = [...new Set(rows.filter((r) => typeof r === 'string'))].sort();
    if (canonical.length !== rows.length || canonical.join('\n') !== rows.join('\n')) {
      g('rows', 'provenance-baseline.json rows must be a sorted list of unique row ids');
    } else if (rows.length !== frozenRows.count || provenanceRowsDigest(rows) !== frozenRows.sha256) {
      g('rows', `provenance-baseline.json rows (${rows.length} ids) are not the ${frozenRows.count} rows frozen when the provenance rules landed; a row added later passes every provenance rule and is never baselined`);
    }
  }
  const known = new Set(rows);
  const valid = [];
  for (const b of entries) {
    const p = [];
    if (!PROVENANCE_BASELINE_RULE.test(String(b?.rule ?? ''))) p.push(`rule "${b?.rule}" is not one of PV1 to PV13`);
    if (!Object.hasOwn(PROVENANCE_WORK_PACKAGES, String(b?.wp ?? ''))) p.push(`work package "${b?.wp}" is not ${Object.keys(PROVENANCE_WORK_PACKAGES).join(' or ')}`);
    else if ((b.rule === 'PV9' || b.rule === 'PV10') && b.wp !== 'PROV-S4') p.push(`${b.rule} entries belong to PROV-S4 (folder files that wait for the item's next release)`);
    else if (b.wp === 'PROV-S4' && !isFolderFileSubject(b.rule, b.subject)) p.push(`PROV-S4 owns folder files only (${folderFileKinds()}); ${b.rule} ${String(b.subject ?? '').split(':')[0]} is a row rule, so fix the row`);
    if (!DATE.test(String(b?.since ?? '')) || b.since < PROVENANCE_BASELINE_SINCE) p.push(`since "${b?.since}" is not a date on or after ${PROVENANCE_BASELINE_SINCE}`);
    const rowId = subjectId(b?.subject);
    if (!rowId || !known.has(rowId)) p.push(`${rowId ? `row ${rowId}` : 'its subject names no row and'} is not among the rows frozen when the provenance rules landed`);
    if (p.length) g(`entry:${b?.rule}::${b?.subject}`, `provenance-baseline.json lists ${b?.rule} ${b?.subject}: ${p.join('; ')}`);
    else valid.push(b);
  }
  for (const b of list(catalog?.baseline_violations)) {
    if (PROVENANCE_RULE.test(String(b?.rule ?? ''))) {
      g(`catalog-entry:${b.rule}::${b.subject}`, `catalog.json's baseline_violations lists ${b.rule} ${b.subject}; provenance entries belong in provenance-baseline.json, because catalog.json is mirrored into landing`);
    }
  }
  // The extension catalog's provenance entries are never applied here: this
  // check runs the provenance rules on skill rows only, and a skill row's
  // entries belong in provenance-baseline.json, behind the guard above. An
  // entry for one of landing's own extension rows is landing's to apply and is
  // passed over; any other provenance entry there is refused, so the extension
  // catalog cannot baseline a skill row the guard would refuse.
  const skillIds = new Set(list(catalog?.items).map((r) => r?.id));
  const extensionIds = new Set(list(extensions?.items).map((r) => r?.id));
  for (const b of list(extensions?.baseline_violations)) {
    if (!PROVENANCE_RULE.test(String(b?.rule ?? ''))) continue;
    const rowId = subjectId(b?.subject);
    if (rowId && extensionIds.has(rowId) && !skillIds.has(rowId)) continue;
    const names = rowId && skillIds.has(rowId) ? `names the skill row ${rowId}` : 'names no row of the extension catalog';
    g(`extensions-entry:${b?.rule}::${b?.subject}`, `the extension catalog's baseline_violations lists ${b?.rule} ${b?.subject}, which ${names}; a skill row's provenance entries belong in provenance-baseline.json, and only the rows frozen when the provenance rules landed may have them`);
  }
  return { problems, entries: valid };
}

/** The entries of the extension catalog's baseline this check applies: every one but the provenance entries. */
export function extensionBaselineEntries(extensions) {
  return list(extensions?.baseline_violations).filter((b) => !PROVENANCE_RULE.test(String(b?.rule ?? '')));
}

export function runCheck({
  root = REPO_ROOT, catalog, builtins, jobs = null, extensions = null,
  provenance = readProvenanceBaseline(root),
  frozenRows = { count: PROVENANCE_BASELINE_ROWS, sha256: PROVENANCE_BASELINE_ROWS_SHA256 },
} = {}) {
  const errors = [];
  const warnings = [];
  const raw = [];
  const catalogFormat = catalog?.format;
  if (catalogFormat !== 1 && catalogFormat !== PROVENANCE_FORMAT) raw.push(fail('row', 'format:catalog', 'catalog.json must have "format": 1 or 2'));
  const rows = catalog?.items ?? [];

  // Ids are unique, and every folder has exactly one row.
  const seen = new Map();
  for (const r of rows) {
    if (seen.has(r.id)) raw.push(fail('row', `duplicate:${r.id}`, `two rows have the id ${r.id}`));
    seen.set(r.id, r);
  }
  const folders = discoverFolders(root);
  const byPath = new Map(rows.map((r) => [r.path, r]));
  for (const f of folders) if (!byPath.has(f.path)) raw.push(fail('folder', `unlisted:${f.path}`, `folder ${f.path} has no catalog row`));
  for (const r of rows) {
    raw.push(...checkRowShape(r, catalogFormat));
    raw.push(...checkRowFolder(root, r, catalog, provenance));
    warnings.push(...brandWarnings(root, r));
    warnings.push(...frontmatterWarnings(root, r, catalog));
  }

  // The provenance row rules (PV1 to PV6, PV8, PV11 to PV13).
  const prov = ruleProvenance(rows, { catalogFormat: catalogFormat === PROVENANCE_FORMAT ? PROVENANCE_FORMAT : 1, catalog: 'skills' });
  raw.push(...prov.failures);
  warnings.push(...prov.warnings);

  // The duplicate rules.
  const threshold = jobs?.similarity_threshold ?? DEFAULT_SIMILARITY_THRESHOLD;
  const genericWords = jobs?.generic_words ?? DEFAULT_GENERIC_WORDS;
  const componentThreshold = jobs?.component_similarity_threshold ?? DEFAULT_COMPONENT_SIMILARITY_THRESHOLD;
  if (jobs && (jobs.similarity_threshold !== DEFAULT_SIMILARITY_THRESHOLD ||
      jobs.component_similarity_threshold !== DEFAULT_COMPONENT_SIMILARITY_THRESHOLD ||
      JSON.stringify(jobs.generic_words) !== JSON.stringify([...DEFAULT_GENERIC_WORDS]))) {
    raw.push(fail('jobs', 'rules-drift', `jobs.json similarity_threshold, component_similarity_threshold or generic_words differ from scripts/lib/catalog-rules.mjs; change both together`));
  }
  const builtinNames = { skills: builtins?.skills ?? [], bundles: builtins?.bundles ?? [], extensions: builtins?.extensions ?? [] };
  const { items: sItems, bodies } = skillItems(root, catalog);
  const eItems = extensions ? extensionItems(extensions) : [];
  const all = [...sItems, ...eItems];
  const rowsOnly = all.filter((i) => i.kind !== 'component');

  raw.push(...ruleD1(all, { builtinJobs: jobs?.builtin ?? [] }));
  const ms = methodSkillWarnings(all);
  raw.push(...ms.failures);
  warnings.push(...ms.warnings);
  // A retired item's id stays reserved (D2), with the one written exception the
  // landing check also makes: a retired row may pass its name to the active
  // item in the other catalog that took over its job (UCSFHPCAgent's name to
  // the ucsf-hpc skill), stated as retired.name_passes_to on the retired row.
  const rowOf = (ref) => {
    const [kind, id] = ref.split(':');
    if (kind === 'extension') return (extensions?.items ?? []).find((r) => r.id === id) ?? null;
    if (kind === 'skill') return rows.find((r) => r.id === id) ?? null;
    return null;
  };
  raw.push(
    ...ruleD2(all, builtinNames).filter((f) => {
      const owners = [...new Set(f.refs)];
      if (owners.length !== 2) return true;
      const [a, b] = owners.map(rowOf);
      if (!a || !b) return true;
      const passes = (old, ref) => old.status !== 'active' && old.retired?.name_passes_to === ref;
      return !(passes(a, owners[1]) && b.status === 'active') && !(passes(b, owners[0]) && a.status === 'active');
    })
  );
  raw.push(...ruleD3(rowsOnly.filter((i) => i.kind !== 'bundled-skill'), { threshold, genericWords }));
  raw.push(...ruleD4(all, builtinNames));
  raw.push(...ruleD5(all, { threshold: componentThreshold, genericWords, builtins: builtinNames }));
  raw.push(...ruleD6(bodies.filter((b) => seen.get(b.id)?.status === 'active'), { isTemplate: templatePredicate(root) }));
  if (jobs) {
    const g = ruleG1(all, jobs.required ?? []);
    raw.push(...g.failures);
    warnings.push(...g.warnings);
  }

  // The baselines: catalog.json's and the extension catalog's (no provenance
  // entry of a skill row may sit in either) and provenance-baseline.json's,
  // after its guard.
  const guard = provenanceBaselineProblems(provenance, catalog, frozenRows, { extensions });
  const catalogBaseline = list(catalog?.baseline_violations).filter((b) => !PROVENANCE_RULE.test(String(b?.rule ?? '')));
  const baseline = [...catalogBaseline, ...guard.entries, ...extensionBaselineEntries(extensions)];
  const done = [...(catalog?.done_work_packages ?? []), ...list(provenance?.done_work_packages), ...(extensions?.done_work_packages ?? [])];
  // Cross-kind entries (they need jobs.json or the extension catalog) only
  // apply when those were given.
  const relevant = baseline.filter((b) => (extensions || jobs) || !b.cross_kind);
  const result = applyBaseline(raw, relevant, done);
  errors.push(...result.errors);
  // The guard's own failures are never baselined.
  errors.push(...guard.problems);
  return { errors, warnings, accepted: result.accepted, raw, threshold };
}

function parseArgs(argv) {
  const args = { root: REPO_ROOT, json: false, scores: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') args.json = true;
    else if (a === '--root') args.root = path.resolve(argv[++i]);
    else if (a === '--catalog') args.catalog = path.resolve(argv[++i]);
    else if (a === '--jobs') args.jobs = path.resolve(argv[++i]);
    else if (a === '--extensions') args.extensions = path.resolve(argv[++i]);
    else if (a === '--builtins') args.builtins = path.resolve(argv[++i]);
    else if (a === '--scores') args.scores = Number(argv[++i]);
    else if (a === '--help' || a === '-h') args.help = true;
    else throw new Error(`unknown argument ${a}`);
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    const lines = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1);
    const header = lines.slice(0, lines.findIndex((l) => !l.startsWith('//')));
    console.log(header.map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
    return 0;
  }
  const catalog = readJson(args.catalog ?? path.join(args.root, 'catalog.json'));
  const builtins = readJson(args.builtins ?? path.join(args.root, 'builtin-skill-names.json'));
  const jobs = args.jobs ? readJson(args.jobs) : null;
  const extensions = args.extensions ? readJson(args.extensions) : null;
  if (args.scores != null) {
    const { items } = skillItems(args.root, catalog);
    const all = [...items, ...(extensions ? extensionItems(extensions) : [])].filter((i) => i.kind !== 'component' && i.kind !== 'bundled-skill');
    for (const p of lookalikeScores(all, { genericWords: jobs?.generic_words }).filter((p) => p.score >= args.scores))
      console.log(`${p.score.toFixed(3)}  ${p.a.ref}  ${p.b.ref}`);
    return 0;
  }
  const res = runCheck({ root: args.root, catalog, builtins, jobs, extensions });
  if (args.json) {
    console.log(JSON.stringify({ ok: res.errors.length === 0, errors: res.errors, warnings: res.warnings, accepted: res.accepted }, null, 2));
  } else {
    const active = (catalog.items ?? []).filter((r) => r.status === 'active').length;
    console.log(`catalog: ${(catalog.items ?? []).length} rows, ${active} active; look-alike threshold ${res.threshold}`);
    if (res.accepted.length) {
      const byWp = {};
      for (const a of res.accepted) byWp[a.wp] = (byWp[a.wp] ?? 0) + 1;
      console.log(`baseline violations still open: ${res.accepted.length} (${Object.entries(byWp).map(([k, v]) => `${k} ${v}`).join(', ')})`);
    }
    const brand = res.warnings.filter((w) => w.includes('"BioRouter"'));
    const other = res.warnings.filter((w) => !w.includes('"BioRouter"'));
    for (const w of other) console.log(`warning: ${w}`);
    if (brand.length) console.log(`warning: ${brand.length} active items still spell "BioRouter" in a SKILL.md`);
    for (const e of res.errors) console.log(`FAIL [${e.rule}] ${e.message}`);
    console.log(res.errors.length ? `${res.errors.length} failure(s)` : 'ok');
  }
  return res.errors.length ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().then((code) => process.exit(code), (e) => {
    console.error(e.stack || e.message);
    process.exit(2);
  });
}
