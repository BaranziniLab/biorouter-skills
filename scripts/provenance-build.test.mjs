// Tests for the packaging side of provenance format 2: the archive's own
// LICENSE, the release check of a published asset, the release notes and the
// upstream drift targets.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { buildItemZip, archiveOptions, diffArchives, sha256 } from './lib/build.mjs';
import { readZip, writeZip } from './lib/zip.mjs';
import { listTree, REPO_ROOT } from './lib/repo.mjs';
import { makeFixture, row as fixtureRow, clone } from './lib/fixture-repo.mjs';
import { adaptedRow, inHouseRow, stubRow, upstream } from './lib/fixture-provenance.mjs';
import { CURATED_BY, MADE_BY_LAB } from './lib/catalog-rules.mjs';
import { PROVENANCE_BASELINE_FILE } from './lib/provenance-baseline.mjs';
import { stubProblem, missingProvenanceFiles, assetProblems } from './verify-release.mjs';
import { releaseNotes } from './release.mjs';
import { driftTargets, comparePin } from './upstream-drift.mjs';

const LICENCE_TEXT = 'Apache License\nVersion 2.0, January 2004\n(the repository licence, as a fixture)\n';

/** makeFixture() with a repository LICENSE, alpha rewritten as a format 2 row, and the given provenance baseline entries. */
function provenanceFixture({ alpha = inHouseRow('alpha'), baseline = [] } = {}) {
  const fx = makeFixture();
  fx.write('LICENSE', LICENCE_TEXT);
  fx.catalog.items[0] = alpha;
  fx.write(PROVENANCE_BASELINE_FILE, `${JSON.stringify({ format: 1, since: '2026-11-27', rows: [], done_work_packages: [], baseline_violations: baseline }, null, 2)}\n`);
  return fx;
}

const names = (buf) => readZip(buf).map((e) => e.name);
const entry = (buf, name) => readZip(buf).find((e) => e.name === name);

/** The archive the builder made before format 2: the folder's tree under the id, and nothing else. */
function folderOnlyZip(root, row) {
  const abs = path.join(root, row.path);
  const { files, dirs } = listTree(abs);
  return writeZip([
    { name: `${row.id}/`, dir: true },
    ...dirs.map((d) => ({ name: `${row.id}/${d}/`, dir: true })),
    ...files.map((f) => ({ name: `${row.id}/${f.rel}`, data: fs.readFileSync(f.abs), executable: f.executable })),
  ]);
}

test('build: a wanted row gets the repository LICENSE as <id>/LICENSE, byte for byte', () => {
  const fx = provenanceFixture();
  const r = fx.catalog.items[0];
  const opts = archiveOptions(fx.root, r, fx.catalog);
  assert.deepEqual(opts, { addLicence: true });
  const z = buildItemZip(fx.root, r, opts);
  assert.deepEqual(names(z), ['alpha/', 'alpha/LICENSE', 'alpha/SKILL.md']);
  const lic = entry(z, 'alpha/LICENSE');
  assert.equal(lic.data.toString('utf8'), LICENCE_TEXT);
  assert.equal(lic.mode & 0o111, 0, 'the LICENSE is not executable');
  assert.deepEqual(diffArchives(buildItemZip(fx.root, r), z), ['only in the second: alpha/LICENSE']);
  assert.equal(sha256(buildItemZip(fx.root, r, opts)), sha256(z), 'still reproducible');
});

test('build: a catalog in format 2 wants the LICENSE for every row, even one without the per-row marker', () => {
  const fx = provenanceFixture();
  const r = fx.catalog.items[1];
  assert.deepEqual(archiveOptions(fx.root, r, { ...fx.catalog, format: 2 }), { addLicence: true });
  assert.deepEqual(archiveOptions(fx.root, r, fx.catalog), { addLicence: false });
});

