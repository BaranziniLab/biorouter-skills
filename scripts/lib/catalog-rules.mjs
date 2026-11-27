// The BAAM duplicate rules (D1 to D6) and the gap rule (G1).
//
// This module is shared by two checks and must stay free of file system and
// network access: biorouter-skills `scripts/check-catalog.mjs` (skills, their
// bundle components and, when given the extension catalog and jobs.json, the
// cross-kind rules) and the biorouter repository's `landing/scripts/` checks,
// which copy this file verbatim. Every rule takes plain items and returns
// failures; the callers decide where the items come from.
//
// An item is
//   { ref, catalog, kind, id, display_name, status, aliases, job, distinct_from,
//     text, parent, method_skill }
// where `ref` is unique ("skill:<id>", "extension:<id>",
// "component:<bundle>/<folder>", "bundled:<extension>/<skill>"), `catalog` is
// "skills" or "extensions", `kind` is skill | bundle | extension | component |
// bundled-skill, `text` is the list of strings D3 compares, and `parent` is the
// ref of the bundle or extension that holds a component or bundled skill.
//
// A failure is { rule, subject, message, refs }. `rule` and `subject` together
// are the key a `baseline_violations` entry names.
//
// The second half of the file is the provenance and credits contract (format 2
// records, the fixed texts, creditLine and the row rules PV1 to PV6, PV8, PV11,
// PV12 and PV13). It reads rows, never folders: the folder halves of PV7 to
// PV11 and PV13 live in biorouter-skills `scripts/check-catalog.mjs`.

export const RULES_VERSION = 1;

// Calibrated against the baseline catalogs in November 2026 (see
// scripts/calibration.test.mjs in biorouter-skills). Card text is short, so
// token-set Jaccard scores are low: the fifth-highest of the seven known
// look-alike pairs scores 2/17 (0.118), and the plan's starting value of 0.40
// flagged one of them. 0.115 flags five of the seven; the two it misses share a
// job with their partner in the baseline, so D1 catches them. jobs.json freezes
// the same number, and the check fails when the two differ.
export const DEFAULT_SIMILARITY_THRESHOLD = 0.115;

// D5 screens bundle components with the plan's starting value. Component
// descriptions are longer and written from one template, so at 0.115 the
// screen flags several hundred sibling pairs (627 at 0.15 in the baseline);
// at 0.40 it flags the three cross-bundle pairs that are worth a sentence.
export const DEFAULT_COMPONENT_SIMILARITY_THRESHOLD = 0.4;

// Words too common in BAAM card text to tell two items apart. The first eight
// come from the plan; the rest are the words that appear in more than about
// ten percent of baseline items, frozen here so the screen does not drift as
// the catalog grows.
export const DEFAULT_GENERIC_WORDS = Object.freeze([
  'skill', 'agent', 'biorouter', 'analysis', 'workflow', 'data', 'research', 'tool',
  'apache', 'mcp', 'plan', 'planning', 'review', 'style', 'user', 'check', 'access',
  'guarded', 'metadata', 'scientific', 'design', 'model', 'report', 'provenance',
  'structure', 'api', 'adapter', 'file', 'read', 'call', 'run', 'project', 'across',
  'work', 'task', 'ask', 'command', 'request', 'handle', 'system', 'result', 'support',
  'help', 'need', 'want', 'make', 'build', 'create', 'write', 'include', 'provide',
]);

// English stopwords (the common NLTK list plus a few connective words that
// card text uses). Words shorter than three letters are dropped before this.
export const STOPWORDS = Object.freeze(new Set(`
about above after again against all also and any are aren arent because been before being below
between both but can cannot could couldn did didn does doesn doing don down during each either
else etc every few for from further had hadn has hasn have haven having her here hers herself him
himself his how into isn its itself just let like may might mightn more most must mustn myself
needn neither nor not now off once one only onto other ought our ours ourselves out over own per
same shan she should shouldn since some such than that the their theirs them themselves then there
these they this those though through thus too two under until upon very via was wasn were weren
what when where whether which while who whom whose why will with within without won would wouldn
yet you your yours yourself yourselves use used uses using
`.trim().split(/\s+/)));

/** Lowercase, letters and digits only, a trailing "agent" removed (rule D2). */
export function normalizeName(value) {
  const flat = String(value ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
  return flat.length > 5 && flat.endsWith('agent') ? flat.slice(0, -5) : flat;
}

/** Plural folding only; deterministic and documented, so a score can be reproduced by hand. */
export function foldPlural(word) {
  if (word.length > 4 && word.endsWith('ies')) return `${word.slice(0, -3)}y`;
  if (word.length > 4 && /(ss|x|ch|sh)es$/.test(word)) return word.slice(0, -2);
  if (word.length > 3 && word.endsWith('s') && !/(ss|us|is)$/.test(word)) return word.slice(0, -1);
  return word;
}

export function tokenSet(parts, genericWords = DEFAULT_GENERIC_WORDS) {
  const generic = new Set([...genericWords].map(foldPlural));
  const out = new Set();
  for (const part of parts) {
    for (const raw of String(part ?? '').toLowerCase().match(/[a-z]+/g) ?? []) {
      if (raw.length < 3 || STOPWORDS.has(raw)) continue;
      const w = foldPlural(raw);
      if (generic.has(w) || STOPWORDS.has(w)) continue;
      out.add(w);
    }
  }
  return out;
}

export function jaccard(a, b) {
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  const union = a.size + b.size - inter;
  return union === 0 ? 0 : inter / union;
}

const isActive = (item) => item.status === 'active';
const pairKey = (a, b) => [a, b].sort().join('|');

function lists(item, otherId) {
  return (item.distinct_from ?? []).some(
    (d) => d && d.id === otherId && typeof d.boundary === 'string' && d.boundary.trim().length > 0,
  );
}

/** True when either item records a written boundary with the other. */
export function hasBoundary(a, b) {
  return lists(a, b.id) || lists(b, a.id);
}

// ---------------------------------------------------------------------------
// D1, one job, one owner.

export const JOB_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)+$/;

export function ruleD1(items, { builtinJobs = [] } = {}) {
  const failures = [];
  const builtin = new Map(builtinJobs.map((b) => [b.job, b.owner]));
  const byJob = new Map();
  for (const item of items.filter(isActive)) {
    if (!item.job || !JOB_PATTERN.test(item.job)) {
      failures.push({ rule: 'D1', subject: `job-format:${item.ref}`, refs: [item.ref],
        message: `${item.ref} has no job key, or "${item.job}" is not <domain>.<task> in lowercase` });
      continue;
    }
    if (item.kind === 'bundled-skill') {
      if (!item.job.endsWith('.tool-usage')) {
        failures.push({ rule: 'D1', subject: `tool-usage:${item.ref}`, refs: [item.ref],
          message: `${item.ref} is a bundled adapter skill, so its job must end in ".tool-usage" (it is "${item.job}")` });
      }
    }
    if (builtin.has(item.job)) {
      failures.push({ rule: 'D1', subject: `builtin:${item.job}`, refs: [item.ref],
        message: `${item.ref} claims "${item.job}", which Biorouter itself owns (${builtin.get(item.job)})` });
    }
    if (!byJob.has(item.job)) byJob.set(item.job, []);
    byJob.get(item.job).push(item.ref);
  }
  for (const [job, refs] of byJob) {
    if (refs.length > 1) {
      failures.push({ rule: 'D1', subject: `job:${job}`, refs,
        message: `${refs.length} active items share the job "${job}": ${refs.join(', ')}. One of them merges into the other.` });
    }
  }
  return failures;
}

