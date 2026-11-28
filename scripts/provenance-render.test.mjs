// Tests for the provenance generators: PROVENANCE.md, the README provenance
// blocks, the NOTICE fixes, the stub's credit lines, setMetadata, and the
// --check of render-readme.mjs and write-stubs.mjs on a throwaway repository.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import {
  CURATED_BY,
  MADE_BY_LAB,
  ORIGIN_SENTENCES,
  creditLine,
  frontmatterCredits,
  labCopyrightLine,
  processWordingProblems,
  stubCreditLines,
} from './lib/catalog-rules.mjs';
import {
  adaptedRow,
  contributor,
  dataset,
  idea,
  ideasDerivedRow,
  inHouseRow,
  stubRow,
  thirdPartyBundleRow,
  upstream,
  validSkillRows,
} from './lib/fixture-provenance.mjs';
import { GENERATED_MARK, PROVENANCE_FILE, mdCode, mdLink, mdText, oneLine, renderProvenanceMd } from './lib/provenance-md.mjs';
import { parseFrontmatter, readSkillText, retiredMetadataKey, setMetadata, splitFrontmatter } from './lib/frontmatter.mjs';
import { STUB_LAST_BULLET, stubFiles } from './lib/stub.mjs';
import { REPO_ROOT } from './lib/repo.mjs';
import { readProvenanceBaseline } from './lib/provenance-baseline.mjs';
import { renderNotice, renderSections } from './render-readme.mjs';

const EM_DASH = String.fromCharCode(0x2014);
const catalogOf = (items) => ({ format: 1, items });

function noLeaks(text, label) {
  assert.doesNotMatch(text, /\bnull\b|\bundefined\b|\[object Object\]/, `${label} prints a missing value`);
  assert.ok(!text.includes(EM_DASH), `${label} uses an em dash`);
}

