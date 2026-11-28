// Builds one catalog item's release archive from its folder.

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { listTree } from './repo.mjs';
import { writeZip, readZip } from './zip.mjs';
import { folderProvenanceWanted } from './catalog-rules.mjs';
import { readProvenanceBaseline } from './provenance-baseline.mjs';

export function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

/** The file name the archive adds at its root when `addLicence` is set: Biorouter's own licence. */
export const ARCHIVE_LICENCE = 'LICENSE';

/**
 * The archive of a row: its folder under a root folder named by the id.
 *
 * With `addLicence`, the repository's LICENSE (Biorouter's own Apache-2.0
 * text) is added byte for byte as <id>/LICENSE, and a folder that holds its
 * own top-level LICENSE (in any case, since a case-insensitive file system
 * would extract both to one file) is refused: that name is reserved for the
 * repository's licence. Without it, the archive is the folder and nothing
 * else, exactly as before provenance format 2. archiveOptions() decides.
 */
export function buildItemZip(root, row, { addLicence = false } = {}) {
  const abs = path.join(root, row.path);
  if (!fs.existsSync(abs)) throw new Error(`${row.id}: folder ${row.path} does not exist`);
  const { files, dirs } = listTree(abs);
  const entries = [{ name: `${row.id}/`, dir: true }];
  for (const d of dirs) entries.push({ name: `${row.id}/${d}/`, dir: true });
  for (const f of files) entries.push({ name: `${row.id}/${f.rel}`, data: fs.readFileSync(f.abs), executable: f.executable });
  if (addLicence) {
    const own = [...files.map((f) => f.rel), ...dirs].find((rel) => !rel.includes('/') && rel.toLowerCase() === ARCHIVE_LICENCE.toLowerCase());
    if (own) throw new Error(`${row.id}: folder ${row.path} holds its own ${own}; <id>/${ARCHIVE_LICENCE} is reserved for the repository's licence (move the folder's text into its notice file)`);
    const lic = path.join(root, ARCHIVE_LICENCE);
    if (!fs.existsSync(lic)) throw new Error(`${row.id}: no ${ARCHIVE_LICENCE} at the repository root ${root} to add to the archive`);
    entries.push({ name: `${row.id}/${ARCHIVE_LICENCE}`, data: fs.readFileSync(lic), executable: false });
  }
  return writeZip(entries);
}

/**
 * The build options a row's release archive takes: the repository LICENSE is
 * added when the row's provenance folder files are wanted now (format 2 and
 * not deferred to its next release in provenance-baseline.json).
 */
export function archiveOptions(root, row, catalog) {
  return { addLicence: folderProvenanceWanted(row, { catalogFormat: catalog?.format, baseline: readProvenanceBaseline(root) }) };
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
