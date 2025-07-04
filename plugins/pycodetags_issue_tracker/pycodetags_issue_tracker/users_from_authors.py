"""
Author file parsing.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_authors_file_simple(file_path: str) -> list[str]:
    """Parses an AUTHORS file to extract unique author names."""
    authors = set()
    for item in parse_authors_file(file_path):
        for _, value in item.items():
            authors.add(value)
    return list(authors)


def parse_authors_file(file_path: str) -> list[dict[str, str | Any]]:
    """
    Parses an AUTHORS file, attempting to extract names and emails.
    Handles common formats but is flexible due to the "folk schema" nature.

    Args:
        file_path (str): The path to the AUTHORS file.

    Returns:
        list: A list of dictionaries, where each dictionary represents an author
              and may contain 'name' and 'email' keys.
    """
    authors = []
    # Regex to capture name and optional email
    # Groups: 1=name, 2=email (if present)
    author_pattern = re.compile(r"^\s*(.*?)(?:\s+<([^>]+)>)?\s*$")

    with open(file_path, encoding="utf-8") as file_handle:
        for line in file_handle:
            line = line.strip()
            if not line or line.startswith("#"):  # Skip empty lines and comments
                continue

            match = author_pattern.match(line)
            if match:
                name = match.group(1).strip()
                email = match.group(2)

                author_info = {"name": name}
                if email:
                    author_info["email"] = email.strip()
                authors.append(author_info)
            else:
                # If a line doesn't match the common pattern, you might
                # want to log it or handle it differently.
                # For simplicity, we'll just add the whole line as a name.
                authors.append({"name": line})
                print(f"Warning: Could not fully parse line: '{line}'")

    return authors


# --- Example Usage ---
if __name__ == "__main__":

    def example() -> None:
        """
        Example function to demonstrate how to use the parse_authors_file function.
        """
        # Create a dummy AUTHORS file for testing
        dummy_authors_content = """
# Project Contributors

John Doe <john.doe@example.com>
Jane Smith
Alice Wonderland <alice@wonderland.org>
Bob The Builder (Maintenance Lead)
    # A comment line
Charlie Chaplin
    """
        with open("AUTHORS_test.txt", "w", encoding="utf-8") as f:
            f.write(dummy_authors_content.strip())

        parsed_authors = parse_authors_file("AUTHORS_test.txt")

        print("Parsed Authors:")
        for author in parsed_authors:
            print(author)

        os.remove("AUTHORS_test.txt")

    example()
