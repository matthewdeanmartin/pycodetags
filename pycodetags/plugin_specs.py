"""
Pluggy supports
"""

from __future__ import annotations

# pylint: disable=unused-argument
import argparse
from collections.abc import Callable

import pluggy

from pycodetags.config import CodeTagsConfig
from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTag, DataTagSchema
from pycodetags.folk_code_tags import FolkTag

hookspec = pluggy.HookspecMarker("pycodetags")


class CodeTagsSpec:
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
        self,
        command_name: str,
        args: argparse.Namespace,
        found_data: Callable[[DataTagSchema], list[DATA]],
        config: CodeTagsConfig,
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
    def validate(self, item: DataTag, config: CodeTagsConfig) -> list[str]:
        """
        Allows plugins to add custom validation logic to TODO items.

        Args:
            item: The TODO item to validate.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            List of validation error messages.
        """
        return []

    @hookspec
    def find_source_tags(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> list[FolkTag]:
        """
        Allows plugins to provide folk-style code tag parsing for non-Python source files.

        Args:
            already_processed: first pass attempt to find all tags. Be careful of duplicates.
            file_path: The path to the source file.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            A list of FolkTag dictionaries.
        """
        return []

    @hookspec
    def file_handler(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> bool:
        """
        Allows plugins to do something with source file.

        Args:
            already_processed: Indicates if the file has been processed before.
            file_path: The path to the source file.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            True if file processed by plugin
        """
        return False
