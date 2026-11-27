// Mutant tests for the provenance row rules (PV1 to PV6, PV8, PV11, PV12 and
// PV13 in scripts/lib/catalog-rules.mjs) and the helpers the folder rules and
// the generators share. Each mutant changes one field of a valid format 2
// record and expects exactly one failure.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CURATED_BY, CREDIT_LINE_MAX, MADE_BY_LAB, containsCopyright, creditLine, fixedTextProblems,
  folderFilesDeferred, folderProvenanceWanted, frontmatterCredits, labCopyrightLine, missingLicenceTexts,
  noticeSources, originSentence, provenanceFormat, ruleProvenance, stubCreditLines, subjectId,
} from './lib/catalog-rules.mjs';
import {
  adaptedRow, idea, ideasDerivedRow, inHouseRow, stubRow, thirdPartyBundleRow, thirdPartyExtensionRow,
  upstream, validSkillRows,
} from './lib/fixture-provenance.mjs';

const subjects = (res) => res.failures.map((f) => `${f.rule}:${f.subject}`).sort();
const byId = (rows, id) => rows.find((r) => r.id === id);

/** The valid fixture rows with one change applied, run through the row rules. */
function mutant(change) {
  const rows = validSkillRows();
  change((id) => byId(rows, id), rows);
  return ruleProvenance(rows, { catalogFormat: 1, catalog: 'skills' });
}

test('the valid format 2 records pass with no failure and no warning', () => {
  const res = ruleProvenance(validSkillRows(), { catalogFormat: 1, catalog: 'skills' });
  assert.deepEqual(res.failures, []);
  assert.deepEqual(res.warnings, []);
});

test('a format 1 row fails PV1 format and nothing else', () => {
  const old = { ...inHouseRow('zeta'), source: { origin: 'native', upstreams: [], maintained_here: false } };
  delete old.contributors;
  assert.deepEqual(subjects(ruleProvenance([old])), ['PV1:format:zeta']);
});

test('in a format 2 catalog every row is format 2, marker or not', () => {
  const rows = validSkillRows();
  for (const r of rows) delete r.source.format;
  assert.equal(provenanceFormat(rows[0], 1), 1);
  assert.equal(provenanceFormat(rows[0], 2), 2);
  assert.deepEqual(subjects(ruleProvenance(rows, { catalogFormat: 2 })), []);
});

test('PV1: the marker, the origin and content_moved_to', () => {
  assert.deepEqual(subjects(mutant((r) => delete r('alpha').source.format)), ['PV1:format:alpha']);
  assert.deepEqual(subjects(mutant((r) => (r('epsilon').source.origin = 'native'))), ['PV1:origin:epsilon']);
  assert.deepEqual(subjects(mutant((r) => delete r('beta').source.content_moved_to)), ['PV1:moved:beta']);
  assert.deepEqual(subjects(mutant((r) => (r('beta').source.content_moved_to = 'delta'))), ['PV1:moved:beta']);
  assert.deepEqual(subjects(mutant((r) => (r('alpha').source.content_moved_to = 'beta'))), ['PV1:moved:alpha']);
  assert.deepEqual(subjects(mutant((r) => (r('alpha').notices = []))), ['PV1:field:alpha:notices']);
  assert.deepEqual(subjects(mutant((r) => (r('alpha').source.inspired_by = ['x']))), ['PV1:field:alpha:inspired_by']);
  assert.deepEqual(subjects(mutant((r) => (r('beta').history[0].origin = 'native'))), ['PV1:history:beta']);
});

test('PV2: an in-house item takes no current idea and copies nothing', () => {
  assert.deepEqual(subjects(mutant((r) => (r('epsilon').source.ideas_from = [idea()]))), ['PV2:in-house:epsilon']);
  // An earlier idea is recorded and changes nothing.
  assert.deepEqual(subjects(mutant((r) => (r('epsilon').source.ideas_from = [idea({ applies_to: 'earlier' })]))), []);
});

