"""
Registry of plugin hooks. These are exported via "entrypoints".
"""

import argparse
from collections.abc import Callable, Sequence

import pluggy
from pluggy import HookimplMarker
from pycodetags_issue_tracker import cli
from pycodetags_issue_tracker.converters import convert_data_to_TODO
from pycodetags_issue_tracker.issue_tracker_schema import IssueTrackerSchema
from pycodetags_issue_tracker.plugin_manager import set_plugin_manager

from pycodetags import DATA, DataTagSchema
from pycodetags.config import CodeTagsConfig

hookimpl = HookimplMarker("pycodetags")


class IssueTrackerApp:
    """Organizes pluggy hooks"""
    @hookimpl
    def register_app(
        self,
        pm: pluggy.PluginManager,
        # pylint: disable=unused-argument
        parser: argparse.ArgumentParser,
    ) -> bool:
        """Allow plugin to support its own plugins"""
        set_plugin_manager(new_pm=pm)
        # TODO: register issue tracker specific commands, e.g. remove DONE
        #  <matth 2025-07-04 priority:low category:plugin status:development release:1.0.0 iteration:1>
        return True

    @hookimpl
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        """Register all commands the plugin supports into the argparser"""
        cli.handle_cli(subparsers)

    @hookimpl
    def run_cli_command(
        self, command_name: str, args: argparse.Namespace, found_data:
            Callable[[DataTagSchema], Sequence[DATA]], config: CodeTagsConfig
    ) -> bool:
        """Run any CLI command that the plugin supports"""
        callback_data = found_data(IssueTrackerSchema)
        found_todos = [convert_data_to_TODO(_) for _ in callback_data]
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
        """Handle a data report"""
        # Returns a new way to view raw data.
        # This doesn't work for domain specific TODOs

        # [convert_data_to_TODO(_) for _ in found_data]

        if format_name == "todo.md":
            print("hello!")
            return True
        return False

    @hookimpl
    def print_report_style_name(self) -> list[str]:
        """Name of format of data report that the plugin supports"""
        # Returns a new way to view raw data.
        # This doesn't work for domain specific TODOs
        return []


issue_tracker_app_plugin = IssueTrackerApp()
