# Contents of pycodetags source tree

## File: aggregate.py

```python
from __future__ import annotations

import importlib
import logging
import logging.config
import pathlib

from pycodetags.app_config import get_code_tags_config
from pycodetags.data_tags import (
    DATA,
    DataTag,
    DataTagSchema,
    convert_data_tag_to_data_object,
    iterate_comments_from_file,
)
from pycodetags.exceptions import FileParsingError, ModuleImportError
from pycodetags.pure_data_schema import PureDataSchema
from pycodetags.python.collect import collect_all_data

logger = logging.getLogger(__name__)


def aggregate_all_kinds_multiple_input(
    module_names: list[str], source_paths: list[str], schema: DataTagSchema
) -> list[DATA]:
    if not module_names:
        module_names = []
    if not source_paths:
        source_paths = []
    if schema is None:
        schema = PureDataSchema
    logger.info(
        f"aggregate_all_kinds_multiple_input: module_names={module_names}, source_paths={source_paths}"
    )
    collected_DATA: list[DATA] = []
    collected: list[DataTag] = []
    found_in_modules: list[DATA] = []

    for module_name in module_names:
        found_tags, found_in_modules = aggregate_all_kinds(module_name, "", schema)
        collected.extend(found_tags)
        logger.debug(
            f"Found {len(found_in_modules)} by looking at imported module: {module_name}"
        )

    for source_path in source_paths:
        found_tags, found_in_modules = aggregate_all_kinds("", source_path, schema)
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_tags)} by looking at src folder {source_path}")

    for found_tag in collected:
        item = convert_data_tag_to_data_object(found_tag, schema)
        collected_DATA.append(item)
    collected_DATA.extend(found_in_modules)

    return collected_DATA


def aggregate_all_kinds(
    module_name: str, source_path: str, schema: DataTagSchema
) -> tuple[list[DataTag], list[DATA]]:
    config = get_code_tags_config()

    active_schemas = config.active_schemas()

    logger.info(
        f"aggregate_all_kinds: module_name={module_name}, source_path={source_path}, active_schemas={active_schemas}"
    )
    found_in_modules: list[DATA] = []
    if bool(module_name) and module_name is not None and not module_name == "None":
        logging.info(f"Checking {module_name}")
        try:
            module = importlib.import_module(module_name)
            found_in_modules = collect_all_data(module, include_submodules=False)
        except ImportError as ie:
            logger.error(f"Error: Could not import module(s) '{module_name}'")
            raise ModuleImportError(
                f"Error: Could not import module(s) '{module_name}'"
            ) from ie

    found_tags: list[DataTag] = []
    schemas: list[DataTagSchema] = [schema]

    if source_path:
        src_found = 0
        path = pathlib.Path(source_path)
        files = [path] if path.is_file() else path.rglob("*.*")
        for file in files:
            if file.name.endswith(".py"):

                found_items = list(
                    _
                    for _ in iterate_comments_from_file(
                        str(file),
                        schemas=schemas,
                        include_folk_tags="folk" in active_schemas,
                    )
                )
                found_tags.extend(found_items)
                src_found += 1
            else:
                from pycodetags.plugin_manager import get_plugin_manager

                pm = get_plugin_manager()

                plugin_results = pm.hook.find_source_tags(
                    already_processed=False,
                    file_path=str(file),
                    config=get_code_tags_config(),
                )
                for result_list in plugin_results:
                    found_tags.extend(result_list)
                if plugin_results:
                    src_found += 1
        if src_found == 0:
            raise FileParsingError(
                f"Can't find any files in source folder {source_path}"
            )

    return found_tags, found_in_modules

```

## File: common_interfaces.py

```python
from __future__ import annotations

import io
import os
from collections.abc import Iterable
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import TextIO, Union

from pycodetags.data_tags import (
    DATA,
    DataTag,
    DataTagSchema,
    convert_data_tag_to_data_object,
    iterate_comments,
)
from pycodetags.pure_data_schema import PureDataSchema

IOInput = Union[str, os.PathLike, TextIO]  ##

IOSource = Union[str, IOInput]


def string_to_data(
    value: str,
    file_path: Path | None = None,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> Iterable[DATA]:
    if schema is None:
        schema = PureDataSchema
    tags = []
    for tag in iterate_comments(
        value,
        source_file=file_path,
        schemas=[schema],
        include_folk_tags=include_folk_tags,
    ):
        tags.append(convert_data_tag_to_data_object(tag, schema))
    return tags


def string_to_data_tag_typed_dicts(
    value: str,
    file_path: Path | None = None,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> Iterable[DataTag]:
    if schema is None:
        schema = PureDataSchema
    tags: list[DataTag] = []
    for tag in iterate_comments(
        value,
        source_file=file_path,
        schemas=[schema],
        include_folk_tags=include_folk_tags,
    ):
        tags.append(tag)
    return tags


def _open_for_read(source: IOInput) -> StringIO | TextIOWrapper | TextIO:
    if isinstance(source, str):
        return io.StringIO(source)
    elif isinstance(source, os.PathLike) or isinstance(source, str):
        return open(source, encoding="utf-8")
    elif hasattr(source, "read"):
        return source  ##

    else:
        raise TypeError(f"Unsupported input type: {type(source)}")


def _open_for_write(dest: IOInput) -> StringIO | TextIOWrapper | TextIO:
    if isinstance(dest, io.StringIO):
        return dest  ##

    elif isinstance(dest, os.PathLike) or isinstance(dest, str):
        return open(dest, "w", encoding="utf-8")
    elif hasattr(dest, "write"):
        return dest  ##

    else:
        raise TypeError(f"Unsupported output type: {type(dest)}")


def dumps(obj: DATA) -> str:
    if not obj:
        return ""

    return obj.as_data_comment()


def dump(obj: DATA, dest: Union[str, Path, os.PathLike, TextIO]) -> None:  ##

    with _open_for_write(dest) as f:
        f.write(obj.as_data_comment())


def loads(
    s: str,
    file_path: Path | None = None,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> DATA | None:
    items = string_to_data(s, file_path, schema, include_folk_tags)
    return next((_ for _ in items), None)


def load(
    source: IOInput,
    file_path: Path | None = None,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> DATA | None:

    with _open_for_read(source) as f:
        items = string_to_data(f.read(), file_path, schema, include_folk_tags)
        return next((_ for _ in items), None)


def dump_all(objs: Iterable[DATA], dest: IOInput) -> None:
    with _open_for_write(dest) as f:
        for obj in objs:
            f.write(obj.as_data_comment() + "\n")


def dumps_all(objs: Iterable[DATA]) -> str:
    return "\n".join(obj.as_data_comment() for obj in objs)


def load_all(
    source: IOInput,
    file_path: Path | None = None,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> Iterable[DATA]:
    with _open_for_read(source) as f:
        return string_to_data(f.read(), file_path, schema, include_folk_tags)


def loads_all(
    s: str,
    file_path: Path | None = None,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> Iterable[DATA]:
    return string_to_data(s, file_path, schema, include_folk_tags)


def inspect_file(
    file_path: str | Path,
    schema: DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> list[DATA]:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"No such file: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    schema = schema or PureDataSchema

    return list(
        string_to_data(
            content,
            file_path=file_path,
            schema=schema,
            include_folk_tags=include_folk_tags,
        )
    )


def list_available_schemas() -> list[DataTagSchema]:
    schemas = [PureDataSchema]

    from pycodetags.plugin_manager import get_plugin_manager

    pm = get_plugin_manager()
    if hasattr(pm.hook, "provide_schemas"):
        for result in pm.hook.provide_schemas():
            if isinstance(result, list):
                schemas.extend(result)
    return schemas

```

## File: exceptions.py

```python
class PyCodeTagsError(Exception):


class DataTagError(PyCodeTagsError):


class ValidationError(PyCodeTagsError):


class SchemaError(PyCodeTagsError):


class DataTagParseError(PyCodeTagsError):


class AggregationError(PyCodeTagsError):


class ModuleImportError(AggregationError):


class SourceNotFoundError(AggregationError):


class PluginError(PyCodeTagsError):


class PluginLoadError(PluginError):


class PluginHookError(PluginError):


class FileParsingError(PyCodeTagsError):


class CommentNotFoundError(FileParsingError):


class ConfigError(PyCodeTagsError):


class InvalidActionError(ConfigError):

```

## File: filters.py

```python
import logging
from collections.abc import Callable
from typing import Any

import jmespath

from pycodetags.data_tags.data_tags_classes import DATA

logger = logging.getLogger(__name__)


class InvalidJMESPathFilter(Exception):
    pass


def compile_jmes_filter(expression: str) -> Callable[[dict[str, Any]], bool]:
    try:
        compiled = jmespath.compile(expression)
    except jmespath.exceptions.JMESPathError as e:
        raise InvalidJMESPathFilter(f"Invalid JMESPath expression: {e}") from e

    def predicate(flat_dict: dict[str, Any]) -> bool:
        try:
            result = compiled.search(flat_dict)
            return bool(result)
        except Exception as e:
            logger.warning(f"Failed to evaluate JMESPath expression: {e}")
            return False

    return predicate


def filter_data_by_expression(data_list: list[DATA], expression: str) -> list[DATA]:

    pred = compile_jmes_filter(expression)
    return [
        item
        for item in data_list
        if pred(item.to_flat_dict(include_comment_and_tag=True))
    ]

```

## File: logging_config.py

```python
from __future__ import annotations

import logging
import os
from typing import Any

try:
    import colorlog  ##

    if False:  ##

        assert colorlog  ##

    colorlog_available = True
except ImportError:  ##

    colorlog_available = False


def generate_config(
    level: str = "DEBUG", enable_bug_trail: bool = False
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "standard": {"format": "[%(levelname)s] %(name)s: %(message)s"},
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": "%(log_color)s%(levelname)-8s%(reset)s %(green)s%(message)s",
            },
        },
        "handlers": {
            "default": {
                "level": level,
                "formatter": "colored",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  ##
            },
        },
        "loggers": {
            "pycodetags": {
                "handlers": ["default"],
                "level": level,
                "propagate": False,
            }
        },
    }
    if not colorlog_available:
        del config["formatters"]["colored"]
        config["handlers"]["default"]["formatter"] = "standard"

    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        config["handlers"]["default"]["formatter"] = "standard"

    if enable_bug_trail:
        try:

            import bug_trail_core
        except ImportError:
            print(
                "bug_trail_core is not installed, skipping bug trail handler configuration."
            )
            return config

        section = bug_trail_core.read_config(config_path="pyproject.toml")

        config["handlers"]["bugtrail"] = {
            "class": "bug_trail_core.BugTrailHandler",
            "db_path": section.database_path,
            "minimum_level": logging.DEBUG,
        }
        config["loggers"]["pycodetags"]["handlers"].append("bugtrail")

    return config

```

