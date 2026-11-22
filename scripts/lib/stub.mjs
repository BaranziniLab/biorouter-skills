// The redirect stub that replaces a merged or retired skill's folder.
//
// A stub keeps the old skill's `name` (identity never moves) so that a person
// who installs from an old link, a cached registry or an older app's embedded
// registry gets a pointer instead of stale content. The text is generated from
// the catalog row, and check-catalog.mjs fails when a stub folder differs from
// what this function produces, so a stub can never drift from its row.

function yamlString(value) {
  return `"${String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function frontmatter({ name, description, version, status }) {
  return [
    '---',
    `name: ${name}`,
    `description: ${yamlString(description)}`,
    'license: Apache-2.0',
    'user-invocable: true',
    'metadata:',
    `  version: ${yamlString(version)}`,
    `  status: ${yamlString(status)}`,
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
 * target's display name). Returns { 'SKILL.md': text }.
 */
export function stubFiles(row, catalog) {
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
  const text = frontmatter({ name: row.id, description, version: row.version, status }) + '\n' + body.join('\n');
  return { 'SKILL.md': text };
}
