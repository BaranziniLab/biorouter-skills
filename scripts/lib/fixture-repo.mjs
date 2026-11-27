// Small throwaway repositories for the check's tests.
//
// makeFixture(): two single skills, one bundle, a format 1 catalog that passes,
// and the built-in names. Its provenance baseline lists the one failure every
// format 1 row has (PV1 format:<id>), so the fixture passes like the real
// repository does while its rows wait for format 2.
//
// makeFixture2(): a format 2 repository built from the records of
// fixture-provenance.mjs (in-house, ideas-derived, adapted, a third-party
// bundle with a component written for Biorouter and a merged file, and a
// merged stub), with every generated folder file written, so it passes with an
// empty provenance baseline.
//
// Each test copies one, changes one thing, and expects exactly the failure
// that change should cause.

import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  componentOfFile, folderProvenanceWanted, frontmatterCredits, labCopyrightLine, licenceTokens, noticeSources,
  shippedSources, sourceKey, upstreamNoticeMarker,
} from './catalog-rules.mjs';
import { validSkillRows } from './fixture-provenance.mjs';
import { PROVENANCE_BASELINE_FILE, PROVENANCE_BASELINE_SINCE } from './provenance-baseline.mjs';
import { PROVENANCE_FILE, renderProvenanceMd } from './provenance-md.mjs';
import { stubFiles } from './stub.mjs';

export const BUILTINS = {
  format: 1,
  skills: ['develop-biorouter-skill', 'office-word'],
  bundles: ['knowledge-bases'],
  extensions: ['developer', 'knowledge', 'Web & Documents'],
};

function skillMd(name, description, extra = '') {
  return `---\nname: ${name}\ndescription: ${description}\nlicense: Apache-2.0\nuser-invocable: true\n${extra}---\n\n# ${name}\n\nA body line unique to ${name}.\nAnother line about ${description.split(' ')[0]}.\n`;
}

export function row(id, over = {}) {
  return {
    id,
    display_name: id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    kind: 'skill',
    category: 'core',
    path: id,
    version: '1.0.0',
    status: 'active',
    aliases: [],
    job: `test.${id}`,
    summary: '',
    keywords: [],
    invocation: 'user',
    distinct_from: [],
    source: { origin: 'native', upstreams: [], maintained_here: false },
    licence: 'Apache-2.0',
    notice_file: null,
    release: { tag: `skill-${id}`, asset: `${id}.zip`, sha256: null },
    components: null,
    history: [{ version: '1.0.0', date: '2026-07-01' }],
    ...over,
  };
}

/** The `frozenRows` a fixture's runCheck takes: the count and SHA-256 of its sorted ids, as provenance-baseline.mjs freezes the real ones. */
export function frozenRowsFor(ids) {
  const sorted = [...ids].sort();
  return { count: sorted.length, sha256: crypto.createHash('sha256').update(sorted.join('\n')).digest('hex') };
}

/** A provenance baseline for the given ids and entries, shaped like provenance-baseline.json. */
export function provenanceBaseline(ids, entries = []) {
  return {
    format: 1,
    description: "The fixture's provenance baseline.",
    since: PROVENANCE_BASELINE_SINCE,
    rows: [...ids].sort(),
    done_work_packages: [],
    baseline_violations: entries,
  };
}

/** A provenance baseline entry, dated the day the rules landed. */
export function pvEntry(rule, subject, wp = 'PROV-S1', over = {}) {
  return { rule, subject, wp, since: PROVENANCE_BASELINE_SINCE, note: `${rule} ${subject}`, ...over };
}

function writer(root) {
  return (rel, text) => {
    fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
    fs.writeFileSync(path.join(root, rel), text);
  };
}