## File: mutator.py

```python
from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path


from pycodetags.data_tags import DATA
from pycodetags.exceptions import DataTagError


def apply_mutations(
    file_path: str | os.PathLike[str],
    mutations: Sequence[tuple[DATA, DATA | None]],
) -> None:
    p_file_path = Path(file_path)
    if not p_file_path.is_file():
        raise FileNotFoundError(f"No such file: '{p_file_path}'")

    try:
        content = p_file_path.read_text()
    except Exception as e:
        raise OSError(f"Could not read file '{p_file_path}': {e}") from e

    replacements = []
    for old_tag, new_tag in mutations:
        if not isinstance(old_tag, DATA) or (
            new_tag is not None and not isinstance(new_tag, DATA)
        ):
            raise TypeError("mutations must be a list of (DATA, DATA | None) tuples.")

        if not old_tag.offsets or old_tag.original_text is None:
            raise DataTagError(
                "The 'old_tag' must be an object from a parse operation "
                "with valid 'offsets' and 'original_text' attributes."
            )

        start_line, start_char, end_line, end_char = old_tag.offsets

        lines = content.splitlines(True)
        if start_line == end_line:
            try:
                original_slice = lines[start_line][start_char:end_char]
            except IndexError as ie:
                raise DataTagError("Tag mismatch") from ie
        else:

            first_line = lines[start_line][start_char:]
            middle_lines = "".join(lines[start_line + 1 : end_line])
            last_line = lines[end_line][:end_char]
            original_slice = first_line + middle_lines + last_line

        if " ".join(original_slice.split()) != " ".join(old_tag.original_text.split()):
            raise DataTagError(
                f"Tag mismatch for '{old_tag.comment}' at {p_file_path}:{start_line + 1}. "
                "The file may have been modified since the tag was parsed."
            )

        replacement_text = new_tag.as_data_comment() if new_tag else ""
        replacements.append((old_tag.offsets, replacement_text))

    replacements.sort(key=lambda item: item[0][0], reverse=True)

    lines = content.splitlines(True)  ##

    for (start_line, start_char, end_line, end_char), new_text in replacements:
        if start_line == end_line:

            line = lines[start_line]
            lines[start_line] = line[:start_char] + new_text + line[end_char:]
        else:

            indentation = lines[start_line][:start_char]

            formatted_new_text = new_text
            if new_text:

                new_text_lines = new_text.splitlines(True)
                formatted_new_text = "".join(
                    [
                        f"{indentation}{line.lstrip()}" if index > 0 else line
                        for index, line in enumerate(new_text_lines)
                    ]
                )

            first_line_part = lines[start_line][:start_char]
            last_line_part = lines[end_line][end_char:]

            lines[start_line] = first_line_part + formatted_new_text + last_line_part

            for i in range(start_line + 1, end_line + 1):
                lines[i] = ""

    modified_content = "".join(lines)

    try:

        temp_file_path = p_file_path.with_suffix(f"{p_file_path.suffix}.tmp")
        temp_file_path.write_text(modified_content)
        os.replace(temp_file_path, p_file_path)
    except Exception as e:
        raise OSError(f"Could not write to file '{p_file_path}': {e}") from e


def delete_tags(
    file_path: str | os.PathLike[str],
    tags_to_delete: list[DATA],
) -> None:
    mutations = [(tag, None) for tag in tags_to_delete]
    apply_mutations(file_path, mutations)


def replace_with_strings(
    file_path: str | os.PathLike[str],
    replacements: list[tuple[DATA, str]],
) -> None:
    mutations = []
    for old_tag, new_string in replacements:

        new_tag = DATA(code_tag=old_tag.code_tag, comment=new_string)
        mutations.append((old_tag, new_tag))
    apply_mutations(file_path, mutations)


def insert_tags(
    file_path: str | os.PathLike[str],
    insertions: list[tuple[int, DATA, int]],
) -> None:
    p_file_path = Path(file_path)
    if not p_file_path.is_file():
        raise FileNotFoundError(f"No such file: '{p_file_path}'")

    try:
        lines = p_file_path.read_text().splitlines(True)

        if not lines or not lines[-1].endswith(("\n", "\r")):
            lines.append("\n")

    except Exception as e:
        raise OSError(f"Could not read file '{p_file_path}': {e}") from e

    for line_number, _tag_to_insert, _ in insertions:
        if not (1 <= line_number <= len(lines) + 1):
            raise ValueError(
                f"Invalid line number: {line_number}. File has {len(lines)} lines."
            )

        if line_number <= len(lines) and lines[line_number - 1].strip():
            raise ValueError(
                f"Cannot insert tag at line {line_number}. Line is not blank."
            )

    insertions.sort(key=lambda item: item[0], reverse=True)

    for line_number, tag_to_insert, indent_level in insertions:
        indentation = " " * indent_level
        tag_text = tag_to_insert.as_data_comment()

        indented_tag_text = (
            "\n".join(f"{indentation}{line}" for line in tag_text.splitlines()) + "\n"
        )

        lines.insert(line_number - 1, indented_tag_text)

    modified_content = "".join(lines)

    try:
        temp_file_path = p_file_path.with_suffix(f"{p_file_path.suffix}.tmp")
        temp_file_path.write_text(modified_content)
        os.replace(temp_file_path, p_file_path)
    except Exception as e:
        raise OSError(f"Could not write to file '{p_file_path}': {e}") from e

```

## File: plugin_manager.py

```python
import logging

import pluggy

from pycodetags.plugin_specs import CodeTagsSpec

logger = logging.getLogger(__name__)

PM = pluggy.PluginManager("pycodetags")
PM.add_hookspecs(CodeTagsSpec)

PLUGIN_COUNT = PM.load_setuptools_entrypoints("pycodetags")
logger.info(f"Found {PLUGIN_COUNT} plugins")


def reset_plugin_manager() -> None:

    global PM  ##

    PM = pluggy.PluginManager("pycodetags")
    PM.add_hookspecs(CodeTagsSpec)
    PM.load_setuptools_entrypoints("pycodetags")


if logger.isEnabledFor(logging.DEBUG):

    PM.trace.root.setwriter(print)
    undo = PM.enable_tracing()


def get_plugin_manager() -> pluggy.PluginManager:
    return PM


def plugin_currently_loaded(pm: pluggy.PluginManager) -> None:
    print("--- Loaded pycodetags Plugins ---")
    loaded_plugins = pm.get_plugins()  ##

    if not loaded_plugins:
        print("No plugins currently loaded.")
    else:
        for plugin in loaded_plugins:
            plugin_name = pm.get_canonical_name(plugin)  ##

            blocked_status = " (BLOCKED)" if pm.is_blocked(plugin_name) else ""  ##

            print(f"- {plugin_name}{blocked_status}")

            for hook_name in pm.hook.__dict__:
                if hook_name.startswith("_"):  ##

                    continue
                hook_caller = getattr(pm.hook, hook_name)
                if plugin in hook_caller.get_hookimpls():  ##

                    print(f"  - Implements hook: {hook_name}")

    print("------------------------------")

```

## File: plugin_specs.py

```python

from __future__ import annotations


import argparse
from typing import Callable  ##


import pluggy

from pycodetags.app_config import CodeTagsConfig
from pycodetags.data_tags import DATA, DataTag, DataTagSchema

hookspec = pluggy.HookspecMarker("pycodetags")


class CodeTagsSpec:

    @hookspec
    def register_app(self, pm: pluggy.PluginManager, parser: argparse.ArgumentParser) -> bool:
        return False

    @hookspec
    def print_report(self, format_name: str, found_data: list[DATA], output_path: str, config: CodeTagsConfig) -> bool:
        return False

    @hookspec
    def print_report_style_name(self) -> list[str]:
        return []

    @hookspec
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  ##


    @hookspec
    def run_cli_command(
        self,
        command_name: str,
        args: argparse.Namespace,
        found_data: Callable[[DataTagSchema], list[DATA]],
        config: CodeTagsConfig,
    ) -> bool:
        return False

    @hookspec
    def validate(self, item: DataTag, config: CodeTagsConfig) -> list[str]:
        return []

    @hookspec
    def find_source_tags(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> list[DataTag]:
        return []

    @hookspec
    def file_handler(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> bool:
        return False

    @hookspec
    def provide_schemas(self) -> list[DataTagSchema]:
        return []

```

## File: pure_data_schema.py

```python
from pycodetags.data_tags.data_tags_schema import DataTagSchema

PureDataSchema: DataTagSchema = {
    "name": "DATA",
    "matching_tags": ["DATA"],
    "default_fields": {},
    "data_fields": {},
    "data_field_aliases": {},
    "field_infos": {},
}

```

## File: _TODO.py

```python


```

## File: __about__.py

```python
__all__ = [
    "__title__",
    "__version__",
    "__description__",
    "__readme__",
    "__credits__",
    "__keywords__",
    "__license__",
    "__requires_python__",
    "__status__",
]

__title__ = "pycodetags"
__version__ = "0.6.0"
__description__ = "TODOs in source code as a first class construct, follows PEP350"
__readme__ = "README.md"
__credits__ = [{"name": "Matthew Martin", "email": "matthewdeanmartin@gmail.com"}]
__keywords__ = [
    "pep350",
    "pep-350",
    "codetag",
    "codetags",
    "code-tags",
    "code-tag",
    "TODO",
    "FIXME",
    "pycodetags",
]
__license__ = "MIT"
__requires_python__ = ">=3.7"
__status__ = "4 - Beta"

```

## File: __init__.py

```python
__all__ = [
    "DATA",
    "DataTag",
    "DataTagSchema",
    "PureDataSchema",
    "dumps",
    "dump",
    "dump_all",
    "dumps_all",
    "loads",
    "load",
    "load_all",
    "loads_all",
    "CodeTagsSpec",
    "CodeTagsConfig",
    "inspect_file",
    "list_available_schemas",
]

from pycodetags.app_config import CodeTagsConfig
from pycodetags.common_interfaces import (
    dump,
    dump_all,
    dumps,
    dumps_all,
    inspect_file,
    list_available_schemas,
    load,
    load_all,
    loads,
    loads_all,
)
from pycodetags.data_tags import DATA, DataTag, DataTagSchema
from pycodetags.plugin_specs import CodeTagsSpec
from pycodetags.pure_data_schema import PureDataSchema

```

## File: __main__.py