function sections(md) {
  return md.split('\n').filter((l) => l.startsWith('## ') || l.startsWith('### ')).map((l) => l.replace(/^#+ /, ''));
}

// ---------------------------------------------------------------------------
// PROVENANCE.md

test('PROVENANCE.md, in-house: credit, origin, data and services, contributors, licences, curator line last', () => {
  const row = inHouseRow('epsilon', { contributors: [contributor(), contributor({ name: 'Gianmarco Bellucci', role: 'co-wrote it' })] });
  const md = renderProvenanceMd(row, catalogOf([row]));
  const lines = md.split('\n');
  assert.equal(lines[0], '# Provenance and credits: Epsilon');
  assert.ok(md.includes(GENERATED_MARK));
  assert.ok(md.includes(`\n${MADE_BY_LAB}\n`));
  assert.ok(md.includes(`\n${ORIGIN_SENTENCES['in-house']}\n`));
  assert.deepEqual(sections(md), ['Data and services', 'Contributors', 'Licences']);
  assert.match(md, /\[Example KG 1\.0\]\(https:\/\/doi\.org\/10\.0000\/example\), a dataset by A\. Author, B\. Author\. Terms: CC0-1\.0\. How it is used: downloaded once on request, not bundled\. Cite: An example knowledge graph/);
  assert.match(md, /- Wanjun Gu, Baranzini Lab, UCSF: wrote it\n- Gianmarco Bellucci, Baranzini Lab, UCSF: co-wrote it/);
  assert.ok(md.includes(labCopyrightLine('2026')));
  assert.ok(md.endsWith(`\n${CURATED_BY}\n`), 'the curator line is last');
  assert.ok(!md.endsWith('\n\n'));
  noLeaks(md, 'in-house');
});

test('PROVENANCE.md, ideas-derived: current ideas under Ideas, earlier ones under Earlier versions', () => {
  const row = ideasDerivedRow('delta');
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.ok(md.includes(`\n${creditLine(row)}\n`));
  assert.ok(md.includes(ORIGIN_SENTENCES['ideas-derived']));
  assert.deepEqual(sections(md), ['Ideas', 'Contributors', 'Earlier versions', 'Licences']);
  const ideas = md.slice(md.indexOf('## Ideas'), md.indexOf('## Contributors'));
  assert.match(ideas, /\[Example Research Skills\]\(https:\/\/github\.com\/example-lab\/example-research-skills\), a repository by Example Lab \(CC-BY-SA-4\.0\): the stage list and the idea of a gate per stage\. Ideas only, no text or code taken: 0 shared six-word runs/);
  assert.ok(!ideas.includes('Earlier Skill List'), 'an earlier idea is not a current one');
  const earlier = md.slice(md.indexOf('## Earlier versions'), md.indexOf('## Licences'));
  assert.match(earlier, /Ideas for an earlier version: \[Earlier Skill List\]\(https:\/\/github\.com\/example-lab\/earlier\), a repository by Example Lab \(CC-BY-SA-4\.0\): the topic of version 1\.0\.0\. Ideas only, no text or code taken/);
  noLeaks(md, 'ideas-derived');
});

test('PROVENANCE.md, adapted: a sources table with every column, the changes and where the licence texts are', () => {
  const row = adaptedRow('alpha');
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.ok(md.includes('Adapted from example-skills by Example Org (MIT).'));
  assert.deepEqual(sections(md), ['Sources', 'Contributors', 'Licences']);
  assert.ok(md.includes('| Source | Commit or version | Licence | Credit and people | Use and what | Files | Via |\n|---|---|---|---|---|---|---|'));
  assert.ok(md.includes('| [example-skills](https://github.com/example-org/example-skills): `example-org/example-skills`, `skills/example` | commit `0123456789ab`, taken 2026-11-25 | MIT; Copyright (c) 2026 Example Org | Example Org | text: the example SKILL.md and its references | `SKILL.md` |  |'));
  assert.ok(md.includes('Changes for Biorouter: SKILL.md rewritten for Biorouter; one script kept unchanged.'));
  assert.ok(md.includes('The copyright lines and licence texts of its sources are in LICENSE-UPSTREAM.'));
  assert.ok(md.includes('The item as a whole is licensed under Apache-2.0 AND MIT.'));
  noLeaks(md, 'adapted');
});

test('PROVENANCE.md: table cells are escaped, a holder-less source is flagged, via and an upstream NOTICE are shown', () => {
  const row = adaptedRow('alpha', {
    source: {
      ...adaptedRow('alpha').source,
      upstreams: [
        upstream({ credit: 'Pipe | Org', people: ['Ada Lovelace', 'Alan Turing'], what: 'two\nlines', copyright: null, copyright_note: 'the licence names no holder', licence: 'Apache-2.0', upstream_notice: true, via: 'origin-org/origin-skills' }),
        upstream({ repo: 'origin-org/origin-skills', display: null, url: null, path: null, commit: null, version: '2.1.0', use: ['dependency'], what: 'installed at run time', files: [], credit: 'Origin Org', copyright: null }),
      ],
    },
  });
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.ok(md.includes('Pipe \\| Org; people: Ada Lovelace, Alan Turing'), 'a pipe in a cell is escaped');
  assert.ok(md.includes('text: two lines'), 'a newline in a cell is a space');
  assert.ok(md.includes('Apache-2.0; no copyright line: the licence names no holder; its NOTICE file ships with this item'));
  // example-skills draws on origin-skills (its via), so origin-skills was reached through example-skills.
  assert.ok(md.includes('| origin-skills: `origin-org/origin-skills` | version 2.1.0, taken 2026-11-25 | MIT | Origin Org | dependency: installed at run time |  | `example-org/example-skills` |'), 'a url-less source is not linked, an empty list is an empty cell, and Via names the source it was reached through');
  assert.ok(md.split('\n').find((l) => l.startsWith('| [example-skills]')).endsWith('| `SKILL.md` |  |'), 'the source that draws on another was not reached through it');
  assert.ok(md.includes('LICENSE-UPSTREAM also reproduces the NOTICE file of example-org/example-skills, as section 4(d) of the Apache License asks.'));
  noLeaks(md, 'escaping');
});

test('Markdown helpers: an untrusted value stays text, a code span holds its backticks, a link destination cannot be broken', () => {
  assert.equal(mdLink('x', 'https://a.b/c>d)e'), '[x](https://a.b/c%3Ed%29e)');
  assert.equal(mdLink('A (b)', 'https://en.wikipedia.org/wiki/A_(b)'), '[A (b)](https://en.wikipedia.org/wiki/A_%28b%29)');
  assert.equal(mdLink('<x>', 'https://a.b/<script>'), '[\\<x\\>](https://a.b/%3Cscript%3E)');
  assert.equal(mdLink('[x](y)', 'ftp://x'), '\\[x\\](y)', 'a label is escaped, and a URL that is not http(s) is not linked');
  assert.equal(mdText('`a` *b* <b>c</b> ~d~ [e](f)'), '\\`a\\` \\*b\\* \\<b\\>c\\</b\\> \\~d\\~ \\[e\\](f)');
  assert.equal(mdText('_e_ snake_case a\\b'), '\\_e\\_ snake_case a\\\\b', 'an underscore inside a word stays as written');
  assert.equal(mdText('AT&T &amp; &#169;'), 'AT&T &amp;amp; &amp;#169;');
  assert.equal(mdText('two\nlines'), 'two lines');
  assert.equal(oneLine('a\n *b* <c>'), 'a *b* <c>', 'plain text is left alone');
  assert.equal(mdCode('plain'), '`plain`');
  assert.equal(mdCode('a`b'), '``a`b``');
  assert.equal(mdCode('`x`'), '`` `x` ``');
  assert.equal(mdCode('a ``` b'), '````a ``` b````');
});

test('PROVENANCE.md, README and NOTICE: hostile upstream values cannot add markup', () => {
  const hostile = {
    credit: 'Evil <img src=x onerror=alert(1)> `Org`',
    what: 'see [here](https://evil.example) **now**',
    path: 'skills/`x`',
    url: 'https://a.b/c>d)e',
    people: ['<b>Mallory</b>'],
  };
  const row = adaptedRow('alpha', { source: { ...adaptedRow('alpha').source, upstreams: [upstream(hostile)] } });
  const md = renderProvenanceMd(row, catalogOf([row]));
  const rawTag = /(^|[^\\])<(img|b>|\/b>)/m;
  assert.doesNotMatch(md, rawTag, 'raw HTML is escaped');
  assert.doesNotMatch(md, /(^|[^\\])\]\(https:\/\/evil/m, 'a link written in a value is not a link');
  assert.ok(md.includes('see \\[here\\](https://evil.example)'));
  assert.ok(!md.includes('**now**'), 'emphasis written in a value is escaped');
  assert.ok(md.includes(mdCode('skills/`x`')), 'a path with a backtick keeps a whole code span');
  assert.ok(md.includes('(https://a.b/c%3Ed%29e)'), 'the link destination is encoded');
  assert.ok(md.includes(mdText(creditLine(row))), 'the credit line is escaped as prose');
  const readme = renderSections(catalogOf([row])).provenance;
  assert.ok(!rawTag.test(readme) && readme.includes('Evil \\<img src=x onerror=alert(1)\\> \\`Org\\`'));
  const notice = renderNotice(catalogOf([row]));
  assert.ok(notice.includes('Credited to Evil <img src=x onerror=alert(1)> `Org`, with <b>Mallory</b>.'), 'NOTICE is plain text: values as written, no escapes');
});

test('PROVENANCE.md, bundle: one file, a section per component that is not plain copied material', () => {
  const row = thirdPartyBundleRow('gamma');
  row.components.four = { name: 'gamma-four', status: 'active', job: 'test.gamma.four', upstream_path: 'example-org/bio-skills:gamma/four', licence: 'MIT', sources: [0] };
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.ok(md.includes('From bioSkills by Example Org (MIT), packaged for Biorouter by the Baranzini Lab.'));
  assert.deepEqual(sections(md), ['Sources', 'Written for Biorouter', 'one (`gamma-one`)', 'two (`gamma-two`)', 'three (`gamma-three`)', 'Contributors', 'Licences']);
  assert.ok(md.includes('Components kept from these sources: `four` (`example-org/bio-skills:gamma/four`).'));
  assert.ok(md.includes('Maintained in this repository: the copy is not resynced from its source.'));
  const one = md.slice(md.indexOf('### one'), md.indexOf('### two'));
  assert.match(one, /Licence: MIT\. Status: active\. Source path: `example-org\/bio-skills:gamma\/one`\./);
  assert.match(one, /- `one\/references\/merged-notes\.md`: notes merged from the old three component\. Ideas-derived, Apache-2\.0\. Ideas from \[Example Tool Skill\]\(https:\/\/github\.com\/example-lab\/tool-skill\), a skill by Example Lab \(CC-BY-SA-4\.0\): which tool to teach\./);
  const two = md.slice(md.indexOf('### two'), md.indexOf('### three'));
  assert.ok(two.includes(MADE_BY_LAB));
  assert.ok(two.includes(ORIGIN_SENTENCES['in-house']));
  assert.ok(two.includes('Licence: Apache-2.0. Status: active.'));
  const three = md.slice(md.indexOf('### three'), md.indexOf('## Contributors'));
  assert.ok(three.includes('Made by the Baranzini Lab (Wanjun Gu, UCSF), with ideas from Example Tool Skill (Example Lab).'));
  assert.ok(three.includes('Status: merged into `gamma/one`. Its content now lives in `gamma/one/references/merged-notes.md`.'));
  assert.ok(three.includes('Ideas from [Example Tool Skill](https://github.com/example-lab/tool-skill), a skill by Example Lab (CC-BY-SA-4.0): which tool to teach. Ideas only, no text or code taken: 0 shared six-word runs with the version read.'));
  assert.equal(md.split(CURATED_BY).length, 2, 'the curator line appears once');
  noLeaks(md, 'bundle');
});

test('PROVENANCE.md, stub row: earlier versions from history, and where the content now lives', () => {
  const rows = validSkillRows();
  const row = rows.find((r) => r.id === 'beta');
  const md = renderProvenanceMd(row, catalogOf(rows));
  assert.ok(md.includes(stubCreditLines(row, rows)[0]));
  assert.match(md, /- 1\.0\.0 \(2026-06-10\): adapted, licensed under MIT\./);
  assert.match(md, /- 1\.1\.0 \(2026-11-22\): adapted, licensed under Apache-2\.0\./);
  assert.ok(md.includes(labCopyrightLine('2026')), 'the year is the first history entry\'s');
  noLeaks(md, 'stub');
});

test('PROVENANCE.md: references, a cite-only idea, missing terms and the first history year', () => {
  const row = inHouseRow('epsilon', {
    history: [{ version: '1.0.0', date: '2025-03-01' }, { version: '1.1.0', date: '2026-11-22', origin: 'in-house', licence: 'Apache-2.0', note: 'rebuilt' }],
    version: '1.1.0',
    source: {
      ...inHouseRow('epsilon').source,
      references: [{ name: 'DESeq2', url: 'https://bioconductor.org/packages/DESeq2', cite: 'Love MI et al. Genome Biology 15, 550 (2014).', credit: 'Michael Love, Wolfgang Huber, Simon Anders' }],
      data_and_services: [dataset({ terms: null, cite: null, how: null })],
      ideas_from: [idea({ kind: 'paper', url: null, cite: 'A Paper. Journal 1 (2020).', applies_to: 'earlier', version_read: 'v2' })],
    },
  });
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.match(md, /## References\n\n- \[DESeq2\]\(https:\/\/bioconductor\.org\/packages\/DESeq2\), by Michael Love, Wolfgang Huber, Simon Anders\. Cite: Love MI et al\./);
  assert.match(md, /a dataset by A\. Author, B\. Author\. Terms: not recorded\.\n/);
  assert.match(md, /Ideas for an earlier version: Example Research Skills, a paper by Example Lab \(CC-BY-SA-4\.0\): the stage list and the idea of a gate per stage\. Ideas only, no text or code taken: 0 shared six-word runs with the version read\. Version read: v2\. Cite: A Paper\. Journal 1 \(2020\)\./);
  assert.match(md, /- 1\.1\.0 \(2026-11-22\): in-house, licensed under Apache-2\.0\. Note: rebuilt\./);
  assert.ok(md.includes(labCopyrightLine('2025')));
  noLeaks(md, 'references');
});

// ---------------------------------------------------------------------------
// README blocks

function formatOneRow(id, source, over = {}) {
  return {
    id, display_name: id, kind: 'skill', category: 'core', path: id, version: '1.0.0', status: 'active', aliases: [], job: `test.${id}`,
    summary: '', keywords: [], invocation: 'user', distinct_from: [], licence: 'Apache-2.0', notice_file: null,
    release: { tag: `skill-${id}`, asset: `${id}.zip`, sha256: null }, components: null, history: [{ version: '1.0.0', date: '2026-07-01' }],
    source: { origin: 'native', upstreams: [], maintained_here: false, ...source }, ...over,
  };
}

test('README: provenance blocks for a mixed catalog, format 2 by origin and source groups, format 1 not yet classified', () => {
  const items = [
    formatOneRow('lab-one', { origin: 'lab' }),
    formatOneRow('native-one', { inspired_by: ['a-org/a-skills', 'b-org/b-skills'] }),
    formatOneRow('adapted-one', {
      origin: 'adapted',
      upstreams: [
        { repo: 'k-org/k-skills', path: 'x', commit: 'abc1234', licence: 'MIT', copyright: 'Copyright (c) 2025 K' },
        { repo: 'k-org/k-skills', path: 'y', commit: 'abc1234', licence: 'BSD-3-Clause', copyright: 'Copyright (c) 2025 K' },
        { repo: 'k-org/k-skills', path: 'z', commit: 'abc1234', licence: 'MIT', copyright: 'Copyright (c) 2025 K' },
      ],
    }, { licence: 'Apache-2.0 AND MIT AND BSD-3-Clause' }),
    adaptedRow('alpha'),
    adaptedRow('alpha-two'),
    inHouseRow('epsilon'),
    ideasDerivedRow('delta'),
    thirdPartyBundleRow('gamma'),
    stubRow('beta', 'alpha'),
  ];
  const s = renderSections(catalogOf(items));
  assert.ok(!('sources' in s), 'the sources block is gone');
  const p = s.provenance;
  assert.ok(p.startsWith('| Skills | Origin | Sources and credit | Licence |\n|---|---|---|---|\n'));
  assert.ok(p.includes('| `lab-one` | Not yet classified | Lab-original | Apache-2.0 |'));
  assert.ok(p.includes('| `native-one` | Not yet classified | Native rewrite inspired by [a-org/a-skills](https://github.com/a-org/a-skills) and [b-org/b-skills](https://github.com/b-org/b-skills); no upstream text copied | Apache-2.0 |'));
  assert.ok(p.includes('[k-org/k-skills](https://github.com/k-org/k-skills) (MIT, BSD-3-Clause)'), 'every distinct licence of one repository');
  assert.ok(p.includes('| `alpha`, `alpha-two` | Adapted | [example-skills](https://github.com/example-org/example-skills) by Example Org (MIT) | Apache-2.0 AND MIT |'), 'rows with the same sources are grouped');
  assert.ok(p.includes(`| \`epsilon\` | In-house | ${MADE_BY_LAB} | Apache-2.0 |`));
  assert.ok(p.includes(`| \`delta\` | Ideas-derived | ${creditLine(ideasDerivedRow('delta'))} | Apache-2.0 |`));
  assert.ok(p.includes('| `gamma` | Third-party | [bioSkills](https://github.com/example-org/bio-skills) by Example Org (MIT) | Apache-2.0 AND MIT |'));
  assert.ok(!p.includes('`beta`'), 'only active rows are listed');
  const ideas = s['provenance-ideas'];
  assert.ok(ideas.startsWith('| Skills | Ideas | References | Earlier versions |\n|---|---|---|---|\n'));
  assert.ok(ideas.includes('| `native-one` | [a-org/a-skills](https://github.com/a-org/a-skills), [b-org/b-skills](https://github.com/b-org/b-skills) |  |  |'), 'format 1 inspired_by as recorded');
  assert.ok(ideas.includes('| `delta` | [Example Research Skills](https://github.com/example-lab/example-research-skills) (Example Lab) |  | Ideas from [Earlier Skill List](https://github.com/example-lab/earlier) (Example Lab) |'));
  assert.ok(ideas.includes('| `gamma` | `one/references/merged-notes.md`: [Example Tool Skill](https://github.com/example-lab/tool-skill) (Example Lab); `three`: [Example Tool Skill](https://github.com/example-lab/tool-skill) (Example Lab) |  |  |'));
  assert.ok(!ideas.includes('`epsilon`') && !ideas.includes('`alpha`'), 'rows with nothing to show are left out');
  for (const [name, body] of Object.entries(s)) noLeaks(body, `README block ${name}`);
});

test("README: a lab-owned source with no licence file makes no licence claim, as NOTICE and PROVENANCE.md say", () => {
  const lab = upstream({ repo: 'lab-org/lab-skills', display: 'lab-skills', url: 'https://github.com/lab-org/lab-skills', path: 'SKILL.md', copyright: null,
    copyright_note: "the Baranzini Lab's own work", credit: 'Baranzini Lab (Wanjun Gu, UCSF)', owner: 'lab', licence_file: false });
  const row = adaptedRow('alpha', { source: { ...adaptedRow('alpha').source, upstreams: [upstream(), lab] } });
  const p = renderSections(catalogOf([row])).provenance;
  assert.ok(p.includes('[lab-skills](https://github.com/lab-org/lab-skills) by Baranzini Lab (Wanjun Gu, UCSF) (no licence file in its repository)'), p);
  assert.ok(p.includes('[example-skills](https://github.com/example-org/example-skills) by Example Org (MIT)'), 'a source with a licence file keeps its licence');
  assert.ok(!/lab-skills\][^|]*\(MIT\)/.test(p), 'no licence is claimed for the lab source');
  // The same row with a licence file names its licence.
  const withFile = adaptedRow('alpha', { source: { ...adaptedRow('alpha').source, upstreams: [upstream(), { ...lab, licence_file: undefined }] } });
  assert.ok(renderSections(catalogOf([withFile])).provenance.includes('by Baranzini Lab (Wanjun Gu, UCSF) (MIT)'));
});

test('README and PROVENANCE.md: the people an idea names are credited with it', () => {
  const row = ideasDerivedRow('delta');
  row.source.ideas_from[0].people = ['Ada Lovelace', 'Alan Turing'];
  row.source.ideas_from[0].licence_note = 'as the repository states it';
  const ideas = renderSections(catalogOf([row]))['provenance-ideas'];
  assert.ok(ideas.includes('[Example Research Skills](https://github.com/example-lab/example-research-skills) (Example Lab, with Ada Lovelace, Alan Turing)'), ideas);
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.match(md, /\[Example Research Skills\]\(https:\/\/github\.com\/example-lab\/example-research-skills\), a repository by Example Lab, with Ada Lovelace, Alan Turing \(CC-BY-SA-4\.0; as the repository states it\): the stage list/);
  noLeaks(ideas, 'README ideas');
  noLeaks(md, 'ideas with people');
});

test('PROVENANCE.md: a reference shows what it gave, its licence and note, and a component its note', () => {
  const row = thirdPartyBundleRow('gamma');
  row.components.two.note = 'its section headings follow bioSkills; no text is shared';
  row.components.two.references = [{ kind: 'software', name: 'ESM', url: 'https://github.com/facebookresearch/esm', credit: 'Meta FAIR', note: 'which esm package is meant is not pinned' }];
  row.source.references = [{ name: 'A Course', url: 'https://example.org/course', credit: 'A University', what: 'the method the skill teaches', licence: 'CC BY (version not stated)', licence_note: 'as the course states it', cite: 'A Course. A University.' }];
  const md = renderProvenanceMd(row, catalogOf([row]));
  assert.match(md, /- \[A Course\]\(https:\/\/example\.org\/course\), by A University \(CC BY \(version not stated\); as the course states it\): the method the skill teaches\. Cite: A Course\. A University\./);
  assert.match(md, /Status: active\. Note: its section headings follow bioSkills; no text is shared\./);
  assert.match(md, /References: \[ESM\]\(https:\/\/github\.com\/facebookresearch\/esm\), by Meta FAIR\. Note: which esm package is meant is not pinned\./);
  noLeaks(md, 'reference fields');
});

test('README: the ideas block says so when no row has anything to show', () => {
  assert.equal(renderSections(catalogOf([formatOneRow('lab-one', { origin: 'lab' })]))['provenance-ideas'], 'No item records ideas, references or earlier versions yet.');
});

// ---------------------------------------------------------------------------
// NOTICE

test('NOTICE: the header keeps the lab copyright line and adds the curator line', () => {
  const n = renderNotice(catalogOf([]));
  const lines = n.split('\n');
  assert.equal(lines[0], 'Biorouter Skills');
  assert.equal(lines[1], labCopyrightLine(2026));
  assert.equal(lines[2], CURATED_BY);
  noLeaks(n, 'NOTICE header');
});

test('NOTICE: each id once, distinct folders counted once, a holder-less source flagged', () => {
  const up = (p) => ({ repo: 'm-org/m-skills', path: p, commit: 'abc1234', licence: 'MIT', copyright: 'Copyright (c) 2026 M' });
  const items = [
    formatOneRow('one', { origin: 'adapted', upstreams: [up('a'), up('b'), up('c')] }),
    formatOneRow('two', { origin: 'adapted', upstreams: [up('d'), up('a')] }),
    formatOneRow('three', { origin: 'adapted', upstreams: [{ repo: 'n-org/plugins', path: 'plugins/x', commit: 'def5678', licence: 'Apache-2.0', copyright: null }], changes: 'folded' }),
  ];
  const n = renderNotice(catalogOf(items));
  assert.match(n, /\none, two include material from m-org\/m-skills \(4 folders across the items named here, commit abc1234\),\nCopyright \(c\) 2026 M, licensed under MIT\./);
  assert.match(n, /\nthree includes material from n-org\/plugins \(plugins\/x, commit def5678\), licensed under Apache-2\.0; its licence names no copyright holder\. Changes: folded/);
  noLeaks(n, 'NOTICE');
});

test('NOTICE: a format 2 row lists shipped sources with credit, and other credited work apart', () => {
  const row = adaptedRow('alpha', {
    source: {
      ...adaptedRow('alpha').source,
      upstreams: [
        upstream({ people: ['Ada Lovelace'] }),
        upstream({ repo: 'p-org/plugins', display: 'plugins', url: 'https://github.com/p-org/plugins', path: 'plugins/y', licence: 'Apache-2.0', copyright: null, copyright_note: 'the licence names no holder', credit: 'P Org', upstream_notice: true }),
        upstream({ kind: 'package', repo: 'r-org/runner', display: 'Runner', url: 'https://github.com/r-org/runner', path: null, commit: null, version: '1.2.3', use: ['launched'], copyright: null, credit: 'R Org', what: 'the runner, fetched at run time' }),
      ],
      data_and_services: [dataset()],
    },
  });
  const n = renderNotice(catalogOf([row, inHouseRow('epsilon')]));
  assert.match(n, /\nalpha includes material from example-org\/example-skills \(skills\/example, commit 0123456789abcdef0123456789abcdef01234567\),\nCopyright \(c\) 2026 Example Org, licensed under MIT\.\nCredited to Example Org, with Ada Lovelace\./);
  assert.match(n, /\nalpha includes material from p-org\/plugins \(plugins\/y, commit 0123456789abcdef0123456789abcdef01234567\), licensed under Apache-2\.0; its licence names no copyright holder\.\nCredited to P Org\.\nIts NOTICE file is reproduced in the notice file of each item named here\./);
  assert.match(n, /Other credited work\n===================\n\nalpha uses Runner \(r-org\/runner, version 1\.2\.3\) by R Org, licensed under MIT: the runner, fetched at run time \(launched, not redistributed\)\./);
  assert.match(n, /alpha, epsilon use Example KG 1\.0 \(https:\/\/doi\.org\/10\.0000\/example\), a dataset by A\. Author, B\. Author; terms: CC0-1\.0\. Cite: An example knowledge graph\. Example Journal 1, 1 \(2026\)\./);
  noLeaks(n, 'NOTICE format 2');
});

test('NOTICE: one block for a source several items record prints every credit, person and citation once', () => {
  const shared = { repo: 's-org/s-skills', display: 's-skills', url: 'https://github.com/s-org/s-skills', path: 'skills/one', copyright: 'Copyright (c) 2026 S Org', credit: 'S Org' };
  const rowOf = (id, extra) => adaptedRow(id, { source: { ...adaptedRow(id).source, upstreams: [upstream(), upstream({ ...shared, ...extra })] } });
  const items = [
    rowOf('alpha', { people: ['Ada Lovelace'], cite: 'S Org. S Skills.' }),
    rowOf('omega', { path: 'skills/two', people: ['Grace Hopper', 'Ada Lovelace'], cite: 'Hopper G. S Skills, part two.' }),
    rowOf('zeta', { path: 'skills/three', people: ['Alan Turing'] }),
  ];
  const block = renderNotice(catalogOf(items)).split('\n\n').find((b) => b.includes('s-org/s-skills')).trimEnd();
  assert.match(block, /^alpha, omega, zeta include material from s-org\/s-skills /);
  assert.match(block, /\nCredited to S Org, with Ada Lovelace, Grace Hopper, Alan Turing\.\nCite: S Org\. S Skills\.\nCite: Hopper G\. S Skills, part two\.$/);
  // A person the credit already names is not repeated after it.
  const guideline = adaptedRow('alpha', { source: { ...adaptedRow('alpha').source, upstreams: [upstream(), upstream({ ...shared, credit: 'von Elm E et al.', people: ['von Elm E', 'Altman DG', 'Elm'] })] } });
  const g = renderNotice(catalogOf([guideline])).split('\n\n').find((b) => b.includes('s-org/s-skills'));
  assert.match(g, /\nCredited to von Elm E et al\., with Altman DG\.\n?/);
  noLeaks(g, 'NOTICE shared source');
});

test("the repository's generated NOTICE names every person every shipped source of an active row credits", () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const notice = renderNotice(catalog, { baseline: readProvenanceBaseline(REPO_ROOT) });
  const blocks = notice.split('\n\n');
  let checked = 0;
  for (const row of catalog.items.filter((r) => r.status === 'active')) {
    for (const u of row.source?.upstreams ?? []) {
      if (!(u.use ?? []).some((x) => ['text', 'code', 'data', 'bundled', 'bundled-modified'].includes(x))) continue;
      // A repository is named by its owner/name; a guideline or a paper by its title.
      const ident = u.repo ?? (['guideline', 'paper'].includes(u.kind) ? u.display : u.url ?? u.display);
      const mine = blocks.filter((b) => b.includes(` material from ${ident}`) && new RegExp(`(^|, )${row.id}( |,)`).test(b.split('\n')[0]));
      assert.ok(mine.length, `${row.id}: no NOTICE block for ${ident}`);
      for (const who of [u.credit, ...(u.people ?? [])].filter(Boolean)) {
        assert.ok(mine.some((b) => b.includes(oneLine(who))), `${row.id}: ${ident} credits ${who}, which the NOTICE leaves out`);
        checked += 1;
      }
    }
  }
  assert.ok(checked > 300, `only ${checked} credits checked`);
});

test("NOTICE: the lab's own work is under the top line, a repository with no licence file gets no licence claim, and a holder-less source gets the fixed sentence", () => {
  const lab = (extra) => upstream({ repo: 'lab-org/lab-skills', display: 'lab-skills', url: 'https://github.com/lab-org/lab-skills', path: 'SKILL.md', copyright: null,
    copyright_note: "the Baranzini Lab's own work; the repository has no licence file at 0123456", credit: 'Baranzini Lab (Wanjun Gu, UCSF)', owner: 'lab', ...extra });
  const rowOf = (id, u) => adaptedRow(id, { source: { ...adaptedRow(id).source, upstreams: [upstream(), u] } });
  const none = renderNotice(catalogOf([rowOf('alpha', lab({ licence_file: false }))]));
  const block = none.split('\n\n').find((b) => b.includes('lab-org/lab-skills')).trimEnd();
  assert.match(block, /^alpha includes material from lab-org\/lab-skills \(SKILL\.md, commit [0-9a-f]+\), the Baranzini Lab's own work, under the copyright line at the top of this file; that repository has no licence file\.\nCredited to Baranzini Lab \(Wanjun Gu, UCSF\)\.$/);
  assert.ok(!block.includes('licensed under') && !block.includes('names no copyright holder') && !block.includes('0123456;'), block);
  const withFile = renderNotice(catalogOf([rowOf('alpha', lab({ licence: 'Apache-2.0' }))])).split('\n\n').find((b) => b.includes('lab-org/lab-skills'));
  assert.match(withFile, /, the Baranzini Lab's own work, under the copyright line at the top of this file, licensed under Apache-2\.0\.\n/);
  const holderless = renderNotice(catalogOf([rowOf('alpha', upstream({ repo: 'h-org/h', display: 'h', url: 'https://github.com/h-org/h', path: 'x', copyright: null, copyright_note: 'owner Q4: a decision note', credit: 'h-org' }))]));
  assert.match(holderless, /\nalpha includes material from h-org\/h \(x, commit [0-9a-f]+\), licensed under MIT; its licence names no copyright holder\.\nCredited to h-org\./);
  assert.ok(!holderless.includes('a decision note'));
  noLeaks(none, 'NOTICE lab source');
  // PROVENANCE.md's licence cell: the lab's holder, and no licence claim without a licence file.
  const md = renderProvenanceMd(rowOf('alpha', lab({ licence_file: false })), catalogOf([rowOf('alpha', lab({ licence_file: false }))]));
  const labRow = md.split('\n').find((l) => l.includes('lab-org/lab-skills') && l.startsWith('|'));
  assert.match(labRow, /\| no licence file in its repository; held by Baranzini Lab, University of California, San Francisco \|/);
  assert.ok(!/\| MIT/.test(labRow) && !labRow.includes('names no copyright holder'), labRow);
});

test('NOTICE: one source at one commit is one block whether or not an entry records a version, and a line\'s own full stop is not doubled', () => {
  const at = (id, extra) => adaptedRow(id, { source: { ...adaptedRow(id).source, upstreams: [upstream(extra)] } });
  const items = [at('alpha', { version: 'v2.72.0' }), at('omega', { path: 'skills/other', version: null })];
  const blocks = renderNotice(catalogOf(items)).split('\n\n').filter((b) => b.includes('example-org/example-skills'));
  assert.equal(blocks.length, 1, blocks.join('\n---\n'));
  assert.match(blocks[0], /^alpha, omega include material from example-org\/example-skills \(skills\/example, skills\/other, commit 0123456789abcdef0123456789abcdef01234567\),/);
  // A version still keys a source that has no commit.
  const pinned = (id, version) => adaptedRow(id, { source: { ...adaptedRow(id).source, upstreams: [upstream({ commit: null, version })] } });
  assert.equal(renderNotice(catalogOf([pinned('alpha', '1.0'), pinned('omega', '2.0')])).split('\n\n').filter((b) => b.includes('example-org/example-skills')).length, 2);
  const dotted = renderNotice(catalogOf([at('alpha', { copyright: 'Copyright (c) 2026: Tim Holy.' })]));
  assert.ok(dotted.includes('\nCopyright (c) 2026: Tim Holy. Licensed under MIT.\n'), dotted);
  assert.ok(!dotted.includes('Holy.,'));
});

test("NOTICE and PROVENANCE.md: a source's licence note follows its copyright line as a sentence of its own", () => {
  const bmj = upstream({ kind: 'guideline', repo: null, display: 'PRISMA 2020', url: 'https://doi.org/10.1136/bmj.n71', doi: '10.1136/bmj.n71', path: null, commit: null,
    version: 'PRISMA 2020', licence: 'CC-BY-4.0', licence_note: "the article's licence paragraph grants CC BY 4.0, commercial use included",
    copyright: '\u00a9 Author(s) (or their employer(s)) 2019. Re-use permitted under CC BY. No commercial re-use. See rights and permissions. Published by BMJ.',
    copyright_note: 'the statement as the publisher deposited it', credit: 'Page MJ et al.', people: ['Page MJ'], cite: 'Page MJ, et al. The PRISMA 2020 statement. BMJ 2021;372:n71.' });
  const row = adaptedRow('alpha', { source: { ...adaptedRow('alpha').source, upstreams: [upstream(), bmj] } });
  const block = renderNotice(catalogOf([row])).split('\n\n').find((b) => b.includes('PRISMA 2020'));
  assert.ok(block.includes('Published by BMJ. Licensed under CC-BY-4.0. The article\'s licence paragraph grants CC BY 4.0, commercial use included.\nCredited to Page MJ et al.'), block);
  // A source with no note prints no extra sentence, and the note keys its block.
  const plain = renderNotice(catalogOf([adaptedRow('alpha')])).split('\n\n').find((b) => b.includes('example-org/example-skills'));
  assert.ok(!plain.includes('grants'), plain);
  const twice = renderNotice(catalogOf([row, adaptedRow('omega', { source: { ...adaptedRow('omega').source, upstreams: [upstream(), { ...bmj, licence_note: undefined }] } })]));
  assert.equal(twice.split('\n\n').filter((b) => b.includes('PRISMA 2020')).length, 2, twice);
  const md = renderProvenanceMd(row, catalogOf([row]));
  const line = md.split('\n').find((l) => l.startsWith('|') && l.includes('PRISMA 2020'));
  assert.match(line, /\| CC-BY-4\.0 \(the article's licence paragraph grants CC BY 4\.0, commercial use included\); \u00a9 Author\(s\)/);
  noLeaks(block, 'NOTICE licence note');
});

test('NOTICE: the preamble names the items whose notice file waits for its next release', () => {
  const items = [adaptedRow('alpha'), adaptedRow('omega'), inHouseRow('epsilon')];
  const entry = (rule, subject) => ({ rule, subject, wp: 'PROV-S4', since: '2026-11-28', note: '' });
  const head = (baseline) => renderNotice(catalogOf(items), { baseline }).split('\n\nThis file is generated')[0];
  assert.ok(head(null).endsWith('upstream copyright line and licence text in its notice file.'));
  assert.match(head({ baseline_violations: [entry('PV7', 'notice-copyright:omega:example-org/example-skills')] }),
    /in its notice file\.\nThe notice file of omega gains the lines it still lacks at its next release\.$/);
  const notice = items[0].notice_file;
  const two = head({ baseline_violations: [entry('PV7', 'notice-apache:omega:x/y'), entry('PV13', `fixed-text:alpha:${notice}`), entry('PV9', 'folder:epsilon'), entry('PV13', 'fixed-text:epsilon:SKILL.md')] });
  assert.match(two, /\nThe notice files of alpha and omega gain the lines they still lack at their next\nrelease\.$/);
  for (const line of two.split('\n')) assert.ok(line.length <= 80, line);
});

test("the repository's generated NOTICE and every PROVENANCE.md carry no process wording", () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const baseline = readProvenanceBaseline(REPO_ROOT);
  const texts = [['NOTICE', renderNotice(catalog, { baseline })]];
  for (const row of catalog.items) if (row.source?.origin && catalog.format === 2) texts.push([`${row.id}/${PROVENANCE_FILE}`, renderProvenanceMd(row, catalog)]);
  assert.ok(texts.length > 100);
  for (const [label, text] of texts) {
    for (const phrase of ['owner Q', 'sign-off', 'before any generated file', 'Proposed by the migration']) assert.ok(!text.includes(phrase), `${label} prints "${phrase}"`);
    assert.deepEqual(processWordingProblems(text), [], `${label} prints process wording`);
  }
});

test("NOTICE: an Apache source's NOTICE is said to ship only with the items whose notice file carries it", () => {
  const apache = { repo: 'p-org/plugins', display: 'plugins', url: 'https://github.com/p-org/plugins', path: 'plugins/y', licence: 'Apache-2.0', copyright: 'Copyright 2026 P Org', credit: 'P Org', upstream_notice: true };
  const rowOf = (id) => adaptedRow(id, { source: { ...adaptedRow(id).source, upstreams: [upstream(apache)] } });
  const items = [rowOf('alpha'), rowOf('omega')];
  const deferral = (id) => ({ rule: 'PV7', subject: `notice-apache:${id}:p-org/plugins`, wp: 'PROV-S4', since: '2026-11-28', note: '' });
  const block = (baseline) => renderNotice(catalogOf(items), { baseline }).split('\n\n').find((b) => b.includes('p-org/plugins')).trimEnd();
  assert.match(block(null), /\nIts NOTICE file is reproduced in the notice file of each item named here\.$/);
  assert.match(block({ baseline_violations: [deferral('omega')] }), /\nIts NOTICE file is reproduced in the notice file of alpha\.\nIts NOTICE file ships in the notice file of omega from its next release\.$/);
  const both = block({ baseline_violations: [deferral('alpha'), deferral('omega')] });
  assert.match(both, /\nIts NOTICE file ships in the notice file of alpha, omega from their next release\.$/);
  assert.ok(!both.includes('is reproduced'));
  // Another rule's entry, or another source's, defers nothing.
  assert.match(block({ baseline_violations: [{ ...deferral('omega'), rule: 'PV9' }, { ...deferral('omega'), subject: 'notice-apache:omega:other/repo' }] }), /reproduced in the notice file of each item named here\.$/);
});

// ---------------------------------------------------------------------------
// Stubs

const MOVED_STUB_TODAY = '---\nname: beta\ndescription: "Moved: this skill is now part of Alpha (alpha). Use alpha instead."\nlicense: Apache-2.0\nuser-invocable: true\nmetadata:\n  version: "1.1.0"\n  status: "superseded_by:alpha"\n---\n\n# Beta has moved\n\nThis skill is now part of **Alpha** (`alpha`).\n\n- Use the `alpha` skill for this work. If it is installed, load it now and follow it.\n- If `alpha` is not installed, tell the person how to add it: in Biorouter, open Skills, choose Browse, search for "Alpha" (a search for "beta" finds it too), and add it.\n- If an older copy of `beta` is still installed next to `alpha`, `alpha` is the current version of its content and wins.\n- This copy is only a pointer and can be removed.\n';
const RETIRED_STUB_TODAY = '---\nname: gone\ndescription: "Retired: it was an empty template. Use Biorouter\'s built-in develop-biorouter-skill skill instead."\nlicense: Apache-2.0\nuser-invocable: true\nmetadata:\n  version: "1.1.0"\n  status: "retired"\n---\n\n# Gone is retired\n\nit was an empty template.\n\n- Use the built-in `develop-biorouter-skill` skill instead. Load it now and follow it.\n- If `develop-biorouter-skill` is missing, this copy of Biorouter is older than the skill; tell the person to update Biorouter.\n- Nothing is wrong.\n- This copy is only a notice and can be removed.\n';

test('stubs: the default output is byte for byte what it was, here and for every stub in the repository', () => {
  const cat = { items: [{ id: 'alpha', display_name: 'Alpha' }] };
  assert.equal(stubFiles({ id: 'beta', display_name: 'Beta', version: '1.1.0', status: 'superseded_by:alpha' }, cat)['SKILL.md'], MOVED_STUB_TODAY);
  assert.equal(stubFiles({ id: 'gone', display_name: 'Gone', version: '1.1.0', status: 'retired', retired: { reason: 'it was an empty template', use: 'builtin:develop-biorouter-skill', guidance: 'Nothing is wrong.' } }, cat, { provenance: false })['SKILL.md'], RETIRED_STUB_TODAY);
  const real = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'catalog.json'), 'utf8'));
  const stubs = real.items.filter((r) => r.status !== 'active');
  assert.ok(stubs.length > 0);
  for (const r of stubs) assert.equal(stubFiles(r, real)['SKILL.md'], fs.readFileSync(path.join(REPO_ROOT, r.path, 'SKILL.md'), 'utf8'), r.id);
});

test('stubs: with provenance, the front matter carries the credits and the body the credit lines before the last bullet', () => {
  const rows = validSkillRows();
  const row = rows.find((r) => r.id === 'beta');
  const cat = catalogOf(rows);
  const plain = stubFiles(row, cat)['SKILL.md'];
  const text = stubFiles(row, cat, { provenance: true })['SKILL.md'];
  const { frontmatter, body } = readSkillText(text);
  const want = frontmatterCredits(row);
  assert.equal(frontmatter.metadata.origin, want.origin);
  assert.equal(frontmatter.metadata.credit, want.credit);
  assert.equal(frontmatter.metadata.curated_by, CURATED_BY);
  assert.equal(frontmatter.metadata.version, '1.1.0');
  const bullets = body.split('\n').filter((l) => l.startsWith('- '));
  const [moved, curated] = stubCreditLines(row, rows);
  assert.deepEqual(bullets.slice(-3), [`- ${moved}`, `- ${curated}`, '- This copy is only a pointer and can be removed.']);
  // Everything else is the plain stub's text.
  const strip = (t) => t.split('\n').filter((l) => !/^  (origin|credit|curated_by): /.test(l) && l !== `- ${moved}` && l !== `- ${curated}`).join('\n');
  assert.equal(strip(text), plain);
  assert.equal(readSkillText(stubFiles({ ...row, status: 'retired', retired: { reason: 'gone' } }, cat, { provenance: true })['SKILL.md']).body.split('\n').filter((l) => l.startsWith('- ')).at(-1), '- This copy is only a notice and can be removed.');
});

test('stubs: the credit lines sit before the "This copy is only" bullet in every stub shape, found by its text', () => {
  const rows = validSkillRows();
  const cat = catalogOf(rows);
  const base = rows.find((r) => r.id === 'beta');
  const shapes = {
    merged: base,
    builtin: { ...base, status: 'superseded_by:builtin:develop-biorouter-skill', source: { ...base.source, content_moved_to: 'builtin:develop-biorouter-skill' } },
    'retired, with a replacement and guidance': { ...base, status: 'retired', retired: { reason: 'it was an empty template', use: 'alpha', guidance: 'Nothing is wrong.' } },
    'retired, alone': { ...base, status: 'retired', retired: { reason: 'it was an empty template' }, source: { ...base.source, content_moved_to: null } },
  };
  for (const [shape, row] of Object.entries(shapes)) {
    const body = readSkillText(stubFiles(row, cat, { provenance: true })['SKILL.md']).body.split('\n');
    const at = body.findIndex((l) => l.startsWith(STUB_LAST_BULLET));
    const [moved, curated] = stubCreditLines(row, rows);
    assert.deepEqual(body.slice(at - 2, at + 1).map((l) => l.slice(0, 40)), [`- ${moved}`, `- ${curated}`, body[at]].map((l) => l.slice(0, 40)), shape);
    assert.equal(body.filter((l) => l.startsWith(STUB_LAST_BULLET)).length, 1, shape);
  }
});

// ---------------------------------------------------------------------------
// setMetadata

const SKILL = [
  '---',
  'name: x',
  'description: "Says \\"hi\\"."',
  'license: Apache-2.0',
  'tool_type: python',
  'user-invocable: false',
  'metadata:',
  '  version: "1.1.0"',
  '  origin: "adapted"',
  '  upstream: "GPTomics/bioSkills@d91ed3d"',
  '  upstream_licence: "MIT"',
  '  upstream_author: "Someone (@someone)"',
  '  source:',
  '    model: google',
  '  upstream_version: "1.1"',
  '---',
  '',
  '# x',
  '',
  'metadata: this line is body text',
  '',
].join('\n');

test('setMetadata: replaces and appends keys under metadata, quoted, and leaves every other line alone', () => {
  const values = { origin: 'third-party', credit: 'From "bio" \\ Skills by GPTomics (MIT).', curated_by: CURATED_BY };
  const out = setMetadata(SKILL, values, { remove: ['upstream_licence', 'upstream_author', 'source'] });
  const fm = parseFrontmatter(splitFrontmatter(out).raw);
  assert.deepEqual(fm.metadata, { version: '1.1.0', origin: 'third-party', upstream: 'GPTomics/bioSkills@d91ed3d', upstream_version: '1.1', credit: values.credit, curated_by: CURATED_BY });
  assert.equal(fm.description, 'Says "hi".');
  assert.equal(fm['user-invocable'], 'false');
  assert.ok(out.includes('  credit: "From \\"bio\\" \\\\ Skills by GPTomics (MIT)."\n'));
  assert.ok(out.endsWith('---\n\n# x\n\nmetadata: this line is body text\n'), 'the body is untouched');
  const kept = SKILL.split('\n').filter((l) => !/^  (origin|upstream_licence|upstream_author|source):|^    model:/.test(l));
  assert.deepEqual(out.split('\n').filter((l) => !/^  (origin|credit|curated_by):/.test(l)), kept);
  assert.equal(setMetadata(out, values, { remove: ['upstream_licence', 'upstream_author', 'source'] }), out, 'idempotent');
});

test('setMetadata: creates metadata after license or user-invocable, keeps CRLF, and takes a predicate', () => {
  const bare = '---\nname: y\nlicense: MIT\nuser-invocable: true\nlong: >\n  folded\n---\nbody\n';
  const out = setMetadata(bare, { origin: 'in-house', credit: MADE_BY_LAB });
  assert.equal(out, `---\nname: y\nlicense: MIT\nuser-invocable: true\nmetadata:\n  origin: "in-house"\n  credit: "${MADE_BY_LAB}"\nlong: >\n  folded\n---\nbody\n`);
  const noInvocable = setMetadata('---\nname: z\nlicense: MIT\ndescription: d\n---\n', { origin: 'adapted' });
  assert.equal(noInvocable, '---\nname: z\nlicense: MIT\nmetadata:\n  origin: "adapted"\ndescription: d\n---\n');
  const crlf = SKILL.replace(/\n/g, '\r\n');
  const outCrlf = setMetadata(crlf, { credit: 'c' }, { remove: (key) => key === 'upstream_author' });
  assert.ok(!/[^\r]\n/.test(outCrlf), 'every line still ends in CRLF');
  assert.equal(readSkillText(outCrlf).frontmatter.metadata.credit, 'c');
  assert.equal(readSkillText(outCrlf).frontmatter.metadata.upstream_author, undefined);
  assert.throws(() => setMetadata('no front matter', { origin: 'x' }), /front matter/);
});

test('retiredMetadataKey: drops the old provenance keys, and upstream unless it names an upstream of the row', () => {
  const drop = retiredMetadataKey(thirdPartyBundleRow('gamma'));
  assert.equal(drop('upstream_licence', 'MIT'), true);
  assert.equal(drop('upstream_author', 'x'), true);
  assert.equal(drop('source', 'Biorouter original'), true);
  assert.equal(drop('upstream', 'example-org/bio-skills@d91ed3d'), false);
  assert.equal(drop('upstream', 'example-org/bio-skills/gamma/one@d91ed3d'), false);
  assert.equal(drop('upstream', 'Example-Org/Bio-Skills@d91ed3d'), false, 'compared case-blind');
  assert.equal(drop('upstream', 'GPTomics/bioSkills@d91ed3d'), true);
  assert.equal(drop('upstream', 'none (native rewrite, no upstream text copied)'), true);
  assert.equal(drop('version', '1.0.0'), false);
  assert.equal(drop('upstream_version', '1.1'), false);
});

// ---------------------------------------------------------------------------
// The scripts on a throwaway repository.

const SCRIPTS = path.join(REPO_ROOT, 'scripts');
const README_BLOCKS = ['counts', 'core', 'developer', 'biomedical', 'moved', 'provenance', 'provenance-ideas'];

function skillMd(name, extra = '') {
  return `---\nname: ${name}\ndescription: A skill named ${name}\nlicense: Apache-2.0 AND MIT\nuser-invocable: true\nmetadata:\n  version: "1.0.0"\n  upstream: "example-org/example-skills@0123456"\n  upstream_licence: "MIT"\n${extra}---\n\n# ${name}\n`;
}

function makeRepo(items, baselineViolations = []) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'provenance-render-'));
  const w = (rel, text) => {
    fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
    fs.writeFileSync(path.join(root, rel), text);
  };
  w('README.md', `# Fixture\n\n${README_BLOCKS.map((b) => `<!-- catalog:begin ${b} -->\n<!-- catalog:end ${b} -->`).join('\n\n')}\n`);
  w('catalog.json', `${JSON.stringify({ format: 1, done_work_packages: [], baseline_violations: [], items }, null, 2)}\n`);
  w('provenance-baseline.json', `${JSON.stringify({ format: 1, rows: [], done_work_packages: [], baseline_violations: baselineViolations }, null, 2)}\n`);
  for (const r of items) if (r.status === 'active' && r.kind === 'skill') w(`${r.path}/SKILL.md`, skillMd(r.id));
  for (const r of items) if (r.status === 'active' && r.kind === 'bundle') for (const [folder, c] of Object.entries(r.components)) if (c.status === 'active') w(`${r.path}/${folder}/SKILL.md`, skillMd(c.name));
  for (const r of items) if (r.status !== 'active') w(`${r.path}/SKILL.md`, 'placeholder\n');
  return { root, w, read: (rel) => fs.readFileSync(path.join(root, rel), 'utf8'), exists: (rel) => fs.existsSync(path.join(root, rel)) };
}

