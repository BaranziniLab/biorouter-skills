// The redirect stub that replaces a merged or retired skill's folder.
//
// A stub keeps the old skill's `name` (identity never moves) so that a person
// who installs from an old link, a cached registry or an older app's embedded
// registry gets a pointer instead of stale content. The text is generated from
// the catalog row, and check-catalog.mjs fails when a stub folder differs from
// what this function produces, so a stub can never drift from its row.
//
// A row in format 2 whose folder files are wanted now (folderProvenanceWanted
// in catalog-rules.mjs) gets the provenance variant: the front matter carries
// metadata.origin, metadata.credit and metadata.curated_by, and the body names
// the last real content's credit and the curator line. The default output is
// the stub as it was before format 2, byte for byte.

import { frontmatterCredits, stubCreditLines } from './catalog-rules.mjs';
import { yamlString } from './frontmatter.mjs';

/** How every stub's last bullet begins; the provenance credit lines go just before it. */
export const STUB_LAST_BULLET = '- This copy is only a';

function frontmatter({ name, description, version, status, credits = null }) {
  return [
    '---',
    `name: ${name}`,
    `description: ${yamlString(description)}`,
    'license: Apache-2.0',
    'user-invocable: true',
    'metadata:',
    `  version: ${yamlString(version)}`,
    `  status: ${yamlString(status)}`,
    ...(credits ? Object.entries(credits).map(([k, v]) => `  ${k}: ${yamlString(v)}`) : []),
    '---',
    '',
  ].join('\n');
}

function addFromBaam(targetId, targetName, oldId) {
  return (
    `If \`${targetId}\` is not installed, tell the person how to add it: in Biorouter, open ` +
    `Skills, choose Browse, search for "${targetName}" (a search for "${oldId}" finds it too), and add it.`
  );
}

/**
 * row: the catalog row of the old skill. catalog: the whole catalog (to find the
 * target's display name). provenance: write the format 2 credits (see above).
 * Returns { 'SKILL.md': text }.
 */
export function stubFiles(row, catalog, { provenance = false } = {}) {
  const byId = new Map((catalog.items ?? []).map((r) => [r.id, r]));
  const status = row.status;
  let description;
  let body;
  if (status.startsWith('superseded_by:builtin:')) {
    const name = status.slice('superseded_by:builtin:'.length);
    description = `Moved: this skill is now part of Biorouter's built-in ${name} skill. Use ${name} instead.`;
    body = [
      `# ${row.display_name} has moved`,
      '',
      `This skill is now part of **${name}**, a skill that ships built into Biorouter.`,
      '',
      `- Use the built-in \`${name}\` skill for this work. Load it now and follow it.`,
      `- If \`${name}\` is missing, this copy of Biorouter is older than the skill; tell the person to update Biorouter.`,
      `- This copy is only a pointer and can be removed. Its content lives on in \`${name}\`.`,
      '',
    ];
  } else if (status.startsWith('superseded_by:')) {
    const targetId = status.slice('superseded_by:'.length);
    const target = byId.get(targetId);
    const targetName = target?.display_name ?? targetId;
    description = `Moved: this skill is now part of ${targetName} (${targetId}). Use ${targetId} instead.`;
    body = [
      `# ${row.display_name} has moved`,
      '',
      `This skill is now part of **${targetName}** (\`${targetId}\`).`,
      '',
      `- Use the \`${targetId}\` skill for this work. If it is installed, load it now and follow it.`,
      `- ${addFromBaam(targetId, targetName, row.id)}`,
      `- If an older copy of \`${row.id}\` is still installed next to \`${targetId}\`, \`${targetId}\` is the current version of its content and wins.`,
      `- This copy is only a pointer and can be removed.`,
      '',
    ];
  } else if (status === 'retired') {
    const r = row.retired ?? {};
    const use = r.use ?? null;
    const useText = use
      ? use.startsWith('builtin:')
        ? `Biorouter's built-in ${use.slice('builtin:'.length)} skill`
        : `${byId.get(use)?.display_name ?? use} (${use})`
      : null;
    description = `Retired: ${r.reason ?? 'this skill is no longer maintained'}.${useText ? ` Use ${useText} instead.` : ''}`;
    body = [`# ${row.display_name} is retired`, '', `${r.reason ?? 'This skill is no longer maintained'}.`, ''];
    if (use && use.startsWith('builtin:')) {
      const name = use.slice('builtin:'.length);
      body.push(
        `- Use the built-in \`${name}\` skill instead. Load it now and follow it.`,
        `- If \`${name}\` is missing, this copy of Biorouter is older than the skill; tell the person to update Biorouter.`,
      );
    } else if (use) {
      body.push(
        `- Use the \`${use}\` skill instead. If it is installed, load it now and follow it.`,
        `- ${addFromBaam(use, byId.get(use)?.display_name ?? use, row.id)}`,
      );
    }
    if (r.guidance) body.push(`- ${r.guidance}`);
    body.push('- This copy is only a notice and can be removed.', '');
  } else {
    throw new Error(`${row.id} is active; only a merged or retired skill gets a stub`);
  }
  let credits = null;
  if (provenance) {
    credits = frontmatterCredits(row);
    // The credit lines go before the bullet that says what this copy is
    // ("- This copy is only a pointer ..." or "... only a notice ..."), found by
    // its text, so a change to the body's shape cannot move them.
    const last = body.findIndex((line) => line.startsWith(STUB_LAST_BULLET));
    if (last < 0 || body.findIndex((line, i) => i > last && line.startsWith(STUB_LAST_BULLET)) >= 0) {
      throw new Error(`${row.id}: the stub body has no single "${STUB_LAST_BULLET}" bullet to put the credit lines before`);
    }
    body.splice(last, 0, ...stubCreditLines(row, catalog.items ?? []).map((line) => `- ${line}`));
  }
  const text = frontmatter({ name: row.id, description, version: row.version, status, credits }) + '\n' + body.join('\n');
  return { 'SKILL.md': text };
}