```python
from __future__ import annotations

import argparse
import logging
import logging.config
import sys
from collections.abc import Sequence

import pluggy

import pycodetags.__about__ as __about__
import pycodetags.pure_data_schema as pure_data_schema
from pycodetags.aggregate import aggregate_all_kinds_multiple_input
from pycodetags.app_config.config import CodeTagsConfig, get_code_tags_config
from pycodetags.app_config.config_init import init_pycodetags_config
from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.exceptions import CommentNotFoundError
from pycodetags.filters import InvalidJMESPathFilter, filter_data_by_expression
from pycodetags.logging_config import generate_config
from pycodetags.plugin_manager import get_plugin_manager, plugin_currently_loaded
from pycodetags.utils import load_dotenv
from pycodetags.views import (
    print_html,
    print_json,
    print_summary,
    print_text,
    print_validate,
)


class InternalViews:

    @pluggy.HookimplMarker("pycodetags")
    def print_report(self, format_name: str, found_data: list[DATA]) -> bool:
        if format_name == "text":
            print_text(found_data)
            return True
        if format_name == "html":
            print_html(found_data)
            return True
        if format_name == "json":
            print_json(found_data)
            return True
        if format_name == "summary":
            print_summary(found_data)
            return True
        return False


def main(argv: Sequence[str] | None = None) -> int:
    pm = get_plugin_manager()

    pm.register(InternalViews())

    parser = argparse.ArgumentParser(
        description=f"{__about__.__description__} (v{__about__.__version__})",
        epilog="Install pycodetags-issue-tracker plugin for TODO tags. ",
    )
    common_switches(parser)

    base_parser = argparse.ArgumentParser(add_help=False)
    common_switches(base_parser)

    base_parser.add_argument(
        "--validate", action="store_true", help="Validate all the items found"
    )

    base_parser.add_argument("--filter", help="JMESPath filter expression")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser(
        "init", parents=[base_parser], help="Initialize domain-free config"
    )

    report_parser = subparsers.add_parser(
        "data", parents=[base_parser], help="Generate code tag reports"
    )

    report_parser.add_argument(
        "--module",
        action="append",
        help="Python module to inspect (e.g., 'my_project.main')",
    )
    report_parser.add_argument(
        "--src", action="append", help="file or folder of source code"
    )

    report_parser.add_argument("--output", help="destination file or folder")

    extra_supported_formats = []
    for result in pm.hook.print_report_style_name():
        extra_supported_formats.extend(result)

    supported_formats = list(
        set(["text", "html", "json", "summary"] + extra_supported_formats)
    )

    report_parser.add_argument(
        "--format",
        choices=supported_formats,
        default="text",
        help="Output format for the report.",
    )

    _plugin_info_parser = subparsers.add_parser(
        "plugin-info",
        parents=[base_parser],
        help="Display information about loaded plugins",
    )

    new_subparsers = pm.hook.add_cli_subcommands(subparsers=subparsers)

    for new_subparser in new_subparsers:
        common_switches(new_subparser)

        new_subparser.add_argument(
            "--validate", action="store_true", help="Validate all the items found"
        )
        new_subparser.add_argument("--filter", help="JMESPath filter")

    args = parser.parse_args(args=argv)

    if hasattr(args, "config") and args.config:
        code_tags_config = CodeTagsConfig(pyproject_path=args.config)
    else:
        code_tags_config = CodeTagsConfig()

    if code_tags_config.use_dot_env():
        load_dotenv()

    verbose = hasattr(args, "verbose") and args.verbose
    info = hasattr(args, "info") and args.info
    bug_trail = hasattr(args, "bug_trail") and args.bug_trail

    if verbose:
        config = generate_config(level="DEBUG", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)
    elif info:
        config = generate_config(level="INFO", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)
    else:

        config = generate_config(level="FATAL", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "init":
        init_pycodetags_config()
        return 0

    if args.command in ("report", "data"):
        modules = args.module or code_tags_config.modules_to_scan()
        src = args.src or code_tags_config.source_folders_to_scan()

        if not modules and not src:
            print(
                "Need to specify one or more importable modules (--module) "
                "or source code folders/files (--src) or specify in config file.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            found = aggregate_all_kinds_multiple_input(
                modules, src, pure_data_schema.PureDataSchema
            )

            if args.filter:
                try:
                    found = filter_data_by_expression(found, args.filter)
                except InvalidJMESPathFilter as e:
                    print(f"Filter error: {e}", file=sys.stderr)
                    return 200

        except ImportError:
            print(f"Error: Could not import module(s) '{args.module}'", file=sys.stderr)
            return 1

        if args.validate:
            if len(found) == 0:
                raise CommentNotFoundError("No data to validate.")
            found_problems = print_validate(found)
            print(f"{len(found)} validation problems.")
            if found_problems:
                return 100
        else:
            if len(found) == 0:
                raise CommentNotFoundError("No data to report.")

            results = pm.hook.print_report(
                format_name=args.format,
                output_path=args.output,
                found_data=found,
                config=get_code_tags_config(),
            )
            if not any(results):
                print(
                    f"Error: Format '{args.format}' is not supported.", file=sys.stderr
                )
                return 1

    elif args.command == "plugin-info":
        plugin_currently_loaded(pm)
    else:

        if hasattr(args, "module") and args.module:
            modules = getattr(args, "module", [])
        else:
            modules = code_tags_config.modules_to_scan()

        if hasattr(args, "src") and args.src:
            src = getattr(args, "src", [])
        else:
            src = code_tags_config.source_folders_to_scan()

        def found_data_for_plugins_callback(schema: DataTagSchema) -> list[DATA]:
            try:
                return source_and_modules_searcher(
                    args.command, modules, src, schema, args.filter
                )
            except InvalidJMESPathFilter as e:
                print(f"Filter error: {e}", file=sys.stderr)
                sys.exit(200)

        handled_by_plugin = pm.hook.run_cli_command(
            command_name=args.command,
            args=args,
            found_data=found_data_for_plugins_callback,
            config=get_code_tags_config(),
        )
        if not any(handled_by_plugin):
            print(f"Error: Unknown command '{args.command}'.", file=sys.stderr)
            return 1
    return 0


def source_and_modules_searcher(
    command: str, modules: list[str], src: list[str], schema: DataTagSchema, filter: str
) -> list[DATA]:
    try:
        all_found: list[DATA] = []
        for source in src:
            found_tags = aggregate_all_kinds_multiple_input([""], [source], schema)
            all_found.extend(found_tags)
        more_found = aggregate_all_kinds_multiple_input(modules, [], schema)
        all_found.extend(more_found)

        if filter:
            all_found = filter_data_by_expression(all_found, filter)

        found_data_for_plugins = all_found

    except ImportError:
        logging.warning(
            f"Could not aggregate data for command {command}, proceeding without it."
        )
        found_data_for_plugins = []
    return found_data_for_plugins


def common_switches(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        help="Path to config file, defaults to current folder pyproject.toml",
    )
    parser.add_argument(
        "--verbose",
        default=False,
        action="store_true",
        help="verbose level logging output",
    )
    parser.add_argument(
        "--info", default=False, action="store_true", help="info level logging output"
    )
    parser.add_argument(
        "--bug-trail",
        default=False,
        action="store_true",
        help="enable bug trail, local logging",
    )


if __name__ == "__main__":
    sys.exit(main())

```

## File: app_config\config.py

```python
from __future__ import annotations

import logging
import os
import sys
from typing import Any

from pycodetags.exceptions import ConfigError

try:
    import tomllib  ##


except ModuleNotFoundError:
    try:
        import toml
    except ImportError:

        pass


logger = logging.getLogger(__name__)


def careful_to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("false", "0"):
        return False
    if value is None:
        return default
    if value == "":
        return default
    return default


class CodeTagsConfig:
    _instance: CodeTagsConfig | None = None
    config: dict[str, Any] = {}

    def __init__(self, pyproject_path: str = "pyproject.toml"):

        self._pyproject_path = pyproject_path
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._pyproject_path):
            self.config = {}
            return

        with open(self._pyproject_path, "rb" if "tomllib" in sys.modules else "r") as f:

            data = tomllib.load(f) if "tomllib" in sys.modules else toml.load(f)

        self.config = data.get("tool", {}).get("pycodetags", {})

    def disable_all_runtime_behavior(self) -> bool:

        return careful_to_bool(
            self.config.get("disable_all_runtime_behavior", False), False
        )

    def enable_actions(self) -> bool:

        return careful_to_bool(self.config.get("enable_actions", False), False)

    def default_action(self) -> str:

        field = "default_action"
        result = self.config.get(field, "")
        accepted = ("warn", "warning", "stop", "nothing", "")
        if result not in accepted:
            raise ConfigError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

    def disable_on_ci(self) -> bool:

        return careful_to_bool(self.config.get("disable_on_ci", True), True)

    def use_dot_env(self) -> bool:

        return careful_to_bool(self.config.get("use_dot_env", True), True)

    @property
    def runtime_behavior_enabled(self) -> bool:

        return bool(self.config) and not careful_to_bool(
            self.config.get("disable_all_runtime_behavior", False), False
        )

    def modules_to_scan(self) -> list[str]:

        return [_.lower() for _ in self.config.get("modules", [])]

    def source_folders_to_scan(self) -> list[str]:

        return [_.lower() for _ in self.config.get("src", [])]

    def active_schemas(self) -> list[str]:

        return [str(_).lower() for _ in self.config.get("active_schemas", [])]

    @classmethod
    def get_instance(cls, pyproject_path: str = "pyproject.toml") -> CodeTagsConfig:

        if cls._instance is None:
            cls._instance = cls(pyproject_path)
        return cls._instance

    @classmethod
    def set_instance(cls, instance: CodeTagsConfig | None) -> None:

        cls._instance = instance


def get_code_tags_config() -> CodeTagsConfig:
    return CodeTagsConfig.get_instance()

```

## File: app_config\config_init.py

