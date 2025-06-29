"""
Pluggy supports
"""

from __future__ import annotations

# pylint: disable=unused-argument
import argparse

import pluggy

from pycodetags.config import CodeTagsConfig
from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTag

hookspec = pluggy.HookspecMarker("pycodetags")


class IssueTrackerSpec:
    """A hook specification namespace for pycodetags."""

    @hookspec
    def register_app(self, pm: pluggy.PluginManager, parser: argparse.ArgumentParser) -> bool:
        """Register a plugin that acts like an app with its own plugins and cli commands."""
        return False

    @hookspec
    def print_report(self, format_name: str, found_data: list[DATA], output_path: str, config: CodeTagsConfig) -> bool:
        """
        Allows plugins to define new output report formats.

        Args:
            format_name: The name of the report format to print.
            found_data: The list[DATA] data to be printed.
            output_path: The path where the report should be saved.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            bool: True if the plugin handled the report printing, False otherwise.
        """
        return False

    @hookspec
    def print_report_style_name(self) -> list[str]:
        """
        Allows plugins announce report format names.

        Returns:
            List of supported format
        """
        return []

    @hookspec
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        """
        Allows plugins to add new subcommands to the pycodetags CLI.

        Args:
            subparsers (argparse._SubParsersAction): The ArgumentParser subparsers object to add subcommands to.
        """

    @hookspec
    def run_cli_command(
        self, command_name: str, args: argparse.Namespace, found_data: list[DATA], config: CodeTagsConfig
    ) -> bool:
        """
        Allows plugins to handle the execution of their registered CLI commands.

        Args:
            command_name: The name of the command to run.
            args: The parsed arguments for the command.
            found_data: The list[DATA] data to be processed.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            bool: True if the command was handled by the plugin, False otherwise.
        """
        return False

    @hookspec
    def validate_domain(self, item: DataTag, config: CodeTagsConfig) -> list[str]:
        """
        Allows plugins to add custom validation logic to TODO items.

        Args:
            item: The TODO item to validate.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            List of validation error messages.
        """
        return []
