// Mutant tests for the provenance folder rules (PV7 to PV11 and PV13 in
// check-catalog.mjs) and the provenance baseline, on throwaway repositories:
// makeFixture2() for format 2 rows, makeFixture() for format 1 rows.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { checkRowShape, provenanceBaselineProblems, provenanceRowsDigest, runCheck } from './check-catalog.mjs';
import { initProvenance, markDone, planAccept, pruneBaselines } from './baseline.mjs';
import { mergeRow } from './merge-rows.mjs';
import { upstream, contributor, thirdPartyExtensionRow } from './lib/fixture-provenance.mjs';
import {
  BUILTINS, MIT_LICENCE_TEXT, clone, fixtureNoticeText, frozenRowsFor, makeFixture, makeFixture2, provenanceBaseline,
  pvEntry, row,
} from './lib/fixture-repo.mjs';
import { PROVENANCE_BASELINE_ROWS, PROVENANCE_BASELINE_ROWS_SHA256, readProvenanceBaseline } from './lib/provenance-baseline.mjs';
import { REPO_ROOT } from './lib/repo.mjs';
import { stubFiles } from './lib/stub.mjs';

const rules = (res) => res.errors.map((e) => `${e.rule}:${e.subject}`).sort();
const item = (fx, id) => fx.catalog.items.find((r) => r.id === id);

/** makeFixture2 with one change; `mutate` may return { provenance } to replace the baseline. */
function run2(mutate = () => {}) {
  const fx = makeFixture2();
  const over = mutate(fx) ?? {};
  return runCheck({ root: fx.root, catalog: fx.catalog, builtins: BUILTINS, frozenRows: fx.frozenRows, ...over });
}

/** makeFixture (format 1) with one change; `mutate` may return { provenance }. */
function run1(mutate = () => {}) {
  const fx = makeFixture();
  const over = mutate(fx) ?? {};
  return runCheck({ root: fx.root, catalog: fx.catalog, builtins: BUILTINS, frozenRows: fx.frozenRows, ...over });
}

test('the format 2 fixture passes with an empty provenance baseline', () => {
  const res = run2();
  assert.deepEqual(rules(res), []);
  assert.deepEqual(res.warnings, []);
  assert.deepEqual(res.accepted, []);
});

test('the format 1 fixture passes because each row has its PV1 entry', () => {
  const res = run1();
  assert.deepEqual(rules(res), []);
  assert.deepEqual(res.accepted.map((a) => `${a.rule}:${a.subject}:${a.wp}`).sort(), ['PV1:format:alpha:PROV-S1', 'PV1:format:beta:PROV-S1', 'PV1:format:gamma:PROV-S1']);
});

// ---------------------------------------------------------------------------
// PV7, the notice file.

const toApache = (r, notice = false) => {
  r.source.upstreams[0].licence = 'Apache-2.0';
  r.source.upstreams[0].upstream_notice = notice;
  r.licence = 'Apache-2.0';
};

test('PV7: an Apache-2.0 source needs a notice file', () => {
  const res = run2((fx) => {
    toApache(item(fx, 'alpha'));
    item(fx, 'alpha').notice_file = null;
    fx.regenerate();
  });
  assert.deepEqual(rules(res), ['PV7:notice:alpha']);
  assert.match(res.errors[0].message, /upstream material but no notice_file/);
  const missing = run2((fx) => fx.remove('alpha/LICENSE-UPSTREAM'));
  assert.deepEqual(rules(missing), ['PV7:notice:alpha']);
  assert.match(missing.errors[0].message, /notice_file LICENSE-UPSTREAM is missing from the folder/);
});

test('PV7, format 2: a source whose licence names no holder has no copyright line to look for (PV6 asks for its note)', () => {
  const res = run2((fx) => {
    const u = item(fx, 'alpha').source.upstreams[0];
    u.copyright = null;
    u.copyright_note = 'the licence names no copyright holder';
    fx.regenerate();
  });
  assert.deepEqual(rules(res), []);
  assert.match(res.warnings.join('\n'), /names no copyright holder/);
});

test("PV7: the notice file carries each licence's text", () => {
  const res = run2((fx) => fx.write('alpha/LICENSE-UPSTREAM', fx.read('alpha/LICENSE-UPSTREAM').replace('Permission is hereby granted, free of charge', 'Permission is granted')));
  assert.deepEqual(rules(res), ['PV7:notice-licence:alpha:MIT']);
});