const node = (script, root, ...args) => spawnSync(process.execPath, [path.join(SCRIPTS, script), '--root', root, ...args], { encoding: 'utf8' });
const deferral = (id) => ({ rule: 'PV9', subject: `folder:${id}`, wp: 'PROV-S4', since: '2026-11-27', note: 'folder files at the next release' });

test('render-readme: writes PROVENANCE.md and the front matter credits for wanted rows only, and --check holds them', () => {
  const legacy = formatOneRow('legacy', { origin: 'lab' });
  const bundle = thirdPartyBundleRow('gamma');
  const items = [adaptedRow('alpha'), inHouseRow('epsilon'), legacy, bundle];
  const fx = makeRepo(items, [deferral('epsilon')]);
  const before = { epsilon: fx.read('epsilon/SKILL.md'), legacy: fx.read('legacy/SKILL.md') };
  const wrote = node('render-readme.mjs', fx.root);
  assert.equal(wrote.status, 0, wrote.stderr);
  const cat = JSON.parse(fx.read('catalog.json'));
  assert.equal(fx.read(`alpha/${PROVENANCE_FILE}`), renderProvenanceMd(cat.items[0], cat));
  assert.equal(fx.read(`bio-skills/gamma/${PROVENANCE_FILE}`), renderProvenanceMd(cat.items[3], cat));
  const alpha = readSkillText(fx.read('alpha/SKILL.md')).frontmatter.metadata;
  assert.deepEqual({ origin: alpha.origin, credit: alpha.credit, curated_by: alpha.curated_by }, frontmatterCredits(cat.items[0]));
  assert.equal(alpha.upstream, 'example-org/example-skills@0123456', 'an upstream that names the row stays');
  assert.equal(alpha.upstream_licence, undefined, 'the old licence key goes');
  const two = readSkillText(fx.read('bio-skills/gamma/two/SKILL.md')).frontmatter.metadata;
  assert.equal(two.origin, 'in-house');
  assert.equal(two.credit, MADE_BY_LAB);
  assert.equal(two.upstream, undefined, 'an upstream naming no source of the row goes');
  assert.ok(!fx.exists(`epsilon/${PROVENANCE_FILE}`), 'a deferred row gets no PROVENANCE.md');
  assert.equal(fx.read('epsilon/SKILL.md'), before.epsilon, 'nor its front matter');
  assert.ok(!fx.exists(`legacy/${PROVENANCE_FILE}`), 'a format 1 row gets none');
  assert.equal(fx.read('legacy/SKILL.md'), before.legacy);
  assert.ok(fx.read('NOTICE').includes(CURATED_BY));
  assert.ok(fx.read('README.md').includes('| `legacy` | Not yet classified | Lab-original |'));

  const ok = node('render-readme.mjs', fx.root, '--check');
  assert.equal(ok.status, 0, ok.stderr);
  assert.match(ok.stdout, /current/);

  fx.w(`epsilon/${PROVENANCE_FILE}`, 'anything at all\n');
  assert.equal(node('render-readme.mjs', fx.root, '--check').status, 0, 'a deferred row is skipped');

  const good = fx.read(`alpha/${PROVENANCE_FILE}`);
  fx.w(`alpha/${PROVENANCE_FILE}`, good.replace('Example Org', 'Someone Else'));
  const stale = node('render-readme.mjs', fx.root, '--check');
  assert.equal(stale.status, 1);
  assert.match(stale.stderr, /alpha\/PROVENANCE\.md/);
  fx.w(`alpha/${PROVENANCE_FILE}`, good);

  fs.rmSync(path.join(fx.root, 'bio-skills/gamma', PROVENANCE_FILE));
  assert.match(node('render-readme.mjs', fx.root, '--check').stderr, /bio-skills\/gamma\/PROVENANCE\.md/, 'a missing file is stale');
  assert.equal(node('render-readme.mjs', fx.root).status, 0);

  fx.w('alpha/SKILL.md', fx.read('alpha/SKILL.md').replace(/credit: ".*"/, 'credit: "Made by someone else."'));
  const fm = node('render-readme.mjs', fx.root, '--check');
  assert.equal(fm.status, 1);
  assert.match(fm.stderr, /alpha\/SKILL\.md/);
});

