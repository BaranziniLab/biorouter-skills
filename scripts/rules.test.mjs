// Mutant tests for the duplicate and gap rules: each case breaks one rule and
// expects that rule, and only that rule, to fail.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  applyBaseline, foldPlural, jaccard, normalizeName, ruleD1, ruleD2, ruleD3, ruleD4, ruleD5, ruleD6, ruleG1,
  methodSkillWarnings, tokenSet,
} from './lib/catalog-rules.mjs';

const item = (id, over = {}) => ({
  ref: `skill:${id}`, catalog: 'skills', kind: 'skill', id, display_name: id, status: 'active',
  aliases: [], job: `test.${id}`, distinct_from: [], text: [id], ...over,
});
const ext = (id, over = {}) => item(id, { ref: `extension:${id}`, catalog: 'extensions', kind: 'extension', ...over });
const subjects = (fs) => fs.map((f) => `${f.rule}:${f.subject}`).sort();

test('normalizeName folds case and punctuation and drops a trailing agent', () => {
  assert.equal(normalizeName('Literature Agent'), 'literature');
  assert.equal(normalizeName('UCSFHPCAgent'), 'ucsfhpc');
  assert.equal(normalizeName('ucsf-hpc'), 'ucsfhpc');
  assert.equal(normalizeName('agent'), 'agent');
});

test('the tokenizer drops short words, stopwords and generic words, and folds plurals', () => {
  assert.deepEqual([...tokenSet(['The skill plots volcano plots for genes'], ['skill'])].sort(), ['gene', 'plot', 'volcano']);
  assert.equal(foldPlural('studies'), 'study');
  assert.equal(foldPlural('analysis'), 'analysis');
  assert.equal(jaccard(new Set(['a', 'b']), new Set(['b', 'c'])), 1 / 3);
});

test('D1 passes distinct jobs and fails a shared job', () => {
  assert.deepEqual(ruleD1([item('a'), item('b')]), []);
  assert.deepEqual(subjects(ruleD1([item('a', { job: 'x.y' }), item('b', { job: 'x.y' })])), ['D1:job:x.y']);
});

test('D1 ignores inactive items', () => {
  assert.deepEqual(ruleD1([item('a', { job: 'x.y' }), item('b', { job: 'x.y', status: 'superseded_by:a' })]), []);
});

test('D1 fails a built-in job and a malformed key', () => {
  assert.deepEqual(subjects(ruleD1([item('a', { job: 'skill.authoring' })], { builtinJobs: [{ job: 'skill.authoring', owner: 'b' }] })), ['D1:builtin:skill.authoring']);
  assert.deepEqual(subjects(ruleD1([item('a', { job: 'Nodot' })])), ['D1:job-format:skill:a']);
});

test('D1 counts components and bundled adapter skills, which must end in .tool-usage', () => {
  const comp = item('b/c', { ref: 'component:b/c', kind: 'component', job: 'x.y' });
  assert.deepEqual(subjects(ruleD1([item('a', { job: 'x.y' }), comp])), ['D1:job:x.y']);
  const bundled = item('lit-skill', { ref: 'bundled:lit/lit-skill', catalog: 'extensions', kind: 'bundled-skill', job: 'literature.api' });
  assert.deepEqual(subjects(ruleD1([bundled])), ['D1:tool-usage:bundled:lit/lit-skill']);
});

test('a bundled skill names an active method skill, or warns when it names none', () => {
  const b = (m) => item('s', { ref: 'bundled:e/s', catalog: 'extensions', kind: 'bundled-skill', job: 'e.tool-usage', method_skill: m });
  assert.equal(methodSkillWarnings([b(null)]).warnings.length, 1);
  assert.deepEqual(subjects(methodSkillWarnings([b('missing')]).failures), ['D1:method-skill:bundled:e/s']);
  assert.deepEqual(methodSkillWarnings([b('a'), item('a')]).failures, []);
});

test('D2 fails a repeated name across ids, display names and aliases', () => {
  assert.deepEqual(subjects(ruleD2([item('a-b'), item('c', { display_name: 'A B' })])), ['D2:name:ab']);
  assert.deepEqual(subjects(ruleD2([item('a'), item('c', { aliases: ['a'] })])), ['D2:name:a']);
});

