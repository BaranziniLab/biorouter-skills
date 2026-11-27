// Format 2 provenance records for the tests: one valid record per origin, a
// bundle with a component written for Biorouter and a merged file, a merged
// stub, and a third-party extension row. Every builder returns a fresh object,
// so a test can change one field and expect exactly the failure that causes.
//
// Data only: no folders. A test that needs folders writes them with
// makeFixture() from fixture-repo.mjs and the generators.
//
// This module is part of the step 1 contract (designer-owned): lanes import
// it and build further cases in their own test files from these builders.

import { CURATED_BY } from './catalog-rules.mjs';

export const LAB = Object.freeze({ name: 'Wanjun Gu', affiliation: 'Baranzini Lab, UCSF', role: 'wrote it' });

export const MIT_TEXT_COPYRIGHT = 'Copyright (c) 2026 Example Org';

export function contributor(over = {}) {
  return { ...LAB, ...over };
}

/** A copied MIT source, complete. */
export function upstream(over = {}) {
  return {
    kind: 'repository',
    repo: 'example-org/example-skills',
    display: 'example-skills',
    url: 'https://github.com/example-org/example-skills',
    path: 'skills/example',
    commit: '0123456789abcdef0123456789abcdef01234567',
    version: null,
    licence: 'MIT',
    copyright: MIT_TEXT_COPYRIGHT,
    copyright_note: null,
    credit: 'Example Org',
    people: [],
    use: ['text'],
    what: 'the example SKILL.md and its references',
    files: ['SKILL.md'],
    via: null,
    upstream_notice: false,
    owner: 'external',
    taken: '2026-11-25',
    ...over,
  };
}

/** An ideas-only source that shapes the current version. */
export function idea(over = {}) {
  return {
    kind: 'repository',
    name: 'Example Research Skills',
    url: 'https://github.com/example-lab/example-research-skills',
    licence: 'CC-BY-SA-4.0',
    credit: 'Example Lab',
    what: 'the stage list and the idea of a gate per stage',
    evidence: '0 shared six-word runs with the version read',
    version_read: null,
    applies_to: 'current',
    ...over,
  };
}

export function dataset(over = {}) {
  return {
    kind: 'dataset',
    name: 'Example KG 1.0',
    url: 'https://doi.org/10.0000/example',
    terms: 'CC0-1.0',
    credit: 'A. Author, B. Author',
    cite: 'An example knowledge graph. Example Journal 1, 1 (2026).',
    how: 'downloaded once on request, not bundled',
    ...over,
  };
}

function base(id, over = {}) {
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
    licence: 'Apache-2.0',
    notice_file: null,
    release: { tag: `skill-${id}`, asset: `${id}.zip`, sha256: null },
    components: null,
    history: [{ version: '1.0.0', date: '2026-07-01' }],
    contributors: [contributor()],
    ...over,
  };
}

function source(over = {}) {
  return {
    format: 2,
    origin: 'in-house',
    upstreams: [],
    ideas_from: [],
    data_and_services: [],
    references: [],
    refused_sources: [],
    changes: null,
    maintained_here: false,
    ...over,
  };
}

/** in-house: "Made by the Baranzini Lab (Wanjun Gu, UCSF)." */
export function inHouseRow(id = 'alpha', over = {}) {
  return base(id, { source: source({ data_and_services: [dataset()] }), ...over });
}

/** ideas-derived: written here, shaped by one current idea and one earlier one. */
export function ideasDerivedRow(id = 'alpha', over = {}) {
  return base(id, {
    source: source({
      origin: 'ideas-derived',
      ideas_from: [idea(), idea({ name: 'Earlier Skill List', url: 'https://github.com/example-lab/earlier', credit: 'Example Lab', applies_to: 'earlier', what: 'the topic of version 1.0.0' })],
    }),
    ...over,
  });
}

/** adapted: MIT text changed for Biorouter, with its notice file. */
export function adaptedRow(id = 'alpha', over = {}) {
  return base(id, {
    licence: 'Apache-2.0 AND MIT',
    notice_file: 'LICENSE-UPSTREAM',
    source: source({ origin: 'adapted', upstreams: [upstream()], changes: 'SKILL.md rewritten for Biorouter; one script kept unchanged.' }),
    contributors: [contributor({ role: 'adapted it for Biorouter' })],
    ...over,
  });
}

