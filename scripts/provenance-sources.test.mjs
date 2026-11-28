// Tests for source shapes the format 2 record takes: publications as
// upstreams (a reporting guideline or a paper, pinned by its citation), a
// source reached through another one (`via` as a list), an extension that
// forwards calls to a program its publisher hosts (`use: hosted`, the
// "Bridges to" line), and a source's preferred citation (`cite`). Each rule has a mutant that changes one field of a valid record
// and expects exactly the failure that causes.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CREDIT_LINE_MAX,
  ORIGINS,
  ORIGIN_SENTENCES,
  PUBLICATION_KINDS,
  UPSTREAM_KINDS,
  USES,
  componentCreditLine,
  creditLine,
  frontmatterCredits,
  originSentence,
  ruleProvenance,
  sourceKey,
  sourceUrl,
  stubCreditLines,
  viaOf,
} from './lib/catalog-rules.mjs';
import { adaptedRow, ideasDerivedRow, inHouseRow, thirdPartyBundleRow, thirdPartyExtensionRow, upstream } from './lib/fixture-provenance.mjs';
import { renderProvenanceMd } from './lib/provenance-md.mjs';
import { stubFiles } from './lib/stub.mjs';
import { releaseNotes } from './release.mjs';
import { renderNotice, renderSections } from './render-readme.mjs';

const subjects = (res) => res.failures.map((f) => `${f.rule}:${f.subject}`).sort();
const messages = (res) => res.failures.map((f) => f.message).join('\n');
const catalogOf = (items) => ({ format: 1, items });
const EM_DASH = String.fromCharCode(0x2014);

function noLeaks(text, label) {
  assert.doesNotMatch(text, /\bnull\b|\bundefined\b|\[object Object\]/, `${label} prints a missing value`);
  assert.ok(!text.includes(EM_DASH), `${label} uses an em dash`);
}

const STROBE_URL = 'https://doi.org/10.1371/journal.pmed.0040296';
const STROBE_CITE = 'von Elm E, Altman DG, Egger M, Pocock SJ, Gotzsche PC, Vandenbroucke JP. The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement. PLoS Med 2007;4(10):e296. doi:10.1371/journal.pmed.0040296';
const PAPER_DOI = '10.1038/s41597-023-01960-3';

/** A reporting guideline whose item text the skill reproduces (CC BY 4.0). */
function guideline(over = {}) {
  return upstream({
    kind: 'guideline',
    repo: null,
    display: 'STROBE 2007',
    url: STROBE_URL,
    path: null,
    commit: null,
    version: 'STROBE 2007',
    licence: 'CC-BY-4.0',
    copyright: null,
    copyright_note: 'the checklist file names no copyright line for the statement',
    credit: 'von Elm E et al.',
    people: ['von Elm E', 'Altman DG', 'Egger M'],
    use: ['text'],
    what: "the guideline's item text, reproduced in checklists/STROBE.md",
    files: ['checklists/STROBE.md'],
    taken: '2026-11-22',
    cite: STROBE_CITE,
    ...over,
  });
}

/** A paper cited as the source of a method's text, known by its DOI alone. */
function paper(over = {}) {
  return upstream({
    kind: 'paper',
    repo: null,
    display: 'PrimeKG paper',
    url: null,
    doi: PAPER_DOI,
    path: null,
    commit: null,
    version: null,
    licence: 'CC-BY-4.0',
    copyright: 'Copyright (c) 2023 The Authors',
    credit: 'Payal Chandak et al.',
    people: ['Payal Chandak', 'Kexin Huang', 'Marinka Zitnik'],
    use: ['text'],
    what: 'the description of the graph schema, quoted in references/schema.md',
    files: ['references/schema.md'],
    cite: 'Chandak P, Huang K, Zitnik M. Building a knowledge graph to enable precision medicine. Scientific Data 10, 67 (2023).',
    ...over,
  });
}

/** An adapted skill that copies an MIT repository and reproduces a guideline and a paper. */
function publicationRow(over = {}) {
  const row = adaptedRow('alpha', { licence: 'Apache-2.0 AND MIT AND CC-BY-4.0' });
  row.source.upstreams = [upstream(), guideline(), paper()];
  return Object.assign(row, over);
}

const run = (rows, catalog = 'skills') => ruleProvenance(rows, { catalogFormat: 1, catalog });

function mutantOf(make, change, catalog) {
  const row = make();
  change(row.source.upstreams, row);
  return run([row], catalog);
}

// ---------------------------------------------------------------------------
// Publications: a guideline or a paper.