test('PV3: an ideas-derived item has a current idea', () => {
  const res = mutant((r) => {
    for (const i of r('delta').source.ideas_from) i.applies_to = 'earlier';
  });
  assert.deepEqual(subjects(res), ['PV3:ideas-derived:delta']);
});

test('PV4: an adapted item says what it changed', () => {
  assert.deepEqual(subjects(mutant((r) => (r('alpha').source.changes = null))), ['PV4:adapted:alpha']);
});

test('PV5: a third-party item copies, bundles or launches outside work', () => {
  assert.deepEqual(subjects(mutant((r) => (r('gamma').source.upstreams[0].use = ['dependency']))), ['PV5:third-party:gamma']);
});

test('PV6: every source is complete', () => {
  assert.deepEqual(subjects(mutant((r) => delete r('alpha').source.upstreams[0].what)), ['PV6:source:alpha:example-org/example-skills']);
  const nullCopyright = mutant((r) => {
    r('alpha').source.upstreams[0].copyright = null;
    r('alpha').source.upstreams[0].copyright_note = null;
  });
  assert.deepEqual(subjects(nullCopyright), ['PV6:source:alpha:example-org/example-skills']);
  // A holder-less licence is allowed with a note, and listed for review.
  const noted = mutant((r) => {
    r('alpha').source.upstreams[0].copyright = null;
    r('alpha').source.upstreams[0].copyright_note = 'the licence names no copyright holder';
  });
  assert.deepEqual(subjects(noted), []);
  assert.equal(noted.warnings.length, 1);
  assert.match(noted.warnings[0], /names no copyright holder/);
  assert.deepEqual(subjects(mutant((r) => delete r('delta').source.ideas_from[0].evidence)), ['PV6:idea:delta:Example Research Skills']);
  assert.deepEqual(subjects(mutant((r) => delete r('epsilon').source.data_and_services[0].credit)), ['PV6:data:epsilon:Example KG 1.0']);
});

test('PV8: the row and component licences name what ships', () => {
  assert.deepEqual(subjects(mutant((r) => (r('alpha').licence = 'Apache-2.0'))), ['PV8:licence:alpha']);
  assert.deepEqual(subjects(mutant((r) => (r('gamma').components.two.licence = 'Apache-2.0 AND MIT'))), ['PV8:component-licence:gamma/two']);
});

test('PV11: components carry their own lineage', () => {
  assert.deepEqual(subjects(mutant((r) => delete r('gamma').components.two.origin)), ['PV11:component:gamma/two']);
  assert.deepEqual(subjects(mutant((r) => (r('gamma').components.one.upstream_path = 'example-org/bio-skills/gamma/one'))), ['PV11:component:gamma/one']);
  assert.deepEqual(subjects(mutant((r) => (r('gamma').components.one.written_for_biorouter = []))), ['PV11:written:gamma/three']);
});

test('PV12: every row names the people behind its Biorouter side', () => {
  assert.deepEqual(subjects(mutant((r) => (r('epsilon').contributors = []))), ['PV12:contributors:epsilon']);
  assert.deepEqual(subjects(mutant((r) => (r('epsilon').contributors = [{ name: 'Wanjun Gu' }]))), ['PV12:contributors:epsilon']);
  const account = mutant((r) => (r('alpha').source.upstreams[0].credit = 'example-org'));
  assert.deepEqual(subjects(account), []);
  assert.match(account.warnings.join('\n'), /"example-org" is an account name/);
});

test('PV13: the credit line fits and card text carries no credit', () => {
  assert.deepEqual(subjects(mutant((r) => (r('alpha').source.upstreams[0].display = 'x'.repeat(100)))), ['PV13:line:alpha']);
  assert.deepEqual(subjects(mutant((r) => (r('alpha').summary = 'Adapted from example-skills by Example Org.'))), ['PV13:card-credit:alpha']);
  assert.deepEqual(subjects(mutant((r) => (r('alpha').summary = 'Made by the Baranzini lab.'))), ['PV13:card-credit:alpha']);
});