test("PV7: the notice file carries each source's copyright line, one failure per repository", () => {
  const res = run2((fx) => fx.write('alpha/LICENSE-UPSTREAM', fx.read('alpha/LICENSE-UPSTREAM').replace('Copyright (c) 2026 Example Org', 'Copyright (c) 2025 Someone Else')));
  assert.deepEqual(rules(res), ['PV7:notice-copyright:alpha:example-org/example-skills']);
  const two = run2((fx) => {
    const a = item(fx, 'alpha');
    a.source.upstreams.push(upstream({ path: 'skills/other', copyright: 'Copyright (c) 2024 Example Org' }));
    fx.regenerate();
    fx.write('alpha/LICENSE-UPSTREAM', fx.read('alpha/LICENSE-UPSTREAM').replaceAll('Example Org', 'Nobody'));
  });
  assert.deepEqual(rules(two), ['PV7:notice-copyright:alpha:example-org/example-skills']);
});

test("PV7: an Apache source with a NOTICE file ships it under its marker", () => {
  const ok = run2((fx) => {
    toApache(item(fx, 'alpha'), true);
    fx.regenerate();
  });
  assert.deepEqual(rules(ok), []);
  const res = run2((fx) => {
    toApache(item(fx, 'alpha'), true);
    fx.regenerate();
    fx.write('alpha/LICENSE-UPSTREAM', fx.read('alpha/LICENSE-UPSTREAM').replace('NOTICE file of example-org/example-skills', 'Upstream notice'));
  });
  assert.deepEqual(rules(res), ['PV7:notice-apache:alpha:example-org/example-skills']);
});

test("PV7: a format 2 folder may not hold its own top-level LICENSE (the archive's is reserved)", () => {
  assert.deepEqual(rules(run2((fx) => fx.write('alpha/LICENSE', 'Apache License\n'))), ['PV7:reserved-licence:alpha']);
  assert.deepEqual(rules(run2((fx) => fx.write('epsilon/LICENSE', 'Apache License\n'))), ['PV7:reserved-licence:epsilon']);
});

test('PV7 reads format 1 rows too: an adapted Apache-2.0 source needs its licence text', () => {
  const up = { repo: 'x/y', licence: 'Apache-2.0', copyright: null, commit: 'abcdef1' };
  const res = run1(({ catalog }) => {
    catalog.items[0].source = { origin: 'adapted', upstreams: [up], maintained_here: false };
  });
  assert.deepEqual(rules(res), ['PV7:notice:alpha']);
  const lab = run1(({ catalog }) => {
    catalog.items[0].source = { origin: 'lab', upstreams: [up], maintained_here: false };
  });
  assert.deepEqual(rules(lab), [], 'a lab row with a lab Apache source owes no notice file');
});

// ---------------------------------------------------------------------------
// PV8 to PV11 and PV13, the folder halves.

test("PV8: a component's SKILL.md declares the component's own licence", () => {
  const res = run2((fx) => fx.write('bio-skills/gamma/one/SKILL.md', fx.read('bio-skills/gamma/one/SKILL.md').replace('license: MIT', 'license: Apache-2.0 AND MIT')));
  assert.deepEqual(rules(res), ['PV8:frontmatter-licence:gamma:one/SKILL.md']);
  const row = run2((fx) => fx.write('alpha/SKILL.md', fx.read('alpha/SKILL.md').replace('license: Apache-2.0 AND MIT', 'license: Apache-2.0')));
  assert.deepEqual(rules(row), ['PV8:frontmatter-licence:alpha:SKILL.md']);
});

test('PV9: an active format 2 folder holds its generated PROVENANCE.md', () => {
  assert.deepEqual(rules(run2((fx) => fx.remove('alpha/PROVENANCE.md'))), ['PV9:folder:alpha']);
  assert.deepEqual(rules(run2((fx) => fx.write('delta/PROVENANCE.md', `${fx.read('delta/PROVENANCE.md')}\nedited by hand\n`))), ['PV9:folder:delta']);
  assert.deepEqual(rules(run2((fx) => fx.remove('bio-skills/gamma/PROVENANCE.md'))), ['PV9:folder:gamma']);
});