test('build: no LICENSE for a format 1 row or a row whose folder files are deferred', () => {
  const fx = provenanceFixture();
  for (const r of fx.catalog.items.slice(1)) {
    assert.deepEqual(archiveOptions(fx.root, r, fx.catalog), { addLicence: false }, `${r.id} is format 1`);
    assert.ok(!names(buildItemZip(fx.root, r, archiveOptions(fx.root, r, fx.catalog))).some((n) => n.endsWith('/LICENSE')));
  }
  const deferred = provenanceFixture({ baseline: [{ rule: 'PV9', subject: 'folder:alpha', wp: 'PROV-S4', since: '2026-11-27', note: 'waits for its next release' }] });
  const r = deferred.catalog.items[0];
  assert.deepEqual(archiveOptions(deferred.root, r, deferred.catalog), { addLicence: false });
  assert.deepEqual(names(buildItemZip(deferred.root, r, archiveOptions(deferred.root, r, deferred.catalog))), ['alpha/', 'alpha/SKILL.md']);
  const other = provenanceFixture({ baseline: [{ rule: 'PV9', subject: 'folder:beta', wp: 'PROV-S4', since: '2026-11-27' }] });
  assert.deepEqual(archiveOptions(other.root, other.catalog.items[0], other.catalog), { addLicence: true }, "another row's deferral does not defer this one");
});

test('build: no provenance baseline file reads as an empty baseline', () => {
  const fx = provenanceFixture();
  fs.rmSync(path.join(fx.root, PROVENANCE_BASELINE_FILE));
  assert.deepEqual(archiveOptions(fx.root, fx.catalog.items[0], fx.catalog), { addLicence: true });
  assert.deepEqual(archiveOptions(fx.root, fx.catalog.items[1], fx.catalog), { addLicence: false });
});

test('build: a folder with its own top-level LICENSE is refused when the archive adds one', () => {
  const fx = provenanceFixture();
  const r = fx.catalog.items[0];
  fx.write('alpha/LICENSE', 'a folder licence');
  assert.throws(() => buildItemZip(fx.root, r, { addLicence: true }), /alpha: .*LICENSE.*reserved/);
  fs.rmSync(path.join(fx.root, 'alpha/LICENSE'));
  fx.write('alpha/license', 'a lower-case folder licence');
  assert.throws(() => buildItemZip(fx.root, r, { addLicence: true }), /alpha: .*license.*reserved/, 'a case-insensitive file system would extract both to one file');
  fs.rmSync(path.join(fx.root, 'alpha/license'));
  fx.write('alpha/LICENSE/text.md', 'a folder named LICENSE');
  assert.throws(() => buildItemZip(fx.root, r, { addLicence: true }), /alpha: .*LICENSE.*reserved/);
  fs.rmSync(path.join(fx.root, 'alpha/LICENSE'), { recursive: true });
  fx.write('alpha/references/LICENSE', 'a nested licence is the folder\'s own business');
  assert.ok(names(buildItemZip(fx.root, r, { addLicence: true })).includes('alpha/references/LICENSE'));
});

test('build: adding the LICENSE needs the repository LICENSE', () => {
  const fx = provenanceFixture();
  fs.rmSync(path.join(fx.root, 'LICENSE'));
  assert.throws(() => buildItemZip(fx.root, fx.catalog.items[0], { addLicence: true }), /no LICENSE at the repository root/);
});

test('build: two-argument builds are unchanged, whatever the row says', () => {
  const fx = provenanceFixture();
  fx.write('beta/LICENSE', 'a folder licence, fine when the archive adds none');
  for (const r of fx.catalog.items) {
    const want = sha256(folderOnlyZip(fx.root, r));
    assert.equal(sha256(buildItemZip(fx.root, r)), want, `${r.id}: two arguments`);
    assert.equal(sha256(buildItemZip(fx.root, r, {})), want, `${r.id}: empty options`);
    assert.equal(sha256(buildItemZip(fx.root, r, { addLicence: false })), want, `${r.id}: addLicence false`);
  }
  assert.ok(!names(buildItemZip(fx.root, fx.catalog.items[0])).includes('alpha/LICENSE'), 'the builder never decides by itself');
});

