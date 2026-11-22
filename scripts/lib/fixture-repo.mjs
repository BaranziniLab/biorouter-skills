// A small throwaway repository for the check's tests: two single skills, one
// bundle, a catalog that passes, and the built-in names. Each test copies it,
// changes one thing, and expects exactly the failure that change should cause.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

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

export function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'catalog-fixture-'));
  const w = (rel, text) => {
    fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
    fs.writeFileSync(path.join(root, rel), text);
  };
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
  return { root, catalog, write: w };
}

export const clone = (x) => JSON.parse(JSON.stringify(x));