test('PV9: a format 2 stub carries its credit lines', () => {
  const res = run2((fx) => fx.write('beta/SKILL.md', stubFiles(item(fx, 'beta'), fx.catalog)['SKILL.md']));
  assert.deepEqual(rules(res), ['PV9:folder:beta', 'stub:stub:beta']);
});

test("PV9: a deferred stub keeps today's text until its release, and a deferral whose stub is already written is stale", () => {
  const deferred = run2((fx) => {
    const provenance = { ...fx.provenance, baseline_violations: [pvEntry('PV9', 'folder:beta', 'PROV-S4')] };
    fx.regenerate(fx.catalog, provenance);
    return { provenance };
  });
  assert.deepEqual(rules(deferred), []);
  const stale = run2((fx) => ({ provenance: { ...fx.provenance, baseline_violations: [pvEntry('PV9', 'folder:beta', 'PROV-S4')] } }));
  assert.deepEqual(rules(stale), ['baseline:PV9::folder:beta', 'stub:stub:beta']);
});

test('PV10: SKILL.md front matter carries the generated credits', () => {
  const res = run2((fx) => fx.write('alpha/SKILL.md', fx.read('alpha/SKILL.md').replace(/credit: ".*"/, 'credit: "Adapted from something else."')));
  assert.deepEqual(rules(res), ['PV10:frontmatter:alpha']);
  const two = run2((fx) => {
    fx.write('bio-skills/gamma/one/SKILL.md', fx.read('bio-skills/gamma/one/SKILL.md').replace(/ {2}curated_by: .*\n/, ''));
    fx.write('bio-skills/gamma/two/SKILL.md', fx.read('bio-skills/gamma/two/SKILL.md').replace('origin: "in-house"', 'origin: "third-party"'));
  });
  assert.deepEqual(rules(two), ['PV10:frontmatter:gamma']);
  assert.match(two.errors[0].message, /one\/SKILL\.md .*two\/SKILL\.md/);
});

test('PV10: old provenance keys only warn', () => {
  const res = run2((fx) => {
    fx.write('alpha/SKILL.md', fx.read('alpha/SKILL.md').replace('metadata:\n', 'metadata:\n  upstream_author: "Example Org"\n  upstream: "elsewhere/other@abc1234"\n'));
    fx.write('delta/SKILL.md', fx.read('delta/SKILL.md').replace('metadata:\n', 'metadata:\n  source: "Biorouter original"\n'));
    fx.write('bio-skills/gamma/one/SKILL.md', fx.read('bio-skills/gamma/one/SKILL.md').replace('metadata:\n', 'metadata:\n  upstream: "example-org/bio-skills@0123456"\n'));
  });
  assert.deepEqual(rules(res), []);
  const w = res.warnings.join('\n');
  assert.match(w, /alpha: SKILL\.md metadata\.upstream_author/);
  assert.match(w, /alpha: SKILL\.md metadata\.upstream "elsewhere\/other@abc1234" names no upstream of the row/);
  assert.match(w, /delta: SKILL\.md metadata\.source/);
  assert.doesNotMatch(w, /gamma/);
});

test('PV11: a file listed under written_for_biorouter exists', () => {
  const res = run2((fx) => fx.remove('bio-skills/gamma/one/references/merged-notes.md'));
  assert.deepEqual(rules(res), ['PV11:written-file:gamma/one:references/merged-notes.md']);
  const outside = run2((fx) => {
    item(fx, 'gamma').components.one.written_for_biorouter[0].path = '../two/SKILL.md';
    fx.regenerate();
  });
  assert.ok(rules(outside).includes('PV11:written-file:gamma/one:../two/SKILL.md'), rules(outside).join(', '));
});

test('PV13: a folder file states a fixed text as its constant', () => {
  const res = run2((fx) => fx.write('alpha/LICENSE-UPSTREAM', `${fx.read('alpha/LICENSE-UPSTREAM')}\nCopyright 2026 The Regents of the University of California\n`));
  assert.deepEqual(rules(res), ['PV13:fixed-text:alpha:LICENSE-UPSTREAM']);
  const body = run2((fx) => fx.write('delta/SKILL.md', `${fx.read('delta/SKILL.md')}\nCurated and organised by the lab.\n`));
  assert.deepEqual(rules(body), ['PV13:fixed-text:delta:SKILL.md']);
  const comp = run2((fx) => fx.write('bio-skills/gamma/two/SKILL.md', `${fx.read('bio-skills/gamma/two/SKILL.md')}\nMade by the Baranzini lab.\n`));
  assert.deepEqual(rules(comp), ['PV13:fixed-text:gamma:two/SKILL.md']);
});