test('the upstream kinds include guideline and paper, the two publication kinds', () => {
  assert.ok(UPSTREAM_KINDS.includes('guideline'));
  assert.ok(UPSTREAM_KINDS.includes('paper'));
  assert.deepEqual([...PUBLICATION_KINDS].sort(), ['guideline', 'paper']);
});

test('PV6: a guideline and a paper are pinned by their citation, not a commit, and pass', () => {
  const res = run([publicationRow()]);
  assert.deepEqual(res.failures, []);
  // The guideline's licence names no holder: listed for review, as for any source.
  assert.equal(res.warnings.length, 1);
  assert.match(res.warnings[0], /names no copyright holder/);
});

test('PV6: a publication needs a citation', () => {
  const res = mutantOf(publicationRow, (ups) => delete ups[1].cite);
  assert.deepEqual(subjects(res), [`PV6:source:alpha:${STROBE_URL}`]);
  assert.match(messages(res), /a guideline needs its citation in cite/);
  const paperRes = mutantOf(publicationRow, (ups) => (ups[2].cite = ' '));
  assert.deepEqual(subjects(paperRes), [`PV6:source:alpha:${PAPER_DOI}`]);
  assert.match(messages(paperRes), /a paper needs its citation in cite/);
});

test('PV6: a publication needs a DOI or a URL', () => {
  const res = mutantOf(publicationRow, (ups) => {
    ups[2].doi = null;
    ups[2].url = null;
  });
  assert.deepEqual(subjects(res), ['PV6:source:alpha:PrimeKG paper']);
  assert.match(messages(res), /no DOI or url/);
  assert.doesNotMatch(messages(res), /no repo or url/);
});

test('PV6: a publication needs a licence and a credit', () => {
  const noLicence = mutantOf(publicationRow, (ups, row) => {
    delete ups[1].licence;
    row.licence = 'Apache-2.0 AND MIT AND CC-BY-4.0';
  });
  assert.deepEqual(subjects(noLicence), [`PV6:source:alpha:${STROBE_URL}`]);
  assert.match(messages(noLicence), /no licence/);
  const noCredit = mutantOf(publicationRow, (ups) => delete ups[1].credit);
  assert.deepEqual(subjects(noCredit), [`PV6:source:alpha:${STROBE_URL}`]);
  assert.match(messages(noCredit), /no credit/);
});

test('PV6: only a publication is exempt from the pin; the same entry as a repository needs a commit or a version', () => {
  const asPublication = mutantOf(publicationRow, (ups) => (ups[1].version = null));
  assert.deepEqual(subjects(asPublication), []);
  const asRepository = mutantOf(publicationRow, (ups) => {
    ups[1].version = null;
    ups[1].kind = 'repository';
  });
  assert.deepEqual(subjects(asRepository), [`PV6:source:alpha:${STROBE_URL}`]);
  assert.match(messages(asRepository), /needs a commit or a version/);
  // A publication's text still ships under an allowed licence.
  const nc = mutantOf(publicationRow, (ups, row) => {
    ups[1].licence = 'CC-BY-NC-4.0';
    row.licence = 'Apache-2.0 AND MIT AND CC-BY-4.0 AND CC-BY-NC-4.0';
  });
  assert.match(messages(nc), /licence CC-BY-NC-4\.0 may not be copied or bundled/);
});

test('PV6: a doi is a bare DOI, and a cite is text', () => {
  const doi = mutantOf(publicationRow, (ups) => (ups[2].doi = `https://doi.org/${PAPER_DOI}`));
  assert.deepEqual(subjects(doi), [`PV6:source:alpha:https://doi.org/${PAPER_DOI}`]);
  assert.match(messages(doi), /is not a DOI/);
  const emptyCite = mutantOf(publicationRow, (ups) => (ups[0].cite = ''));
  assert.deepEqual(subjects(emptyCite), ['PV6:source:alpha:example-org/example-skills']);
  assert.match(messages(emptyCite), /cite must be the citation as text/);
  const objectCite = mutantOf(publicationRow, (ups) => (ups[0].cite = { title: 'x' }));
  assert.deepEqual(subjects(objectCite), ['PV6:source:alpha:example-org/example-skills']);
  // A repository may carry its preferred citation, and a null one is no citation.
  assert.deepEqual(subjects(mutantOf(publicationRow, (ups) => (ups[0].cite = 'Example Org. Example Skills. doi:10.5281/zenodo.1'))), []);
  assert.deepEqual(subjects(mutantOf(publicationRow, (ups) => (ups[0].cite = null))), []);
});

