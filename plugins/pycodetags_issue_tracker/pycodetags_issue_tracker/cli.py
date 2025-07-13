from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import cast

from pycodetags_issue_tracker import TODO
from pycodetags_issue_tracker.views import views_templated
from pycodetags_issue_tracker.views.views import (
    print_changelog,
    print_done_file,
    print_text,
    print_todo_md,
    print_validate,
)

from pycodetags import DATA
from pycodetags.app_config.config import CodeTagsConfig


def handle_cli(subparsers: argparse._SubParsersAction):
    report_parser = subparsers.add_parser(
        "issues",
        # parents=[base_parser],
        help="Reports for TODOs and BUGs",
    )
    # report runs collectors, collected things can be validated
    report_parser.add_argument("--module", action="append", help="Python module to inspect (e.g., 'my_project.main')")
    report_parser.add_argument("--src", action="append", help="file or folder of source code")

    report_parser.add_argument("--output", help="destination file or folder")

    supported_formats = ["changelog", "validate", "html", "todomd", "donefile", "text"]

    report_parser.add_argument(
        "--format",
        choices=supported_formats,
        default="text",
        help="Output format for the report.",
    )

    common_switches(report_parser)


def common_switches(parser) -> None:
    parser.add_argument("--config", help="Path to config file, defaults to current folder pyproject.toml")
    parser.add_argument("--verbose", default=False, action="store_true", help="verbose level logging output")
    parser.add_argument("--info", default=False, action="store_true", help="info level logging output")
    parser.add_argument("--bug-trail", default=False, action="store_true", help="enable bug trail, local logging")
    parser.add_argument("--filter", help="JMESPath filter")


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
            if print_validate(cast(list[TODO], found_data)):
                sys.exit(100)
            return True
        if format_name == "html":
            views_templated.print_html(cast(list[TODO], found_data))
            return True
        if format_name == "todomd":
            print_todo_md(cast(list[TODO], found_data))
            return True
        if format_name == "text":
            print_text(cast(list[TODO], found_data))
            return True
        if format_name == "changelog":
            print_changelog(cast(list[TODO], found_data))
            return True
        if format_name == "donefile":
            print_done_file(cast(list[TODO], found_data))
            return True
        return False
    return False
