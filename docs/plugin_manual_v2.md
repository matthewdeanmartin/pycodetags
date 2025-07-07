# 📦 PyCodeTags Plugin Developer Manual

## Overview

Welcome to the **PyCodeTags Plugin System**! This guide is for developers who want to extend the behavior of PyCodeTags through plugins.

You’ll learn how to:

* Understand the plugin architecture
* Register new CLI commands or output formats
* Contribute custom schemas, tag parsers, or runtime actions
* Validate or enrich DATA tags

PyCodeTags uses [Pluggy](https://pluggy.readthedocs.io/) under the hood — the same system powering `pytest`.

---

## 🔌 Plugin Basics

### 📁 Entry Point Structure

Your plugin must expose a `pycodetags` entry point in `pyproject.toml` or `setup.cfg`:

```toml
[project.entry-points."pycodetags"]
my_plugin = "my_plugin_package.plugin:plugin"
```

or in `setup.py`:

```python
entry_points={
    "pycodetags": ["my_plugin = my_plugin_package.plugin:plugin"],
}
```

### 🧠 Basic Structure

Your plugin must implement and register a class with one or more hook implementations.

```python
from pycodetags.plugin_specs import CodeTagsSpec

class MyPlugin:
    @CodeTagsSpec.hookimpl
    def provide_schemas(self):
        return [MY_CUSTOM_SCHEMA]

    @CodeTagsSpec.hookimpl
    def validate(self, item, config):
        return ["Missing 'originator'" if not item.data_fields.get("originator") else ""]

plugin = MyPlugin()
```

---

## 🪝 Available Hooks

Below is the full set of hooks available to plugin authors, with examples.

### 1. `provide_schemas()`

Register new tag schemas.

```python
def provide_schemas():
    return [MY_CUSTOM_SCHEMA]
```

Use this to support domain-specific tags (e.g. compliance, safety, etc.).

---

### 2. `find_source_tags()`

Extract tags from custom file types (e.g. `.md`, `.ipynb`).

```python
def find_source_tags(already_processed, file_path, config):
    if file_path.endswith(".md"):
        return extract_md_tags(file_path)
    return []
```

---

### 3. `print_report()`

Provide a custom report format.

```python
def print_report(format_name, found_data, output_path, config):
    if format_name == "csv":
        with open(output_path or "output.csv", "w") as f:
            for item in found_data:
                f.write(f"{item.code_tag},{item.comment}\n")
        return True
    return False
```

---

### 4. `print_report_style_name()`

Declare new report format names.

```python
def print_report_style_name():
    return ["csv"]
```

---

### 5. `add_cli_subcommands()`

Add subcommands to the CLI.

```python
def add_cli_subcommands(subparsers):
    parser = subparsers.add_parser("hello", help="Say hello from plugin")
    parser.add_argument("--name", help="Your name")
```

Then handle with `run_cli_command`.

---

### 6. `run_cli_command()`

Respond to CLI subcommands.

```python
def run_cli_command(command_name, args, found_data, config):
    if command_name == "hello":
        print(f"Hello, {args.name or 'World'}!")
        return True
    return False
```

---

### 7. `validate()`

Inject additional validation logic for a tag.

```python
def validate(item, config):
    errors = []
    if not item.comment:
        errors.append("Comment is required.")
    return errors
```

---

### 8. `decorate_validation()`

Post-process validation messages.

```python
def decorate_validation(data, errors, config):
    if "originator" not in data.data_fields:
        errors.append("originator field missing (enforced by company policy)")
    return errors
```

---

### 9. `postprocess_data()`

Transform `DATA` items after they’ve been loaded.

```python
def postprocess_data(data, config):
    for item in data:
        item.data_fields["checked_by"] = "auto-tool"
    return data
```

---

### 10. `preprocess_source()`

Transform raw source code before parsing.

```python
def preprocess_source(source_code, file_path, config):
    return source_code.replace("👀", "# TODO:")
```

---

### 11. `parse_custom_tags()`

Define your own tag extraction logic from raw source.

```python
def parse_custom_tags(source_code, file_path, config):
    if "##BUG:" in source_code:
        return [{
            "code_tag": "BUG",
            "comment": "Hardcoded password",
            "fields": {"default_fields": {}, "data_fields": {}, "custom_fields": {}, "unprocessed_defaults": [], "identity_fields": []},
            "file_path": file_path,
            "original_text": "##BUG: Hardcoded password",
            "original_schema": "custom",
            "offsets": (5, 0, 5, 25)
        }]
    return []
```

---

### 12. `contribute_runtime_actions()`

Add runtime behavior when a `DATA` tag is called as a decorator or context manager.

```python
def contribute_runtime_actions(data, config):
    if data.data_fields.get("priority") == "high":
        print(f"[ALERT] Running high-priority code: {data.comment}")
```

---

## 🧪 Developing Your Plugin

We recommend setting up an editable install:

```bash
pip install -e .[dev]
```

Enable plugin logging:

```bash
pycodetags --verbose plugin-info
```

Or test your custom report:

```bash
pycodetags data --src myproject --format csv --output out.csv
```

---

## 🧰 Helper Utilities

* Use `pycodetags.inspect_file(path)` to test parsing.
* Use `DATA.as_data_comment()` to print your tag as a comment.
* Leverage your schema’s `field_infos` to apply dynamic logic (e.g. defaulting, display names).

---

## 🛡️ Best Practices

* ✅ Use unique schema names
* ✅ Add version headers or comments
* ✅ Make plugin features opt-in via config
* ✅ Catch exceptions inside plugins — don’t let them crash `pycodetags`
* ❌ Don’t mutate global state
* ❌ Don’t monkeypatch PyCodeTags internals

---

## 📚 Resources

* [PEP 002: Plugin Standardization and Expansion](#)
* [`pluggy` documentation](https://pluggy.readthedocs.io/)
* Example plugin: [`pycodetags-issue-tracker`](https://github.com/pycodetags/plugins/pycodetags_issue_tracker)

---

## ✨ Contributing

Have ideas for improving plugin support? File a proposal or open a PR against [PEP 002](https://github.com/pycodetags/peps)!