/** Bundled adapter skills must name an active method skill (or null, which warns). */
export function methodSkillWarnings(items) {
  const active = new Set(items.filter((i) => isActive(i) && (i.kind === 'skill' || i.kind === 'bundle')).map((i) => i.id));
  const failures = [];
  const warnings = [];
  for (const item of items.filter((i) => isActive(i) && i.kind === 'bundled-skill')) {
    if (item.method_skill == null) {
      warnings.push(`${item.ref} names no method_skill`);
    } else if (!active.has(item.method_skill)) {
      failures.push({ rule: 'D1', subject: `method-skill:${item.ref}`, refs: [item.ref],
        message: `${item.ref} names method_skill "${item.method_skill}", which is not an active BAAM skill` });
    }
  }
  return { failures, warnings };
}

// ---------------------------------------------------------------------------
// D2, one name.

/**
 * builtins: { skills: [...names], bundles: [...], extensions: [...names or labels] }
 * The namespace holds every row's id (whatever its status, so a retired id is
 * never reused), and for active items their display names and aliases, plus
 * bundled skill names of active extensions and every Biorouter built-in name.
 */
export function ruleD2(items, builtins = {}) {
  const entries = new Map();
  const add = (name, owner, what) => {
    const n = normalizeName(name);
    if (!n) return;
    if (!entries.has(n)) entries.set(n, []);
    entries.get(n).push({ owner, what, raw: name });
  };
  const byRef = new Map(items.map((i) => [i.ref, i]));
  for (const item of items) {
    if (item.kind === 'component') continue; // D5 covers component names.
    if (item.kind === 'bundled-skill') {
      if (isActive(item)) add(item.id, item.ref, 'bundled skill name');
      continue;
    }
    add(item.id, item.ref, 'id');
    if (!isActive(item)) continue;
    add(item.display_name, item.ref, 'display name');
    for (const alias of item.aliases ?? []) add(alias, item.ref, 'alias');
  }
  for (const n of builtins.skills ?? []) add(n, `builtin-skill:${n}`, 'built-in skill');
  for (const n of builtins.bundles ?? []) add(n, `builtin-skill:${n}`, 'built-in skill bundle');
  for (const n of builtins.extensions ?? []) add(n, `builtin-extension:${normalizeName(n)}`, 'built-in extension');

  const failures = [];
  for (const [name, list] of entries) {
    const owners = [...new Set(list.map((e) => e.owner))];
    if (owners.length < 2) continue;
    const ownerItems = owners.map((o) => byRef.get(o)).filter(Boolean);
    const builtinOwners = owners.filter((o) => o.startsWith('builtin-'));
    // A built-in skill and a built-in extension of one name are Biorouter's own business.
    if (ownerItems.length === 0) continue;
    // An extension and the skill it bundles may share a name: they install together.
    if (ownerItems.length === 2 && !builtinOwners.length) {
      const [a, b] = ownerItems;
      if (a.parent === b.ref || b.parent === a.ref) continue;
    }
    // The one exception in the plan: an alias that equals the id of an item
    // superseded by the item carrying the alias.
    const aliasException = (() => {
      if (ownerItems.length !== 2 || builtinOwners.length) return false;
      const [a, b] = ownerItems;
      const check = (carrier, old) =>
        list.some((e) => e.owner === carrier.ref && e.what === 'alias') &&
        list.some((e) => e.owner === old.ref && e.what === 'id') &&
        old.status === `superseded_by:${carrier.id}`;
      return check(a, b) || check(b, a);
    })();
    if (aliasException) continue;
    // A retired or superseded row keeps its id reserved; that id may equal a
    // built-in (the reason develop-biorouter-extension was retired).
    if (ownerItems.length === 1 && !isActive(ownerItems[0]) && builtinOwners.length) continue;
    // An inactive row's display name was never registered, so only ids clash here.
    // Two catalogs: a skill and an extension that share a normalized name may
    // stand together only with a written boundary (see the plan's D2 note).
    if (ownerItems.length === 2 && !builtinOwners.length) {
      const [a, b] = ownerItems;
      if (a.catalog !== b.catalog && isActive(a) && isActive(b) && a.id !== b.id && hasBoundary(a, b)) continue;
    }
    failures.push({ rule: 'D2', subject: `name:${name}`, refs: owners,
      message: `the name "${name}" is used by ${list.map((e) => `${e.owner} (${e.what} "${e.raw}")`).join(', ')}` });
  }
  return failures;
}

// ---------------------------------------------------------------------------
// D3, look-alike screen (and D5's component screen, which uses the same code).

export function lookalikeScores(items, { genericWords = DEFAULT_GENERIC_WORDS } = {}) {
  const active = items.filter(isActive);
  const sets = new Map(active.map((i) => [i.ref, tokenSet(i.text ?? [], genericWords)]));
  const out = [];
  for (let x = 0; x < active.length; x++) {
    for (let y = x + 1; y < active.length; y++) {
      const a = active[x];
      const b = active[y];
      if (a.catalog !== b.catalog || (a.kind === 'component') !== (b.kind === 'component')) continue;
      out.push({ a, b, score: jaccard(sets.get(a.ref), sets.get(b.ref)) });
    }
  }
  return out.sort((p, q) => q.score - p.score || pairKey(p.a.ref, p.b.ref).localeCompare(pairKey(q.a.ref, q.b.ref)));
}

export function ruleD3(items, { threshold = DEFAULT_SIMILARITY_THRESHOLD, genericWords, rule = 'D3' } = {}) {
  return lookalikeScores(items, { genericWords })
    .filter((p) => p.score >= threshold && !hasBoundary(p.a, p.b))
    .map((p) => ({
      rule,
      subject: `pair:${pairKey(p.a.id, p.b.id)}`,
      refs: [p.a.ref, p.b.ref],
      score: p.score,
      message: `${p.a.ref} and ${p.b.ref} look alike (Jaccard ${p.score.toFixed(3)} >= ${threshold}); merge them, or record a distinct_from boundary`,
    }));
}

// ---------------------------------------------------------------------------
// D4, redirects are complete.

export const STATUS_PATTERN = /^(active|retired|superseded_by:(builtin:)?[a-z0-9][a-z0-9-]*(\/[a-z0-9][a-z0-9-]*)?)$/;
// A bundle component may also be "removed" (dropped upstream, nothing replaces it).
export const COMPONENT_STATUS_PATTERN = /^(active|removed|superseded_by:[a-z0-9][a-z0-9-]*(\/[a-z0-9][a-z0-9-]*)?)$/;

