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
