"""
Pluggy supports
"""

from __future__ import annotations

# pylint: disable=unused-argument
import argparse

import pluggy

from pycodetags.collection_types import CollectedTODOs
from pycodetags.config import CodeTagsConfig
from pycodetags.folk_code_tags import FolkTag
from pycodetags.todo_tag_types import TODO

hookspec = pluggy.HookspecMarker("pycodetags")


class CodeTagsSpec:
    """A hook specification namespace for pycodetags."""

    @hookspec
    def code_tags_print_report(
        self, format_name: str, found_data: CollectedTODOs, output_path: str, config: CodeTagsConfig
    ) -> bool:
        """
        Allows plugins to define new output report formats.

        Args:
            format_name: The name of the report format to print.
            found_data: The CollectedTODOs data to be printed.
            output_path: The path where the report should be saved.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            bool: True if the plugin handled the report printing, False otherwise.
        """
        return False

    @hookspec
    def code_tags_print_report_style_name(self) -> list[str]:
        """
        Allows plugins announce report format names.

        Returns:
            List of supported format
        """
        return []

    @hookspec
    def code_tags_add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        """
        Allows plugins to add new subcommands to the pycodetags CLI.

        Args:
            subparsers (argparse._SubParsersAction): The ArgumentParser subparsers object to add subcommands to.
        """

    @hookspec
    def code_tags_run_cli_command(
        self, command_name: str, args: argparse.Namespace, found_data: CollectedTODOs, config: CodeTagsConfig
    ) -> bool:
        """
        Allows plugins to handle the execution of their registered CLI commands.

        Args:
            command_name: The name of the command to run.
            args: The parsed arguments for the command.
            found_data: The CollectedTODOs data to be processed.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            bool: True if the command was handled by the plugin, False otherwise.
        """
        return False

    @hookspec
    def code_tags_validate_todo(self, todo_item: TODO, config: CodeTagsConfig) -> list[str]:
        """
        Allows plugins to add custom validation logic to TODO items.

        Args:
            todo_item: The TODO item to validate.
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
