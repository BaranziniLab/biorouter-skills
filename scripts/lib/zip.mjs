// Deterministic ZIP writer and a small reader, with no dependencies.
//
// Every entry is STORED (no compression). That is the whole point: Node's
// bundled zlib is Chromium's fork, whose deflate output can differ between CPU
// architectures and releases, so a deflated zip built on an arm64 laptop and the
// same folder built on an x86 runner could have different bytes. Stored entries,
// sorted names, one fixed timestamp and fixed attributes make the archive a pure
// function of the folder, which is what verify-release.mjs compares by SHA-256.
// The skill archives are small (the largest bundle is about 1 MB uncompressed).

import zlib from 'node:zlib';

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// 1980-01-01 00:00:00, the earliest DOS timestamp.
const DOS_DATE = (0 << 9) | (1 << 5) | 1;
const DOS_TIME = 0;
const FLAG_UTF8 = 0x0800;
const MADE_BY_UNIX = (3 << 8) | 20;

/**
 * entries: [{ name: 'id/dir/', dir: true } | { name: 'id/file', data: Buffer, executable: bool }]
 * Names use forward slashes; directories end with '/'. The caller sorts nothing:
 * this function sorts by name so the order never depends on readdir.
 */
export function writeZip(entries) {
  const sorted = [...entries].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  const seen = new Set();
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const e of sorted) {
    if (seen.has(e.name)) throw new Error(`duplicate zip entry ${e.name}`);
    seen.add(e.name);
    const name = Buffer.from(e.name, 'utf8');
    const data = e.dir ? Buffer.alloc(0) : e.data;
    const crc = e.dir ? 0 : crc32(data);
    const mode = e.dir ? 0o040755 : e.executable ? 0o100755 : 0o100644;
    const external = ((mode << 16) | (e.dir ? 0x10 : 0)) >>> 0;

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(10, 4);
    local.writeUInt16LE(FLAG_UTF8, 6);
    local.writeUInt16LE(0, 8);
    local.writeUInt16LE(DOS_TIME, 10);
    local.writeUInt16LE(DOS_DATE, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    locals.push(local, name, data);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(MADE_BY_UNIX, 4);
    central.writeUInt16LE(10, 6);
    central.writeUInt16LE(FLAG_UTF8, 8);
    central.writeUInt16LE(0, 10);
    central.writeUInt16LE(DOS_TIME, 12);
    central.writeUInt16LE(DOS_DATE, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(external, 38);
    central.writeUInt32LE(offset, 42);
    centrals.push(central, name);

    offset += 30 + name.length + data.length;
  }
  const cd = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(sorted.length, 8);
  end.writeUInt16LE(sorted.length, 10);
  end.writeUInt32LE(cd.length, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);
  if (offset > 0xffffffff || sorted.length > 0xffff) throw new Error('archive needs zip64, which this writer does not produce');
  return Buffer.concat([...locals, cd, end]);
}

/** Reads any ordinary zip (stored or deflated): [{ name, dir, data, mode }]. */
export function readZip(buf) {
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 22 - 0xffff); i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) {
      eocd = i;
      break;
    }
  }
  if (eocd === -1) throw new Error('not a zip archive (no end of central directory)');
  const count = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  const out = [];
  for (let n = 0; n < count; n++) {
    if (buf.readUInt32LE(p) !== 0x02014b50) throw new Error('corrupt central directory');
    const method = buf.readUInt16LE(p + 10);
    const csize = buf.readUInt32LE(p + 20);
    const nameLen = buf.readUInt16LE(p + 28);
    const extraLen = buf.readUInt16LE(p + 30);
    const commentLen = buf.readUInt16LE(p + 32);
    const external = buf.readUInt32LE(p + 38);
    const localOffset = buf.readUInt32LE(p + 42);
    const name = buf.slice(p + 46, p + 46 + nameLen).toString('utf8');
    const lNameLen = buf.readUInt16LE(localOffset + 26);
    const lExtraLen = buf.readUInt16LE(localOffset + 28);
    const start = localOffset + 30 + lNameLen + lExtraLen;
    const raw = buf.slice(start, start + csize);
    let data;
    if (method === 0) data = Buffer.from(raw);
    else if (method === 8) data = zlib.inflateRawSync(raw);
    else throw new Error(`unsupported compression method ${method} for ${name}`);
    out.push({ name, dir: name.endsWith('/'), data, mode: external >>> 16 });
    p += 46 + nameLen + extraLen + commentLen;
  }
  return out;
}