export function ruleD4(items, builtins = {}) {
  const failures = [];
  const rows = items.filter((i) => i.kind !== 'component' && i.kind !== 'bundled-skill');
  const byId = new Map(rows.map((i) => [`${i.catalog}:${i.id}`, i]));
  // A component is addressed as <bundle>/<folder> or as <bundle>/<component name>.
  const components = new Map();
  for (const i of items.filter((x) => x.kind === 'component')) {
    components.set(i.id, i);
    if (i.name) components.set(`${i.id.split('/')[0]}/${i.name}`, i);
  }
  const builtinSkills = new Set([...(builtins.skills ?? []), ...(builtins.bundles ?? [])]);
  const builtinExtensions = new Set((builtins.extensions ?? []).map(normalizeName));
  for (const item of items) {
    const pattern = item.kind === 'component' ? COMPONENT_STATUS_PATTERN : STATUS_PATTERN;
    if (!pattern.test(item.status ?? '')) {
      failures.push({ rule: 'D4', subject: `status:${item.ref}`, refs: [item.ref],
        message: `${item.ref} has status "${item.status}", which is not active, retired or superseded_by:<id>` });
      continue;
    }
    if (!item.status.startsWith('superseded_by:')) continue;
    const target = item.status.slice('superseded_by:'.length);
    if (target.startsWith('builtin:')) {
      const name = target.slice('builtin:'.length);
      const ok = item.catalog === 'skills' ? builtinSkills.has(name) : builtinExtensions.has(normalizeName(name));
      if (!ok) {
        failures.push({ rule: 'D4', subject: `target:${item.ref}`, refs: [item.ref],
          message: `${item.ref} is superseded by built-in "${name}", which Biorouter does not ship` });
      }
      continue;
    }
    if (item.kind === 'component') {
      // A removed component points at another component (<bundle>/<folder>) or a whole item.
      const t = target.includes('/') ? components.get(target) : byId.get(`skills:${target}`);
      if (!t || !isActive(t)) {
        failures.push({ rule: 'D4', subject: `target:${item.ref}`, refs: [item.ref],
          message: `${item.ref} is superseded by "${target}", which is not an active component or skill` });
      }
      continue;
    }
    const t = byId.get(`${item.catalog}:${target}`);
    if (!t) {
      failures.push({ rule: 'D4', subject: `target:${item.ref}`, refs: [item.ref],
        message: `${item.ref} is superseded by "${target}", which has no row in the ${item.catalog} catalog` });
      continue;
    }
    if (!isActive(t)) {
      failures.push({ rule: 'D4', subject: `chain:${item.ref}`, refs: [item.ref, t.ref],
        message: `${item.ref} is superseded by ${t.ref}, which is not active (no chains, no cycles)` });
      continue;
    }
    if (!(t.aliases ?? []).includes(item.id)) {
      failures.push({ rule: 'D4', subject: `alias:${item.ref}`, refs: [item.ref, t.ref],
        message: `${t.ref} replaces ${item.ref} but does not list "${item.id}" in aliases` });
    }
  }
  return failures;
}

// ---------------------------------------------------------------------------
// D5, components: unique names across bundles and single skills, and the look-alike screen.

export function ruleD5(items, { threshold = DEFAULT_COMPONENT_SIMILARITY_THRESHOLD, genericWords, builtins = {}, screen = true } = {}) {
  const failures = [];
  const names = new Map();
  const add = (name, owner) => {
    const n = normalizeName(name);
    if (!names.has(n)) names.set(n, new Set());
    names.get(n).add(owner);
  };
  for (const item of items) {
    if (item.catalog !== 'skills' && item.kind !== 'bundled-skill') continue;
    if (!isActive(item)) continue;
    if (item.kind === 'component') add(item.name ?? item.id, item.ref);
    else if (item.kind === 'skill') add(item.id, item.ref);
    else if (item.kind === 'bundled-skill') add(item.id, item.ref);
  }
  for (const n of [...(builtins.skills ?? [])]) add(n, `builtin-skill:${n}`);
  for (const [name, owners] of names) {
    const list = [...owners];
    if (list.length > 1 && list.some((o) => o.startsWith('component:'))) {
      failures.push({ rule: 'D5', subject: `name:${name}`, refs: list,
        message: `the component name "${name}" is also used by ${list.join(', ')}` });
    }
  }
  if (screen) {
    const comps = items.filter((i) => i.kind === 'component');
    failures.push(...ruleD3(comps, { threshold, genericWords, rule: 'D5' }));
  }
  return failures;
}

// ---------------------------------------------------------------------------
// D6, no empty shells.

/** The lines the detector compares: trimmed, non-empty, and not a level-one heading. */
export function shellLines(body) {
  return String(body ?? '')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('# '));
}

/**
 * bodies: [{ ref, id, body }] for every active single skill. A skill fails when
 * more than half of its lines appear in five or more other skills.
 *
 * isTemplate(line), when given, also counts a line as shared. The check passes
 * the template lines frozen from the baseline, because the frequency alone
 * forgets a template once enough of the shells built from it become stubs: a
 * shell must keep failing until it is rebuilt, not pass because its siblings
 * were merged away.
 */
export function ruleD6(bodies, { minOthers = 5, maxShare = 0.5, isTemplate = () => false } = {}) {
  const lines = new Map(bodies.map((b) => [b.ref, shellLines(b.body)]));
  const freq = new Map();
  for (const ls of lines.values()) for (const l of new Set(ls)) freq.set(l, (freq.get(l) ?? 0) + 1);
  const failures = [];
  for (const b of bodies) {
    const ls = lines.get(b.ref);
    if (!ls.length) {
      failures.push({ rule: 'D6', subject: `shell:${b.id}`, refs: [b.ref], share: 1, message: `${b.ref} has an empty body` });
      continue;
    }
    const shared = ls.filter((l) => freq.get(l) >= minOthers + 1 || isTemplate(l)).length;
    const share = shared / ls.length;
    if (share > maxShare) {
      failures.push({ rule: 'D6', subject: `shell:${b.id}`, refs: [b.ref], share,
        message: `${b.ref} is a template shell: ${shared} of its ${ls.length} lines (${Math.round(share * 100)}%) appear in ${minOthers} or more other skills or in the baseline template` });
    }
  }
  return failures;
}

// ---------------------------------------------------------------------------
// G1, every required job has an active owner or a plan.

/** required: [{ job, why, owner, planned }]. Owner is an item id, "<bundle>/<component>" or "<extension>/<bundled skill>". */
export function ruleG1(items, required = []) {
  const failures = [];
  const warnings = [];
  const activeById = new Map();
  for (const i of items.filter(isActive)) {
    const key = i.kind === 'component' || i.kind === 'bundled-skill' ? i.id : i.id;
    activeById.set(key, i);
  }
  const jobOwners = new Map();
  for (const i of items.filter(isActive)) jobOwners.set(i.job, i);
  for (const r of required) {
    if (!r || !JOB_PATTERN.test(r.job ?? '')) {
      failures.push({ rule: 'G1', subject: `format:${r?.job}`, refs: [], message: `required job "${r?.job}" is not a valid job key` });
      continue;
    }
    const owner = r.owner ? activeById.get(r.owner) : null;
    const claimant = jobOwners.get(r.job);
    if (claimant && (!owner || claimant.ref !== owner.ref)) {
      failures.push({ rule: 'G1', subject: `owner:${r.job}`, refs: [claimant.ref],
        message: `${claimant.ref} claims required job "${r.job}", but jobs.json names ${r.owner ?? 'no owner'}` });
      continue;
    }
    if (owner) continue;
    if (r.planned) {
      warnings.push(`required job "${r.job}" has no active owner yet; planned: ${r.planned}${r.owner ? ` (intended owner ${r.owner})` : ''}`);
      continue;
    }
    failures.push({ rule: 'G1', subject: `gap:${r.job}`, refs: [],
      message: `required job "${r.job}" has no active owner and no planned entry` });
  }
  return { failures, warnings };
}

// ---------------------------------------------------------------------------
// Baseline violations: failures that exist today, each owned by a work package.

/**
 * baseline: [{ rule, subject, wp, note }]; done: work package ids marked done.
 * Returns { errors, accepted, stale }: errors are failures with no baseline
 * entry, entries whose work package is done, and entries that no longer fail.
 */
export function applyBaseline(failures, baseline = [], done = []) {
  const doneSet = new Set(done);
  const key = (f) => `${f.rule}::${f.subject}`;
  const byKey = new Map(baseline.map((b) => [key(b), b]));
  const errors = [];
  const accepted = [];
  const seen = new Set();
  for (const f of failures) {
    const b = byKey.get(key(f));
    if (!b) {
      errors.push(f);
      continue;
    }
    seen.add(key(f));
    if (doneSet.has(b.wp)) {
      errors.push({ ...f, message: `${f.message} [baseline entry belongs to ${b.wp}, which is marked done]` });
    } else {
      accepted.push({ ...f, wp: b.wp });
    }
  }
  const stale = baseline
    .filter((b) => !seen.has(key(b)))
    .map((b) => ({ rule: 'baseline', subject: key(b), refs: [],
      message: `baseline_violations lists ${b.rule} ${b.subject} (${b.wp}), which no longer fails; remove the entry` }));
  return { errors: [...errors, ...stale], accepted, stale };
}

