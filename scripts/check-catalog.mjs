#!/usr/bin/env node
// Checks catalog.json against the skill folders and the BAAM duplicate rules.
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
  DEFAULT_COMPONENT_SIMILARITY_THRESHOLD,
  DEFAULT_GENERIC_WORDS,
  DEFAULT_SIMILARITY_THRESHOLD,
  COMPONENT_STATUS_PATTERN,
  JOB_PATTERN,
  STATUS_PATTERN,
  applyBaseline,
  lookalikeScores,
  methodSkillWarnings,
  ruleD1,
  ruleD2,
  ruleD3,
  ruleD4,
  ruleD5,
  ruleD6,
  ruleG1,
} from './lib/catalog-rules.mjs';
import { REPO_ROOT, bundleComponents, discoverFolders, readSkillFile, skillFilesIn, listTree } from './lib/repo.mjs';
import { stubFiles } from './lib/stub.mjs';

export const ALLOWED_LICENCES = new Set([
  'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'BlueOak-1.0.0', 'CC0-1.0', 'CC-BY-4.0',
]);
// Upstream licences whose text and copyright line must travel inside the zip.
export const NOTICE_LICENCES = new Set(['MIT', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'BlueOak-1.0.0', 'CC-BY-4.0']);
export const CATEGORIES = new Set(['core', 'developer', 'biomedical']);
export const ORIGINS = new Set(['native', 'lab', 'adapted']);
const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SHA256 = /^[0-9a-f]{64}$/;

function cmpSemver(a, b) {
  const pa = a.split('.').map(Number);
  const pb = b.split('.').map(Number);
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] - pb[i];
  return 0;
}

export function licenceTokens(expr) {
  return String(expr ?? '')
    .replace(/[()]/g, ' ')
    .split(/\s+(?:AND|OR|WITH)\s+|\s+/)
    .filter(Boolean)
    .filter((t) => t !== 'AND' && t !== 'OR');
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const fail = (rule, subject, message, refs = []) => ({ rule, subject, message, refs });

/** Structural checks of one row's fields, independent of the folder. */
export function checkRowShape(row) {
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
  if (!ORIGINS.has(src.origin)) s('origin', `source.origin "${src.origin}" is not native, lab or adapted`);
  if (!Array.isArray(src.upstreams)) s('upstreams', 'source.upstreams must be a list');
  if (typeof src.maintained_here !== 'boolean') s('maintained-here', 'source.maintained_here must be true or false');
  if (src.origin === 'adapted' && !(src.upstreams ?? []).length) s('upstreams', 'an adapted item names its upstreams');
  for (const u of src.upstreams ?? []) {
    if (!u.repo || !u.licence) s('upstream', `an upstream needs repo and licence`);
    if (u.licence && !ALLOWED_LICENCES.has(u.licence)) s('upstream-licence', `upstream ${u.repo} is ${u.licence}, which may not be integrated`);
    if (u.commit && !/^[0-9a-f]{7,40}$/.test(u.commit)) s('upstream-commit', `upstream ${u.repo} commit "${u.commit}" is not a hex sha`);
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

/** Folder, frontmatter, version, licence, notice and stub checks for one row. */
export function checkRowFolder(root, row, catalog) {
  const out = [];
  const ref = `skill:${row.id}`;
  const f = (rule, sub, msg) => out.push(fail(rule, `${sub}:${row.id}`, `${row.id}: ${msg}`, [ref]));
  const abs = path.join(root, row.path ?? '');
  if (!row.path || !fs.existsSync(abs)) {
    f('folder', 'missing', `folder ${row.path} does not exist`);
    return out;
  }
  const active = row.status === 'active';
  if (!active) {
    // A merged or retired item's folder is exactly its generated stub.
    let expected;
    try {
      expected = stubFiles(row, catalog);
    } catch (e) {
      f('stub', 'stub', e.message);
      return out;
    }
    const tree = listTree(abs);
    const have = tree.files.map((x) => x.rel).sort();
    const want = Object.keys(expected).sort();
    if (have.join('\n') !== want.join('\n') || tree.dirs.length) {
      f('stub', 'stub', `folder holds ${have.join(', ') || 'nothing'}; a ${row.status} item holds only its generated stub (run node scripts/write-stubs.mjs)`);
    } else {
      for (const name of want)
        if (fs.readFileSync(path.join(abs, name), 'utf8') !== expected[name])
          f('stub', 'stub', `${name} differs from the generated stub (run node scripts/write-stubs.mjs)`);
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
    if (fm.license !== row.licence) f('licence', `licence-${s.rel}`, `${s.rel} declares license "${fm.license}", the row says "${row.licence}"`);
  }
  const needsNotice = (row.source?.upstreams ?? []).filter((u) => NOTICE_LICENCES.has(u.licence));
  if (needsNotice.length) {
    if (!row.notice_file) f('notice', 'notice', `has ${needsNotice.map((u) => `${u.repo} (${u.licence})`).join(', ')} upstream text but no notice_file`);
    else {
      const p = path.join(abs, row.notice_file);
      if (!fs.existsSync(p)) f('notice', 'notice', `notice_file ${row.notice_file} is missing from the folder`);
      else {
        const text = fs.readFileSync(p, 'utf8');
        for (const u of needsNotice)
          if (!u.copyright || !text.includes(u.copyright)) f('notice', 'notice', `${row.notice_file} lacks the copyright line of ${u.repo}`);
      }
    }
  } else if (row.notice_file && !fs.existsSync(path.join(abs, row.notice_file))) {
    f('notice', 'notice', `notice_file ${row.notice_file} is missing from the folder`);
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

export function runCheck({ root = REPO_ROOT, catalog, builtins, jobs = null, extensions = null } = {}) {
  const errors = [];
  const warnings = [];
  const raw = [];
  if (catalog?.format !== 1) raw.push(fail('row', 'format:catalog', 'catalog.json must have "format": 1'));
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
    raw.push(...checkRowShape(r));
    raw.push(...checkRowFolder(root, r, catalog));
    warnings.push(...brandWarnings(root, r));
  }

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

  const baseline = [...(catalog?.baseline_violations ?? []), ...(extensions?.baseline_violations ?? [])];
  const done = [...(catalog?.done_work_packages ?? []), ...(extensions?.done_work_packages ?? [])];
  // Cross-kind entries (they need jobs.json or the extension catalog) only
  // apply when those were given.
  const relevant = baseline.filter((b) => (extensions || jobs) || !b.cross_kind);
  const result = applyBaseline(raw, relevant, done);
  errors.push(...result.errors);
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
    console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 11).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
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