test('sourceKey and sourceUrl know a publication by its DOI when it has no URL', () => {
  assert.equal(sourceKey(paper()), PAPER_DOI);
  assert.equal(sourceUrl(paper()), `https://doi.org/${PAPER_DOI}`);
  assert.equal(sourceUrl(guideline()), STROBE_URL);
  assert.equal(sourceUrl(upstream({ url: null })), null);
});

test('creditLine counts each publication as a source of its own', () => {
  assert.equal(creditLine(publicationRow()), 'Adapted from example-skills by Example Org (MIT) and 2 more.');
  const only = adaptedRow('alpha', { licence: 'Apache-2.0 AND CC-BY-4.0' });
  only.source.upstreams = [guideline()];
  assert.equal(creditLine(only), 'Adapted from STROBE 2007 by von Elm E et al. (CC-BY-4.0).');
  assert.deepEqual(subjects(run([only])), []);
});

// ---------------------------------------------------------------------------
// via: a source reached through another one.

const OCU = 'iFurySt/open-computer-use';

/** Open Computer Use's shape: one vendored program and two sources of its own, reached through it. */
function viaRow(over = {}) {
  const ext = (o) => upstream({ kind: 'package', path: null, use: ['bundled-modified'], files: [], ...o });
  return thirdPartyExtensionRow('opencomputeruseagent', {
    licence: 'Apache-2.0 AND MIT',
    source: {
      ...thirdPartyExtensionRow().source,
      origin: 'adapted',
      upstreams: [
        ext({ repo: OCU, display: 'Open Computer Use', url: `https://github.com/${OCU}`, version: '1.1.5', credit: 'Leo', copyright: 'Copyright (c) 2026 Leo', what: 'pristine source vendored with 14 local patches', via: ['trycua/cua', 'asmvik/yabai'] }),
        ext({ repo: 'trycua/cua', display: 'Cua Driver', url: 'https://github.com/trycua/cua', credit: 'Cua AI, Inc.', copyright: 'Copyright (c) 2025 Cua AI, Inc.', people: ['Francesco Bonacci'], what: 'code inside Open Computer Use (the SkyLight event bridge)' }),
        ext({ repo: 'asmvik/yabai', display: 'yabai', url: 'https://github.com/asmvik/yabai', credit: 'Asmund Vikane', copyright: 'Copyright (c) 2019 Asmund Vikane', what: 'code inside Open Computer Use (focus-without-raise records)' }),
      ],
      changes: 'Open Computer Use vendored and changed by 14 local patches; the extension around it is the lab\'s.',
    },
    ...over,
  });
}

const runExt = (rows) => run(rows, 'extensions');

test('viaOf reads a single repository or a list', () => {
  assert.deepEqual(viaOf(upstream()), []);
  assert.deepEqual(viaOf(upstream({ via: 'a/b' })), ['a/b']);
  assert.deepEqual(viaOf(upstream({ via: ['a/b', 'c/d'] })), ['a/b', 'c/d']);
});

test('PV6: a via list passes when each entry names another upstream with its own licence and credit', () => {
  assert.deepEqual(runExt([viaRow()]).failures, []);
  // One repository named as a string still works.
  const single = viaRow();
  single.source.upstreams[0].via = 'trycua/cua';
  assert.deepEqual(runExt([single]).failures, []);
});

test('PV6: a via entry that names no other upstream fails', () => {
  const res = mutantOf(viaRow, (ups) => (ups[0].via = ['trycua/cua', 'koekeishiya/yabai']), 'extensions');
  assert.deepEqual(subjects(res), [`PV6:source:opencomputeruseagent:${OCU}`]);
  assert.match(messages(res), /via "koekeishiya\/yabai" names no other upstream of the row/);
});

test('PV6: a via entry must carry its own licence and credit', () => {
  const noCredit = mutantOf(viaRow, (ups) => delete ups[2].credit, 'extensions');
  assert.deepEqual(subjects(noCredit), ['PV6:source:opencomputeruseagent:asmvik/yabai', `PV6:source:opencomputeruseagent:${OCU}`]);
  assert.match(messages(noCredit), /via "asmvik\/yabai" names a source with no credit of its own/);
  const noLicence = mutantOf(viaRow, (ups) => (ups[1].licence = ''), 'extensions');
  assert.deepEqual(subjects(noLicence), [`PV6:source:opencomputeruseagent:${OCU}`, 'PV6:source:opencomputeruseagent:trycua/cua']);
  assert.match(messages(noLicence), /via "trycua\/cua" names a source with no licence of its own/);
});