test("PV13: a source's verbatim copyright line keeps its wording", () => {
  const res = run2((fx) => {
    item(fx, 'alpha').source.upstreams[0].copyright = 'Copyright (c) 2026 Wanjun Gu';
    fx.regenerate();
  });
  assert.deepEqual(rules(res), []);
});

// ---------------------------------------------------------------------------
// The provenance baseline.

test('a format 1 row is accepted only with its PV1 entry', () => {
  const res = run1((fx) => ({ provenance: { ...fx.provenance, baseline_violations: fx.provenance.baseline_violations.filter((b) => b.subject !== 'format:alpha') } }));
  assert.deepEqual(rules(res), ['PV1:format:alpha']);
});

test("a new row's provenance entry is refused, so the row must pass every provenance rule", () => {
  const res = run1((fx) => {
    fx.write('delta/SKILL.md', '---\nname: delta\ndescription: Sorts sequencing barcodes\nlicense: Apache-2.0\nuser-invocable: true\n---\n\n# delta\n\nA body line unique to delta.\n');
    fx.catalog.items.push(row('delta'));
    return { provenance: { ...fx.provenance, baseline_violations: [...fx.provenance.baseline_violations, pvEntry('PV1', 'format:delta')] } };
  });
  assert.deepEqual(rules(res), ['PV1:format:delta', 'provenance-baseline:entry:PV1::format:delta']);
});

/** A one-row extension catalog for the cross-kind run, with the given baseline entries. */
function extensionCatalog(entries = []) {
  return { format: 1, items: [thirdPartyExtensionRow('exampleagent')], baseline_violations: entries, done_work_packages: [] };
}

test("the extension catalog cannot baseline a skill row: its provenance entries are refused, never applied", () => {
  const res = run1((fx) => {
    fx.write('delta/SKILL.md', '---\nname: delta\ndescription: Sorts sequencing barcodes\nlicense: Apache-2.0\nuser-invocable: true\n---\n\n# delta\n\nA body line unique to delta.\n');
    fx.catalog.items.push(row('delta'));
    return { extensions: extensionCatalog([pvEntry('PV1', 'format:delta')]) };
  });
  assert.deepEqual(rules(res), ['PV1:format:delta', 'provenance-baseline:extensions-entry:PV1::format:delta']);
  assert.match(res.errors.find((e) => e.rule === 'provenance-baseline').message, /names the skill row delta/);
  // A frozen row is refused there too: its entries belong in provenance-baseline.json.
  const frozen = run1((fx) => ({
    provenance: { ...fx.provenance, baseline_violations: fx.provenance.baseline_violations.filter((b) => b.subject !== 'format:alpha') },
    extensions: extensionCatalog([pvEntry('PV1', 'format:alpha')]),
  }));
  assert.deepEqual(rules(frozen), ['PV1:format:alpha', 'provenance-baseline:extensions-entry:PV1::format:alpha']);
  // An entry naming no row of either catalog is refused.
  assert.deepEqual(rules(run1(() => ({ extensions: extensionCatalog([pvEntry('PV1', 'format:nowhere')]) }))), ['provenance-baseline:extensions-entry:PV1::format:nowhere']);
});

test("the extension catalog's provenance entries for its own rows are landing's: passed over, never reported stale", () => {
  const res = run1(() => ({ extensions: extensionCatalog([pvEntry('PV1', 'format:exampleagent'), { rule: 'D4', subject: 'alias:extension:exampleagent', wp: 'WP-30', cross_kind: true }]) }));
  assert.deepEqual(rules(res), ['baseline:D4::alias:extension:exampleagent'], 'the provenance entry is passed over; an ordinary stale entry still fails');
  assert.ok(!res.accepted.some((a) => a.subject === 'format:exampleagent'));
});

test("a PV entry in catalog.json is refused (catalog.json is mirrored into landing)", () => {
  const res = run1((fx) => {
    fx.catalog.baseline_violations = [pvEntry('PV1', 'format:alpha')];
    return { provenance: { ...fx.provenance, baseline_violations: fx.provenance.baseline_violations.filter((b) => b.subject !== 'format:alpha') } };
  });
  assert.deepEqual(rules(res), ['PV1:format:alpha', 'provenance-baseline:catalog-entry:PV1::format:alpha']);
});