test('build: a released format 1 row still builds to its recorded digest (ralph)', () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const ralph = catalog.items.find((r) => r.id === 'ralph');
  assert.ok(ralph.release.sha256, 'ralph records a digest');
  const opts = archiveOptions(REPO_ROOT, ralph, catalog);
  assert.deepEqual(opts, { addLicence: false });
  assert.equal(sha256(buildItemZip(REPO_ROOT, ralph, opts)), ralph.release.sha256);
});

function stubZip(files) {
  return writeZip([{ name: 'beta/', dir: true }, ...Object.entries(files).map(([n, t]) => ({ name: `beta/${n}`, data: Buffer.from(t) }))]);
}
const STUB_MD = '---\nname: beta\ndescription: "Moved: this skill is now part of Alpha (alpha)."\nlicense: Apache-2.0\n---\n\n# Beta has moved\n';

test('verify: a stub holds one SKILL.md, plus the LICENSE when the row wants it', () => {
  assert.equal(stubProblem(stubZip({ 'SKILL.md': STUB_MD })), null);
  assert.equal(stubProblem(stubZip({ 'SKILL.md': STUB_MD, LICENSE: LICENCE_TEXT }), { licence: true }), null);
  assert.equal(stubProblem(stubZip({ 'SKILL.md': STUB_MD, LICENSE: LICENCE_TEXT })), 'holds 2 files, a stub holds one SKILL.md', 'without the option, exactly today');
  assert.equal(stubProblem(stubZip({ 'SKILL.md': STUB_MD }), { licence: true }), null, 'a missing LICENSE is named by missingProvenanceFiles, not twice');
  assert.match(stubProblem(stubZip({ 'SKILL.md': STUB_MD, LICENSE: LICENCE_TEXT, 'notes.md': 'x' }), { licence: true }), /holds 3 files, a stub holds one SKILL.md and the LICENSE/);
  assert.match(stubProblem(stubZip({ 'SKILL.md': STUB_MD, 'refs/LICENSE': LICENCE_TEXT }), { licence: true }), /holds 2 files/, 'only <id>/LICENSE counts');
  assert.match(stubProblem(stubZip({ LICENSE: LICENCE_TEXT }), { licence: true }), /holds 1 files/);
  const twoRoots = writeZip([{ name: 'beta/SKILL.md', data: Buffer.from(STUB_MD) }, { name: 'beta/LICENSE', data: Buffer.from('l') }, { name: 'other/LICENSE', data: Buffer.from('l') }]);
  assert.match(stubProblem(twoRoots, { licence: true }), /holds 3 files/, 'one LICENSE at most');
  assert.match(stubProblem(stubZip({ 'SKILL.md': STUB_MD.replace('Moved:', 'Plots'), LICENSE: LICENCE_TEXT }), { licence: true }), /does not start with "Moved" or "Retired"/);
});

test('verify: missingProvenanceFiles names the LICENSE, and PROVENANCE.md for an active row, only when wanted', () => {
  const bare = writeZip([{ name: 'alpha/', dir: true }, { name: 'alpha/SKILL.md', data: Buffer.from('x') }]);
  const full = writeZip([{ name: 'alpha/', dir: true }, { name: 'alpha/SKILL.md', data: Buffer.from('x') }, { name: 'alpha/LICENSE', data: Buffer.from('l') }, { name: 'alpha/PROVENANCE.md', data: Buffer.from('p') }]);
  const active = { id: 'alpha', status: 'active' };
  const stub = { id: 'alpha', status: 'superseded_by:gamma' };
  assert.deepEqual(missingProvenanceFiles(bare, active, { addLicence: false }), []);
  assert.deepEqual(missingProvenanceFiles(bare, active, { addLicence: true }), ['alpha/LICENSE', 'alpha/PROVENANCE.md']);
  assert.deepEqual(missingProvenanceFiles(bare, stub, { addLicence: true }), ['alpha/LICENSE'], 'a stub carries no PROVENANCE.md');
  assert.deepEqual(missingProvenanceFiles(full, active, { addLicence: true }), []);
});

