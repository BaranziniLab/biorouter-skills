// The D3 calibration (plan 1.4): run against the baseline catalogs, the screen
// must flag at least five of the seven known look-alike pairs, and every known
// pair it misses must share a job in the baseline assignment, so D1 catches it.
// The fixture freezes the baseline text, so later content changes cannot move
// this result.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { DEFAULT_SIMILARITY_THRESHOLD, lookalikeScores, ruleD1 } from './lib/catalog-rules.mjs';

const fixture = JSON.parse(fs.readFileSync(new URL('./fixtures/baseline/items.json', import.meta.url), 'utf8'));
const KNOWN = [
  ['structuredpapersearchagent', 'literatureagent'],
  ['singlecellomicsagent', 'cellxgenecensusagent'],
  ['ncbiagent', 'unifiedpublicdatabaselookupagent'],
  ['citation-temporal-integrity', 'claim-evidence-integrity'],
  ['open-science-review', 'replication-package-audit'],
  ['taste-skill', 'frontend-design'],
  ['financial-accounting-econometrics', 'econometrics-toolkit'],
];

test('the baseline fixture is the whole BAAM catalog before the refresh', () => {
  const by = (c) => fixture.items.filter((i) => i.catalog === c && i.status === 'active').length;
  assert.equal(by('skills'), 129);
  assert.equal(by('extensions'), 38);
});

test('D3 flags at least five of the seven known pairs, and D1 catches the rest', () => {
  const scores = lookalikeScores(fixture.items);
  const score = (a, b) => scores.find((p) => (p.a.id === a && p.b.id === b) || (p.a.id === b && p.b.id === a))?.score ?? 0;
  const flagged = KNOWN.filter(([a, b]) => score(a, b) >= DEFAULT_SIMILARITY_THRESHOLD);
  assert.ok(flagged.length >= 5, `flagged ${flagged.length} of 7: ${KNOWN.map(([a, b]) => `${a}/${b} ${score(a, b).toFixed(3)}`).join(', ')}`);
  const d1 = ruleD1(fixture.items);
  for (const [a, b] of KNOWN.filter((p) => !flagged.includes(p))) {
    const caught = d1.some((f) => f.refs.some((r) => r.endsWith(`:${a}`)) && f.refs.some((r) => r.endsWith(`:${b}`)));
    assert.ok(caught, `${a}/${b} is neither flagged by D3 nor caught by D1`);
  }
});

test('the threshold sits between the fifth and the sixth known pair', () => {
  const scores = lookalikeScores(fixture.items);
  const known = KNOWN.map(([a, b]) => scores.find((p) => (p.a.id === a && p.b.id === b) || (p.a.id === b && p.b.id === a))?.score ?? 0).sort((x, y) => y - x);
  assert.ok(DEFAULT_SIMILARITY_THRESHOLD <= known[4], 'the fifth known pair must stay flagged');
  assert.ok(DEFAULT_SIMILARITY_THRESHOLD > known[5], 'a lower threshold buys nothing: the sixth known pair is far below');
});