```python
from __future__ import annotations

import os


def init_pycodetags_config() -> None:

    pyproject_path = "pyproject.toml"
    print("--- PyCodeTags Config Initializer ---")

    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, encoding="utf-8") as f:
                content = f.read()
            if "[tool.pycodetags]" in content:
                print(
                    f"\nConfiguration for '[tool.pycodetags]' already exists in {pyproject_path}."
                )
                print(
                    "Initialization is not needed. Please edit the file manually for any changes."
                )
                return
        except OSError as e:
            print(f"Error reading {pyproject_path}: {e}")
            return

    print("\nSearching for potential source code folders...")
    potential_folders = _find_potential_src_folders()

    if not potential_folders:
        print("Could not automatically detect any source folders.")
        src_folder = input(
            "Please manually enter the path to your source folder (e.g., 'src', 'my_app'): "
        )
    else:
        src_folder = _select_src_folder_interactive(potential_folders) or ""

    if not src_folder or not src_folder.strip():
        print("\nNo source folder selected. Aborting initialization.")
        return

    print(f"\nUsing '{src_folder}' as the primary source folder.")

    toml_section = _generate_pycodetags_toml_section(src_folder)

    _write_to_pyproject_safe(toml_section, pyproject_path)

    print(
        "\nInitialization complete! You can now customize the settings in pyproject.toml."
    )


def _find_potential_src_folders(root: str = ".") -> list[str]:

    folders = []

    project_name = os.path.basename(os.path.abspath(root))

    for name in ["src", "app", project_name]:
        if os.path.isdir(name) and name not in folders:

            try:
                if any(f.endswith(".py") for f in os.listdir(name)):
                    folders.append(name)
            except OSError:
                continue  ##

    for item in os.listdir(root):
        if os.path.isdir(item) and not item.startswith(".") and "venv" not in item:
            if item in folders:
                continue
            try:
                if any(f.endswith(".py") for f in os.listdir(item)):
                    folders.append(item)
            except OSError:
                continue  ##

    return folders


def _select_src_folder_interactive(folders: list[str]) -> str | None:

    print("\nPlease select your primary source folder from the list below:")
    for i, folder in enumerate(folders):
        print(f"  {i+1}) {folder}")
    print(f"  {len(folders)+1}) [Manual Entry]")
    print(f"  {len(folders)+2}) [Cancel]")

    while True:
        try:
            choice_str = input(f"Enter your choice [1-{len(folders)+2}]: ")
            choice_int = int(choice_str)
            if 1 <= choice_int <= len(folders):
                return folders[choice_int - 1]
            elif choice_int == len(folders) + 1:
                return input("Enter path to your source folder: ")
            elif choice_int == len(folders) + 2:
                return None
            else:
                print(
                    f"Invalid choice. Please enter a number between 1 and {len(folders)+2}."
                )
        except (ValueError, IndexError):
            print("Invalid input. Please enter a number from the list.")


def _generate_pycodetags_toml_section(src_folder: str) -> str:

    return f"""
[tool.pycodetags]
# Source folders to scan for code tags.
# This allows you to run `pycodetags` without specifying the path every time.
src = ["{src_folder}"]

# --- Optional: Common Configurations ---

# Specify Python modules to scan. Useful if your project structure is complex.
# modules = []

# Define which tag schemas are active.
# Default schemas are: todo, fixme, hack, note, perf, bug, question, important
# Example: active_schemas = ["todo", "fixme", "bug"]

# --- Runtime Behavior Control ---
# These settings control pycodetags's behavior when imported in your code.

# Master switch to disable all runtime features (e.g., for production).
# Setting this to true ensures zero performance overhead from the library.
disable_all_runtime_behavior = false

# Enables or disables the runtime actions ('log', 'warn', 'stop').
# If false, runtime checks are silent, even if `disable_all_runtime_behavior` is false.
enable_actions = true

# Default action for runtime checks if a tag doesn't specify one.
# Valid options: "warn", "stop" (raises TypeError), "log", or "nothing".
default_action = "warn"

# Automatically disables all runtime actions when in a CI environment.
# Checks for common CI environment variables (e.g., CI, GITHUB_ACTIONS).
disable_on_ci = true

# Allow pycodetags to load environment variables from a .env file.
use_dot_env = true
"""


def _write_to_pyproject_safe(toml_section: str, pyproject_path: str) -> None:

    try:

        with open(pyproject_path, "a", encoding="utf-8") as f:

            if f.tell() > 0:
                f.write("\n")  ##

            f.write(toml_section.strip())

        print(f"\nSuccessfully configured '[tool.pycodetags]' in {pyproject_path}")
    except OSError as e:
        print(f"\nError: Could not write to {pyproject_path}. {e}")


if __name__ == "__main__":

    init_pycodetags_config()

```

## File: app_config\__init__.py

```python
__all__ = ["get_code_tags_config", "CodeTagsConfig", "init_pycodetags_config"]

from pycodetags.app_config.config import CodeTagsConfig, get_code_tags_config
from pycodetags.app_config.config_init import init_pycodetags_config

```

## File: data_tags\data_tags_classes.py

```python


from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field, fields
from functools import wraps
from typing import Any, Callable, cast  ##



from pycodetags.exceptions import DataTagError, ValidationError

try:
    from typing import Literal  ##


except ImportError:
    from typing_extensions import Literal  ##



logger = logging.getLogger(__name__)


class Serializable:


    def to_dict(self) -> dict[str, Any]:

        d = self.__dict__.copy()
        for key, value in list(d.items()):
            if isinstance(value, datetime.datetime):
                d[key] = value.isoformat()
            if key.startswith("_"):
                del d[key]
            if key == "data_meta":
                del d[key]
        return d


@dataclass(eq=False)
class DATA(Serializable):


    code_tag: str | None = "DATA"
    """Capitalized tag name"""
    comment: str | None = None
    """Unstructured text"""








    default_fields: dict[str, str] | None = None
    data_fields: dict[str, str] | None = None
    custom_fields: dict[str, str] | None = None
    identity_fields: list[str] | None = None
    unprocessed_defaults: list[str] | None = None





    file_path: str | None = None
    original_text: str | None = None
    original_schema: str | None = None
    offsets: tuple[int, int, int, int] | None = None

    data_meta: DATA | None = field(init=False, default=None)
    """Necessary internal field for decorators"""

    def __post_init__(self) -> None:

        self.data_meta = self

    def _perform_action(self) -> None:


    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
            self._perform_action()
            return cast(Callable[..., Any], func(*args, **kwargs))

        cast(Any, wrapper).data_meta = self
        return wrapper

    def __enter__(self) -> DATA:


        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> Literal[False]:
        return False  ##





    def validate(self) -> list[str]:

        return []

    def validate_or_raise(self) -> None:
        errors = self.validate()
        if errors:
            raise ValidationError(errors)

    def _extract_data_fields(self) -> dict[str, str]:
        d = {}
        for f in fields(self):


            if f.name in ("data_fields", "default_fields"):
                continue
            val = getattr(self, f.name)




            if val is not None:
                if isinstance(val, datetime.datetime):
                    d[f.name] = val.isoformat()
                else:
                    d[f.name] = str(val)





        return d

    def as_data_comment(self) -> str:

        the_fields = ""
        to_skip = []

        metadata = [
            "file_path",
            "line_number",
            "original_text",
            "original_schema",
            "offsets",
        ]

        if self.default_fields:
            for key, value in self.default_fields.items():
                to_skip.append(key)
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
                elif isinstance(value, list):
                    value = ",".join(value)
                the_fields += f"{value} "

        for field_set in (self.custom_fields, self.data_fields):
            if field_set:
                for key, value in field_set.items():

                    if (
                        value  ##


                        and key != "custom_fields"
                        and key not in to_skip  ##


                        and not key.startswith("_")  ##


                        and key not in metadata  ##


                    ):
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        elif isinstance(value, list):
                            value = ",".join(value)
                        else:
                            value = str(value)
                        if " " in value and "'" in value and '"' in value:
                            value = f'"""{value}"""'
                        elif " " in value and '"' not in value:
                            value = f'"{value}"'
                        elif " " in value and "'" not in value:
                            value = f"'{value}'"
                        elif ":" in value or "=" in value:
                            value = f'"{value}"'

                        the_fields += f"{key}:{value} "

        first_line = f"# {(self.code_tag or '').upper()}: {self.comment}"
        complete = f"{first_line} <{the_fields.strip()}>"
        if len(complete) > 120:
            first_line += "\n# "
            complete = f"{first_line}<{the_fields.strip()}>"
        return complete

    def __eq__(self, other: object) -> bool:













        for f in fields(self):
            self_val = getattr(self, f.name)
            other_val = getattr(other, f.name)



            if self_val is self and other_val is other:
                continue

            if self_val != other_val:
                return False

        return True

    def __repr__(self) -> str:
        field_strings = []
        for f in fields(self):
            if f.name != "data_meta" and f.name != "type":
                field_strings.append(f"{f.name}={getattr(self, f.name)!r}")
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

    def terminal_link(self) -> str:

        if self.offsets:
            start_line, start_char, _end_line, _end_char = self.offsets
            return f"{self.file_path}:{start_line+1}:{start_char}"
        if self.file_path:
            return f"{self.file_path}:0"
        return ""

    def to_flat_dict(self, include_comment_and_tag: bool = False, raise_on_doubles: bool = True) -> dict[str, Any]:





        if self.data_fields:
            data = self.data_fields.copy()
        else:
            data = {}
        if self.custom_fields:
            for key, value in self.custom_fields.items():
                if raise_on_doubles and key in data:
                    raise DataTagError("Field in data_fields and custom fields")
                data[key] = value
        if include_comment_and_tag:
            if self.comment:
                data["comment"] = self.comment
            if self.code_tag:
                data["code_tag"] = self.code_tag
        return data

```

## File: data_tags\data_tags_methods.py

