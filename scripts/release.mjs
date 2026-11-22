#!/usr/bin/env node
// Releases skills: build, install-test, upload, annotate, verify.
//
//   node scripts/release.mjs <id> [<id> ...]                 # dry run: prints every step, changes nothing
//   node scripts/release.mjs <id> ... --execute --work <dir> [--biorouter <path to biorouter>]
//
// --work holds the hand-off files: counts-before.tsv (download counts taken
// once, before the first asset is replaced, so the usage dashboard's history
// can be checked afterwards) and archive/<id>-<old version>.zip (the published
// archive before it is replaced, which is also the rollback copy).
// --biorouter runs the install test in a throwaway BIOROUTER_PATH_ROOT: the
// new archive installed fresh, then over the previous archive, must land under
// the same id both times. Without it the install test is skipped and the run
// says so.
//
// Every step runs gh against BaranziniLab/biorouter-skills. A release that
// already exists gets its asset replaced (--clobber) and its notes rewritten;
// a new item gets a new release. The row's release.sha256 is updated in
// catalog.json afterwards; commit that change.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT } from './lib/repo.mjs';
import { buildItemZip, sha256 } from './lib/build.mjs';
import { runCheck } from './check-catalog.mjs';

const REPO = 'BaranziniLab/biorouter-skills';
const argv = process.argv.slice(2);
const opts = { execute: false, work: null, biorouter: null, ids: [] };
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--execute') opts.execute = true;
  else if (argv[i] === '--work') opts.work = path.resolve(argv[++i]);
  else if (argv[i] === '--biorouter') opts.biorouter = path.resolve(argv[++i]);
  else opts.ids.push(argv[i]);
}
if (!opts.ids.length) {
  console.error('usage: node scripts/release.mjs <id>... [--execute --work <dir>] [--biorouter <path>]');
  process.exit(2);
}
if (opts.execute && !opts.work) {
  console.error('--execute needs --work <dir> for counts-before.tsv and the rollback archive');
  process.exit(2);
}

const catalogPath = path.join(REPO_ROOT, 'catalog.json');
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
const builtins = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'builtin-skill-names.json'), 'utf8'));
const say = (s) => console.log(s);
const step = (s) => say(`${opts.execute ? 'run ' : 'plan'}  ${s}`);
const gh = (args, extra = {}) => execFileSync('gh', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], ...extra });

// Preflight: the catalog must pass before anything is published.
const check = runCheck({ root: REPO_ROOT, catalog, builtins });
if (check.errors.length) {
  for (const e of check.errors) say(`FAIL [${e.rule}] ${e.message}`);
  say('the catalog check fails; nothing released');
  process.exit(1);
}
const rows = opts.ids.map((id) => catalog.items.find((r) => r.id === id) ?? (() => { throw new Error(`no catalog row ${id}`); })());

const counts = opts.work ? path.join(opts.work, 'counts-before.tsv') : 'counts-before.tsv';
if (!opts.work || !fs.existsSync(counts)) {
  step(`snapshot download counts: gh api repos/${REPO}/releases --paginate --jq '.[] | .tag_name as $t | .assets[] | [$t, .id, .name, .download_count] | @tsv' > ${counts}`);
  if (opts.execute) {
    fs.mkdirSync(opts.work, { recursive: true });
    fs.writeFileSync(counts, gh(['api', `repos/${REPO}/releases`, '--paginate', '--jq', '.[] | .tag_name as $t | .assets[] | [$t, .id, .name, .download_count] | @tsv']));
  }
} else say(`ok    ${counts} exists (taken before the first replacement)`);

function tagExists(tag) {
  try {
    gh(['release', 'view', tag, '-R', REPO, '--json', 'tagName']);
    return true;
  } catch {
    return false;
  }
}

