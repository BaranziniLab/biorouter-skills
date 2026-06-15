---
name: develop-biorouter-extension
description: Guide for building a BioRouter extension (.brxt file) — covers required structure, manifest schema, Python MCP server setup, and optional bundled skills.
user-invocable: true
---

# Developing a BioRouter Extension (.brxt)

A `.brxt` file is a standard ZIP archive renamed with the `.brxt` extension. BioRouter validates and installs it by unzipping it to `~/.config/biorouter/extensions/<name>/` and running `uv sync` to build the Python virtual environment.

## Required ZIP Contents

```
my-extension.brxt (ZIP archive)
├── manifest.json       ← BioRouter metadata (required)
├── README.md           ← Extension documentation (required)
├── pyproject.toml      ← Python project config (required)
└── src/                ← Python source directory (required)
    └── __init__.py
```

Validation fails if any of the four required entries are missing.

## manifest.json Schema

```json
{
  "name": "myextension",
  "display_name": "My Extension",
  "description": "What this extension does.",
  "version": "1.0.0",
  "entry_point": "myextension",
  "repository": "https://github.com/you/myextension",
  "env_vars": [
    {
      "key": "MY_API_KEY",
      "required": true,
      "auto_propagate": false,
      "description": "API key for the external service.",
      "secret": true,
      "default": ""
    }
  ]
}
```

**Required fields:** `name`, `display_name`, `description`, `version`, `entry_point`, `repository`, `env_vars`

**`env_vars` field reference:**

| Field | Type | Purpose |
|---|---|---|
| `key` | string | Environment variable name |
| `required` | bool | Whether BioRouter blocks startup if missing |
| `auto_propagate` | bool | Whether to pass the var through automatically |
| `description` | string | Shown to the user in the UI |
| `secret` | bool | Masks the value in the UI |
| `default` | string | Optional fallback value |

## Python Package (pyproject.toml + src/)

The extension is a Python package that implements an MCP server. Use `uv` for dependency management — BioRouter runs `uv sync` on install.

Minimal `pyproject.toml`:

```toml
[project]
name = "myextension"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
  "mcp>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The `entry_point` field in `manifest.json` must match the Python module name (the package importable as `python -m <entry_point>`).

## Cross-Platform Dependencies (avoid source builds)

`uv sync` runs on the **end user's machine** at install time. Every dependency
(direct *and* transitive) must therefore either ship a prebuilt wheel for the
user's OS + CPU + Python, or be compilable there. When no wheel matches, uv
falls back to building from source — which silently requires a C and/or Rust
toolchain the user may not have, turning "install an extension" into a compiler
error. This is the single most common cause of install failures.

**Real example:** `cryptography` ≥ 49 (2026-06-12) removed x86_64 (Intel) macOS
wheels. Any extension that pulls it in — e.g. transitively via
`fastmcp → fastmcp-slim[server] → joserfc → cryptography` — forces Intel-Mac
users into a from-source Rust build that fails on most machines.

**Mitigation — cap the dependency only where wheels are missing.** Use a uv
constraint with an environment marker so other platforms keep the newest
version. This works even for *transitive* deps (a constraint narrows a version
that's already in the tree; it does not add a new dependency):

```toml
[tool.uv]
# cryptography >=49 dropped x86_64 macOS wheels (2026-06-12), forcing a
# from-source Rust build on Intel Macs. Cap it to <49 there so Intel users get
# a prebuilt wheel; arm64/Linux/Windows are unaffected.
constraint-dependencies = [
    "cryptography<49; sys_platform == 'darwin' and platform_machine == 'x86_64'",
]
```

**Verify resolution per platform** before you publish — `uv pip compile`
resolves for a target without installing:

```bash
uv pip compile pyproject.toml --python-platform x86_64-apple-darwin  | grep -i cryptography   # Intel mac → must be <49
uv pip compile pyproject.toml --python-platform aarch64-apple-darwin | grep -i cryptography   # Apple silicon
uv pip compile pyproject.toml --python-platform x86_64-unknown-linux-gnu | grep -i cryptography
```

Guidelines:
- Prefer dependency versions that ship wheels for **every** platform you
  support. Check a package's "Download files" page on PyPI for the wheel tags.
- Commit a `uv.lock` for reproducible installs. After adding a constraint, run
  `uv lock` and `uv lock --check`. The lock is what `uv sync` consumes, so an
  invalid lock breaks installs outright — always validate it.
- Pure-Python packages (no compiled extension) are always safe. The risk is
  packages with native code: `cryptography`, `pymssql`, `pydantic-core`,
  anything built with maturin/setuptools-rust/cffi.

## Optional: Bundled Skills

Skills can be shipped inside the `.brxt` and are installed atomically alongside the extension:

```
skills/
  my-skill-slug/
    SKILL.md
  another-skill/
    SKILL.md
    supporting-file.md
```

Each `SKILL.md` must begin with valid YAML frontmatter:

```markdown
---
name: My Skill Name
description: One-line description of what this skill does.
---

Skill body in markdown...
```

Skills install to `~/.config/biorouter/extensions/<name>/skills/<slug>/SKILL.md` and are auto-discovered by the agent on startup.

## Building the .brxt File

```bash
# Create the ZIP and rename to .brxt
cd my-extension-dir
zip -r ../myextension.brxt manifest.json README.md pyproject.toml src/ skills/
```

Or using Python:

```python
import zipfile, pathlib

with zipfile.ZipFile("myextension.brxt", "w", zipfile.ZIP_DEFLATED) as zf:
    for path in pathlib.Path(".").rglob("*"):
        if path.is_file() and ".venv" not in path.parts:
            zf.write(path)
```

Exclude `.venv/`, `__pycache__/`, and any build artifacts.

## Installation & Uninstallation

BioRouter installs by:
1. Unzipping all contents to `~/.config/biorouter/extensions/<name>/`
2. Running `uv sync` (timeout: 10 minutes — generous so a legitimate
   from-source build of a dependency has time to finish) to build the virtual
   environment. If `uv sync` fails, BioRouter surfaces uv's output along with a
   hint for common causes (missing/broken Rust toolchain, no wheel for the
   platform).

Uninstallation removes the entire `~/.config/biorouter/extensions/<name>/` directory, including any bundled skills.

## Validation Checklist

Before distributing a `.brxt`, verify:

```
[ ] ZIP contains manifest.json at root
[ ] ZIP contains README.md at root
[ ] ZIP contains pyproject.toml at root
[ ] ZIP contains src/ directory
[ ] manifest.json has all required fields
[ ] env_vars is a JSON array (even if empty: [])
[ ] Each SKILL.md has --- frontmatter with name and description
[ ] .venv/ and __pycache__/ are excluded from the ZIP
[ ] uv sync completes cleanly from the unzipped directory
[ ] Every dependency has a wheel for each target platform, OR a marker-scoped
    constraint caps it to a version that does (verify with `uv pip compile
    --python-platform ...`, including x86_64-apple-darwin for Intel Macs)
[ ] If a uv.lock is committed, `uv lock --check` passes
```
