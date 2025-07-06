"""
Registry of plugin hooks. These are exported via "entrypoints".
"""

import argparse
from collections.abc import Callable, Sequence

import pluggy
from pluggy import HookimplMarker

from pycodetags import DATA, DataTagSchema
from pycodetags.config import CodeTagsConfig

hookimpl = HookimplMarker("pycodetags")


class ChatApp:
    """Organizes pluggy hooks"""

    @hookimpl
    def register_app(
        self,
        pm: pluggy.PluginManager,
        # pylint: disable=unused-argument
        parser: argparse.ArgumentParser,
    ) -> bool:
        """Allow plugin to support its own plugins"""
        return False

    @hookimpl
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        """Register all commands the plugin supports into the argparser"""

    @hookimpl
    def run_cli_command(
        self,
        # pylint: disable=unused-argument
        command_name: str,
        # pylint: disable=unused-argument
        args: argparse.Namespace,
        # pylint: disable=unused-argument
        found_data: Callable[[DataTagSchema], Sequence[DATA]],
        # pylint: disable=unused-argument
        config: CodeTagsConfig,
    ) -> bool:
        """Run any CLI command that the plugin supports"""
        return False

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
        return False

    @hookimpl
    def print_report_style_name(self) -> list[str]:
        """Name of format of data report that the plugin supports"""
        # Returns a new way to view raw data.
        return []


chat_app_plugin = ChatApp()
