"""
CLI for pycodetags.
"""

from __future__ import annotations

import argparse
import logging
import logging.config
import sys
from collections.abc import Sequence

import pluggy

import pycodetags.__about__ as __about__
from pycodetags import DATA, DataTagSchema, data_schema
from pycodetags.aggregate import aggregate_all_kinds_multiple_input
from pycodetags.config import CodeTagsConfig, get_code_tags_config
from pycodetags.dotenv import load_dotenv
from pycodetags.exceptions import CommentNotFoundError
from pycodetags.logging_config import generate_config
from pycodetags.plugin_diagnostics import plugin_currently_loaded
from pycodetags.plugin_manager import get_plugin_manager
from pycodetags.views import print_html, print_json, print_summary, print_text, print_validate


class InternalViews:
    """Register internal views as a plugin"""

    @pluggy.HookimplMarker("pycodetags")
    def print_report(self, format_name: str, found_data: list[DATA]) -> bool:
        """
        Internal method to handle printing of reports in various formats.

        Args:
            format_name (str): The name of the format requested by the user.
            found_data (list[DATA]): The data collected from the source code.

        Returns:
            bool: True if the format was handled, False otherwise.
        """
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
    """
    Main entry point for the pycodetags CLI.

    Args:
        argv (Sequence[str] | None): Command line arguments. If None, uses sys.argv.
    """
    pm = get_plugin_manager()

    pm.register(InternalViews())
    # --- end pluggy setup ---

    parser = argparse.ArgumentParser(
        description=f"{__about__.__description__} (v{__about__.__version__})",
        epilog="Install pycodetags-issue-tracker plugin for TODO tags. ",
    )
    common_switches(parser)

    # Basic arguments that apply to all commands (like verbose/info/bug-trail/config)
    base_parser = argparse.ArgumentParser(add_help=False)
    common_switches(base_parser)
    # validate switch
    base_parser.add_argument("--validate", action="store_true", help="Validate all the items found")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'report' command
    report_parser = subparsers.add_parser("data", parents=[base_parser], help="Generate code tag reports")
    # report runs collectors, collected things can be validated
    report_parser.add_argument("--module", action="append", help="Python module to inspect (e.g., 'my_project.main')")
    report_parser.add_argument("--src", action="append", help="file or folder of source code")

    report_parser.add_argument("--output", help="destination file or folder")

    extra_supported_formats = []
    for result in pm.hook.print_report_style_name():
        extra_supported_formats.extend(result)

    supported_formats = list(set(["text", "html", "json", "summary"] + extra_supported_formats))

    report_parser.add_argument(
        "--format",
        choices=supported_formats,
        default="text",
        help="Output format for the report.",
    )
    # report_parser.add_argument("--validate", action="store_true", help="Validate all the items found")

    _plugin_info_parser = subparsers.add_parser(
        "plugin-info", parents=[base_parser], help="Display information about loaded plugins"
    )

    # Allow plugins to add their own subparsers
    new_subparsers = pm.hook.add_cli_subcommands(subparsers=subparsers)
    # Hack because we don't want plugins to have to wire up the basic stuff
    for new_subparser in new_subparsers:
        common_switches(new_subparser)
        # validate switch
        new_subparser.add_argument("--validate", action="store_true", help="Validate all the items found")

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
        # Essentially, quiet mode
        config = generate_config(level="FATAL", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)

    if not args.command:
        parser.print_help()
        return 1

    # Handle the 'report' command
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
            found = aggregate_all_kinds_multiple_input(modules, src, data_schema.PureDataSchema)

        except ImportError:
            print(f"Error: Could not import module(s) '{args.module}'", file=sys.stderr)
            return 1

        if args.validate:
            if len(found) == 0:
                raise CommentNotFoundError("No data to validate.")
            print_validate(found)
        else:
            if len(found) == 0:
                raise CommentNotFoundError("No data to report.")
            # Call the hook.
            results = pm.hook.print_report(
                format_name=args.format, output_path=args.output, found_data=found, config=get_code_tags_config()
            )
            if not any(results):
                print(f"Error: Format '{args.format}' is not supported.", file=sys.stderr)
                return 1
                # --- NEW: Handle 'plugin-info' command ---
    elif args.command == "plugin-info":
        plugin_currently_loaded(pm)
    else:
        # Pass control to plugins for other commands
        # Aggregate data if plugins might need it
        if hasattr(args, "module") and args.module:
            modules = getattr(args, "module", [])
        else:
            modules = code_tags_config.modules_to_scan()

        if hasattr(args, "src") and args.src:
            src = getattr(args, "src", [])
        else:
            src = code_tags_config.source_folders_to_scan()

        def found_data_for_plugins_callback(schema: DataTagSchema) -> list[DATA]:
            return source_and_modules_searcher(args.command, modules, src, schema)

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


def source_and_modules_searcher(command: str, modules: list[str], src: list[str], schema: DataTagSchema) -> list[DATA]:
    try:
        all_found: list[DATA] = []
        for source in src:
            found_tags = aggregate_all_kinds_multiple_input([""], [source], schema)
            all_found.extend(found_tags)
        more_found = aggregate_all_kinds_multiple_input(modules, [], schema)
        all_found.extend(more_found)
        found_data_for_plugins = all_found
    except ImportError:
        logging.warning(f"Could not aggregate data for command {command}, proceeding without it.")
        found_data_for_plugins = []
    return found_data_for_plugins


def common_switches(parser) -> None:
    parser.add_argument("--config", help="Path to config file, defaults to current folder pyproject.toml")
    parser.add_argument("--verbose", default=False, action="store_true", help="verbose level logging output")
    parser.add_argument("--info", default=False, action="store_true", help="info level logging output")
    parser.add_argument("--bug-trail", default=False, action="store_true", help="enable bug trail, local logging")


if __name__ == "__main__":
    sys.exit(main())