test('verify: assetProblems compares a published asset with the folder build and names missing provenance files', () => {
  const fx = provenanceFixture();
  const r = fx.catalog.items[0];
  fx.write('alpha/PROVENANCE.md', '# Alpha: provenance and credits\n');
  const good = buildItemZip(fx.root, r, archiveOptions(fx.root, r, fx.catalog));
  assert.deepEqual(assetProblems(fx.root, r, fx.catalog, good), []);
  const old = buildItemZip(fx.root, r);
  const p = assetProblems(fx.root, r, fx.catalog, old);
  assert.equal(p.length, 2, p.join('\n'));
  assert.match(p[0], /differs from the folder build .*only in the second: alpha\/LICENSE/);
  assert.equal(p[1], 'lacks alpha/LICENSE');
  fs.rmSync(path.join(fx.root, 'alpha/PROVENANCE.md'));
  const noRecord = buildItemZip(fx.root, r, archiveOptions(fx.root, r, fx.catalog));
  assert.deepEqual(assetProblems(fx.root, r, fx.catalog, noRecord), ['lacks alpha/PROVENANCE.md']);
  const digest = clone(r);
  digest.release.sha256 = 'f'.repeat(64);
  assert.match(assetProblems(fx.root, digest, fx.catalog, noRecord).join('\n'), /the row records sha256 ffffffffffff/);
  const fmt1 = fx.catalog.items[1];
  assert.deepEqual(assetProblems(fx.root, fmt1, fx.catalog, buildItemZip(fx.root, fmt1)), [], 'a format 1 row is checked as today');
});

test('verify: assetProblems accepts a wanted stub with its LICENSE and rejects a non-stub', () => {
  const fx = provenanceFixture({ alpha: stubRow('alpha', 'beta') });
  const r = fx.catalog.items[0];
  fs.writeFileSync(path.join(fx.root, 'alpha/SKILL.md'), STUB_MD.replace('name: beta', 'name: alpha'));
  const asset = buildItemZip(fx.root, r, archiveOptions(fx.root, r, fx.catalog));
  assert.deepEqual(names(asset), ['alpha/', 'alpha/LICENSE', 'alpha/SKILL.md']);
  assert.deepEqual(assetProblems(fx.root, r, fx.catalog, asset), []);
  fx.write('alpha/extra.md', 'x');
  const fat = buildItemZip(fx.root, r, archiveOptions(fx.root, r, fx.catalog));
  assert.match(assetProblems(fx.root, r, fx.catalog, fat).join('\n'), /is superseded_by:beta but its asset is not a stub: holds 3 files, a stub holds one SKILL.md and the LICENSE/);
});

test('release notes: format 1 rows keep today\'s line', () => {
  const r = fixtureRow('alpha', { history: [{ version: '1.0.0', date: '2026-07-01', note: 'first BAAM release' }] });
  assert.equal(releaseNotes(r), 'alpha 1.0.0, 2026-07-01: first BAAM release. Install via Skills, Add Skill.');
  assert.equal(releaseNotes(fixtureRow('alpha')), 'alpha 1.0.0, 2026-07-01: release. Install via Skills, Add Skill.');
  assert.equal(releaseNotes(fixtureRow('alpha', { history: [{ version: '1.0.0', date: null }] }), { today: '2026-11-27' }), 'alpha 1.0.0, 2026-11-27: release. Install via Skills, Add Skill.');
  assert.ok(!releaseNotes(r).includes(CURATED_BY));
});