test('PV6: a via list is not empty, holds repository names, and never names its own repository', () => {
  const empty = mutantOf(viaRow, (ups) => (ups[0].via = []), 'extensions');
  assert.deepEqual(subjects(empty), [`PV6:source:opencomputeruseagent:${OCU}`]);
  assert.match(messages(empty), /via is an empty list/);
  const notText = mutantOf(viaRow, (ups) => (ups[0].via = ['trycua/cua', 7]), 'extensions');
  assert.deepEqual(subjects(notText), [`PV6:source:opencomputeruseagent:${OCU}`]);
  assert.match(messages(notText), /via must name repositories/);
  const self = mutantOf(viaRow, (ups) => {
    ups[0].via = [OCU];
    ups.push(upstream({ kind: 'package', repo: OCU, display: 'Open Computer Use', url: `https://github.com/${OCU}`, path: 'patches', version: '1.1.5', credit: 'Leo', copyright: 'Copyright (c) 2026 Leo', use: ['bundled-modified'], files: [], what: 'the patch set' }));
  }, 'extensions');
  assert.deepEqual(subjects(self), [`PV6:source:opencomputeruseagent:${OCU}`]);
  assert.match(messages(self), /names its own repository/);
});

test("PROVENANCE.md: a via entry's row says which source it was reached through", () => {
  const row = viaRow();
  const md = renderProvenanceMd(row, catalogOf([row]));
  const line = (name) => md.split('\n').find((l) => l.startsWith(`| [${name}]`));
  assert.ok(line('Open Computer Use').endsWith('|  |'), 'the program itself was reached directly');
  assert.ok(line('Cua Driver').endsWith(`| \`${OCU}\` |`), line('Cua Driver'));
  assert.ok(line('yabai').endsWith(`| \`${OCU}\` |`), line('yabai'));
  assert.ok(!md.includes('trycua/cua,asmvik/yabai'), 'a list is never joined into one name');
  noLeaks(md, 'via');
});

// ---------------------------------------------------------------------------
// hosted: an extension that forwards calls to a program its publisher runs.

/** IDCAgent's shape: the tool definitions copied, every call forwarded to the hosted server. */
function bridgeRow(over = {}) {
  return thirdPartyExtensionRow('idcagent', {
    licence: 'Apache-2.0',
    source: {
      ...thirdPartyExtensionRow().source,
      upstreams: [upstream({
        kind: 'repository', repo: 'ImagingDataCommons/IDC-REST-MCP', display: 'the NCI IDC MCP server', url: 'https://github.com/ImagingDataCommons/IDC-REST-MCP',
        path: null, commit: 'd2452ce36c15b226455e9e96658eaa03fc0cc36f', version: '3.0.0b7', licence: 'Apache-2.0', copyright: 'Copyright 2026, Imaging Data Commons',
        credit: 'Imaging Data Commons', people: ['Andrey Fedorov', 'Steve Pieper'], use: ['text', 'hosted'], files: ['src/idcagent/tools_snapshot.json'],
        what: 'the tool definitions the hosted server publishes, copied into tools_snapshot.json; every call is forwarded to that server',
      })],
      changes: 'Packaging only: the lab wrote the extension that forwards calls to the hosted server.',
    },
    ...over,
  });
}

test('hosted is a use: a program its publisher runs, which the extension forwards calls to', () => {
  assert.ok(USES.includes('hosted'));
  assert.deepEqual(runExt([bridgeRow()]).failures, []);
});

test('creditLine: an extension that forwards to a hosted program "Bridges to" it', () => {
  const row = bridgeRow();
  assert.equal(creditLine(row, { catalog: 'extensions' }), 'Bridges to the NCI IDC MCP server by Imaging Data Commons; extension by the Baranzini Lab.');
  assert.equal(originSentence(row, { catalog: 'extensions' }), ORIGIN_SENTENCES['third-party-bridge']);
  assert.notEqual(ORIGIN_SENTENCES['third-party-bridge'], ORIGIN_SENTENCES['third-party-extension']);
  const two = bridgeRow();
  two.source.upstreams.push(upstream({ kind: 'repository', repo: 'o/helper', display: 'helper', path: null, use: ['text'] }));
  assert.equal(creditLine(two, { catalog: 'extensions' }), 'Bridges to the NCI IDC MCP server by Imaging Data Commons and 1 more; extension by the Baranzini Lab.');
  assert.ok(creditLine(two, { catalog: 'extensions' }).length <= CREDIT_LINE_MAX);
});