test('D2 fails a BAAM item that takes a built-in name', () => {
  assert.deepEqual(subjects(ruleD2([item('office-word')], { skills: ['office-word'] })), ['D2:name:officeword']);
  assert.deepEqual(subjects(ruleD2([ext('knowledgeagent', { display_name: 'KnowledgeAgent' })], { extensions: ['knowledge'] })), ['D2:name:knowledge']);
});

test('D2 allows the alias of a superseded id on the item that replaced it', () => {
  assert.deepEqual(ruleD2([item('old', { status: 'superseded_by:new' }), item('new', { aliases: ['old'] })]), []);
  // ... but not on an unrelated item
  assert.deepEqual(subjects(ruleD2([item('old', { status: 'superseded_by:new' }), item('new'), item('other', { aliases: ['old'] })])), ['D2:name:old']);
});

test('D2 keeps a retired id reserved, but lets it equal the built-in it was retired for', () => {
  assert.deepEqual(ruleD2([item('office-word', { status: 'retired' })], { skills: ['office-word'] }), []);
  assert.deepEqual(subjects(ruleD2([item('x', { status: 'retired' }), item('y', { display_name: 'X' })])), ['D2:name:x']);
});

test('D2 lets an extension share a name with its own bundled skill', () => {
  const e = ext('zoteroagent', { display_name: 'ZoteroAgent' });
  const b = item('zotero', { ref: 'bundled:zoteroagent/zotero', catalog: 'extensions', kind: 'bundled-skill', parent: 'extension:zoteroagent' });
  assert.deepEqual(ruleD2([e, b]), []);
});

test('D2 lets a skill and an extension share a normalized name only with a written boundary', () => {
  const s = item('chem');
  const e = ext('chemagent', { display_name: 'ChemAgent' });
  assert.deepEqual(subjects(ruleD2([s, e])), ['D2:name:chem']);
  assert.deepEqual(ruleD2([s, { ...e, distinct_from: [{ id: 'chem', boundary: 'methods vs tools' }] }]), []);
  assert.deepEqual(subjects(ruleD2([s, { ...e, distinct_from: [{ id: 'chem', boundary: ' ' }] }])), ['D2:name:chem']);
});

test('D3 flags look-alikes of one catalog and accepts a written boundary', () => {
  const a = item('a', { text: ['volcano plot omics table matplotlib'] });
  const b = item('b', { text: ['volcano plot omics table seaborn'] });
  assert.deepEqual(subjects(ruleD3([a, b], { threshold: 0.4 })), ['D3:pair:a|b']);
  assert.deepEqual(ruleD3([a, { ...b, distinct_from: [{ id: 'a', boundary: 'seaborn vs matplotlib' }] }], { threshold: 0.4 }), []);
  assert.deepEqual(ruleD3([a, { ...b, catalog: 'extensions' }], { threshold: 0.4 }), [], 'different catalogs are never compared');
  assert.deepEqual(ruleD3([a, { ...b, status: 'retired' }], { threshold: 0.4 }), [], 'inactive items are not screened');
});

test('D4 passes a complete redirect', () => {
  assert.deepEqual(ruleD4([item('old', { status: 'superseded_by:new' }), item('new', { aliases: ['old'] })]), []);
});

test('D4 fails a missing target, an inactive target, a missing alias and a bad status', () => {
  assert.deepEqual(subjects(ruleD4([item('old', { status: 'superseded_by:gone' })])), ['D4:target:skill:old']);
  assert.deepEqual(subjects(ruleD4([item('old', { status: 'superseded_by:mid' }), item('mid', { status: 'superseded_by:new', aliases: ['old'] }), item('new', { aliases: ['mid'] })])), ['D4:chain:skill:old']);
  assert.deepEqual(subjects(ruleD4([item('old', { status: 'superseded_by:new' }), item('new')])), ['D4:alias:skill:old']);
  assert.deepEqual(subjects(ruleD4([item('old', { status: 'moved' })])), ['D4:status:skill:old']);
});

test('D4 requires a built-in target to be a name Biorouter ships', () => {
  assert.deepEqual(ruleD4([item('old', { status: 'superseded_by:builtin:develop-biorouter-skill' })], { skills: ['develop-biorouter-skill'] }), []);
  assert.deepEqual(subjects(ruleD4([item('old', { status: 'superseded_by:builtin:nope' })], { skills: ['develop-biorouter-skill'] })), ['D4:target:skill:old']);
});

