# How to create a plugin

## Examples

Look at the example plugins in the `/plugins/` folder.

Some plugins need plugins. Look at the issue tracker plugin for examples.

The plugin architecture assumes you will be either extending the pycodetags as a serialization and parsing library or
you will be creating static websites or other reports using parsed code tags.

## Steps

- Make a schema (optionally use existing schema)
- Optionally create a strongly typed Tag class deriving from `DATA` (Optionally use the DATA() class directly)
- Optionally implement identity and equality logic. 
- Optionally add run time behaviors to your strongly typed tag
- Optionally create validations for your tags
- Optionally create views that use a list of DATA objects
- Wire up entrypoints in pyproject.toml
- Test, test, test
- Publish to pypi with a name prefixed with `pycodetags-` so I can find it and add it to the directory of plugins.


## Implement the Hook Spec

Implement some or all of these methods as some sort of callable.

```python
import argparse
import pluggy
from pycodetags.config import CodeTagsConfig
from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTag
from pycodetags.folk_code_tags import FolkTag

hookspec = pluggy.HookspecMarker("pycodetags")

class CodeTagsSpec:

    @hookspec
    def register_app(self, pm: pluggy.PluginManager, parser: argparse.ArgumentParser) -> bool:
        ...

    @hookspec
    def print_report(
        self, format_name: str, found_data: list[DATA], output_path: str, config: CodeTagsConfig
    ) -> bool:
        ...

    @hookspec
    def print_report_style_name(self) -> list[str]:
        ...

    @hookspec
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        ...

    @hookspec
    def run_cli_command(
        self, command_name: str, args: argparse.Namespace, found_data: list[DATA], config: CodeTagsConfig
    ) -> bool:
        ...

    @hookspec
    def validate(self, item: DataTag, config: CodeTagsConfig) -> list[str]:
        ...

    @hookspec
    def find_source_tags(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> list[FolkTag]:
        ...

    @hookspec
    def file_handler(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> bool:
        ...
```

## Things the library provides

You get 
- CLI commands
- Config file
- Iteration across files
- Tag parsing

You provide
- Pretty output reports
- Business rules for validation and actions
- A schema for data fields, default fields
- A domain to decide what the fields mean, what the action mean, etc.