```python
from __future__ import annotations

import datetime
import logging
from typing import Any

import jmespath
from jmespath.functions import Functions
from jmespath.visitor import Options

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_schema import (
    DataTagFields,
    DataTagSchema,
    FieldInfo,
)
from pycodetags.data_tags.meta_builder import build_meta_object

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  ##


logger = logging.getLogger(__name__)


class DataTag(TypedDict, total=False):

    code_tag: str
    comment: str
    fields: DataTagFields

    file_path: str | None
    original_text: str | None
    """Source code before parsing"""

    original_schema: str | None
    """Pep350 or Folk"""

    offsets: tuple[int, int, int, int] | None
    """Start line, start character, end line, end character"""


def convert_data_tag_to_data_object(tag_value: DataTag, schema: DataTagSchema) -> DATA:

    kwargs = upgrade_to_specific_schema(tag_value, schema)

    return DATA(**kwargs)  ##


def upgrade_to_specific_schema(
    tag_value: DataTag, schema: DataTagSchema, flat: bool = True
) -> dict[str, Any]:

    try:
        print(tag_value)
        data_fields = tag_value["fields"]["data_fields"]
    except KeyError:
        print(tag_value)
        raise
    custom_fields = tag_value["fields"]["custom_fields"]
    final_data = {}
    final_custom = {}
    for found, value in data_fields.items():
        if found in schema["data_fields"]:
            final_data[found] = value
        else:
            final_custom[found] = value
    for found, value in custom_fields.items():
        if found in schema["data_fields"]:
            if found in final_data:
                logger.warning("Found same field in both data and custom")
            final_data[found] = value
        else:
            if found in final_custom:
                logger.warning("Found same field in both data and custom")
            final_custom[found] = value
    kwargs: DataTag | dict[str, Any] = {
        "code_tag": tag_value["code_tag"],
        "comment": tag_value["comment"],
        "file_path": tag_value.get("file_path"),
        "original_text": tag_value.get("original_text"),
        "original_schema": "pep350",
        "offsets": tag_value.get("offsets"),
    }
    if flat:
        kwargs["default_fields"] = tag_value["fields"]["default_fields"]  ##

        kwargs["data_fields"] = final_data  ##

        kwargs["custom_fields"] = final_custom  ##

        ud = tag_value["fields"]["unprocessed_defaults"]
        kwargs["unprocessed_defaults"] = ud  ##

    else:
        kwargs["fields"] = {
            "data_fields": final_data,
            "custom_fields": final_custom,
            "default_fields": tag_value["fields"]["default_fields"],
            "unprocessed_defaults": tag_value["fields"]["unprocessed_defaults"],
            "identity_fields": tag_value["fields"].get("identity_fields", []),
        }
        promote_fields(kwargs, schema)  ##

    return kwargs  ##


def promote_fields(tag: DataTag, data_tag_schema: DataTagSchema) -> None:
    fields = tag["fields"]
    if fields["unprocessed_defaults"]:
        for value in fields.get("unprocessed_defaults", []):
            consumed = False
            for the_type, the_name in data_tag_schema["default_fields"].items():
                if (
                    the_type == "int"
                    and not fields["data_fields"].get(the_name)
                    and not consumed
                ):
                    try:
                        fields["data_fields"][the_name] = int(value)
                        consumed = True
                    except ValueError:
                        logger.warning(f"Failed to convert {value} to int")
                elif (
                    the_type == "date"
                    and not fields["data_fields"].get(the_name)
                    and not consumed
                ):
                    try:
                        fields["data_fields"][the_name] = datetime.datetime.strptime(
                            value, "%Y-%m-%d"
                        ).date()
                        consumed = True
                    except ValueError:
                        logger.warning(f"Failed to convert {value} to datetime")
                elif (
                    the_type == "str"
                    and not fields["data_fields"].get(the_name)
                    and not consumed
                ):
                    fields["data_fields"][the_name] = value
                    consumed = True

    if not fields.get("custom_fields", {}) and not fields.get("default_fields", {}):

        return

    for default_key, default_value in tag["fields"]["default_fields"].items():
        if (
            default_key in fields["data_fields"]
            and fields["data_fields"][default_key] != default_value
        ):

            logger.warning(
                "Field in both data_fields and default_fields and they don't match: "
                f'{default_key}: {fields["data_fields"][default_key]} != {default_value}'
            )

        else:
            fields["data_fields"][default_key] = default_value

    field_aliases: dict[str, str] = data_tag_schema["data_field_aliases"]

    for custom_field, custom_value in fields["custom_fields"].copy().items():
        if custom_field in field_aliases:

            full_alias = field_aliases[custom_field]

            if fields["data_fields"].get(full_alias):

                consumed = False
                if isinstance(fields["data_fields"][full_alias], list):

                    if isinstance(custom_value, list):

                        fields["data_fields"][full_alias].extend(custom_value)
                        consumed = True
                    elif isinstance(custom_value, str):

                        fields["data_fields"][full_alias] = fields["data_fields"][
                            full_alias
                        ].append(custom_value)
                        consumed = True
                    else:

                        logger.warning(
                            f"Promoting custom_field {full_alias}/{custom_value} to unexpected type"
                        )
                        fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                elif isinstance(fields["data_fields"][full_alias], str):
                    if isinstance(custom_value, list):

                        fields["data_fields"][full_alias] = [
                            fields["data_fields"][full_alias]
                        ] + custom_value
                        consumed = True
                    elif isinstance(custom_value, str):

                        fields["data_fields"][full_alias] = [
                            fields["data_fields"][full_alias],
                            custom_value,
                        ]
                        consumed = True
                    else:

                        logger.warning(
                            f"Promoting custom_field {full_alias}/{custom_value} to unexpected type"
                        )
                        fields["data_fields"][full_alias] = [
                            fields["data_fields"][full_alias],
                            custom_value,
                        ]  ##

                        consumed = True
                else:

                    logger.warning(
                        f"Promoting custom_field {full_alias}/{custom_value} to unexpected type"
                    )
                    fields[full_alias] = [fields[full_alias], custom_value]  ##

                    consumed = True
                if consumed:
                    del fields["custom_fields"][custom_field]
                else:

                    logger.warning(
                        f"Failed to promote custom_field {full_alias}/{custom_value}, not consumed"
                    )

    meta = build_meta_object(tag.get("file_path"))
    initialize_fields_from_schema(
        tag, meta, data_tag_schema["field_infos"], is_new=False
    )


def merge_two_dicts(x: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    z = x.copy()  ##

    z.update(y)  ##

    return z


class ExpressionEvaluationError(Exception):
    pass


class CodeTagsCustomFunctions(Functions):  ##

    @jmespath.functions.signature({"types": ["object"]}, {"types": []})  ##
    def _func_lookup(self, dictionary: dict[str, Any], key: Any) -> Any:

        return dictionary.get(key)


def evaluate_field_expression(
    expr: str | None, *, tag: DataTag, meta: dict[str, Any]
) -> Any:

    if not expr:
        return None

    context = {
        "tag": tag,
        "meta": meta,
    }

    try:

        return jmespath.search(
            expr, context, options=Options(custom_functions=CodeTagsCustomFunctions())
        )

    except Exception as e:
        print(expr)
        print(context)
        raise ExpressionEvaluationError(
            f"Error evaluating expression '{expr}': {e}"
        ) from e


def initialize_fields_from_schema(
    tag: DataTag,
    meta: dict[str, Any],
    field_infos: dict[str, FieldInfo],
    is_new: bool = False,
) -> dict[str, Any]:

    result_fields = tag["fields"]["data_fields"]

    for field_name, info in field_infos.items():
        expr = ""
        current_value = result_fields.get(field_name)

        if is_new:
            expr = info.get("value_on_new", "")
        elif not current_value:
            expr = info.get("value_on_blank", "")
        else:
            continue  ##

        if not expr:
            continue

        value = evaluate_field_expression(expr, tag=tag, meta=meta)
        if value is not None:
            logger.debug(f"Setting {field_name} using jmespath expression {expr}")
            result_fields[field_name] = value

    return result_fields

```

## File: data_tags\data_tags_parsers.py

```python
from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path

from pycodetags.data_tags import folk_tags_parser
from pycodetags.data_tags.data_tags_methods import (
    DataTag,
    merge_two_dicts,
    promote_fields,
)
from pycodetags.data_tags.data_tags_schema import DataTagFields, DataTagSchema
from pycodetags.exceptions import SchemaError
from pycodetags.python.comment_finder import find_comment_blocks_from_string

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  ##


logger = logging.getLogger(__name__)


__all__ = ["iterate_comments_from_file", "iterate_comments"]


def iterate_comments_from_file(
    file: str, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag]:

    logger.info(f"iterate_comments: processing {file}")
    yield from iterate_comments(
        Path(file).read_text(encoding="utf-8"), Path(file), schemas, include_folk_tags
    )


def iterate_comments(
    source: str,
    source_file: Path | None,
    schemas: list[DataTagSchema],
    include_folk_tags: bool,
) -> Generator[DataTag]:

    if not schemas and not include_folk_tags:
        raise SchemaError(
            "No active schemas, not looking for folk tags. Won't find anything."
        )
    things: list[DataTag] = []
    for (
        _start_line,
        _start_char,
        _end_line,
        _end_char,
        final_comment,
    ) in find_comment_blocks_from_string(source):

        logger.debug(f"Search for {[_['name'] for _ in schemas]} schema tags")
        found_data_tags = []
        for schema in schemas:
            found_data_tags = parse_codetags(final_comment, schema, strict=False)

            for found in found_data_tags:
                found["file_path"] = str(source_file) if source_file else None
                found["original_text"] = final_comment
                found["original_schema"] = "PEP350"
                found["offsets"] = (_start_line, _start_char, _end_line, _end_char)

            if found_data_tags:
                logger.debug(
                    f"Found data tags! : {','.join(_['code_tag'] for _ in found_data_tags)}"
                )
            things.extend(found_data_tags)

        for schema in schemas:
            if not found_data_tags and include_folk_tags and schema["matching_tags"]:

                found_folk_tags: list[DataTag] = []

                folk_tags_parser.process_text(
                    final_comment,
                    allow_multiline=True,
                    default_field_meaning="assignee",
                    found_tags=found_folk_tags,
                    file_path=str(source_file) if source_file else "",
                    valid_tags=schema["matching_tags"],
                )
                for found_folk_tag in found_folk_tags:

                    a, b, c, d = found_folk_tag["offsets"] or (0, 0, 0, 0)
                    new_offset = (
                        _start_line + a,
                        _start_char + b,
                        _end_line + c,
                        _end_char + d,
                    )
                    found_folk_tag["offsets"] = new_offset

                if found_folk_tags:
                    logger.debug(
                        f"Found folk tags! : {','.join(_['code_tag'] for _ in found_folk_tags)}"
                    )
                things.extend(found_folk_tags)

    yield from things


def is_int(s: str) -> bool:

    if len(s) and s[0] in ("-", "+"):
        return s[1:].isdigit()
    return s.isdigit()


def parse_fields(
    field_string: str, schema: DataTagSchema, strict: bool  ##
) -> DataTagFields:

    legit_names = {}
    for key in schema["data_fields"]:
        legit_names[key] = key
    field_aliases: dict[str, str] = merge_two_dicts(
        schema["data_field_aliases"], legit_names
    )

    fields: DataTagFields = {
        "default_fields": {},
        "data_fields": {},
        "custom_fields": {},
        "unprocessed_defaults": [],
        "identity_fields": [],
    }

    key_value_pattern = re.compile(
        r"""
        ([a-zA-Z_][a-zA-Z0-9_]*) # Key (group 1): alphanumeric key name
        \s*[:=]\s* # Separator (colon or equals, with optional spaces)
        (                        # Start of value group (group 2)
            '(?:[^'\\]|\\.)*' |  # Match single-quoted string (non-greedy, allowing escaped quotes)
            "(?:[^"\\]|\\.)*" |  # Match double-quoted string (non-greedy, allowing escaped quotes)
            (?:[^\s'"<]+)       # Unquoted value: one or more characters not in \s ' " <
        )
        """,
        re.VERBOSE,  ##
    )

    key_value_matches = []

    for match in key_value_pattern.finditer(field_string):

        key_value_matches.append((match.span(), match.group(1), match.group(2)))

    for (_start_idx, _end_idx), key, value_raw in key_value_matches:
        key_lower = key.lower()

        value = value_raw
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        if key_lower in field_aliases:
            normalized_key: str = field_aliases[key_lower]

            fields["data_fields"][normalized_key] = value
        else:

            fields["custom_fields"][key] = value

    consumed_spans = sorted([span for span, _, _ in key_value_matches])

    unconsumed_segments = []
    current_idx = 0

    for start, end in consumed_spans:
        if current_idx < start:

            segment = field_string[current_idx:start].strip()
            if segment:  ##

                unconsumed_segments.append(segment)
        current_idx = max(current_idx, end)  ##

    if current_idx < len(field_string):
        segment = field_string[current_idx:].strip()
        if segment:  ##

            unconsumed_segments.append(segment)

    other_tokens_raw = " ".join(unconsumed_segments)
    other_tokens = [
        token.strip() for token in other_tokens_raw.split() if token.strip()
    ]

    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    for token in other_tokens:

        if token == "#":  ##

            continue
        matched_default = False

        matched_default = False
        for default_type in ["int", "date", "str", "str|list[str]"]:
            default_key = schema["default_fields"].get(default_type)
            if default_key:

                if not matched_default:
                    if default_type == "date" and date_pattern.match(token):

                        fields["default_fields"][default_key] = token  ##

                        matched_default = True
                    elif default_type.replace(" ", "") == "str|list[str]":  ##

                        if default_key in fields["default_fields"]:
                            fields["default_fields"][default_key].extend(
                                [t.strip() for t in token.split(",") if t]
                            )
                        else:
                            fields["default_fields"][default_key] = [
                                t.strip() for t in token.split(",") if t
                            ]
                        matched_default = True
                    elif default_type == "int" and is_int(token):
                        fields["default_fields"][default_key] = token  ##

                        matched_default = True
                    elif default_type == "str":
                        fields["default_fields"][default_key] = token  ##

                        matched_default = True

        if not matched_default:
            fields["unprocessed_defaults"].append(token)

    return fields


def parse_codetags(
    text_block: str, data_tag_schema: DataTagSchema, strict: bool
) -> list[DataTag]:

    results: list[DataTag] = []
    code_tag_regex = re.compile(
        r"""
        (?P<code_tag>[A-Z\?\!]{3,}) # Code tag (e.g., TODO, FIXME, BUG)
        \s*:\s* # Colon separator with optional whitespace
        (?P<comment>.*?)            # Comment text (non-greedy)
        <                           # Opening angle bracket for fields
        (?P<field_string>.*?)       # Field string (non-greedy)
        >                           # Closing angle bracket for fields
        """,
        re.DOTALL | re.VERBOSE,  ##
    )

    matches = list(code_tag_regex.finditer(text_block))
    for match in matches:
        tag_parts = {
            "code_tag": match.group("code_tag").strip(),
            "comment": match.group("comment").strip().rstrip(" \n#"),  ##
            "field_string": match.group("field_string").strip().replace("\n", " "),  ##
        }
        fields = parse_fields(tag_parts["field_string"], data_tag_schema, strict)
        results.append(
            {
                "code_tag": tag_parts["code_tag"],
                "comment": tag_parts["comment"],
                "fields": fields,
                "original_text": "N/A",  ##
            }
        )

    for result in results:
        promote_fields(result, data_tag_schema)
    return results

```

