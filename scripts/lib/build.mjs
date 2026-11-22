// Builds one catalog item's release archive from its folder.

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { listTree } from './repo.mjs';
import { writeZip, readZip } from './zip.mjs';

export function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

/** The archive of a row: its folder under a root folder named by the id. */
export function buildItemZip(root, row) {
  const abs = path.join(root, row.path);
  if (!fs.existsSync(abs)) throw new Error(`${row.id}: folder ${row.path} does not exist`);
  const { files, dirs } = listTree(abs);
  const entries = [{ name: `${row.id}/`, dir: true }];
  for (const d of dirs) entries.push({ name: `${row.id}/${d}/`, dir: true });
  for (const f of files) entries.push({ name: `${row.id}/${f.rel}`, data: fs.readFileSync(f.abs), executable: f.executable });
  return writeZip(entries);
}

/** A comparable listing of an archive: path, kind, mode bits that matter, content hash. */
export function archiveListing(buf) {
  return readZip(buf)
    .map((e) => ({ name: e.name, dir: e.dir, exec: !e.dir && (e.mode & 0o111) !== 0, sha: e.dir ? null : sha256(e.data) }))
    .sort((a, b) => (a.name < b.name ? -1 : 1));
}

/** Human-readable differences between two archives' contents. */
export function diffArchives(a, b) {
  const la = new Map(archiveListing(a).map((e) => [e.name, e]));
  const lb = new Map(archiveListing(b).map((e) => [e.name, e]));
  const out = [];
  for (const [n, e] of la) {
    const o = lb.get(n);
    if (!o) out.push(`only in the first: ${n}`);
    else if (e.sha !== o.sha) out.push(`content differs: ${n}`);
    else if (e.exec !== o.exec) out.push(`executable bit differs: ${n}`);
  }
  for (const n of lb.keys()) if (!la.has(n)) out.push(`only in the second: ${n}`);
  return out;
}