// ===========================================================================
// Provenance and credits (format 2).
//
// The owner's rule of 2026-11-27: every skill and extension says what it
// borrowed (text, code, data or ideas), from whom, under which licence, and
// credits the people behind it; an item made entirely in-house says it was made
// by the Baranzini Lab (Wanjun Gu, UCSF); every item says it is curated and
// organized by Wanjun Gu, Baranzini Lab, UCSF.
//
// One row is the source of truth. A row is in format 2 when its catalog says
// "format": 2, or, while the catalog still says 1, when the row's own source
// says "format": 2 (rows move one at a time; the landing mirror requires a
// format 1 catalog until it learns format 2). The row's `source`:
//
//   { format: 2, origin, upstreams: [Upstream], ideas_from: [Idea],
//     data_and_services: [Data], references: [Reference], refused_sources: [Refused],
//     changes, maintained_here, content_moved_to, built_with (extensions) }
//
// and the row's `contributors: [{ name, affiliation, role }]`. Upstream:
//
//   { kind, repo, display, url, path, commit, version, licence, copyright,
//     copyright_note, credit, people, use, what, files, via, upstream_notice,
//     owner, taken }
//
// Idea: { kind, name, url, cite, licence, credit, what, evidence, version_read, applies_to }
// Data: { kind, name, url, terms, credit, cite, how }
// Reference: { name, url, cite, credit }      Refused: { repo, url, path, reason }
//
// A bundle component may add { origin, licence, sources: [index into upstreams],
// ideas_from, references, written_for_biorouter: [{ path, origin, licence,
// what, ideas_from, references }], content_moved_to }. A history entry may add
// { origin, licence }. Retired in format 2: row `notices`, row
// `refused_sources` (moved under source) and `source.inspired_by` (now
// `ideas_from`).
//
// Rule subjects. Every provenance failure's subject is "<kind>:<id>" or
// "<kind>:<id>/<component>", optionally followed by ":<detail>", so
// subjectId() can tell which row a baseline entry names.

export const PROVENANCE_FORMAT = 2;

/** The curator line. On every record, never on a card (owner answer Q1). */
export const CURATED_BY = 'Curated and organized by Wanjun Gu, Baranzini Lab, UCSF.';
/** The card and app line of an in-house item, fixed whoever co-wrote it (owner answer Q2). */
export const MADE_BY_LAB_STEM = 'Made by the Baranzini Lab (Wanjun Gu, UCSF)';
export const MADE_BY_LAB = `${MADE_BY_LAB_STEM}.`;
export const PACKAGED_BY_LAB = 'packaged for Biorouter by the Baranzini Lab';
export const EXTENSION_BY_LAB = 'extension by the Baranzini Lab';
/** The copyright holder for the lab's own work, everywhere (owner answer Q9). */
export const LAB_COPYRIGHT_HOLDER = 'Baranzini Lab, University of California, San Francisco';
export function labCopyrightLine(year) {
  return `Copyright ${year} ${LAB_COPYRIGHT_HOLDER}`;
}
/** A card or app line is at most this long (PV13). */
export const CREDIT_LINE_MAX = 120;

/**
 * Origin question 1 for a skill (owner answer Q10): third-party when at least
 * this share of its source-derived lines is unchanged and Biorouter-written
 * lines are under the second share, by a body diff against the source at its
 * pinned commit (front matter removed, whitespace collapsed). The migration
 * script applies it; a person confirms every row.
 */
export const THIRD_PARTY_MIN_KEPT_SHARE = 0.9;
export const THIRD_PARTY_MAX_WRITTEN_SHARE = 0.1;

export const ORIGINS = Object.freeze(['in-house', 'ideas-derived', 'adapted', 'third-party']);
/** The origins a format 1 skill row records. */
export const FORMAT1_ORIGINS = Object.freeze(['native', 'lab', 'adapted']);

/** How a source is used. */
export const USES = Object.freeze(['text', 'code', 'data', 'bundled', 'bundled-modified', 'dependency', 'launched']);
/** Outside material inside the item that decides its origin (PV2 to PV4). */
export const ORIGIN_COPY_USES = Object.freeze(['text', 'code', 'data', 'bundled-modified']);
/** Material redistributed with the item: licence text, copyright line and a pin are owed (PV6 to PV8). */
export const SHIPPED_USES = Object.freeze(['text', 'code', 'data', 'bundled', 'bundled-modified']);
/** Outside work a third-party item is made of or runs (PV5). */
export const THIRD_PARTY_USES = Object.freeze(['text', 'code', 'data', 'bundled', 'bundled-modified', 'launched']);
/** The program a third-party extension runs, preferred for its card line. */
export const RUN_USES = Object.freeze(['bundled', 'bundled-modified', 'launched']);

export const UPSTREAM_KINDS = Object.freeze(['repository', 'package', 'program']);
export const IDEA_KINDS = Object.freeze(['repository', 'skill', 'paper', 'guideline', 'book']);
export const DATA_KINDS = Object.freeze(['dataset', 'service']);
export const APPLIES_TO = Object.freeze(['current', 'earlier']);
export const OWNERS = Object.freeze(['external', 'lab']);

/** Licences copied material may carry (formerly scripts/check-catalog.mjs:38-40). */
export const ALLOWED_LICENCES = Object.freeze(new Set([
  'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'BlueOak-1.0.0', 'CC0-1.0', 'CC-BY-4.0',
]));
/** The licences whose text a format 1 notice file had to carry (the rule PV7 replaces). */
export const FORMAT1_NOTICE_LICENCES = Object.freeze(new Set(['MIT', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'BlueOak-1.0.0', 'CC-BY-4.0']));

/**
 * PV7: phrases a notice file must hold for each licence, compared case-blind
 * with whitespace collapsed. Apache-2.0's two phrases prove the full text and
 * not only its header; BSD-3-Clause's second phrase is the non-endorsement
 * clause; CC-BY-4.0 needs the licence link (the title, author and statement of
 * changes come from the row). CC0-1.0 owes nothing.
 */
export const LICENCE_FINGERPRINTS = Object.freeze({
  'MIT': ['Permission is hereby granted, free of charge, to any person obtaining a copy'],
  'Apache-2.0': ['TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION', 'END OF TERMS AND CONDITIONS'],
  'BSD-2-Clause': ['Redistribution and use in source and binary forms, with or without modification, are permitted'],
  'BSD-3-Clause': ['Redistribution and use in source and binary forms, with or without modification, are permitted', 'Neither the name of'],
  'ISC': ['for any purpose with or without fee is hereby granted'],
  'BlueOak-1.0.0': ['Blue Oak Model License'],
  'CC-BY-4.0': ['creativecommons.org/licenses/by/4.0'],
  'CC0-1.0': [],
});

/** The heading a notice file writes above an Apache source's NOTICE text (PV7, upstream_notice). */
export function upstreamNoticeMarker(repoOrName) {
  return `NOTICE file of ${repoOrName}`;
}

/** The sentence a full record opens with, by origin (audit table 1.4). */
export const ORIGIN_SENTENCES = Object.freeze({
  'in-house': 'Original work of the Baranzini Lab.',
  'ideas-derived': 'Written by the Baranzini Lab. The sources below shaped its design; none of their text or code is included.',
  'adapted': 'Includes text or code from the sources below, changed for Biorouter. Their licences and copyright lines ship with it.',
  'third-party': 'The sources below, kept largely as published and packaged for Biorouter. Their licences and copyright lines ship with it.',
  'third-party-extension': 'The program below does the work; the Baranzini Lab wrote the extension around it.',
});

/** Text a card's summary or description may never carry (PV13). */
export const CARD_CREDIT_PATTERN = /made by the baranzini lab|adapted from |curated and organi[sz]ed by|packaged for biorouter by/i;