## File: data_tags\data_tags_schema.py

```python
from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  ##


logger = logging.getLogger(__name__)


class DataTagSchema(TypedDict):

    name: str

    matching_tags: list[str]
    """What tag names match, e.g. TODO, FIXME are issue tracker tags"""

    default_fields: dict[str, str]
    """type:name, e.g. str:assignees"""

    data_fields: dict[str, str]
    """name:type, e.g. priority:str"""

    data_field_aliases: dict[str, str]
    """name:alias, e.g. priority:p"""

    field_infos: dict[str, FieldInfo]
    """ALl info about a field, a field could appear in defaults, data"""


class FieldInfo(TypedDict):
    name: str
    """Name as written in tag, no spaces"""
    data_type: str
    """str, int, list[str], str|list[str]"""
    valid_values: list[str]
    """Default range, override with config"""
    label: str
    """What to display in UI"""
    description: str
    """What does this field mean"""
    aliases: list[str]
    """Alternate names and abbreviations for field"""

    value_on_new: str
    """Value on first appearance of data tag, e.g. originator={git-user}"""
    value_on_blank: str
    """Value of last resort that is reasonable at all times, e.g. priority=medium"""
    value_on_delete: str
    """Value of missing field after data tag is deleted, e.g. status=closed"""


class DataTagFields(TypedDict):

    unprocessed_defaults: list[str]

    default_fields: dict[str, list[Any]]
    """Field without label identified by data type, range or fallback, e.g. user and date"""

    data_fields: dict[str, Any]
    """Expected fields with labels, e.g. category, priority"""

    custom_fields: dict[str, str]
    """Key value pairs, e.g. SAFe program increment number"""

    identity_fields: list[str]
    """Fields which combine to form an identity for the tag, e.g. originator, origination_date"""


def merge_schemas(base: DataTagSchema, override: DataTagSchema) -> DataTagSchema:

    merged: DataTagSchema = deepcopy(base)

    merged["name"] = override.get("name", merged["name"])

    merged["matching_tags"] = list(
        sorted(set(merged.get("matching_tags", []) + override.get("matching_tags", [])))
    )

    for key in ("default_fields", "data_fields", "data_field_aliases"):
        base_dict = merged.get(key, {})
        override_dict = override.get(key, {})
        merged[key] = {**base_dict, **override_dict}  ##

    return merged


def data_fields_as_list(schema: DataTagSchema) -> list[str]:
    return list(schema["data_fields"].keys())

```

## File: data_tags\folk_tags_parser.py

```python
from __future__ import annotations

import logging
import re

from pycodetags.data_tags.data_tags_methods import DataTag

try:
    from typing import Literal, TypedDict  ##


except ImportError:
    from typing_extensions import Literal  ##

    from typing_extensions import TypedDict  ##


__all__ = ["process_text"]

logger = logging.getLogger(__name__)


def extract_first_url(text: str) -> str | None:

    pattern = r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/[^\s]+)"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def probably_pep350(text: str) -> bool:
    return ":" in text and "#" in text and "<" in text


def process_text(
    text: str,
    allow_multiline: bool,
    default_field_meaning: str,
    found_tags: list[DataTag],
    file_path: str,
    valid_tags: list[str],
) -> None:
    if probably_pep350(text):

        return

    if "\r\n" in text:
        lines = text.split("\r\n")
    else:
        lines = text.split("\n")

    if len(lines) == 1:
        logger.debug(f"Processing  {file_path}: {lines[0]}")
    else:
        for log_line in lines:
            logger.debug(f"Processing {file_path} ==>: {log_line}")

    line_index = 0
    while line_index < len(lines):
        consumed_lines = process_line(
            file_path,
            found_tags,
            lines,
            line_index,
            valid_tags,
            allow_multiline,
            default_field_meaning,
        )
        line_index += consumed_lines


def process_line(
    file_path: str,
    found_tags: list[DataTag],
    lines: list[str],
    start_idx: int,
    valid_tags: list[str],
    allow_multiline: bool,
    default_field_meaning: str,
) -> int:
    current_line = lines[start_idx]

    match = re.match(r"\s*#\s*([A-Z]+)\b(.*)", current_line)
    if not match:
        return 1

    code_tag_candidate = match.group(1)
    content = match.group(2).strip()

    if valid_tags and code_tag_candidate not in valid_tags:
        return 1

    if content.startswith(":"):
        content = content[1:].lstrip()

    start_line = start_idx
    start_char = current_line.find("#")

    current_idx = start_idx
    if allow_multiline and valid_tags:
        multiline_content = [content]
        next_idx = current_idx + 1
        while next_idx < len(lines):
            next_line = lines[next_idx].strip()
            if next_line.startswith("#") and not any(
                re.match(rf"#\s*{t}\b", next_line) for t in valid_tags
            ):
                multiline_content.append(next_line.lstrip("# "))
                next_idx += 1
            else:
                break
        content = " ".join(multiline_content)
        end_line = next_idx - 1
        end_char = len(lines[end_line].rstrip())
        consumed_lines = next_idx - start_idx
    else:
        end_line = start_idx
        end_char = len(current_line.rstrip())
        consumed_lines = 1

    default_field = None
    custom_fields = {}
    comment = content

    field_match = re.match(r"\(([^)]*)\):(.*)", content)
    if field_match:
        field_section = field_match.group(1).strip()
        comment = field_match.group(2).strip()

        for part in field_section.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                key, val = part.split("=", 1)
                custom_fields[key.strip()] = val.strip()
            else:
                if default_field is None:
                    default_field = part
                else:
                    default_field += ", " + part
    else:
        id_match = re.match(r"(\d+):(.*)", content)
        if id_match:
            default_field = id_match.group(1)
            comment = id_match.group(2).strip()

    found_tag: DataTag = {
        "file_path": file_path,
        "code_tag": code_tag_candidate,
        "fields": {
            "unprocessed_defaults": [],
            "default_fields": {},
            "data_fields": {},
            "custom_fields": custom_fields,
            "identity_fields": [],
        },
        "comment": comment,
        "original_schema": "folk",
        "original_text": content,
        "offsets": (start_line, start_char, end_line, end_char),
    }

    if default_field and default_field_meaning:
        found_tag["fields"]["default_fields"][default_field_meaning] = [default_field]

    url = extract_first_url(comment)
    if url:
        found_tag["fields"]["custom_fields"]["tracker"] = url

    if len(code_tag_candidate) > 1:
        found_tags.append(found_tag)

    return consumed_lines

```

## File: data_tags\tdg_tags_parser.py

```python
from __future__ import annotations

import re
from collections.abc import Generator
from pathlib import Path

from pycodetags.data_tags.data_tags_methods import DataTag
from pycodetags.data_tags.data_tags_parsers import parse_fields
from pycodetags.data_tags.data_tags_schema import DataTagSchema


def iterate_comments(
    source: str, source_file: Path | None, schemas: list[DataTagSchema]
) -> Generator[DataTag]:

    tdg_regex = re.compile(
        r"""
        ^[ \t]*#\s*(?P<code_tag>[A-Z]+):\s*(?P<comment>.*) # Line 1: Tag and Title
        \n[ \t]*#\s*(?P<field_string>[^\n]*)              # Line 2: Fields
        (?P<body_lines>(?:\n[ \t]*#\s*.*)*)                # Line 3+: Optional body
        """,
        re.MULTILINE | re.VERBOSE,
    )

    for match in tdg_regex.finditer(source):
        code_tag = match.group("code_tag").strip()
        comment = match.group("comment").strip()
        field_string = match.group("field_string").strip()
        body_lines_raw = match.group("body_lines")

        active_schema = None
        for schema in schemas:
            if code_tag in schema.get("matching_tags", []):
                active_schema = schema
                break

        if not active_schema:
            continue  ##

        fields = parse_fields(field_string, active_schema, strict=False)

        if body_lines_raw:
            cleaned_body_lines = []
            for line in body_lines_raw.strip().split("\n"):

                cleaned_line = re.sub(r"^[ \t]*#\s?", "", line)
                cleaned_body_lines.append(cleaned_line)
            body = "\n".join(cleaned_body_lines)

            if body:
                fields["custom_fields"]["body"] = body

        start_char_offset = match.start()
        end_char_offset = match.end()

        start_line = source.count("\n", 0, start_char_offset)
        start_col = start_char_offset - source.rfind("\n", 0, start_char_offset) - 1
        end_line = source.count("\n", 0, end_char_offset)
        end_col = end_char_offset - source.rfind("\n", 0, end_char_offset) - 1

        data_tag: DataTag = {
            "code_tag": code_tag,
            "comment": comment,
            "fields": fields,
            "file_path": str(source_file) if source_file else None,
            "original_text": match.group(0),
            "original_schema": "TDG",
            "offsets": (start_line, start_col, end_line, end_col),
        }

        yield data_tag

```

