"""
Register plugin hooks
"""

import argparse
from collections.abc import Sequence

import pluggy
from pluggy import HookimplMarker
from pycodetags_issue_tracker import cli
from pycodetags_issue_tracker.converters import convert_data_to_TODO
from pycodetags_issue_tracker.plugin_manager import set_plugin_manager

from pycodetags import DATA
from pycodetags.config import CodeTagsConfig

hookimpl = HookimplMarker("pycodetags")


class IssueTrackerApp:
    @hookimpl
    def register_app(self, pm: pluggy.PluginManager, parser: argparse.ArgumentParser) -> bool:
        set_plugin_manager(new_pm=pm)
        # TODO: register issue tracker specific commands, e.g. remove DONE
        return True

    @hookimpl
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        cli.handle_cli(subparsers)

    @hookimpl
    def run_cli_command(
        self, command_name: str, args: argparse.Namespace, found_data: Sequence[DATA], config: CodeTagsConfig
    ) -> bool:
        found_todos = [convert_data_to_TODO(_) for _ in found_data]
        return cli.run_cli_command(command_name, args, found_todos, config)

    @hookimpl
    def print_report(
        self,
        format_name: str,
        found_data: list[DATA],
        # pylint: disable=unused-argument
        output_path: str,
        # pylint: disable=unused-argument
        config: CodeTagsConfig,
    ) -> bool:
        # Returns a new way to view raw data.
        # This doesn't work for domain specific TODOs

        [convert_data_to_TODO(_) for _ in found_data]

        if format_name == "todo.md":
            print("hello!")
            return True
        return False

    @hookimpl
    def print_report_style_name(self) -> list[str]:
        # Returns a new way to view raw data.
        # This doesn't work for domain specific TODOs
        return []


issue_tracker_app_plugin = IssueTrackerApp()