/**
 * third-party bundle kept largely as published, with one component written
 * for Biorouter (in-house, Apache-2.0) and one component merged into a file of
 * another component, which lists it under written_for_biorouter.
 */
export function thirdPartyBundleRow(id = 'gamma', over = {}) {
  const repo = 'example-org/bio-skills';
  return base(id, {
    kind: 'bundle',
    category: 'biomedical',
    path: `bio-skills/${id}`,
    invocation: 'bundle',
    licence: 'Apache-2.0 AND MIT',
    notice_file: 'LICENSE-UPSTREAM',
    source: source({
      origin: 'third-party',
      upstreams: [upstream({ repo, display: 'bioSkills', url: `https://github.com/${repo}`, path: id, credit: 'Example Org', what: `the ${id} skills`, files: ['one/', 'two/'] })],
      changes: 'packaging only: front matter names and versions',
      maintained_here: true,
    }),
    components: {
      one: { name: `${id}-one`, status: 'active', job: `test.${id}.one`, upstream_path: `${repo}:${id}/one`, licence: 'MIT', sources: [0],
        written_for_biorouter: [{ path: 'references/merged-notes.md', origin: 'ideas-derived', licence: 'Apache-2.0', what: 'notes merged from the old three component',
          ideas_from: [idea({ name: 'Example Tool Skill', kind: 'skill', url: 'https://github.com/example-lab/tool-skill', what: 'which tool to teach' })] }] },
      two: { name: `${id}-two`, status: 'active', job: `test.${id}.two`, upstream_path: null, origin: 'in-house', licence: 'Apache-2.0' },
      three: { name: `${id}-three`, status: `superseded_by:${id}/one`, job: `test.${id}.three`, upstream_path: null, origin: 'ideas-derived', licence: 'Apache-2.0',
        ideas_from: [idea({ name: 'Example Tool Skill', kind: 'skill', url: 'https://github.com/example-lab/tool-skill', what: 'which tool to teach' })],
        content_moved_to: `${id}/one/references/merged-notes.md` },
    },
    contributors: [contributor({ role: 'packaged it for Biorouter' })],
    ...over,
  });
}

/** A merged stub: keeps the provenance of its last real content. */
export function stubRow(id = 'beta', target = 'alpha', over = {}) {
  return base(id, {
    version: '1.1.0',
    status: `superseded_by:${target}`,
    history: [{ version: '1.0.0', date: '2026-06-10', origin: 'adapted', licence: 'MIT' }, { version: '1.1.0', date: '2026-11-22', origin: 'adapted', licence: 'Apache-2.0' }],
    source: source({ origin: 'adapted', upstreams: [upstream()], changes: 'version 1.0.0 kept the upstream text; 1.1.0 is a redirect stub', content_moved_to: target }),
    ...over,
  });
}

/** A third-party extension row (landing's catalog): runs an outside program. */
export function thirdPartyExtensionRow(id = 'exampleagent', over = {}) {
  return {
    id,
    display_name: 'ExampleAgent',
    manifest_name: id,
    repository: 'BaranziniLab/ExampleAgent',
    group: 'adapters',
    version: '0.1.0',
    status: 'active',
    aliases: [],
    job: 'test.example-agent',
    role: 'data-access',
    summary: '',
    keywords: [],
    licence: 'Apache-2.0 AND MIT',
    history: [{ version: '0.1.0', date: '2026-11-22' }],
    source: source({
      origin: 'third-party',
      upstreams: [upstream({ kind: 'package', repo: 'example-org/example-mcp', display: 'Example MCP', url: 'https://github.com/example-org/example-mcp', path: null, commit: null, version: '0.9.3', use: ['launched'], what: 'example-mcp launched by the extension from PyPI, pinned by SHA-256', files: [], credit: 'Ada Example' })],
      changes: 'launcher, policy and packaging only',
      built_with: null,
    }),
    contributors: [contributor({ role: 'wrote the extension' })],
    ...over,
  };
}

/** Every valid record above, as one catalog's items (skills only). */
export function validSkillRows() {
  return [adaptedRow('alpha'), ideasDerivedRow('delta'), inHouseRow('epsilon'), thirdPartyBundleRow('gamma'), stubRow('beta', 'alpha')];
}

export { CURATED_BY };