test('D4 checks a removed component points at an active component or skill', () => {
  const c = (id, status) => item(id, { ref: `component:${id}`, kind: 'component', status });
  assert.deepEqual(ruleD4([c('b/x', 'superseded_by:b/y'), c('b/y', 'active')]), []);
  assert.deepEqual(subjects(ruleD4([c('b/x', 'superseded_by:b/z')])), ['D4:target:component:b/x']);
});

test('D5 fails a component name that repeats another component or a single skill', () => {
  const c = (id, name) => item(id, { ref: `component:${id}`, kind: 'component', name });
  assert.deepEqual(ruleD5([c('b/x', 'b-x'), c('d/x', 'd-x')], { screen: false }), []);
  assert.deepEqual(subjects(ruleD5([c('b/x', 'shared'), c('d/x', 'shared')], { screen: false })), ['D5:name:shared']);
  assert.deepEqual(subjects(ruleD5([item('shared'), c('d/x', 'shared')], { screen: false })), ['D5:name:shared']);
});

test('D5 screens component look-alikes with the component threshold', () => {
  const c = (id, text, over = {}) => item(id, { ref: `component:${id}`, kind: 'component', name: id.replace('/', '-'), text: [text], ...over });
  const a = c('b/x', 'peak calling chip reads macs');
  const b = c('d/y', 'peak calling chip reads homer');
  assert.deepEqual(subjects(ruleD5([a, b], { threshold: 0.4 })), ['D5:pair:b/x|d/y']);
  assert.deepEqual(ruleD5([a, { ...b, distinct_from: [{ id: 'b/x', boundary: 'homer vs macs' }] }], { threshold: 0.4 }), []);
});

test('D6 fails a skill whose lines mostly appear in five or more others', () => {
  const shared = ['Use when planning.', 'Check the inputs.', 'Report the results.'];
  const bodies = Array.from({ length: 7 }, (_, i) => ({ ref: `skill:s${i}`, id: `s${i}`, body: `# Title ${i}\n${shared.join('\n')}\nUnique line ${i}.` }));
  const rich = { ref: 'skill:rich', id: 'rich', body: `${shared[0]}\nOne.\nTwo.\nThree.\nFour.` };
  const fails = ruleD6([...bodies, rich]);
  assert.equal(fails.length, 7);
  assert.ok(!fails.some((f) => f.subject === 'shell:rich'));
  assert.deepEqual(ruleD6(bodies.slice(0, 5)), [], 'with only four others a shared line does not count');
});

test('G1 passes an active owner, warns on a planned gap, fails an unplanned gap', () => {
  const required = [
    { job: 'figures.r-style', owner: 'ggplot', planned: null },
    { job: 'r.live-session', owner: 'gptr', planned: 'this round, WP-14' },
  ];
  const g = ruleG1([item('ggplot', { job: 'figures.r-style' })], required);
  assert.deepEqual(g.failures, []);
  assert.equal(g.warnings.length, 1);
  assert.deepEqual(subjects(ruleG1([], [{ job: 'x.y', owner: null, planned: null }]).failures), ['G1:gap:x.y']);
});

test('G1 fails when an item other than the named owner claims a required job', () => {
  const g = ruleG1([item('other', { job: 'figures.r-style' })], [{ job: 'figures.r-style', owner: 'ggplot', planned: 'WP-17' }]);
  assert.deepEqual(subjects(g.failures), ['G1:owner:figures.r-style']);
});

test('G1 accepts a component or a bundled skill as the owner', () => {
  const comp = item('database-access/ontology', { ref: 'component:database-access/ontology', kind: 'component', job: 'terminology.ontology-mapping' });
  assert.deepEqual(ruleG1([comp], [{ job: 'terminology.ontology-mapping', owner: 'database-access/ontology' }]).failures, []);
});

test('baseline entries accept a known failure, refuse a done work package and report stale entries', () => {
  const f = [{ rule: 'D6', subject: 'shell:a', message: 'm', refs: [] }];
  assert.equal(applyBaseline(f, [{ rule: 'D6', subject: 'shell:a', wp: 'WP-16a' }]).errors.length, 0);
  assert.equal(applyBaseline(f, []).errors.length, 1);
  assert.match(applyBaseline(f, [{ rule: 'D6', subject: 'shell:a', wp: 'WP-16a' }], ['WP-16a']).errors[0].message, /marked done/);
  const stale = applyBaseline([], [{ rule: 'D6', subject: 'shell:a', wp: 'WP-16a' }]);
  assert.match(stale.errors[0].message, /no longer fails/);
});
