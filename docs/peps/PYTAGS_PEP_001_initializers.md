# PYCODETAGS PEP: 001 – Pycodetags Enhancement Proposal 

| PEP:             | 001                                                                                             |
|------------------|-------------------------------------------------------------------------------------------------|
| Title:           | Default Initializers for Data Tag Fields                                                        |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com)               |
| Author:          | [ChatGPT (gpt-4-turbo, OpenAI)](https://chatgpt.com/share/68728893-3324-8007-bcd1-164a8338beda) |
| Status:          | Draft                                                                                           |
| Type:            | Standards Track                                                                                 |
| Created:         | 2025-07-12                                                                                      |
| License:         | MIT                                                                                             |
| Intended Version | ≥ 0.6.0                                                                                         |

## Abstract

This PEP proposes a feature extension to PyCodeTags that introduces a standardized mechanism for defining default values and initializers for data tag fields within schemas. These initializers will support a small expression language powered by JMESPath. The evaluator will receive two JSON documents: the code tag's structured representation and a metadata context (e.g., `$git_blame`, `$git_user`). This allows powerful, declarative initialization logic while maintaining safety and modularity.

## Motivation

While PyCodeTags supports typed metadata and schema validation, its current handling of default/unlabeled fields (previously referred to as "defaults") lacks sophistication:

- They cannot be initialized dynamically.
- There is no formal mechanism for fallback or conditional population.
- Many common values (e.g., creation date, author) must be manually specified.

To address this, we propose expanding the schema's field definitions to include `value_on_new`, `value_on_blank`, and `value_on_delete`, which support a safe expression DSL based on JMESPath.

## Specification

### Schema Field Extension

We extend the `FieldInfo` structure in `data_tags_schema.py`:

```python
class FieldInfo(TypedDict):
    name: str
    data_type: str
    valid_values: list[str]
    label: str
    description: str
    aliases: list[str]
    value_on_new: str  # JMESPath expression
    value_on_blank: str  # JMESPath expression
    value_on_delete: str  # JMESPath expression
```

### Expression Engine

Expressions in `value_on_*` fields are JMESPath queries. Evaluation occurs using a composite context:

```json
{
  "tag": { ... },
  "meta": {
    "current_date": "2025-07-12",
    "current_time": "18:30",
    "git_user": "matthew",
    "git_blame": "alice",
    "cwd": "/project",
    "filename": "main.py"
  }
}
```

These values are injected at runtime by the resolver engine.

### Example JMESPath Expressions

| Use Case                                  | Expression                                                                                                        |   |                  |
|-------------------------------------------|-------------------------------------------------------------------------------------------------------------------|---|------------------|
| Use git blame or fallback to current user | \`meta.git\_blame                                                                                                 |   | meta.git\_user\` |
| Infer module name from path               | `tag.file_path.split('/')[1]`                                                                                     |   |                  |
| Tag classifier by comment                 | `contains(tag.comment, 'refactor') ? 'technical_debt' : 'feature'`                                                |   |                  |
| Escalate priority if security-related     | `tag.data_fields.module == 'security' && tag.data_fields.priority == 'low' ? 'medium' : tag.data_fields.priority` |   |                  |

### Application Semantics

- `value_on_new`: used when a new tag is created and the field is not explicitly set.
- `value_on_blank`: used if a tag exists but the field is empty.
- `value_on_delete`: used to represent the logical placeholder when a tag is deleted or a field is removed.

## Dependency

- **Library**: [JMESPath](https://github.com/jmespath/jmespath.py)
- **Rationale**: JMESPath is safe, expressive, and suitable for querying structured tag data without allowing arbitrary code execution.

## Implementation Plan

The following files will need to be updated:

### 1. `data_tags_schema.py`

- Extend `FieldInfo` with `value_on_new`, `value_on_blank`, `value_on_delete`.

### 2. `data_tags_methods.py`

- Modify `promote_fields()` to evaluate JMESPath expressions.
- Introduce `resolve_jmespath(expr: str, context: dict) -> str`

### 3. `converters.py`

- When building `DATA`, ensure blank or missing fields are initialized using schema logic.

### 4. `data_tags_parsers.py`

- Integrate the evaluation of `value_on_new` and `value_on_blank` when parsing tags.

### 5. (Optional) `plugin_specs.py`

- Expose plugin hooks for populating the `meta` dictionary passed to JMESPath.

### 6. New Utility Module

- `expression_engine.py`: wrapper around JMESPath to evaluate expressions with tag+meta context.

## Future Considerations

- Add expression chaining with fallback (e.g., `expr1 || expr2 || 'unknown'`).
- Allow user-defined meta sources via plugins.
- Inject CI/build metadata as meta fields (e.g., commit hash, build number).

## Rejected Ideas

- Embedding arbitrary Python code in field expressions (too risky).
- Defining our own DSL (reinventing the wheel).

## Reference Example

```toml
[data_fields.assignee]
data_type = "str"
label = "Assigned To"
description = "Person responsible"
value_on_new = "meta.git_user"
value_on_blank = "'unassigned'"
value_on_delete = "'archived'"
```

```python
# TODO: Refactor the code <priority:high>
# --> Automatically expands to:
# TODO: Refactor the code <priority:high assignee:matthew>
```

## Copyright

This document is licensed under the MIT License.


Authoritative source URL: [https://chatgpt.com/share/68728893-3324-8007-bcd1-164a8338beda](https://chatgpt.com/share/68728893-3324-8007-bcd1-164a8338beda)

