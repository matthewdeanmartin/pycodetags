# PyCodeTags Design Document

## Overview

**PyCodeTags** is a Python package that treats code annotations (e.g., `TODO`, `FIXME`) as structured, first-class entities. It is inspired by PEP 350 and provides parsing, transformation, validation, and reporting mechanisms for code tags across Python source files and modules. It supports extensibility via plugins and integrates with build tools through configuration in `pyproject.toml`.

## Goals

- Parse structured and folk (unstructured) tags from code comments.
- Convert tags into structured `DATA` objects for processing.
- Enable aggregation of tags across modules and file paths.
- Allow schema-based validation and transformation.
- Provide reporting tools and CLI for developers.
- Support plugin-based extensibility.

---

## Architecture Overview

### Core Components:

1. **Data Tag System**

   - `DATA` class: Represents a structured tag with typed metadata.
   - `DataTagSchema`: Defines accepted tag structures and validation rules.
   - `FolkTag`: Simplified tags parsed with heuristics.

2. **Parsers and Converters**

   - `data_tags_parsers.py`: Extracts structured and folk tags from code.
   - `converters.py`: Converts raw tags into `DATA` instances.

3. **Tag Aggregation**

   - `aggregate.py`: High-level API to collect tags from files and modules.
   - `collect.py`: Traverses Python objects for embedded `DATA` instances.

4. **Config and Schema Control**

   - `config.py`: Loads and parses `pyproject.toml` for tool behavior.
   - `pure_data_schema.py`: Provides default schema.

5. **Reporting and CLI**

   - `views.py`: Multiple output formats (text, json, html).
   - `__main__.py`: CLI entrypoint using `argparse`.

6. **Plugin System**

   - `plugin_manager.py`: Manages pluggy-based extension mechanism.
   - `plugin_specs.py`: Defines plugin hook specifications.

---

## Data Flow Summary

```
User Source Code
   |
   V
aggregate_all_kinds_multiple_input
   |
   V
[ Module Import ] <----> [ File Traversal ]
   |                          |
   V                          V
collect_all_data         iterate_comments_from_file
   |                          |
   V                          V
DATA objects         DataTag / FolkTag parsed
   \                         /
    \                       /
     --> Converters --> DATA
                            |
                            V
                         Reporting / CLI
```

---

## Key Design Concepts

### 1. **Structured Tags (**``**)**

- Represented using `dataclass`.
- Fields: `code_tag`, `comment`, `data_fields`, `custom_fields`, `file_path`, `offsets`, etc.
- Provides `as_data_comment()` for serializing back to a comment.
- Usable as decorators or context managers.

### 2. **Parsing Strategy**

- `comment_finder.py`: Uses `ast_comments` or fallback to tokenize-based line parsing.
- `data_tags_parsers.py`: Extracts metadata from comment blocks using regex and schema rules.
- Supports both PEP-style and informal `# TODO: text` tags.

### 3. **Schema System**

- `DataTagSchema` defines field types, default values, and aliases.
- Promotes raw fields into structured fields (e.g., infers `priority=high`).
- Schemas can be extended through config or plugins.

### 4. **Aggregation Logic**

- Supports module introspection using `importlib`.
- Recursively scans attributes using `inspect`.
- Source file traversal uses pathlib and plugin hook fallback.

### 5. **Configuration**

- Defined in `pyproject.toml` under `[tool.pycodetags]`.
- Fields:
  - `src`: source directories
  - `modules`: python modules to scan
  - `active_schemas`: enabled schemas (e.g., todo, bug)
  - `disable_all_runtime_behavior`, `enable_actions`, etc.

### 6. **Plugin Support**

- Plugins register new CLI commands, file handlers, validations, or report formats.
- Uses `pluggy` for flexible extension points.

---

## CLI Commands

- `init`: initializes pyproject.toml section.
- `data`: collects and displays tag data.
- `plugin-info`: lists loaded plugins.
- Plugins can register new commands.

---

## Example: Data Tag

```python
# TODO: Refactor login logic <priority:high module:auth date:2025-07-12>
```

Parsed into:

```json
{
  "code_tag": "TODO",
  "comment": "Refactor login logic",
  "data_fields": {
    "priority": "high",
    "module": "auth",
    "date": "2025-07-12"
  },
  ...
}
```

---

## Design Strengths

- Schema-based extensibility.
- Works with both structured and legacy comments.
- Strong CLI interface and reporting.
- Plugin-ready and configuration-driven.

## Potential Improvements

- More robust AST support for comment extraction.
- LSP integration for IDE feedback.
- Web UI for tag browsing and filtering.
- CI integration for validation enforcement.

---

## Conclusion

**PyCodeTags** enables a formal and extensible framework for managing annotations in source code. Its schema-driven design and plugin architecture make it suitable for both small projects and large-scale codebases that require structured metadata tracking and reporting from comments.

