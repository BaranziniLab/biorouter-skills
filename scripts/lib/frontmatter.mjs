// Reads the YAML frontmatter that Biorouter skills use.
//
// The subset is deliberately small, because every SKILL.md in this repository
// uses only it: top-level scalars, block scalars (`>` and `|`), simple lists,
// and one level of nested maps (the Agent Skills `metadata` map). Anything more
// deeply nested is kept as raw text so a check can still see that it exists.
// No dependencies, so the check runs on a bare Node install.

const KEY = /^([A-Za-z0-9_.-]+):(?:\s+(.*))?$/;

export function splitFrontmatter(text) {
  const normalized = text.replace(/\r\n/g, '\n');
  if (!normalized.startsWith('---\n')) {
    return { ok: false, raw: '', body: normalized };
  }
  const end = normalized.indexOf('\n---', 4);
  if (end === -1) return { ok: false, raw: '', body: normalized };
  const after = normalized.indexOf('\n', end + 4);
  const raw = normalized.slice(4, end);
  const body = after === -1 ? '' : normalized.slice(after + 1);
  return { ok: true, raw, body };
}

export function unquote(value) {
  const v = value.trim();
  if (v.length >= 2 && v.startsWith('"') && v.endsWith('"')) {
    return v
      .slice(1, -1)
      .replace(/\\(["\\nt])/g, (_, c) => ({ n: '\n', t: '\t', '"': '"', '\\': '\\' })[c]);
  }
  if (v.length >= 2 && v.startsWith("'") && v.endsWith("'")) {
    return v.slice(1, -1).replace(/''/g, "'");
  }
  // A trailing comment on a plain scalar.
  const hash = v.search(/\s#/);
  return hash === -1 ? v : v.slice(0, hash).trimEnd();
}

function indentOf(line) {
  return line.length - line.trimStart().length;
}

function readBlockScalar(lines, start, style) {
  const out = [];
  let i = start;
  let indent = null;
  for (; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === '') {
      out.push('');
      continue;
    }
    const ind = indentOf(line);
    if (indent === null) indent = ind;
    if (ind < indent || ind === 0) break;
    out.push(line.slice(indent));
  }
  while (out.length && out[out.length - 1] === '') out.pop();
  const text = style.startsWith('|') ? out.join('\n') : out.join(' ').replace(/\s+/g, ' ').trim();
  return { value: text, next: i };
}

export function parseFrontmatter(raw) {
  const lines = raw.split('\n');
  const data = {};
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.trim() === '' || line.trimStart().startsWith('#')) {
      i++;
      continue;
    }
    if (indentOf(line) > 0) {
      i++;
      continue;
    }
    const m = line.match(KEY);
    if (!m) {
      i++;
      continue;
    }
    const key = m[1];
    const rest = m[2] === undefined ? '' : m[2];
    if (rest === '' ) {
      // A nested map or a list, made of the indented lines that follow.
      const block = [];
      let j = i + 1;
      for (; j < lines.length; j++) {
        if (lines[j].trim() !== '' && indentOf(lines[j]) === 0) break;
        block.push(lines[j]);
      }
      const content = block.filter((l) => l.trim() !== '');
      if (content.length && content[0].trimStart().startsWith('- ')) {
        const base = indentOf(content[0]);
        data[key] = content
          .filter((l) => indentOf(l) === base && l.trimStart().startsWith('- '))
          .map((l) => unquote(l.trimStart().slice(2)));
      } else if (content.length) {
        const base = indentOf(content[0]);
        const map = {};
        for (let k = 0; k < block.length; k++) {
          const l = block[k];
          if (l.trim() === '' || indentOf(l) !== base) continue;
          const mm = l.trim().match(KEY);
          if (!mm) continue;
          const v = mm[2] === undefined ? '' : mm[2];
          if (/^[>|][-+]?$/.test(v)) {
            const sub = readBlockScalar(block, k + 1, v);
            map[mm[1]] = sub.value;
          } else {
            map[mm[1]] = unquote(v);
          }
        }
        data[key] = map;
      } else {
        data[key] = '';
      }
      i = j;
      continue;
    }
    if (/^[>|][-+]?$/.test(rest)) {
      const sub = readBlockScalar(lines, i + 1, rest);
      data[key] = sub.value;
      i = sub.next;
      continue;
    }
    data[key] = unquote(rest);
    i++;
  }
  return data;
}

export function readSkillText(text) {
  const split = splitFrontmatter(text);
  return { ok: split.ok, frontmatter: split.ok ? parseFrontmatter(split.raw) : {}, body: split.body };
}

// ---------------------------------------------------------------------------
// Writing front matter.

/** A YAML double-quoted string, the quoting scripts/lib/stub.mjs and the generators use. */
export function yamlString(value) {
  return `"${String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

/**
 * The provenance keys format 1 skills wrote under `metadata` and format 2
 * retires: the generated `metadata.origin`, `metadata.credit` and
 * `metadata.curated_by` replace them.
 */
export const RETIRED_METADATA_KEYS = Object.freeze(['upstream_licence', 'upstream_author', 'source']);

/**
 * True when a `metadata.upstream` value ("<owner>/<repo>[/<path>]@<commit>")
 * names an upstream repository of the row, compared case-blind. This is a
 * stricter test than PV10's warning (which accepts any mention of a source's
 * repo or URL), so a file the generator writes never draws that warning.
 */
export function metadataUpstreamNamesRow(value, row) {
  const ref = String(value ?? '').trim().split('@')[0];
  const parts = ref.split('/');
  if (parts.length < 2 || !parts[0] || !parts[1]) return false;
  const repo = `${parts[0]}/${parts[1]}`.toLowerCase();
  return (row?.source?.upstreams ?? []).some((u) => typeof u?.repo === 'string' && u.repo.toLowerCase() === repo);
}

/**
 * The `remove` predicate for setMetadata on a row's SKILL.md: the retired keys
 * always, and `upstream` unless it names an upstream of the row.
 */
export function retiredMetadataKey(row) {
  return (key, value) => RETIRED_METADATA_KEYS.includes(key) || (key === 'upstream' && !metadataUpstreamNamesRow(value, row));
}

const TOP_KEY = /^([A-Za-z0-9_.-]+):(?:\s+(.*))?$/;

/**
 * Writes `values` as keys of the front matter's `metadata` map, quoted with
 * yamlString, and removes the keys `remove` names (a list of keys, or a
 * predicate (key, value) => boolean; a key in `values` is never removed).
 * An existing key is rewritten in place; a new one is added at the end of the
 * map; a missing map is created after the `user-invocable` or `license` line
 * (the later of the two), else at the end of the front matter. Every other
 * byte of the file is unchanged, line endings included.
 */
export function setMetadata(text, values = {}, { remove = [] } = {}) {
  const src = String(text);
  const crlf = /^---\r\n/.test(src);
  if (!/^---\r?\n/.test(src)) throw new Error('the file has no front matter');
  const cr = crlf ? '\r' : '';
  const lines = src.split('\n');
  const bare = (l) => l.replace(/\r$/, '');
  let close = -1;
  for (let i = 1; i < lines.length; i++) {
    if (bare(lines[i]).startsWith('---')) {
      close = i;
      break;
    }
  }
  if (close === -1) throw new Error('the front matter is not closed');
  const removes = typeof remove === 'function' ? remove : (key) => remove.includes(key);
  const want = Object.entries(values ?? {}).filter(([, v]) => v !== undefined && v !== null);
  const indentOf = (l) => bare(l).length - bare(l).trimStart().length;
  const blank = (l) => bare(l).trim() === '';

  let meta = -1;
  for (let i = 1; i < close; i++) {
    if (indentOf(lines[i]) === 0 && /^metadata:\s*$/.test(bare(lines[i]))) {
      meta = i;
      break;
    }
  }

  if (meta === -1) {
    if (!want.length) return src;
    let at = close;
    let anchor = -1;
    for (let i = 1; i < close; i++) {
      const m = indentOf(lines[i]) === 0 ? bare(lines[i]).match(TOP_KEY) : null;
      if (m && (m[1] === 'user-invocable' || m[1] === 'license')) anchor = i;
    }
    if (anchor !== -1) {
      at = anchor + 1;
      // A value continued on indented lines belongs to the anchor key.
      while (at < close && !blank(lines[at]) && indentOf(lines[at]) > 0) at++;
    }
    const block = ['metadata:', ...want.map(([k, v]) => `  ${k}: ${yamlString(v)}`)].map((l) => l + cr);
    return [...lines.slice(0, at), ...block, ...lines.slice(at)].join('\n');
  }

  // The map's lines run from meta + 1 to the next top-level line (or the close).
  let end = meta + 1;
  while (end < close && (blank(lines[end]) || indentOf(lines[end]) > 0)) end++;
  const firstChild = lines.slice(meta + 1, end).find((l) => !blank(l));
  const base = firstChild ? indentOf(firstChild) : 2;
  const pad = ' '.repeat(base);
  const entries = [];
  for (let i = meta + 1; i < end; i++) {
    if (blank(lines[i]) || indentOf(lines[i]) !== base) continue;
    const m = bare(lines[i]).trim().match(TOP_KEY);
    if (!m) continue;
    let j = i + 1;
    while (j < end && (blank(lines[j]) || indentOf(lines[j]) > base)) j++;
    // Trailing blank lines stay where they are.
    while (j > i + 1 && blank(lines[j - 1])) j--;
    entries.push({ key: m[1], value: unquote(m[2] ?? ''), start: i, end: j });
  }
  const wanted = new Map(want);
  const out = lines.slice(0, meta + 1);
  const done = new Set();
  let cursor = meta + 1;
  let lastKeyed = out.length; // index in `out` just after the last kept entry
  for (const e of entries) {
    out.push(...lines.slice(cursor, e.start));
    cursor = e.end;
    if (wanted.has(e.key)) {
      if (!done.has(e.key)) {
        out.push(`${pad}${e.key}: ${yamlString(wanted.get(e.key))}${cr}`);
        done.add(e.key);
        lastKeyed = out.length;
      }
      continue;
    }
    if (removes(e.key, e.value)) continue;
    out.push(...lines.slice(e.start, e.end));
    lastKeyed = out.length;
  }
  const added = want.filter(([k]) => !done.has(k)).map(([k, v]) => `${pad}${k}: ${yamlString(v)}${cr}`);
  const rest = lines.slice(cursor, end);
  const merged = [...out.slice(0, lastKeyed), ...added, ...out.slice(lastKeyed), ...rest];
  return [...merged, ...lines.slice(end)].join('\n');
}