const list = (x) => (Array.isArray(x) ? x : []);
const str = (x) => typeof x === 'string' && x.trim().length > 0;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const COMMIT = /^[0-9a-f]{7,40}$/;
const REPO = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const URL_PATTERN = /^https?:\/\/\S+$/;
const UPSTREAM_PATH = /^([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+):(\S.*)$/;

/** SPDX expression to licence ids (formerly scripts/check-catalog.mjs). */
export function licenceTokens(expr) {
  return String(expr ?? '')
    .replace(/[()]/g, ' ')
    .split(/\s+(?:AND|OR|WITH)\s+|\s+/)
    .filter(Boolean)
    .filter((t) => t !== 'AND' && t !== 'OR');
}

/** 2 when the row is in format 2, else 1. */
export function provenanceFormat(row, catalogFormat = 1) {
  if (catalogFormat === PROVENANCE_FORMAT) return PROVENANCE_FORMAT;
  return row?.source?.format === PROVENANCE_FORMAT ? PROVENANCE_FORMAT : 1;
}

/** "skills" for a skill or bundle row, "extensions" otherwise. */
export function catalogOf(row) {
  return row?.kind === 'skill' || row?.kind === 'bundle' ? 'skills' : 'extensions';
}

const refOf = (row, catalog) => `${catalog === 'extensions' ? 'extension' : 'skill'}:${row.id}`;

export const usesOf = (u) => list(u?.use);
const hasAny = (u, uses) => usesOf(u).some((x) => uses.includes(x));
export const isLabOwned = (u) => u?.owner === 'lab';

/** The key that groups upstream entries of one source (one repository can hold several entries). */
export function sourceKey(u) {
  return u?.repo ?? u?.url ?? u?.display ?? u?.name ?? '';
}

/** The short name a line shows: `display`, else the repository's name, else `name` or the URL. */
export function sourceName(u) {
  if (str(u?.display)) return u.display;
  if (str(u?.name)) return u.name;
  if (str(u?.repo)) return String(u.repo).split('/').pop();
  return u?.url ?? 'an unnamed source';
}

/** Format 2: outside material inside the item that decides its origin. */
export function externalCopying(row) {
  return list(row?.source?.upstreams).filter((u) => !isLabOwned(u) && hasAny(u, ORIGIN_COPY_USES));
}

/** Material redistributed with the item, any owner. Format 1: every upstream (the old notice rule read them all). */
export function shippedSources(row, catalogFormat = 1) {
  const ups = list(row?.source?.upstreams);
  if (provenanceFormat(row, catalogFormat) === 1) return ups;
  return ups.filter((u) => hasAny(u, SHIPPED_USES));
}

/**
 * PV7: the sources whose licence text and copyright line a notice file must
 * carry. Format 1 keeps the old rule (every upstream under an old notice
 * licence) and adds Apache-2.0 upstreams of adapted rows. Format 2 takes every
 * shipped source except CC0-1.0 and lab-owned Apache-2.0 text, which the
 * archive's own LICENSE already covers.
 */
export function noticeSources(row, catalogFormat = 1) {
  const ups = list(row?.source?.upstreams);
  if (provenanceFormat(row, catalogFormat) === 1) {
    return ups.filter((u) => FORMAT1_NOTICE_LICENCES.has(u.licence) || (row.source?.origin === 'adapted' && u.licence === 'Apache-2.0'));
  }
  return shippedSources(row, catalogFormat).filter((u) => {
    const ids = licenceTokens(u.licence);
    if (ids.length && ids.every((t) => t === 'CC0-1.0')) return false;
    return !(isLabOwned(u) && ids.length && ids.every((t) => t === 'Apache-2.0'));
  });
}

/** Licences among `licences` whose fingerprint phrases `text` lacks (PV7). */
export function missingLicenceTexts(text, licences) {
  const flat = String(text ?? '').replace(/\s+/g, ' ').toLowerCase();
  const out = [];
  for (const id of [...new Set(licences)]) {
    const phrases = LICENCE_FINGERPRINTS[id];
    if (!phrases) {
      out.push(id);
      continue;
    }
    if (phrases.some((p) => !flat.includes(p.replace(/\s+/g, ' ').toLowerCase()))) out.push(id);
  }
  return out;
}

/** `copyright` found in `text`, whitespace collapsed (PV7). */
export function containsCopyright(text, copyright) {
  const norm = (s) => String(s ?? '').replace(/\s+/g, ' ').trim();
  return norm(text).includes(norm(copyright));
}

/** The `ideas_from` entries that shape the item as it ships now. */
export function currentIdeas(rowOrComponent) {
  const ideas = rowOrComponent?.source ? rowOrComponent.source.ideas_from : rowOrComponent?.ideas_from;
  return list(ideas).filter((i) => i?.applies_to === 'current');
}

function primarySources(row, catalog) {
  const origin = row?.source?.origin;
  if (origin === 'ideas-derived') return currentIdeas(row);
  const external = list(row?.source?.upstreams).filter((u) => !isLabOwned(u));
  if (origin === 'adapted') return external.filter((u) => hasAny(u, ORIGIN_COPY_USES));
  if (origin === 'third-party') {
    const made = external.filter((u) => hasAny(u, THIRD_PARTY_USES));
    if (catalog !== 'extensions') return made;
    return [...made.filter((u) => hasAny(u, RUN_USES)), ...made.filter((u) => !hasAny(u, RUN_USES))];
  }
  return [];
}

/** Sources grouped by sourceKey, in first-appearance order, with every distinct licence. */
export function groupSources(entries) {
  const groups = new Map();
  for (const u of entries) {
    const key = sourceKey(u);
    if (!groups.has(key)) groups.set(key, { key, name: sourceName(u), credit: u.credit ?? null, version: u.version ?? null, licences: [], entries: [] });
    const g = groups.get(key);
    g.entries.push(u);
    for (const t of licenceTokens(u.licence)) if (!g.licences.includes(t)) g.licences.push(t);
    if (!g.credit && u.credit) g.credit = u.credit;
    if (!g.version && u.version) g.version = u.version;
  }
  return [...groups.values()];
}

const UNRECORDED = 'a source not yet recorded';

/**
 * The one credit line a card, an app row, the README, PROVENANCE.md and the
 * front matter all print (audit table 1.4). At most CREDIT_LINE_MAX characters
 * when the record allows it: the "and N more" tail goes first, and a line that
 * is still too long fails PV13 (shorten the source's `display`).
 */
export function creditLine(row, { catalog = catalogOf(row) } = {}) {
  const origin = row?.source?.origin;
  if (origin === 'in-house') return MADE_BY_LAB;
  const groups = groupSources(primarySources(row, catalog));
  const first = groups[0] ?? null;
  const others = Math.max(0, groups.length - 1);
  const name = first?.name ?? UNRECORDED;
  const credit = first?.credit || 'an uncredited author';
  const lic = first?.licences.length ? first.licences.join(', ') : 'licence not recorded';
  const build = (withMore) => {
    const more = withMore && others > 0 ? ` and ${others} more` : '';
    if (origin === 'ideas-derived') {
      const by = first && first.credit && first.credit !== first.name ? ` (${first.credit})` : '';
      return `${MADE_BY_LAB_STEM}, with ideas from ${name}${by}${more}.`;
    }
    if (!first) {
      if (origin === 'adapted') return `Adapted from ${UNRECORDED}.`;
      if (origin === 'third-party') return catalog === 'extensions' ? `Runs ${UNRECORDED}; ${EXTENSION_BY_LAB}.` : `From ${UNRECORDED}, ${PACKAGED_BY_LAB}.`;
      return `Provenance not recorded (origin "${origin}").`;
    }
    if (origin === 'adapted') return `Adapted from ${name} by ${credit} (${lic})${more}.`;
    if (origin === 'third-party' && catalog === 'extensions') {
      const ver = first.version ? ` ${first.version}` : '';
      return `Runs ${name}${ver} by ${credit} (${lic})${more}; ${EXTENSION_BY_LAB}.`;
    }
    if (origin === 'third-party') return `From ${name} by ${credit} (${lic})${more}, ${PACKAGED_BY_LAB}.`;
    return `Provenance not recorded (origin "${origin}").`;
  };
  const long = build(true);
  return long.length > CREDIT_LINE_MAX ? build(false) : long;
}

/** The origin sentence a full record opens with. */
export function originSentence(row, { catalog = catalogOf(row) } = {}) {
  const origin = row?.source?.origin;
  if (origin === 'third-party' && catalog === 'extensions') return ORIGIN_SENTENCES['third-party-extension'];
  return ORIGIN_SENTENCES[origin] ?? `Provenance not recorded (origin "${origin}").`;
}

/** A bundle component's view of its row: its own origin, sources and ideas when it declares an origin. */
export function componentRecord(row, folder) {
  const comp = row?.components?.[folder];
  if (!comp || !comp.origin) return row;
  const ups = list(row.source?.upstreams);
  const own = Array.isArray(comp.sources)
    ? comp.sources.map((i) => ups[i]).filter(Boolean)
    : comp.origin === 'in-house' || comp.origin === 'ideas-derived' ? [] : ups;
  return { ...row, source: { ...row.source, origin: comp.origin, upstreams: own, ideas_from: list(comp.ideas_from) } };
}

/** The credit line of one component (its row's line unless the component declares its own origin). */
export function componentCreditLine(row, folder, opts = {}) {
  return creditLine(componentRecord(row, folder), opts);
}

/** The component folder a SKILL.md belongs to ("<folder>/..." of a bundle), or null. */
export function componentOfFile(row, rel) {
  const first = String(rel ?? '').split('/')[0];
  return row?.kind === 'bundle' && row.components && Object.hasOwn(row.components, first) && String(rel).includes('/') ? first : null;
}

/** PV10: the generated front matter values of one SKILL.md of a row. */
export function frontmatterCredits(row, rel = 'SKILL.md') {
  const folder = componentOfFile(row, rel);
  const origin = (folder && row.components[folder].origin) || row?.source?.origin;
  return { origin, credit: folder ? componentCreditLine(row, folder) : creditLine(row), curated_by: CURATED_BY };
}

function describeTarget(target, rows) {
  if (target == null) return null;
  if (String(target).startsWith('builtin:')) return `Biorouter's built-in ${String(target).slice('builtin:'.length)} skill`;
  if (String(target).includes('/')) return String(target);
  const t = list(rows).find((r) => r.id === target);
  return t ? `${t.display_name} (${target})` : String(target);
}

/** The lines a merged or retired item's stub carries in format 2: the last real content's credit, and the curator line. */
export function stubCreditLines(row, rows = []) {
  const target = describeTarget(row?.source?.content_moved_to ?? null, rows);
  const where = target ? `Its content now lives in ${target}.` : 'Its content was not carried forward.';
  return [`Earlier versions: ${creditLine(row)} ${where}`, CURATED_BY];
}

/** The row id a provenance subject names ("<kind>:<id>[/<component>][:<detail>]"), or null. */
export function subjectId(subject) {
  const m = /^[^:]+:([a-z0-9]+(?:-[a-z0-9]+)*)(?=$|[:/])/.exec(String(subject ?? ''));
  return m ? m[1] : null;
}

/**
 * A row whose generated folder files (PROVENANCE.md, front matter, the stub's
 * credit, the archive's LICENSE) wait for its next release: its PV9 failure is
 * in the provenance baseline (owner answer Q5). `baseline` is the parsed
 * provenance baseline file (or anything with `baseline_violations`).
 */
export function folderFilesDeferred(baseline, id) {
  return list(baseline?.baseline_violations).some((b) => b?.rule === 'PV9' && b.subject === `folder:${id}`);
}

/** True when the generators write, and the checks expect, a row's provenance folder files now. */
export function folderProvenanceWanted(row, { catalogFormat = 1, baseline = null } = {}) {
  return provenanceFormat(row, catalogFormat) === PROVENANCE_FORMAT && !folderFilesDeferred(baseline, row.id);
}

/**
 * PV13, fixed texts in a hand-written or generated file: a curator line, a
 * "Made by the Baranzini Lab" line or a copyright line for the lab that differs
 * from its constant. `allowed` holds verbatim upstream copyright lines, which
 * keep the wording their source publishes. Returns [{ line, text, expected }].
 */
export function fixedTextProblems(text, { allowed = [] } = {}) {
  const norm = (s) => String(s ?? '').replace(/\s+/g, ' ').trim();
  const ok = list(allowed).filter(str).map(norm);
  const out = [];
  String(text ?? '').split('\n').forEach((raw, i) => {
    const line = norm(raw);
    if (/curated and organi[sz]ed by/i.test(line) && !line.includes(CURATED_BY)) out.push({ line: i + 1, text: line, expected: CURATED_BY });
    if (/made by the baranzini lab/i.test(line) && !line.includes(MADE_BY_LAB_STEM)) out.push({ line: i + 1, text: line, expected: MADE_BY_LAB_STEM });
    if (/^\W*copyright\b/i.test(line) && /regents of the university of california|baranzini|wanjun gu/i.test(line) &&
        !line.includes(LAB_COPYRIGHT_HOLDER) && !ok.some((a) => line.includes(a))) {
      out.push({ line: i + 1, text: line, expected: labCopyrightLine('<year>') });
    }
  });
  return out;
}

// ---------------------------------------------------------------------------
// The row rules.

function checkSource(u, ctx) {
  const p = [];
  const shipped = hasAny(u, SHIPPED_USES);
  if (!str(u?.repo) && !str(u?.url)) p.push('no repo or url');
  if (str(u?.repo) && !REPO.test(u.repo)) p.push(`repo "${u.repo}" is not <owner>/<name>`);
  if (u?.url != null && !URL_PATTERN.test(String(u.url))) p.push(`url "${u.url}" is not an http(s) URL`);
  if (!UPSTREAM_KINDS.includes(u?.kind)) p.push(`kind "${u?.kind}" is not ${UPSTREAM_KINDS.join(', ')}`);
  if (!OWNERS.includes(u?.owner)) p.push(`owner "${u?.owner}" is not external or lab`);
  if (!usesOf(u).length || usesOf(u).some((x) => !USES.includes(x))) p.push(`use must be a non-empty list of ${USES.join(', ')}`);
  if (!str(u?.credit)) p.push('no credit');
  if (!str(u?.what)) p.push('no what');
  if (!str(u?.licence)) p.push('no licence');
  if (u?.people != null && (!Array.isArray(u.people) || u.people.some((x) => !str(x)))) p.push('people must be a list of names');
  if (u?.files != null && (!Array.isArray(u.files) || u.files.some((x) => !str(x)))) p.push('files must be a list of paths');
  if (u?.taken != null && !DATE.test(String(u.taken))) p.push(`taken "${u.taken}" is not YYYY-MM-DD`);
  if (u?.commit != null && !COMMIT.test(String(u.commit))) p.push(`commit "${u.commit}" is not a hex sha`);
  if (u?.via != null && !list(ctx.upstreams).some((o) => o !== u && o.repo === u.via)) p.push(`via "${u.via}" names no other upstream of the row`);
  if (u?.upstream_notice != null && typeof u.upstream_notice !== 'boolean') p.push('upstream_notice must be true or false');
  if (u?.upstream_notice === true && !licenceTokens(u.licence).includes('Apache-2.0')) p.push('upstream_notice is set on a source that is not Apache-2.0');
  if (shipped) {
    if (!(u?.commit && COMMIT.test(String(u.commit))) && !str(u?.version)) p.push('a copied or bundled source needs a commit or a version');
    for (const t of licenceTokens(u?.licence)) if (!ALLOWED_LICENCES.has(t)) p.push(`licence ${t} may not be copied or bundled`);
    if (u?.copyright == null && !str(u?.copyright_note)) p.push('copyright is null with no copyright_note');
    if (u?.copyright != null && !str(u.copyright)) p.push('copyright is empty; write null and a copyright_note');
  }
  return p;
}

function checkIdea(i) {
  const p = [];
  if (!str(i?.name)) p.push('no name');
  if (!IDEA_KINDS.includes(i?.kind)) p.push(`kind "${i?.kind}" is not ${IDEA_KINDS.join(', ')}`);
  if (!str(i?.url) && !str(i?.cite)) p.push('no url or cite');
  if (i?.url != null && !URL_PATTERN.test(String(i.url))) p.push(`url "${i.url}" is not an http(s) URL`);
  if (!str(i?.credit)) p.push('no credit');
  if (!str(i?.what)) p.push('no what');
  if (!str(i?.evidence)) p.push('no evidence (how "no text" was established)');
  if (!APPLIES_TO.includes(i?.applies_to)) p.push(`applies_to "${i?.applies_to}" is not current or earlier`);
  return p;
}

/**
 * The provenance row rules over one catalog's rows. Returns { failures,
 * warnings }. Format 1 rows get PV1 "format:<id>" and nothing else (PV7, a
 * folder rule, also reads format 1 rows). `rows` is the whole catalog's items,
 * so a merged component can find its host in another bundle.
 */
export function ruleProvenance(rows, { catalogFormat = 1, catalog = null } = {}) {
  const failures = [];
  const warnings = [];
  const all = list(rows);
  const byId = new Map(all.map((r) => [r.id, r]));
  for (const row of all) {
    const kind = catalog ?? catalogOf(row);
    const ref = refOf(row, kind);
    const id = row.id;
    const fail = (rule, subject, message) => failures.push({ rule, subject, message: `${id}: ${message}`, refs: [ref] });
    const warn = (message) => warnings.push(`${id}: ${message}`);
    const src = row.source ?? {};
    const active = row.status === 'active';

    // PV1, the record and its origin.
    if (provenanceFormat(row, catalogFormat) === 1) {
      fail('PV1', `format:${id}`, `records its provenance in format 1 (origin "${src.origin}"); write it in format 2 (source.format 2, one of ${ORIGINS.join(', ')}, contributors)`);
      continue;
    }
    if (!ORIGINS.includes(src.origin)) fail('PV1', `origin:${id}`, `source.origin "${src.origin}" is not ${ORIGINS.join(', ')}`);
    if (catalogFormat !== PROVENANCE_FORMAT && src.format !== PROVENANCE_FORMAT) fail('PV1', `origin:${id}`, 'source.format must be 2');
    if (row.notices !== undefined) fail('PV1', `field:${id}:notices`, '`notices` is retired in format 2; the NOTICE is generated');
    if (row.refused_sources !== undefined) fail('PV1', `field:${id}:refused_sources`, '`refused_sources` moves under source in format 2');
    if (src.inspired_by !== undefined) fail('PV1', `field:${id}:inspired_by`, '`source.inspired_by` is retired in format 2; write ideas_from');
    for (const key of ['upstreams', 'ideas_from', 'data_and_services']) if (!Array.isArray(src[key])) fail('PV1', `field:${id}:${key}`, `source.${key} must be a list`);
    for (const key of ['references', 'refused_sources']) if (src[key] !== undefined && !Array.isArray(src[key])) fail('PV1', `field:${id}:${key}`, `source.${key} must be a list when present`);
    if (src.changes !== undefined && src.changes !== null && typeof src.changes !== 'string') fail('PV1', `field:${id}:changes`, 'source.changes must be text or null');
    for (const h of list(row.history)) {
      if (h.origin !== undefined && !ORIGINS.includes(h.origin)) fail('PV1', `history:${id}`, `history ${h.version} has origin "${h.origin}"`);
      if (h.licence !== undefined && (!str(h.licence) || licenceTokens(h.licence).some((t) => !ALLOWED_LICENCES.has(t)))) fail('PV1', `history:${id}`, `history ${h.version} has licence "${h.licence}"`);
    }
    if (!active) {
      if (!Object.hasOwn(src, 'content_moved_to')) fail('PV1', `moved:${id}`, `is ${row.status} but source.content_moved_to is missing (an item id, builtin:<name>, a <bundle>/<folder> path, or null)`);
      else if (String(row.status).startsWith('superseded_by:')) {
        const target = String(row.status).slice('superseded_by:'.length);
        const to = src.content_moved_to;
        if (typeof to !== 'string' || (to !== target && !to.startsWith(`${target}/`))) fail('PV1', `moved:${id}`, `content_moved_to "${to}" is not "${target}" or a path inside it`);
      }
    } else if (src.content_moved_to != null) fail('PV1', `moved:${id}`, 'an active row has content_moved_to');
    if (!ORIGINS.includes(src.origin)) continue;

    // PV2 to PV5, the origin agrees with the sources.
    const copying = externalCopying(row);
    const ideas = currentIdeas(row);
    const names = (us) => [...new Set(us.map(sourceKey))].join(', ');
    if (src.origin === 'in-house' && (copying.length || ideas.length)) {
      fail('PV2', `in-house:${id}`, `is in-house but ${[copying.length ? `copies from ${names(copying)}` : '', ideas.length ? `takes current ideas from ${ideas.map((i) => i.name).join(', ')}` : ''].filter(Boolean).join(' and ')}`);
    }
    if (src.origin === 'ideas-derived' && (!ideas.length || copying.length)) {
      fail('PV3', `ideas-derived:${id}`, `is ideas-derived but ${!ideas.length ? 'has no ideas_from entry that applies to the current version' : `copies from ${names(copying)}`}`);
    }
    if (src.origin === 'adapted' && (!copying.length || !str(src.changes))) {
      fail('PV4', `adapted:${id}`, `is adapted but ${!copying.length ? 'names no outside source it copies text, code or data from' : 'says nothing in source.changes'}`);
    }
    if (src.origin === 'third-party') {
      const made = list(src.upstreams).filter((u) => !isLabOwned(u) && hasAny(u, THIRD_PARTY_USES));
      if (!made.length || !str(src.changes)) fail('PV5', `third-party:${id}`, `is third-party but ${!made.length ? 'names no outside source it copies, bundles or launches' : 'says nothing in source.changes (write "packaging only" if that is all)'}`);
    }

    // PV6, every source is complete.
    const upstreams = list(src.upstreams);
    upstreams.forEach((u, i) => {
      const p = checkSource(u, { upstreams });
      if (p.length) fail('PV6', `source:${id}:${sourceKey(u) || `#${i}`}`, `upstream ${sourceKey(u) || `#${i}`}: ${p.join('; ')}`);
      if (hasAny(u, SHIPPED_USES) && u?.copyright == null && str(u?.copyright_note)) warn(`upstream ${sourceKey(u)} names no copyright holder (${u.copyright_note}); listed for review`);
      if (str(u?.path) && /[\s(),;]/.test(u.path)) warn(`upstream ${sourceKey(u)} path "${u.path}" reads as prose; put it in what`);
    });
    const ideaLists = [[`${id}`, list(src.ideas_from)]];
    for (const [folder, comp] of Object.entries(row.components ?? {})) {
      ideaLists.push([`${id}/${folder}`, list(comp?.ideas_from)]);
      for (const w of list(comp?.written_for_biorouter)) ideaLists.push([`${id}/${folder}`, list(w?.ideas_from)]);
    }
    for (const [where, ideasHere] of ideaLists) {
      ideasHere.forEach((i, n) => {
        const p = checkIdea(i);
        if (p.length) fail('PV6', `idea:${where}:${i?.name ?? `#${n}`}`, `idea ${i?.name ?? `#${n}`}: ${p.join('; ')}`);
      });
    }
    list(src.data_and_services).forEach((d, n) => {
      const p = [];
      if (!str(d?.name)) p.push('no name');
      if (!DATA_KINDS.includes(d?.kind)) p.push(`kind "${d?.kind}" is not ${DATA_KINDS.join(', ')}`);
      if (!str(d?.url) || !URL_PATTERN.test(d.url)) p.push('no http(s) url');
      if (!str(d?.credit)) p.push('no credit');
      if (p.length) fail('PV6', `data:${id}:${d?.name ?? `#${n}`}`, `data or service ${d?.name ?? `#${n}`}: ${p.join('; ')}`);
      else if (!str(d?.terms)) warn(`data or service ${d.name} states no terms`);
    });
    list(src.references).forEach((r, n) => {
      if (!str(r?.name) || (!str(r?.url) && !str(r?.cite))) fail('PV6', `reference:${id}:${r?.name ?? `#${n}`}`, `reference ${r?.name ?? `#${n}`} needs a name and a url or cite`);
    });
    list(src.refused_sources).forEach((r, n) => {
      if ((!str(r?.repo) && !str(r?.url)) || !str(r?.reason)) fail('PV6', `refused:${id}:${r?.repo ?? r?.url ?? `#${n}`}`, `refused source ${r?.repo ?? r?.url ?? `#${n}`} needs a repo or url and a reason`);
    });

    // PV8, the row licence names what ships.
    if (active) {
      const tokens = new Set(licenceTokens(row.licence));
      const missing = new Set();
      for (const u of shippedSources(row, catalogFormat)) for (const t of licenceTokens(u.licence)) if (!tokens.has(t)) missing.add(t);
      if (['in-house', 'ideas-derived', 'adapted'].includes(src.origin) && !tokens.has('Apache-2.0')) missing.add('Apache-2.0 (the lab\'s own text)');
      if (missing.size) fail('PV8', `licence:${id}`, `licence "${row.licence}" does not name ${[...missing].join(', ')}`);
      for (const [folder, comp] of Object.entries(row.components ?? {})) {
        const own = comp?.origin === 'in-house' || comp?.origin === 'ideas-derived';
        const p = [];
        if (comp?.licence != null) {
          const ct = licenceTokens(comp.licence);
          if (!ct.length || ct.some((t) => !ALLOWED_LICENCES.has(t))) p.push(`licence "${comp.licence}" is not allowed`);
          if (comp.status === 'active') for (const t of ct) if (!tokens.has(t)) p.push(`the row licence does not name its ${t}`);
        }
        if (own && comp?.licence !== 'Apache-2.0') p.push(`is written for Biorouter (${comp.origin}), so its licence is Apache-2.0, not "${comp?.licence ?? '(none)'}"`);
        for (const w of list(comp?.written_for_biorouter)) if (w?.licence !== 'Apache-2.0') p.push(`written file ${w?.path} must be Apache-2.0`);
        if (p.length) fail('PV8', `component-licence:${id}/${folder}`, `component ${folder}: ${p.join('; ')}`);
      }
    }

    // PV11, components carry their own lineage.
    if (row.kind === 'bundle' && row.components) {
      const repos = upstreams.map((u) => u.repo).filter(Boolean);
      for (const [folder, comp] of Object.entries(row.components)) {
        const p = [];
        if (comp?.origin !== undefined && !ORIGINS.includes(comp.origin)) p.push(`origin "${comp.origin}" is not ${ORIGINS.join(', ')}`);
        if (comp?.upstream_path == null) {
          if (src.origin !== 'in-house' && !comp?.origin) p.push('has no upstream_path and declares no origin');
        } else {
          const m = UPSTREAM_PATH.exec(String(comp.upstream_path));
          if (!m) p.push(`upstream_path "${comp.upstream_path}" is not <owner>/<repo>:<path>`);
          else if (!repos.includes(m[1])) p.push(`upstream_path names ${m[1]}, which is not an upstream of the row`);
          else if (Array.isArray(comp.sources) && !comp.sources.some((n) => upstreams[n]?.repo === m[1])) p.push(`upstream_path names ${m[1]}, which its sources do not`);
        }
        if (comp?.sources !== undefined && (!Array.isArray(comp.sources) || comp.sources.some((n) => !Number.isInteger(n) || !upstreams[n]))) p.push('sources must be indexes into the row\'s upstreams');
        if (p.length) fail('PV11', `component:${id}/${folder}`, `component ${folder}: ${p.join('; ')}`);

        // A merged component written for Biorouter is listed by its host.
        const moved = comp?.content_moved_to;
        if (String(comp?.status ?? '').startsWith('superseded_by:') && (comp?.origin === 'in-house' || comp?.origin === 'ideas-derived')) {
          const target = String(comp.status).slice('superseded_by:'.length);
          const parts = typeof moved === 'string' ? moved.split('/') : [];
          let problem = null;
          if (parts.length < 3) problem = `content_moved_to "${moved}" is not <bundle>/<folder>/<file>`;
          else if (!target.includes('/') || !moved.startsWith(`${target}/`)) problem = `content_moved_to "${moved}" is not inside ${target}`;
          else {
            const [hostBundle, hostFolder, ...rest] = parts;
            const host = byId.get(hostBundle)?.components?.[hostFolder];
            if (!host) problem = `host ${hostBundle}/${hostFolder} has no catalog entry`;
            else if (!list(host.written_for_biorouter).some((w) => w?.path === rest.join('/'))) problem = `${hostBundle}/${hostFolder} does not list ${rest.join('/')} under written_for_biorouter`;
          }
          if (problem) fail('PV11', `written:${id}/${folder}`, `merged component ${folder}: ${problem}`);
        }
      }
    }

    // PV12, the people behind the Biorouter side.
    const people = list(row.contributors);
    const badPeople = people.filter((c) => !str(c?.name) || !str(c?.role));
    if (!Array.isArray(row.contributors) || !people.length || badPeople.length) {
      fail('PV12', `contributors:${id}`, !people.length ? 'names no contributor' : `${badPeople.length} contributor(s) lack a name or a role`);
    }
    const accounts = new Set();
    for (const u of upstreams) if (str(u?.repo)) accounts.add(u.repo.split('/')[0].toLowerCase());
    for (const i of list(src.ideas_from)) {
      const m = /^https?:\/\/github\.com\/([^/]+)/.exec(i?.url ?? '');
      if (m) accounts.add(m[1].toLowerCase());
    }
    const named = [
      ...upstreams.flatMap((u) => [u?.credit, ...list(u?.people)]),
      ...list(src.ideas_from).map((i) => i?.credit),
      ...people.map((c) => c?.name),
    ].filter(str);
    for (const n of [...new Set(named)]) if (accounts.has(n.toLowerCase())) warn(`"${n}" is an account name; credit the name the source publishes, if it publishes one`);

    // PV13, the generated line fits, and card text carries no credit.
    const line = creditLine(row, { catalog: kind });
    if (line.length > CREDIT_LINE_MAX) fail('PV13', `line:${id}`, `credit line is ${line.length} characters (at most ${CREDIT_LINE_MAX}): "${line}"`);
    if (active) {
      const texts = [row.summary, row.card?.description].filter(str);
      const hit = texts.find((t) => CARD_CREDIT_PATTERN.test(t) || fixedTextProblems(t).length);
      if (hit) fail('PV13', `card-credit:${id}`, 'card text carries credit; the credit line is generated, so take it out of summary and card.description');
    }
  }
  return { failures, warnings };
}
