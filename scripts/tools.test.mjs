// Tests for the frontmatter reader, the deterministic zip, the stub generator,
// the README renderer, and the real repository's own state.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { parseFrontmatter, readSkillText } from './lib/frontmatter.mjs';
import { readZip, writeZip, crc32 } from './lib/zip.mjs';
import { buildItemZip, sha256 } from './lib/build.mjs';
import { stubFiles } from './lib/stub.mjs';
import { makeFixture } from './lib/fixture-repo.mjs';
import { REPO_ROOT } from './lib/repo.mjs';
import { applySections, renderNotice } from './render-readme.mjs';

test('frontmatter: scalars, quotes, the metadata map, lists and block scalars', () => {
  const fm = parseFrontmatter([
    'name: x',
    'description: "Says \\"hi\\": twice"',
    "license: 'Apache-2.0'",
    'user-invocable: true',
    'metadata:',
    '  version: "1.1.0"',
    '  upstream: GPTomics/bioSkills@d91ed3d',
    'depends_on:',
    '  - a/b',
    '  - c/d',
    'long: >',
    '  one',
    '  two',
  ].join('\n'));
  assert.equal(fm.description, 'Says "hi": twice');
  assert.equal(fm.license, 'Apache-2.0');
  assert.deepEqual(fm.metadata, { version: '1.1.0', upstream: 'GPTomics/bioSkills@d91ed3d' });
  assert.deepEqual(fm.depends_on, ['a/b', 'c/d']);
  assert.equal(fm.long, 'one two');
  assert.equal(readSkillText('no frontmatter').ok, false);
});

test('zip: the same entries give the same bytes in any order, and read back intact', () => {
  const a = [{ name: 'x/', dir: true }, { name: 'x/b.txt', data: Buffer.from('b') }, { name: 'x/a.sh', data: Buffer.from('#!/bin/sh\n'), executable: true }];
  const z1 = writeZip(a);
  const z2 = writeZip([...a].reverse());
  assert.equal(sha256(z1), sha256(z2));
  const back = readZip(z1);
  assert.deepEqual(back.map((e) => e.name), ['x/', 'x/a.sh', 'x/b.txt']);
  assert.equal(back[1].mode & 0o777, 0o755);
  assert.equal(back[2].data.toString(), 'b');
  assert.equal(crc32(Buffer.from('123456789')), 0xcbf43926);
  assert.throws(() => writeZip([{ name: 'x', data: Buffer.from('') }, { name: 'x', data: Buffer.from('') }]), /duplicate/);
});

test('build: a folder archive is rooted at the id, skips junk, and is reproducible', () => {
  const fx = makeFixture();
  fx.write('alpha/.DS_Store', 'junk');
  fx.write('alpha/__pycache__/x.pyc', 'junk');
  const r = fx.catalog.items[0];
  const z = buildItemZip(fx.root, r);
  assert.deepEqual(readZip(z).map((e) => e.name), ['alpha/', 'alpha/SKILL.md']);
  fs.utimesSync(path.join(fx.root, 'alpha/SKILL.md'), new Date(2001, 1, 1), new Date(2001, 1, 1));
  assert.equal(sha256(buildItemZip(fx.root, r)), sha256(z), 'timestamps never reach the archive');
  const bundle = readZip(buildItemZip(fx.root, fx.catalog.items[2])).map((e) => e.name);
  assert.ok(bundle.includes('gamma/one/SKILL.md'), 'a bio bundle is rooted at its id, not bio-skills/');
});

test('build-zip.mjs and Python zipfile agree on what the archive holds', () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'zipcheck-'));
  execFileSync(process.execPath, [path.join(REPO_ROOT, 'scripts/build-zip.mjs'), '--out', out, 'ralph'], { stdio: 'ignore' });
  const listing = execFileSync('python3', ['-I', '-c', 'import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None; print("\\n".join(sorted(z.namelist())))', path.join(out, 'ralph.zip')], { encoding: 'utf8' });
  assert.ok(listing.split('\n').includes('ralph/SKILL.md'));
});