export function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'catalog-fixture-'));
  const w = writer(root);
  w('alpha/SKILL.md', skillMd('alpha', 'Plots volcanoes with matplotlib for omics tables'));
  w('beta/SKILL.md', skillMd('beta', 'Drafts grant aims and milestones for funders'));
  w('bio-skills/gamma/README.md', '# gamma\n');
  w('bio-skills/gamma/one/SKILL.md', skillMd('gamma-one', 'Calls ChIP binding sites'));
  w('bio-skills/gamma/two/SKILL.md', skillMd('gamma-two', 'Annotates genes near regions'));
  const catalog = {
    format: 1,
    done_work_packages: [],
    baseline_violations: [],
    items: [
      row('alpha'),
      row('beta'),
      row('gamma', {
        kind: 'bundle',
        category: 'biomedical',
        path: 'bio-skills/gamma',
        invocation: 'bundle',
        components: {
          one: { name: 'gamma-one', status: 'active', job: 'test.gamma.one', upstream_path: null },
          two: { name: 'gamma-two', status: 'active', job: 'test.gamma.two', upstream_path: null },
        },
      }),
    ],
  };
  const ids = catalog.items.map((r) => r.id);
  const provenance = provenanceBaseline(ids, [...ids].sort().map((id) => pvEntry('PV1', `format:${id}`, 'PROV-S1', { note: `${id} records its provenance in format 1` })));
  w(PROVENANCE_BASELINE_FILE, `${JSON.stringify(provenance, null, 2)}\n`);
  return { root, catalog, write: w, provenance: clone(provenance), frozenRows: frozenRowsFor(ids) };
}

// ---------------------------------------------------------------------------
// makeFixture2: a format 2 repository.

/** The MIT licence text (the permission notice and the warranty disclaimer). */
export const MIT_LICENCE_TEXT = `Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
`;

/** A stand-in for the Apache-2.0 text: a test fixture only, carrying the two phrases PV7 looks for. */
export const APACHE_LICENCE_STAND_IN = `Apache License
Version 2.0, January 2004

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

(A real notice file carries the full text here.)

END OF TERMS AND CONDITIONS
`;

const LICENCE_TEXTS = { 'MIT': MIT_LICENCE_TEXT, 'Apache-2.0': APACHE_LICENCE_STAND_IN };

// Card descriptions that share no words, so the duplicate screens stay quiet.
const DESCRIPTIONS = {
  alpha: 'Plots volcanoes with matplotlib for omics tables',
  delta: 'Drafts grant aims and milestones for funders',
  epsilon: 'Queries a pharmacology graph of compounds and pathways',
  'gamma/one': 'Calls ChIP binding peaks from aligned reads',
  'gamma/two': 'Annotates loci near genomic intervals',
};

const yamlString = (value) => `"${String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;

/**
 * A SKILL.md with the generated metadata keys. Written here, not through
 * frontmatter.mjs's setMetadata, so the fixture does not depend on the
 * generators it helps to test.
 */
export function skillMd2(name, description, licence, metadata) {
  const lines = ['---', `name: ${name}`, `description: ${yamlString(description)}`, `license: ${licence}`, 'user-invocable: true', 'metadata:'];
  for (const [k, v] of Object.entries(metadata)) if (v != null) lines.push(`  ${k}: ${yamlString(v)}`);
  const word = description.split(' ')[0].toLowerCase();
  lines.push('---', '', `# ${name}`, '', `A body line unique to ${name}.`, `Another line about how it ${word} things.`, '');
  return lines.join('\n');
}

/** The front matter values one SKILL.md of a row carries: its version and, when the row's folder files are due, the credits. */
export function fixtureMetadata(row, rel, wanted) {
  const meta = { version: row.version };
  if (wanted) Object.assign(meta, frontmatterCredits(row, rel));
  return meta;
}