test('changed or unsorted rows are refused', () => {
  const added = run1((fx) => ({ provenance: { ...fx.provenance, rows: [...fx.provenance.rows, 'zeta'] } }));
  assert.deepEqual(rules(added), ['provenance-baseline:rows']);
  const dropped = run1((fx) => ({ provenance: { ...fx.provenance, rows: ['alpha', 'beta'], baseline_violations: fx.provenance.baseline_violations.filter((b) => b.subject !== 'format:gamma') } }));
  assert.deepEqual(rules(dropped), ['PV1:format:gamma', 'provenance-baseline:rows']);
  const unsorted = run1((fx) => ({ provenance: { ...fx.provenance, rows: ['beta', 'alpha', 'gamma'] } }));
  assert.deepEqual(rules(unsorted), ['provenance-baseline:rows']);
  // The real constants freeze the 145 rows of 2b542a8, whatever a test passes.
  assert.equal(PROVENANCE_BASELINE_ROWS, 145);
  const fx = makeFixture();
  const real = runCheck({ root: fx.root, catalog: fx.catalog, builtins: BUILTINS, frozenRows: { count: PROVENANCE_BASELINE_ROWS, sha256: PROVENANCE_BASELINE_ROWS_SHA256 } });
  assert.deepEqual(rules(real), ['provenance-baseline:rows']);
});

test('a deferral holds while the folder files wait, and is stale once they are written', () => {
  const entries = [pvEntry('PV9', 'folder:alpha', 'PROV-S4'), pvEntry('PV10', 'frontmatter:alpha', 'PROV-S4')];
  const waiting = run2((fx) => {
    const provenance = { ...fx.provenance, baseline_violations: entries };
    fx.regenerate(fx.catalog, provenance);
    assert.equal(fs.existsSync(path.join(fx.root, 'alpha/PROVENANCE.md')), false, 'a deferred row gets no PROVENANCE.md');
    return { provenance };
  });
  assert.deepEqual(rules(waiting), []);
  assert.deepEqual(waiting.accepted.map((a) => a.subject).sort(), ['folder:alpha', 'frontmatter:alpha']);
  const stale = run2((fx) => ({ provenance: { ...fx.provenance, baseline_violations: entries } }));
  assert.deepEqual(rules(stale), ['baseline:PV10::frontmatter:alpha', 'baseline:PV9::folder:alpha']);
});

test('PV9 and PV10 entries belong to PROV-S4, and every entry is a dated PV1 to PV13 entry of a frozen row', () => {
  const s1 = run2((fx) => {
    fx.remove('alpha/PROVENANCE.md');
    return { provenance: { ...fx.provenance, baseline_violations: [pvEntry('PV9', 'folder:alpha', 'PROV-S1')] } };
  });
  assert.deepEqual(rules(s1), ['PV9:folder:alpha', 'provenance-baseline:entry:PV9::folder:alpha']);
  const bad = (entry) => rules(run1((fx) => ({ provenance: { ...fx.provenance, baseline_violations: [...fx.provenance.baseline_violations.filter((b) => b.subject !== 'format:alpha'), entry] } })));
  assert.deepEqual(bad(pvEntry('PV1', 'format:alpha', 'PROV-S1', { since: '2026-11-26' })), ['PV1:format:alpha', 'provenance-baseline:entry:PV1::format:alpha']);
  assert.deepEqual(bad(pvEntry('PV1', 'format:alpha', 'PROV-S1', { since: undefined })), ['PV1:format:alpha', 'provenance-baseline:entry:PV1::format:alpha']);
  assert.deepEqual(bad(pvEntry('PV1', 'format:alpha', 'WP-17')), ['PV1:format:alpha', 'provenance-baseline:entry:PV1::format:alpha']);
  assert.deepEqual(bad(pvEntry('PV14', 'format:alpha')), ['PV1:format:alpha', 'provenance-baseline:entry:PV14::format:alpha']);
  assert.deepEqual(bad(pvEntry('licence', 'licence-SKILL.md:alpha')), ['PV1:format:alpha', 'provenance-baseline:entry:licence::licence-SKILL.md:alpha']);
});

