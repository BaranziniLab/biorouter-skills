// Mutant tests for the folder checks in check-catalog.mjs, on a throwaway repository.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { runCheck } from './check-catalog.mjs';
import { BUILTINS, clone, makeFixture, row } from './lib/fixture-repo.mjs';
import { stubFiles } from './lib/stub.mjs';

const rules = (res) => res.errors.map((e) => `${e.rule}:${e.subject}`).sort();

function run(mutate = () => {}) {
  const fx = makeFixture();
  const catalog = clone(fx.catalog);
  mutate({ ...fx, catalog });
  return runCheck({ root: fx.root, catalog, builtins: BUILTINS });
}

test('the fixture passes', () => {
  assert.deepEqual(rules(run()), []);
});

test('a folder without a row fails, and so does a row without a folder', () => {
  assert.deepEqual(rules(run(({ write }) => write('delta/SKILL.md', '---\nname: delta\n---\n'))), ['folder:unlisted:delta']);
  assert.deepEqual(rules(run(({ catalog }) => catalog.items.push(row('epsilon')))), ['folder:missing:epsilon']);
});

test('a frontmatter name that is not the id fails', () => {
  const res = run(({ write }) => write('alpha/SKILL.md', '---\nname: alfa\ndescription: x\nlicense: Apache-2.0\n---\nbody\n'));
  assert.deepEqual(rules(res), ['frontmatter:name:alpha']);
});

test("a component's name is pinned by its row", () => {
  const res = run(({ write }) => write('bio-skills/gamma/one/SKILL.md', '---\nname: renamed\ndescription: x\nlicense: Apache-2.0\n---\nbody\n'));
  assert.deepEqual(rules(res), ['frontmatter:component-name-one:gamma']);
});

test('a component folder without an entry, and an active entry without a folder, both fail', () => {
  assert.deepEqual(rules(run(({ write }) => write('bio-skills/gamma/three/SKILL.md', '---\nname: gamma-three\ndescription: x\nlicense: Apache-2.0\n---\nb\n'))), ['components:unlisted-three:gamma']);
  assert.deepEqual(rules(run(({ root }) => fs.rmSync(path.join(root, 'bio-skills/gamma/two'), { recursive: true }))), ['components:missing-two:gamma']);
});

test('a version bump must reach every SKILL.md of the item', () => {
  const bump = (r) => {
    r.version = '1.1.0';
    r.history.push({ version: '1.1.0', date: '2026-11-22' });
  };
  // A 1.0.0 row may have no metadata.version; a 1.1.0 row may not.
  assert.deepEqual(rules(run(({ catalog }) => bump(catalog.items[0]))), ['version:version-SKILL.md:alpha']);
  const ok = run(({ catalog, write }) => {
    bump(catalog.items[0]);
    write('alpha/SKILL.md', '---\nname: alpha\ndescription: Plots volcanoes\nlicense: Apache-2.0\nmetadata:\n  version: "1.1.0"\n---\nbody\n');
  });
  assert.deepEqual(rules(ok), []);
  const partial = run(({ catalog, write }) => {
    bump(catalog.items[2]);
    write('bio-skills/gamma/one/SKILL.md', '---\nname: gamma-one\ndescription: x\nlicense: Apache-2.0\nmetadata:\n  version: "1.1.0"\n---\nb\n');
  });
  assert.deepEqual(rules(partial), ['version:version-two/SKILL.md:gamma']);
});

test('history must end at the row version and increase', () => {
  assert.deepEqual(rules(run(({ catalog }) => (catalog.items[0].history = [{ version: '0.9.0' }]))), ['row:history:alpha']);
});

test('a licence line that differs from the row fails, and a refused licence fails the row', () => {
  assert.deepEqual(rules(run(({ write }) => write('beta/SKILL.md', '---\nname: beta\ndescription: x\nlicense: MIT\n---\nb\n'))), ['licence:licence-SKILL.md:beta']);
  const gpl = run(({ catalog }) => {
    catalog.items[1].source = { origin: 'adapted', upstreams: [{ repo: 'x/y', licence: 'GPL-3.0' }], maintained_here: false };
  });
  assert.ok(rules(gpl).includes('row:upstream-licence:beta'));
});

test('MIT upstream text needs a notice file that carries the copyright line', () => {
  const up = { repo: 'x/y', licence: 'MIT', copyright: 'Copyright (c) 2026 Someone', commit: 'abcdef1' };
  const adapt = (catalog) => {
    catalog.items[0].source = { origin: 'adapted', upstreams: [up], maintained_here: false };
  };
  assert.deepEqual(rules(run(({ catalog }) => adapt(catalog))), ['notice:notice:alpha']);
  const wrong = run(({ catalog, write }) => {
    adapt(catalog);
    catalog.items[0].notice_file = 'LICENSE-UPSTREAM';
    write('alpha/LICENSE-UPSTREAM', 'MIT License\nCopyright (c) 2025 Someone Else\n');
  });
  assert.deepEqual(rules(wrong), ['notice:notice:alpha']);
  const right = run(({ catalog, write }) => {
    adapt(catalog);
    catalog.items[0].notice_file = 'LICENSE-UPSTREAM';
    write('alpha/LICENSE-UPSTREAM', 'MIT License\nCopyright (c) 2026 Someone\n');
  });
  assert.deepEqual(rules(right), []);
});