test('release notes: format 2 rows carry the credit line and the curator line', () => {
  const adapted = adaptedRow('alpha', { history: [{ version: '1.0.0', date: '2026-07-01', note: 'first release' }] });
  assert.equal(releaseNotes(adapted), `alpha 1.0.0, 2026-07-01: first release. Adapted from example-skills by Example Org (MIT). ${CURATED_BY} Install via Skills, Add Skill.`);
  assert.equal(releaseNotes(inHouseRow('alpha')), `alpha 1.0.0, 2026-07-01: release. ${MADE_BY_LAB} ${CURATED_BY} Install via Skills, Add Skill.`);
  const unmarked = inHouseRow('alpha');
  delete unmarked.source.format;
  assert.equal(releaseNotes(unmarked), 'alpha 1.0.0, 2026-07-01: release. Install via Skills, Add Skill.', 'no marker in a format 1 catalog: format 1');
  assert.equal(releaseNotes(unmarked, { catalogFormat: 2 }), `alpha 1.0.0, 2026-07-01: release. ${MADE_BY_LAB} ${CURATED_BY} Install via Skills, Add Skill.`, 'a format 2 catalog makes every row format 2');
});

test('drift: format 1 targets are every pinned upstream of an active row not maintained here', () => {
  const up = (repo, commit, extra = {}) => ({ repo, path: 'p', commit, licence: 'MIT', ...extra });
  const catalog = {
    format: 1,
    items: [
      fixtureRow('a', { source: { origin: 'adapted', upstreams: [up('x/y', 'abc1234'), up('x/z', undefined)], maintained_here: false } }),
      fixtureRow('b', { status: 'retired', source: { origin: 'adapted', upstreams: [up('x/b', 'abc1234')], maintained_here: false } }),
      fixtureRow('c', { source: { origin: 'adapted', upstreams: [up('x/c', 'abc1234')], maintained_here: true } }),
      fixtureRow('d'),
    ],
  };
  const { targets, skipped } = driftTargets(catalog);
  assert.deepEqual(targets, [{ id: 'a', format: 1, repo: 'x/y', commit: 'abc1234', path: 'p', paths: ['p'] }]);
  assert.deepEqual(skipped, { urlOnly: 0, versionOnly: 0, unpinned: 0 }, 'format 1 skips are not counted, as today');
});

test('drift: format 2 targets need a repo and a commit; url-only, version-only and unpinned sources are counted; lab-owned sources are labelled', () => {
  const row = adaptedRow('d', {
    source: {
      ...adaptedRow('d').source,
      upstreams: [
        upstream(),
        upstream({ repo: null, url: 'https://example.org/paper-code', commit: null, version: '2.0' }),
        upstream({ repo: 'example-org/pkg', commit: null, version: '1.2.3', use: ['dependency'] }),
        upstream({ repo: 'example-org/service', commit: null, version: null, use: ['launched'] }),
        upstream({ repo: 'BaranziniLab/lab-thing', commit: 'fedcba9', owner: 'lab', path: null }),
      ],
    },
  });
  const here = adaptedRow('e', { source: { ...adaptedRow('e').source, maintained_here: true } });
  const { targets, skipped } = driftTargets({ format: 1, items: [row, here] });
  assert.deepEqual(targets, [
    { id: 'd', format: 2, repo: 'example-org/example-skills', commit: '0123456789abcdef0123456789abcdef01234567', path: 'skills/example', paths: ['skills/example'], owner: 'external' },
    { id: 'd', format: 2, repo: 'BaranziniLab/lab-thing', commit: 'fedcba9', path: null, paths: [], owner: 'lab' },
  ]);
  assert.deepEqual(skipped, { urlOnly: 1, versionOnly: 1, unpinned: 1 });
});