function installTest(zip, previous, id) {
  if (!opts.biorouter) {
    say(`skip  install test for ${id} (no --biorouter)`);
    return true;
  }
  const run = (root, file) =>
    execFileSync(opts.biorouter, ['skill', 'install', file], {
      encoding: 'utf8',
      env: { ...process.env, BIOROUTER_PATH_ROOT: root, BIOROUTER_DISABLE_KEYRING: 'true' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  const fresh = fs.mkdtempSync(path.join(os.tmpdir(), `br-skill-${id}-fresh-`));
  const over = fs.mkdtempSync(path.join(os.tmpdir(), `br-skill-${id}-over-`));
  step(`install ${path.basename(zip)} fresh in ${fresh}`);
  step(`install ${previous ? path.basename(previous) : '(no previous archive)'} then ${path.basename(zip)} in ${over}`);
  if (!opts.execute) return true;
  const a = run(fresh, zip);
  if (previous) run(over, previous);
  const b = run(over, zip);
  const named = (out) => out.includes(id);
  if (!named(a) || !named(b)) {
    say(`FAIL  install of ${id} did not report the id both times\n--- fresh\n${a}\n--- over\n${b}`);
    return false;
  }
  return true;
}

let failed = 0;
for (const row of rows) {
  say(`\n${row.id} ${row.version} (${row.status})`);
  const dist = path.join(REPO_ROOT, 'dist');
  fs.mkdirSync(dist, { recursive: true });
  const buf = buildItemZip(REPO_ROOT, row);
  const zip = path.join(dist, row.release.asset);
  fs.writeFileSync(zip, buf);
  const digest = sha256(buf);
  say(`ok    built ${path.relative(REPO_ROOT, zip)} ${digest}`);
  const exists = opts.execute ? tagExists(row.release.tag) : row.history.length > 1 || row.release.sha256 != null;
  const prevVersion = row.history.length > 1 ? row.history.at(-2).version : null;
  let previous = null;
  if (exists && prevVersion) {
    previous = opts.work ? path.join(opts.work, 'archive', `${row.id}-${prevVersion}.zip`) : `archive/${row.id}-${prevVersion}.zip`;
    if (!opts.work || !fs.existsSync(previous)) {
      step(`keep the published ${prevVersion} archive: gh release download ${row.release.tag} -p ${row.release.asset} -R ${REPO} -O ${previous}`);
      if (opts.execute) {
        fs.mkdirSync(path.dirname(previous), { recursive: true });
        gh(['release', 'download', row.release.tag, '-p', row.release.asset, '-R', REPO, '-O', previous]);
      }
    }
  }
  if (!installTest(zip, previous && fs.existsSync(previous) ? previous : null, row.id)) {
    failed++;
    continue;
  }
  const note = row.history.at(-1).note ?? 'release';
  const date = row.history.at(-1).date ?? new Date().toISOString().slice(0, 10);
  const notes = `${row.id} ${row.version}, ${date}: ${note}. Install via Skills, Add Skill.`;
  if (exists) {
    step(`gh release upload ${row.release.tag} ${path.relative(REPO_ROOT, zip)} --clobber -R ${REPO}`);
    step(`gh release edit ${row.release.tag} --notes "${notes}" -R ${REPO}`);
    if (opts.execute) {
      gh(['release', 'upload', row.release.tag, zip, '--clobber', '-R', REPO]);
      gh(['release', 'edit', row.release.tag, '--notes', notes, '-R', REPO]);
    }
  } else {
    step(`gh release create ${row.release.tag} ${path.relative(REPO_ROOT, zip)} --title "${row.display_name}" --notes "${notes}" -R ${REPO}`);
    if (opts.execute) gh(['release', 'create', row.release.tag, zip, '--title', row.display_name, '--notes', notes, '-R', REPO]);
  }
  step(`node scripts/verify-release.mjs ${row.id}`);
  if (opts.execute) {
    row.release.sha256 = digest;
    fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
    try {
      execFileSync(process.execPath, [path.join(REPO_ROOT, 'scripts/verify-release.mjs'), row.id], { stdio: 'inherit' });
    } catch {
      failed++;
    }
  }
}
say(opts.execute ? (failed ? `\n${failed} item(s) failed` : '\ndone; commit catalog.json (release.sha256)') : '\ndry run: nothing was changed (pass --execute --work <dir> to release)');
process.exit(failed ? 1 : 0);