## File: data_tags\__init__.py

```python
__all__ = [
    "DATA",
    "DataTag",
    "DataTagSchema",
    "convert_data_tag_to_data_object",
    "iterate_comments",
    "iterate_comments_from_file",
    "data_fields_as_list",
]

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.data_tags_methods import (
    DataTag,
    convert_data_tag_to_data_object,
)
from pycodetags.data_tags.data_tags_parsers import (
    iterate_comments,
    iterate_comments_from_file,
)
from pycodetags.data_tags.data_tags_schema import DataTagSchema, data_fields_as_list

```

## File: python\collect.py

```python
from __future__ import annotations

import inspect
import logging
import os
import sysconfig
import types
from types import ModuleType, SimpleNamespace
from typing import Any

from pycodetags.data_tags.data_tags_classes import DATA

logger = logging.getLogger(__name__)


def is_stdlib_module(module: types.ModuleType | SimpleNamespace) -> bool:

    if not hasattr(module, "__file__"):
        return True

    stdlib_path = sysconfig.get_paths()["stdlib"]
    the_path = getattr(module, "__file__", "")
    if not the_path:
        return True
    module_path = os.path.abspath(the_path)

    return module_path.startswith(os.path.abspath(stdlib_path))


class DATACollector:

    def __init__(self) -> None:
        self.data: list[DATA] = []
        self.visited: set[int] = set()

    def collect_from_module(
        self, module: ModuleType, include_submodules: bool = True, max_depth: int = 10
    ) -> list[DATA]:

        logger.info(
            f"Collecting from module {module.__name__} with max depth {max_depth}"
        )
        self._reset()
        self._collect_recursive(module, include_submodules, max_depth, 0)
        return self.data.copy()

    def _reset(self) -> None:

        self.data.clear()
        self.visited.clear()

    def _collect_recursive(
        self, obj: Any, include_submodules: bool, max_depth: int, current_depth: int
    ) -> None:

        if current_depth > max_depth or id(obj) in self.visited:
            if current_depth > max_depth:
                logger.debug(f"Maximum depth {max_depth}")
            else:
                logger.debug(f"Already visited {id(obj)}")
            return

        self.visited.add(id(obj))

        if inspect.ismodule(obj) and not is_stdlib_module(obj):
            logger.debug(f"Collecting module {obj}")
            self._collect_from_module_attributes(
                obj, include_submodules, max_depth, current_depth
            )

        if isinstance(obj, SimpleNamespace):
            logger.debug(f"Collecting namespace {obj}")
            self._collect_from_module_attributes(
                obj, include_submodules, max_depth, current_depth
            )

        if inspect.isclass(obj):
            logger.debug(f"Collecting class {obj}")
            self._collect_from_class_attributes(
                obj, include_submodules, max_depth, current_depth
            )

        if inspect.isfunction(obj) or inspect.ismethod(obj):
            logger.debug(f"Collecting function/method {obj}")
            self._check_object_for_metadata(obj)

            self._collect_from_class_attributes(
                obj, include_submodules, max_depth, current_depth
            )
        if isinstance(obj, (list, set, tuple)) and obj:
            logger.debug(f"Found a list/set/tuple {obj}")
            for item in obj:
                self._check_object_for_metadata(item)
        else:

            logger.debug(f"Don't know what to do with {obj}")

    def _check_object_for_metadata(self, obj: Any) -> None:

        if hasattr(obj, "data_meta"):
            if isinstance(obj.data_meta, DATA):
                logger.info(f"Found todo, by instance and has data_meta attr on {obj}")
                self.data.append(obj.data_meta)

    def _collect_from_module_attributes(
        self,
        module: ModuleType | SimpleNamespace,
        include_submodules: bool,
        max_depth: int,
        current_depth: int,
    ) -> None:

        if is_stdlib_module(module) or module.__name__ == "builtins":
            return

        for attr_name in dir(module):
            if attr_name.startswith("__"):
                continue

            logger.debug(f"looping : {module} : {attr_name}")

            try:
                attr = getattr(module, attr_name)

                if include_submodules and inspect.ismodule(attr):

                    if (
                        hasattr(attr, "__file__")
                        and attr.__file__ is not None
                        and not attr.__name__.startswith("builtins")
                    ):
                        self._collect_recursive(
                            attr, include_submodules, max_depth, current_depth + 1
                        )

                else:
                    logger.debug(f"Collecting something ...{attr_name}: {attr}")
                    self._collect_recursive(
                        attr, include_submodules, max_depth, current_depth + 1
                    )

            except (AttributeError, ImportError, TypeError):

                continue

    def _collect_from_class_attributes(
        self,
        cls: type | types.FunctionType | types.MethodType,
        include_submodules: bool,
        max_depth: int,
        current_depth: int,
    ) -> None:

        logger.debug("Collecting from class attributes ------------")

        for attr_name in dir(cls):
            if attr_name.startswith("__"):
                continue

            try:
                attr = getattr(cls, attr_name)
                self._collect_recursive(
                    attr, include_submodules, max_depth, current_depth + 1
                )
            except (AttributeError, TypeError):
                logger.error(f"ERROR ON attr_name {attr_name}")
                continue

    def collect_standalone_items(self, items_list: list[DATA]) -> list[DATA]:

        data = [item for item in items_list if isinstance(item, DATA)]
        return data


def collect_all_data(
    module: ModuleType,
    standalone_items: list[DATA] | None = None,
    include_submodules: bool = True,
) -> list[DATA]:

    collector = DATACollector()

    todos = collector.collect_from_module(module, include_submodules)
    logger.info(f"Found {len(todos)} DATA in module '{module.__name__}'.")

    if standalone_items:
        standalone_todos = collector.collect_standalone_items(standalone_items)
        logger.info(f"Found {len(standalone_todos)} standalone DATA.")
        todos.extend(standalone_todos)

    return todos

```

## File: python\comment_finder.py

```python
from __future__ import annotations

import logging
import tokenize
from ast import walk
from typing import Any

from pycodetags.exceptions import FileParsingError
from pycodetags.utils import persistent_memoize

try:
    from ast_comments import Comment, parse
except ImportError:
    Comment: Any = None  ##

    parse: Any = None  ##


LOGGER = logging.getLogger(__name__)

__all__ = [
    "find_comment_blocks_from_string",
    "find_comment_blocks_from_string_fallback",
]


@persistent_memoize(ttl_seconds=60 * 60 * 24 * 7, use_gzip=True)
def find_comment_blocks_from_string(
    source: str,
) -> list[tuple[int, int, int, int, str]]:

    blocks: list[tuple[int, int, int, int, str]] = []
    if parse is None:

        return find_comment_blocks_from_string_fallback(source)

    if not source:
        return blocks

    try:
        tree = parse(source)
    except tokenize.TokenError:
        logging.warning("Can't parse source code, TokenError")
        return []
    except SyntaxError:
        logging.warning("Can't parse source code, SyntaxError")
        return []
    except ValueError:
        logging.warning("Can't parse source code, ValueError")
        return []
    lines = source.splitlines()

    comments = [node for node in walk(tree) if isinstance(node, Comment)]

    def comment_pos(comment: Comment) -> tuple[int, int, int, int]:

        for i, line in enumerate(lines):
            idx = line.find(comment.value)
            if idx != -1:
                return (i, idx, i, idx + len(comment.value))
        raise FileParsingError(f"Could not locate comment in source: {comment.value}")

    block: list[tuple[int, int, int, int]] = []

    for comment in comments:
        try:
            pos = comment_pos(comment)
        except FileParsingError:
            logging.warning(f"Failed to parse {comment}")
            continue

        if not block:
            block.append(pos)
        else:
            prev_end_line = block[-1][2]
            if pos[0] == prev_end_line + 1:

                block.append(pos)
            else:

                start_line, start_char, _, _ = block[0]
                end_line, _, _, end_char = block[-1]
                final_comment = extract_comment_text(
                    source, (start_line, start_char, end_line, end_char)
                )
                blocks.append(
                    (start_line, start_char, end_line, end_char, final_comment)
                )
                block = [pos]

    if block:
        start_line, start_char, _, _ = block[0]
        end_line, _, _, end_char = block[-1]
        final_comment = extract_comment_text(
            source, (start_line, start_char, end_line, end_char)
        )
        blocks.append((start_line, start_char, end_line, end_char, final_comment))
    return blocks


def extract_comment_text(text: str, offsets: tuple[int, int, int, int]) -> str:

    start_line, start_char, end_line, end_char = offsets

    lines = text.splitlines()

    if start_line == end_line:
        return lines[start_line][start_char:end_char]

    block_lines = [lines[start_line][start_char:]]
    for line_num in range(start_line + 1, end_line):
        block_lines.append(lines[line_num])
    block_lines.append(lines[end_line][:end_char])

    return "\n".join(block_lines)


def find_comment_blocks_from_string_fallback(
    source: str,
) -> list[tuple[int, int, int, int, str]]:

    blocks = []

    lines = source.split("\n")

    in_block = False
    start_line = start_char = 0
    end_line = end_char = 0
    comment_lines: list[str] = []

    for idx, line in enumerate(lines):
        line_wo_newline = line.rstrip("\n")
        comment_pos = line.find("#")

        if comment_pos != -1:
            if not in_block:

                in_block = True
                start_line = idx
                start_char = comment_pos
                comment_lines = []
                LOGGER.debug(
                    "Starting comment block at line %d, char %d", start_line, start_char
                )

            end_line = idx
            end_char = len(line_wo_newline)
            comment_lines.append(line_wo_newline[comment_pos:])

            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            next_comment_pos = next_line.find("#")
            next_stripped = next_line.strip()

            if not next_stripped or next_comment_pos == -1:

                comment_text = "\n".join(comment_lines)
                LOGGER.debug(
                    "Ending comment block at line %d, char %d", end_line, end_char
                )
                blocks.append(
                    (start_line, start_char, end_line, end_char, comment_text)
                )
                in_block = False

        else:
            if in_block:

                comment_text = "\n".join(comment_lines)
                LOGGER.debug(
                    "Ending comment block at line %d, char %d", end_line, end_char
                )
                blocks.append(
                    (start_line, start_char, end_line, end_char, comment_text)
                )
                in_block = False

    if in_block:
        comment_text = "\n".join(comment_lines)
        LOGGER.debug(
            "Ending final comment block at line %d, char %d", end_line, end_char
        )
        blocks.append((start_line, start_char, end_line, end_char, comment_text))
    return blocks


if parse is None:

    find_comment_blocks_from_string = find_comment_blocks_from_string_fallback  ##

```