test('write-stubs: a wanted format 2 stub carries its credit lines, a deferred one does not', () => {
  const items = [adaptedRow('alpha'), stubRow('beta', 'alpha'), stubRow('zeta', 'alpha')];
  const fx = makeRepo(items, [deferral('zeta')]);
  const res = node('write-stubs.mjs', fx.root);
  assert.equal(res.status, 0, res.stderr);
  const cat = JSON.parse(fx.read('catalog.json'));
  assert.equal(fx.read('beta/SKILL.md'), stubFiles(cat.items[1], cat, { provenance: true })['SKILL.md']);
  assert.ok(fx.read('beta/SKILL.md').includes(CURATED_BY));
  assert.equal(fx.read('zeta/SKILL.md'), stubFiles(cat.items[2], cat)['SKILL.md']);
  assert.ok(!fx.read('zeta/SKILL.md').includes(CURATED_BY));
});

test('the real README and NOTICE carry no em dash and the curator line', () => {
  const readme = fs.readFileSync(path.join(REPO_ROOT, 'README.md'), 'utf8');
  const notice = fs.readFileSync(path.join(REPO_ROOT, 'NOTICE'), 'utf8');
  assert.ok(!readme.includes(EM_DASH) && !notice.includes(EM_DASH));
  assert.ok(readme.includes(CURATED_BY) && notice.includes(CURATED_BY));
  assert.ok(readme.includes('<!-- catalog:begin provenance -->') && readme.includes('<!-- catalog:begin provenance-ideas -->'));
  assert.ok(!readme.includes('<!-- catalog:begin sources -->'));
  assert.ok(!readme.includes('## Sources and attribution'));
});