test('drift: an upstream path that lists several paths gives a target with every one of them', () => {
  const pinned = (path) => upstream({ path });
  const row = adaptedRow('f', {
    source: {
      ...adaptedRow('f').source,
      upstreams: [
        pinned('skills/prd, skills/ralph, prompt.md'),
        pinned('plugins/code-review (v1.0.1, c905cd8 command)'),
        pinned('skills/scientific-slides (references, assets, three scripts), skills/diagram-design, THIRD_PARTY_LICENSES.md'),
        pinned('skills/ (13 of 15; two left out)'),
        pinned('skills/example'),
        pinned(null),
      ],
    },
  });
  const paths = driftTargets({ format: 2, items: [row] }).targets.map((t) => t.paths);
  assert.deepEqual(paths, [
    ['skills/prd', 'skills/ralph', 'prompt.md'],
    ['plugins/code-review'],
    ['skills/scientific-slides', 'skills/diagram-design', 'THIRD_PARTY_LICENSES.md'],
    ['skills'],
    ['skills/example'],
    [],
  ]);
  const format1 = fixtureRow('g', { source: { origin: 'adapted', upstreams: [{ repo: 'x/y', path: 'a/b, c/d', commit: 'abc1234', licence: 'MIT' }], maintained_here: false } });
  assert.deepEqual(driftTargets({ format: 1, items: [format1] }).targets.map((t) => t.paths), [['a/b', 'c/d']], 'a format 1 row splits its list the same way');
});

test('drift: every path of a list is compared on its own, and the pin moved when any one of them moved', () => {
  /** A fake `gh api`: answers the given endpoints and records each path the commits endpoint is asked about. */
  const fakeGh = (answers) => {
    const asked = [];
    const gh = (args) => {
      const m = /^repos\/x\/y\/commits\?path=([^&]*)&per_page=1$/.exec(args[0]);
      if (m) asked.push(decodeURIComponent(m[1]));
      if (!Object.hasOwn(answers, args[0])) throw new Error(`unexpected gh api ${args[0]}`);
      return answers[args[0]];
    };
    return { gh, asked };
  };
  const pin = 'abc1234';
  const base = { [`repos/x/y/compare/${pin}...HEAD`]: { ahead: 5 }, 'repos/x/y/commits?path=a%2Fb&per_page=1': [`${pin}0000`] };

  const one = fakeGh({ ...base, 'repos/x/y/commits?path=c%2Fd&per_page=1': ['def5678aaaa'], [`repos/x/y/compare/${pin}...def5678aaaa`]: { status: 'ahead' } });
  assert.deepEqual(comparePin('x/y', pin, ['a/b', 'c/d'], one.gh), {
    ahead: 5,
    pathMoved: true,
    latest: 'def5678',
    paths: [
      { path: 'a/b', moved: false, latest: 'abc1234' },
      { path: 'c/d', moved: true, latest: 'def5678' },
    ],
  });
  assert.deepEqual(one.asked, ['a/b', 'c/d'], 'each path is asked about once, never the joined list');

  const none = fakeGh({ ...base, 'repos/x/y/commits?path=c%2Fd&per_page=1': [`${pin}1111`] });
  const quiet = comparePin('x/y', pin, ['a/b', 'c/d'], none.gh);
  assert.equal(quiet.pathMoved, false, 'no path moved: unrelated changes');
  assert.equal(quiet.latest, 'abc1234');

  const current = fakeGh({ [`repos/x/y/compare/${pin}...HEAD`]: { ahead: 0 } });
  assert.deepEqual(comparePin('x/y', pin, ['a/b', 'c/d'], current.gh), { ahead: 0, pathMoved: false });
  assert.deepEqual(current.asked, [], 'a current pin asks about no path');

  const whole = fakeGh({ [`repos/x/y/compare/${pin}...HEAD`]: { ahead: 2 } });
  assert.deepEqual(comparePin('x/y', pin, [], whole.gh), { ahead: 2, pathMoved: true }, 'no path: any change counts');

  const failing = comparePin('x/y', pin, ['a/b'], () => {
    throw Object.assign(new Error('gh failed'), { stderr: 'HTTP 404: Not Found\nmore' });
  });
  assert.deepEqual(failing, { error: 'HTTP 404: Not Found' });
});
