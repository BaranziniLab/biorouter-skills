#!/usr/bin/env node
// Writes builtin-skill-names.json: the skill and extension names Biorouter
// ships, read from a biorouter checkout, so no BAAM item can take one.
//
//   node scripts/builtin-names.mjs --biorouter-repo <path>          # rewrite the file
//   node scripts/builtin-names.mjs --biorouter-repo <path> --check  # fail if it is stale
//
// Sources in the biorouter repository:
//   crates/biorouter/src/agents/skills_extension.rs  BUILTIN_SKILLS, KNOWLEDGE_SKILLS, KNOWLEDGE_BUNDLE
//   crates/biorouter/src/knowledge/soul.rs           SOUL_SKILL_DIR (and the legacy name)
//   crates/biorouter/src/agents/builtin_skills/      one folder per shipped skill (cross-checked)
//   ui/desktop/src/utils/toolGlyph.ts                BUILT_IN_EXTENSION_KEYS and display labels

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT } from './lib/repo.mjs';

function arrayNames(src, ident) {
  const start = src.indexOf(`pub static ${ident}`);
  if (start === -1) throw new Error(`${ident} not found`);
  const end = src.indexOf('];', start);
  return [...src.slice(start, end).matchAll(/\(\s*"([a-z0-9-]+)",\s*include_str!/g)].map((m) => m[1]);
}

function constValue(src, ident) {
  const m = src.match(new RegExp(`pub const ${ident}: &str = "([^"]+)"`));
  if (!m) throw new Error(`${ident} not found`);
  return m[1];
}

export function readBuiltins(repo) {
  const skillsRs = fs.readFileSync(path.join(repo, 'crates/biorouter/src/agents/skills_extension.rs'), 'utf8');
  const soulRs = fs.readFileSync(path.join(repo, 'crates/biorouter/src/knowledge/soul.rs'), 'utf8');
  const glyph = fs.readFileSync(path.join(repo, 'ui/desktop/src/utils/toolGlyph.ts'), 'utf8');
  const skills = [...arrayNames(skillsRs, 'BUILTIN_SKILLS'), ...arrayNames(skillsRs, 'KNOWLEDGE_SKILLS'), constValue(soulRs, 'SOUL_SKILL_DIR')];
  const legacy = [constValue(soulRs, 'SOUL_SKILL_DIR_LEGACY')];
  const bundles = [constValue(skillsRs, 'KNOWLEDGE_BUNDLE')];
  const folders = fs.readdirSync(path.join(repo, 'crates/biorouter/src/agents/builtin_skills')).filter((n) => !n.startsWith('.')).sort();
  for (const f of folders) if (!skills.includes(f)) throw new Error(`builtin_skills/${f} is not in BUILTIN_SKILLS or KNOWLEDGE_SKILLS`);
  const keysAt = glyph.indexOf('export const BUILT_IN_EXTENSION_KEYS');
  const labelsAt = glyph.indexOf('const DISPLAY_KEY_ALIASES');
  if (keysAt === -1 || labelsAt === -1) throw new Error('toolGlyph.ts no longer declares BUILT_IN_EXTENSION_KEYS and DISPLAY_KEY_ALIASES');
  const keysBlock = glyph.slice(keysAt, glyph.indexOf(']);', keysAt));
  // `platform` and `workflow` are tool prefixes, not extensions.
  const keys = [...keysBlock.matchAll(/'([a-z_]+)'/g)].map((m) => m[1]).filter((k) => k !== 'platform' && k !== 'workflow');
  const labelBlock = glyph.slice(labelsAt, glyph.indexOf('] as const', labelsAt));
  const labels = [...labelBlock.matchAll(/\['([^']+)', '[a-z_]+'\]/g)].map((m) => m[1]);
  let commit = null;
  try {
    commit = execFileSync('git', ['-C', repo, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  } catch {}
  return {
    format: 1,
    source: { repo: 'BaranziniLab/biorouter', commit },
    skills: [...new Set(skills)].sort(),
    legacy_skills: legacy,
    bundles,
    extensions: [...new Set([...keys, ...labels])].sort(),
  };
}

function render(obj) {
  return `${JSON.stringify(obj, null, 2)}\n`;
}

function main() {
  const argv = process.argv.slice(2);
  const i = argv.indexOf('--biorouter-repo');
  if (i === -1) {
    console.error('usage: node scripts/builtin-names.mjs --biorouter-repo <path> [--check]');
    process.exit(2);
  }
  const repo = path.resolve(argv[i + 1]);
  const out = path.join(REPO_ROOT, 'builtin-skill-names.json');
  const next = readBuiltins(repo);
  if (argv.includes('--check')) {
    const cur = JSON.parse(fs.readFileSync(out, 'utf8'));
    const strip = (o) => JSON.stringify({ ...o, source: { repo: o.source?.repo } });
    if (strip(cur) !== strip(next)) {
      console.error('builtin-skill-names.json is stale; run node scripts/builtin-names.mjs --biorouter-repo <path>');
      process.exit(1);
    }
    console.log('builtin-skill-names.json is current');
    return;
  }
  fs.writeFileSync(out, render(next));
  console.log(`wrote ${path.relative(process.cwd(), out)}: ${next.skills.length} skills, ${next.bundles.length} bundle, ${next.extensions.length} extension names`);
}

main();