test('PROV-S4 owns folder files only: a row rule failure under it is refused, and the failure shows', () => {
  // The mutant: a frozen row loses its contributors, and the PV12 failure is baselined as if it waited for a release.
  const hidden = run2((fx) => {
    item(fx, 'alpha').contributors = [];
    fx.regenerate();
    return { provenance: { ...fx.provenance, baseline_violations: [pvEntry('PV12', 'contributors:alpha', 'PROV-S4')] } };
  });
  assert.deepEqual(rules(hidden), ['PV12:contributors:alpha', 'provenance-baseline:entry:PV12::contributors:alpha']);
  assert.match(hidden.errors.find((e) => e.rule === 'provenance-baseline').message, /PROV-S4 owns folder files only/);
  // Every row rule subject is refused under PROV-S4; every folder file subject is taken.
  const fx = makeFixture2();
  const guard = (entry) => provenanceBaselineProblems({ ...fx.provenance, baseline_violations: [entry] }, fx.catalog, fx.frozenRows).problems.map((p) => p.subject);
  for (const [rule, subject] of [['PV1', 'origin:alpha'], ['PV4', 'adapted:alpha'], ['PV6', 'source:alpha:example-org/example-skills'], ['PV8', 'licence:alpha'],
    ['PV11', 'component:gamma/one'], ['PV12', 'contributors:alpha'], ['PV13', 'process-text:alpha:source.changes'], ['PV13', 'line:alpha']]) {
    assert.deepEqual(guard(pvEntry(rule, subject, 'PROV-S4')), [`entry:${rule}::${subject}`], `${rule} ${subject} is a row rule`);
  }
  for (const [rule, subject] of [['PV7', 'notice-copyright:alpha:example-org/example-skills'], ['PV7', 'notice-apache:alpha:p-org/plugins'], ['PV7', 'notice:alpha'],
    ['PV8', 'frontmatter-licence:alpha:SKILL.md'], ['PV9', 'folder:alpha'], ['PV10', 'frontmatter:alpha'], ['PV11', 'written-file:gamma/one:x.md'], ['PV13', 'fixed-text:alpha:SKILL.md']]) {
    assert.deepEqual(guard(pvEntry(rule, subject, 'PROV-S4')), [], `${rule} ${subject} is a folder file`);
  }
  // accept refuses the same.
  const errors = [
    { rule: 'PV12', subject: 'contributors:alpha', message: 'm1' },
    { rule: 'PV7', subject: 'notice-copyright:alpha:x/y', message: 'm2' },
    { rule: 'PV13', subject: 'fixed-text:alpha:SKILL.md', message: 'm3' },
  ];
  const plan = planAccept(errors, { wp: 'PROV-S4', since: '2026-11-28', rows: ['alpha'] });
  assert.deepEqual(plan.refused.map((r) => `${r.rule}:${r.subject}`), ['PV12:contributors:alpha']);
  assert.match(plan.refused[0].reason, /PROV-S4 owns folder files only/);
  assert.deepEqual(plan.provenanceEntries.map((e) => `${e.rule}:${e.subject}`), ['PV7:notice-copyright:alpha:x/y', 'PV13:fixed-text:alpha:SKILL.md']);
});

test("the repository's provenance baseline holds the frozen rows and passes its guard", () => {
  const real = readProvenanceBaseline(REPO_ROOT);
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  assert.equal(real.rows.length, PROVENANCE_BASELINE_ROWS);
  assert.equal(provenanceRowsDigest(real.rows), PROVENANCE_BASELINE_ROWS_SHA256);
  assert.deepEqual(provenanceBaselineProblems(real, catalog).problems, []);
  const subjects = real.baseline_violations.map((b) => `${b.rule}:${b.subject}`);
  assert.equal(new Set(subjects).size, subjects.length, 'no entry is listed twice');
  for (const fixed of ['PV7:notice:code-simplifier', 'PV7:notice:playground']) assert.ok(!subjects.includes(fixed), `${fixed} is fixed, never baselined`);
});

test("a provenance work package marked done fails its entries", () => {
  const res = run1((fx) => ({ provenance: { ...fx.provenance, done_work_packages: ['PROV-S1'] } }));
  assert.deepEqual(rules(res), ['PV1:format:alpha', 'PV1:format:beta', 'PV1:format:gamma']);
  assert.match(res.errors[0].message, /PROV-S1, which is marked done/);
});