test('a merged row needs its generated stub and a complete redirect', () => {
  const merge = (catalog) => {
    const b = catalog.items[1];
    b.status = 'superseded_by:alpha';
    b.version = '1.1.0';
    b.history.push({ version: '1.1.0', date: '2026-11-22' });
    catalog.items[0].aliases = ['beta'];
  };
  // The old folder is still there, so the stub check fails.
  assert.deepEqual(rules(run(({ catalog }) => merge(catalog))), ['stub:stub:beta']);
  const stubbed = run(({ catalog, root }) => {
    merge(catalog);
    fs.rmSync(path.join(root, 'beta'), { recursive: true });
    fs.mkdirSync(path.join(root, 'beta'));
    for (const [n, t] of Object.entries(stubFiles(catalog.items[1], catalog))) fs.writeFileSync(path.join(root, 'beta', n), t);
  });
  assert.deepEqual(rules(stubbed), []);
  const noAlias = run(({ catalog, root }) => {
    merge(catalog);
    catalog.items[0].aliases = [];
    fs.rmSync(path.join(root, 'beta'), { recursive: true });
    fs.mkdirSync(path.join(root, 'beta'));
    for (const [n, t] of Object.entries(stubFiles(catalog.items[1], catalog))) fs.writeFileSync(path.join(root, 'beta', n), t);
  });
  assert.deepEqual(rules(noAlias), ['D4:alias:skill:beta']);
});

test('a hand-edited stub fails', () => {
  const res = run(({ catalog, root }) => {
    const b = catalog.items[1];
    b.status = 'retired';
    b.retired = { reason: 'no longer maintained' };
    b.version = '1.1.0';
    b.history.push({ version: '1.1.0', date: '2026-11-22' });
    fs.rmSync(path.join(root, 'beta'), { recursive: true });
    fs.mkdirSync(path.join(root, 'beta'));
    fs.writeFileSync(path.join(root, 'beta', 'SKILL.md'), `${stubFiles(b, catalog)['SKILL.md']}\nextra\n`);
  });
  assert.deepEqual(rules(res), ['stub:stub:beta']);
});

test('the D6 shell check runs over the single skills of the repository', () => {
  const res = run(({ catalog, write }) => {
    const shared = ['## When to use', 'Use for planning.', 'Verify the inputs.', 'Report the results.'];
    const words = ['apple', 'berry', 'cherry', 'damson', 'elderflower', 'fig'];
    for (const [i, id] of ['s1', 's2', 's3', 's4', 's5', 's6'].entries()) {
      write(`${id}/SKILL.md`, `---\nname: ${id}\ndescription: ${words[i]}\nlicense: Apache-2.0\n---\n# ${id}\n${shared.join('\n')}\n`);
      catalog.items.push(row(id));
    }
  });
  assert.deepEqual(rules(res), ['D6:shell:s1', 'D6:shell:s2', 'D6:shell:s3', 'D6:shell:s4', 'D6:shell:s5', 'D6:shell:s6']);
});

test('a baseline entry silences its failure until its work package is done', () => {
  const res = run(({ catalog, write }) => {
    write('beta/SKILL.md', '---\nname: beta\ndescription: x\nlicense: MIT\n---\nb\n');
    catalog.baseline_violations = [{ rule: 'licence', subject: 'licence-SKILL.md:beta', wp: 'WP-17' }];
  });
  assert.deepEqual(rules(res), []);
  const done = run(({ catalog, write }) => {
    write('beta/SKILL.md', '---\nname: beta\ndescription: x\nlicense: MIT\n---\nb\n');
    catalog.baseline_violations = [{ rule: 'licence', subject: 'licence-SKILL.md:beta', wp: 'WP-17' }];
    catalog.done_work_packages = ['WP-17'];
  });
  assert.deepEqual(rules(done), ['licence:licence-SKILL.md:beta']);
});

test('jobs.json must carry the same screen settings as the rules library', async () => {
  const { DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_COMPONENT_SIMILARITY_THRESHOLD, DEFAULT_GENERIC_WORDS } = await import('./lib/catalog-rules.mjs');
  const fx = makeFixture();
  const jobs = { similarity_threshold: DEFAULT_SIMILARITY_THRESHOLD, component_similarity_threshold: DEFAULT_COMPONENT_SIMILARITY_THRESHOLD, generic_words: [...DEFAULT_GENERIC_WORDS], builtin: [], required: [] };
  assert.deepEqual(rules(runCheck({ root: fx.root, catalog: fx.catalog, builtins: BUILTINS, jobs })), []);
  const drift = runCheck({ root: fx.root, catalog: fx.catalog, builtins: BUILTINS, jobs: { ...jobs, similarity_threshold: 0.4 } });
  assert.deepEqual(rules(drift), ['jobs:rules-drift']);
});
