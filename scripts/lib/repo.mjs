// Reads skill folders from a checkout of this repository.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readSkillText } from './frontmatter.mjs';

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

// Top-level entries that are repository plumbing, not skills.
export const NON_ITEM_TOP = new Set(['.git', '.github', 'scripts', 'bio-skills', 'dist', 'node_modules']);

// Files that never belong in a release archive.
export function isJunk(name) {
  return (
    name === '.DS_Store' ||
    name === 'Thumbs.db' ||
    name === 'desktop.ini' ||
    name === '__pycache__' ||
    name === '.ipynb_checkpoints' ||
    name.startsWith('._') ||
    name.endsWith('.pyc')
  );
}

/** Every file and directory under `dir`, relative and POSIX-style, junk skipped, sorted. */
export function listTree(dir) {
  const files = [];
  const dirs = [];
  const walk = (abs, rel) => {
    const names = fs.readdirSync(abs).sort();
    for (const name of names) {
      if (isJunk(name)) continue;
      const a = path.join(abs, name);
      const r = rel ? `${rel}/${name}` : name;
      const st = fs.lstatSync(a);
      if (st.isSymbolicLink()) throw new Error(`symbolic link in a skill folder: ${a}`);
      if (st.isDirectory()) {
        dirs.push(r);
        walk(a, r);
      } else if (st.isFile()) {
        files.push({ rel: r, abs: a, executable: (st.mode & 0o111) !== 0 });
      }
    }
  };
  walk(dir, '');
  return { files, dirs };
}

/** The folders on disk that hold a catalog item: top-level skills and bundles, and bio-skills/<id>. */
export function discoverFolders(root = REPO_ROOT) {
  const out = [];
  for (const name of fs.readdirSync(root).sort()) {
    if (name.startsWith('.') || NON_ITEM_TOP.has(name)) continue;
    const abs = path.join(root, name);
    if (!fs.statSync(abs).isDirectory()) continue;
    out.push({ id: name, path: name });
  }
  const bio = path.join(root, 'bio-skills');
  if (fs.existsSync(bio)) {
    for (const name of fs.readdirSync(bio).sort()) {
      const abs = path.join(bio, name);
      if (name.startsWith('.') || !fs.statSync(abs).isDirectory()) continue;
      out.push({ id: name, path: `bio-skills/${name}` });
    }
  }
  return out;
}

export function readSkillFile(abs) {
  if (!fs.existsSync(abs)) return { exists: false, ok: false, frontmatter: {}, body: '', text: '' };
  const text = fs.readFileSync(abs, 'utf8');
  return { exists: true, text, ...readSkillText(text) };
}

/** The component folders of a bundle: immediate subdirectories that hold a SKILL.md. */
export function bundleComponents(root, relPath) {
  const abs = path.join(root, relPath);
  if (!fs.existsSync(abs)) return [];
  return fs
    .readdirSync(abs)
    .sort()
    .filter((name) => !isJunk(name) && fs.statSync(path.join(abs, name)).isDirectory())
    .filter((name) => fs.existsSync(path.join(abs, name, 'SKILL.md')))
    .map((folder) => ({ folder, ...readSkillFile(path.join(abs, folder, 'SKILL.md')) }));
}

/** Every SKILL.md inside an item's folder, at any depth, relative to the item folder. */
export function skillFilesIn(root, relPath) {
  const abs = path.join(root, relPath);
  if (!fs.existsSync(abs)) return [];
  return listTree(abs)
    .files.filter((f) => path.posix.basename(f.rel) === 'SKILL.md')
    .map((f) => ({ rel: f.rel, ...readSkillFile(f.abs) }));
}