test('creditLine: a program the extension runs leads over a hosted one, and a hosted one over copied text', () => {
  const runs = bridgeRow();
  runs.source.upstreams.push(upstream({ kind: 'package', repo: 'o/local-mcp', display: 'Local MCP', path: null, commit: null, version: '1.0.0', use: ['launched'], files: [], credit: 'Ada Example' }));
  assert.equal(creditLine(runs, { catalog: 'extensions' }), 'Runs Local MCP 1.0.0 by Ada Example (MIT) and 1 more; extension by the Baranzini Lab.');
  assert.equal(originSentence(runs, { catalog: 'extensions' }), ORIGIN_SENTENCES['third-party-extension']);
  // A program the extension launches itself, which its publisher also hosts, is run, not bridged.
  const both = bridgeRow();
  both.source.upstreams[0].use = ['launched', 'hosted'];
  assert.equal(creditLine(both, { catalog: 'extensions' }), 'Runs the NCI IDC MCP server 3.0.0b7 by Imaging Data Commons (Apache-2.0); extension by the Baranzini Lab.');
  assert.equal(originSentence(both, { catalog: 'extensions' }), ORIGIN_SENTENCES['third-party-extension']);
  const text = bridgeRow();
  text.source.upstreams.unshift(upstream({ kind: 'repository', repo: 'o/notes', display: 'notes', path: null, use: ['text'] }));
  assert.match(creditLine(text, { catalog: 'extensions' }), /^Bridges to the NCI IDC MCP server by Imaging Data Commons and 1 more;/);
  // A skill never bridges: the line is the skill's own.
  const skill = adaptedRow('alpha');
  skill.source.upstreams[0].use = ['text', 'hosted'];
  assert.equal(creditLine(skill), 'Adapted from example-skills by Example Org (MIT).');
});