// ---------------------------------------------------------------------------
// One mutant for each condition the tests above do not reach on its own: a
// condition whose subject another condition can also raise is checked by its
// message, so turning it off fails the test.

const messages = (res) => res.failures.map((f) => f.message).join('\n');

test('PV1: a retired row records content_moved_to, and a history licence must be allowed', () => {
  const retired = mutant((r) => {
    r('beta').status = 'retired';
    delete r('beta').source.content_moved_to;
  });
  assert.deepEqual(subjects(retired), ['PV1:moved:beta']);
  assert.match(messages(retired), /content_moved_to is missing/);
  assert.deepEqual(subjects(mutant((r) => (r('beta').history[0].licence = 'GPL-3.0'))), ['PV1:history:beta']);
  assert.match(messages(mutant((r) => (r('beta').history[0].licence = 'GPL-3.0'))), /has licence "GPL-3\.0"/);
});

test('PV6: each condition of a source fails on its own', () => {
  const src = (change) => mutant((r) => change(r('alpha').source.upstreams[0], r('alpha')));
  const noPlace = src((u) => {
    u.repo = null;
    u.url = null;
  });
  assert.deepEqual(subjects(noPlace), ['PV6:source:alpha:example-skills']);
  assert.match(messages(noPlace), /no repo or url/);
  const unpinned = src((u) => {
    u.commit = null;
    u.version = null;
  });
  assert.deepEqual(subjects(unpinned), ['PV6:source:alpha:example-org/example-skills']);
  assert.match(messages(unpinned), /needs a commit or a version/);
  const gpl = src((u, row) => {
    u.licence = 'GPL-3.0';
    row.licence = 'Apache-2.0 AND GPL-3.0';
  });
  assert.deepEqual(subjects(gpl), ['PV6:source:alpha:example-org/example-skills']);
  assert.match(messages(gpl), /licence GPL-3\.0 may not be copied or bundled/);
  const uncredited = src((u) => delete u.credit);
  assert.deepEqual(subjects(uncredited), ['PV6:source:alpha:example-org/example-skills']);
  assert.match(messages(uncredited), /no credit/);
  // A source that is only a dependency owes no pin.
  assert.deepEqual(subjects(src((u, row) => {
    u.commit = null;
    u.use = ['dependency'];
    row.source.upstreams.push(upstream({ path: 'skills/kept' }));
  })), []);
});

test('PV6: references, refused sources and the ideas of components and written files are complete', () => {
  const ref = mutant((r) => (r('alpha').source.references = [{ name: 'A Paper' }]));
  assert.deepEqual(subjects(ref), ['PV6:reference:alpha:A Paper']);
  const refused = mutant((r) => (r('alpha').source.refused_sources = [{ repo: 'other-org/other-skills' }]));
  assert.deepEqual(subjects(refused), ['PV6:refused:alpha:other-org/other-skills']);
  assert.deepEqual(subjects(mutant((r) => (r('alpha').source.refused_sources = [{ repo: 'other-org/other-skills', reason: 'GPL-3.0' }]))), []);
  assert.deepEqual(subjects(mutant((r) => delete r('gamma').components.three.ideas_from[0].evidence)), ['PV6:idea:gamma/three:Example Tool Skill']);
  assert.deepEqual(subjects(mutant((r) => delete r('gamma').components.one.written_for_biorouter[0].ideas_from[0].credit)), ['PV6:idea:gamma/one:Example Tool Skill']);
});

