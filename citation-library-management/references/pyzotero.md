<!-- Adapted for Biorouter from K-Dense-AI/scientific-agent-skills, skills/pyzotero/SKILL.md at commit ec59a29a03d5 (upstream skill version 1.4, last reviewed upstream 2026-09-30).
     Licence: MIT; see LICENSE-UPSTREAM at the skill root. Changes: upstream
     frontmatter replaced by this note; sections removed: Citing Scientific Agent Skills; relative paths
     rewritten to start at the skill root. -->

> Upstream: K-Dense-AI/scientific-agent-skills (`skills/pyzotero`), MIT. Paths in this guide are relative to the skill folder.
> Requirements stated upstream: Requires Python 3.10+ and pyzotero 1.15.2. Remote access needs network access; private reads and writes need a Zotero API key. Local reads require Zotero 7+ with local API enabled; local writes require Zotero 10+ and separate local authorization.

# Pyzotero

Pyzotero is a Python wrapper for the [Zotero API v3](https://www.zotero.org/support/dev/web_api/v3/start). Use it to programmatically manage Zotero libraries: read items and collections, create and update references, upload attachments, manage tags, and export citations.

**Reviewed target:** [pyzotero 1.15.2](https://pypi.org/project/pyzotero/1.15.2/) on 2026-09-30. Checked official [SDK documentation](https://pyzotero.readthedocs.io/en/latest/), release source, and [Web API contracts](https://www.zotero.org/support/dev/web_api/v3/basics). Examples requiring a private library or running Zotero are illustrative; read-only public probes and isolated SDK contract checks do not establish authenticated write success.

## Authentication Setup

**For remote private reads and writes**, get credentials from https://www.zotero.org/settings/keys:
- **User ID**: shown as "Your userID for use in API calls"
- **API Key**: create at https://www.zotero.org/settings/keys/new
- **Library ID**: for group libraries, the integer after `/groups/` in the group URL

Store credentials in environment variables or a `.env` file:
```
ZOTERO_LIBRARY_ID=your_user_id
ZOTERO_API_KEY=your_api_key
ZOTERO_LIBRARY_TYPE=user  # or "group"
```

See [references/pyzotero/references/authentication.md](references/pyzotero/references/authentication.md) for full setup details.

## Installation

```bash
uv add "pyzotero==1.15.2"    # Reviewed Web API client
uv add "pyzotero[cli]==1.15.2"  # + local CLI
uv add "pyzotero[mcp]==1.15.2"  # + MCP server
```

## Quick Start

```python
import os
from pyzotero import Zotero

zot = Zotero(
    library_id=os.environ['ZOTERO_LIBRARY_ID'],
    library_type=os.environ.get('ZOTERO_LIBRARY_TYPE', 'user'),
    api_key=os.environ['ZOTERO_API_KEY'],
)

# Retrieve top-level items (returns 100 by default)
items = zot.top(limit=10)
for item in items:
    print(item['data'].get('title', ''), item['data']['itemType'])

# Search by keyword
results = zot.items(q='machine learning', limit=20)

# Retrieve all items (use everything() for complete results)
all_items = zot.everything(zot.items())
```

## Core Concepts

- A `Zotero` instance is bound to a single library (user or group). All methods operate on that library.
- Item data lives in `item['data']`. Access fields like `item['data']['title']`, `item['data']['creators']`.
- Pyzotero returns 100 items by default (API default is 25). Use `zot.everything(zot.items())` to get all items.
- Return types are method-specific: `update_item()` reports Boolean success, while `create_items()` returns per-item creation status. Inspect its `failed`, `successful` (full saved objects), `success` (legacy keys), and `unchanged` mappings and retain the input-index-to-key mapping. A truthy response dictionary does not establish that every item was created; report partial failures and retry only the failed inputs after reconciliation. See the [write-method contracts](https://pyzotero.readthedocs.io/en/latest/#creating-and-updating-items).

## Reference Files

| File | Contents |
|------|----------|
| [references/pyzotero/references/authentication.md](references/pyzotero/references/authentication.md) | Credentials, library types, local mode |
| [references/pyzotero/references/read-api.md](references/pyzotero/references/read-api.md) | Retrieving items, collections, tags, groups |
| [references/pyzotero/references/search-params.md](references/pyzotero/references/search-params.md) | Filtering, sorting, search parameters |
| [references/pyzotero/references/write-api.md](references/pyzotero/references/write-api.md) | Creating, updating, deleting items |
| [references/pyzotero/references/collections.md](references/pyzotero/references/collections.md) | Collection CRUD operations |
| [references/pyzotero/references/tags.md](references/pyzotero/references/tags.md) | Tag access and management |
| [references/pyzotero/references/files-attachments.md](references/pyzotero/references/files-attachments.md) | File download and attachment uploads |
| [references/pyzotero/references/exports.md](references/pyzotero/references/exports.md) | BibTeX, CSL-JSON, bibliography export |
| [references/pyzotero/references/pagination.md](references/pyzotero/references/pagination.md) | follow(), everything(), generators |
| [references/pyzotero/references/full-text.md](references/pyzotero/references/full-text.md) | Full-text content indexing and access |
| [references/pyzotero/references/saved-searches.md](references/pyzotero/references/saved-searches.md) | Saved search management |
| [references/pyzotero/references/cli.md](references/pyzotero/references/cli.md) | Command-line interface (local Zotero) |
| [references/pyzotero/references/mcp.md](references/pyzotero/references/mcp.md) | MCP server for LLM clients (local Zotero) |
| [references/pyzotero/references/error-handling.md](references/pyzotero/references/error-handling.md) | Errors and exception handling |

## Common Patterns

### Fetch and modify an item
```python
item = zot.item('ITEMKEY')
item['data']['title'] = 'New Title'
zot.update_item(item)
```

### Create an item from a template
```python
template = zot.item_template('journalArticle')
template['title'] = 'My Paper'
template['creators'] = [{'creatorType': 'author', 'firstName': 'Jane', 'lastName': 'Doe'}]
result = zot.create_items([template])
if result.get('failed'):
    raise RuntimeError(f"Item creation failed: {result['failed']}")
```

### Export as BibTeX
```python
bibtex = zot.top(format='bibtex', limit=50)
# bibtex is a bibtexparser BibDatabase object
print(bibtex.entries)
```

### Local reads (no API key needed)
```python
zot = Zotero(library_id='0', library_type='user', local=True)
items = zot.items()
```

### Local Zotero (CLI or MCP)

The CLI and MCP server search a running Zotero desktop app, including indexed PDF text, with Zotero 7+ and local API access enabled. Zotero 10+ also supports writes with a separate local API key. The MCP server exposes writes only with `--enable-writes`; permanent deletion additionally requires `--enable-deletes`. Python local writes cannot use `item_template()`; see the authentication reference. See [references/pyzotero/references/cli.md](references/pyzotero/references/cli.md) and [references/pyzotero/references/mcp.md](references/pyzotero/references/mcp.md).