test('PV5: a third-party extension made only of a hosted program passes, and one made of a dependency does not', () => {
  const hosted = bridgeRow();
  Object.assign(hosted.source.upstreams[0], { use: ['hosted'], commit: null, version: null, files: [] });
  assert.deepEqual(subjects(runExt([hosted])), [], 'a hosted program is not shipped, so it owes no pin');
  assert.match(renderSections(catalogOf([hosted])).provenance, /by Imaging Data Commons \(Apache-2\.0\), run on its publisher's servers/);
  assert.match(renderNotice(catalogOf([hosted])), /\(hosted, not redistributed\)/);
  const dep = bridgeRow();
  Object.assign(dep.source.upstreams[0], { use: ['dependency'], commit: null, version: null, files: [] });
  assert.deepEqual(subjects(runExt([dep])), ['PV5:third-party:idcagent']);
});

// ---------------------------------------------------------------------------
// hosted is an extension's use: a skill row never reads "Bridges to".
//
// A skill forwards calls to nothing, so the "Bridges to" line and the bridge
// sentence belong to extensions alone. The render guard keys on the row
// itself (a skill or bundle row never bridges, whatever catalog a caller
// names), and PV6 refuses `use: hosted` on a skill or bundle row in every
// status, because a skill names a hosted service under data_and_services.

const BRIDGE_LINE = /Bridges to/;
const BRIDGE_SENTENCE = ORIGIN_SENTENCES['third-party-bridge'];
const SKILL_STATUSES = ['active', 'superseded_by:delta', 'retired'];
const HOSTED_REPO = 'example-org/hosted-api';

/** Every use value alone, and every other one together with hosted. */
const USE_SETS = [...USES.map((x) => [x]), ...USES.filter((x) => x !== 'hosted').map((x) => [x, 'hosted'])];

/** A program its publisher runs, as an upstream of the row; `use` decides how. */
function hostedSource(use = ['hosted'], over = {}) {
  return upstream({
    kind: 'program', repo: HOSTED_REPO, display: 'the Example hosted API', url: `https://github.com/${HOSTED_REPO}`,
    path: null, commit: null, version: null, use, files: [], credit: 'Example Hosting',
    what: 'the API a model would call', ...over,
  });
}

const SKILL_BUILDERS = {
  'in-house': () => inHouseRow('alpha'),
  'ideas-derived': () => ideasDerivedRow('alpha'),
  'adapted': () => adaptedRow('alpha'),
  'third-party': () => {
    const row = adaptedRow('alpha');
    Object.assign(row.source, { origin: 'third-party', changes: 'packaging only: front matter names and versions' });
    return row;
  },
};

/** A skill row (kind skill) or a bundle row of one origin. */
function skillRowOf(origin, kind) {
  const row = SKILL_BUILDERS[origin]();
  if (kind === 'skill') return row;
  const bundle = thirdPartyBundleRow('gamma');
  bundle.source = { ...bundle.source, origin, ideas_from: row.source.ideas_from, changes: bundle.source.changes };
  return bundle;
}

/** The row in `status`, with what a merged or retired row records. */
function withStatus(row, status) {
  row.status = status;
  if (status === 'active') return row;
  row.source.content_moved_to = status.startsWith('superseded_by:') ? status.slice('superseded_by:'.length) : null;
  if (status === 'retired') row.retired = { reason: 'Its tool closed its service' };
  return row;
}

/** Every skill and bundle row, of every origin and status, whose upstreams carry every use, hosted leading or not. */
function* skillRowsOfEveryUse() {
  for (const origin of ORIGINS) {
    for (const kind of ['skill', 'bundle']) {
      for (const status of SKILL_STATUSES) {
        for (const use of USE_SETS) {
          for (const shape of ['alone', 'after a hosted lead']) {
            const row = withStatus(skillRowOf(origin, kind), status);
            row.source.upstreams = shape === 'alone' ? [hostedSource(use)] : [hostedSource(['hosted']), upstream({ use })];
            yield { label: `${origin} ${kind}, ${status}, use ${use.join('+')}, ${shape}`, row };
          }
        }
      }
    }
  }
}

/** Every text Biorouter generates for one row: its lines, sentences, front matter, stub, record, README, NOTICE and release notes. */
function generatedTexts(row) {
  const catalog = catalogOf([row]);
  const folders = Object.keys(row.components ?? {});
  const out = [];
  for (const opts of [{}, { catalog: 'skills' }, { catalog: 'extensions' }]) {
    const as = opts.catalog ?? 'its own catalog';
    out.push([`creditLine as ${as}`, creditLine(row, opts)]);
    out.push([`originSentence as ${as}`, originSentence(row, opts)]);
    for (const folder of folders) out.push([`componentCreditLine ${folder} as ${as}`, componentCreditLine(row, folder, opts)]);
  }
  for (const rel of ['SKILL.md', ...folders.map((f) => `${f}/SKILL.md`)]) out.push([`front matter of ${rel}`, frontmatterCredits(row, rel).credit]);
  out.push(['stub credit lines', stubCreditLines(row, [row]).join('\n')]);
  if (row.status !== 'active') out.push(['stub SKILL.md', stubFiles(row, catalog, { provenance: true })['SKILL.md']]);
  out.push(['PROVENANCE.md', renderProvenanceMd(row, catalog)]);
  out.push(['README sections', Object.values(renderSections(catalog)).join('\n')]);
  out.push(['NOTICE', renderNotice(catalog)]);
  out.push(['release notes', releaseNotes(row, { catalogFormat: 2, today: '2026-11-27' })]);
  return out;
}

test('a skill or bundle row, in any status and with any use, never reads "Bridges to" anywhere it is shown', () => {
  let rows = 0;
  for (const { label, row } of skillRowsOfEveryUse()) {
    rows++;
    for (const [where, text] of generatedTexts(row)) {
      assert.doesNotMatch(text, BRIDGE_LINE, `${label}: ${where}`);
      assert.ok(!text.includes(BRIDGE_SENTENCE), `${label}: ${where} opens with the bridge sentence`);
    }
  }
  // 4 origins, 2 kinds, 3 statuses, 17 use sets, 2 shapes: the loop really ran over them all.
  assert.equal(rows, ORIGINS.length * 2 * SKILL_STATUSES.length * USE_SETS.length * 2);
});

test('a third-party skill whose lead source is hosted reads as a skill, even when a caller names the extension catalog', () => {
  const row = skillRowOf('third-party', 'skill');
  row.source.upstreams = [hostedSource(['hosted'])];
  const skillLine = 'From the Example hosted API by Example Hosting (MIT), packaged for Biorouter by the Baranzini Lab.';
  assert.equal(creditLine(row), skillLine);
  assert.equal(creditLine(row, { catalog: 'skills' }), skillLine);
  assert.doesNotMatch(creditLine(row, { catalog: 'extensions' }), BRIDGE_LINE);
  assert.notEqual(originSentence(row, { catalog: 'extensions' }), BRIDGE_SENTENCE);
  // Bridging needs an extension row read as an extension: the same source on one does bridge.
  const ext = bridgeRow();
  ext.source.upstreams = [hostedSource(['hosted'])];
  assert.equal(creditLine(ext), 'Bridges to the Example hosted API by Example Hosting; extension by the Baranzini Lab.');
  assert.equal(originSentence(ext), BRIDGE_SENTENCE);
  assert.doesNotMatch(creditLine(ext, { catalog: 'skills' }), BRIDGE_LINE, 'an extension row read for the skill catalog is not bridged either');
});

/** Valid rows of every skill shape that can be valid as built: each origin as a skill, and the adapted and third-party bundles. */
function validSkillShapes() {
  const shapes = ORIGINS.map((origin) => [`${origin} skill`, () => skillRowOf(origin, 'skill')]);
  for (const origin of ['adapted', 'third-party']) shapes.push([`${origin} bundle`, () => skillRowOf(origin, 'bundle')]);
  return shapes;
}

const HOSTED_REFUSAL = /use "hosted" is for an extension that forwards calls to a program its publisher runs; a skill forwards nothing, so name the service under data_and_services/;

test('PV6: a skill or bundle row may not name a hosted source, in any status', () => {
  for (const [shape, make] of validSkillShapes()) {
    for (const status of SKILL_STATUSES) {
      const label = `${shape}, ${status}`;
      const valid = withStatus(make(), status);
      assert.deepEqual(subjects(run([valid])), [], `${label}: valid before a hosted source is added`);
      const hosted = withStatus(make(), status);
      hosted.source.upstreams.push(hostedSource(['hosted']));
      const res = run([hosted]);
      assert.deepEqual(subjects(res), [`PV6:source:${hosted.id}:${HOSTED_REPO}`], label);
      assert.match(messages(res), HOSTED_REFUSAL, label);
      // Read for the extension catalog, a skill row is refused all the same.
      assert.deepEqual(subjects(run([hosted], 'extensions')), [`PV6:source:${hosted.id}:${HOSTED_REPO}`], `${label}, read as an extension`);
    }
  }
});

test('PV6: hosted beside any other use on a skill source is refused, and the same source without it is not', () => {
  for (const use of USES.filter((x) => x !== 'hosted')) {
    const without = adaptedRow('alpha');
    without.source.upstreams[0].use = [use, 'text'];
    assert.doesNotMatch(messages(run([without])), HOSTED_REFUSAL, use);
    const withHosted = adaptedRow('alpha');
    withHosted.source.upstreams[0].use = [use, 'text', 'hosted'];
    const res = run([withHosted]);
    assert.ok(subjects(res).includes('PV6:source:alpha:example-org/example-skills'), use);
    assert.match(messages(res), HOSTED_REFUSAL, use);
  }
});

test('PV6: an extension row may name a hosted source; read as a skill it may not', () => {
  const ext = thirdPartyExtensionRow();
  ext.source.upstreams.push(hostedSource(['hosted']));
  assert.deepEqual(subjects(runExt([ext])), []);
  assert.deepEqual(subjects(run([ext], 'skills')), [`PV6:source:exampleagent:${HOSTED_REPO}`]);
  assert.deepEqual(runExt([bridgeRow()]).failures, []);
});

// ---------------------------------------------------------------------------
// cite: a source's preferred citation.

test("PROVENANCE.md lists each source's preferred citation once, escaped", () => {
  const row = publicationRow();
  row.source.upstreams[0].cite = 'Example Org. Example Skills <v2>. doi:10.5281/zenodo.1';
  row.source.upstreams.push(upstream({ path: 'skills/other', cite: 'Example Org. Example Skills <v2>. doi:10.5281/zenodo.1' }));
  const md = renderProvenanceMd(row, catalogOf([row]));
  const at = md.indexOf('How each source asks to be cited:');
  assert.ok(at > md.indexOf('| Source |') && at < md.indexOf('Changes for Biorouter'), 'the citations follow the sources table');
  const block = md.slice(at, md.indexOf('Changes for Biorouter'));
  assert.equal(block.match(/^- /gm).length, 3, 'one line per source and citation');
  assert.ok(block.includes('- [example-skills](https://github.com/example-org/example-skills): Example Org. Example Skills \\<v2\\>. doi:10.5281/zenodo.1'));
  assert.ok(block.includes(`- [STROBE 2007](${STROBE_URL}): von Elm E, Altman DG`));
  assert.ok(block.includes(`- [PrimeKG paper](https://doi.org/${PAPER_DOI}): Chandak P, Huang K, Zitnik M. Building a knowledge graph`));
  noLeaks(md, 'citations');
});

test('PROVENANCE.md: no citation block when no source gives one', () => {
  const row = adaptedRow('alpha');
  assert.ok(!renderProvenanceMd(row, catalogOf([row])).includes('asks to be cited'));
});

test('PROVENANCE.md: a publication links its DOI and is pinned by its version or DOI', () => {
  const row = publicationRow();
  const md = renderProvenanceMd(row, catalogOf([row]));
  const line = (name) => md.split('\n').find((l) => l.startsWith(`| [${name}]`));
  // With no copyright line, the cell gives the record's own reason, never a claim the record does not make.
  assert.match(line('STROBE 2007'), /^\| \[STROBE 2007\]\(https:\/\/doi\.org\/10\.1371\/journal\.pmed\.0040296\) \| version STROBE 2007, taken 2026-11-22 \| CC-BY-4\.0; no copyright line: the checklist file names no copyright line for the statement \|/);
  assert.ok(!line('STROBE 2007').includes('its licence names no copyright holder'));
  const bare = publicationRow();
  bare.source.upstreams.find((u) => u.display === 'STROBE 2007').copyright_note = null;
  const bareLine = renderProvenanceMd(bare, catalogOf([bare])).split('\n').find((l) => l.startsWith('| [STROBE 2007]'));
  assert.match(bareLine, /\| CC-BY-4\.0; the publication names no copyright holder \|/);
  const held = publicationRow();
  Object.assign(held.source.upstreams.find((u) => u.display === 'STROBE 2007'), { copyright: '© 2007 von Elm et al.', copyright_note: 'as deposited in PubMed Central' });
  const heldLine = renderProvenanceMd(held, catalogOf([held])).split('\n').find((l) => l.startsWith('| [STROBE 2007]'));
  assert.match(heldLine, /\| CC-BY-4\.0; © 2007 von Elm et al\. \(as deposited in PubMed Central\) \|/);
  assert.match(line('PrimeKG paper'), new RegExp(`^\\| \\[PrimeKG paper\\]\\(https://doi\\.org/${PAPER_DOI.replace(/\./g, '\\.')}\\) \\| DOI \`${PAPER_DOI.replace(/\./g, '\\.')}\``));
});

test('NOTICE gives the citation of each source it names, and README links a DOI', () => {
  const row = publicationRow();
  row.source.upstreams[0].cite = 'Example Org. Example Skills. doi:10.5281/zenodo.1';
  row.source.upstreams.push(upstream({ repo: 'o/dep', display: 'dep', path: null, use: ['dependency'], files: [], cite: 'Dep Authors. Dep. doi:10.5281/zenodo.2' }));
  const notice = renderNotice(catalogOf([row]));
  assert.ok(notice.includes('Credited to Example Org.\nCite: Example Org. Example Skills. doi:10.5281/zenodo.1'));
  // A publication is named by its title and its DOI or URL, and with no copyright line it claims no holder for its licence.
  assert.ok(notice.includes(`alpha includes material from STROBE 2007 (${STROBE_URL}), licensed under CC-BY-4.0; the publication names no copyright holder.`));
  assert.ok(notice.includes(`Cite: ${STROBE_CITE}`));
  assert.ok(notice.includes(`alpha includes material from PrimeKG paper (DOI ${PAPER_DOI})`), 'a DOI-only source is named with its DOI');
  // Its own copyright statement is kept verbatim, and a statement's full stop is not doubled.
  const held = publicationRow();
  Object.assign(held.source.upstreams.find((u) => u.display === 'STROBE 2007'), { copyright: '© 2007 von Elm et al.', doi: '10.1371/journal.pmed.0040296' });
  assert.ok(renderNotice(catalogOf([held])).includes('alpha includes material from STROBE 2007 (DOI 10.1371/journal.pmed.0040296),\n© 2007 von Elm et al. Licensed under CC-BY-4.0.\n'));
  assert.match(notice, /alpha uses dep \(o\/dep\) by Example Org, licensed under MIT: [^\n]+\(dependency, not redistributed\)\. Cite: Dep Authors\. Dep\. doi:10\.5281\/zenodo\.2/);
  const readme = renderSections(catalogOf([row])).provenance;
  assert.ok(readme.includes(`[PrimeKG paper](https://doi.org/${PAPER_DOI}) by Payal Chandak et al. (CC-BY-4.0)`));
  noLeaks(notice, 'NOTICE');
});