/** A notice file for a row: Biorouter's part, each source's copyright line and NOTICE, and each licence text once. */
export function fixtureNoticeText(row, catalogFormat = 1) {
  const sources = noticeSources(row, catalogFormat);
  for (const u of shippedSources(row, catalogFormat)) if (u?.upstream_notice === true && !sources.includes(u)) sources.push(u);
  const lines = [
    `${row.display_name}: licences of the material it includes`,
    '',
    `Biorouter's own part is licensed under the Apache License 2.0, ${labCopyrightLine(2026)}.`,
    '',
  ];
  for (const u of sources) {
    lines.push(`Source: ${sourceKey(u)} (${u.path ?? 'the whole repository'}, ${u.commit ? `commit ${u.commit}` : `version ${u.version}`}), licensed under ${u.licence}.`);
    if (u.copyright) lines.push(u.copyright);
    if (u.upstream_notice === true) lines.push('', upstreamNoticeMarker(u.repo ?? sourceKey(u)), '', 'Example NOTICE text, as the source publishes it.');
    lines.push('');
  }
  const licences = [...new Set(sources.flatMap((u) => licenceTokens(u.licence)))];
  for (const id of licences) if (LICENCE_TEXTS[id]) lines.push(`${id}`, '', LICENCE_TEXTS[id]);
  return `${lines.join('\n').trimEnd()}\n`;
}

/**
 * Rewrites every folder of `catalog` from its rows: SKILL.md files (with the
 * credits when the row's folder files are due under `baseline`), PROVENANCE.md,
 * the notice file, the files listed under written_for_biorouter, and stubs.
 */
export function writeFixture2Folders(root, catalog, baseline = null) {
  const w = writer(root);
  const catalogFormat = catalog.format ?? 1;
  for (const r of catalog.items) {
    const abs = path.join(root, r.path);
    fs.rmSync(abs, { recursive: true, force: true });
    const wanted = folderProvenanceWanted(r, { catalogFormat, baseline });
    if (r.status !== 'active') {
      for (const [name, text] of Object.entries(stubFiles(r, catalog, { provenance: wanted }))) w(`${r.path}/${name}`, text);
      continue;
    }
    if (r.kind === 'skill') {
      w(`${r.path}/SKILL.md`, skillMd2(r.id, DESCRIPTIONS[r.id] ?? `Handles the ${r.id} task`, r.licence, fixtureMetadata(r, 'SKILL.md', wanted)));
    } else {
      for (const [folder, comp] of Object.entries(r.components ?? {})) {
        if (comp.status !== 'active') continue;
        const rel = `${folder}/SKILL.md`;
        if (componentOfFile(r, rel) !== folder) throw new Error(`fixture: ${rel} is not a component file of ${r.id}`);
        w(`${r.path}/${rel}`, skillMd2(comp.name, DESCRIPTIONS[`${r.id}/${folder}`] ?? `Handles the ${comp.name} task`, comp.licence ?? r.licence, fixtureMetadata(r, rel, wanted)));
        for (const file of comp.written_for_biorouter ?? []) w(`${r.path}/${folder}/${file.path}`, `# ${file.what}\n\nWritten for Biorouter.\n`);
      }
    }
    if (r.notice_file) w(`${r.path}/${r.notice_file}`, fixtureNoticeText(r, catalogFormat));
    if (wanted) w(`${r.path}/${PROVENANCE_FILE}`, renderProvenanceMd(r, catalog));
  }
}

export function makeFixture2() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'catalog-fixture2-'));
  const items = validSkillRows();
  // The merged stub beta redirects to alpha, which takes its id as an alias (D4).
  items.find((r) => r.id === 'alpha').aliases = ['beta'];
  const catalog = { format: 1, done_work_packages: [], baseline_violations: [], items };
  const ids = items.map((r) => r.id);
  const provenance = provenanceBaseline(ids);
  writeFixture2Folders(root, catalog, provenance);
  const w = writer(root);
  w(PROVENANCE_BASELINE_FILE, `${JSON.stringify(provenance, null, 2)}\n`);
  return {
    root,
    catalog,
    write: w,
    provenance: clone(provenance),
    frozenRows: frozenRowsFor(ids),
    /** Rewrites every folder from the (changed) catalog, the given baseline deciding which rows' folder files are due. */
    regenerate: (cat = catalog, baseline = provenance) => writeFixture2Folders(root, cat, baseline),
    read: (rel) => fs.readFileSync(path.join(root, rel), 'utf8'),
    remove: (rel) => fs.rmSync(path.join(root, rel), { recursive: true, force: true }),
  };
}

export const clone = (x) => JSON.parse(JSON.stringify(x));