test('stubs: a merged stub says Moved, a built-in redirect says so, a retired stub says Retired', () => {
  const catalog = { items: [{ id: 'new', display_name: 'New Skill' }] };
  const moved = stubFiles({ id: 'old', display_name: 'Old', version: '1.1.0', status: 'superseded_by:new' }, catalog)['SKILL.md'];
  const fm = readSkillText(moved).frontmatter;
  assert.equal(fm.name, 'old');
  assert.match(fm.description, /^Moved: this skill is now part of New Skill \(new\)/);
  assert.equal(fm.metadata.version, '1.1.0');
  assert.match(moved, /search for "New Skill"/);
  const builtin = readSkillText(stubFiles({ id: 'sc', display_name: 'SC', version: '1.1.0', status: 'superseded_by:builtin:develop-biorouter-skill' }, catalog)['SKILL.md']);
  assert.match(builtin.frontmatter.description, /^Moved: .*built-in develop-biorouter-skill/);
  assert.match(builtin.body, /update Biorouter/);
  const retired = readSkillText(stubFiles({ id: 'r', display_name: 'R', version: '1.1.0', status: 'retired', retired: { reason: 'an empty template', use: 'new' } }, catalog)['SKILL.md']);
  assert.match(retired.frontmatter.description, /^Retired: an empty template\. Use New Skill \(new\) instead\./);
  assert.throws(() => stubFiles({ id: 'a', status: 'active' }, catalog), /active/);
});

test('render: generated sections replace only their blocks, and NOTICE carries each copyright line', () => {
  const readme = 'intro\n<!-- catalog:begin core -->\nold\n<!-- catalog:end core -->\noutro\n';
  assert.equal(applySections(readme, { core: 'new' }), 'intro\n<!-- catalog:begin core -->\nnew\n<!-- catalog:end core -->\noutro\n');
  assert.throws(() => applySections('no blocks', { core: 'x' }), /no <!-- catalog:begin core -->/);
  const notice = renderNotice({ items: [{ id: 'a', status: 'active', source: { origin: 'adapted', upstreams: [{ repo: 'u/v', path: 'p', commit: 'abc1234', licence: 'BSD-3-Clause', copyright: 'Copyright (c) 2024 U' }], changes: 'trimmed' } }] });
  assert.match(notice, /a includes material from u\/v \(p, commit abc1234\),\nCopyright \(c\) 2024 U, licensed under BSD-3-Clause\. Changes: trimmed/);
  assert.match(notice, /not used to endorse/);
});

test('the repository passes its own checks', () => {
  const run = (script, ...args) => execFileSync(process.execPath, [path.join(REPO_ROOT, 'scripts', script), ...args], { encoding: 'utf8' });
  assert.match(run('check-catalog.mjs'), /\nok\n?$/);
  assert.match(run('render-readme.mjs', '--check'), /current/);
  assert.match(run('write-stubs.mjs', '--check'), /every merged or retired folder holds its stub/);
});

test('merge-rows: incoming fields win, unknown fields stay, history and boundaries are united', async () => {
  const { mergeRow } = await import('./merge-rows.mjs');
  const fx = makeFixture();
  const existing = { ...fx.catalog.items[2], summary: 'card text', keywords: ['k'], release: { tag: 'skill-gamma', asset: 'gamma.zip', sha256: 'a'.repeat(64) } };
  existing.components.one.distinct_from = [{ id: 'other/x', boundary: 'b' }];
  const incoming = {
    id: 'gamma', version: '1.1.0', job: 'bio.gamma', aliases: ['old-gamma'],
    history: [{ version: '1.0.0', date: '2026-07-01' }, { version: '1.1.0', date: '2026-11-22', note: 'resync' }],
    components: { one: { status: 'active', job: 'gamma.one' }, two: { status: 'removed', job: 'gamma.two' } },
  };
  const m = mergeRow(existing, incoming, fx.root);
  assert.equal(m.summary, 'card text');
  assert.deepEqual(m.keywords, ['k']);
  assert.equal(m.version, '1.1.0');
  assert.equal(m.release.sha256, null, 'a new version clears the old digest');
  assert.deepEqual(m.history.map((h) => h.version), ['1.0.0', '1.1.0']);
  assert.equal(m.components.one.name, 'gamma-one', 'a missing component name is read from its folder');
  assert.deepEqual(m.components.one.distinct_from, [{ id: 'other/x', boundary: 'b' }]);
  assert.deepEqual(m.aliases, ['old-gamma']);
});
