from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import cast

from pycodetags_issue_tracker import TODO, views, views_templated

from pycodetags import DATA
from pycodetags.config import CodeTagsConfig


def handle_cli(subparsers: argparse._SubParsersAction):
    _report_parser = subparsers.add_parser(
        "sqlite",
        # parents=[base_parser],
        help="Sqlite Export",
    )
    # # report runs collectors, collected things can be validated
    # report_parser.add_argument("--module", action="append", help="Python module to inspect (e.g., 'my_project.main')")
    # report_parser.add_argument("--src", action="append", help="file or folder of source code")
    #
    # report_parser.add_argument("--output", help="destination file or folder")
    #
    # supported_formats = ["changelog", "validate", "html", "todomd", "donefile", "text"]
    #
    # report_parser.add_argument(
    #     "--format",
    #     choices=supported_formats,
    #     default="text",
    #     help="Output format for the report.",
    # )
    #
    # common_switches(report_parser)


def common_switches(parser) -> None:
    parser.add_argument("--config", help="Path to config file, defaults to current folder pyproject.toml")
    parser.add_argument("--verbose", default=False, action="store_true", help="verbose level logging output")
    parser.add_argument("--info", default=False, action="store_true", help="info level logging output")
    parser.add_argument("--bug-trail", default=False, action="store_true", help="enable bug trail, local logging")


def run_cli_command(
    command_name: str,
    args: argparse.Namespace,
    found_data: Sequence[DATA | TODO],
    # pylint: disable=unused-argument)
    config: CodeTagsConfig,
) -> bool:
    format_name = args.format
    # args.output
    if command_name == "issues":
        if format_name == "validate":
            views.print_validate(cast(list[TODO], found_data))
            return True
        if format_name == "html":
            views_templated.print_html(cast(list[TODO], found_data))
            return True
        if format_name == "todomd":
            views.print_todo_md(cast(list[TODO], found_data))
            return True
        if format_name == "text":
            views.print_text(cast(list[TODO], found_data))
            return True
        if format_name == "changelog":
            views.print_changelog(cast(list[TODO], found_data))
            return True
        if format_name == "donefile":
            views.print_done_file(cast(list[TODO], found_data))
            return True
        return False
    return False