## File: python\__init__.py

```python

```

## File: utils\cache_utils.py

```python
from __future__ import annotations

import gzip
import hashlib
import logging
import pickle  ##


import shutil
import time
from functools import wraps
from pathlib import Path
from typing import Callable  ##


from typing import Any, TypeVar

logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., Any])


_CACHE_CLEANUP_PERFORMED: dict[str, bool] = {}


def _get_cache_dir(cache_dir_override: Path | None = None) -> Path:

    if cache_dir_override:
        return cache_dir_override

    current_path = Path.cwd().resolve()
    for parent in [current_path] + list(current_path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent / ".pycodetags_cache"

    raise FileNotFoundError(
        "Could not find project root. The 'persistent_memoize' decorator requires "
        "a 'pyproject.toml' file to determine the cache location, or you must "
        "provide a 'cache_dir_override'."
    )


def clear_cache(cache_dir_override: Path | None = None) -> None:

    try:
        cache_dir = _get_cache_dir(cache_dir_override)
        if not cache_dir.is_dir():
            print(f"Cache directory {cache_dir} does not exist. Nothing to clear.")
            return

        for item in cache_dir.iterdir():
            try:
                if item.name == ".gitignore":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except OSError as e:
                print(f"Warning: Could not remove cache item {item}. Error: {e}")
        print(f"Cache cleared successfully at {cache_dir}.")
    except (FileNotFoundError, OSError) as e:
        print(f"Error clearing cache: {e}")


def persistent_memoize(
    ttl_seconds: int = 86400,
    cache_dir_override: Path | None = None,
    use_gzip: bool = False,
    raise_on_missing_config: bool = False,
) -> Callable[[F], F]:

    global _CACHE_CLEANUP_PERFORMED

    try:
        cache_dir = _get_cache_dir(cache_dir_override)
        cache_dir.mkdir(exist_ok=True)

        gitignore_path = cache_dir / ".gitignore"
        if not gitignore_path.exists():
            with gitignore_path.open("w") as f:
                f.write("*\n")

    except (FileNotFoundError, OSError) as e:
        print(f"Warning: Persistent memoization disabled. Reason: {e}")
        if raise_on_missing_config:
            raise FileNotFoundError(
                "Persistent memoization requires a 'pyproject.toml' file to determine "
                "the cache location, or you must provide a 'cache_dir_override'."
            ) from e

        def no_op_decorator(func: F) -> F:
            return func

        return no_op_decorator

    cache_dir_str = str(cache_dir)
    if not _CACHE_CLEANUP_PERFORMED.get(cache_dir_str):
        now = time.time()
        try:
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file() and cache_file.name != ".gitignore":
                    try:
                        modification_time = cache_file.stat().st_mtime
                        if (now - modification_time) > ttl_seconds:
                            cache_file.unlink()
                    except OSError:
                        pass
        except OSError as e:
            print(f"Warning: Could not perform cache cleanup. Error: {e}")
        _CACHE_CLEANUP_PERFORMED[cache_dir_str] = True

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                key_data = pickle.dumps((args, sorted(kwargs.items())))
            except Exception:
                return func(*args, **kwargs)

            hasher = hashlib.sha256()
            hasher.update(func.__qualname__.encode("utf-8"))
            hasher.update(key_data)

            extension = ".pkl.gz" if use_gzip else ".pkl"
            cache_filename = f"{hasher.hexdigest()}{extension}"
            cache_filepath = cache_dir / cache_filename

            if (
                cache_filepath.is_file()
                and (time.time() - cache_filepath.stat().st_mtime) < ttl_seconds
            ):
                try:
                    open_func = gzip.open if use_gzip else open
                    with open_func(cache_filepath, "rb") as f:
                        return pickle.load(f)  ##

                except (
                    pickle.UnpicklingError,
                    EOFError,
                    OSError,
                    gzip.BadGzipFile,
                ) as e:
                    print(
                        f"Warning: Could not read cache file {cache_filepath}. Recomputing. Error: {e}"
                    )

            result = func(*args, **kwargs)
            try:
                open_func = gzip.open if use_gzip else open
                with open_func(cache_filepath, "wb") as f:
                    pickle.dump(result, f)
            except OSError as e:
                print(
                    f"Warning: Could not write to cache file {cache_filepath}. Error: {e}"
                )

            return result

        return wrapper  ##

    return decorator

```

## File: utils\dotenv.py

```python
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _strip_inline_comment(value: str) -> str:

    result = []
    in_single = in_double = False

    for i, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            logger.debug(f"Stripping inline comment starting at index {i}")
            break
        result.append(char)
    return "".join(result).strip()


def _unquote(value: str) -> str:

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def load_dotenv(file_path: Path | None = None) -> None:

    if file_path is None:
        file_path = Path.cwd() / ".env"

    logger.info(f"Looking for .env file at: {file_path}")

    if not file_path.exists():
        logger.info(f".env file not found at: {file_path}")
        return

    logger.info(".env file found. Starting to parse...")

    with file_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            original_line = line.rstrip("\n")
            line = line.strip()

            logger.debug(f"Line {line_number}: '{original_line}'")

            if (
                not line
                or line.startswith("#")
                or line.startswith("#!")
                or line.startswith("!/")
            ):
                logger.debug(
                    f"Line {line_number} is blank, a comment, or a shebang. Skipping."
                )
                continue

            if line.startswith("export "):
                line = line[len("export ") :].strip()

            if "=" not in line:
                logger.warning(
                    f"Line {line_number} is not a valid assignment. Skipping: '{original_line}'"
                )
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                logger.warning(
                    f"Line {line_number} has empty key. Skipping: '{original_line}'"
                )
                continue

            value = _strip_inline_comment(value)
            value = _unquote(value)

            if key in os.environ:
                logger.info(
                    f"Line {line_number}: Key '{key}' already in os.environ. Skipping."
                )
                continue

            os.environ[key] = value
            logger.info(f"Line {line_number}: Loaded '{key}' = '{value}'")


if __name__ == "__main__":
    load_dotenv()

```

## File: utils\__init__.py

```python
__all__ = ["persistent_memoize", "clear_cache", "load_dotenv"]

from pycodetags.utils.cache_utils import clear_cache, persistent_memoize
from pycodetags.utils.dotenv import load_dotenv

```

## File: views\views.py

```python
from __future__ import annotations

import json
import logging
from typing import Any

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.views.view_tools import group_and_sort

logger = logging.getLogger(__name__)


def print_validate(found: list[DATA]) -> bool:

    found_problems = False
    for item in sorted(found, key=lambda x: x.code_tag or ""):
        validations = item.validate()
        if validations:
            found_problems = True
            print(item.as_data_comment())
            print(item.terminal_link())
            for validation in validations:
                print(f"  {validation}")
                print(f"Original Schema {item.original_schema}")
                print(f"Original Text {item.original_schema}")

            print()
    return found_problems


def print_html(found: list[DATA]) -> None:

    tags = set()
    for todo in found:
        tags.add(todo.code_tag)

    for tag in tags:
        for todo in found:

            if todo.code_tag == tag:
                print(f"<h1>{tag}</h1>")
                print("<ul>")
                print(f"<li><strong>{todo.comment}</strong><br>{todo.data_fields}</li>")
                print("</ul>")


def print_text(found: list[DATA]) -> None:

    todos = found
    if todos:
        grouped = group_and_sort(
            todos,
            key_fn=lambda x: x.code_tag or "N/A",
            sort_items=True,
            sort_key=lambda x: x.comment or "N/A",
        )
        for tag, items in grouped.items():
            print(f"--- {tag.upper()} ---")
            for todo in items:
                print(todo.as_data_comment())
                print(todo.terminal_link())
                print()
    else:
        print("No Code Tags found.")


def print_json(found: list[DATA]) -> None:

    todos = found

    output = [t.to_dict() for t in todos]

    def default(o: Any) -> str:
        if hasattr(o, "data_meta"):
            o.data_meta = None

        return json.dumps(o.to_dict()) if hasattr(o, "to_dict") else str(o)

    print(json.dumps(output, indent=2, default=default))


def print_data_md(found: list[DATA]) -> None:

    grouped = group_and_sort(
        found, lambda _: "" if not _.file_path else _.file_path, sort_items=False
    )
    for file, items in grouped.items():
        print(file)
        print("```python")
        for item in items:
            print(item.as_data_comment())
            print()
        print("```")
        print()


def print_summary(found: list[DATA]) -> None:

    from collections import Counter

    tag_counter = Counter(tag.code_tag or "UNKNOWN" for tag in found)

    if not tag_counter:
        print("No code tags found.")
        return

    print("Code Tag Summary:")
    for tag, count in sorted(tag_counter.items()):
        print(f"{tag.upper()}: {count}")

```

## File: views\view_tools.py

```python
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable  ##


def group_and_sort(
    items: list[Any],
    key_fn: Callable[[Any], str],
    sort_items: bool = True,
    sort_key: Callable[[Any], Any] | None = None,
) -> dict[str, list[Any]]:

    grouped: dict[str, list[Any]] = defaultdict(list)

    for item in items:
        raw_key = key_fn(item)
        norm_key = str(raw_key).strip().lower() if raw_key else "(unlabeled)"
        grouped[norm_key].append(item)

    if sort_items:
        for norm_key, group in grouped.items():
            try:
                grouped[norm_key] = sorted(group, key=sort_key or key_fn)
            except Exception as e:
                raise ValueError(f"Failed to sort group '{norm_key}': {e}") from e

    return dict(sorted(grouped.items(), key=lambda x: x[0]))

```

## File: views\__init__.py

```python
__all__ = [
    "print_html",
    "print_json",
    "print_summary",
    "print_text",
    "print_validate",
    "print_data_md",
]

from pycodetags.views.views import (
    print_data_md,
    print_html,
    print_json,
    print_summary,
    print_text,
    print_validate,
)

```