test('without a provenance-baseline.json every format 1 row fails PV1', () => {
  const fx = makeFixture();
  fs.rmSync(path.join(fx.root, 'provenance-baseline.json'));
  const res = runCheck({ root: fx.root, catalog: fx.catalog, builtins: BUILTINS, frozenRows: fx.frozenRows });
  assert.deepEqual(rules(res), ['PV1:format:alpha', 'PV1:format:beta', 'PV1:format:gamma']);
});

test('a catalog may say format 2, and then every row is format 2', () => {
  const res = run2((fx) => {
    fx.catalog.format = 2;
    for (const r of fx.catalog.items) delete r.source.format;
    fx.regenerate();
  });
  assert.deepEqual(rules(res), []);
  const bad = run2((fx) => {
    fx.catalog.format = 3;
  });
  assert.deepEqual(rules(bad), ['row:format:catalog']);
});

// ---------------------------------------------------------------------------
// checkRowShape, merge-rows and baseline.mjs.

test('checkRowShape takes the format 2 origins and leaves sources to PV6', () => {
  const fx = makeFixture2();
  const alpha = clone(item(fx, 'alpha'));
  assert.deepEqual(checkRowShape(alpha), []);
  alpha.source.upstreams = [upstream({ repo: null, kind: 'program', url: 'https://example.org/tool' })];
  assert.deepEqual(checkRowShape(alpha), [], 'a url-only source is valid in format 2');
  alpha.source.origin = 'native';
  assert.deepEqual(checkRowShape(alpha).map((f) => f.subject), ['origin:alpha']);
  const old = row('zeta', { source: { origin: 'in-house', upstreams: [], maintained_here: false } });
  assert.deepEqual(checkRowShape(old).map((f) => f.subject), ['origin:zeta'], 'a format 1 row keeps the format 1 origins');
  delete alpha.source.format;
  alpha.source.origin = 'in-house';
  assert.deepEqual(checkRowShape(alpha, 2), [], 'in a format 2 catalog the marker is not needed');
});

test('merge-rows: a format 2 row keeps its source whole and unites contributors by name', () => {
  const fx = makeFixture2();
  const existing = clone(item(fx, 'alpha'));
  existing.contributors = [contributor({ role: 'adapted it for Biorouter' }), contributor({ name: 'Ilan Ladabaum', role: 'editor' })];
  const incoming = {
    id: 'alpha', version: '1.0.1',
    history: [{ version: '1.0.1', date: '2026-11-27', note: 'credits' }],
    source: { ...clone(existing.source), changes: 'rewritten', upstreams: [upstream({ path: 'skills/new' })] },
    contributors: [contributor({ role: 'maintains it' }), contributor({ name: 'Gianmarco Bellucci', role: 'co-wrote it' })],
  };
  const m = mergeRow(existing, incoming, fx.root);
  assert.deepEqual(m.source, incoming.source);
  assert.deepEqual(m.contributors.map((c) => `${c.name}: ${c.role}`), ['Wanjun Gu: maintains it', 'Ilan Ladabaum: editor', 'Gianmarco Bellucci: co-wrote it']);
  const plain = mergeRow(row('zeta'), { id: 'zeta', summary: 'x' }, fx.root);
  assert.equal(Object.hasOwn(plain, 'contributors'), false, 'a format 1 row gains no contributors key');
});

