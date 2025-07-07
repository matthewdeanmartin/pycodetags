Certainly! Here's **PEP 002** written in the style of a Python Enhancement Proposal (PEP), tailored for the `pycodetags` project and its plugin system.

---

# PEP 002 – Plugin System Standardization and Expansion

| PEP:      | 002                                                               |
| --------- | ----------------------------------------------------------------- |
| Title:    | Standardizing and Expanding the Plugin Architecture in PyCodeTags |
| Author:   | PyCodeTags Team                                                   |
| Status:   | Draft                                                             |
| Type:     | Standards Track                                                   |
| Created:  | 2025-07-12                                                        |
| Requires: | PEP 000                                                           |
| License:  | MIT                                                               |

## Abstract

This PEP proposes a standardized and more extensible plugin architecture for the `pycodetags` tool. It aims to define clearer plugin lifecycle hooks, address limitations in the current system, and provide plugin authors with additional integration points such as preprocessing, schema extension, custom validators, and runtime transformation logic.

## Motivation

PyCodeTags supports a plugin system via `pluggy` but currently exposes a limited set of hooks:

* CLI registration (`add_cli_subcommands`)
* Report printing (`print_report`)
* Source tag collection (`find_source_tags`)
* Schema provisioning (`provide_schemas`)
* Validation (`validate`)

This minimal surface:

* Restricts advanced integrations (e.g., code analyzers, runtime behavior modifiers).
* Offers inconsistent support across lifecycle stages (e.g., no hooks for parsing, preprocessing).
* Lacks standardized ways to inspect and manipulate tag metadata beyond simple validation.

By standardizing and expanding the plugin API, PyCodeTags can become a more powerful and customizable platform for domain-specific code annotation, documentation, and automation.

## Rationale

Plugin extensibility should cover:

* **Discovery**: Add hooks that allow discovery of custom tag semantics (e.g., per organization).
* **Schema Augmentation**: Allow plugins to contribute new tag schemas.
* **Parsing**: Enable plugins to preprocess comments or contribute alternate parsing logic.
* **Validation**: Support layered or scoped validators.
* **Runtime Integration**: Allow hooks into tag execution logic.
* **Serialization**: Plugins may define how tags should be persisted or transformed.

## Specification

### Plugin Lifecycle Hooks

This PEP proposes the following *new* or improved hook specifications (in addition to those that already exist):

#### `preprocess_source`

```python
@hookspec
def preprocess_source(source_code: str, file_path: str | None, config: CodeTagsConfig) -> str:
    """Optionally modify or transform source code before comment/tag extraction."""
```

#### `parse_custom_tags`

```python
@hookspec
def parse_custom_tags(source_code: str, file_path: str, config: CodeTagsConfig) -> list[DataTag | FolkTag]:
    """Allow plugins to extract tags from source code using custom logic (e.g., regex, LLMs)."""
```

#### `postprocess_data`

```python
@hookspec
def postprocess_data(data: list[DATA], config: CodeTagsConfig) -> list[DATA]:
    """Modify or enrich collected DATA items after aggregation."""
```

#### `contribute_runtime_actions`

```python
@hookspec
def contribute_runtime_actions(data: DATA, config: CodeTagsConfig) -> None:
    """Allow plugins to define new runtime behaviors when a DATA tag is invoked at runtime."""
```

#### `decorate_validation`

```python
@hookspec
def decorate_validation(data: DATA, errors: list[str], config: CodeTagsConfig) -> list[str]:
    """Enhance or suppress validation errors dynamically."""
```

#### `contribute_serializers`

```python
@hookspec
def contribute_serializers(data: DATA, config: CodeTagsConfig) -> dict[str, str]:
    """Provide custom serialization formats (e.g., markdown, YAML, org-mode)."""
```

### Enhancements to Existing Hooks

* `provide_schemas()` should return richer metadata (e.g., display preferences, file affinity).
* `validate()` should be executed in a multi-stage chainable fashion.
* `find_source_tags()` may optionally receive preprocessed source.

## Backwards Compatibility

Existing plugins using `pluggy` hooks like `validate`, `print_report`, or `add_cli_subcommands` will continue to function as-is. The hook specification is additive and backwards-compatible.

## Reference Implementation

This PEP will result in:

* Expanding the `plugin_specs.py` file to define new hooks.
* Updating the plugin manager to recognize and register new hook implementations.
* Adding `postprocess`, `preprocess`, and `runtime` phases to the internal `aggregate` and `load` pipelines.
* Modifying `DATA.validate()` to invoke `decorate_validation()` if available.

## Security Considerations

Allowing plugins to preprocess or execute runtime logic increases the potential for malicious or unintended side effects. Plugins should be sandboxed (where feasible), and a config flag (e.g. `trusted_plugins`) may be introduced to selectively enable them.

## Future Directions

* Plugin-level permissions in config files.
* Plugin inspection via CLI (`pycodetags plugin-info --verbose`).
* Metadata about plugin authorship and versioning.

## Copyright

This document is licensed under the MIT License.

---

Let me know if you'd like a version as a `.md` file or included in the source tree as a proposed `PEP002.md`.