test("PV8: the lab's own text is Apache-2.0, and so is every file written for Biorouter", () => {
  const own = mutant((r) => (r('epsilon').licence = 'MIT'));
  assert.deepEqual(subjects(own), ['PV8:licence:epsilon']);
  assert.match(messages(own), /Apache-2\.0 \(the lab's own text\)/);
  const written = mutant((r) => (r('gamma').components.one.written_for_biorouter[0].licence = 'MIT'));
  assert.deepEqual(subjects(written), ['PV8:component-licence:gamma/one']);
  assert.match(messages(written), /written file references\/merged-notes\.md must be Apache-2\.0/);
});

test('PV11: an upstream_path names an upstream of the row, and sources are indexes into its upstreams', () => {
  const elsewhere = mutant((r) => (r('gamma').components.one.upstream_path = 'other-org/other-skills:gamma/one'));
  assert.deepEqual(subjects(elsewhere), ['PV11:component:gamma/one']);
  assert.match(messages(elsewhere), /names other-org\/other-skills, which is not an upstream of the row/);
  const range = mutant((r) => (r('gamma').components.two.sources = [5]));
  assert.deepEqual(subjects(range), ['PV11:component:gamma/two']);
  assert.match(messages(range), /sources must be indexes/);
});

// ---------------------------------------------------------------------------
// creditLine and the origin sentences.

const one = (u) => upstream({ copyright: 'Copyright (c) 2026 X', ...u });

test('creditLine reproduces the audit examples', () => {
  const medsci = adaptedRow('phi', { source: { ...adaptedRow().source, upstreams: [one({ repo: 'Aperivue/medsci-skills', display: 'medsci-skills', credit: 'Aperivue', use: ['code', 'text'] })] } });
  assert.equal(creditLine(medsci), 'Adapted from medsci-skills by Aperivue (MIT).');
  const bio = thirdPartyBundleRow('align');
  bio.source.upstreams = [one({ repo: 'GPTomics/bioSkills', display: 'bioSkills', credit: 'GPTomics' })];
  assert.equal(creditLine(bio), 'From bioSkills by GPTomics (MIT), packaged for Biorouter by the Baranzini Lab.');
  const biomcp = thirdPartyExtensionRow('biomcpagent');
  biomcp.source.upstreams = [one({ kind: 'package', repo: 'genomoncology/biomcp', display: 'BioMCP', version: '0.9.3', commit: null, credit: 'Ian Maurer', use: ['launched'] })];
  assert.equal(creditLine(biomcp, { catalog: 'extensions' }), 'Runs BioMCP 0.9.3 by Ian Maurer (MIT); extension by the Baranzini Lab.');
  assert.equal(creditLine(inHouseRow('cdwagent')), MADE_BY_LAB);
  const kdense = adaptedRow('scientific-data-engineering');
  const k = (over) => one({ repo: 'K-Dense-AI/scientific-agent-skills', display: 'Scientific Agent Skills', credit: 'K-Dense Inc.', ...over });
  kdense.source.upstreams = [k({ path: 'a' }), k({ path: 'b', licence: 'BSD-3-Clause' }), k({ path: 'c' }), one({ repo: 'o1/r1', display: 'r1' }), one({ repo: 'o2/r2', display: 'r2' })];
  assert.equal(creditLine(kdense), 'Adapted from Scientific Agent Skills by K-Dense Inc. (MIT, BSD-3-Clause) and 2 more.');
});

test('creditLine for ideas-derived and the extension fixture', () => {
  assert.equal(creditLine(ideasDerivedRow('delta')), 'Made by the Baranzini Lab (Wanjun Gu, UCSF), with ideas from Example Research Skills (Example Lab).');
  assert.equal(creditLine(thirdPartyExtensionRow()), 'Runs Example MCP 0.9.3 by Ada Example (MIT); extension by the Baranzini Lab.');
  assert.equal(originSentence(thirdPartyExtensionRow()), 'The program below does the work; the Baranzini Lab wrote the extension around it.');
  assert.equal(originSentence(inHouseRow()), 'Original work of the Baranzini Lab.');
});

test('creditLine drops "and N more" first above 120 characters, and PV13 fails what is still too long', () => {
  const row = (len) => {
    const r = adaptedRow('alpha');
    r.source.upstreams = [one({ display: 'n'.repeat(len) }), one({ repo: 'o1/r1', display: 'r1' }), one({ repo: 'o2/r2', display: 'r2' })];
    return r;
  };
  const fits = creditLine(row(70));
  assert.ok(fits.endsWith(' and 2 more.') && fits.length <= CREDIT_LINE_MAX, fits);
  const cut = creditLine(row(80));
  assert.equal(cut, `Adapted from ${'n'.repeat(80)} by Example Org (MIT).`);
  assert.ok(cut.length <= CREDIT_LINE_MAX);
  const long = row(100);
  assert.ok(creditLine(long).length > CREDIT_LINE_MAX);
  assert.deepEqual(subjects(ruleProvenance([long])), ['PV13:line:alpha']);
});

test('a broken record gets a "not yet recorded" line, never the lab line', () => {
  const r = adaptedRow('alpha');
  r.source.upstreams = [];
  assert.equal(creditLine(r), 'Adapted from a source not yet recorded.');
});

test('frontmatterCredits gives a component with its own origin its own line', () => {
  const g = thirdPartyBundleRow('gamma');
  assert.deepEqual(frontmatterCredits(g, 'two/SKILL.md'), { origin: 'in-house', credit: MADE_BY_LAB, curated_by: CURATED_BY });
  assert.equal(frontmatterCredits(g, 'one/SKILL.md').credit, creditLine(g));
  assert.equal(frontmatterCredits(g, 'one/SKILL.md').origin, 'third-party');
  assert.equal(frontmatterCredits(adaptedRow('alpha')).origin, 'adapted');
});

test('stubCreditLines names the last real content and where it lives', () => {
  const rows = validSkillRows();
  assert.deepEqual(stubCreditLines(byId(rows, 'beta'), rows), [
    'Earlier versions: Adapted from example-skills by Example Org (MIT). Its content now lives in Alpha (alpha).',
    CURATED_BY,
  ]);
  const gone = stubRow('beta', 'alpha', { status: 'retired' });
  gone.source.content_moved_to = null;
  assert.match(stubCreditLines(gone, rows)[0], /Its content was not carried forward\.$/);
});

// ---------------------------------------------------------------------------
// Subjects and the baseline helpers.

test('subjectId reads the row id of every subject shape', () => {
  assert.equal(subjectId('format:alpha'), 'alpha');
  assert.equal(subjectId('component:gamma/two'), 'gamma');
  assert.equal(subjectId('idea:gamma/one:Example Tool Skill'), 'gamma');
  assert.equal(subjectId('notice-copyright:code-review:anthropics/claude-plugins-official'), 'code-review');
  assert.equal(subjectId('frontmatter-licence:gamma:one/SKILL.md'), 'gamma');
  assert.equal(subjectId('written-file:gamma/one:references/merged-notes.md'), 'gamma');
  assert.equal(subjectId('folder:scientific-artifacts'), 'scientific-artifacts');
  assert.equal(subjectId('format'), null);
  assert.equal(subjectId('format:Alpha'), null);
  assert.equal(subjectId(undefined), null);
});

test('folderFilesDeferred reads only a PV9 folder entry', () => {
  const baseline = { baseline_violations: [{ rule: 'PV9', subject: 'folder:alpha', wp: 'PROV-S4' }, { rule: 'PV10', subject: 'frontmatter:beta', wp: 'PROV-S4' }] };
  assert.equal(folderFilesDeferred(baseline, 'alpha'), true);
  assert.equal(folderFilesDeferred(baseline, 'beta'), false);
  assert.equal(folderFilesDeferred(null, 'alpha'), false);
  const row = adaptedRow('alpha');
  assert.equal(folderProvenanceWanted(row, { catalogFormat: 1, baseline }), false);
  assert.equal(folderProvenanceWanted(adaptedRow('gamma'), { catalogFormat: 1, baseline }), true);
  delete row.source.format;
  assert.equal(folderProvenanceWanted(row, { catalogFormat: 1 }), false, 'a format 1 row writes no folder files');
  assert.equal(folderProvenanceWanted(row, { catalogFormat: 2 }), true, 'in a format 2 catalog the row is format 2, and nothing defers it');
  assert.equal(folderProvenanceWanted(row, { catalogFormat: 2, baseline }), false, 'its PV9 entry defers it');
});

test('fixedTextProblems flags variants of the fixed texts and keeps verbatim upstream lines', () => {
  assert.deepEqual(fixedTextProblems(`${CURATED_BY}\n${MADE_BY_LAB}\n${labCopyrightLine(2026)}\n`), []);
  const lines = (t, o) => fixedTextProblems(t, o).map((p) => p.line);
  assert.deepEqual(lines('ok\nCurated and organised by Wanjun Gu.\n'), [2]);
  assert.deepEqual(lines('Made by the Baranzini lab (Wanjun Gu).'), [1]);
  assert.deepEqual(lines('Copyright 2026 The Regents of the University of California'), [1]);
  assert.deepEqual(lines('Copyright (c) 2026 Wanjun Gu'), [1]);
  assert.deepEqual(lines('Copyright (c) 2026 Wanjun Gu', { allowed: ['Copyright (c) 2026 Wanjun Gu'] }), []);
  assert.deepEqual(lines('Copyright (c) 2026 Example Org'), [], 'a third party line is not the lab line');
});

// ---------------------------------------------------------------------------
// The PV7 helpers the folder rule calls.

test('noticeSources: format 1 keeps the old rule and adds adapted Apache sources; format 2 takes shipped sources', () => {
  const f1 = (origin, licence) => ({ id: 'x', source: { origin, upstreams: [{ repo: 'a/b', licence }] } });
  assert.equal(noticeSources(f1('adapted', 'MIT')).length, 1);
  assert.equal(noticeSources(f1('adapted', 'Apache-2.0')).length, 1);
  assert.equal(noticeSources(f1('lab', 'Apache-2.0')).length, 0);
  assert.equal(noticeSources(f1('native', 'CC0-1.0')).length, 0);
  const f2 = adaptedRow('alpha');
  assert.equal(noticeSources(f2).length, 1);
  f2.source.upstreams.push(upstream({ repo: 'a/cc0', licence: 'CC0-1.0' }), upstream({ repo: 'lab/own', licence: 'Apache-2.0', owner: 'lab' }), upstream({ repo: 'a/dep', use: ['dependency'] }));
  assert.deepEqual(noticeSources(f2).map((u) => u.repo), ['example-org/example-skills']);
});

test('missingLicenceTexts and containsCopyright compare case-blind with whitespace collapsed', () => {
  const mit = 'MIT License\n\nPermission is hereby granted, free of charge,\n  to any person obtaining a copy\n';
  assert.deepEqual(missingLicenceTexts(mit, ['MIT']), []);
  assert.deepEqual(missingLicenceTexts('MIT License', ['MIT']), ['MIT']);
  assert.deepEqual(missingLicenceTexts('TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION', ['Apache-2.0']), ['Apache-2.0']);
  assert.deepEqual(missingLicenceTexts('', ['CC0-1.0']), []);
  assert.deepEqual(missingLicenceTexts('', ['GPL-3.0']), ['GPL-3.0']);
  assert.equal(containsCopyright('a\nCopyright (c)   2026\nExample Org\n', 'Copyright (c) 2026 Example Org'), true);
  assert.equal(containsCopyright('Copyright (c) 2025 Example Org', 'Copyright (c) 2026 Example Org'), false);
});