test('baseline.mjs: accept sends PV entries to the provenance baseline and refuses what the guard would', () => {
  const errors = [
    { rule: 'PV1', subject: 'format:alpha', message: 'm1' },
    { rule: 'PV7', subject: 'notice:alpha', message: 'm2' },
    { rule: 'D4', subject: 'alias:skill:beta', message: 'm3' },
    { rule: 'baseline', subject: 'x::y', message: 'stale' },
    { rule: 'provenance-baseline', subject: 'rows', message: 'guard' },
  ];
  const rows = ['alpha', 'beta'];
  const pv = planAccept(errors, { wp: 'PROV-S1', since: '2026-11-27', rows });
  assert.deepEqual(pv.provenanceEntries.map((e) => `${e.rule}:${e.subject}:${e.wp}:${e.since}`), ['PV1:format:alpha:PROV-S1:2026-11-27', 'PV7:notice:alpha:PROV-S1:2026-11-27']);
  assert.deepEqual(pv.catalogEntries, []);
  assert.deepEqual(pv.refused, []);
  const only = planAccept(errors, { wp: 'PROV-S1', rule: 'PV7', except: ['notice:alpha'], since: '2026-11-27', rows });
  assert.deepEqual(only.provenanceEntries, []);
  const cat = planAccept(errors, { wp: 'WP-30', since: '2026-11-27', rows });
  assert.deepEqual(cat.catalogEntries.map((e) => `${e.rule}:${e.subject}:${e.wp}`), ['D4:alias:skill:beta:WP-30']);
  assert.equal(Object.hasOwn(cat.catalogEntries[0], 'since'), false, 'catalog entries keep their shape');
  const newRow = planAccept([{ rule: 'PV1', subject: 'format:zeta', message: 'm' }], { wp: 'PROV-S1', since: '2026-11-27', rows });
  assert.deepEqual(newRow.refused.map((r) => r.subject), ['format:zeta']);
  const s1 = planAccept([{ rule: 'PV9', subject: 'folder:alpha', message: 'm' }], { wp: 'PROV-S1', since: '2026-11-27', rows });
  assert.deepEqual(s1.refused.map((r) => r.subject), ['folder:alpha']);
  assert.equal(planAccept([{ rule: 'PV9', subject: 'folder:alpha', message: 'm' }], { wp: 'PROV-S4', since: '2026-11-27', rows }).provenanceEntries.length, 1);
  assert.throws(() => planAccept(errors, { wp: 'PROV-S9', since: '2026-11-27', rows }), /PROV-S1 or PROV-S4/);
});

test('baseline.mjs: init-provenance writes rows only when the ids are the frozen ones', () => {
  const fx = makeFixture();
  const p = initProvenance(fx.catalog, null, fx.frozenRows);
  assert.deepEqual(p.rows, ['alpha', 'beta', 'gamma']);
  assert.deepEqual(Object.keys(p), ['format', 'description', 'since', 'rows', 'done_work_packages', 'baseline_violations']);
  const kept = initProvenance(fx.catalog, { ...fx.provenance, rows: [] }, fx.frozenRows);
  assert.equal(kept.baseline_violations.length, 3, 'existing entries are kept');
  const grown = clone(fx.catalog);
  grown.items.push(row('delta'));
  assert.throws(() => initProvenance(grown, null, fx.frozenRows), /frozen/);
  assert.throws(() => initProvenance(fx.catalog, null, { count: PROVENANCE_BASELINE_ROWS, sha256: PROVENANCE_BASELINE_ROWS_SHA256 }), /frozen/);
});

test('baseline.mjs: prune drops stale entries from both files, and done refuses a package that still owns entries', () => {
  const catalog = { baseline_violations: [{ rule: 'D4', subject: 'a', wp: 'WP-1' }, { rule: 'D4', subject: 'b', wp: 'WP-1', cross_kind: true }] };
  const provenance = { baseline_violations: [pvEntry('PV1', 'format:alpha'), pvEntry('PV1', 'format:beta')], done_work_packages: [] };
  const stale = [{ rule: 'baseline', subject: 'D4::a' }, { rule: 'baseline', subject: 'D4::b' }, { rule: 'baseline', subject: 'PV1::format:beta' }];
  assert.deepEqual(pruneBaselines(stale, catalog, provenance), { catalog: 1, provenance: 1 });
  assert.deepEqual(catalog.baseline_violations.map((b) => b.subject), ['b']);
  assert.deepEqual(provenance.baseline_violations.map((b) => b.subject), ['format:alpha']);
  assert.throws(() => markDone('PROV-S1', catalog, provenance), /still owns 1/);
  provenance.baseline_violations = [];
  markDone('PROV-S1', catalog, provenance);
  assert.deepEqual(provenance.done_work_packages, ['PROV-S1']);
  catalog.done_work_packages = [];
  markDone('WP-2', catalog, provenance);
  assert.deepEqual(catalog.done_work_packages, ['WP-2']);
});

test('the fixture notice text carries what PV7 asks for', () => {
  const fx = makeFixture2();
  const text = fixtureNoticeText(item(fx, 'alpha'));
  assert.ok(text.includes(MIT_LICENCE_TEXT.split('\n')[0]));
  assert.ok(text.includes('Copyright (c) 2026 Example Org'));
  assert.equal(frozenRowsFor(['b', 'a']).count, 2);
  assert.deepEqual(provenanceBaseline(['b', 'a']).rows, ['a', 'b']);
});
