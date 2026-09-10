# pycodetags-universal

Read standalone JavaScript/TypeScript `//` comment blocks using explicit TDG or extended PEP-350
schemas. Supports pycodetags 0.8.x and Python 3.9–3.15.

```toml
[tool.pycodetags]
schema = "TDG"
src = ["web"]
```

```javascript
// TODO: Retry failed uploads
// id=17 issue=100
// Retry transient failures.
const attempts = 5;
```

Install with `pip install pycodetags-universal`, then run `pycodetags data --format json`.
Use `schema = "PEP350"` and trailing `<...>` metadata for that format. Per-path schema rules work
as in the core library. Only `.js`, `.ts`, `.jsx`, and `.tsx` are scanned. Standalone line comments
are supported; inline comments, block comments, and string-literal detection are outside this scanner.

Records are read-only: core mutation, ID assignment, and the SQLite snapshot index support Python
source files. The plugin does not claim safe JavaScript rewriting or arbitrary-language parsing.
